# -*- coding: utf-8 -*-
"""
统一电影资源模型
"""
from sqlalchemy import Boolean, Column, Date, Integer, String, Text, DECIMAL, DateTime, BigInteger, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.base import BaseModel
from app.core.json_types import JSON


class UnifiedMovie(BaseModel):
    """统一电影资源表"""

    __tablename__ = "unified_movies"

    # ============ 核心标识 ============
    tmdb_id = Column(Integer, nullable=True, unique=True, index=True, comment="TMDB ID")
    imdb_id = Column(String(20), nullable=True, unique=True, index=True, comment="IMDB ID")
    douban_id = Column(String(20), nullable=True, unique=True, index=True, comment="豆瓣ID")

    # ============ 标题 ============
    title = Column(String(500), nullable=False, comment="主标题（通常中文）")
    original_title = Column(String(500), nullable=True, comment="原始语言标题")
    aka = Column(JSON, nullable=True, comment="别名/译名，JSON数组")

    # ============ 基础信息 ============
    year = Column(Integer, nullable=True, index=True, comment="年份")
    release_date = Column(Date, nullable=True, index=True, comment="上映日期")
    runtime = Column(Integer, nullable=True, comment="时长（分钟）")

    # ============ 评分 ============
    rating_tmdb = Column(DECIMAL(3, 1), nullable=True, comment="TMDB评分")
    votes_tmdb = Column(Integer, nullable=True, comment="TMDB投票数")
    rating_douban = Column(DECIMAL(3, 1), nullable=True, comment="豆瓣评分")
    votes_douban = Column(Integer, nullable=True, comment="豆瓣投票数")
    rating_imdb = Column(DECIMAL(3, 1), nullable=True, comment="IMDB评分")
    votes_imdb = Column(Integer, nullable=True, comment="IMDB投票数")

    # ============ 分类/标签 ============
    genres = Column(JSON, nullable=True, comment="类型 JSON数组")
    tags = Column(JSON, nullable=True, comment="标签 JSON数组")
    languages = Column(JSON, nullable=True, comment="语言 JSON数组")
    countries = Column(JSON, nullable=True, comment="国家 JSON数组")

    # ============ 人员（存储对象数组，含详细信息）============
    directors = Column(JSON, nullable=True, comment="导演，JSON数组")
    actors = Column(JSON, nullable=True, comment="演员，JSON数组（含角色名、头像）")
    writers = Column(JSON, nullable=True, comment="编剧，JSON数组")

    # ============ 内容描述 ============
    overview = Column(Text, nullable=True, comment="简介（优先中文）")
    tagline = Column(String(500), nullable=True, comment="宣传语")

    # ============ 分级/系列 ============
    certification = Column(String(20), nullable=True, comment="分级（PG-13, R等）")
    collection_id = Column(Integer, nullable=True, comment="系列ID")
    collection_name = Column(String(200), nullable=True, comment="系列名")

    # ============ 制作信息 ============
    budget = Column(BigInteger, nullable=True, comment="预算")
    revenue = Column(BigInteger, nullable=True, comment="票房")
    production_companies = Column(JSON, nullable=True, comment="制作公司，JSON数组")
    status = Column(String(20), nullable=True, comment="状态：Released/Post_Production/Rumored")

    # ============ 图片 ============
    poster_url = Column(Text, nullable=True, comment="海报URL")
    backdrop_url = Column(Text, nullable=True, comment="背景图URL")
    logo_url = Column(Text, nullable=True, comment="Logo URL")
    clearart_url = Column(Text, nullable=True, comment="透明艺术图URL")
    banner_url = Column(Text, nullable=True, comment="横幅URL")

    # ============ PT资源统计 ============
    pt_resource_count = Column(Integer, default=0, nullable=False, comment="关联的PT资源数量")
    has_free_resource = Column(Boolean, default=False, nullable=False, index=True, comment="是否有Free资源")
    best_quality = Column(String(20), nullable=True, comment="最佳质量：4K/1080P等")
    best_seeder_count = Column(Integer, default=0, nullable=False, comment="最高做种数")
    last_resource_updated_at = Column(DateTime(timezone=True), nullable=True, comment="PT资源最后更新时间")

    # ============ 本地文件 ============
    local_file_count = Column(Integer, default=0, nullable=False, comment="本地文件数量")
    has_local = Column(Boolean, default=False, nullable=False, comment="是否有本地文件")
    local_images_dir = Column(String(500), nullable=True, comment="本地图片目录")

    # ============ 元数据管理 ============
    detail_loaded = Column(Boolean, default=False, nullable=False, comment="详情是否已加载")
    detail_loaded_at = Column(DateTime(timezone=True), nullable=True, comment="详情加载时间")
    metadata_source = Column(String(20), nullable=True, comment="元数据来源：douban/tmdb")

    def __repr__(self):
        return f"<UnifiedMovie(id={self.id}, title={self.title}, year={self.year})>"

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
            ResourceMapping.unified_table_name == "unified_movies",
            ResourceMapping.unified_resource_id == self.id
        )
        count_result = await db.execute(count_query)
        self.pt_resource_count = count_result.scalar_one()

        # 查询关联的PT资源，更新统计字段
        mappings_query = (
            select(PTResource)
            .join(ResourceMapping, ResourceMapping.pt_resource_id == PTResource.id)
            .where(
                ResourceMapping.unified_table_name == "unified_movies",
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
