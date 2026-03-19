# -*- coding: utf-8 -*-
"""
媒体服务器媒体库服务
"""
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.media_server_library_stats import MediaServerLibraryStats
from app.models.media_server_library import MediaServerLibrary
from app.services.media_server.media_server_config_service import MediaServerConfigService
from app.utils.timezone import now

logger = logging.getLogger(__name__)


class MediaServerLibraryService:
    """媒体服务器媒体库服务"""

    @staticmethod
    async def get_libraries(db: AsyncSession, config_id: int, include_hidden: bool = False) -> List[Dict[str, Any]]:
        """
        获取媒体库列表（优先从数据库读取）

        Args:
            db: 数据库会话
            config_id: 媒体服务器配置ID
            include_hidden: 是否包含隐藏的媒体库

        Returns:
            List[Dict]: 标准化的媒体库列表
        """
        # 尝试从数据库获取
        query = select(MediaServerLibrary).where(MediaServerLibrary.media_server_config_id == config_id)
        result = await db.execute(query)
        libraries = result.scalars().all()

        if libraries:
            # 结果处理
            results = [
                {
                    "id": lib.library_id,
                    "name": lib.name,
                    "type": lib.type,
                    "locations": lib.locations,
                    "image_url": lib.image_url,
                    "web_url": lib.web_url,
                    "item_count": lib.item_count,
                    "last_scan_at": lib.last_scan_at,
                    "config_id": config_id
                }
                for lib in libraries
            ]
            
            if not include_hidden:
                # 获取配置以检查排除列表
                config = await MediaServerConfigService.get_by_id(db, config_id)
                if config and config.server_config:
                    excluded_ids = config.server_config.get("excluded_library_ids")
                    if excluded_ids:
                        if isinstance(excluded_ids, str):
                            excluded_ids = [i.strip() for i in excluded_ids.split(",") if i.strip()]
                        results = [l for l in results if l["id"] not in excluded_ids]
            
            return results

        # 如果数据库没有，则实时同步一次
        return await MediaServerLibraryService.sync_libraries(db, config_id, include_hidden=include_hidden)

    @staticmethod
    async def sync_libraries(db: AsyncSession, config_id: int, include_hidden: bool = False) -> List[Dict[str, Any]]:
        """
        同步媒体服务器库信息到数据库

        Args:
            db: 数据库会话
            config_id: 媒体服务器配置ID
            include_hidden: 是否包含隐藏的媒体库

        Returns:
            List[Dict]: 同步后的媒体库列表
        """
        # 获取配置
        config = await MediaServerConfigService.get_by_id(db, config_id)
        if not config:
            raise ValueError(f"Media server config not found: {config_id}")

        # 获取适配器
        adapter = MediaServerConfigService._get_adapter(config)

        # 获取媒体库列表
        try:
            remote_libraries = await adapter.get_libraries()
            
            # 获取现有记录
            query = select(MediaServerLibrary).where(MediaServerLibrary.media_server_config_id == config_id)
            result = await db.execute(query)
            existing_libs = {lib.library_id: lib for lib in result.scalars().all()}
            
            current_lib_ids = set()
            synced_libraries = []
            
            for lib_data in remote_libraries:
                lib_id = lib_data.get("id")
                current_lib_ids.add(lib_id)
                
                if lib_id in existing_libs:
                    # 更新
                    lib = existing_libs[lib_id]
                    lib.name = lib_data.get("name")
                    lib.type = lib_data.get("type")
                    lib.locations = lib_data.get("locations")
                    lib.image_url = lib_data.get("image_url")
                    lib.web_url = lib_data.get("web_url")
                    lib.item_count = lib_data.get("item_count", 0)
                    if lib_data.get("last_scan_at"):
                        lib.last_scan_at = lib_data.get("last_scan_at")
                else:
                    # 新增
                    lib = MediaServerLibrary(
                        media_server_config_id=config_id,
                        library_id=lib_id,
                        name=lib_data.get("name"),
                        type=lib_data.get("type"),
                        locations=lib_data.get("locations"),
                        image_url=lib_data.get("image_url"),
                        web_url=lib_data.get("web_url"),
                        item_count=lib_data.get("item_count", 0),
                        last_scan_at=lib_data.get("last_scan_at")
                    )
                    db.add(lib)
                
                synced_libraries.append({
                    "id": lib_id,
                    "name": lib_data.get("name"),
                    "type": lib_data.get("type"),
                    "locations": lib_data.get("locations"),
                    "image_url": lib_data.get("image_url"),
                    "web_url": lib_data.get("web_url"),
                    "item_count": lib_data.get("item_count", 0),
                    "last_scan_at": lib_data.get("last_scan_at"),
                    "config_id": config_id
                })

            # 删除不再存在的库
            for lib_id, lib in existing_libs.items():
                if lib_id not in current_lib_ids:
                    await db.delete(lib)
            
            await db.commit()
            logger.info(f"Synced {len(synced_libraries)} libraries from {config.name}")

            if not include_hidden:
                # 过滤排除的库
                excluded_ids = config.server_config.get("excluded_library_ids") if config.server_config else None
                if excluded_ids:
                    if isinstance(excluded_ids, str):
                        excluded_ids = [i.strip() for i in excluded_ids.split(",") if i.strip()]
                    
                    synced_libraries = [l for l in synced_libraries if l["id"] not in excluded_ids]

            return synced_libraries
            
        except Exception as e:
            logger.error(f"Failed to sync libraries from media server: {str(e)}")
            raise

    @staticmethod
    async def refresh_library(db: AsyncSession, config_id: int, library_id: Optional[str] = None) -> bool:
        """
        刷新媒体库

        Args:
            db: 数据库会话
            config_id: 媒体服务器配置ID
            library_id: 媒体库ID（可选），如果为None则刷新所有媒体库

        Returns:
            bool: 刷新操作是否成功触发
        """
        # 获取配置
        config = await MediaServerConfigService.get_by_id(db, config_id)
        if not config:
            raise ValueError(f"Media server config not found: {config_id}")

        # 获取适配器
        adapter = MediaServerConfigService._get_adapter(config)

        # 刷新媒体库
        try:
            success = await adapter.refresh_library(library_id)
            if success:
                from sqlalchemy import update
                from app.utils.timezone import now
                
                # 构造更新语句
                stmt = update(MediaServerLibrary).where(MediaServerLibrary.media_server_config_id == config_id)
                if library_id:
                    stmt = stmt.where(MediaServerLibrary.library_id == library_id)
                    logger.info(f"Refreshed library {library_id} on {config.name}")
                else:
                    logger.info(f"Refreshed all libraries on {config.name}")
                
                # 更新 last_scan_at
                await db.execute(stmt.values(last_scan_at=now()))
                await db.commit()
            else:
                logger.warning(f"Failed to trigger library refresh on {config.name}")
            return success
        except Exception as e:
            logger.error(f"Failed to refresh library: {str(e)}")
            return False

    @staticmethod
    async def update_library_stats(db: AsyncSession, config_id: int) -> Dict[str, Any]:
        """
        更新媒体库统计缓存

        Args:
            db: 数据库会话
            config_id: 媒体服务器配置ID

        Returns:
            Dict: 统计数据
        """
        # 获取配置
        config = await MediaServerConfigService.get_by_id(db, config_id)
        if not config:
            raise ValueError(f"Media server config not found: {config_id}")

        # 获取适配器
        adapter = MediaServerConfigService._get_adapter(config)

        # 获取统计数据
        try:
            stats_data = await adapter.get_library_stats()
            # 同时同步媒体库基本信息
            await MediaServerLibraryService.sync_libraries(db, config_id)
        except Exception as e:
            logger.error(f"Failed to get library stats from media server: {str(e)}")
            raise

        # 查询是否已有缓存记录
        query = select(MediaServerLibraryStats).where(
            MediaServerLibraryStats.media_server_config_id == config_id
        )
        result = await db.execute(query)
        existing_stats = result.scalar_one_or_none()

        if existing_stats:
            # 更新现有记录
            existing_stats.stats_data = stats_data
            await db.commit()
            await db.refresh(existing_stats)
            logger.info(f"Updated library stats cache for {config.name}")
        else:
            # 创建新记录
            new_stats = MediaServerLibraryStats(media_server_config_id=config_id, stats_data=stats_data)
            db.add(new_stats)
            await db.commit()
            await db.refresh(new_stats)
            logger.info(f"Created library stats cache for {config.name}")

        return stats_data

    @staticmethod
    async def get_library_stats(db: AsyncSession, config_id: int, use_cache: bool = True) -> Dict[str, Any]:
        """
        获取媒体库统计信息

        Args:
            db: 数据库会话
            config_id: 媒体服务器配置ID
            use_cache: 是否使用缓存（默认True）

        Returns:
            Dict: 统计数据
        """
        if use_cache:
            # 尝试从缓存获取
            query = select(MediaServerLibraryStats).where(
                MediaServerLibraryStats.media_server_config_id == config_id
            )
            result = await db.execute(query)
            cached_stats = result.scalar_one_or_none()

            if cached_stats:
                logger.debug(f"Using cached library stats for config {config_id}")
                return MediaServerLibraryService._normalize_stats(cached_stats.stats_data)

        # 缓存不存在或不使用缓存，实时获取并更新缓存
        logger.debug(f"Fetching fresh library stats for config {config_id}")
        raw_stats = await MediaServerLibraryService.update_library_stats(db, config_id)
        return MediaServerLibraryService._normalize_stats(raw_stats)

    @staticmethod
    def _normalize_stats(raw_stats: Dict[str, Any]) -> Dict[str, Any]:
        """标准化统计数据"""
        # Jellyfin/Emby 格式
        movie_count = raw_stats.get("MovieCount") or raw_stats.get("movie_count", 0)
        tv_count = raw_stats.get("SeriesCount") or raw_stats.get("tv_count", 0)
        episode_count = raw_stats.get("EpisodeCount") or raw_stats.get("episode_count", 0)
        
        # 用户统计通常由 Adapter.get_users().count() 决定，但这里先只做媒体统计
        # 完善返回结果
        return {
            "stats_data": raw_stats,
            "movie_count": int(movie_count),
            "tv_count": int(tv_count),
            "episode_count": int(episode_count),
            "user_count": raw_stats.get("UserCount", 0)
        }
