"""
同步日志相关Schemas
"""
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SyncLogBase(BaseModel):
    """同步日志基础配置"""

    site_id: int = Field(..., description="站点ID")
    sync_type: str = Field(..., description="同步类型: full/incremental/manual")
    status: str = Field(..., description="状态: running/success/failed/cancelled")


class SyncLogResponse(SyncLogBase):
    """同步日志响应"""

    id: int
    started_at: datetime
    completed_at: Optional[datetime]
    duration: Optional[int]

    # 统计信息
    total_pages: Optional[int]
    resources_found: int
    resources_new: int
    resources_updated: int
    resources_skipped: int
    resources_error: int
    duplicate_resources: int
    invalid_resources: int

    # 同步策略参数
    sync_strategy: Optional[str]
    sync_params: Optional[Dict[str, Any]]

    # 错误信息
    error_message: Optional[str]
    error_detail: Optional[Dict[str, Any]]

    # 性能指标
    requests_count: int
    avg_response_time: Optional[int]
    rate_limited: bool
    peak_memory_usage: Optional[int]
    cpu_usage_percent: Optional[Decimal]
    network_bytes_received: Optional[int]

    # 详细统计
    quality_distribution: Optional[Dict[str, Any]]
    response_times: Optional[Dict[str, Any]]
    error_types: Optional[Dict[str, Any]]

    # 增量同步
    incremental_checkpoint: Optional[str]
    pages_processed: int
    items_per_page: int

    # 触发操作
    auto_download_triggered: int
    recommendations_generated: int

    # 调试信息
    debug_info: Optional[Dict[str, Any]]
    sync_version: Optional[str]
    user_agent: Optional[str]
    proxy_used: bool

    created_at: datetime

    # 计算字段
    is_running: bool = Field(description="是否正在运行")
    is_success: bool = Field(description="是否成功")
    is_failed: bool = Field(description="是否失败")
    success_rate: float = Field(description="成功率")

    class Config:
        from_attributes = True


class SyncLogList(BaseModel):
    """同步日志列表响应"""

    total: int = Field(..., description="总数")
    page: int = Field(..., description="当前页")
    page_size: int = Field(..., description="每页大小")
    items: List[SyncLogResponse] = Field(..., description="日志列表")


class SyncLogFilter(BaseModel):
    """同步日志过滤参数"""

    site_id: Optional[int] = Field(None, description="站点ID")
    sync_type: Optional[str] = Field(None, description="同步类型")
    status: Optional[str] = Field(None, description="状态")
    start_date: Optional[datetime] = Field(None, description="开始日期")
    end_date: Optional[datetime] = Field(None, description="结束日期")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页大小")