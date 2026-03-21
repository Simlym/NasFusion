"""
通知相关数据模型
"""
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models.base import BaseModel
from app.core.json_types import JSON, TZDateTime
from app.utils.timezone import now


class NotificationChannel(BaseModel):
    """通知渠道配置表"""

    __tablename__ = "notification_channels"

    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, comment="用户ID，NULL表示系统级"
    )
    channel_type = Column(
        String(30), nullable=False, comment="渠道类型: telegram/email/webhook/discord"
    )
    name = Column(String(100), nullable=False, comment="渠道名称")
    config = Column(JSON, nullable=False, comment="渠道特定配置")
    enabled = Column(Boolean, default=True, nullable=False, comment="是否启用")
    status = Column(String(20), default="healthy", nullable=False, comment="状态: healthy/error")
    last_test_at = Column(TZDateTime(), nullable=True, comment="最后测试时间")
    last_test_result = Column(Text, nullable=True, comment="最后测试结果")
    subscribed_events = Column(JSON, nullable=True, comment="订阅的事件类型")
    priority = Column(Integer, default=5, nullable=False, comment="渠道优先级(1-10)")
    rate_limit = Column(JSON, nullable=True, comment="发送频率限制")
    supports_html = Column(Boolean, default=False, nullable=False, comment="是否支持HTML格式")
    supports_markdown = Column(Boolean, default=False, nullable=False, comment="是否支持Markdown格式")
    max_message_length = Column(Integer, default=1000, nullable=False, comment="最大消息长度")
    message_templates = Column(JSON, nullable=True, comment="消息模板")
    failure_handling = Column(JSON, nullable=True, comment="失败处理策略")
    last_success_at = Column(TZDateTime(), nullable=True, comment="最后成功时间")
    consecutive_failures = Column(Integer, default=0, nullable=False, comment="连续失败次数")
    health_check_url = Column(Text, nullable=True, comment="健康检查URL")
    description = Column(Text, nullable=True, comment="渠道描述")
    icon_url = Column(Text, nullable=True, comment="图标URL")
    color = Column(String(7), default="#007bff", nullable=False, comment="渠道颜色")

    # 关系
    user = relationship("User", back_populates="notification_channels")
    notification_external = relationship("NotificationExternal", back_populates="channel", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<NotificationChannel(id={self.id}, type={self.channel_type}, name={self.name})>"


class NotificationInternal(BaseModel):
    """站内消息表 - 用户在系统内收到的通知"""

    __tablename__ = "notification_internal"

    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, comment="用户ID，NULL表示系统广播"
    )
    notification_type = Column(String(50), nullable=False, index=True, comment="通知类型")
    title = Column(String(200), nullable=False, comment="通知标题")
    content = Column(Text, nullable=False, comment="通知内容")
    priority = Column(
        String(20), nullable=False, default="normal", index=True, comment="优先级: low/normal/high/urgent"
    )
    status = Column(
        String(20), nullable=False, default="unread", index=True, comment="状态: unread/read/archived"
    )
    related_type = Column(
        String(50), nullable=True, comment="关联资源类型: pt_resource/subscription/download_task等"
    )
    related_id = Column(Integer, nullable=True, comment="关联资源ID")
    extra_data = Column(JSON, nullable=True, comment="扩展数据(JSON)")
    read_at = Column(TZDateTime(), nullable=True, comment="阅读时间")
    expires_at = Column(TZDateTime(), nullable=True, index=True, comment="过期时间")

    # 关系
    user = relationship("User", back_populates="notification_internal")

    def __repr__(self):
        return f"<NotificationInternal(id={self.id}, type={self.notification_type}, title={self.title})>"


class NotificationRule(BaseModel):
    """通知规则配置表"""

    __tablename__ = "notification_rules"

    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True, comment="用户ID"
    )
    name = Column(String(100), nullable=False, comment="规则名称")
    enabled = Column(Boolean, nullable=False, default=True, index=True, comment="是否启用")
    event_type = Column(String(50), nullable=False, index=True, comment="事件类型")
    conditions = Column(JSON, nullable=True, comment="触发条件(JSON)")
    channel_ids = Column(JSON, nullable=False, comment="通知渠道ID列表(JSON数组)")
    send_in_app = Column(Boolean, nullable=False, default=True, comment="发送系统内通知")
    template_id = Column(
        Integer, ForeignKey("notification_templates.id", ondelete="SET NULL"), nullable=True, comment="使用的模板ID"
    )
    silent_hours = Column(JSON, nullable=True, comment="静默时段配置(JSON)")
    deduplication_window = Column(Integer, nullable=True, comment="去重时间窗口(秒)")
    priority = Column(Integer, nullable=False, default=5, comment="规则优先级(1-10)")

    # 关系
    user = relationship("User", back_populates="notification_rules")
    template = relationship("NotificationTemplate", back_populates="rules")

    def __repr__(self):
        return f"<NotificationRule(id={self.id}, name={self.name}, event_type={self.event_type})>"


class NotificationTemplate(BaseModel):
    """通知模板表"""

    __tablename__ = "notification_templates"

    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, comment="用户ID，NULL表示系统模板"
    )
    event_type = Column(String(50), nullable=False, index=True, comment="事件类型")
    name = Column(String(100), nullable=False, comment="模板名称")
    language = Column(String(10), nullable=False, default="zh-CN", comment="语言")
    format = Column(String(20), nullable=False, default="markdown", comment="格式: markdown/html/text")
    title_template = Column(String(200), nullable=False, comment="标题模板")
    content_template = Column(Text, nullable=False, comment="内容模板")
    variables = Column(JSON, nullable=True, comment="可用变量说明(JSON)")
    is_system = Column(Boolean, nullable=False, default=False, comment="是否系统模板")

    # 关系
    user = relationship("User", back_populates="notification_templates")
    rules = relationship("NotificationRule", back_populates="template")

    def __repr__(self):
        return f"<NotificationTemplate(id={self.id}, name={self.name}, event_type={self.event_type})>"


class NotificationExternal(BaseModel):
    """站外通知表 - 记录通过外部渠道发送的通知"""

    __tablename__ = "notification_external"

    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True, comment="用户ID"
    )
    notification_type = Column(String(50), nullable=False, index=True, comment="通知类型")
    channel_id = Column(
        Integer,
        ForeignKey("notification_channels.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="通知渠道ID",
    )
    channel_type = Column(String(30), nullable=True, comment="渠道类型")
    title = Column(String(200), nullable=False, comment="通知标题")
    content = Column(Text, nullable=False, comment="通知内容")
    status = Column(String(20), nullable=False, index=True, comment="状态: pending/sent/failed")
    retry_count = Column(Integer, nullable=False, default=0, comment="重试次数")
    error_message = Column(Text, nullable=True, comment="错误信息")
    sent_at = Column(TZDateTime(), nullable=True, comment="发送时间")
    response_data = Column(JSON, nullable=True, comment="渠道返回数据(JSON)")
    extra_data = Column(JSON, nullable=True, comment="扩展数据(JSON)")

    # 关系
    user = relationship("User", back_populates="notification_external")
    channel = relationship("NotificationChannel", back_populates="notification_external")

    def __repr__(self):
        return f"<NotificationExternal(id={self.id}, type={self.notification_type}, status={self.status})>"
