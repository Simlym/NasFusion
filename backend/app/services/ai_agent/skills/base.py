# -*- coding: utf-8 -*-
"""
AI Agent Skill 基类

Skill 是高级工作流，区别于单步 Tool：
- Tool：单一操作（搜索、下载、查询）
- Skill：编排多个 Tool，完成复合场景

使用方式与 Tool 相同（继承 BaseTool + @register_tool），
LLM 调用时自动路由，用户无感知。
"""
from app.services.ai_agent.tool_registry import BaseTool

# BaseSkill 即 BaseTool，通过继承关系标记为 Skill，便于未来按类型过滤
BaseSkill = BaseTool
