"""
用户相关数据模型
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models.base import BaseModel
from app.utils.timezone import now


class User(BaseModel):
    """用户表"""

    __tablename__ = "users"

    username = Column(String(50), unique=True, nullable=False, index=True, comment="用户名")
    email = Column(String(255), unique=True, nullable=True, index=True, comment="邮箱")
    password_hash = Column(String(255), nullable=False, comment="密码哈希")
    role = Column(String(20), default="user", nullable=False, comment="角色: admin/user")
    is_active = Column(Boolean, default=True, nullable=False, comment="是否激活")
    is_verified = Column(Boolean, default=False, nullable=False, comment="是否已验证")
    last_login_at = Column(DateTime(timezone=True), nullable=True, comment="最后登录时间")
    display_name = Column(String(100), nullable=True, comment="显示名称")
    avatar_url = Column(Text, nullable=True, comment="头像URL")
    timezone = Column(String(50), default="UTC", nullable=False, comment="时区")
    language = Column(String(10), default="zh-CN", nullable=False, comment="语言")
    password_changed_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False, comment="密码修改时间"
    )
    login_attempts = Column(Integer, default=0, nullable=False, comment="登录尝试次数")
    locked_until = Column(DateTime(timezone=True), nullable=True, comment="锁定到期时间")

    # 关系
    profile = relationship(
        "UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    notification_channels = relationship(
        "NotificationChannel", back_populates="user", cascade="all, delete-orphan"
    )
    notification_internal = relationship(
        "NotificationInternal", back_populates="user", cascade="all, delete-orphan"
    )
    notification_rules = relationship(
        "NotificationRule", back_populates="user", cascade="all, delete-orphan"
    )
    notification_templates = relationship(
        "NotificationTemplate", back_populates="user", cascade="all, delete-orphan"
    )
    notification_external = relationship(
        "NotificationExternal", back_populates="user", cascade="all, delete-orphan"
    )
    download_tasks = relationship(
        "DownloadTask", back_populates="user"
    )
    login_histories = relationship(
        "LoginHistory", back_populates="user", cascade="all, delete-orphan",
        order_by="desc(LoginHistory.login_at)"
    )

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, role={self.role})>"

    @property
    def is_admin(self) -> bool:
        """是否是管理员"""
        return self.role == "admin"

    @property
    def is_locked(self) -> bool:
        """是否被锁定"""
        if self.locked_until is None:
            return False
        return now() < self.locked_until


class UserProfile(BaseModel):
    """用户配置表"""

    __tablename__ = "user_profiles"

    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, comment="用户ID"
    )

    # UI设置
    ui_theme = Column(String(20), default="auto", nullable=False, comment="界面主题: light/dark/auto")
    language = Column(String(10), default="zh-CN", nullable=False, comment="用户界面语言")
    timezone = Column(String(50), default="UTC", nullable=False, comment="用户时区")
    items_per_page = Column(Integer, default=50, nullable=False, comment="每页显示数量")

    # 下载偏好
    min_seeders = Column(Integer, default=1, nullable=False, comment="最小做种数要求")
    max_auto_download_size_gb = Column(Integer, nullable=True, comment="自动下载最大大小(GB)")
    default_downloader = Column(String(50), nullable=True, comment="默认下载器")
    auto_start_download = Column(Boolean, default=True, nullable=False, comment="自动开始下载")
    download_path_template = Column(Text, nullable=True, comment="下载路径模板")

    # 通知设置
    notification_enabled = Column(Boolean, default=True, nullable=False, comment="启用通知")
    email_notifications = Column(Boolean, default=False, nullable=False, comment="邮件通知")
    push_notifications = Column(Boolean, default=True, nullable=False, comment="推送通知")

    # AI推荐设置
    ai_recommendations_enabled = Column(Boolean, default=False, nullable=False, comment="AI推荐开关")
    recommendation_frequency = Column(
        String(20), default="daily", nullable=False, comment="推荐频率: daily/weekly"
    )

    # 隐私设置
    share_anonymous_stats = Column(Boolean, default=True, nullable=False, comment="分享匿名统计")
    public_watchlist = Column(Boolean, default=False, nullable=False, comment="公开观看列表")

    # 关系
    user = relationship("User", back_populates="profile")

    def __repr__(self):
        return f"<UserProfile(user_id={self.user_id}, theme={self.ui_theme})>"
