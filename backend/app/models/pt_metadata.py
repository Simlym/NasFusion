# -*- coding: utf-8 -*-
"""
PT站点元数据模型

包括分类、视频编码、分辨率、来源、音频编码、语言、国家等元数据表
"""
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.models.base import BaseModel
from app.core.db_types import JSON


class PTCategory(BaseModel):
    """PT站点分类模型"""

    __tablename__ = "pt_categories"

    # 站点关联
    site_id = Column(
        Integer, ForeignKey("pt_sites.id", ondelete="CASCADE"), nullable=False, index=True, comment="站点ID"
    )

    # 站点原始分类ID
    category_id = Column(String(50), nullable=False, comment="站点原始分类ID")

    # 分类名称
    name_chs = Column(String(200), nullable=False, comment="简体中文分类名")
    name_cht = Column(String(200), nullable=True, comment="繁体中文分类名")
    name_eng = Column(String(200), nullable=True, comment="英文分类名")

    # 层级结构
    parent_id = Column(String(50), nullable=True, comment="父级分类ID")
    order = Column(Integer, default=0, nullable=False, comment="排序顺序")

    # 其他信息
    image = Column(String(500), nullable=True, comment="分类图片URL")
    description = Column(Text, nullable=True, comment="分类描述")

    # 统一分类映射
    mapped_category = Column(
        String(20),
        nullable=False,
        default="other",
        comment="统一分类: movie/tv/music/book/anime/adult/game/other",
    )

    # 分类属性
    is_adult = Column(Boolean, default=False, nullable=False, index=True, comment="是否为成人内容")
    is_active = Column(Boolean, default=True, nullable=False, comment="是否启用")

    # 原始数据
    raw_data = Column(JSON, nullable=True, comment="原始分类数据JSON")

    # 关系
    site = relationship("PTSite", backref="categories")

    # 唯一约束：同一站点的分类ID唯一
    __table_args__ = (
        UniqueConstraint("site_id", "category_id", name="uq_site_category"),
        {"comment": "PT站点分类映射表"},
    )

    def __repr__(self):
        return f"<PTCategory(id={self.id}, site_id={self.site_id}, category_id={self.category_id}, name={self.name_chs})>"

    @property
    def display_name(self) -> str:
        """获取显示名称：优先简体中文"""
        return self.name_chs or self.name_cht or self.name_eng or self.category_id

    @property
    def is_root_category(self) -> bool:
        """是否为根级分类"""
        return self.parent_id is None or self.parent_id == ""

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "site_id": self.site_id,
            "category_id": self.category_id,
            "name_chs": self.name_chs,
            "name_cht": self.name_cht,
            "name_eng": self.name_eng,
            "parent_id": self.parent_id,
            "order": self.order,
            "image": self.image,
            "description": self.description,
            "mapped_category": self.mapped_category,
            "is_adult": self.is_adult,
            "is_active": self.is_active,
            "raw_data": self.raw_data,
        }


class PTVideoCodec(BaseModel):
    """PT站点视频编码表"""

    __tablename__ = "pt_video_codecs"

    # 站点关联
    site_id = Column(
        Integer, ForeignKey("pt_sites.id", ondelete="CASCADE"), nullable=False, index=True, comment="站点ID"
    )

    # 站点原始编码ID
    codec_id = Column(String(50), nullable=False, comment="站点原始编码ID")

    # 编码名称
    name = Column(String(200), nullable=False, comment="编码名称")
    name_chs = Column(String(200), nullable=True, comment="简体中文名称")
    name_cht = Column(String(200), nullable=True, comment="繁体中文名称")
    name_eng = Column(String(200), nullable=True, comment="英文名称")

    # 映射到标准值
    mapped_value = Column(
        String(50), nullable=False, comment="标准化映射值: H.264/H.265/VC-1/MPEG-2/XVID等"
    )

    # 其他信息
    description = Column(Text, nullable=True, comment="编码描述")
    order = Column(Integer, default=0, nullable=False, comment="排序顺序")

    # 状态
    is_active = Column(Boolean, default=True, nullable=False, comment="是否启用")

    # 原始数据
    raw_data = Column(JSON, nullable=True, comment="原始元数据JSON")

    # 关系
    site = relationship("PTSite", backref="video_codecs")

    # 唯一约束：同一站点的编码ID唯一
    __table_args__ = (
        UniqueConstraint("site_id", "codec_id", name="uq_site_video_codec"),
        {"comment": "PT站点视频编码映射表"},
    )

    def __repr__(self):
        return f"<PTVideoCodec(id={self.id}, site_id={self.site_id}, codec_id={self.codec_id}, name={self.name})>"

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "site_id": self.site_id,
            "codec_id": self.codec_id,
            "name": self.name,
            "name_chs": self.name_chs,
            "name_cht": self.name_cht,
            "name_eng": self.name_eng,
            "mapped_value": self.mapped_value,
            "description": self.description,
            "order": self.order,
            "is_active": self.is_active,
            "raw_data": self.raw_data,
        }


