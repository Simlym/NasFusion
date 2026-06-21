# -*- coding: utf-8 -*-
"""
Agent 文件工具沙箱

设计参考 MoviePilot 的 _check_local_file_access，但策略更严格：
NasFusion 的 Agent 工具**对所有用户**只允许访问沙箱根目录（DATA_DIR/agent）内的
文件，不开放管理员全盘访问。这样 read/write/edit/list 工具即使被 LLM 误用或被
提示注入，也无法触碰系统其它文件。

沙箱根目录用途：
- memory/   长期记忆（Agent 自己写的 *.md，供后续会话注入）
- 其它      Agent 临时草稿、用户让其保存的笔记等
"""
from pathlib import Path
from typing import Tuple

from app.core.config import settings


def get_sandbox_root() -> Path:
    """获取沙箱根目录（自动创建），所有文件工具只能在此目录树内操作。"""
    root = (Path(settings.DATA_DIR) / "agent").expanduser().resolve(strict=False)
    root.mkdir(parents=True, exist_ok=True)
    return root


def _is_within(path: Path, root: Path) -> bool:
    """判断 path 是否位于 root 目录内（含 root 本身）。"""
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def resolve_in_sandbox(path: str) -> Tuple[Path, str]:
    """
    将用户/LLM 传入的路径解析为沙箱内的绝对路径。

    - 相对路径基于沙箱根目录解析
    - 绝对路径必须落在沙箱内
    - 解析后做 `..`/符号链接展开再校验，杜绝逃逸

    Returns:
        (resolved_path, error)。error 非空表示拒绝访问，此时不应使用 resolved_path。
    """
    if not path or not path.strip():
        return Path(), "错误：路径不能为空"

    root = get_sandbox_root()
    raw = Path(path.strip())

    # 相对路径 → 基于沙箱根；绝对路径 → 原样（随后校验是否在沙箱内）
    candidate = raw if raw.is_absolute() else (root / raw)

    resolved = candidate.expanduser().resolve(strict=False)

    if not _is_within(resolved, root):
        return (
            resolved,
            f"拒绝访问：Agent 文件工具只能访问沙箱目录 {root} 内的文件，"
            f"请使用相对路径（如 memory/notes.md）或位于该目录下的绝对路径。",
        )

    return resolved, ""
