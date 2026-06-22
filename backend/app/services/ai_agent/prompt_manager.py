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

PROMPTS_DIR = Path(__file__).parent / "prompts"
SKILLS_DIR = Path(__file__).parent / "skills"

# 单个用户记忆注入 system prompt 的总量上限（字符），超出截断防爆 context
MAX_MEMORY_CHARS = 4000


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

    @classmethod
    def get_skills_prompt(cls) -> str:
        """
        扫描 SKILL.md，提取 frontmatter description 注入系统提示词。

        来源两处：
        1. 内置 skills/*/SKILL.md（随代码发布）
        2. 用户沙箱 data/agent/skills/*/SKILL.md（用户自定义，无需改代码）
        """
        lines = []
        seen = set()
        try:
            skill_dirs = [SKILLS_DIR.glob("*/SKILL.md")]
            # 沙箱内用户自定义 skill（延迟导入避免循环依赖）
            try:
                from app.services.ai_agent.tools._fs_sandbox import get_sandbox_root

                user_skills = get_sandbox_root() / "skills"
                if user_skills.exists():
                    skill_dirs.append(user_skills.glob("*/SKILL.md"))
            except Exception:
                logger.debug("沙箱 skills 目录不可用，跳过")

            for source in skill_dirs:
                for skill_md in sorted(source):
                    content = skill_md.read_text(encoding="utf-8")
                    data = cls._parse_frontmatter(content)
                    name = data.get("name", "")
                    description = data.get("description", "")
                    if name and description and name not in seen:
                        seen.add(name)
                        lines.append(f"- {name}: {description}")
        except Exception:
            logger.exception("读取 SKILL.md 失败")
        if not lines:
            return ""
        return "## 可用 Skills\n" + "\n".join(lines)

    @classmethod
    def get_safety_prompt(cls) -> str:
        """危险操作二次确认协议，始终注入（即使用户自定义了 system_prompt）。"""
        return (
            "## 危险操作确认协议\n"
            "部分工具涉及删除/清理等不可逆操作。当你调用这类工具后，若返回 "
            "`requires_confirmation=true`，表示该操作**尚未执行**，须先获得用户确认：\n"
            "1. 必须把返回的 `confirmation_prompt` **原样转达用户**，等待其明确同意（如「确认」「是」）。\n"
            "2. 用户明确同意前，**禁止重复调用该工具，也不得自行编造确认令牌**。\n"
            "3. 用户同意后，再次调用同一工具，**保持其余参数完全一致**，并附带 "
            "`__confirm__=<confirmation_token>`（用返回的令牌原样填入）。\n"
            "4. 用户拒绝或未明确同意时，放弃该操作并告知用户已取消。"
        )

    @classmethod
    def get_memory_prompt(cls, user_id: int) -> str:
        """
        读取用户长期记忆并拼成 system prompt 片段。

        记忆是 Agent 自己用 write_file/edit_file 写在沙箱
        data/agent/memory/user_{id}/*.md 下的 Markdown，
        供后续会话注入，实现「自学习」用户偏好。超量截断。
        """
        try:
            from app.services.ai_agent.tools._fs_sandbox import get_sandbox_root

            mem_dir = get_sandbox_root() / "memory" / f"user_{user_id}"
            if not mem_dir.exists():
                return ""

            blocks = []
            total = 0
            for md in sorted(mem_dir.glob("*.md")):
                try:
                    text = md.read_text(encoding="utf-8").strip()
                except OSError:
                    continue
                if not text:
                    continue
                block = f"### {md.stem}\n{text}"
                if total + len(block) > MAX_MEMORY_CHARS:
                    blocks.append("（记忆内容较多，已截断；可用 read_file 读取完整记忆）")
                    break
                blocks.append(block)
                total += len(block)

            if not blocks:
                return ""
            return "## 关于用户的长期记忆\n" + "\n\n".join(blocks)
        except Exception:
            logger.exception("读取用户记忆失败")
            return ""

    @staticmethod
    def get_memory_relpath(user_id: int) -> str:
        """返回该用户记忆目录的沙箱相对路径，用于在 system prompt 告知 Agent 写入位置。"""
        return f"memory/user_{user_id}"

    @staticmethod
    def _parse_frontmatter(content: str) -> dict:
        """解析 YAML frontmatter（--- 包裹的块）"""
        if not content.startswith("---"):
            return {}
        end = content.find("---", 3)
        if end == -1:
            return {}
        try:
            return yaml.safe_load(content[3:end]) or {}
        except Exception:
            return {}
