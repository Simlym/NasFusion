"""
登录历史记录模型
记录所有登录尝试（成功和失败），包含 IP、User-Agent 和地理位置信息
"""
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models.base import BaseModel
from app.utils.timezone import now


class LoginHistory(BaseModel):
    """登录历史表"""

    __tablename__ = "login_histories"

    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True, comment="用户ID"
    )
    ip_address = Column(String(45), nullable=True, comment="登录IP地址（支持IPv6）")
    user_agent = Column(Text, nullable=True, comment="浏览器User-Agent")
    location = Column(String(255), nullable=True, comment="IP所在地（国家/省/市）")
    login_status = Column(String(20), nullable=False, default="success", comment="登录状态: success/failed/locked")
    failure_reason = Column(String(100), nullable=True, comment="失败原因")
    login_at = Column(DateTime(timezone=True), default=now, nullable=False, index=True, comment="登录时间")

    # 关系
    user = relationship("User", back_populates="login_histories")

    def __repr__(self):
        return f"<LoginHistory(user_id={self.user_id}, ip={self.ip_address}, status={self.login_status})>"
