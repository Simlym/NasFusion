# -*- coding: utf-8 -*-
"""
统一成人资源模型

用于存储从DMM等元数据源获取的成人内容信息
支持无外部元数据时使用PT资源信息作为简化替代
"""
from sqlalchemy import Boolean, Column, Date, Integer, String, Text, DECIMAL, BigInteger, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.base import BaseModel
from app.core.json_types import JSON, TZDateTime


class UnifiedAdult(BaseModel):
    """统一成人资源表"""

    __tablename__ = "unified_adult"

    # ============ 核心标识 ============
    # DMM产品番号是主要标识
    product_number = Column(String(100), nullable=True, unique=True, index=True, comment="产品番号(如: nsps485)")
    dmm_url = Column(Text, nullable=True, comment="DMM页面URL")

    # ============ 标题 ============
    title = Column(String(1000), nullable=False, comment="标题")
    original_title = Column(String(1000), nullable=True, comment="原始标题（日文）")

    # ============ 基础信息 ============
    release_date = Column(Date, nullable=True, index=True, comment="发行日期")
    duration = Column(String(50), nullable=True, comment="时长")
    year = Column(Integer, nullable=True, index=True, comment="年份")

    # ============ 制作信息 ============
    maker = Column(String(200), nullable=True, comment="制作商")
    label = Column(String(200), nullable=True, comment="发行商/厂牌")
    series = Column(String(500), nullable=True, comment="系列")
    director = Column(String(200), nullable=True, comment="导演")

    # ============ 人员 ============
    # 演员列表（JSON数组）
    actresses = Column(JSON, nullable=True, comment="演员列表，JSON数组")

    # ============ 分类/标签 ============
    genres = Column(JSON, nullable=True, comment="类型/关键词 JSON数组")
    tags = Column(JSON, nullable=True, comment="标签 JSON数组")

    # ============ 内容描述 ============
    overview = Column(Text, nullable=True, comment="简介/描述")

    # ============ 评分 ============
    rating = Column(DECIMAL(3, 1), nullable=True, comment="评分")

    # ============ 图片 ============
    poster_url = Column(Text, nullable=True, comment="封面URL（主图）")
    backdrop_url = Column(Text, nullable=True, comment="背景图URL")
    # 多图存储（DMM通常有多张预览图）
    image_list = Column(JSON, nullable=True, comment="预览图列表，JSON数组")

    # ============ PT资源统计 ============
    pt_resource_count = Column(Integer, default=0, nullable=False, comment="关联的PT资源数量")
    has_free_resource = Column(Boolean, default=False, nullable=False, index=True, comment="是否有Free资源")
    best_quality = Column(String(20), nullable=True, comment="最佳质量：4K/1080P等")
    best_seeder_count = Column(Integer, default=0, nullable=False, comment="最高做种数")
    last_resource_updated_at = Column(TZDateTime(), nullable=True, comment="PT资源最后更新时间")

    # ============ 本地文件 ============
    local_file_count = Column(Integer, default=0, nullable=False, comment="本地文件数量")
    has_local = Column(Boolean, default=False, nullable=False, comment="是否有本地文件")
    local_images_dir = Column(String(500), nullable=True, comment="本地图片目录")

    # ============ 元数据管理 ============
    detail_loaded = Column(Boolean, default=False, nullable=False, comment="详情是否已加载（DMM数据）")
    detail_loaded_at = Column(TZDateTime(), nullable=True, comment="详情加载时间")
    metadata_source = Column(String(20), nullable=True, comment="元数据来源：dmm/pt_resource")

    # ============ 原始数据 ============
    raw_dmm_data = Column(JSON, nullable=True, comment="DMM原始数据JSON")

    def __repr__(self):
        return f"<UnifiedAdult(id={self.id}, title={self.title[:30] if self.title else 'N/A'}, product_number={self.product_number})>"

    @property
    def is_simplified(self) -> bool:
        """是否为简化模式（无DMM元数据）"""
        return self.metadata_source == "pt_resource"

    async def update_statistics(self, db: AsyncSession):
        """
        更新PT资源统计信息

        Args:
            db: 数据库会话
        """
        from app.models.resource_mapping import ResourceMapping
        from app.models.pt_resource import PTResource

        # 统计关联的PT资源数量
        count_query = select(func.count()).select_from(ResourceMapping).where(
            ResourceMapping.unified_table_name == "unified_adult",
            ResourceMapping.unified_resource_id == self.id
        )
        count_result = await db.execute(count_query)
        self.pt_resource_count = count_result.scalar_one()

        # 查询关联的PT资源，更新统计字段
        mappings_query = (
            select(PTResource)
            .join(ResourceMapping, ResourceMapping.pt_resource_id == PTResource.id)
            .where(
                ResourceMapping.unified_table_name == "unified_adult",
                ResourceMapping.unified_resource_id == self.id
            )
        )
        mappings_result = await db.execute(mappings_query)
        pt_resources = mappings_result.scalars().all()

        if pt_resources:
            # 是否有免费资源
            self.has_free_resource = any(r.is_free for r in pt_resources)

            # 最佳质量（优先级：2160p > 1080p > 720p）
            quality_priority = {"2160p": 4, "1080p": 3, "720p": 2, "480p": 1}
            best_quality_resource = max(
                pt_resources,
                key=lambda r: quality_priority.get(r.resolution, 0),
                default=None
            )
            self.best_quality = best_quality_resource.resolution if best_quality_resource else None

            # 最高做种数
            self.best_seeder_count = max((r.seeders for r in pt_resources), default=0)

            # 最后更新时间
            from app.utils.timezone import ensure_timezone
            latest_resource = max(
                pt_resources,
                key=lambda r: ensure_timezone(r.updated_at or r.created_at),
                default=None
            )
            if latest_resource:
                self.last_resource_updated_at = latest_resource.updated_at or latest_resource.created_at

        await db.commit()
