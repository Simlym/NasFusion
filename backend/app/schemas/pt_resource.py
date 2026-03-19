"""
PT资源相关Schemas
"""
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


def to_camel(string: str) -> str:
    """将 snake_case 转换为 camelCase"""
    components = string.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


class PTResourceBase(BaseModel):
    """PT资源基础配置"""

    title: str = Field(..., min_length=1, max_length=1000, description="标题")
    subtitle: Optional[str] = Field(None, max_length=500, description="副标题")
    category: Optional[str] = Field(None, description="分类: movie/tv/music/book/other")
    size_bytes: int = Field(..., ge=0, description="文件大小(字节)")
    file_count: int = Field(default=1, ge=1, description="文件数量")


class PTResourceCreate(PTResourceBase):
    """创建PT资源"""

    site_id: int = Field(..., description="站点ID")
    torrent_id: str = Field(..., max_length=200, description="站点种子ID")
    torrent_hash: Optional[str] = Field(None, max_length=40, description="种子InfoHash")

    # 种子状态
    seeders: int = Field(default=0, ge=0, description="做种数")
    leechers: int = Field(default=0, ge=0, description="下载数")
    completions: int = Field(default=0, ge=0, description="完成数")
    last_seeder_update_at: Optional[datetime] = Field(None, description="做种数更新时间")

    # 促销信息
    promotion_type: Optional[str] = Field(None, description="促销类型: free/50%/2x/2x50%/none")
    promotion_expire_at: Optional[datetime] = Field(None, description="促销过期时间")
    is_free: bool = Field(default=False, description="是否免费")
    is_discount: bool = Field(default=False, description="是否折扣")
    is_double_upload: bool = Field(default=False, description="是否双倍上传")

    # HR规则
    has_hr: bool = Field(default=False, description="是否有HR规则")
    hr_days: Optional[int] = Field(None, ge=0, description="HR天数")
    hr_seed_time: Optional[int] = Field(None, ge=0, description="HR做种时间")
    hr_ratio: Optional[Decimal] = Field(None, ge=0, description="HR分享率")

    # 媒体属性
    resolution: Optional[str] = Field(None, max_length=20, description="分辨率: 2160p/1080p/720p等")
    source: Optional[str] = Field(None, max_length=50, description="来源: BluRay/WEB-DL/HDTV等")
    codec: Optional[str] = Field(None, max_length=50, description="编码: x264/x265/AV1等")
    audio: Optional[List[str]] = Field(None, description="音频信息")
    subtitle_info: Optional[List[str]] = Field(None, description="字幕信息")
    quality_tags: Optional[List[str]] = Field(None, description="质量标签")

    # 外部ID
    imdb_id: Optional[str] = Field(None, max_length=20, description="IMDB ID")
    douban_id: Optional[str] = Field(None, max_length=20, description="豆瓣ID")
    tmdb_id: Optional[int] = Field(None, description="TMDB ID")

    # URL和原始数据
    detail_url: Optional[str] = Field(None, description="详情页URL")
    download_url: str = Field(..., description="下载链接")
    magnet_link: Optional[str] = Field(None, description="磁力链接")
    raw_page_html: Optional[str] = Field(None, description="原始页面HTML(调试用)")
    raw_page_json: Optional[Dict[str, Any]] = Field(None, description="原始页面JSON数据")

    # 状态信息
    is_active: bool = Field(default=True, description="是否激活")
    last_check_at: Optional[datetime] = Field(None, description="最后检查时间")
    published_at: Optional[datetime] = Field(None, description="发布时间")


