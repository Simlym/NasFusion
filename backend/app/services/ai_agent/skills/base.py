# -*- coding: utf-8 -*-
"""
AI Agent Skill 基类

Skill 是高级工作流，区别于单步 Tool：
- Tool：单一操作（搜索、下载、查询）
- Skill：编排多个 Tool，完成复合场景

每个 Skill 对应两个文件（以 subscribe_tv 为例）：
  skills/subscribe_tv.yaml   —— 描述文件（name、description、parameters、examples）
  skills/subscribe_tv.py     —— 执行逻辑（只含 execute 方法）

get_definition() 自动从同名 YAML 文件加载描述，实现描述与逻辑分离。
"""
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from app.adapters.llm.base import ToolDefinition
from app.services.ai_agent.tool_registry import BaseTool


class BaseSkill(BaseTool):
    """
    Skill 基类

    子类只需实现 execute()，其余元数据（name、description、parameters）
    从同目录的 {module_name}.yaml 文件加载，无需在 Python 代码中硬编码。
    """

    @classmethod
    def _load_descriptor(cls) -> Optional[Dict[str, Any]]:
        """从与 Python 文件同名的 YAML 文件加载描述"""
        module = sys.modules.get(cls.__module__)
        if not module or not getattr(module, "__file__", None):
            return None

        yaml_path = Path(module.__file__).with_suffix(".yaml")
        if not yaml_path.exists():
            return None

        try:
            with open(yaml_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception:
            return None

    @classmethod
    def get_definition(cls) -> ToolDefinition:
        """优先从 YAML 描述文件读取，降级到类属性"""
        descriptor = cls._load_descriptor()
        if descriptor:
            return ToolDefinition(
                name=descriptor.get("name", cls.name),
                description=str(descriptor.get("description", cls.description)).strip(),
                parameters=descriptor.get("parameters", cls.parameters),
            )
        return super().get_definition()
