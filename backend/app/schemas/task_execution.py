# -*- coding: utf-8 -*-
"""
任务执行记录相关Schemas
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from app.constants import EXECUTION_STATUSES, TASK_TYPES, RELATED_TYPES
from app.schemas.base import BaseResponseSchema


class TaskExecutionBase(BaseModel):
    """任务执行基础信息"""

    task_type: str = Field(..., description="任务类型")
    task_name: str = Field(..., description="任务名称")


class TaskExecutionCreate(TaskExecutionBase):
    """创建任务执行记录"""

    scheduled_task_id: Optional[int] = Field(None, description="关联调度任务ID")
    related_type: Optional[str] = Field(None, description="关联实体类型")
    related_id: Optional[int] = Field(None, description="关联实体ID")
    handler: str = Field(..., description="处理器标识")
    handler_params: Optional[Dict[str, Any]] = Field(None, description="处理器参数")
    priority: int = Field(default=0, description="任务优先级")
    scheduled_at: Optional[datetime] = Field(None, description="计划执行时间")
    max_retries: int = Field(default=3, ge=0, description="最大重试次数")
    task_metadata: Optional[Dict[str, Any]] = Field(None, description="任务元数据")

    @field_validator("task_type")
    @classmethod
    def validate_task_type(cls, v: str) -> str:
        """验证任务类型"""
        if v not in TASK_TYPES:
            raise ValueError(f"任务类型必须是: {', '.join(TASK_TYPES)}之一")
        return v

    @field_validator("related_type")
    @classmethod
    def validate_related_type(cls, v: Optional[str]) -> Optional[str]:
        """验证关联类型"""
        if v is not None and v not in RELATED_TYPES:
            raise ValueError(f"关联类型必须是: {', '.join(RELATED_TYPES)}之一")
        return v


class TaskExecutionUpdate(BaseModel):
    """更新任务执行记录"""

    status: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration: Optional[int] = Field(None, ge=0)
    retry_count: Optional[int] = Field(None, ge=0)
    next_retry_at: Optional[datetime] = None
    worker_id: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    error_detail: Optional[Dict[str, Any]] = None
    progress: Optional[int] = Field(None, ge=0, le=100)
    progress_detail: Optional[Dict[str, Any]] = None
    logs: Optional[str] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        """验证状态"""
        if v is not None and v not in EXECUTION_STATUSES:
            raise ValueError(f"状态必须是: {', '.join(EXECUTION_STATUSES)}之一")
        return v


class TaskExecutionResponse(BaseResponseSchema, TaskExecutionBase):
    """任务执行记录响应"""

    id: int
    scheduled_task_id: Optional[int] = None
    related_type: Optional[str] = None
    related_id: Optional[int] = None
    status: str
    priority: int
    handler: str
    handler_params: Optional[Dict[str, Any]] = None
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration: Optional[int] = None
    retry_count: int
    max_retries: int
    next_retry_at: Optional[datetime] = None
    worker_id: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    error_detail: Optional[Dict[str, Any]] = None
    progress: int
    progress_detail: Optional[Dict[str, Any]] = None
    logs: Optional[str] = None
    task_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime


class TaskExecutionListResponse(BaseModel):
    """任务执行记录列表响应"""

    total: int = Field(..., description="总数")
    items: List[TaskExecutionResponse] = Field(..., description="执行记录列表")


class TaskExecutionSummary(BaseResponseSchema):
    """任务执行摘要（用于前端任务队列展示）"""

    id: int
    task_name: str
    task_type: str
    status: str
    progress: int
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration: Optional[int] = None
    handler_params: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class TaskQueueResponse(BaseModel):
    """任务队列响应"""

    running: List[TaskExecutionSummary] = Field(..., description="运行中的任务")
    pending: List[TaskExecutionSummary] = Field(..., description="等待中的任务")
    recent_completed: List[TaskExecutionSummary] = Field(..., description="最近完成的任务")
