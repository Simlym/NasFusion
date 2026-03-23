# -*- coding: utf-8 -*-
"""
AI Agent 提示词管理器

从 backend/app/prompts/*.yaml 加载提示词，支持：
- Jinja2 模板变量（current_time、username 等）
- 文件热加载（修改 YAML 无需重启服务）
- 降级到硬编码常量（YAML 文件不存在时）
"""
import logging
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from jinja2 import BaseLoader, Environment

from app.constants.ai_agent import DEFAULT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"


class PromptManager:
    """提示词管理器（热加载 + Jinja2 模板）"""

    _cache: Dict[str, Dict] = {}
    _mtime_cache: Dict[str, float] = {}
    _jinja_env = Environment(loader=BaseLoader(), keep_trailing_newline=True)

    @classmethod
    def _load_yaml(cls, name: str) -> Optional[Dict]:
        """加载 YAML 文件，自动检测文件修改时间以热加载"""
        path = PROMPTS_DIR / f"{name}.yaml"
        if not path.exists():
            return None

        try:
            mtime = path.stat().st_mtime
            if name in cls._cache and cls._mtime_cache.get(name) == mtime:
                return cls._cache[name]

            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            cls._cache[name] = data
            cls._mtime_cache[name] = mtime
            logger.debug(f"已加载提示词文件: {path.name}")
            return data

        except Exception:
            logger.exception(f"加载提示词文件失败: {path}")
            return None

    @classmethod
    def get(cls, name: str, variables: Optional[Dict[str, Any]] = None) -> str:
        """
        获取提示词，并渲染 Jinja2 模板变量。

        Args:
            name: 提示词名称（对应 prompts/{name}.yaml 的 content 字段）
            variables: Jinja2 模板变量，如 {"current_time": "2026-03-23 10:00", "username": "alice"}

        Returns:
            渲染后的提示词字符串。文件不存在时降级到硬编码常量。
        """
        data = cls._load_yaml(name)
        if not data:
            # 降级：使用硬编码常量
            if name == "system":
                return DEFAULT_SYSTEM_PROMPT
            return ""

        content: str = data.get("content", "")
        if not content:
            return ""

        if variables:
            try:
                template = cls._jinja_env.from_string(content)
                content = template.render(**variables)
            except Exception:
                logger.exception(f"渲染提示词模板失败: {name}")

        return content.strip()

    @classmethod
    def get_system_prompt(cls, variables: Optional[Dict[str, Any]] = None) -> str:
        """获取系统提示词（快捷方法）"""
        return cls.get("system", variables)
