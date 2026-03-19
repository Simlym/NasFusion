# -*- coding: utf-8 -*-
"""
调度任务相关Schemas
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from app.constants import SCHEDULE_TYPES, TASK_TYPES, LAST_RUN_STATUSES
from app.schemas.base import BaseResponseSchema


class ScheduledTaskBase(BaseModel):
    """调度任务基础信息"""

    task_name: str = Field(..., min_length=1, max_length=255, description="任务名称，全局唯一")
    task_type: str = Field(..., description="任务类型")
    description: Optional[str] = Field(None, description="任务描述")


class ScheduledTaskCreate(ScheduledTaskBase):
    """创建调度任务"""

    enabled: bool = Field(default=True, description="是否启用")
    schedule_type: str = Field(..., description="调度类型: cron/interval/one_time/manual")
    schedule_config: Optional[Dict[str, Any]] = Field(None, description="调度配置")
    handler: str = Field(..., description="处理器标识")
    handler_params: Optional[Dict[str, Any]] = Field(None, description="处理器参数模板")
    priority: int = Field(default=0, description="任务优先级")
    timeout: Optional[int] = Field(None, ge=1, description="任务超时时间（秒）")
    max_retries: int = Field(default=3, ge=0, description="最大重试次数")
    retry_delay: int = Field(default=60, ge=1, description="重试延迟（秒）")

    @field_validator("task_type")
    @classmethod
    def validate_task_type(cls, v: str) -> str:
        """验证任务类型"""
        if v not in TASK_TYPES:
            raise ValueError(f"任务类型必须是: {', '.join(TASK_TYPES)}之一")
        return v

    @field_validator("schedule_type")
    @classmethod
    def validate_schedule_type(cls, v: str) -> str:
        """验证调度类型"""
        if v not in SCHEDULE_TYPES:
            raise ValueError(f"调度类型必须是: {', '.join(SCHEDULE_TYPES)}之一")
        return v


class ScheduledTaskUpdate(BaseModel):
    """更新调度任务"""

    task_name: Optional[str] = Field(None, min_length=1, max_length=255)
    task_type: Optional[str] = None
    enabled: Optional[bool] = None
    schedule_type: Optional[str] = None
    schedule_config: Optional[Dict[str, Any]] = None
    handler: Optional[str] = None
    handler_params: Optional[Dict[str, Any]] = None
    priority: Optional[int] = None
    timeout: Optional[int] = Field(None, ge=1)
    max_retries: Optional[int] = Field(None, ge=0)
    retry_delay: Optional[int] = Field(None, ge=1)
    description: Optional[str] = None

    @field_validator("task_type")
    @classmethod
    def validate_task_type(cls, v: Optional[str]) -> Optional[str]:
        """验证任务类型"""
        if v is not None and v not in TASK_TYPES:
            raise ValueError(f"任务类型必须是: {', '.join(TASK_TYPES)}之一")
        return v

    @field_validator("schedule_type")
    @classmethod
    def validate_schedule_type(cls, v: Optional[str]) -> Optional[str]:
        """验证调度类型"""
        if v is not None and v not in SCHEDULE_TYPES:
            raise ValueError(f"调度类型必须是: {', '.join(SCHEDULE_TYPES)}之一")
        return v


class ScheduledTaskResponse(BaseResponseSchema, ScheduledTaskBase):
    """调度任务响应"""

    id: int
    enabled: bool
    schedule_type: str
    schedule_config: Optional[Dict[str, Any]] = None
    handler: str
    handler_params: Optional[Dict[str, Any]] = None
    priority: int
    timeout: Optional[int] = None
    max_retries: int
    retry_delay: int
    next_run_at: Optional[datetime] = None
    last_run_at: Optional[datetime] = None
    last_run_status: Optional[str] = None
    last_run_duration: Optional[int] = None
    total_runs: int
    success_runs: int
    failed_runs: int
    created_at: datetime
    updated_at: datetime


class ScheduledTaskListResponse(BaseModel):
    """调度任务列表响应"""

    total: int = Field(..., description="总数")
    items: List[ScheduledTaskResponse] = Field(..., description="任务列表")


class ScheduledTaskRunRequest(BaseModel):
    """立即执行任务请求"""

    handler_params: Optional[Dict[str, Any]] = Field(None, description="覆盖处理器参数")


class PTSyncTaskCreate(BaseModel):
    """PT站点同步任务快速创建"""

    site_id: int = Field(..., description="站点ID")
    task_name: str = Field(..., min_length=1, max_length=255, description="任务名称")
    schedule_type: str = Field(default="interval", description="调度类型")
    schedule_config: Optional[Dict[str, Any]] = Field(
        default=None, description="调度配置，interval模式默认6小时"
    )
    sync_type: str = Field(default="incremental", description="同步类型: full/incremental/manual")
    max_pages: Optional[int] = Field(None, ge=1, description="最大同步页数")
    request_interval: Optional[int] = Field(None, ge=1, le=60, description="请求间隔（秒），留空使用站点默认配置")
    enabled: bool = Field(default=True, description="是否启用")
    description: Optional[str] = Field(None, description="任务描述")

    # ========== 过滤参数 ==========
    mode: Optional[str] = Field(
        default="normal",
        description="资源模式: normal/movie/tvshow/adult"
    )
    categories: Optional[List[str]] = Field(
        None,
        description="分类列表"
    )
    upload_date_start: Optional[str] = Field(
        None,
        description="上传开始时间"
    )
    upload_date_end: Optional[str] = Field(
        None,
        description="上传结束时间"
    )
    keyword: Optional[str] = Field(
        None,
        description="关键字搜索"
    )
    sortField: Optional[str] = Field(
        None,
        description="排序字段"
    )
    sortDirection: Optional[str] = Field(
        None,
        description="排序方向: ASC/DESC"
    )

    @field_validator("schedule_type")
    @classmethod
    def validate_schedule_type(cls, v: str) -> str:
        """验证调度类型"""
        if v not in SCHEDULE_TYPES:
            raise ValueError(f"调度类型必须是: {', '.join(SCHEDULE_TYPES)}之一")
        return v

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v: Optional[str]) -> Optional[str]:
        """验证资源模式"""
        from app.constants import SYNC_MODES
        if v is not None and v not in SYNC_MODES:
            raise ValueError(f"资源模式必须是: {', '.join(SYNC_MODES)}之一")
        return v
