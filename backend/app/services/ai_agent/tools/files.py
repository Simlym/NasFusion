# -*- coding: utf-8 -*-
"""
文件工具（沙箱内）

提供 Agent 在沙箱目录（DATA_DIR/agent）内的文件读写能力，主要用途：
- 让 Agent 自己维护长期记忆（memory/*.md）
- 保存用户让其记录的笔记、草稿

安全：所有路径都经 _fs_sandbox.resolve_in_sandbox 校验，无法逃逸到沙箱外。
设计参考 MoviePilot 的 read_file/write_file/edit_file/list_directory，
但收紧为「全员仅沙箱」策略。
"""
import logging
from datetime import datetime
from typing import Any, Dict

from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.ai_agent import (
    AGENT_TOOL_LIST_DIRECTORY,
    AGENT_TOOL_READ_FILE,
    AGENT_TOOL_WRITE_FILE,
    AGENT_TOOL_EDIT_FILE,
)
from app.services.ai_agent.tool_registry import BaseTool, register_tool
from app.services.ai_agent.tools._fs_sandbox import (
    get_sandbox_root,
    resolve_in_sandbox,
)


logger = logging.getLogger(__name__)

# 读取上限 50KB，超出截断并提示分段读取
MAX_READ_SIZE = 50 * 1024
# 写入上限 1MB，避免误写超大内容
MAX_WRITE_SIZE = 1024 * 1024
# 目录列举最多返回条数
MAX_LIST_ITEMS = 50


def _rel(path) -> str:
    """返回相对沙箱根的展示路径。"""
    try:
        return str(path.relative_to(get_sandbox_root()))
    except ValueError:
        return str(path)


