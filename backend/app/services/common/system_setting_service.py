# -*- coding: utf-8 -*-
"""
系统设置服务
"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.system_setting import SystemSetting
from app.schemas.system_setting import SystemSettingCreate, SystemSettingUpdate


class SystemSettingService:
    """系统设置服务"""

    @staticmethod
    async def get_by_key(db: AsyncSession, category: str, key: str) -> Optional[SystemSetting]:
        """
        根据分类和键获取设置

        Args:
            db: 数据库会话
            category: 设置分类
            key: 设置键

        Returns:
            SystemSetting: 设置对象，不存在则返回None
        """
        query = select(SystemSetting).where(
            SystemSetting.category == category,
            SystemSetting.key == key,
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_category(db: AsyncSession, category: str) -> list[SystemSetting]:
        """
        根据分类获取所有设置

        Args:
            db: 数据库会话
            category: 设置分类

        Returns:
            list[SystemSetting]: 设置列表
        """
        query = select(SystemSetting).where(SystemSetting.category == category)
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_all(db: AsyncSession) -> list[SystemSetting]:
        """
        获取所有设置

        Args:
            db: 数据库会话

        Returns:
            list[SystemSetting]: 设置列表
        """
        query = select(SystemSetting)
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def create(db: AsyncSession, setting_data: SystemSettingCreate) -> SystemSetting:
        """
        创建设置

        Args:
            db: 数据库会话
            setting_data: 设置数据

        Returns:
            SystemSetting: 创建的设置对象
        """
        setting = SystemSetting(**setting_data.model_dump())
        db.add(setting)
        await db.commit()
        await db.refresh(setting)
        return setting

    @staticmethod
    async def update(
        db: AsyncSession, category: str, key: str, setting_data: SystemSettingUpdate
    ) -> Optional[SystemSetting]:
        """
        更新设置

        Args:
            db: 数据库会话
            category: 设置分类
            key: 设置键
            setting_data: 更新数据

        Returns:
            SystemSetting: 更新后的设置对象，不存在则返回None
        """
        setting = await SystemSettingService.get_by_key(db, category, key)
        if not setting:
            return None

        for field, value in setting_data.model_dump(exclude_unset=True).items():
            setattr(setting, field, value)

        await db.commit()
        await db.refresh(setting)
        return setting

    @staticmethod
    async def upsert(
        db: AsyncSession, category: str, key: str, value: str, description: str = None
    ) -> SystemSetting:
        """
        创建或更新设置（如果存在则更新，不存在则创建）

        Args:
            db: 数据库会话
            category: 设置分类
            key: 设置键
            value: 设置值
            description: 设置描述

        Returns:
            SystemSetting: 设置对象
        """
        existing = await SystemSettingService.get_by_key(db, category, key)

        if existing:
            # 更新
            existing.value = value
            if description:
                existing.description = description
            await db.commit()
            await db.refresh(existing)
            return existing
        else:
            # 创建
            setting = SystemSetting(
                category=category, key=key, value=value, description=description
            )
            db.add(setting)
            await db.commit()
            await db.refresh(setting)
            return setting

    @staticmethod
    async def delete(db: AsyncSession, category: str, key: str) -> bool:
        """
        删除设置

        Args:
            db: 数据库会话
            category: 设置分类
            key: 设置键

        Returns:
            bool: 是否删除成功
        """
        setting = await SystemSettingService.get_by_key(db, category, key)
        if not setting:
            return False

        await db.delete(setting)
        await db.commit()
        return True
