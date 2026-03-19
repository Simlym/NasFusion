# -*- coding: utf-8 -*-
"""
成人资源识别服务

支持两种模式：
1. DMM模式：从PT资源标题提取番号，通过MTeam DMM API获取元数据
2. 简化模式：直接使用PT资源信息（标题、图片等）
"""
import logging
import re
from typing import Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.pt_resource import PTResource
from app.models.unified_adult import UnifiedAdult
from app.models.resource_mapping import ResourceMapping
from app.constants import MEDIA_TYPE_ADULT, UNIFIED_TABLE_ADULT
from app.utils.timezone import now

logger = logging.getLogger(__name__)


class AdultIdentifyService:
    """成人资源识别服务"""

    @staticmethod
    def extract_product_number(title: str, subtitle: str = "") -> Optional[str]:
        """
        从PT资源标题中提取产品番号

        Args:
            title: 资源标题
            subtitle: 资源副标题

        Returns:
            产品番号（小写），如果未找到返回None
        """
        # 合并标题和副标题
        full_text = f"{title} {subtitle}".upper()

        # 常见番号模式（按优先级排序）
        patterns = [
            # 格式1: ABC-123 或 ABC123 (字母+数字)
            r'\b([A-Z]{2,6})-?(\d{2,5})\b',
            # 格式2: 123ABC-456 (数字+字母+数字)
            r'\b(\d{1,3})([A-Z]{2,6})-?(\d{2,5})\b',
            # 格式3: T28-123 (带数字的前缀)
            r'\b([A-Z]\d{1,2})-?(\d{2,5})\b',
        ]

        for pattern in patterns:
            match = re.search(pattern, full_text)
            if match:
                groups = match.groups()
                if len(groups) == 2:
                    return f"{groups[0].lower()}{groups[1]}"
                elif len(groups) == 3:
                    return f"{groups[0]}{groups[1].lower()}{groups[2]}"

        return None

    @staticmethod
    async def identify_from_dmm(
        db: AsyncSession,
        pt_resource: PTResource,
        mteam_adapter,
    ) -> Optional[UnifiedAdult]:
        """
        通过DMM API识别成人资源

        Args:
            db: 数据库会话
            pt_resource: PT资源对象
            mteam_adapter: MTeam适配器实例

        Returns:
            UnifiedAdult对象，如果识别失败返回None
        """
        # 提取番号
        product_number = AdultIdentifyService.extract_product_number(
            pt_resource.title,
            pt_resource.subtitle or ""
        )

        if not product_number:
            logger.debug(f"无法从标题中提取番号: {pt_resource.title}")
            return None

        # 检查是否已存在
        stmt = select(UnifiedAdult).where(UnifiedAdult.product_number == product_number)
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            logger.info(f"已存在统一成人资源: {product_number}")
            return existing

        # 调用DMM API获取元数据
        try:
            dmm_info = await mteam_adapter.fetch_dmm_info(product_number)
        except Exception as e:
            logger.warning(f"DMM API调用失败: {e}")
            dmm_info = None

        if dmm_info:
            # 创建统一成人资源（DMM模式）
            unified_adult = UnifiedAdult(
                product_number=product_number,
                dmm_url=dmm_info.get("url"),
                title=dmm_info.get("title") or pt_resource.title,
                original_title=dmm_info.get("original_title"),
                release_date=dmm_info.get("release_date"),
                duration=dmm_info.get("duration"),
                year=dmm_info.get("year"),
                maker=dmm_info.get("maker"),
                label=dmm_info.get("label"),
                series=dmm_info.get("series"),
                director=dmm_info.get("director"),
                actresses=dmm_info.get("actresses"),
                genres=dmm_info.get("genres"),
                overview=dmm_info.get("overview"),
                rating=dmm_info.get("rating"),
                poster_url=dmm_info.get("poster_url"),
                backdrop_url=dmm_info.get("backdrop_url"),
                image_list=dmm_info.get("image_list"),
                detail_loaded=True,
                detail_loaded_at=now(),
                metadata_source="dmm",
                raw_dmm_data=dmm_info.get("raw_data"),
            )
            db.add(unified_adult)
            await db.flush()

            logger.info(f"创建统一成人资源(DMM): {product_number} - {unified_adult.title}")
            return unified_adult

        return None

    @staticmethod
    async def identify_simplified(
        db: AsyncSession,
        pt_resource: PTResource,
    ) -> UnifiedAdult:
        """
        简化模式识别成人资源

        当无法通过DMM获取元数据时，直接使用PT资源信息

        Args:
            db: 数据库会话
            pt_resource: PT资源对象

        Returns:
            UnifiedAdult对象
        """
        # 尝试提取番号
        product_number_extracted = AdultIdentifyService.extract_product_number(
            pt_resource.title,
            pt_resource.subtitle or ""
        )
        
        # 构建唯一标识
        # 格式：{extracted_pn}_SIM_{site_id}_{torrent_id} 或 SIM_{site_id}_{torrent_id}
        if pt_resource.site_id and pt_resource.torrent_id:
            suffix = f"SIM_{pt_resource.site_id}_{pt_resource.torrent_id}"
        else:
            import uuid
            suffix = f"SIM_{uuid.uuid4().hex[:8]}"
            
        if product_number_extracted:
            final_product_number = f"{product_number_extracted}_{suffix}"
        else:
            final_product_number = suffix

        # 检查是否已存在 (精确匹配生成的 final_product_number)
        stmt = select(UnifiedAdult).where(UnifiedAdult.product_number == final_product_number)
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            return existing
            
        # 如果有提取出的番号，也可以尝试按番号+SIM模糊匹配查找是否已有类似的记录 (可选，但为了防止重复创建)
        # 暂时只精确匹配 site_id + torrent_id 组合，因为 simplified 模式就是为了特定资源创建的

        # 解析图片列表
        image_list = None
        if pt_resource.image_list:
            if isinstance(pt_resource.image_list, str):
                # 如果是逗号分隔的字符串
                image_list = [url.strip() for url in pt_resource.image_list.split(",") if url.strip()]
            elif isinstance(pt_resource.image_list, list):
                image_list = pt_resource.image_list

        # 获取第一张图片作为封面
        poster_url = None
        if image_list and len(image_list) > 0:
            poster_url = image_list[0]

        # 创建简化模式的统一成人资源
        unified_adult = UnifiedAdult(
            product_number=final_product_number,
            title=pt_resource.title,
            original_title=pt_resource.title,
            overview=pt_resource.subtitle,
            poster_url=poster_url,
            image_list=image_list,
            detail_loaded=False,
            metadata_source="pt_resource",
        )
        db.add(unified_adult)
        await db.flush()

        logger.info(f"创建简化模式统一成人资源: {pt_resource.id} -> {unified_adult.product_number}")
        return unified_adult

    @staticmethod
    async def identify_adult_resource(
        db: AsyncSession,
        pt_resource: PTResource,
        mteam_adapter=None,
        force_simplified: bool = False,
    ) -> Optional[UnifiedAdult]:
        """
        识别成人资源（主入口方法）

        策略：
        1. 如果force_simplified=True，直接使用简化模式
        2. 尝试通过DMM API识别
        3. 如果DMM失败，使用简化模式

        Args:
            db: 数据库会话
            pt_resource: PT资源对象
            mteam_adapter: MTeam适配器实例（可选）
            force_simplified: 是否强制使用简化模式

        Returns:
            UnifiedAdult对象
        """
        # 验证资源类型
        if pt_resource.category != MEDIA_TYPE_ADULT:
            logger.warning(f"资源不是成人类型: {pt_resource.category}")
            return None

        # 强制简化模式
        if force_simplified or mteam_adapter is None:
            return await AdultIdentifyService.identify_simplified(db, pt_resource)

        # 尝试DMM识别
        unified_adult = await AdultIdentifyService.identify_from_dmm(
            db, pt_resource, mteam_adapter
        )

        # 如果DMM失败，使用简化模式
        if not unified_adult:
            unified_adult = await AdultIdentifyService.identify_simplified(db, pt_resource)

        return unified_adult

    @staticmethod
    async def link_to_unified_adult(
        db: AsyncSession,
        pt_resource: PTResource,
        unified_adult: UnifiedAdult,
    ) -> ResourceMapping:
        """
        创建PT资源与统一成人资源的映射关系

        Args:
            db: 数据库会话
            pt_resource: PT资源对象
            unified_adult: 统一成人资源对象

        Returns:
            ResourceMapping对象
        """
        # 检查是否已存在映射
        stmt = select(ResourceMapping).where(
            ResourceMapping.pt_resource_id == pt_resource.id,
            ResourceMapping.unified_table_name == UNIFIED_TABLE_ADULT,
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            logger.debug(f"映射已存在: PT资源 {pt_resource.id} -> UnifiedAdult {unified_adult.id}")
            return existing

        # 创建新映射
        mapping = ResourceMapping(
            pt_resource_id=pt_resource.id,
            unified_table_name=UNIFIED_TABLE_ADULT,
            unified_resource_id=unified_adult.id,
            match_confidence=1.0 if unified_adult.metadata_source == "dmm" else 0.8,
            match_source="dmm" if unified_adult.metadata_source == "dmm" else "simplified",
        )
        db.add(mapping)

        # 更新PT资源识别状态
        pt_resource.identification_status = "identified"

        await db.commit()

        logger.info(f"创建资源映射: PT资源 {pt_resource.id} -> UnifiedAdult {unified_adult.id}")
        return mapping


# 全局单例
adult_identify_service = AdultIdentifyService()
