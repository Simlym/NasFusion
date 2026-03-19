# -*- coding: utf-8 -*-
"""
任务执行记录数据模型
"""
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)

from app.core.json_types import JSON

from app.models.base import BaseModel


class TaskExecution(BaseModel):
    """任务执行记录表（任务队列）"""

    __tablename__ = "task_executions"

    # 关联调度任务
    scheduled_task_id = Column(
        Integer,
        ForeignKey("scheduled_tasks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="来源的调度任务ID，手动任务可为NULL",
    )

    # 任务基本信息
    task_type = Column(
        String(50), nullable=False, index=True, comment="任务类型：与scheduled_tasks.task_type一致"
    )
    task_name = Column(
        String(255), nullable=False, comment="任务名称，可重复（同一任务多次执行）"
    )

    # 关联实体
    related_type = Column(
        String(50), nullable=True, comment="关联实体类型：pt_site/subscription/user"
    )
    related_id = Column(Integer, nullable=True, comment="关联实体ID")

    # 执行状态
    status = Column(
        String(20),
        default="pending",
        nullable=False,
        index=True,
        comment="任务状态：pending/running/completed/failed/cancelled/timeout",
    )
    priority = Column(Integer, default=0, nullable=False, comment="任务优先级")

    # 处理器配置
    handler = Column(String(255), nullable=False, comment="处理器标识")
    handler_params = Column(JSON, nullable=True, comment="处理器参数，JSON格式")

    # 时间信息
    scheduled_at = Column(DateTime(timezone=True), nullable=True, comment="计划执行时间")
    started_at = Column(DateTime(timezone=True), nullable=True, comment="实际开始执行时间")
    completed_at = Column(DateTime(timezone=True), nullable=True, comment="完成时间")
    duration = Column(Integer, nullable=True, comment="执行耗时，秒")

    # 重试控制
    retry_count = Column(Integer, default=0, nullable=False, comment="当前重试次数")
    max_retries = Column(Integer, default=3, nullable=False, comment="最大重试次数")
    next_retry_at = Column(DateTime(timezone=True), nullable=True, comment="下次重试时间")

    # 执行信息
    worker_id = Column(String(100), nullable=True, comment="执行该任务的工作进程ID")
    result = Column(JSON, nullable=True, comment="执行结果，JSON格式")
    error_message = Column(Text, nullable=True, comment="错误信息")
    error_detail = Column(JSON, nullable=True, comment="详细错误信息，JSON格式")

    # 进度信息
    progress = Column(Integer, default=0, nullable=False, comment="任务进度 0-100")
    progress_detail = Column(JSON, nullable=True, comment="进度详情，JSON格式")

    # 日志和元数据
    logs = Column(Text, nullable=True, comment="任务执行日志")
    task_metadata = Column(JSON, nullable=True, comment="任务元数据，JSON格式")

    __table_args__ = (
        CheckConstraint("progress >= 0 AND progress <= 100", name="check_progress_range"),
    )

    def __repr__(self):
        return f"<TaskExecution(id={self.id}, name={self.task_name}, status={self.status}, progress={self.progress}%)>"

    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self.status == "running"

    @property
    def is_finished(self) -> bool:
        """是否已完成（包括成功、失败、取消、超时）"""
        return self.status in ["completed", "failed", "cancelled", "timeout"]

    @property
    def can_retry(self) -> bool:
        """是否可以重试"""
        return self.status == "failed" and self.retry_count < self.max_retries
