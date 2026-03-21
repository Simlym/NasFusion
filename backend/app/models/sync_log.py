# -*- coding: utf-8 -*-
"""
PT站点同步日志模型
记录PT站点资源同步任务的详细日志和统计信息
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    DECIMAL,
    Index,
)
from sqlalchemy.orm import relationship

from app.models.base import BaseModel
from app.core.json_types import JSON, TZDateTime


class SyncLog(BaseModel):
    """PT站点同步日志表"""

    __tablename__ = "sync_logs"

    # 基础信息
    site_id = Column(Integer, ForeignKey("pt_sites.id"), nullable=False, comment="站点ID")
    sync_type = Column(
        String(20), nullable=False, comment="同步类型: full/incremental/manual"
    )
    status = Column(
        String(20), nullable=False, comment="状态: running/success/failed/cancelled"
    )

    # 时间信息
    started_at = Column(TZDateTime(), nullable=False, comment="开始时间")
    completed_at = Column(TZDateTime(), nullable=True, comment="完成时间")
    duration = Column(Integer, nullable=True, comment="耗时，秒")

    # 资源统计
    total_pages = Column(Integer, nullable=True, comment="总翻页数")
    resources_found = Column(Integer, default=0, nullable=False, comment="发现资源数")
    resources_new = Column(Integer, default=0, nullable=False, comment="新增资源数")
    resources_updated = Column(Integer, default=0, nullable=False, comment="更新资源数")
    resources_skipped = Column(Integer, default=0, nullable=False, comment="跳过资源数")
    resources_error = Column(Integer, default=0, nullable=False, comment="错误资源数")
    duplicate_resources = Column(Integer, default=0, nullable=False, comment="重复资源数")
    invalid_resources = Column(Integer, default=0, nullable=False, comment="无效资源数")

    # 同步策略
    sync_strategy = Column(
        String(20), nullable=True, comment="同步策略：time_based/page_based/id_based"
    )
    sync_params = Column(JSON, nullable=True, comment="同步参数，JSON")

    # 错误信息
    error_message = Column(Text, nullable=True, comment="错误信息")
    error_detail = Column(JSON, nullable=True, comment="详细错误，JSON")

    # 性能指标
    requests_count = Column(Integer, default=0, nullable=False, comment="请求次数")
    avg_response_time = Column(Integer, nullable=True, comment="平均响应时间，毫秒")
    rate_limited = Column(Boolean, default=False, nullable=False, comment="是否触发限流")
    peak_memory_usage = Column(Integer, nullable=True, comment="峰值内存使用(字节)")
    cpu_usage_percent = Column(
        DECIMAL(5, 2), nullable=True, comment="CPU使用率"
    )
    network_bytes_received = Column(Integer, nullable=True, comment="网络接收字节数")

    # 详细统计
    quality_distribution = Column(JSON, nullable=True, comment="质量分布统计")
    response_times = Column(JSON, nullable=True, comment="响应时间分布")
    error_types = Column(JSON, nullable=True, comment="错误类型统计")

    # 增量同步
    incremental_checkpoint = Column(Text, nullable=True, comment="增量同步检查点")
    pages_processed = Column(Integer, default=0, nullable=False, comment="已处理页数")
    items_per_page = Column(Integer, default=0, nullable=False, comment="每页平均项目数")

    # 触发操作
    auto_download_triggered = Column(
        Integer, default=0, nullable=False, comment="触发的自动下载数"
    )
    recommendations_generated = Column(
        Integer, default=0, nullable=False, comment="生成的推荐数"
    )

    # 调试信息
    debug_info = Column(JSON, nullable=True, comment="调试信息")
    sync_version = Column(String(20), nullable=True, comment="同步引擎版本")
    user_agent = Column(Text, nullable=True, comment="使用的User-Agent")
    proxy_used = Column(Boolean, default=False, nullable=False, comment="是否使用代理")

    # 关系
    site = relationship("PTSite", backref="sync_logs")

    # 索引
    __table_args__ = (
        Index("idx_sync_logs_site_started", "site_id", "started_at"),
        Index("idx_sync_logs_status_started", "status", "started_at"),
    )

    def __repr__(self):
        return f"<SyncLog(id={self.id}, site_id={self.site_id}, sync_type={self.sync_type}, status={self.status})>"

    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self.status == "running"

    @property
    def is_success(self) -> bool:
        """是否成功"""
        return self.status == "success"

    @property
    def is_failed(self) -> bool:
        """是否失败"""
        return self.status == "failed"

    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.resources_found == 0:
            return 0.0
        successful = self.resources_new + self.resources_updated + self.resources_skipped
        return round(successful / self.resources_found, 4)
