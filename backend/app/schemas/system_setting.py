# -*- coding: utf-8 -*-
"""
系统设置Schema
"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class SystemSettingBase(BaseModel):
    """系统设置基础Schema"""

    category: str = Field(..., description="设置分类")
    key: str = Field(..., description="设置键")
    value: Optional[str] = Field(None, description="设置值")
    description: Optional[str] = Field(None, description="设置描述")
    is_active: bool = Field(True, description="是否启用")


class SystemSettingCreate(SystemSettingBase):
    """创建系统设置"""

    pass


class SystemSettingUpdate(BaseModel):
    """更新系统设置"""

    value: Optional[str] = Field(None, description="设置值")
    description: Optional[str] = Field(None, description="设置描述")
    is_active: Optional[bool] = Field(None, description="是否启用")


class SystemSettingResponse(SystemSettingBase):
    """系统设置响应"""

    id: int
    is_encrypted: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SystemSettingList(BaseModel):
    """系统设置列表响应"""

    total: int
    items: list[SystemSettingResponse]
