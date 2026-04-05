# -*- coding: utf-8 -*-
"""
LLM 配置管理服务

管理员维护全局 LLM 供应商配置
"""
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.llm import get_llm_adapter
from app.models.llm_config import LLMConfig
from app.utils.encryption import encryption_util
from app.utils.timezone import now

logger = logging.getLogger(__name__)


class LLMConfigService:
    """LLM 配置管理服务"""

    @staticmethod
    async def list_all(db: AsyncSession) -> List[LLMConfig]:
        """列出所有 LLM 配置"""
        result = await db.execute(
            select(LLMConfig).order_by(LLMConfig.sort_order, LLMConfig.created_at)
        )
        return list(result.scalars().all())

    @staticmethod
    async def list_enabled(db: AsyncSession) -> List[LLMConfig]:
        """列出已启用的 LLM 配置"""
        result = await db.execute(
            select(LLMConfig)
            .where(LLMConfig.is_enabled == True)  # noqa: E712
            .order_by(LLMConfig.sort_order, LLMConfig.created_at)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_by_id(db: AsyncSession, config_id: int) -> Optional[LLMConfig]:
        """获取指定 LLM 配置"""
        result = await db.execute(
            select(LLMConfig).where(LLMConfig.id == config_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create(db: AsyncSession, data: Dict[str, Any]) -> LLMConfig:
        """创建 LLM 配置"""
        # 加密 api_key
        raw_api_key = data.pop("api_key", "")
        encrypted_key = encryption_util.encrypt(raw_api_key)

        config = LLMConfig(api_key=encrypted_key, **data)
        db.add(config)
        await db.commit()
        await db.refresh(config)
        return config

    @staticmethod
    async def update(db: AsyncSession, config_id: int, data: Dict[str, Any]) -> Optional[LLMConfig]:
        """更新 LLM 配置"""
        config = await LLMConfigService.get_by_id(db, config_id)
        if not config:
            return None

        # 如果更新了 api_key，加密存储
        raw_api_key = data.pop("api_key", None)
        if raw_api_key is not None:
            config.api_key = encryption_util.encrypt(raw_api_key)

        for key, value in data.items():
            if hasattr(config, key) and value is not None:
                setattr(config, key, value)

        await db.commit()
        await db.refresh(config)
        return config

    @staticmethod
    async def delete(db: AsyncSession, config_id: int) -> bool:
        """删除 LLM 配置"""
        config = await LLMConfigService.get_by_id(db, config_id)
        if not config:
            return False

        await db.delete(config)
        await db.commit()
        return True

    @staticmethod
    async def test_connection(db: AsyncSession, config_id: int) -> Dict[str, Any]:
        """测试 LLM 配置连接"""
        config = await LLMConfigService.get_by_id(db, config_id)
        if not config:
            return {"success": False, "message": "配置不存在"}

        # 解密 api_key
        api_key = encryption_util.decrypt(config.api_key)
        if not api_key:
            return {"success": False, "message": "API Key 解密失败"}

        try:
            adapter = get_llm_adapter(
                config.provider,
                {
                    "api_key": api_key,
                    "api_base": config.api_base,
                    "proxy": config.proxy,
                    "model": config.model,
                }
            )
            result = await adapter.test_connection()

            # 更新测试结果
            config.last_test_at = now()
            config.last_test_result = result.get("message", "测试成功" if result.get("success") else "测试失败")
            await db.commit()

            return result
        except Exception as e:
            error_msg = f"连接失败: {str(e)}"
            config.last_test_at = now()
            config.last_test_result = error_msg
            await db.commit()

            return {"success": False, "message": error_msg, "latency_ms": 0}

    @staticmethod
    async def get_resolved_config(db: AsyncSession, config_id: int) -> Optional[Dict[str, Any]]:
        """
        获取解密后的 LLM 配置字典

        用于 agent_service 创建 adapter 实例
        """
        config = await LLMConfigService.get_by_id(db, config_id)
        if not config:
            return None

        api_key = encryption_util.decrypt(config.api_key)
        if not api_key:
            return None

        return {
            "provider": config.provider,
            "api_key": api_key,
            "api_base": config.api_base,
            "proxy": config.proxy,
            "model": config.model,
            "temperature": float(config.default_temperature),
            "max_tokens": config.default_max_tokens,
            "top_p": float(config.default_top_p),
        }
