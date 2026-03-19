# -*- coding: utf-8 -*-
"""
资源映射关系服务
"""
import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.resource_mapping import ResourceMapping
from app.schemas.resource_mapping import ResourceMappingCreate

logger = logging.getLogger(__name__)


class ResourceMappingService:
    """资源映射关系服务"""

    @staticmethod
    async def get_by_id(db: AsyncSession, mapping_id: int) -> Optional[ResourceMapping]:
        """根据ID获取映射"""
        result = await db.execute(
            select(ResourceMapping).where(ResourceMapping.id == mapping_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_pt_resource(
        db: AsyncSession, pt_resource_id: int
    ) -> Optional[ResourceMapping]:
        """根据PT资源ID获取映射"""
        result = await db.execute(
            select(ResourceMapping).where(ResourceMapping.pt_resource_id == pt_resource_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_pt_resource_id(
        db: AsyncSession, pt_resource_id: int
    ) -> Optional[ResourceMapping]:
        """根据PT资源ID获取映射（别名方法）"""
        return await ResourceMappingService.get_by_pt_resource(db, pt_resource_id)

    @staticmethod
    async def create_mapping(
        db: AsyncSession,
        mapping_data: ResourceMappingCreate,
    ) -> ResourceMapping:
        """
        创建映射关系

        Args:
            db: 数据库会话
            mapping_data: 映射数据

        Returns:
            ResourceMapping: 创建的映射对象

        Raises:
            ValueError: PT资源已映射
        """
        # 检查是否已存在映射
        existing = await ResourceMappingService.get_by_pt_resource(
            db, mapping_data.pt_resource_id
        )
        if existing:
            raise ValueError(
                f"PT资源 {mapping_data.pt_resource_id} 已映射，请先删除旧映射"
            )

        # 创建映射
        mapping = ResourceMapping(**mapping_data.model_dump())
        db.add(mapping)
        await db.commit()
        await db.refresh(mapping)

        logger.info(
            f"Created mapping: pt_resource_id={mapping.pt_resource_id}, "
            f"media_type={mapping.media_type}, "
            f"table={mapping.unified_table_name}, "
            f"resource_id={mapping.unified_resource_id}"
        )

        return mapping

    @staticmethod
    async def delete_mapping(db: AsyncSession, mapping_id: int) -> bool:
        """
        删除映射关系

        Args:
            db: 数据库会话
            mapping_id: 映射ID

        Returns:
            bool: 是否删除成功
        """
        mapping = await ResourceMappingService.get_by_id(db, mapping_id)
        if not mapping:
            return False

        await db.delete(mapping)
        await db.commit()

        logger.info(f"Deleted mapping: id={mapping_id}")
        return True

    @staticmethod
    async def delete_by_pt_resource(db: AsyncSession, pt_resource_id: int) -> bool:
        """
        删除PT资源的映射关系

        Args:
            db: 数据库会话
            pt_resource_id: PT资源ID

        Returns:
            bool: 是否删除成功
        """
        mapping = await ResourceMappingService.get_by_pt_resource(db, pt_resource_id)
        if not mapping:
            return False

        await db.delete(mapping)
        await db.commit()

        logger.info(f"Deleted mapping by pt_resource_id={pt_resource_id}")
        return True
