# -*- coding: utf-8 -*-
"""
AI Agent Skills 子模块

高级技能/工作流，区别于单步工具（tools）。
Skills 通过 @register_tool 注册到 ToolRegistry，LLM 可直接调用。

skill.md  —— 给 LLM 的触发条件与参数说明，由 PromptManager 注入系统提示词
scripts/  —— 各 Skill 的 Python 实现
"""
from app.services.ai_agent.skills.scripts import (
    SubscribeTVSkill,
    SubscribeMovieSkill,
    SmartDownloadSkill,
    DashboardSkill,
    TrendingDownloadSkill,
)

__all__ = [
    "SubscribeTVSkill",
    "SubscribeMovieSkill",
    "SmartDownloadSkill",
    "DashboardSkill",
    "TrendingDownloadSkill",
]
