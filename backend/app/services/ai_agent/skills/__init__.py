# -*- coding: utf-8 -*-
"""
AI Agent Skills 子模块

每个 Skill 包独立目录，结构：
  {name}/SKILL.md     —— 标准 frontmatter，给 LLM 的触发条件与参数说明
  {name}/scripts/     —— Python 实现
  {name}/__init__.py  —— 导出 Skill 类，触发 @register_tool 注册

新增 Skill 包：创建对应目录后在本文件 import 即可。
"""
from app.services.ai_agent.skills.nasfusion import (
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
