# -*- coding: utf-8 -*-
"""
PT资源详情服务
"""
import logging
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.pt_resource import PTResource
from app.models.pt_resource_detail import PTResourceDetail
from app.utils.timezone import now

logger = logging.getLogger(__name__)


class PTResourceDetailService:
    """PT资源详情服务"""

    @staticmethod
    async def get_by_pt_resource_id(
        db: AsyncSession,
        pt_resource_id: int
    ) -> Optional[PTResourceDetail]:
        """根据PT资源ID获取详情"""
        result = await db.execute(
            select(PTResourceDetail).where(
                PTResourceDetail.pt_resource_id == pt_resource_id
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def fetch_and_save_detail(
        db: AsyncSession,
        pt_resource_id: int,
        mteam_adapter: Any = None,
    ) -> PTResourceDetail:
        """
        从 MTeam API 获取详情并保存到数据库

        Args:
            db: 数据库会话
            pt_resource_id: PT资源ID
            mteam_adapter: MTeam适配器实例（可选）

        Returns:
            PTResourceDetail: 详情对象
        """
        # 1. 检查是否已有详情
        existing_detail = await PTResourceDetailService.get_by_pt_resource_id(db, pt_resource_id)
        if existing_detail and existing_detail.detail_loaded:
            logger.info(f"Detail already loaded for pt_resource_id: {pt_resource_id}")
            return existing_detail

        # 2. 获取 PT 资源
        pt_resource = await db.get(PTResource, pt_resource_id)
        if not pt_resource:
            raise ValueError(f"PT resource not found: {pt_resource_id}")

        # 3. 调用 MTeam 详情 API
        if not mteam_adapter:
            # 如果没有传入适配器，创建临时适配器
            from app.adapters.pt_sites import get_adapter
            from app.services.pt.pt_site_service import PTSiteService
            from app.utils.encryption import encryption_util

            site = await PTSiteService.get_by_id(db, pt_resource.site_id)
            config = {
                "domain": site.domain,
                "auth_passkey": encryption_util.decrypt(site.auth_passkey),
                "proxy_config": site.proxy_config,
            }
            mteam_adapter = get_adapter("mteam", config)

        # 调用详情 API（获取原始数据）
        detail_data = await mteam_adapter.get_resource_detail(pt_resource.torrent_id)

        # 检查返回数据
        if not detail_data:
            raise ValueError(f"Failed to fetch detail from MTeam API for torrent_id: {pt_resource.torrent_id}")

        # 4. 提取原始数据（包含 dmmInfo）
        raw_detail_data = detail_data.get("raw_detail_json", detail_data)

        # 5. 解析并保存到数据库
        detail = await PTResourceDetailService._parse_and_save(
            db, pt_resource_id, raw_detail_data
        )

        return detail

    @staticmethod
    async def _parse_and_save(
        db: AsyncSession,
        pt_resource_id: int,
        detail_data: Dict[str, Any],
    ) -> PTResourceDetail:
        """解析详情数据并保存"""
        # 提取 DMM 信息（确保不为 None）
        dmm_info = detail_data.get("dmmInfo") or {}
        status = detail_data.get("status") or {}

        # 类型转换辅助函数：安全地将值转换为整数
        def safe_int(value, default=None):
            """将值转换为整数，如果失败返回默认值"""
            if value is None:
                return default
            try:
                return int(value)
            except (ValueError, TypeError):
                return default

        # 查找或创建
        detail = await PTResourceDetailService.get_by_pt_resource_id(db, pt_resource_id)
        if detail:
            # 更新现有记录
            detail.description = detail_data.get("descr")
            detail.mediainfo = detail_data.get("mediainfo")
            detail.nfo = detail_data.get("nfo")
            detail.dmm_product_number = dmm_info.get("productNumber")
            detail.dmm_director = dmm_info.get("director")
            detail.dmm_series = dmm_info.get("series")
            detail.dmm_maker = dmm_info.get("maker")
            detail.dmm_label = dmm_info.get("label")
            detail.dmm_actress_list = dmm_info.get("actressList")
            detail.dmm_keyword_list = dmm_info.get("keywordList")
            detail.origin_file_name = detail_data.get("originFileName")
            detail.thank_count = safe_int(status.get("support"))
            detail.comment_count = safe_int(status.get("comments"))
            detail.view_count = safe_int(status.get("views"))
            detail.hit_count = safe_int(status.get("hits"))
            detail.detail_loaded = True
            detail.detail_loaded_at = now()
        else:
            # 创建新记录
            detail = PTResourceDetail(
                pt_resource_id=pt_resource_id,
                description=detail_data.get("descr"),
                mediainfo=detail_data.get("mediainfo"),
                nfo=detail_data.get("nfo"),
                dmm_product_number=dmm_info.get("productNumber"),
                dmm_director=dmm_info.get("director"),
                dmm_series=dmm_info.get("series"),
                dmm_maker=dmm_info.get("maker"),
                dmm_label=dmm_info.get("label"),
                dmm_actress_list=dmm_info.get("actressList"),
                dmm_keyword_list=dmm_info.get("keywordList"),
                origin_file_name=detail_data.get("originFileName"),
                thank_count=safe_int(status.get("support")),
                comment_count=safe_int(status.get("comments")),
                view_count=safe_int(status.get("views")),
                hit_count=safe_int(status.get("hits")),
                detail_loaded=True,
                detail_loaded_at=now(),
            )
            db.add(detail)

        await db.commit()
        await db.refresh(detail)

        logger.info(f"Saved detail for pt_resource_id: {pt_resource_id}")
        return detail
