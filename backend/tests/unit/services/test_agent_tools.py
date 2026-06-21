# -*- coding: utf-8 -*-
"""
AI Agent 工具单元测试

覆盖：
- 文件工具沙箱（路径逃逸防护、相对路径解析）
- 文件工具 read/write/edit/list 往返
- PromptManager 记忆注入与 Skill 扫描
- 工具注册表（模糊匹配、未知工具）

文件工具会真实读写磁盘，故用 tmp_path 重定向沙箱根，避免污染 data/。
DB 相关用 AsyncMock，沿用项目既有风格（见 test_image_cache_optimization.py）。
"""
import os

os.environ.setdefault(
    "SECRET_KEY", "test_secret_key_must_be_at_least_32_bytes_long_for_security"
)

from pathlib import Path

import pytest

import app.services.ai_agent.tools  # noqa: F401 触发工具注册
from app.services.ai_agent.tool_registry import ToolRegistry
from app.services.ai_agent.tools import _fs_sandbox
from app.services.ai_agent.prompt_manager import PromptManager


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    """把沙箱根重定向到临时目录，并清掉 PromptManager 缓存。"""
    from app.core.config import settings

    monkeypatch.setattr(settings, "DATA_DIR", str(tmp_path), raising=False)
    PromptManager._cache.clear()
    PromptManager._mtime_cache.clear()
    return tmp_path / "agent"


# ==================== 沙箱路径安全 ====================

class TestSandbox:
    def test_relative_path_resolves_under_root(self, sandbox):
        resolved, err = _fs_sandbox.resolve_in_sandbox("memory/notes.md")
        assert err == ""
        assert resolved == (sandbox / "memory" / "notes.md").resolve()

    def test_empty_path_rejected(self, sandbox):
        _, err = _fs_sandbox.resolve_in_sandbox("   ")
        assert err

    def test_dotdot_escape_denied(self, sandbox):
        _, err = _fs_sandbox.resolve_in_sandbox("../../etc/passwd")
        assert err
        assert "沙箱" in err

    def test_absolute_outside_denied(self, sandbox):
        # 选一个绝不在临时沙箱内的绝对路径
        outside = str(Path(sandbox).anchor or "/") + "definitely_outside_xyz"
        _, err = _fs_sandbox.resolve_in_sandbox(outside)
        assert err

    def test_root_is_created(self, sandbox):
        root = _fs_sandbox.get_sandbox_root()
        assert root.exists() and root.is_dir()


# ==================== 文件工具往返 ====================

class TestFileTools:
    async def _exec(self, name, args):
        return await ToolRegistry.get_tool(name).execute(None, 1, args)

    async def test_write_read_roundtrip(self, sandbox):
        w = await self._exec("write_file", {"path": "memory/a.md", "content": "hello\nworld\n"})
        assert w["success"], w
        r = await self._exec("read_file", {"path": "memory/a.md"})
        assert r["success"]
        assert r["content"] == "hello\nworld\n"

    async def test_read_missing_file(self, sandbox):
        r = await self._exec("read_file", {"path": "memory/none.md"})
        assert r["success"] is False
        assert "不存在" in r["error"]

    async def test_edit_unique_replace(self, sandbox):
        await self._exec("write_file", {"path": "m.md", "content": "alpha beta gamma"})
        e = await self._exec("edit_file", {"path": "m.md", "old_string": "beta", "new_string": "BETA"})
        assert e["success"], e
        r = await self._exec("read_file", {"path": "m.md"})
        assert r["content"] == "alpha BETA gamma"

    async def test_edit_nonunique_without_replace_all_fails(self, sandbox):
        await self._exec("write_file", {"path": "m.md", "content": "x x x"})
        e = await self._exec("edit_file", {"path": "m.md", "old_string": "x", "new_string": "y"})
        assert e["success"] is False
        assert "不唯一" in e["error"]

    async def test_edit_replace_all(self, sandbox):
        await self._exec("write_file", {"path": "m.md", "content": "x x x"})
        e = await self._exec(
            "edit_file",
            {"path": "m.md", "old_string": "x", "new_string": "y", "replace_all": True},
        )
        assert e["success"]
        r = await self._exec("read_file", {"path": "m.md"})
        assert r["content"] == "y y y"

    async def test_edit_missing_old_string(self, sandbox):
        await self._exec("write_file", {"path": "m.md", "content": "abc"})
        e = await self._exec("edit_file", {"path": "m.md", "old_string": "zzz", "new_string": "q"})
        assert e["success"] is False

    async def test_list_directory(self, sandbox):
        await self._exec("write_file", {"path": "d/one.md", "content": "1"})
        await self._exec("write_file", {"path": "d/two.md", "content": "2"})
        l = await self._exec("list_directory", {"path": "d"})
        assert l["success"]
        assert l["total"] == 2
        assert {i["name"] for i in l["items"]} == {"one.md", "two.md"}

    async def test_write_escape_denied_via_tool(self, sandbox):
        w = await self._exec("write_file", {"path": "../escape.md", "content": "x"})
        assert w["success"] is False


