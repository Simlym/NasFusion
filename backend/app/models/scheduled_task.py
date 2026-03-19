# -*- coding: utf-8 -*-
"""
调度任务数据模型
"""
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text

from app.models.base import BaseModel
from app.core.json_types import JSON


class ScheduledTask(BaseModel):
    """调度任务模板表"""

    __tablename__ = "scheduled_tasks"

    task_name = Column(
        String(255), unique=True, nullable=False, index=True, comment="任务名称，全局唯一标识"
    )
    task_type = Column(
        String(50),
        nullable=False,
        index=True,
        comment="任务类型：pt_sync/subscription_check/ai_recommendation/notification_send/scan_media/cleanup",
    )
    enabled = Column(Boolean, default=True, nullable=False, comment="是否启用该任务")

    # 调度配置
    schedule_type = Column(
        String(50), nullable=False, comment="调度类型：cron/interval/one_time/manual"
    )
    schedule_config = Column(
        JSON,
        nullable=True,
        comment="调度配置，JSON格式。cron: {cron: '0 */6 * * *', timezone: 'Asia/Shanghai'}; interval: {interval: 3600, unit: 'seconds'}",
    )

    # 处理器配置
    handler = Column(
        String(255), nullable=False, comment="处理器标识，对应后端处理函数路径"
    )
    handler_params = Column(JSON, nullable=True, comment="处理器参数模板，JSON格式")

    # 执行控制
    priority = Column(Integer, default=0, nullable=False, comment="任务优先级，数值越大优先级越高")
    timeout = Column(Integer, nullable=True, comment="任务超时时间，秒")
    max_retries = Column(Integer, default=3, nullable=False, comment="最大重试次数")
    retry_delay = Column(Integer, default=60, nullable=False, comment="重试延迟，秒")

    # 执行状态
    next_run_at = Column(DateTime(timezone=True), nullable=True, comment="下次计划执行时间")
    last_run_at = Column(DateTime(timezone=True), nullable=True, comment="最后执行时间")
    last_run_status = Column(String(20), nullable=True, comment="最后执行状态：success/failed/running")
    last_run_duration = Column(Integer, nullable=True, comment="最后执行耗时，秒")

    # 统计信息
    total_runs = Column(Integer, default=0, nullable=False, comment="总执行次数")
    success_runs = Column(Integer, default=0, nullable=False, comment="成功执行次数")
    failed_runs = Column(Integer, default=0, nullable=False, comment="失败执行次数")

    # 描述信息
    description = Column(Text, nullable=True, comment="任务描述说明")

    def __repr__(self):
        return f"<ScheduledTask(id={self.id}, name={self.task_name}, type={self.task_type}, enabled={self.enabled})>"

    @property
    def is_active(self) -> bool:
        """是否处于活动状态"""
        return self.enabled

    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.total_runs == 0:
            return 0.0
        return self.success_runs / self.total_runs * 100
