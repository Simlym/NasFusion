# -*- coding: utf-8 -*-
"""
下载器相关Pydantic模型
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


# ==================== 下载器配置 ====================


class DownloaderConfigBase(BaseModel):
    """下载器配置基础模型"""

    name: str = Field(..., description="下载器名称", min_length=1, max_length=100)
    type: str = Field(..., description="下载器类型：qbittorrent/transmission/synology_ds")
    is_default: bool = Field(default=False, description="是否默认下载器")
    is_enabled: bool = Field(default=True, description="是否启用")
    host: str = Field(..., description="主机地址", min_length=1, max_length=255)
    port: int = Field(..., description="端口号", ge=1, le=65535)
    username: Optional[str] = Field(None, description="用户名", max_length=255)
    password: Optional[str] = Field(None, description="密码")
    use_ssl: bool = Field(default=False, description="是否使用SSL/HTTPS")
    category_paths: Optional[Dict[str, List[Dict[str, Any]]]] = Field(
        None,
        description="[已废弃] 分类路径映射，已由 storage_mounts 表替代",
        deprecated=True,
    )
    hr_strategy: str = Field(default="auto_limit", description="HR处理策略：none/auto_limit/manual")
    max_concurrent_downloads: Optional[int] = Field(5, description="最大并发下载数", ge=1)
    download_speed_limit: Optional[int] = Field(0, description="下载速度限制（KB/s），0为不限制", ge=0)
    upload_speed_limit: Optional[int] = Field(0, description="上传速度限制（KB/s），0为不限制", ge=0)


class DownloaderConfigCreate(DownloaderConfigBase):
    """创建下载器配置"""

    pass


class DownloaderConfigUpdate(BaseModel):
    """更新下载器配置"""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    type: Optional[str] = None
    is_default: Optional[bool] = None
    is_enabled: Optional[bool] = None
    host: Optional[str] = Field(None, min_length=1, max_length=255)
    port: Optional[int] = Field(None, ge=1, le=65535)
    username: Optional[str] = Field(None, max_length=255)
    password: Optional[str] = None
    use_ssl: Optional[bool] = None
    category_paths: Optional[Dict[str, List[Dict[str, Any]]]] = None
    hr_strategy: Optional[str] = None
    max_concurrent_downloads: Optional[int] = Field(None, ge=1)
    download_speed_limit: Optional[int] = Field(None, ge=0)
    upload_speed_limit: Optional[int] = Field(None, ge=0)


class DownloaderConfigResponse(DownloaderConfigBase):
    """下载器配置响应"""

    id: int
    status: str = Field(..., description="状态：online/offline/error")
    last_check_at: Optional[datetime] = Field(None, description="最后检查时间")
    last_error: Optional[str] = Field(None, description="最后错误信息")
    created_at: datetime
    updated_at: datetime

    # 注意：password 不应该在响应中返回，需要在 Service 层过滤

    class Config:
        from_attributes = True


class DownloaderConfigListResponse(BaseModel):
    """下载器配置列表响应"""

    total: int
    items: List[DownloaderConfigResponse]


class DownloaderTestConnectionRequest(BaseModel):
    """下载器测试连接请求"""

    host: str = Field(..., description="主机地址")
    port: int = Field(..., ge=1, le=65535)
    username: Optional[str] = None
    password: Optional[str] = None
    use_ssl: bool = Field(default=False)


class DownloaderTestConnectionResponse(BaseModel):
    """下载器测试连接响应"""

    success: bool
    message: str
    version: Optional[str] = None


# ==================== 下载任务 ====================


class DownloadTaskBase(BaseModel):
    """下载任务基础模型"""

    pt_resource_id: int = Field(..., description="PT资源ID")
    downloader_config_id: int = Field(..., description="下载器配置ID")
    media_type: str = Field(..., description="媒体类型: movie/tv/music/book/anime/adult")
    unified_table_name: Optional[str] = Field(None, description="统一资源表名（unified_movies, unified_tv_series等）")
    unified_resource_id: Optional[int] = Field(None, description="统一资源ID")
    torrent_name: Optional[str] = Field(None, description="种子名称（可选，会从种子文件自动提取）")
    save_path: Optional[str] = Field(None, description="保存路径（可选，会根据存储挂载点自动选择）")
    auto_organize: bool = Field(default=True, description="下载完成后是否自动整理")
    organize_config_id: Optional[int] = Field(None, description="整理配置ID（整理规则：文件名模板、NFO生成等）")
    storage_mount_id: Optional[int] = Field(None, description="存储挂载点ID（最终存储位置）")
    keep_seeding: bool = Field(default=True, description="是否保持做种")
    seeding_time_limit: Optional[int] = Field(None, description="做种时长限制（小时）")
    seeding_ratio_limit: Optional[float] = Field(None, description="做种分享率限制")


class DownloadTaskCreate(DownloadTaskBase):
    """创建下载任务"""

    pass


class DownloadTaskResponse(BaseModel):
    """下载任务响应"""

    id: int
    task_hash: str
    pt_resource_id: int
    downloader_config_id: int
    media_type: str
    unified_table_name: Optional[str] = None
    unified_resource_id: Optional[int] = None
    client_type: str
    client_task_id: Optional[str] = None
    torrent_name: str
    subtitle: Optional[str] = None
    save_path: str
    status: str
    progress: int
    download_speed: Optional[int] = None
    upload_speed: Optional[int] = None
    eta: Optional[int] = None
    total_size: int
    downloaded_size: int
    uploaded_size: int
    ratio: float
    auto_organize: bool
    organize_config_id: Optional[int] = None
    storage_mount_id: Optional[int] = None
    keep_seeding: bool
    seeding_time_limit: Optional[int] = None
    seeding_ratio_limit: Optional[float] = None
    has_hr: bool
    hr_days: Optional[int] = None
    hr_seed_time: Optional[int] = None
    hr_ratio: Optional[float] = None
    added_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    error_at: Optional[datetime] = None
    retry_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DownloadTaskListResponse(BaseModel):
    """下载任务列表响应"""

    total: int
    items: List[DownloadTaskResponse]


class DownloadTaskActionRequest(BaseModel):
    """下载任务操作请求"""

    action: str = Field(..., description="操作：pause/resume/delete")
    delete_files: bool = Field(default=False, description="删除时是否同时删除文件")

    @field_validator("action")
    @classmethod
    def validate_action(cls, v):
        allowed_actions = ["pause", "resume", "delete"]
        if v not in allowed_actions:
            raise ValueError(f"action must be one of {allowed_actions}")
        return v


class DownloadTaskBatchSyncRequest(BaseModel):
    """下载任务批量同步请求"""

    task_ids: List[int] = Field(..., description="任务ID列表")
