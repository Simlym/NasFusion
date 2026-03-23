# -*- coding: utf-8 -*-
"""
AI Agent Skills 子模块

高级技能/工作流，区别于单步工具（tools）。
Skills 通过 @register_tool 注册到 ToolRegistry，LLM 可直接调用。

说明文档见 SKILLS.md。
"""
from app.services.ai_agent.skills.subscribe_tv import SubscribeTVSkill
from app.services.ai_agent.skills.subscribe_movie import SubscribeMovieSkill
from app.services.ai_agent.skills.smart_download import SmartDownloadSkill
from app.services.ai_agent.skills.dashboard import DashboardSkill
from app.services.ai_agent.skills.trending_download import TrendingDownloadSkill

__all__ = [
    "SubscribeTVSkill",
    "SubscribeMovieSkill",
    "SmartDownloadSkill",
    "DashboardSkill",
    "TrendingDownloadSkill",
]