# ==================== 记忆注入 ====================

class TestMemoryPrompt:
    async def test_empty_memory_returns_blank(self, sandbox):
        assert PromptManager.get_memory_prompt(7) == ""

    async def test_memory_injected_after_write(self, sandbox):
        await ToolRegistry.get_tool("write_file").execute(
            None, 7, {"path": "memory/user_7/pref.md", "content": "- 喜欢科幻\n"}
        )
        mp = PromptManager.get_memory_prompt(7)
        assert "科幻" in mp
        assert "长期记忆" in mp

    async def test_memory_is_per_user(self, sandbox):
        await ToolRegistry.get_tool("write_file").execute(
            None, 7, {"path": "memory/user_7/pref.md", "content": "user7 secret"}
        )
        # 另一个用户读不到
        assert "user7" not in PromptManager.get_memory_prompt(8)

    def test_memory_relpath(self):
        assert PromptManager.get_memory_relpath(42) == "memory/user_42"

    def test_memory_truncated_when_oversized(self, sandbox, monkeypatch):
        from app.services.ai_agent import prompt_manager as pm

        monkeypatch.setattr(pm, "MAX_MEMORY_CHARS", 50, raising=False)
        root = _fs_sandbox.get_sandbox_root() / "memory" / "user_9"
        root.mkdir(parents=True, exist_ok=True)
        (root / "big.md").write_text("A" * 500, encoding="utf-8")
        mp = PromptManager.get_memory_prompt(9)
        assert "截断" in mp


# ==================== Skill 扫描 ====================

class TestSkillsPrompt:
    def test_builtin_skills_scanned(self, sandbox):
        prompt = PromptManager.get_skills_prompt()
        # 内置 nasfusion skill 应出现
        assert "nasfusion" in prompt

    def test_sandbox_skill_scanned(self, sandbox):
        skill_dir = _fs_sandbox.get_sandbox_root() / "skills" / "custom"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(
            "---\nname: custom_skill\ndescription: 用户自定义\n---\nbody",
            encoding="utf-8",
        )
        PromptManager._cache.clear()
        prompt = PromptManager.get_skills_prompt()
        assert "custom_skill" in prompt


# ==================== 工具注册表 ====================

class TestToolRegistry:
    def test_new_tools_registered(self):
        names = ToolRegistry.get_tool_names()
        for n in ["site_manage", "organize_media", "watch_history",
                  "read_file", "write_file", "edit_file", "list_directory"]:
            assert n in names, f"{n} 未注册"

    def test_resolve_fuzzy_name(self):
        # KEYWORD_MAP 把 'search' 纠正到 resource_search
        assert ToolRegistry.resolve_tool_name("search_something") == "resource_search"

    def test_resolve_exact_name(self):
        assert ToolRegistry.resolve_tool_name("write_file") == "write_file"

    def test_resolve_unknown_returns_none(self):
        assert ToolRegistry.resolve_tool_name("totally_made_up_xyz") is None

    async def test_execute_unknown_tool(self):
        res = await ToolRegistry.execute_tool("no_such_tool", None, 1, {})
        assert res["success"] is False
        assert "未知工具" in res["error"]