class PTStandard(BaseModel):
    """PT站点分辨率/质量标准表"""

    __tablename__ = "pt_standards"

    # 站点关联
    site_id = Column(
        Integer, ForeignKey("pt_sites.id", ondelete="CASCADE"), nullable=False, index=True, comment="站点ID"
    )

    # 站点原始标准ID
    standard_id = Column(String(50), nullable=False, comment="站点原始标准ID")

    # 标准名称
    name = Column(String(200), nullable=False, comment="标准名称")
    name_chs = Column(String(200), nullable=True, comment="简体中文名称")
    name_cht = Column(String(200), nullable=True, comment="繁体中文名称")
    name_eng = Column(String(200), nullable=True, comment="英文名称")

    # 映射到标准值
    mapped_value = Column(
        String(50), nullable=False, comment="标准化映射值: 2160p/1080p/720p/480p等"
    )

    # 其他信息
    description = Column(Text, nullable=True, comment="标准描述")
    order = Column(Integer, default=0, nullable=False, comment="排序顺序")

    # 状态
    is_active = Column(Boolean, default=True, nullable=False, comment="是否启用")

    # 原始数据
    raw_data = Column(JSON, nullable=True, comment="原始元数据JSON")

    # 关系
    site = relationship("PTSite", backref="standards")

    # 唯一约束
    __table_args__ = (
        UniqueConstraint("site_id", "standard_id", name="uq_site_standard"),
        {"comment": "PT站点分辨率/质量标准映射表"},
    )

    def __repr__(self):
        return f"<PTStandard(id={self.id}, site_id={self.site_id}, standard_id={self.standard_id}, name={self.name})>"

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "site_id": self.site_id,
            "standard_id": self.standard_id,
            "name": self.name,
            "name_chs": self.name_chs,
            "name_cht": self.name_cht,
            "name_eng": self.name_eng,
            "mapped_value": self.mapped_value,
            "description": self.description,
            "order": self.order,
            "is_active": self.is_active,
            "raw_data": self.raw_data,
        }


class PTSource(BaseModel):
    """PT站点来源表"""

    __tablename__ = "pt_sources"

    # 站点关联
    site_id = Column(
        Integer, ForeignKey("pt_sites.id", ondelete="CASCADE"), nullable=False, index=True, comment="站点ID"
    )

    # 站点原始来源ID
    source_id = Column(String(50), nullable=False, comment="站点原始来源ID")

    # 来源名称
    name = Column(String(200), nullable=False, comment="来源名称")
    name_chs = Column(String(200), nullable=True, comment="简体中文名称")
    name_cht = Column(String(200), nullable=True, comment="繁体中文名称")
    name_eng = Column(String(200), nullable=True, comment="英文名称")

    # 映射到标准值
    mapped_value = Column(
        String(50), nullable=False, comment="标准化映射值: BluRay/WEB-DL/HDTV/DVD/Remux等"
    )

    # 其他信息
    description = Column(Text, nullable=True, comment="来源描述")
    order = Column(Integer, default=0, nullable=False, comment="排序顺序")

    # 状态
    is_active = Column(Boolean, default=True, nullable=False, comment="是否启用")

    # 原始数据
    raw_data = Column(JSON, nullable=True, comment="原始元数据JSON")

    # 关系
    site = relationship("PTSite", backref="sources")

    # 唯一约束
    __table_args__ = (
        UniqueConstraint("site_id", "source_id", name="uq_site_source"),
        {"comment": "PT站点来源映射表"},
    )

    def __repr__(self):
        return f"<PTSource(id={self.id}, site_id={self.site_id}, source_id={self.source_id}, name={self.name})>"

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "site_id": self.site_id,
            "source_id": self.source_id,
            "name": self.name,
            "name_chs": self.name_chs,
            "name_cht": self.name_cht,
            "name_eng": self.name_eng,
            "mapped_value": self.mapped_value,
            "description": self.description,
            "order": self.order,
            "is_active": self.is_active,
            "raw_data": self.raw_data,
        }


class PTAudioCodec(BaseModel):
    """PT站点音频编码表"""

    __tablename__ = "pt_audio_codecs"

    # 站点关联
    site_id = Column(
        Integer, ForeignKey("pt_sites.id", ondelete="CASCADE"), nullable=False, index=True, comment="站点ID"
    )

    # 站点原始编码ID
    codec_id = Column(String(50), nullable=False, comment="站点原始音频编码ID")

    # 编码名称
    name = Column(String(200), nullable=False, comment="音频编码名称")
    name_chs = Column(String(200), nullable=True, comment="简体中文名称")
    name_cht = Column(String(200), nullable=True, comment="繁体中文名称")
    name_eng = Column(String(200), nullable=True, comment="英文名称")

    # 映射到标准值
    mapped_value = Column(
        String(50), nullable=False, comment="标准化映射值: AAC/AC3/DTS/TrueHD/FLAC/MP3等"
    )

    # 其他信息
    description = Column(Text, nullable=True, comment="编码描述")
    order = Column(Integer, default=0, nullable=False, comment="排序顺序")

    # 状态
    is_active = Column(Boolean, default=True, nullable=False, comment="是否启用")

    # 原始数据
    raw_data = Column(JSON, nullable=True, comment="原始元数据JSON")

    # 关系
    site = relationship("PTSite", backref="audio_codecs")

    # 唯一约束
    __table_args__ = (
        UniqueConstraint("site_id", "codec_id", name="uq_site_audio_codec"),
        {"comment": "PT站点音频编码映射表"},
    )

    def __repr__(self):
        return f"<PTAudioCodec(id={self.id}, site_id={self.site_id}, codec_id={self.codec_id}, name={self.name})>"

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "site_id": self.site_id,
            "codec_id": self.codec_id,
            "name": self.name,
            "name_chs": self.name_chs,
            "name_cht": self.name_cht,
            "name_eng": self.name_eng,
            "mapped_value": self.mapped_value,
            "description": self.description,
            "order": self.order,
            "is_active": self.is_active,
            "raw_data": self.raw_data,
        }


