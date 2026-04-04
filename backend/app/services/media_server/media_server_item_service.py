# -*- coding: utf-8 -*-
"""
媒体服务器媒体项服务
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.models.media_server_item import MediaServerItem
from app.models.media_file import MediaFile
from app.utils.timezone import now

logger = logging.getLogger(__name__)


class MediaServerItemService:
    """媒体服务器媒体项服务"""

    @staticmethod
    async def get_by_id(db: AsyncSession, item_id: int) -> Optional[MediaServerItem]:
        """
        根据ID获取媒体项

        Args:
            db: 数据库会话
            item_id: 媒体项ID

        Returns:
            MediaServerItem: 媒体项对象，不存在则返回None
        """
        result = await db.execute(select(MediaServerItem).where(MediaServerItem.id == item_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_server_item_id(
        db: AsyncSession, config_id: int, server_item_id: str
    ) -> Optional[MediaServerItem]:
        """
        根据服务器配置ID和服务器端媒体项ID获取媒体项

        Args:
            db: 数据库会话
            config_id: 媒体服务器配置ID
            server_item_id: 服务器端媒体项ID

        Returns:
            MediaServerItem: 媒体项对象，不存在则返回None
        """
        result = await db.execute(
            select(MediaServerItem).where(
                and_(
                    MediaServerItem.media_server_config_id == config_id,
                    MediaServerItem.server_item_id == server_item_id,
                )
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_list(
        db: AsyncSession,
        config_id: Optional[int] = None,
        media_type: Optional[str] = None,
        item_type: Optional[str] = None,
        library_id: Optional[str] = None,
        is_active: bool = True,
        has_media_file: Optional[bool] = None,
        has_unified_resource: Optional[bool] = None,
        keyword: Optional[str] = None,
        excluded_library_ids: Optional[List[str]] = None,
        page: int = 1,
        page_size: int = 100,
        order_by: str = "synced_at",
        order_desc: bool = True,
    ) -> Tuple[List[MediaServerItem], int]:
        """
        获取媒体项列表

        Args:
            db: 数据库会话
            config_id: 媒体服务器配置ID
            media_type: 媒体类型筛选
            item_type: 媒体项类型筛选
            library_id: 媒体库ID筛选
            is_active: 是否仅显示活跃项
            has_media_file: 是否已关联本地文件
            has_unified_resource: 是否已关联统一资源
            keyword: 关键词搜索（标题）
            page: 页码
            page_size: 每页数量
            order_by: 排序字段
            order_desc: 是否降序

        Returns:
            Tuple[List[MediaServerItem], int]: 媒体项列表和总数
        """
        # 构建查询条件
        conditions = []
        if config_id:
            conditions.append(MediaServerItem.media_server_config_id == config_id)
        if media_type:
            conditions.append(MediaServerItem.media_type == media_type)
        if item_type:
            conditions.append(MediaServerItem.item_type == item_type)
        if library_id:
            conditions.append(MediaServerItem.library_id == library_id)
        if is_active is not None:
            conditions.append(MediaServerItem.is_active == is_active)
        if has_media_file is not None:
            if has_media_file:
                conditions.append(MediaServerItem.media_file_id.isnot(None))
            else:
                conditions.append(MediaServerItem.media_file_id.is_(None))
        if has_unified_resource is not None:
            if has_unified_resource:
                conditions.append(MediaServerItem.unified_resource_id.isnot(None))
            else:
                conditions.append(MediaServerItem.unified_resource_id.is_(None))
        if excluded_library_ids:
            conditions.append(
                or_(
                    MediaServerItem.library_id == None,
                    MediaServerItem.library_id.not_in(excluded_library_ids)
                )
            )
        if keyword:
            conditions.append(
                or_(
                    MediaServerItem.name.ilike(f"%{keyword}%"),
                    MediaServerItem.original_name.ilike(f"%{keyword}%"),
                )
            )

        # 查询总数
        count_query = select(func.count(MediaServerItem.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0

        # 查询列表
        query = select(MediaServerItem)
        if conditions:
            query = query.where(and_(*conditions))

        # 排序
        order_column = getattr(MediaServerItem, order_by, MediaServerItem.synced_at)
        if order_desc:
            query = query.order_by(desc(order_column))
        else:
            query = query.order_by(order_column)

        # 分页
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        items = list(result.scalars().all())

        return items, total

    @staticmethod
    async def create_or_update(
        db: AsyncSession, config_id: int, server_item_id: str, item_data: Dict[str, Any]
    ) -> Tuple[MediaServerItem, bool]:
        """
        创建或更新媒体项

        Args:
            db: 数据库会话
            config_id: 媒体服务器配置ID
            server_item_id: 服务器端媒体项ID
            item_data: 媒体项数据

        Returns:
            Tuple[MediaServerItem, bool]: (媒体项对象, 是否新建)
        """
        # 查找是否已存在
        existing = await MediaServerItemService.get_by_server_item_id(db, config_id, server_item_id)

        current_time = now()
        item_data["synced_at"] = current_time
        item_data["is_active"] = True

        if existing:
            # 更新
            for key, value in item_data.items():
                setattr(existing, key, value)
            await db.commit()
            await db.refresh(existing)
            return existing, False
        else:
            # 创建
            item_data["media_server_config_id"] = config_id
            item_data["server_item_id"] = server_item_id
            new_item = MediaServerItem(**item_data)
            db.add(new_item)
            await db.commit()
            await db.refresh(new_item)
            return new_item, True

    @staticmethod
    async def batch_create_or_update(
        db: AsyncSession, config_id: int, items_data: List[Dict[str, Any]]
    ) -> Tuple[int, int]:
        """
        批量创建或更新媒体项

        Args:
            db: 数据库会话
            config_id: 媒体服务器配置ID
            items_data: 媒体项数据列表，每项必须包含 server_item_id

        Returns:
            Tuple[int, int]: (新建数量, 更新数量)
        """
        new_count = 0
        updated_count = 0

        for item_data in items_data:
            server_item_id = item_data.get("server_item_id")
            if not server_item_id:
                logger.warning("Item data missing server_item_id, skipping")
                continue

            _, is_new = await MediaServerItemService.create_or_update(db, config_id, server_item_id, item_data)
            if is_new:
                new_count += 1
            else:
                updated_count += 1

        return new_count, updated_count

    @staticmethod
    async def deactivate_stale_items(
        db: AsyncSession, config_id: int, active_server_item_ids: List[str]
    ) -> int:
        """
        将不在活跃列表中的媒体项标记为非活跃

        Args:
            db: 数据库会话
            config_id: 媒体服务器配置ID
            active_server_item_ids: 活跃的服务器端媒体项ID列表

        Returns:
            int: 被标记为非活跃的数量
        """
        from sqlalchemy import update

        query = (
            update(MediaServerItem)
            .where(
                and_(
                    MediaServerItem.media_server_config_id == config_id,
                    MediaServerItem.is_active == True,
                    MediaServerItem.server_item_id.notin_(active_server_item_ids),
                )
            )
            .values(is_active=False)
        )

        result = await db.execute(query)
        await db.commit()
        deactivated_count = result.rowcount

        if deactivated_count > 0:
            logger.info(f"Deactivated {deactivated_count} stale media server items for config {config_id}")

        return deactivated_count

    @staticmethod
    async def match_media_file_by_path(
        db: AsyncSession, item: MediaServerItem, path_mappings: Optional[List[Dict[str, str]]] = None
    ) -> Optional[MediaFile]:
        """
        根据文件路径匹配本地媒体文件

        Args:
            db: 数据库会话
            item: 媒体服务器媒体项
            path_mappings: 路径映射列表 [{"server_path": "/media/movies", "local_path": "./data/media/Movies"}]

        Returns:
            MediaFile: 匹配的媒体文件，未找到则返回None
        """
        if not item.file_path:
            return None

        # 转换路径（如果有映射配置）
        local_path = item.file_path
        if path_mappings:
            for mapping in path_mappings:
                server_path = mapping.get("server_path", "")
                mapped_local_path = mapping.get("local_path", "")
                if server_path and local_path.startswith(server_path):
                    local_path = local_path.replace(server_path, mapped_local_path, 1)
                    break

        # 标准化路径（处理路径分隔符差异）
        local_path = local_path.replace("\\", "/")

        # 查找匹配的媒体文件
        result = await db.execute(
            select(MediaFile).where(
                or_(
                    MediaFile.file_path == local_path,
                    MediaFile.file_path == item.file_path,
                    MediaFile.file_path.like(f"%{local_path.split('/')[-1]}"),  # 尝试文件名匹配
                )
            )
        )
        media_file = result.scalar_one_or_none()

        if media_file:
            logger.debug(f"Matched media file {media_file.id} for server item {item.id}")

        return media_file

    @staticmethod
    async def update_associations(
        db: AsyncSession, item: MediaServerItem, media_file: Optional[MediaFile] = None
    ) -> MediaServerItem:
        """
        更新媒体项的关联关系

        Args:
            db: 数据库会话
            item: 媒体服务器媒体项
            media_file: 本地媒体文件（可选）

        Returns:
            MediaServerItem: 更新后的媒体项
        """
        if media_file:
            item.media_file_id = media_file.id
            item.unified_table_name = media_file.unified_table_name
            item.unified_resource_id = media_file.unified_resource_id

        await db.commit()
        await db.refresh(item)
        return item

    @staticmethod
    async def delete(db: AsyncSession, item_id: int) -> bool:
        """
        删除媒体项

        Args:
            db: 数据库会话
            item_id: 媒体项ID

        Returns:
            bool: 是否删除成功
        """
        item = await MediaServerItemService.get_by_id(db, item_id)
        if not item:
            return False

        await db.delete(item)
        await db.commit()
        logger.info(f"Deleted media server item {item_id}")
        return True

    @staticmethod
    async def get_statistics(db: AsyncSession, config_id: int) -> Dict[str, Any]:
        """
        获取媒体项统计信息

        Args:
            db: 数据库会话
            config_id: 媒体服务器配置ID

        Returns:
            Dict[str, Any]: 统计信息
        """
        # 总数
        total_result = await db.execute(
            select(func.count(MediaServerItem.id)).where(
                and_(
                    MediaServerItem.media_server_config_id == config_id,
                    MediaServerItem.is_active == True,
                )
            )
        )
        total_count = total_result.scalar() or 0

        # 按媒体类型统计
        type_result = await db.execute(
            select(MediaServerItem.media_type, func.count(MediaServerItem.id))
            .where(
                and_(
                    MediaServerItem.media_server_config_id == config_id,
                    MediaServerItem.is_active == True,
                )
            )
            .group_by(MediaServerItem.media_type)
        )
        by_type = {row[0]: row[1] for row in type_result}

        # 已关联本地文件数量
        matched_file_result = await db.execute(
            select(func.count(MediaServerItem.id)).where(
                and_(
                    MediaServerItem.media_server_config_id == config_id,
                    MediaServerItem.is_active == True,
                    MediaServerItem.media_file_id.isnot(None),
                )
            )
        )
        matched_file_count = matched_file_result.scalar() or 0

        # 已关联统一资源数量
        matched_unified_result = await db.execute(
            select(func.count(MediaServerItem.id)).where(
                and_(
                    MediaServerItem.media_server_config_id == config_id,
                    MediaServerItem.is_active == True,
                    MediaServerItem.unified_resource_id.isnot(None),
                )
            )
        )
        matched_unified_count = matched_unified_result.scalar() or 0

        return {
            "total_count": total_count,
            "by_type": by_type,
            "matched_file_count": matched_file_count,
            "matched_unified_count": matched_unified_count,
        }
