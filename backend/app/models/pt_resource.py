"""
PT资源相关数据模型
"""
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    DECIMAL,
    UniqueConstraint,
)

from app.core.db_types import JSON, TZDateTime
from sqlalchemy.orm import relationship, backref

from app.models.base import BaseModel


class PTResource(BaseModel):
    """PT原始资源表"""

    __tablename__ = "pt_resources"
    __table_args__ = (
        UniqueConstraint("site_id", "torrent_id", name="uq_pt_resources_site_torrent"),
    )

    # 站点关联
    site_id = Column(
        Integer, ForeignKey("pt_sites.id", ondelete="CASCADE"), nullable=False, index=True, comment="站点ID"
    )
    torrent_id = Column(String(200), nullable=False, comment="站点内种子ID")

    # 基础信息
    title = Column(String(1000), nullable=False, comment="原始标题")
    subtitle = Column(String(500), nullable=True, comment="副标题")
    category = Column(String(20), nullable=True, index=True, comment="标准分类: movie/tv/music/anime/book/game/adult/other")
    original_category_id = Column(String(50), nullable=True, index=True, comment="站点原始分类ID")
    subcategory = Column(String(100), nullable=True, comment="子分类/二级分类")
    size_bytes = Column(BigInteger, nullable=False, comment="文件大小(字节)")
    file_count = Column(Integer, default=1, nullable=False, comment="文件数量")
    torrent_hash = Column(String(40), nullable=True, comment="种子哈希InfoHash")

    # 做种信息
    seeders = Column(Integer, default=0, nullable=False, comment="做种数")
    leechers = Column(Integer, default=0, nullable=False, comment="下载数")
    completions = Column(Integer, default=0, nullable=False, comment="完成数")
    last_seeder_update_at = Column(TZDateTime(), nullable=True, comment="做种数最后更新时间")

    # 促销信息
    promotion_type = Column(String(20), nullable=True, comment="促销类型: free/50%/2x/2x50%/none")
    promotion_expire_at = Column(TZDateTime(), nullable=True, comment="促销结束时间")
    is_free = Column(Boolean, default=False, nullable=False, index=True, comment="是否免费")
    is_discount = Column(Boolean, default=False, nullable=False, comment="是否折扣")
    is_double_upload = Column(Boolean, default=False, nullable=False, comment="是否双倍上传")

    # HR要求
    has_hr = Column(Boolean, default=False, nullable=False, comment="是否有HR要求")
    hr_days = Column(Integer, nullable=True, comment="需要保种天数")
    hr_seed_time = Column(Integer, nullable=True, comment="需要保种小时数")
    hr_ratio = Column(DECIMAL(5, 2), nullable=True, comment="需要分享率")

    # 质量信息
    resolution = Column(String(20), nullable=True, comment="分辨率: 2160p/1080p/720p等")
    source = Column(String(50), nullable=True, comment="来源: BluRay/WEB-DL/HDTV等")
    codec = Column(String(50), nullable=True, comment="编码: x264/x265/AV1等")
    audio = Column(JSON, nullable=True, comment="音轨信息JSON数组")
    subtitle_info = Column(JSON, nullable=True, comment="字幕信息JSON数组")
    quality_tags = Column(JSON, nullable=True, comment="其他质量标签JSON数组")

    # 电视剧季度/集数信息（仅当category='tv'时有值）
    tv_info = Column(
        JSON,
        nullable=True,
        comment="电视剧信息JSON: {seasons: [1,2], episodes: {1: {start:1, end:10}}, is_complete_season: true}",
    )

    # 关联ID和评分
    imdb_id = Column(String(20), nullable=True, index=True, comment="IMDB ID")
    imdb_rating = Column(DECIMAL(3, 1), nullable=True, comment="IMDB评分")
    douban_id = Column(String(20), nullable=True, index=True, comment="豆瓣ID")
    douban_rating = Column(DECIMAL(3, 1), nullable=True, comment="豆瓣评分")
    tmdb_id = Column(Integer, nullable=True, comment="TMDB ID")

    # Detail信息（通过detail接口获取）
    description = Column(Text, nullable=True, comment="完整描述(BB代码)")
    mediainfo = Column(Text, nullable=True, comment="MediaInfo信息")
    origin_file_name = Column(String(500), nullable=True, comment="原始种子文件名")
    image_list = Column(JSON, nullable=True, comment="图片列表JSON数组")
    detail_fetched = Column(Boolean, default=False, nullable=False, comment="是否已获取详情")
    detail_fetched_at = Column(TZDateTime(), nullable=True, comment="详情获取时间")

    # 豆瓣详细信息（通过豆瓣API获取）
    douban_info = Column(JSON, nullable=True, comment="豆瓣详细信息JSON")
    douban_fetched = Column(Boolean, default=False, nullable=False, comment="是否已获取豆瓣信息")
    douban_fetched_at = Column(TZDateTime(), nullable=True, comment="豆瓣信息获取时间")

    # 识别状态
    identification_status = Column(
        String(20), nullable=True, index=True, comment="识别状态: unidentified/identified/failed"
    )

    # URL和原始数据
    detail_url = Column(Text, nullable=True, comment="详情页URL")
    download_url = Column(Text, nullable=False, comment="下载链接")
    magnet_link = Column(Text, nullable=True, comment="磁力链接")
    raw_page_html = Column(Text, nullable=True, comment="原始页面HTML(调试用)")
    raw_page_json = Column(JSON, nullable=True, comment="原始页面解析后的结构化数据")
    raw_detail_json = Column(JSON, nullable=True, comment="详情接口原始数据JSON")

    # 状态和时间
    is_active = Column(Boolean, default=True, nullable=False, index=True, comment="是否有效")
    last_check_at = Column(TZDateTime(), nullable=True, comment="最后检查时间")
    published_at = Column(TZDateTime(), nullable=True, index=True, comment="发布时间")

    # 关系
    site = relationship("PTSite", backref=backref("resources", passive_deletes=True))
    download_tasks = relationship("DownloadTask", back_populates="pt_resource")
    # mapping 关系由 ResourceMapping.pt_resource 的 backref 自动生成
    resource_detail = relationship(
        "PTResourceDetail",
        back_populates="pt_resource",
        uselist=False,
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<PTResource(id={self.id}, site_id={self.site_id}, title={self.title[:30]})>"

    @property
    def is_promotional(self) -> bool:
        """是否有促销"""
        return self.is_free or self.is_discount or self.is_double_upload

    @property
    def size_gb(self) -> float:
        """获取文件大小(GB)"""
        return round(self.size_bytes / (1024**3), 2) if self.size_bytes else 0.0

    @property
    def size_human_readable(self) -> str:
        """人类可读的文件大小"""
        if not self.size_bytes:
            return "0 B"

        units = ["B", "KB", "MB", "GB", "TB"]
        size = float(self.size_bytes)
        unit_idx = 0

        while size >= 1024 and unit_idx < len(units) - 1:
            size /= 1024
            unit_idx += 1

        return f"{size:.2f} {units[unit_idx]}"
