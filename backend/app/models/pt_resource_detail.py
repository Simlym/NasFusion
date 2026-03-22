# -*- coding: utf-8 -*-
"""
PT资源详情表（存储从MTeam API获取的完整信息）
"""
from sqlalchemy import Column, String, Text, Integer, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from app.models.base import BaseModel
from app.core.db_types import JSON, TZDateTime


class PTResourceDetail(BaseModel):
    """PT资源详情表

    作为 pt_resources 的子表（1对1关系），永久存储从 MTeam API 获取的完整详情数据
    """

    __tablename__ = "pt_resource_details"

    # ============ 关联关系 ============
    pt_resource_id = Column(
        Integer,
        ForeignKey('pt_resources.id', ondelete='CASCADE'),
        unique=True,
        nullable=False,
        index=True,
        comment="PT资源ID（外键）"
    )

    # ============ MTeam API 详情字段 ============
    description = Column(Text, nullable=True, comment="资源描述（descr字段）")
    mediainfo = Column(Text, nullable=True, comment="媒体信息（mediainfo字段）")
    nfo = Column(Text, nullable=True, comment="NFO信息")

    # ============ DMM 信息（从 dmmInfo 提取）============
    dmm_product_number = Column(String(50), nullable=True, comment="DMM品番")
    dmm_director = Column(String(200), nullable=True, comment="导演")
    dmm_series = Column(String(200), nullable=True, comment="系列")
    dmm_maker = Column(String(200), nullable=True, comment="制作商")
    dmm_label = Column(String(200), nullable=True, comment="厂牌")
    dmm_actress_list = Column(JSON, nullable=True, comment="演员列表，JSON数组")
    dmm_keyword_list = Column(JSON, nullable=True, comment="标签列表，JSON数组")

    # ============ 其他详情字段 ============
    origin_file_name = Column(String(500), nullable=True, comment="原始文件名")
    thank_count = Column(Integer, nullable=True, comment="感谢数")
    comment_count = Column(Integer, nullable=True, comment="评论数")
    view_count = Column(Integer, nullable=True, comment="查看数")
    hit_count = Column(Integer, nullable=True, comment="命中数")

    # ============ 状态管理 ============
    detail_loaded = Column(Boolean, default=False, nullable=False, comment="详情是否已加载")
    detail_loaded_at = Column(TZDateTime(), nullable=True, comment="详情加载时间")

    # ============ 关系 ============
    pt_resource = relationship("PTResource", back_populates="resource_detail")

    def __repr__(self):
        return f"<PTResourceDetail(id={self.id}, pt_resource_id={self.pt_resource_id})>"
