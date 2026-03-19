# -*- coding: utf-8 -*-
"""
榜单同步服务

两阶段同步架构：
- 阶段一：快速落表（sync_collection） - 仅保存基础信息到 trending_collections
- 阶段二：详情同步（sync_collection_details） - 异步任务补全 unified 资源关联
"""
import logging
from typing import List, Dict, Any, Optional

from sqlalchemy import select, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trending_collection import TrendingCollection
from app.adapters.metadata.tmdb_adapter import TMDBAdapter
from app.adapters.metadata.douban_adapter import DoubanAdapter
from app.services.identification.unified_movie_service import UnifiedMovieService
from app.services.identification.unified_tv_series_service import UnifiedTVSeriesService
from app.constants.trending import (
    COLLECTION_TYPE_ADAPTER_METHODS,
    COLLECTION_TYPE_COUNT,
    COLLECTION_TYPE_MEDIA_TYPES,
    DEFAULT_TRENDING_SYNC_COUNT,
)
from app.utils.timezone import now
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class TrendingSyncService:
    """榜单同步服务（两阶段架构）"""

    # ==================== 阶段一：快速落表 ====================

    @staticmethod
    async def sync_collection(
        db: AsyncSession,
        collection_type: str,
        count: int = DEFAULT_TRENDING_SYNC_COUNT,
    ) -> Dict[str, Any]:
        """
        同步单个榜单（阶段一：快速落表）

        工作流程：
        1. 调用适配器获取榜单基础数据（豆瓣/TMDB）
        2. 清空旧榜单数据
        3. 批量插入新榜单记录（仅基础信息，不关联 unified 资源）

        Args:
            db: 数据库会话
            collection_type: 榜单类型
            count: 榜单数量

        Returns:
            同步结果统计
        """
        # 使用榜单特定数量配置（如 TOP250 应获取 250 条）
        actual_count = COLLECTION_TYPE_COUNT.get(collection_type, count)
        logger.info(f"开始同步榜单: {collection_type}, count={actual_count}")

        # 1. 获取适配器和方法名
        if collection_type not in COLLECTION_TYPE_ADAPTER_METHODS:
            raise ValueError(f"未知的榜单类型: {collection_type}")

        adapter_type, method_name = COLLECTION_TYPE_ADAPTER_METHODS[collection_type]
        media_type = COLLECTION_TYPE_MEDIA_TYPES.get(collection_type)
        if not media_type:
            raise ValueError(f"未知的媒体类型: {collection_type}")

        # 4. 调用适配器获取榜单数据
        logger.info(f"从 {adapter_type}.{method_name} 获取数据")

        try:
            all_items = []

            if adapter_type == "douban":
                # 豆瓣：所有接口都支持 start/count 分页
                # 注意：豆瓣不需要代理（国内服务，直连即可）
                adapter = DoubanAdapter({})
                method = getattr(adapter, method_name)

                batch_size = 50
                for start in range(0, actual_count, batch_size):
                    batch_count = min(batch_size, actual_count - start)
                    items = await method(start=start, count=batch_count)
                    all_items.extend(items)
                    if len(items) < batch_count:
                        break
            else:
                # TMDB：需要分页获取（每页最多20条）
                tmdb_config = await TrendingSyncService._get_tmdb_config(db)
                adapter = TMDBAdapter(tmdb_config)
                method = getattr(adapter, method_name)
                
                pages_needed = (actual_count + 19) // 20
                for page in range(1, pages_needed + 1):
                    items = await method(page=page)
                    all_items.extend(items)
                    if len(items) < 20:
                        break

            # 限制数量
            all_items = all_items[:actual_count]
            logger.info(f"从 {adapter_type} 获取了 {len(all_items)} 条数据")

        except Exception as e:
            logger.error(f"从 {adapter_type} 获取数据失败: {str(e)}")
            raise

        # 5. 清空旧榜单数据
        delete_stmt = delete(TrendingCollection).where(
            TrendingCollection.collection_type == collection_type
        )
        result = await db.execute(delete_stmt)
        deleted_count = result.rowcount
        logger.info(f"删除了 {deleted_count} 条旧榜单记录: {collection_type}")

        # 6. 批量插入新榜单数据（仅基础信息）
        synced_at = now()
        records = []
        seen_ids = set()
        rank_counter = 1

        for item in all_items:
            # 提取来源ID
            source_id = TrendingSyncService._extract_source_id(item, adapter_type)
            if not source_id:
                logger.warning(f"跳过无来源ID的项目: {item.get('title', 'unknown')}")
                continue

            # 去重检查
            source_id_str = str(source_id)
            if source_id_str in seen_ids:
                logger.info(f"跳过重复榜单项目: {item.get('title', 'unknown')} (id={source_id_str})")
                continue
            seen_ids.add(source_id_str)

            record = TrendingCollection(
                collection_type=collection_type,
                media_type=media_type,
                rank_position=rank_counter,
                source_type=adapter_type,
                source_id=source_id_str,
                raw_data=item,  # 保存完整的原始数据
                unified_resource_id=None,  # 阶段二填充
                detail_synced=False,
                synced_at=synced_at,
            )
            records.append(record)
            rank_counter += 1

        db.add_all(records)
        await db.commit()
        inserted_count = len(records)
        logger.info(f"插入了 {inserted_count} 条新榜单记录: {collection_type}")

        return {
            "collection_type": collection_type,
            "fetched_count": len(all_items),
            "inserted_count": inserted_count,
            "deleted_count": deleted_count,
            "pending_detail_sync": inserted_count,
        }

    @staticmethod
    def _extract_source_id(item: Dict[str, Any], adapter_type: str) -> Optional[str]:
        """提取来源ID"""
        if adapter_type == "douban":
            return item.get("douban_id")
        else:  # tmdb
            return item.get("tmdb_id")

    # ==================== 阶段二：详情同步 ====================

    @staticmethod
    async def sync_collection_details(
        db: AsyncSession,
        collection_type: Optional[str] = None,
        batch_size: int = 20,
    ) -> Dict[str, Any]:
        """
        同步榜单详情（阶段二：异步任务）

        工作流程：
        1. 查询 detail_synced = False 的记录
        2. 调用 find_or_create() 创建/更新 unified 资源
        3. 更新 unified_resource_id 和 detail_synced

        Args:
            db: 数据库会话
            collection_type: 榜单类型（可选，不指定则处理所有待同步记录）
            batch_size: 每批处理数量

        Returns:
            同步结果统计
        """
        # 1. 查询待同步记录
        query = select(TrendingCollection).where(
            TrendingCollection.detail_synced == False  # noqa: E712
        )
        if collection_type:
            query = query.where(TrendingCollection.collection_type == collection_type)
        
        query = query.order_by(
            TrendingCollection.collection_type,
            TrendingCollection.rank_position,
        ).limit(batch_size)

        result = await db.execute(query)
        pending_records = result.scalars().all()

        if not pending_records:
            logger.info("没有待同步的榜单详情")
            return {
                "processed_count": 0,
                "success_count": 0,
                "error_count": 0,
            }

        logger.info(f"开始同步 {len(pending_records)} 条榜单详情")

        success_count = 0
        error_count = 0

        for record in pending_records:
            try:
                # 从 raw_data 提取元数据
                raw_data = record.raw_data or {}
                douban_id = raw_data.get("douban_id")
                imdb_id = raw_data.get("imdb_id")
                tmdb_id = raw_data.get("tmdb_id")

                # 清理 metadata
                metadata_clean = {
                    k: v for k, v in raw_data.items()
                    if k not in ["media_type", "metadata_source"]
                }

                # 调用 find_or_create
                if record.media_type == "movie":
                    resource, _ = await UnifiedMovieService.find_or_create(
                        db,
                        douban_id=douban_id,
                        imdb_id=imdb_id,
                        tmdb_id=tmdb_id,
                        metadata=metadata_clean,
                    )
                else:  # tv
                    resource, _ = await UnifiedTVSeriesService.find_or_create(
                        db,
                        douban_id=douban_id,
                        imdb_id=imdb_id,
                        tmdb_id=tmdb_id,
                        metadata=metadata_clean,
                    )

                # 更新记录
                record.unified_resource_id = resource.id
                record.detail_synced = True
                success_count += 1

            except Exception as e:
                logger.error(
                    f"同步详情失败: collection={record.collection_type}, "
                    f"rank={record.rank_position}, error={str(e)}"
                )
                error_count += 1
                continue

        await db.commit()

        logger.info(
            f"详情同步完成: 成功 {success_count} 条, 失败 {error_count} 条"
        )

        return {
            "processed_count": len(pending_records),
            "success_count": success_count,
            "error_count": error_count,
        }

    @staticmethod
    async def get_pending_detail_count(
        db: AsyncSession,
        collection_type: Optional[str] = None,
    ) -> int:
        """获取待同步详情数量"""
        from sqlalchemy import func

        query = select(func.count(TrendingCollection.id)).where(
            TrendingCollection.detail_synced == False  # noqa: E712
        )
        if collection_type:
            query = query.where(TrendingCollection.collection_type == collection_type)

        result = await db.execute(query)
        return result.scalar() or 0

    # ==================== 批量同步 ====================

    @staticmethod
    async def sync_all_collections(
        db: AsyncSession,
        collection_types: List[str],
        count: int = DEFAULT_TRENDING_SYNC_COUNT,
    ) -> List[Dict[str, Any]]:
        """
        同步多个榜单（阶段一）

        Args:
            db: 数据库会话
            collection_types: 榜单类型列表
            count: 每个榜单数量

        Returns:
            同步结果列表
        """
        results = []

        for collection_type in collection_types:
            try:
                result = await TrendingSyncService.sync_collection(
                    db, collection_type, count
                )
                results.append(result)
            except Exception as e:
                logger.error(f"同步榜单 {collection_type} 失败: {str(e)}")
                results.append({
                    "collection_type": collection_type,
                    "error": str(e),
                })

        return results

    # ==================== 配置获取 ====================

    @staticmethod
    async def _get_proxy_config(db: AsyncSession) -> Dict[str, Any]:
        """从数据库获取代理配置"""
        from sqlalchemy import select
        from app.models.system_setting import SystemSetting

        proxy_query = select(SystemSetting).where(
            SystemSetting.category == "metadata_scraping",
            SystemSetting.key == "tmdb_proxy",
        )
        proxy_result = await db.execute(proxy_query)
        proxy_setting = proxy_result.scalar_one_or_none()

        if proxy_setting and proxy_setting.value:
            return {"enabled": True, "url": proxy_setting.value}
        return {}

    @staticmethod
    async def _get_tmdb_config(db: AsyncSession) -> Dict[str, Any]:
        """从数据库获取 TMDB 配置"""
        from sqlalchemy import select
        from app.models.system_setting import SystemSetting

        settings = get_settings()

        api_key_query = select(SystemSetting).where(
            SystemSetting.category == "metadata_scraping",
            SystemSetting.key == "tmdb_api_key",
        )
        api_key_result = await db.execute(api_key_query)
        api_key_setting = api_key_result.scalar_one_or_none()

        api_key = (
            api_key_setting.value
            if api_key_setting and api_key_setting.value
            else settings.TMDB_API_KEY
        )

        if not api_key:
            raise ValueError(
                "TMDB API Key 未配置，无法同步 TMDB 榜单。\n"
                "请在系统设置中添加：category='metadata_scraping', key='tmdb_api_key'\n"
                "或设置环境变量：TMDB_API_KEY"
            )

        proxy_config = await TrendingSyncService._get_proxy_config(db)

        return {
            "api_key": api_key,
            "language": settings.TMDB_LANGUAGE,
            "proxy_config": proxy_config,
        }
