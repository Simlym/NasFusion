# -*- coding: utf-8 -*-
"""
LLM 配置管理 API 接口
"""
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_admin_user, get_db
from app.models import User
from app.schemas.llm_config import (
    LLMConfigBrief,
    LLMConfigCreate,
    LLMConfigResponse,
    LLMConfigUpdate,
)
from app.services.llm_config_service import LLMConfigService
from app.constants.ai_agent import (
    LLM_PROVIDERS,
    LLM_PROVIDER_DISPLAY_NAMES,
    LLM_PROVIDER_TYPE_INFO,
    ZHIPU_MODELS,
    ZHIPU_MODEL_DISPLAY_NAMES,
    KIMI_MODELS,
    KIMI_MODEL_DISPLAY_NAMES,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/llm-configs", tags=["LLM 配置管理"])


@router.get("", response_model=List[LLMConfigResponse])
async def list_configs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """列出所有 LLM 配置"""
    configs = await LLMConfigService.list_all(db)
    return [LLMConfigResponse.model_validate(c) for c in configs]


@router.post("", response_model=LLMConfigResponse)
async def create_config(
    data: LLMConfigCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """创建 LLM 配置"""
    config = await LLMConfigService.create(db, data.model_dump())
    return LLMConfigResponse.model_validate(config)


@router.put("/{config_id}", response_model=LLMConfigResponse)
async def update_config(
    config_id: int,
    data: LLMConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """更新 LLM 配置"""
    config = await LLMConfigService.update(
        db, config_id, data.model_dump(exclude_unset=True)
    )
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="配置不存在")
    return LLMConfigResponse.model_validate(config)


@router.delete("/{config_id}")
async def delete_config(
    config_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """删除 LLM 配置"""
    success = await LLMConfigService.delete(db, config_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="配置不存在")
    return {"message": "配置已删除"}


@router.post("/{config_id}/test")
async def test_connection(
    config_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """测试 LLM 配置连接"""
    result = await LLMConfigService.test_connection(db, config_id)
    return result


@router.get("/provider-types")
async def get_provider_types(
    current_user: User = Depends(get_current_admin_user),
):
    """获取供应商类型信息"""
    providers = []
    for provider_key in LLM_PROVIDERS:
        info = LLM_PROVIDER_TYPE_INFO.get(provider_key, {})
        display_name = LLM_PROVIDER_DISPLAY_NAMES.get(provider_key, provider_key)
        models = []

        if provider_key == "zhipu":
            models = [
                {"id": m, "name": ZHIPU_MODEL_DISPLAY_NAMES.get(m, m)}
                for m in ZHIPU_MODELS
            ]
        elif provider_key == "kimi":
            models = [
                {"id": m, "name": KIMI_MODEL_DISPLAY_NAMES.get(m, m)}
                for m in KIMI_MODELS
            ]

        providers.append({
            "provider": provider_key,
            "display_name": display_name,
            "has_predefined_models": info.get("has_predefined_models", False),
            "default_api_base": info.get("default_api_base", ""),
            "models": models,
        })

    return {"providers": providers}