@register_tool
class ListDirectoryTool(BaseTool):
    """列出沙箱目录内容"""

    name = AGENT_TOOL_LIST_DIRECTORY
    description = (
        "列出 Agent 沙箱目录内的文件和子目录（含类型、大小、修改时间）。"
        "沙箱根目录用于存放 Agent 记忆（memory/）与笔记。"
        "path 为相对沙箱根的路径，留空或传 '.' 表示根目录。"
    )

    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "相对沙箱根的目录路径，留空表示根目录",
                "default": ".",
            },
        },
        "required": [],
    }

    @classmethod
    async def execute(
        cls, db: AsyncSession, user_id: int, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        resolved, error = resolve_in_sandbox(arguments.get("path") or ".")
        if error:
            return {"success": False, "error": error}

        if not resolved.exists():
            return {"success": False, "error": f"目录不存在: {_rel(resolved)}"}
        if not resolved.is_dir():
            return {"success": False, "error": f"不是目录: {_rel(resolved)}"}

        entries = sorted(
            resolved.iterdir(),
            key=lambda p: (0 if p.is_dir() else 1, p.name.lower()),
        )
        total = len(entries)
        items = []
        for p in entries[:MAX_LIST_ITEMS]:
            try:
                stat = p.stat()
                mtime = datetime.fromtimestamp(stat.st_mtime).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
                size = stat.st_size if p.is_file() else None
            except OSError:
                mtime, size = None, None
            items.append(
                {
                    "name": p.name,
                    "type": "dir" if p.is_dir() else "file",
                    "path": _rel(p),
                    "size": size,
                    "modify_time": mtime,
                }
            )

        message = f"目录 {_rel(resolved)} 共 {total} 项"
        if total > MAX_LIST_ITEMS:
            message += f"，仅显示前 {MAX_LIST_ITEMS} 项"
        if total == 0:
            message = f"目录 {_rel(resolved)} 为空"

        return {"success": True, "message": message, "total": total, "items": items}


@register_tool
class ReadFileTool(BaseTool):
    """读取沙箱内文本文件"""

    name = AGENT_TOOL_READ_FILE
    description = (
        "读取沙箱内文本文件内容，支持按行范围读取（start_line/end_line，1 起始含端点）。"
        "单次最多读取 50KB，超出会被截断并提示分段读取。"
        "path 为相对沙箱根的路径（如 memory/preferences.md）。"
    )

    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "相对沙箱根的文件路径",
            },
            "start_line": {
                "type": "integer",
                "description": "起始行号（1 起始，含）",
            },
            "end_line": {
                "type": "integer",
                "description": "结束行号（1 起始，含）",
            },
        },
        "required": ["path"],
    }

    @classmethod
    async def execute(
        cls, db: AsyncSession, user_id: int, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        resolved, error = resolve_in_sandbox(arguments.get("path", ""))
        if error:
            return {"success": False, "error": error}

        if not resolved.exists():
            return {"success": False, "error": f"文件不存在: {_rel(resolved)}"}
        if not resolved.is_file():
            return {"success": False, "error": f"不是文件: {_rel(resolved)}"}

        try:
            content = resolved.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return {"success": False, "error": "不是文本文件，无法读取"}
        except OSError as e:
            return {"success": False, "error": f"读取失败: {e}"}

        start_line = arguments.get("start_line")
        end_line = arguments.get("end_line")
        if start_line is not None or end_line is not None:
            lines = content.splitlines(keepends=True)
            total = len(lines)
            s = (start_line - 1) if start_line and start_line >= 1 else 0
            e = end_line if end_line and end_line >= 1 else total
            s = max(0, min(s, total))
            e = max(s, min(e, total))
            content = "".join(lines[s:e])

        truncated = False
        content_bytes = content.encode("utf-8")
        if len(content_bytes) > MAX_READ_SIZE:
            content = content_bytes[:MAX_READ_SIZE].decode("utf-8", errors="ignore")
            truncated = True

        return {
            "success": True,
            "message": f"已读取 {_rel(resolved)}"
            + ("（已截断至 50KB，请用 start_line/end_line 分段读取）" if truncated else ""),
            "path": _rel(resolved),
            "content": content,
            "truncated": truncated,
        }


@register_tool
class WriteFileTool(BaseTool):
    """写入沙箱内文件（覆盖）"""

    name = AGENT_TOOL_WRITE_FILE
    description = (
        "在沙箱内创建或覆盖文件，写入完整内容（已存在则整体替换）。"
        "用于新建记忆文件或整篇重写。若只想改动局部，请用 edit_file。"
        "path 为相对沙箱根的路径，缺失的父目录会自动创建。"
    )

    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "相对沙箱根的文件路径（如 memory/preferences.md）",
            },
            "content": {
                "type": "string",
                "description": "要写入的完整文件内容",
            },
        },
        "required": ["path", "content"],
    }

    @classmethod
    async def execute(
        cls, db: AsyncSession, user_id: int, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        resolved, error = resolve_in_sandbox(arguments.get("path", ""))
        if error:
            return {"success": False, "error": error}

        content = arguments.get("content", "")
        if len(content.encode("utf-8")) > MAX_WRITE_SIZE:
            return {"success": False, "error": "内容超过 1MB 写入上限"}

        if resolved.exists() and resolved.is_dir():
            return {"success": False, "error": f"目标是目录，无法写入: {_rel(resolved)}"}

        try:
            resolved.parent.mkdir(parents=True, exist_ok=True)
            existed = resolved.exists()
            resolved.write_text(content, encoding="utf-8")
        except OSError as e:
            return {"success": False, "error": f"写入失败: {e}"}

        return {
            "success": True,
            "message": f"已{'覆盖' if existed else '创建'}文件 {_rel(resolved)}（{len(content)} 字符）",
            "path": _rel(resolved),
        }


@register_tool
class EditFileTool(BaseTool):
    """精确字符串替换编辑沙箱内文件"""

    name = AGENT_TOOL_EDIT_FILE
    description = (
        "对沙箱内已有文件做精确字符串替换：将 old_string 替换为 new_string。"
        "old_string 必须在文件中唯一出现（否则报错，避免误改）；"
        "若要替换全部出现，置 replace_all=true。适合对记忆文件做局部更新。"
    )

    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "相对沙箱根的文件路径",
            },
            "old_string": {
                "type": "string",
                "description": "要被替换的原文（需与文件内容精确匹配）",
            },
            "new_string": {
                "type": "string",
                "description": "替换后的新文本",
            },
            "replace_all": {
                "type": "boolean",
                "description": "是否替换所有出现",
                "default": False,
            },
        },
        "required": ["path", "old_string", "new_string"],
    }

    @classmethod
    async def execute(
        cls, db: AsyncSession, user_id: int, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        resolved, error = resolve_in_sandbox(arguments.get("path", ""))
        if error:
            return {"success": False, "error": error}

        if not resolved.exists() or not resolved.is_file():
            return {"success": False, "error": f"文件不存在: {_rel(resolved)}"}

        old_string = arguments.get("old_string", "")
        new_string = arguments.get("new_string", "")
        replace_all = arguments.get("replace_all", False)

        if old_string == "":
            return {"success": False, "error": "old_string 不能为空"}
        if old_string == new_string:
            return {"success": False, "error": "old_string 与 new_string 相同，无需编辑"}

        try:
            content = resolved.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError) as e:
            return {"success": False, "error": f"读取失败: {e}"}

        count = content.count(old_string)
        if count == 0:
            return {"success": False, "error": "未找到 old_string，请确认内容精确匹配"}
        if count > 1 and not replace_all:
            return {
                "success": False,
                "error": f"old_string 出现 {count} 次，不唯一。请扩大上下文使其唯一，或置 replace_all=true",
            }

        new_content = content.replace(old_string, new_string)
        try:
            resolved.write_text(new_content, encoding="utf-8")
        except OSError as e:
            return {"success": False, "error": f"写入失败: {e}"}

        replaced = count if replace_all else 1
        return {
            "success": True,
            "message": f"已编辑 {_rel(resolved)}，替换 {replaced} 处",
            "path": _rel(resolved),
        }
