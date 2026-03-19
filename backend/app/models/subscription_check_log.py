# -*- coding: utf-8 -*-
"""
订阅检查日志数据模型
"""
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models.base import BaseModel
from app.core.json_types import JSON


class SubscriptionCheckLog(BaseModel):
    """订阅检查日志表"""

    __tablename__ = "subscription_check_logs"

    # 订阅关联
    subscription_id = Column(
        Integer,
        ForeignKey("subscriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="订阅ID",
    )

    # 检查基础信息
    check_at = Column(DateTime(timezone=True), nullable=False, index=True, comment="检查时间")

    # PT搜索结果
    sites_searched = Column(Integer, nullable=True, comment="搜索的站点数")
    resources_found = Column(Integer, nullable=True, comment="发现的资源数")
    match_count = Column(Integer, nullable=True, comment="匹配规则的资源数")
    best_match = Column(JSON, nullable=True, comment="最佳匹配资源JSON")
    search_results = Column(JSON, nullable=True, comment="搜索结果详情JSON")

    # 匹配分析
    matching_analysis = Column(JSON, nullable=True, comment="匹配分析结果JSON")

    # 触发的动作
    action_triggered = Column(
        String(20),
        nullable=True,
        comment="触发的动作: notification/download/none",
    )
    action_detail = Column(JSON, nullable=True, comment="动作详情JSON")

    # 执行状态
    execution_time = Column(Integer, nullable=True, comment="执行耗时（秒）")
    success = Column(Boolean, nullable=True, index=True, comment="是否成功")
    error_message = Column(Text, nullable=True, comment="错误信息")
    error_category = Column(String(50), nullable=True, comment="错误分类")
    error_severity = Column(
        String(20), nullable=False, default="medium", comment="错误严重程度: low/medium/high"
    )

    # 任务执行关联
    task_execution_id = Column(Integer, nullable=True, index=True, comment="关联的任务执行ID（task_executions表）")

    # 关系
    subscription = relationship("Subscription", back_populates="check_logs")

    def __repr__(self):
        return (
            f"<SubscriptionCheckLog(id={self.id}, subscription_id={self.subscription_id}, "
            f"check_at={self.check_at}, success={self.success})>"
        )
