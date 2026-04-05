# -*- coding: utf-8 -*-
"""
LLM 配置 Pydantic 模型
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.base import BaseResponseSchema


class LLMConfigCreate(BaseModel):
    """创建 LLM 配置"""
    name: str = Field(..., max_length=100, description="配置名称")
    provider: str = Field(..., max_length=50, description="LLM供应商")
    api_key: str = Field(..., description="API密钥")
    api_base: Optional[str] = Field(default=None, max_length=500, description="API基础URL")
    proxy: Optional[str] = Field(default=None, max_length=255, description="代理服务器URL")
    model: str = Field(..., max_length=100, description="默认模型")
    default_temperature: str = Field(default="0.7", max_length=10, description="默认温度")
    default_max_tokens: int = Field(default=2048, description="默认最大Token数")
    default_top_p: str = Field(default="0.9", max_length=10, description="默认Top-P")
    is_enabled: bool = Field(default=True, description="是否启用")
    sort_order: int = Field(default=0, description="排序顺序")


class LLMConfigUpdate(BaseModel):
    """更新 LLM 配置"""
    name: Optional[str] = Field(default=None, max_length=100)
    provider: Optional[str] = Field(default=None, max_length=50)
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    proxy: Optional[str] = None
    model: Optional[str] = Field(default=None, max_length=100)
    default_temperature: Optional[str] = None
    default_max_tokens: Optional[int] = None
    default_top_p: Optional[str] = None
    is_enabled: Optional[bool] = None
    sort_order: Optional[int] = None


class LLMConfigResponse(BaseResponseSchema):
    """LLM 配置响应（不含 api_key）"""
    id: int
    name: str
    provider: str
    api_base: Optional[str]
    proxy: Optional[str]
    model: str
    default_temperature: str
    default_max_tokens: int
    default_top_p: str
    is_enabled: bool
    sort_order: int
    last_test_at: Optional[datetime]
    last_test_result: Optional[str]


class LLMConfigBrief(BaseModel):
    """LLM 配置简要信息（给 AI 助手选择用）"""
    id: int
    name: str
    provider: str
    model: str
    is_enabled: bool

    model_config = {"from_attributes": True}