class PTResourceUpdate(BaseModel):
    """更新PT资源"""

    title: Optional[str] = Field(None, min_length=1, max_length=1000)
    subtitle: Optional[str] = Field(None, max_length=500)
    category: Optional[str] = None
    size_bytes: Optional[int] = Field(None, ge=0)
    file_count: Optional[int] = Field(None, ge=1)
    torrent_hash: Optional[str] = Field(None, max_length=40)

    # 种子状态
    seeders: Optional[int] = Field(None, ge=0)
    leechers: Optional[int] = Field(None, ge=0)
    completions: Optional[int] = Field(None, ge=0)
    last_seeder_update_at: Optional[datetime] = None

    # 促销信息
    promotion_type: Optional[str] = None
    promotion_expire_at: Optional[datetime] = None
    is_free: Optional[bool] = None
    is_discount: Optional[bool] = None
    is_double_upload: Optional[bool] = None

    # HR规则
    has_hr: Optional[bool] = None
    hr_days: Optional[int] = Field(None, ge=0)
    hr_seed_time: Optional[int] = Field(None, ge=0)
    hr_ratio: Optional[Decimal] = Field(None, ge=0)

    # 媒体属性
    resolution: Optional[str] = Field(None, max_length=20)
    source: Optional[str] = Field(None, max_length=50)
    codec: Optional[str] = Field(None, max_length=50)
    audio: Optional[List[str]] = None
    subtitle_info: Optional[List[str]] = None
    quality_tags: Optional[List[str]] = None

    # 外部ID
    imdb_id: Optional[str] = Field(None, max_length=20)
    douban_id: Optional[str] = Field(None, max_length=20)
    tmdb_id: Optional[int] = None

    # URL
    detail_url: Optional[str] = None
    download_url: Optional[str] = None
    magnet_link: Optional[str] = None

    # 状态
    is_active: Optional[bool] = None
    last_check_at: Optional[datetime] = None


class PTResourceResponse(PTResourceBase):
    """PT资源响应"""

    id: int
    site_id: int
    torrent_id: str
    torrent_hash: Optional[str]

    # 种子状态
    seeders: int
    leechers: int
    completions: int
    last_seeder_update_at: Optional[datetime]

    # 促销信息
    promotion_type: Optional[str]
    promotion_expire_at: Optional[datetime]
    is_free: bool
    is_discount: bool
    is_double_upload: bool

    # HR规则
    has_hr: bool
    hr_days: Optional[int]
    hr_seed_time: Optional[int]
    hr_ratio: Optional[Decimal]

    # 媒体属性
    resolution: Optional[str]
    source: Optional[str]
    codec: Optional[str]
    audio: Optional[List[str]]
    subtitle_info: Optional[List[str]]
    quality_tags: Optional[List[str]]

    # 电视剧信息
    tv_info: Optional[Dict[str, Any]] = Field(default=None, description="电视剧信息")

    # 外部ID
    imdb_id: Optional[str]
    douban_id: Optional[str]
    tmdb_id: Optional[int]

    # URL
    detail_url: Optional[str]
    download_url: str
    magnet_link: Optional[str]

    # 状态信息
    is_active: bool
    identification_status: Optional[str] = Field(default=None, description="识别状态: unidentified/identified/failed")
    last_check_at: Optional[datetime]
    published_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    # 计算字段
    size_gb: float = Field(description="文件大小(GB)")
    size_human_readable: str = Field(description="人性化文件大小")
    is_promotional: bool = Field(description="是否促销")

    # 映射状态
    has_mapping: bool = Field(default=False, description="是否已建立映射关系")
    mapping_id: Optional[int] = Field(default=None, description="映射关系ID")
    unified_resource_id: Optional[int] = Field(default=None, description="统一资源ID")
    media_type: Optional[str] = Field(default=None, description="媒体类型")

    # 关联数据
    site_name: Optional[str] = Field(default=None, description="站点名称")

    # 原始分类信息
    original_category_id: Optional[str] = Field(default=None, description="站点原始分类ID")
    original_category_name: Optional[str] = Field(default=None, description="站点原始分类名称")
    subcategory: Optional[str] = Field(default=None, description="子分类/二级分类")

    # 下载状态
    is_downloaded: bool = Field(default=False, description="是否已下载")
    download_status: Optional[str] = Field(default=None, description="下载状态: pending/downloading/paused/completed/seeding/error/deleted")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
    )


