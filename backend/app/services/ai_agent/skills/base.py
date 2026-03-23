# -*- coding: utf-8 -*-
"""
AI Agent Skill 基类

Skill 是高级工作流，区别于单步 Tool：
- Tool：单一操作（搜索、下载、查询）
- Skill：编排多个 Tool，完成复合场景（减少 LLM 多轮调用）

目录结构规范：
  skills/SKILLS.md          —— 全部 Skill 的功能说明、参数、使用示例（人类查阅）
  skills/base.py            —— 本文件，Skill 基类
  skills/{name}.py          —— 各 Skill 实现（name/description/parameters 内联在类属性中）
  skills/__init__.py        —— 导出所有 Skill，触发 @register_tool 注册

每个 Skill 文件结构与 Tool 一致：继承 BaseSkill + @register_tool 装饰器。
"""
from app.services.ai_agent.tool_registry import BaseTool

# BaseSkill 即 BaseTool，保留独立名称便于 isinstance 检查和后续扩展
BaseSkill = BaseTool
