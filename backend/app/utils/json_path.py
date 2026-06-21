# -*- coding: utf-8 -*-
"""
JSON 路径提取与模板渲染工具

供 GenericJSONAPIAdapter 等配置驱动适配器使用：
- get_by_path: 按点号路径从嵌套 dict/list 取值（如 "data.torrents"）
- render_template: 渲染 {{var}} 占位符
- render_template_obj: 递归渲染 dict/list 中的模板字符串
"""
import re
from typing import Any, Dict, Optional

_TEMPLATE_RE = re.compile(r"\{\{\s*(\w+)\s*\}\}")


def get_by_path(obj: Any, path: str, default: Any = None) -> Any:
    """
    按点号路径从嵌套结构取值。

    支持：
    - dict 键：a.b.c
    - list 下标：a.0.b

    Args:
        obj: 源对象（dict/list）
        path: 点号路径；空字符串返回 obj 本身
        default: 取不到时的返回值

    Returns:
        取到的值，或 default
    """
    if not path:
        return obj
    cur = obj
    for part in path.split("."):
        if cur is None:
            return default
        if isinstance(cur, dict):
            if part not in cur:
                return default
            cur = cur[part]
        elif isinstance(cur, (list, tuple)):
            try:
                idx = int(part)
            except ValueError:
                return default
            if idx < 0 or idx >= len(cur):
                return default
            cur = cur[idx]
        else:
            return default
    return cur


def render_template(text: str, context: Dict[str, Any]) -> str:
    """
    渲染字符串模板中的 {{var}} 占位符。

    未在 context 中的变量替换为空字符串。
    """
    if not text or "{{" not in text:
        return text

    def _sub(match: "re.Match") -> str:
        key = match.group(1)
        val = context.get(key, "")
        return "" if val is None else str(val)

    return _TEMPLATE_RE.sub(_sub, text)


def render_template_obj(obj: Any, context: Dict[str, Any]) -> Any:
    """
    递归渲染 dict/list 中的模板字符串。

    - 字符串：若整体就是单个 {{var}}，保留 context 中变量的原始类型（int/list 等）；
      否则做字符串插值。
    - dict/list：递归处理。
    - 其他：原样返回。
    """
    if isinstance(obj, str):
        whole = _TEMPLATE_RE.fullmatch(obj.strip())
        if whole:
            return context.get(whole.group(1))
        return render_template(obj, context)
    if isinstance(obj, dict):
        return {k: render_template_obj(v, context) for k, v in obj.items()}
    if isinstance(obj, list):
        return [render_template_obj(v, context) for v in obj]
    return obj


def safe_int(value: Any, default: int = 0) -> int:
    """宽松地把值转为 int（处理 None/带逗号字符串/浮点）。"""
    if value is None:
        return default
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    try:
        return int(str(value).replace(",", "").strip())
    except (ValueError, TypeError):
        return default


def safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    """宽松地把值转为 float。"""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).replace(",", "").strip())
    except (ValueError, TypeError):
        return default


__all__ = [
    "get_by_path",
    "render_template",
    "render_template_obj",
    "safe_int",
    "safe_float",
]
