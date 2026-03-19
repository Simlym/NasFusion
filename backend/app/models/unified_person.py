# -*- coding: utf-8 -*-
"""
统一人员（演员/导演/编剧）模型
"""
from sqlalchemy import Column, Integer, String, Date, Boolean, DateTime, Text, ForeignKey, Float
from sqlalchemy.orm import relationship, backref

from app.models.base import BaseModel
from app.core.json_types import JSON


class UnifiedPerson(BaseModel):
    """统一人员表（演员/导演/编剧等）"""

    __tablename__ = "unified_persons"

    # ============ 核心标识 ============
    tmdb_id = Column(Integer, unique=True, nullable=True, index=True, comment="TMDB ID")
    imdb_id = Column(String(50), unique=True, nullable=True, index=True, comment="IMDB ID")
    douban_id = Column(String(50), unique=True, nullable=True, index=True, comment="豆瓣 ID")

    # ============ 基本信息 ============
    name = Column(String(255), nullable=False, index=True, comment="姓名")
    other_names = Column(JSON, nullable=True, comment="别名/译名 (JSON数组)")
    family_info = Column(String(500), nullable=True, comment="家庭成员信息")
    biography = Column(Text, nullable=True, comment="简介")
    birthday = Column(Date, nullable=True, comment="出生日期")
    deathday = Column(Date, nullable=True, comment="逝世日期")
    place_of_birth = Column(String(255), nullable=True, comment="出生地")
    gender = Column(Integer, nullable=True, comment="性别 1:女, 2:男, 0:未知")
    homepage = Column(String(500), nullable=True, comment="个人主页")
    known_for_department = Column(String(50), nullable=True, comment="知名于")
    popularity = Column(Float, nullable=True, comment="热度值")

    # ============ 图片 ============
    profile_url = Column(String(500), nullable=True, comment="头像URL")

    # ============ 状态/元数据 ============
    detail_loaded = Column(Boolean, default=False, nullable=False, comment="详情是否已加载")
    detail_loaded_at = Column(DateTime(timezone=True), nullable=True, comment="详情加载时间")
    metadata_source = Column(String(20), nullable=True, comment="元数据来源")
    raw_data = Column(JSON, nullable=True, comment="原始API数据")

    def __repr__(self):
        return f"<UnifiedPerson(id={self.id}, name={self.name}, tmdb_id={self.tmdb_id})>"


class MovieCredit(BaseModel):
    """电影演职员关联表"""

    __tablename__ = "movie_credits"

    movie_id = Column(
        Integer,
        ForeignKey("unified_movies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="电影ID"
    )
    person_id = Column(
        Integer,
        ForeignKey("unified_persons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="人员ID"
    )

    # ============ 职位信息 ============
    job = Column(String(50), nullable=False, index=True, comment="职位: Actor, Director, Writer, etc.")
    character = Column(String(500), nullable=True, comment="角色名")
    order = Column(Integer, default=0, comment="排序")

    # 关系
    movie = relationship("UnifiedMovie", backref=backref("credits", cascade="all, delete-orphan"))
    person = relationship("UnifiedPerson", backref=backref("movie_credits", cascade="all, delete-orphan"))

    def __repr__(self):
        return f"<MovieCredit(movie_id={self.movie_id}, person_id={self.person_id}, job={self.job})>"


class TVSeriesCredit(BaseModel):
    """电视剧演职员关联表"""

    __tablename__ = "tv_series_credits"

    tv_series_id = Column(
        Integer,
        ForeignKey("unified_tv_series.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="电视剧ID"
    )
    person_id = Column(
        Integer,
        ForeignKey("unified_persons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="人员ID"
    )

    # ============ 职位信息 ============
    job = Column(String(50), nullable=False, index=True, comment="职位")
    character = Column(String(500), nullable=True, comment="角色名")
    order = Column(Integer, default=0, comment="排序")

    # 关系
    tv_series = relationship("UnifiedTVSeries", backref=backref("credits", cascade="all, delete-orphan"))
    person = relationship("UnifiedPerson", backref=backref("tv_series_credits", cascade="all, delete-orphan"))

    def __repr__(self):
        return f"<TVSeriesCredit(tv_id={self.tv_series_id}, person_id={self.person_id}, job={self.job})>"
