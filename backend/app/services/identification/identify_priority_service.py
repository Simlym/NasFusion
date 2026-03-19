# -*- coding: utf-8 -*-
"""
识别优先级配置服务
"""
import json
import logging
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.resource_identification import DEFAULT_IDENTIFICATION_PRIORITY
from app.models.system_setting import SystemSetting

logger = logging.getLogger(__name__)

# 配置键
SETTING_CATEGORY = "metadata_scraping"
SETTING_KEY = "identification_priority"


class IdentificationPriorityService:
    """识别优先级配置服务"""

    # 内存缓存
    _cache: Optional[Dict] = None

    @staticmethod
    async def get_priority_config(db: AsyncSession) -> Dict:
        """
        获取识别优先级配置（带缓存）

        Returns:
            Dict: 配置字典，格式：{"enabled_sources": ["local_cache", "mteam_douban", ...]}
        """
        # 1. 先从缓存读取
        if IdentificationPriorityService._cache is not None:
            logger.debug("Using cached identification priority config")
            return IdentificationPriorityService._cache

        # 2. 从数据库读取
        result = await db.execute(
            select(SystemSetting).where(
                SystemSetting.category == SETTING_CATEGORY,
                SystemSetting.key == SETTING_KEY,
            )
        )
        setting = result.scalar_one_or_none()

        config = None
        if setting and setting.value:
            try:
                config = json.loads(setting.value)
                logger.info(f"Loaded identification priority config from database: {config}")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse identification priority config: {e}")

        # 3. 如果数据库没有配置，使用默认配置
        if config is None:
            config = IdentificationPriorityService.get_default_priority()
            logger.info(f"Using default identification priority config: {config}")

        # 4. 更新缓存（关键修复：无论是数据库配置还是默认配置，都要缓存）
        IdentificationPriorityService._cache = config
        return config

    @staticmethod
    def get_default_priority() -> Dict:
        """
        获取默认识别优先级配置

        Returns:
            Dict: 默认配置字典
        """
        return {"enabled_sources": DEFAULT_IDENTIFICATION_PRIORITY}

    @staticmethod
    async def update_priority_config(db: AsyncSession, enabled_sources: List[str]) -> Dict:
        """
        更新识别优先级配置

        Args:
            db: 数据库会话
            enabled_sources: 启用的识别源列表（按优先级排序）

        Returns:
            Dict: 更新后的配置字典
        """
        config = {"enabled_sources": enabled_sources}
        config_json = json.dumps(config, ensure_ascii=False)

        # 1. 查找现有配置
        result = await db.execute(
            select(SystemSetting).where(
                SystemSetting.category == SETTING_CATEGORY,
                SystemSetting.key == SETTING_KEY,
            )
        )
        setting = result.scalar_one_or_none()

        if setting:
            # 更新现有配置
            setting.value = config_json
            logger.info(f"Updated identification priority config: {config}")
        else:
            # 创建新配置
            setting = SystemSetting(
                category=SETTING_CATEGORY,
                key=SETTING_KEY,
                value=config_json,
                description="资源识别优先级配置（启用的识别源及其顺序）",
                is_active=True,
                is_encrypted=False,
            )
            db.add(setting)
            logger.info(f"Created identification priority config: {config}")

        await db.commit()

        # 2. 清除缓存
        IdentificationPriorityService._cache = None
        logger.debug("Cleared identification priority cache")

        return config

    @staticmethod
    def clear_cache():
        """清除内存缓存"""
        IdentificationPriorityService._cache = None
        logger.debug("Cleared identification priority cache")
