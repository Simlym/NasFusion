# -*- coding: utf-8 -*-
"""
版本服务

提供当前版本号，并通过 GitHub Releases API 检查是否有新版本。
GitHub 查询结果带内存缓存（默认 6 小时），避免频繁外网请求；
外网失败时静默降级（不影响主流程），仅返回当前版本。
"""
import asyncio
import logging
import re
from typing import Optional

import httpx

from app.core.config import settings
from app.utils.timezone import now

logger = logging.getLogger(__name__)

# GitHub 仓库（owner/repo）
GITHUB_REPO = "Simlym/NasFusion"
GITHUB_LATEST_RELEASE_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
RELEASE_PAGE_URL = f"https://github.com/{GITHUB_REPO}/releases/latest"

# 缓存有效期（秒）
_CACHE_TTL_SECONDS = 6 * 3600
# 外网请求超时（秒）
_REQUEST_TIMEOUT = 8.0


class _LatestCache:
    """最新版本查询结果的内存缓存"""

    def __init__(self) -> None:
        self.tag: Optional[str] = None
        self.release_url: Optional[str] = None
        self.fetched_at_ts: float = 0.0
        self._lock = asyncio.Lock()

    def is_fresh(self) -> bool:
        return self.tag is not None and (now().timestamp() - self.fetched_at_ts) < _CACHE_TTL_SECONDS


_cache = _LatestCache()


def get_current_version() -> str:
    """当前运行版本（镜像构建时由 Git tag 注入，本地源码运行为 dev）"""
    return settings.APP_VERSION


def _normalize(version: str) -> str:
    """去掉前缀 v / 空白，便于比较。如 'v0.2.0' -> '0.2.0'"""
    return version.strip().lstrip("vV") if version else ""


def _parse(version: str) -> Optional[tuple]:
    """解析为可比较的数字元组；非标准版本（如 dev/edge）返回 None"""
    norm = _normalize(version)
    if not re.fullmatch(r"\d+(\.\d+)*", norm):
        return None
    return tuple(int(p) for p in norm.split("."))


def is_newer(latest: str, current: str) -> bool:
    """latest 是否比 current 新；任一无法解析则视为「无更新」（保守）"""
    lt, ct = _parse(latest), _parse(current)
    if lt is None or ct is None:
        return False
    # 补齐长度后逐位比较
    length = max(len(lt), len(ct))
    lt += (0,) * (length - len(lt))
    ct += (0,) * (length - len(ct))
    return lt > ct


async def _fetch_latest_from_github() -> Optional[tuple]:
    """请求 GitHub，返回 (tag, html_url)；失败返回 None"""
    proxy = settings.openai.PROXY  # 复用已配置的代理（国内访问 GitHub 常需要）
    try:
        async with httpx.AsyncClient(
            timeout=_REQUEST_TIMEOUT,
            proxy=proxy or None,
            headers={"Accept": "application/vnd.github+json", "User-Agent": "NasFusion"},
        ) as client:
            resp = await client.get(GITHUB_LATEST_RELEASE_API)
            resp.raise_for_status()
            data = resp.json()
            tag = data.get("tag_name")
            url = data.get("html_url") or RELEASE_PAGE_URL
            if not tag:
                return None
            return tag, url
    except Exception as exc:  # noqa: BLE001 - 检查更新失败不应影响业务
        logger.warning(f"检查更新失败（已忽略）：{exc}")
        return None


async def get_latest_version(force: bool = False) -> tuple[Optional[str], str]:
    """
    获取最新版本号与发布页地址（带缓存）。

    返回 (latest_tag_or_None, release_url)。
    latest 为 None 表示暂时无法获取（外网失败）。
    """
    if not force and _cache.is_fresh():
        return _cache.tag, _cache.release_url or RELEASE_PAGE_URL

    async with _cache._lock:
        # 双重检查：等锁期间可能已被其他协程刷新
        if not force and _cache.is_fresh():
            return _cache.tag, _cache.release_url or RELEASE_PAGE_URL

        result = await _fetch_latest_from_github()
        if result is not None:
            _cache.tag, _cache.release_url = result
            _cache.fetched_at_ts = now().timestamp()

    return _cache.tag, _cache.release_url or RELEASE_PAGE_URL


async def get_version_info(force: bool = False) -> dict:
    """
    汇总版本信息，供 API 返回。

    {
      "current": "0.1.0",
      "latest": "0.2.0" | None,
      "has_update": true,
      "release_url": "https://github.com/.../releases/latest"
    }
    """
    current = get_current_version()
    latest, release_url = await get_latest_version(force=force)
    return {
        "current": current,
        "latest": _normalize(latest) if latest else None,
        "has_update": bool(latest and is_newer(latest, current)),
        "release_url": release_url,
    }
