"""
PT站点服务层
"""
import asyncio
import logging
from typing import List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import (
    AUTH_TYPE_COOKIE,
    AUTH_TYPE_PASSKEY,
    AUTH_TYPE_USER_PASS,
    SITE_STATUS_ACTIVE,
    SITE_TYPE_MTEAM,
    MTEAM_DEFAULT_CAPABILITIES,
)
from app.models.pt_site import PTSite
from app.schemas.pt_site import PTSiteCreate, PTSiteCreateFromPreset, PTSiteUpdate
from app.constants.site_presets import get_site_preset
from app.utils.encryption import encryption_util
from app.adapters.pt_sites import get_adapter
from app.services.pt.pt_category_service import PTCategoryService
from app.services.pt.pt_metadata_service import PTMetadataService

logger = logging.getLogger(__name__)


class PTSiteService:
    """PT站点服务"""

    @staticmethod
    async def get_by_id(db: AsyncSession, site_id: int) -> Optional[PTSite]:
        """通过ID获取站点"""
        result = await db.execute(select(PTSite).where(PTSite.id == site_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_domain(db: AsyncSession, domain: str) -> Optional[PTSite]:
        """通过域名获取站点"""
        result = await db.execute(select(PTSite).where(PTSite.domain == domain))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_list(
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        sync_enabled: Optional[bool] = None,
    ) -> Tuple[List[PTSite], int]:
        """
        获取站点列表

        Args:
            db: 数据库会话
            page: 页码
            page_size: 每页数量
            status: 状态过滤
            sync_enabled: 同步启用状态过滤

        Returns:
            Tuple[List[PTSite], int]: 站点列表和总数
        """
        # 构建查询
        query = select(PTSite)

        # 添加过滤条件
        if status:
            query = query.where(PTSite.status == status)
        if sync_enabled is not None:
            query = query.where(PTSite.sync_enabled == sync_enabled)

        # 获取总数
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar_one()

        # 分页
        query = query.offset((page - 1) * page_size).limit(page_size)
        query = query.order_by(PTSite.created_at.desc())

        # 执行查询
        result = await db.execute(query)
        sites = result.scalars().all()

        return list(sites), total

    @staticmethod
    async def create_site(db: AsyncSession, site_data: PTSiteCreate) -> PTSite:
        """
        创建站点

        Args:
            db: 数据库会话
            site_data: 站点创建数据

        Returns:
            PTSite: 创建的站点

        Raises:
            ValueError: 域名已存在
        """
        # 检查域名是否存在
        existing = await PTSiteService.get_by_domain(db, site_data.domain)
        if existing:
            raise ValueError(f"域名 '{site_data.domain}' 已存在")

        # 自动设置默认能力（如果未提供）
        capabilities = site_data.capabilities
        if capabilities is None:
            capabilities = PTSiteService._get_default_capabilities(site_data.type)
            logger.info(f"自动设置站点 {site_data.name} 的默认能力: {capabilities}")

        # 加密敏感数据
        site = PTSite(
            name=site_data.name,
            type=site_data.type,
            domain=site_data.domain,
            base_url=site_data.base_url,
            auth_type=site_data.auth_type,
            auth_cookie=encryption_util.encrypt(site_data.auth_cookie)
            if site_data.auth_cookie
            else None,
            auth_passkey=encryption_util.encrypt(site_data.auth_passkey)
            if site_data.auth_passkey
            else None,
            auth_username=encryption_util.encrypt(site_data.auth_username)
            if site_data.auth_username
            else None,
            auth_password=encryption_util.encrypt(site_data.auth_password)
            if site_data.auth_password
            else None,
            cookie_expire_at=site_data.cookie_expire_at,
            proxy_config=site_data.proxy_config,
            capabilities=capabilities,  # 使用处理后的能力
            sync_enabled=site_data.sync_enabled,
            sync_strategy=site_data.sync_strategy,
            sync_interval=site_data.sync_interval,
            sync_config=site_data.sync_config,
            request_interval=site_data.request_interval,
            max_requests_per_day=site_data.max_requests_per_day,
            status=SITE_STATUS_ACTIVE,
        )

        db.add(site)
        await db.commit()
        await db.refresh(site)

        # 异步后台同步元数据（分类 + 其他元数据），不阻塞API响应
        asyncio.create_task(
            PTSiteService._auto_sync_metadata_background(site.id),
            name=f"sync_metadata_site_{site.id}"
        )
        logger.info(f"站点 {site.name} 创建成功，元数据将在后台同步")

        return site

    @staticmethod
    async def create_site_from_preset(db: AsyncSession, site_data: PTSiteCreateFromPreset) -> PTSite:
        """
        从预设配置创建站点

        用户只需提供预设ID和认证信息，其他配置自动从预设加载

        Args:
            db: 数据库会话
            site_data: 从预设创建的站点数据

        Returns:
            PTSite: 创建的站点

        Raises:
            ValueError: 预设不存在或域名已存在
        """
        # 获取预设配置
        preset = get_site_preset(site_data.preset_id)
        if not preset:
            raise ValueError(f"站点预设不存在: {site_data.preset_id}")

        # 使用预设值，允许用户覆盖
        name = site_data.name or preset["display_name"]
        domain = site_data.domain or preset["domain"]
        base_url = site_data.base_url or preset["base_url"]
        site_type = site_data.preset_id  # 站点类型使用preset_id作为适配器标识
        auth_type = preset["auth_type"]

        # 检查域名是否存在
        existing = await PTSiteService.get_by_domain(db, domain)
        if existing:
            raise ValueError(f"域名 '{domain}' 已存在")

        # 验证必填认证信息
        schema = preset.get("schema", "")
        if schema == "nexusphp" and not site_data.auth_cookie:
            raise ValueError("NexusPHP站点必须提供Cookie")

        # 获取默认配置
        default_config = preset.get("default_config", {})
        sync_interval = site_data.sync_interval or default_config.get("sync_interval", 60)
        request_interval = site_data.request_interval or default_config.get("request_interval", 5)
        sync_strategy = default_config.get("sync_strategy", "page_based")
        max_requests_per_day = default_config.get("max_requests_per_day", 200)

        # 获取能力配置
        capabilities = {}
        for cap in preset.get("capabilities", []):
            capabilities[f"supports_{cap}"] = True

        # 加密敏感数据并创建站点
        site = PTSite(
            preset_id=site_data.preset_id,
            name=name,
            type=site_type,
            domain=domain,
            base_url=base_url,
            auth_type=auth_type,
            auth_cookie=encryption_util.encrypt(site_data.auth_cookie) if site_data.auth_cookie else None,
            auth_passkey=encryption_util.encrypt(site_data.auth_passkey) if site_data.auth_passkey else None,
            proxy_config=site_data.proxy_config,
            capabilities=capabilities,
            sync_enabled=site_data.sync_enabled,
            sync_strategy=sync_strategy,
            sync_interval=sync_interval,
            request_interval=request_interval,
            max_requests_per_day=max_requests_per_day,
            status=SITE_STATUS_ACTIVE,
        )

        db.add(site)
        await db.commit()
        await db.refresh(site)

        logger.info(f"站点 {site.name} 从预设 {site_data.preset_id} 创建成功")

        # 异步后台同步元数据
        asyncio.create_task(
            PTSiteService._auto_sync_metadata_background(site.id),
            name=f"sync_metadata_site_{site.id}"
        )

        return site

    @staticmethod
    def _get_default_capabilities(site_type: str) -> dict:
        """
        根据站点类型获取默认能力配置

        Args:
            site_type: 站点类型

        Returns:
            dict: 默认能力配置
        """
        # 根据站点类型返回对应的默认能力
        if site_type == SITE_TYPE_MTEAM:
            return MTEAM_DEFAULT_CAPABILITIES.copy()

        # 未来可扩展其他站点类型的默认能力
        # if site_type == SITE_TYPE_CHDBITS:
        #     return CHDBITS_DEFAULT_CAPABILITIES.copy()

        # 如果没有预定义，返回空字典
        logger.warning(f"站点类型 '{site_type}' 没有预定义的默认能力配置")
        return {}

    @staticmethod
    async def _auto_sync_metadata_background(site_id: int):
        """
        后台异步同步站点元数据（创建站点后调用）

        使用独立的数据库会话，不阻塞API响应

        Args:
            site_id: 站点ID
        """
        from app.core.database import async_session_local

        try:
            async with async_session_local() as db:
                site = await PTSiteService.get_by_id(db, site_id)
                if not site:
                    logger.error(f"后台同步失败：站点 {site_id} 不存在")
                    return

                await PTSiteService._auto_sync_metadata(db, site)
                # 确保所有更改都已提交
                await db.commit()
        except Exception as e:
            logger.error(f"后台同步站点 {site_id} 元数据失败: {str(e)}")

    @staticmethod
    async def _auto_sync_metadata(db: AsyncSession, site: PTSite):
        """
        自动同步站点元数据（创建站点后调用）

        同步顺序：
        1. 同步分类
        2. 同步其他元数据（视频编码、分辨率、来源等）

        Args:
            db: 数据库会话
            site: 站点对象
        """
        try:


            logger.info(f"Auto-syncing metadata for new site: {site.name}")

            # 准备配置
            config = {
                "name": site.name,
                "base_url": site.base_url,
                "domain": site.domain,
                "proxy_config": site.proxy_config,
                "request_interval": site.request_interval or 2,
            }

            # 添加认证信息（需要解密）
            if site.auth_type == AUTH_TYPE_PASSKEY and site.auth_passkey:
                config["auth_passkey"] = encryption_util.decrypt(site.auth_passkey)
            elif site.auth_type == AUTH_TYPE_COOKIE and site.auth_cookie:
                config["auth_cookie"] = encryption_util.decrypt(site.auth_cookie)
            elif site.auth_type == AUTH_TYPE_USER_PASS:
                if site.auth_username:
                    config["auth_username"] = encryption_util.decrypt(site.auth_username)
                if site.auth_password:
                    config["auth_password"] = encryption_util.decrypt(site.auth_password)

            adapter = get_adapter(site.type, config)

            # 1. 同步分类
            if hasattr(adapter, "fetch_categories"):
                try:
                    categories_data = await adapter.fetch_categories()
                    stats = await PTCategoryService.sync_site_categories(
                        db, site, categories_data
                    )
                    logger.info(
                        f"Auto-synced categories for {site.name}: "
                        f"{stats['created']} created, {stats['updated']} updated"
                    )
                except Exception as e:
                    logger.warning(f"Failed to auto-sync categories for {site.name}: {str(e)}")

            # 2. 同步其他元数据
            if hasattr(adapter, "fetch_metadata"):
                try:
                    metadata = await adapter.fetch_metadata()
                    stats = await PTMetadataService.sync_all_metadata(db, site, metadata)
                    logger.info(f"Auto-synced metadata for {site.name}: {stats}")
                except Exception as e:
                    logger.warning(f"Failed to auto-sync metadata for {site.name}: {str(e)}")

            logger.info(f"Completed auto-sync for {site.name}")

            # 发布站点同步完成事件
            # try:
            #     from app.constants.event import EVENT_SITE_SYNC_COMPLETED
            #     from app.events.bus import event_bus

            #     event_data = {
            #         "broadcast": True,  # 广播消息
            #         "site_name": site.name,
            #         "site_id": site.id,
            #         "related_type": "pt_site",
            #         "related_id": site.id,
            #     }

            #     await event_bus.publish(
            #         EVENT_SITE_SYNC_COMPLETED,
            #         event_data
            #     )

            #     logger.debug(f"站点同步完成事件已发布: {site.name}")

            # except Exception as e:
            #     logger.exception(f"发布站点同步事件失败: {e}")

        except Exception as e:
            logger.error(f"Error in auto-sync metadata for {site.name}: {str(e)}")
            # 不抛出异常，因为站点创建已经成功了，元数据同步失败不影响站点创建

    @staticmethod
    async def update_site(
        db: AsyncSession, site_id: int, site_data: PTSiteUpdate
    ) -> Optional[PTSite]:
        """更新站点信息"""
        site = await PTSiteService.get_by_id(db, site_id)
        if not site:
            return None

        # 敏感字段列表
        sensitive_fields = ["auth_cookie", "auth_passkey", "auth_username", "auth_password"]

        # 更新字段
        update_data = site_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            # 敏感字段特殊处理：空字符串表示不修改，跳过更新
            if field in sensitive_fields:
                if not value:
                    # 空值不更新，保留原有数据
                    continue
                # 非空值需要加密
                value = encryption_util.encrypt(value)
            setattr(site, field, value)

        await db.commit()
        await db.refresh(site)

        return site

    @staticmethod
    async def delete_site(db: AsyncSession, site_id: int) -> bool:
        """删除站点"""
        site = await PTSiteService.get_by_id(db, site_id)
        if not site:
            return False

        await db.delete(site)
        await db.commit()

        return True

    @staticmethod
    async def test_connection(
        db: AsyncSession, site_id: int, skip_proxy: bool = False
    ) -> Tuple[bool, str]:
        """
        测试站点连接

        Args:
            db: 数据库会话
            site_id: 站点ID
            skip_proxy: 是否跳过代理直连测试

        Returns:
            Tuple[bool, str]: (是否成功, 消息)
        """
        site = await PTSiteService.get_by_id(db, site_id)
        if not site:
            return False, "站点不存在"

        try:
            # 准备适配器配置
            config = {
                "name": site.name,
                "base_url": site.base_url,
                "domain": site.domain,
                "auth_type": site.auth_type,
                "proxy_config": site.proxy_config if not skip_proxy else None,
                "request_interval": site.request_interval or 2,
            }

            if skip_proxy:
                logger.info(f"[{site.name}] 跳过代理，使用直连模式测试")

            # 解密认证信息
            if site.auth_type == AUTH_TYPE_COOKIE and site.auth_cookie:
                config["auth_cookie"] = encryption_util.decrypt(site.auth_cookie)
            elif site.auth_type == AUTH_TYPE_PASSKEY and site.auth_passkey:
                config["auth_passkey"] = encryption_util.decrypt(site.auth_passkey)
            elif site.auth_type == AUTH_TYPE_USER_PASS:
                if site.auth_username:
                    config["auth_username"] = encryption_util.decrypt(site.auth_username)
                if site.auth_password:
                    config["auth_password"] = encryption_util.decrypt(site.auth_password)

            # 获取适配器并执行健康检查
            adapter = get_adapter(site.type, config)
            is_healthy = await adapter.health_check()

            # 更新健康状态
            from app.utils.timezone import now
            site.health_check_at = now()
            site.health_status = "healthy" if is_healthy else "unhealthy"

            # 如果健康检查成功，更新站点状态为active
            if is_healthy and site.status != SITE_STATUS_ACTIVE:
                site.status = SITE_STATUS_ACTIVE

            await db.commit()
            await db.refresh(site)

            if is_healthy:
                return True, "连接测试成功，站点运行正常"
            else:
                return False, "连接测试失败，站点无响应"

        except Exception as e:
            logger.error(f"测试站点连接失败: {str(e)}")

            # 更新健康状态为不健康
            from app.utils.timezone import now
            site.health_check_at = now()
            site.health_status = "unhealthy"
            await db.commit()

            return False, f"连接测试失败: {str(e)}"

    @staticmethod
    def decrypt_auth_info(site: PTSite) -> dict:
        """
        解密站点认证信息

        Args:
            site: PT站点

        Returns:
            dict: 解密后的认证信息
        """
        return {
            "auth_cookie": encryption_util.decrypt(site.auth_cookie) if site.auth_cookie else None,
            "auth_passkey": encryption_util.decrypt(site.auth_passkey)
            if site.auth_passkey
            else None,
            "auth_username": encryption_util.decrypt(site.auth_username)
            if site.auth_username
            else None,
            "auth_password": encryption_util.decrypt(site.auth_password)
            if site.auth_password
            else None,
        }
