# -*- coding: utf-8 -*-
"""
PT站点元数据相关Schemas
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ==================== 基础Schema ====================


class PTMetadataBase(BaseModel):
    """元数据基础Schema"""

    metadata_id: str = Field(..., max_length=50, description="站点原始ID")
    name: str = Field(..., max_length=200, description="名称")
    name_chs: Optional[str] = Field(None, max_length=200, description="简体中文名称")
    name_cht: Optional[str] = Field(None, max_length=200, description="繁体中文名称")
    name_eng: Optional[str] = Field(None, max_length=200, description="英文名称")
    mapped_value: str = Field(..., max_length=50, description="标准化映射值")
    description: Optional[str] = Field(None, description="描述")
    order: int = Field(default=0, description="排序顺序")
    is_active: bool = Field(default=True, description="是否启用")


# ==================== 视频编码 ====================


class PTVideoCodecResponse(PTMetadataBase):
    """视频编码响应"""

    id: int
    site_id: int
    codec_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PTVideoCodecCreate(BaseModel):
    """创建视频编码"""

    codec_id: str
    name: str
    name_chs: Optional[str] = None
    name_cht: Optional[str] = None
    name_eng: Optional[str] = None
    mapped_value: str
    description: Optional[str] = None
    order: int = 0
    raw_data: Optional[Dict[str, Any]] = None


# ==================== 分辨率/标准 ====================


class PTStandardResponse(PTMetadataBase):
    """分辨率/标准响应"""

    id: int
    site_id: int
    standard_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PTStandardCreate(BaseModel):
    """创建分辨率/标准"""

    standard_id: str
    name: str
    name_chs: Optional[str] = None
    name_cht: Optional[str] = None
    name_eng: Optional[str] = None
    mapped_value: str
    description: Optional[str] = None
    order: int = 0
    raw_data: Optional[Dict[str, Any]] = None


# ==================== 来源 ====================


class PTSourceResponse(PTMetadataBase):
    """来源响应"""

    id: int
    site_id: int
    source_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PTSourceCreate(BaseModel):
    """创建来源"""

    source_id: str
    name: str
    name_chs: Optional[str] = None
    name_cht: Optional[str] = None
    name_eng: Optional[str] = None
    mapped_value: str
    description: Optional[str] = None
    order: int = 0
    raw_data: Optional[Dict[str, Any]] = None


# ==================== 音频编码 ====================


class PTAudioCodecResponse(PTMetadataBase):
    """音频编码响应"""

    id: int
    site_id: int
    codec_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PTAudioCodecCreate(BaseModel):
    """创建音频编码"""

    codec_id: str
    name: str
    name_chs: Optional[str] = None
    name_cht: Optional[str] = None
    name_eng: Optional[str] = None
    mapped_value: str
    description: Optional[str] = None
    order: int = 0
    raw_data: Optional[Dict[str, Any]] = None


# ==================== 语言 ====================


class PTLanguageResponse(PTMetadataBase):
    """语言响应"""

    id: int
    site_id: int
    language_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PTLanguageCreate(BaseModel):
    """创建语言"""

    language_id: str
    name: str
    name_chs: Optional[str] = None
    name_cht: Optional[str] = None
    name_eng: Optional[str] = None
    mapped_value: str
    description: Optional[str] = None
    order: int = 0
    raw_data: Optional[Dict[str, Any]] = None


# ==================== 国家/地区 ====================


class PTCountryResponse(PTMetadataBase):
    """国家/地区响应"""

    id: int
    site_id: int
    country_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PTCountryCreate(BaseModel):
    """创建国家/地区"""

    country_id: str
    name: str
    name_chs: Optional[str] = None
    name_cht: Optional[str] = None
    name_eng: Optional[str] = None
    mapped_value: str
    description: Optional[str] = None
    order: int = 0
    raw_data: Optional[Dict[str, Any]] = None


# ==================== 同步相关 ====================


class MetadataSyncStats(BaseModel):
    """元数据同步统计"""

    video_codecs: int = Field(0, description="视频编码数量")
    audio_codecs: int = Field(0, description="音频编码数量")
    standards: int = Field(0, description="分辨率/标准数量")
    sources: int = Field(0, description="来源数量")
    languages: int = Field(0, description="语言数量")
    countries: int = Field(0, description="国家/地区数量")


class MetadataSyncResponse(BaseModel):
    """元数据同步响应"""

    success: bool
    message: str
    stats: MetadataSyncStats
    synced_types: List[str] = Field(description="已同步的元数据类型")


# ==================== 聚合响应 ====================


class AllMetadataResponse(BaseModel):
    """所有元数据响应"""

    site_id: int
    site_name: str
    video_codecs: List[PTVideoCodecResponse]
    audio_codecs: List[PTAudioCodecResponse]
    standards: List[PTStandardResponse]
    sources: List[PTSourceResponse]
    languages: List[PTLanguageResponse]
    countries: List[PTCountryResponse]
    total_count: int = Field(description="总元数据数量")


# ==================== 映射字典 ====================


class MetadataMappings(BaseModel):
    """元数据映射字典（供适配器使用）"""

    video_codecs: Dict[str, str] = Field(default_factory=dict, description="视频编码映射: ID -> mapped_value")
    audio_codecs: Dict[str, str] = Field(default_factory=dict, description="音频编码映射: ID -> mapped_value")
    standards: Dict[str, str] = Field(default_factory=dict, description="分辨率/标准映射: ID -> mapped_value")
    sources: Dict[str, str] = Field(default_factory=dict, description="来源映射: ID -> mapped_value")
    languages: Dict[str, str] = Field(default_factory=dict, description="语言映射: ID -> mapped_value")
    countries: Dict[str, str] = Field(default_factory=dict, description="国家/地区映射: ID -> mapped_value")
