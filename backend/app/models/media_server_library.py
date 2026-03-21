# -*- coding: utf-8 -*-
"""
媒体服务器媒体库模型
"""
from sqlalchemy import Column, Integer, String, ForeignKey, Index
from sqlalchemy.sql import func

from app.models.base import Base
from app.core.json_types import JSON, TZDateTime


class MediaServerLibrary(Base):
    """媒体服务器媒体库模型"""

    __tablename__ = "media_server_libraries"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # 媒体服务器配置关联
    media_server_config_id = Column(
        Integer,
        ForeignKey("media_server_configs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="媒体服务器配置ID",
    )

    # 媒体库原始ID（媒体服务器中的ID）
    library_id = Column(String(255), nullable=False, index=True, comment="媒体服务器中的库ID")

    # 媒体库名称
    name = Column(String(255), nullable=False, comment="媒体库名称")

    # 媒体库类型（movies/tvshows/music/books等）
    type = Column(String(50), nullable=False, comment="媒体库类型")

    # 存储位置
    locations = Column(JSON, nullable=True, comment="媒体库存储位置列表")

    # 封面图地址（相对路径）
    image_url = Column(String(500), nullable=True, comment="封面图地址")

    # Web 跳转链接
    web_url = Column(String(500), nullable=True, comment="Web跳转链接")

    # 条目数量（可选缓存）
    item_count = Column(Integer, default=0, comment="媒体库条目数量")

    # 最后扫描时间
    last_scan_at = Column(TZDateTime(), nullable=True, comment="最后扫描时间")

    # 时间戳
    created_at = Column(TZDateTime(), server_default=func.now(), nullable=False, comment="创建时间")
    updated_at = Column(
        TZDateTime(), server_default=func.now(), onupdate=func.now(), nullable=False, comment="更新时间"
    )

    # 索引
    __table_args__ = (
        Index("idx_ms_lib_config_lib", "media_server_config_id", "library_id", unique=True),
    )

    def __repr__(self):
        return f"<MediaServerLibrary(name={self.name}, type={self.type})>"