class PTResourceList(BaseModel):
    """PT资源列表响应"""

    total: int = Field(..., description="总数")
    page: int = Field(..., description="当前页")
    page_size: int = Field(..., description="每页大小")
    items: List[PTResourceResponse] = Field(..., description="资源列表")

    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
    )


class PTResourceFilter(BaseModel):
    """PT资源过滤参数"""

    site_id: Optional[int] = Field(None, description="站点ID")
    category: Optional[str] = Field(None, description="标准分类")
    original_category_id: Optional[str] = Field(None, description="站点原始分类ID")
    is_free: Optional[bool] = Field(None, description="免费种子")
    is_promotional: Optional[bool] = Field(None, description="促销种子")
    min_seeders: Optional[int] = Field(None, ge=0, description="最少做种数")
    resolution: Optional[str] = Field(None, description="分辨率")
    source: Optional[str] = Field(None, description="来源")
    codec: Optional[str] = Field(None, description="编码")
    search: Optional[str] = Field(None, description="关键词搜索")
    has_mapping: Optional[bool] = Field(None, description="识别状态: 是否已建立映射关系")
    identification_status: Optional[str] = Field(None, description="识别状态: unidentified/identified/failed")
    subscription_id: Optional[int] = Field(None, description="订阅ID: 仅返回匹配该订阅的资源")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=50, ge=1, le=500, description="每页大小")


class SyncRequest(BaseModel):
    """同步请求"""

    sync_type: str = Field(default="manual", description="同步类型: full/incremental/manual")
    force: bool = Field(default=False, description="强制同步忽略限流")
    max_pages: Optional[int] = Field(None, ge=1, description="最大页数")
    start_page: int = Field(default=1, ge=1, description="起始页")

    # ========== 过滤参数 ==========
    mode: Optional[str] = Field(
        default="normal",
        description="资源模式: normal（普通）/ adult（成人）"
    )
    categories: Optional[List[str]] = Field(
        None,
        description="分类列表（例如：['405'] 表示动漫）"
    )
    upload_date_start: Optional[str] = Field(
        None,
        description="上传开始时间（格式：YYYY-MM-DD HH:MM:SS）"
    )
    upload_date_end: Optional[str] = Field(
        None,
        description="上传结束时间（格式：YYYY-MM-DD HH:MM:SS）"
    )
    keyword: Optional[str] = Field(
        None,
        max_length=200,
        description="关键字搜索"
    )

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v: Optional[str]) -> Optional[str]:
        """验证资源模式"""
        from app.constants import SYNC_MODES
        if v is not None and v not in SYNC_MODES:
            raise ValueError(f"资源模式必须是: {', '.join(SYNC_MODES)}之一")
        return v


class SyncResponse(BaseModel):
    """同步响应"""

    sync_log_id: int = Field(..., description="同步日志ID")
    message: str = Field(..., description="响应信息")
    status: str = Field(..., description="状态: running/queued")


class SyncFilters(BaseModel):
    """同步过滤参数（内部传递）"""

    mode: Optional[str] = None
    categories: Optional[List[str]] = None
    upload_date_start: Optional[str] = None
    upload_date_end: Optional[str] = None
    keyword: Optional[str] = None

    def to_adapter_filters(self) -> Dict[str, Any]:
        """转换为适配器接受的格式"""
        filters = {}

        if self.mode:
            filters["mode"] = self.mode

        if self.categories:
            filters["categories"] = self.categories

        if self.upload_date_start:
            filters["upload_date_start"] = self.upload_date_start

        if self.upload_date_end:
            filters["upload_date_end"] = self.upload_date_end

        if self.keyword:
            filters["keyword"] = self.keyword

        return filters