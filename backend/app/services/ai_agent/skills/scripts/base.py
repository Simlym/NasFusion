# -*- coding: utf-8 -*-
"""
AI Agent Skill 基类

Skill 是高级工作流，区别于单步 Tool：
- Tool：单一操作（搜索、下载、查询）
- Skill：编排多个 Tool，完成复合场景（减少 LLM 多轮调用）

目录结构规范：
  skills/skill.md           —— 给 LLM 的 Skill 说明（触发词、参数、适用场景）
  skills/scripts/base.py    —— 本文件，Skill 基类
  skills/scripts/{name}.py  —— 各 Skill 实现
  skills/__init__.py        —— 导出所有 Skill，触发 @register_tool 注册
"""
from app.services.ai_agent.tool_registry import BaseTool

# BaseSkill 即 BaseTool，保留独立名称便于 isinstance 检查和后续扩展
BaseSkill = BaseTool
