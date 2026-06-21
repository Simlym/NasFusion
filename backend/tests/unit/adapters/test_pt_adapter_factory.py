# -*- coding: utf-8 -*-
"""
PT 站点适配器工厂路由 + 共享基础设施回归测试

覆盖：
- get_adapter 按 preset.schema 路由（hdsky/chdbits -> NexusPHP, mteam -> MTeam）
- 显式 preset_id 透传优先
- 无预设时回退到 site_type 直查
- 未知站点抛 ValueError
- NexusPHPAdapter 正确继承 HttpClientMixin
- 资源标准结构 normalize_resource / make_page_result
"""
import pytest

from app.adapters.pt_sites import get_adapter
from app.adapters.pt_sites.nexusphp import NexusPHPAdapter
from app.adapters.pt_sites.mteam import MTeamAdapter
from app.adapters.pt_sites._http_mixin import HttpClientMixin
from app.adapters.pt_sites._resource_schema import (
    normalize_resource,
    make_page_result,
)

pytestmark = pytest.mark.unit

BASE_CONFIG = {
    "name": "TestSite",
    "base_url": "https://example.org",
    "domain": "example.org",
    "proxy_config": None,
    "request_interval": 1,
    "prefer_requests": False,
}


def _cfg(**overrides):
    return {**BASE_CONFIG, **overrides}


def test_legacy_preset_routes_to_nexusphp():
    """site_type=hdsky（无显式 preset_id）应按 schema=nexusphp 路由。"""
    adapter = get_adapter("hdsky", _cfg(auth_cookie="c=1"))
    assert isinstance(adapter, NexusPHPAdapter)
    assert adapter.preset_id == "hdsky"
    # 预设的选择器与分类映射已加载
    assert adapter.selectors
    assert adapter.category_map.get("401") is not None


def test_mteam_routes_to_mteam_adapter():
    adapter = get_adapter("mteam", _cfg(auth_passkey="k"))
    assert isinstance(adapter, MTeamAdapter)


def test_explicit_preset_id_takes_precedence():
    """config 显式 preset_id 应优先于 site_type。"""
    adapter = get_adapter("ignored_type", _cfg(preset_id="chdbits", auth_cookie="c=1"))
    assert isinstance(adapter, NexusPHPAdapter)
    assert adapter.preset_id == "chdbits"


def test_fallback_to_site_type_registry_without_preset():
    """无预设的原始 site_type（nexusphp）回退到站点级注册表。"""
    adapter = get_adapter("nexusphp", _cfg(auth_cookie="c=1"))
    assert isinstance(adapter, NexusPHPAdapter)


def test_unknown_site_type_raises():
    with pytest.raises(ValueError):
        get_adapter("definitely_not_a_site", _cfg())


def test_nexusphp_inherits_http_mixin():
    adapter = get_adapter("hdsky", _cfg(auth_cookie="c=1"))
    assert isinstance(adapter, HttpClientMixin)
    # mixin 方法可用
    assert callable(adapter._make_request)
    assert adapter._parse_size("1.5 GB") == int(1.5 * 1024 ** 3)
    assert adapter._parse_int("1,234") == 1234
    headers = adapter._get_headers()
    assert headers["Cookie"] == "c=1"
    assert "User-Agent" in headers


def test_normalize_resource_fills_defaults():
    r = normalize_resource({"torrent_id": "1", "title": "X", "category": "movie"})
    assert r["seeders"] == 0
    assert r["promotion_type"] == "none"
    assert r["is_free"] is False
    assert r["detail_fetched"] is False
    # 原始字段保留
    assert r["torrent_id"] == "1" and r["title"] == "X" and r["category"] == "movie"


def test_make_page_result_shape():
    r = normalize_resource({"torrent_id": "1", "title": "X", "category": "movie"})
    page = make_page_result([r], page=2, total_pages=5, total=500)
    assert page["resources"] == [r]
    assert page["page_number"] == 2
    assert page["total_pages"] == 5
    assert page["total"] == 500
    assert page["page_size"] == 1


def test_make_page_result_total_defaults_to_len():
    page = make_page_result([], page=1)
    assert page["total"] == 0
    assert page["total_pages"] == 1
    assert page["page_size"] == 0
