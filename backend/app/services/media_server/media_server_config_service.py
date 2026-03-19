# -*- coding: utf-8 -*-
"""
媒体服务器配置服务
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.media_server_config import MediaServerConfig
from app.adapters.media_servers import get_media_server_adapter, BaseMediaServerAdapter
from app.constants.media_server import (
    MEDIA_SERVER_TYPE_JELLYFIN,
    MEDIA_SERVER_TYPE_EMBY,
    MEDIA_SERVER_TYPE_PLEX,
    MEDIA_SERVER_STATUS_ONLINE,
    MEDIA_SERVER_STATUS_OFFLINE,
    MEDIA_SERVER_STATUS_ERROR,
)
from app.utils.encryption import encryption_util
from app.utils.timezone import now

logger = logging.getLogger(__name__)


class MediaServerConfigService:
    """媒体服务器配置服务（通用）"""

    @staticmethod
    async def get_by_id(db: AsyncSession, config_id: int) -> Optional[MediaServerConfig]:
        """
        根据ID获取配置

        Args:
            db: 数据库会话
            config_id: 配置ID

        Returns:
            MediaServerConfig: 配置对象，不存在则返回None
        """
        result = await db.execute(select(MediaServerConfig).where(MediaServerConfig.id == config_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_user_id(
        db: AsyncSession, user_id: int, server_type: Optional[str] = None
    ) -> List[MediaServerConfig]:
        """
        获取用户的媒体服务器配置列表

        Args:
            db: 数据库会话
            user_id: 用户ID
            server_type: 服务器类型（可选），用于过滤特定类型

        Returns:
            List[MediaServerConfig]: 配置列表
        """
        query = select(MediaServerConfig).where(MediaServerConfig.user_id == user_id)
        if server_type:
            query = query.where(MediaServerConfig.type == server_type)

        query = query.order_by(MediaServerConfig.is_default.desc(), MediaServerConfig.created_at.desc())
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def create(db: AsyncSession, user_id: int, config_data: Dict[str, Any]) -> MediaServerConfig:
        """
        创建媒体服务器配置

        Args:
            db: 数据库会话
            user_id: 用户ID
            config_data: 配置数据

        Returns:
            MediaServerConfig: 创建的配置对象
        """
        # 加密敏感数据
        if config_data.get("api_key"):
            config_data["api_key"] = encryption_util.encrypt(config_data["api_key"])
        if config_data.get("token"):
            config_data["token"] = encryption_util.encrypt(config_data["token"])
        if config_data.get("password"):
            config_data["password"] = encryption_util.encrypt(config_data["password"])

        # 创建配置
        config = MediaServerConfig(user_id=user_id, **config_data)

        db.add(config)
        await db.commit()
        await db.refresh(config)

        logger.info(f"Created media server config: {config.name} (type={config.type}, id={config.id})")
        return config

    @staticmethod
    async def update(db: AsyncSession, config_id: int, updates: Dict[str, Any]) -> MediaServerConfig:
        """
        更新媒体服务器配置

        Args:
            db: 数据库会话
            config_id: 配置ID
            updates: 更新数据

        Returns:
            MediaServerConfig: 更新后的配置对象
        """
        config = await MediaServerConfigService.get_by_id(db, config_id)
        if not config:
            raise ValueError(f"Media server config not found: {config_id}")

        # 敏感字段列表
        sensitive_fields = ["api_key", "token", "password"]

        # 更新字段
        for key, value in updates.items():
            if not hasattr(config, key):
                continue
            # 敏感字段特殊处理：空字符串表示不修改，跳过更新
            if key in sensitive_fields:
                if not value:
                    # 空值不更新，保留原有数据
                    continue
                # 非空值需要加密
                value = encryption_util.encrypt(value)
            setattr(config, key, value)

        await db.commit()
        await db.refresh(config)

        logger.info(f"Updated media server config: {config.name} (id={config.id})")
        return config

    @staticmethod
    async def delete(db: AsyncSession, config_id: int) -> None:
        """
        删除媒体服务器配置

        Args:
            db: 数据库会话
            config_id: 配置ID
        """
        config = await MediaServerConfigService.get_by_id(db, config_id)
        if not config:
            raise ValueError(f"Media server config not found: {config_id}")

        await db.delete(config)
        await db.commit()

        logger.info(f"Deleted media server config: {config.name} (id={config_id})")

    @staticmethod
    async def test_connection(db: AsyncSession, config_id: int) -> Tuple[bool, str]:
        """
        测试媒体服务器连接

        Args:
            db: 数据库会话
            config_id: 配置ID

        Returns:
            Tuple[bool, str]: (是否成功, 消息)
        """
        config = await MediaServerConfigService.get_by_id(db, config_id)
        if not config:
            return False, "配置不存在"

        try:
            # 获取适配器
            adapter = MediaServerConfigService._get_adapter(config)

            # 测试连接
            success = await adapter.test_connection()

            # 更新状态
            if success:
                config.status = MEDIA_SERVER_STATUS_ONLINE
                config.last_check_at = now()
                config.last_error = None
                message = "连接成功"
            else:
                config.status = MEDIA_SERVER_STATUS_OFFLINE
                config.last_check_at = now()
                config.last_error = "连接失败"
                message = "连接失败"

            await db.commit()
            return success, message

        except Exception as e:
            logger.exception(f"Failed to test media server connection: {str(e)}")
            config.status = MEDIA_SERVER_STATUS_ERROR
            config.last_check_at = now()
            config.last_error = str(e)
            await db.commit()
            return False, f"连接错误: {str(e)}"

    @staticmethod
    def get_adapter(config: MediaServerConfig) -> BaseMediaServerAdapter:
        """
        根据服务器类型获取适配器实例（工厂方法）

        Args:
            config: 媒体服务器配置对象

        Returns:
            BaseMediaServerAdapter: 适配器实例
        """
        return MediaServerConfigService._get_adapter(config)

    @staticmethod
    def _get_adapter(config: MediaServerConfig) -> BaseMediaServerAdapter:
        """
        根据服务器类型获取适配器实例（内部实现）

        Args:
            config: 媒体服务器配置对象

        Returns:
            BaseMediaServerAdapter: 适配器实例
        """
        # 构建适配器配置（解密敏感数据）
        adapter_config = {
            "name": config.name,
            "host": config.host,
            "port": config.port,
            "use_ssl": config.use_ssl,
        }

        # 根据服务器类型添加认证信息
        if config.type == MEDIA_SERVER_TYPE_JELLYFIN or config.type == MEDIA_SERVER_TYPE_EMBY:
            if config.api_key:
                adapter_config["api_key"] = encryption_util.decrypt(config.api_key)
        elif config.type == MEDIA_SERVER_TYPE_PLEX:
            if config.token:
                adapter_config["token"] = encryption_util.decrypt(config.token)

        # 其他配置
        if config.server_config:
            adapter_config.update(config.server_config)

        # 调用工厂方法获取适配器
        return get_media_server_adapter(config.type, adapter_config)

    @staticmethod
    async def get_all_with_auto_refresh_enabled(
        db: AsyncSession, user_id: Optional[int] = None
    ) -> List[MediaServerConfig]:
        """
        获取所有启用自动刷新的配置

        Args:
            db: 数据库会话
            user_id: 用户ID（可选），如果提供则只查询该用户的配置

        Returns:
            List[MediaServerConfig]: 配置列表
        """
        query = select(MediaServerConfig).where(MediaServerConfig.auto_refresh_library == True)

        if user_id:
            query = query.where(MediaServerConfig.user_id == user_id)

        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_all_with_sync_enabled(db: AsyncSession) -> List[MediaServerConfig]:
        """
        获取所有启用观看历史同步的配置

        Args:
            db: 数据库会话

        Returns:
            List[MediaServerConfig]: 配置列表
        """
        query = select(MediaServerConfig).where(MediaServerConfig.sync_watch_history == True)
        result = await db.execute(query)
        return list(result.scalars().all())
