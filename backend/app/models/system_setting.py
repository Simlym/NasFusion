# -*- coding: utf-8 -*-
"""
系统设置模型
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Index
from sqlalchemy.sql import func

from app.models.base import Base


class SystemSetting(Base):
    """系统设置表"""

    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # 设置分类
    category = Column(String(50), nullable=False, comment="设置分类（如：metadata, proxy, notification）")

    # 设置键
    key = Column(String(100), nullable=False, unique=True, comment="设置键（唯一）")

    # 设置值
    value = Column(Text, nullable=True, comment="设置值")

    # 设置描述
    description = Column(String(500), nullable=True, comment="设置描述")

    # 是否启用
    is_active = Column(Boolean, default=True, nullable=False, comment="是否启用")

    # 是否加密存储
    is_encrypted = Column(Boolean, default=False, nullable=False, comment="值是否加密存储")

    # 创建和更新时间
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, comment="创建时间")
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False, comment="更新时间"
    )

    # 索引
    __table_args__ = (
        Index("idx_category", "category"),
        Index("idx_category_key", "category", "key"),
    )

    def __repr__(self):
        return f"<SystemSetting(category={self.category}, key={self.key})>"