class PTLanguage(BaseModel):
    """PT站点语言表"""

    __tablename__ = "pt_languages"

    # 站点关联
    site_id = Column(
        Integer, ForeignKey("pt_sites.id", ondelete="CASCADE"), nullable=False, index=True, comment="站点ID"
    )

    # 站点原始语言ID
    language_id = Column(String(50), nullable=False, comment="站点原始语言ID")

    # 语言名称
    name = Column(String(200), nullable=False, comment="语言名称")
    name_chs = Column(String(200), nullable=True, comment="简体中文名称")
    name_cht = Column(String(200), nullable=True, comment="繁体中文名称")
    name_eng = Column(String(200), nullable=True, comment="英文名称")

    # 映射到标准值 (ISO 639-1 或常用名称)
    mapped_value = Column(String(50), nullable=False, comment="标准化映射值: zh/en/ja/ko等")

    # 其他信息
    description = Column(Text, nullable=True, comment="语言描述")
    order = Column(Integer, default=0, nullable=False, comment="排序顺序")

    # 状态
    is_active = Column(Boolean, default=True, nullable=False, comment="是否启用")

    # 原始数据
    raw_data = Column(JSON, nullable=True, comment="原始元数据JSON")

    # 关系
    site = relationship("PTSite", backref="languages")

    # 唯一约束
    __table_args__ = (
        UniqueConstraint("site_id", "language_id", name="uq_site_language"),
        {"comment": "PT站点语言映射表"},
    )

    def __repr__(self):
        return f"<PTLanguage(id={self.id}, site_id={self.site_id}, language_id={self.language_id}, name={self.name})>"

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "site_id": self.site_id,
            "language_id": self.language_id,
            "name": self.name,
            "name_chs": self.name_chs,
            "name_cht": self.name_cht,
            "name_eng": self.name_eng,
            "mapped_value": self.mapped_value,
            "description": self.description,
            "order": self.order,
            "is_active": self.is_active,
            "raw_data": self.raw_data,
        }


class PTCountry(BaseModel):
    """PT站点国家/地区表"""

    __tablename__ = "pt_countries"

    # 站点关联
    site_id = Column(
        Integer, ForeignKey("pt_sites.id", ondelete="CASCADE"), nullable=False, index=True, comment="站点ID"
    )

    # 站点原始国家ID
    country_id = Column(String(50), nullable=False, comment="站点原始国家ID")

    # 国家名称
    name = Column(String(200), nullable=False, comment="国家/地区名称")
    name_chs = Column(String(200), nullable=True, comment="简体中文名称")
    name_cht = Column(String(200), nullable=True, comment="繁体中文名称")
    name_eng = Column(String(200), nullable=True, comment="英文名称")

    # 映射到标准值 (ISO 3166-1 alpha-2 或常用名称)
    mapped_value = Column(String(50), nullable=False, comment="标准化映射值: CN/US/JP/KR等")

    # 其他信息
    description = Column(Text, nullable=True, comment="国家/地区描述")
    order = Column(Integer, default=0, nullable=False, comment="排序顺序")

    # 状态
    is_active = Column(Boolean, default=True, nullable=False, comment="是否启用")

    # 原始数据
    raw_data = Column(JSON, nullable=True, comment="原始元数据JSON")

    # 关系
    site = relationship("PTSite", backref="countries")

    # 唯一约束
    __table_args__ = (
        UniqueConstraint("site_id", "country_id", name="uq_site_country"),
        {"comment": "PT站点国家/地区映射表"},
    )

    def __repr__(self):
        return f"<PTCountry(id={self.id}, site_id={self.site_id}, country_id={self.country_id}, name={self.name})>"

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "site_id": self.site_id,
            "country_id": self.country_id,
            "name": self.name,
            "name_chs": self.name_chs,
            "name_cht": self.name_cht,
            "name_eng": self.name_eng,
            "mapped_value": self.mapped_value,
            "description": self.description,
            "order": self.order,
            "is_active": self.is_active,
            "raw_data": self.raw_data,
        }
