# -*- coding: utf-8 -*-
"""
图片缓存模型
用于存储外部图片的本地缓存元数据
"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, BigInteger, Index

from app.core.db_types import TZDateTime

from app.models.base import BaseModel


class ImageCache(BaseModel):
    """图片缓存表"""

    __tablename__ = "image_cache"

    # 原始URL（唯一索引）
    original_url = Column(Text, nullable=False, unique=True, comment="原始图片URL")

    # 本地存储路径（相对于缓存根目录）
    local_path = Column(String(512), nullable=False, comment="本地文件路径")

    # 文件哈希（用于去重和验证）
    file_hash = Column(String(64), nullable=False, index=True, comment="文件SHA256哈希")

    # 文件信息
    size_bytes = Column(BigInteger, nullable=False, default=0, comment="文件大小（字节）")
    content_type = Column(String(100), nullable=False, default="image/jpeg", comment="MIME类型")

    # 访问统计
    access_count = Column(Integer, nullable=False, default=0, comment="访问次数")
    last_accessed_at = Column(TZDateTime(), nullable=False, default=datetime.now, comment="最后访问时间")

    # 来源信息
    source_type = Column(String(50), nullable=True, comment="来源类型: tmdb, douban, pt_site等")

    __table_args__ = (
        # 组合索引：按来源类型和创建时间查询
        Index("ix_image_cache_source_created", "source_type", "created_at"),
        # 索引：按最后访问时间排序（用于清理）
        Index("ix_image_cache_last_accessed", "last_accessed_at"),
        # 索引：按大小排序（用于清理）
        Index("ix_image_cache_size", "size_bytes"),
        {"comment": "图片缓存元数据表"}
    )

    def __repr__(self):
        return f"<ImageCache(id={self.id}, url={self.original_url[:50]}..., size={self.size_bytes})>"
