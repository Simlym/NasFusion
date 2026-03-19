# -*- coding: utf-8 -*-
"""
下载器配置服务
"""
import logging
from datetime import datetime
from app.utils.timezone import now
from typing import Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.downloaders import (
    QBittorrentAdapter,
    SynologyDownloadStationAdapter,
    TransmissionAdapter,
)
from app.constants import (
    DOWNLOADER_STATUS_ERROR,
    DOWNLOADER_STATUS_OFFLINE,
    DOWNLOADER_STATUS_ONLINE,
    DOWNLOADER_TYPE_QBITTORRENT,
    DOWNLOADER_TYPE_SYNOLOGY_DS,
    DOWNLOADER_TYPE_TRANSMISSION,
)
from app.models.downloader_config import DownloaderConfig
from app.schemas.downloader import DownloaderConfigCreate, DownloaderConfigUpdate
from app.utils.encryption import encryption_util

logger = logging.getLogger(__name__)


class DownloaderConfigService:
    """下载器配置服务"""

    @staticmethod
    def _get_downloader_adapter(config: DownloaderConfig):
        """
        根据配置获取下载器适配器实例

        Args:
            config: 下载器配置

        Returns:
            下载器适配器实例
        """
        # 解密敏感信息
        adapter_config = {
            "host": config.host,
            "port": config.port,
            "username": encryption_util.decrypt(config.username) if config.username else "",
            "password": encryption_util.decrypt(config.password) if config.password else "",
            "use_ssl": config.use_ssl,
        }

        # 根据类型创建适配器
        if config.type == DOWNLOADER_TYPE_QBITTORRENT:
            return QBittorrentAdapter(adapter_config)
        elif config.type == DOWNLOADER_TYPE_TRANSMISSION:
            return TransmissionAdapter(adapter_config)
        elif config.type == DOWNLOADER_TYPE_SYNOLOGY_DS:
            return SynologyDownloadStationAdapter(adapter_config)
        else:
            raise ValueError(f"Unsupported downloader type: {config.type}")

    @staticmethod
    async def create(db: AsyncSession, data: DownloaderConfigCreate) -> DownloaderConfig:
        """
        创建下载器配置

        Args:
            db: 数据库会话
            data: 下载器配置数据

        Returns:
            创建的下载器配置
        """
        try:
            # 检查名称是否重复
            result = await db.execute(
                select(DownloaderConfig).where(DownloaderConfig.name == data.name)
            )
            existing = result.scalar_one_or_none()
            if existing:
                raise ValueError(f"下载器名称 '{data.name}' 已存在")

            # 如果设置为默认，取消其他下载器的默认状态
            if data.is_default:
                await db.execute(
                    select(DownloaderConfig).where(DownloaderConfig.is_default == True)
                )
                result = await db.execute(
                    select(DownloaderConfig).where(DownloaderConfig.is_default == True)
                )
                for downloader in result.scalars():
                    downloader.is_default = False

            # 加密敏感信息
            config = DownloaderConfig(
                name=data.name,
                type=data.type,
                is_default=data.is_default,
                is_enabled=data.is_enabled,
                host=data.host,
                port=data.port,
                username=encryption_util.encrypt(data.username) if data.username else None,
                password=encryption_util.encrypt(data.password) if data.password else None,
                use_ssl=data.use_ssl,
                category_paths=data.category_paths,
                hr_strategy=data.hr_strategy,
                max_concurrent_downloads=data.max_concurrent_downloads,
                download_speed_limit=data.download_speed_limit,
                upload_speed_limit=data.upload_speed_limit,
                status=DOWNLOADER_STATUS_OFFLINE,
            )

            db.add(config)
            await db.commit()
            await db.refresh(config)

            logger.info(f"Created downloader config: {config.name} (ID: {config.id})")
            return config

        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating downloader config: {str(e)}")
            raise

    @staticmethod
    async def get_by_id(db: AsyncSession, config_id: int) -> Optional[DownloaderConfig]:
        """
        根据ID获取下载器配置

        Args:
            db: 数据库会话
            config_id: 配置ID

        Returns:
            下载器配置
        """
        result = await db.execute(
            select(DownloaderConfig).where(DownloaderConfig.id == config_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_default(db: AsyncSession) -> Optional[DownloaderConfig]:
        """
        获取默认下载器配置

        Args:
            db: 数据库会话

        Returns:
            默认下载器配置
        """
        result = await db.execute(
            select(DownloaderConfig).where(
                DownloaderConfig.is_default == True,
                DownloaderConfig.is_enabled == True,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        is_enabled: Optional[bool] = None,
        type: Optional[str] = None,
    ) -> Dict[str, any]:
        """
        获取下载器配置列表

        Args:
            db: 数据库会话
            skip: 跳过数量
            limit: 限制数量
            is_enabled: 是否启用过滤
            type: 类型过滤

        Returns:
            包含总数和列表的字典
        """
        # 构建查询
        query = select(DownloaderConfig)

        if is_enabled is not None:
            query = query.where(DownloaderConfig.is_enabled == is_enabled)
        if type:
            query = query.where(DownloaderConfig.type == type)

        # 获取总数
        count_query = select(func.count()).select_from(query.subquery())
        total = await db.scalar(count_query)

        # 获取列表
        query = query.offset(skip).limit(limit).order_by(DownloaderConfig.created_at.desc())
        result = await db.execute(query)
        items = result.scalars().all()

        return {"total": total or 0, "items": items}

    @staticmethod
    async def update(
        db: AsyncSession,
        config_id: int,
        data: DownloaderConfigUpdate,
    ) -> Optional[DownloaderConfig]:
        """
        更新下载器配置

        Args:
            db: 数据库会话
            config_id: 配置ID
            data: 更新数据

        Returns:
            更新后的配置
        """
        try:
            config = await DownloaderConfigService.get_by_id(db, config_id)
            if not config:
                return None

            # 检查名称是否重复
            if data.name and data.name != config.name:
                result = await db.execute(
                    select(DownloaderConfig).where(
                        DownloaderConfig.name == data.name,
                        DownloaderConfig.id != config_id,
                    )
                )
                if result.scalar_one_or_none():
                    raise ValueError(f"下载器名称 '{data.name}' 已存在")

            # 如果设置为默认，取消其他下载器的默认状态
            if data.is_default:
                result = await db.execute(
                    select(DownloaderConfig).where(
                        DownloaderConfig.is_default == True,
                        DownloaderConfig.id != config_id,
                    )
                )
                for downloader in result.scalars():
                    downloader.is_default = False

            # 敏感字段列表
            sensitive_fields = ["username", "password"]

            # 更新字段
            update_data = data.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                # 敏感字段特殊处理：空字符串表示不修改，跳过更新
                if field in sensitive_fields:
                    if not value:
                        # 空值不更新，保留原有数据
                        continue
                    # 非空值需要加密
                    value = encryption_util.encrypt(value)
                setattr(config, field, value)

            await db.commit()
            await db.refresh(config)

            logger.info(f"Updated downloader config: {config.name} (ID: {config.id})")
            return config

        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating downloader config: {str(e)}")
            raise

    @staticmethod
    async def delete(db: AsyncSession, config_id: int) -> bool:
        """
        删除下载器配置

        Args:
            db: 数据库会话
            config_id: 配置ID

        Returns:
            是否成功
        """
        try:
            config = await DownloaderConfigService.get_by_id(db, config_id)
            if not config:
                return False

            # TODO: 检查是否有正在使用的下载任务

            await db.delete(config)
            await db.commit()

            logger.info(f"Deleted downloader config: {config.name} (ID: {config.id})")
            return True

        except Exception as e:
            await db.rollback()
            logger.error(f"Error deleting downloader config: {str(e)}")
            raise

    @staticmethod
    async def test_connection(db: AsyncSession, config_id: int) -> Dict[str, any]:
        """
        测试下载器连接

        Args:
            db: 数据库会话
            config_id: 配置ID

        Returns:
            测试结果字典
        """
        try:
            config = await DownloaderConfigService.get_by_id(db, config_id)
            if not config:
                return {"success": False, "message": "配置不存在"}

            # 获取适配器
            adapter = DownloaderConfigService._get_downloader_adapter(config)

            # 测试连接
            success = await adapter.test_connection()

            # 更新状态
            config.status = DOWNLOADER_STATUS_ONLINE if success else DOWNLOADER_STATUS_ERROR
            config.last_check_at = now()
            if not success:
                config.last_error = "连接测试失败"

            await db.commit()

            # 清理连接
            await adapter.close()

            return {
                "success": success,
                "message": "连接成功" if success else "连接失败",
            }

        except Exception as e:
            logger.error(f"Error testing downloader connection: {str(e)}")
            # 更新状态
            if config:
                config.status = DOWNLOADER_STATUS_ERROR
                config.last_check_at = now()
                config.last_error = str(e)
                await db.commit()

            return {
                "success": False,
                "message": f"连接测试失败: {str(e)}",
            }

