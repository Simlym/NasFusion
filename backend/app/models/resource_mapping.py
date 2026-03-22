# -*- coding: utf-8 -*-
"""
资源映射关系模型 - 多态关联设计
"""
from sqlalchemy import Boolean, Column, Integer, String, DateTime, ForeignKey, CheckConstraint, Index
from sqlalchemy.orm import relationship, backref

from app.models.base import BaseModel
from app.core.db_types import JSON


class ResourceMapping(BaseModel):
    """
    PT资源与统一资源的映射关系表

    使用多态关联模式：media_type + unified_table_name + unified_resource_id
    优点：
    - 无需为每种媒体类型添加外键字段
    - 扩展性好，添加新类型无需改表结构
    - 灵活性高，不同media_type可映射到同一表

    注意：由于是多态关联，没有数据库级外键约束，需要应用层保证数据一致性
    """

    __tablename__ = "resource_mappings"

    # ============ 核心关联 ============
    pt_resource_id = Column(
        Integer,
        ForeignKey("pt_resources.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
        comment="PT资源ID（一个PT资源只能映射到一个统一资源）"
    )

    media_type = Column(
        String(20),
        nullable=False,
        index=True,
        comment="媒体类型：movie/tv/music/book/anime/adult"
    )

    # ============ 多态关联字段 ============
    unified_table_name = Column(
        String(50),
        nullable=False,
        index=True,
        comment="统一资源表名：unified_movies/unified_tv/unified_music/..."
    )

    unified_resource_id = Column(
        Integer,
        nullable=False,
        index=True,
        comment="统一资源ID"
    )

    # ============ 匹配信息 ============
    match_method = Column(
        String(20),
        nullable=True,
        index=True,
        comment="匹配方式：id_exact/title_year/title_fuzzy/manual"
    )

    match_confidence = Column(
        Integer,
        nullable=True,
        comment="匹配置信度 0-100"
    )

    match_score_detail = Column(
        JSON,
        nullable=True,
        comment="匹配得分详情，JSON"
    )

    # ============ 推荐度 ============
    is_primary = Column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        comment="是否主推荐资源（用于多个PT资源时标记最佳）"
    )

    # recommendation_score = Column(
    #     Integer,
    #     nullable=True,
    #     comment="推荐度评分 0-100"
    # )

    # recommendation_reason = Column(
    #     JSON,
    #     nullable=True,
    #     comment="推荐理由，JSON"
    # )

    # ============ 人工确认 ============
    # is_verified = Column(
    #     Boolean,
    #     default=False,
    #     nullable=False,
    #     comment="是否人工确认"
    # )

    # verified_by = Column(
    #     Integer,
    #     nullable=True,
    #     comment="确认者用户ID"
    # )

    # verified_at = Column(
    #     DateTime,
    #     nullable=True,
    #     comment="确认时间"
    # )

    # ============ 关系 ============
    # 一对一关系：一个PT资源只能有一个映射
    pt_resource = relationship("PTResource", backref=backref("mapping", uselist=False))
    # 注意：由于多态关联，无法直接定义到统一资源的relationship
    # 需要在应用层根据unified_table_name动态查询

    # ============ 约束和索引 ============
    __table_args__ = (
        # 组合索引：加速按统一资源查询映射
        Index("ix_resource_mapping_unified", "unified_table_name", "unified_resource_id"),
        # 约束
        # CheckConstraint(
        #     "match_confidence IS NULL OR (match_confidence >= 0 AND match_confidence <= 100)",
        #     name="check_match_confidence_range"
        # ),
        # CheckConstraint(
        #     "recommendation_score IS NULL OR (recommendation_score >= 0 AND recommendation_score <= 100)",
        #     name="check_recommendation_score_range"
        # ),
    )

    def __repr__(self):
        return (
            f"<ResourceMapping(id={self.id}, pt_resource_id={self.pt_resource_id}, "
            f"media_type={self.media_type}, table={self.unified_table_name}, "
            f"resource_id={self.unified_resource_id})>"
        )
