# -*- coding: utf-8 -*-
"""
AI Agent Skills 子模块

高级技能/工作流，区别于单步工具（tools）。
Skills 通过 @register_tool 注册到 ToolRegistry，LLM 可直接调用。
"""
from app.services.ai_agent.skills.subscribe_tv import SubscribeTVSkill

__all__ = [
    "SubscribeTVSkill",
]
