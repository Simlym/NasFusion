# -*- coding: utf-8 -*-
"""
GenericJSONAPIAdapter 回归测试（mock JSON 响应，无需真实站点）。
以 TNode 预设为例覆盖：字段映射 / response_path / 促销系数 / 时间戳 / 下载链模板 /
请求体模板渲染 / CSRF / 分页推算。
"""
import json
import pytest

from app.adapters.pt_sites import get_adapter
from app.adapters.pt_sites.generic_json_api import GenericJSONAPIAdapter
from app.utils.json_path import get_by_path, render_template, render_template_obj, safe_int
from app.constants import MEDIA_TYPE_MOVIE, MEDIA_TYPE_TV

pytestmark = pytest.mark.unit


class _FakeResp:
    def __init__(self, payload=None, content=b"", text=""):
        self._payload = payload
        self.content = content
        self.text = text

    def json(self):
        return self._payload


def _adapter():
    return get_adapter(
        "tnode",
        {
            "name": "TNode",
            "base_url": "https://tnode.club",
            "domain": "tnode.club",
            "auth_cookie": "c=1",
            "proxy_config": None,
            "request_interval": 1,
            "prefer_requests": False,
        },
    )


# 模拟 advancedSearch 响应
TNODE_RESPONSE = {
    "data": {
        "total": 250,
        "torrents": [
            {
                "id": 9001,
                "title": "Inception 2010 2160p",
                "subtitle": "盗梦空间",
                "size": 32212254720,        # 30 GiB
                "seeding": 88,
                "leeching": 4,
                "complete": 300,
                "category": 501,            # movie
                "upload_time": 1709280000,  # 2024-03-01
                "downloadRate": 0,          # free
                "uploadRate": 2,            # 2x
                "imdb": "tt1375666",
            },
            {
                "id": 9002,
                "title": "Some Drama S02 1080p",
                "subtitle": "",
                "size": 8589934592,         # 8 GiB
                "seeding": 12,
                "leeching": 1,
                "complete": 40,
                "category": 502,            # tv
                "upload_time": 1708000000,
                "downloadRate": 0.5,        # 50%
                "uploadRate": 1,
                "imdb": "",
            },
        ],
    }
}


# ---------- json_path 工具 ----------

def test_get_by_path():
    assert get_by_path({"a": {"b": {"c": 1}}}, "a.b.c") == 1
    assert get_by_path({"a": [{"x": 9}]}, "a.0.x") == 9
    assert get_by_path({"a": 1}, "a.b.c", default="d") == "d"
    assert get_by_path({"a": 1}, "") == {"a": 1}


def test_render_template_obj_preserves_types():
    ctx = {"page": 3, "size": 100, "keyword": "dune"}
    body = {"page": "{{page}}", "size": "{{size}}", "keyword": "{{keyword}}", "type": "title"}
    out = render_template_obj(body, ctx)
    assert out["page"] == 3 and isinstance(out["page"], int)
    assert out["size"] == 100
    assert out["keyword"] == "dune"
    assert out["type"] == "title"


def test_render_template_string_interpolation():
    assert render_template("/api/torrent/download/{{torrent_id}}", {"torrent_id": "42"}) == \
        "/api/torrent/download/42"


# ---------- adapter ----------

def test_build_search_request_renders_body():
    import asyncio
    a = _adapter()
    method, url, kwargs = asyncio.run(a._build_search_request(2, 100, keyword="dune"))
    assert method == "POST"
    assert url == "https://tnode.club/api/torrent/advancedSearch"
    body = kwargs["json"]
    assert body["page"] == 2          # page_base=1 -> page-1+1 = 2
    assert body["size"] == 100
    assert body["keyword"] == "dune"
    assert body["category"] == [501, 502, 503, 504]


def test_map_row_movie_free_2x():
    a = _adapter()
    row = TNODE_RESPONSE["data"]["torrents"][0]
    r = a._map_row(row)
    assert r["torrent_id"] == "9001"
    assert r["title"] == "Inception 2010 2160p"
    assert r["subtitle"] == "盗梦空间"
    assert r["size_bytes"] == 32212254720
    assert r["seeders"] == 88
    assert r["leechers"] == 4
    assert r["completions"] == 300
    assert r["category"] == MEDIA_TYPE_MOVIE
    assert r["original_category_id"] == 501
    assert r["imdb_id"] == "tt1375666"
    assert r["published_at"] is not None
    # downloadRate=0 -> free, uploadRate=2 -> 2x
    assert r["is_free"] is True
    assert r["is_double_upload"] is True
    assert r["promotion_type"] == "free_2x"
    assert r["download_url"] == "https://tnode.club/api/torrent/download/9001"


def test_map_row_tv_half_down():
    a = _adapter()
    row = TNODE_RESPONSE["data"]["torrents"][1]
    r = a._map_row(row)
    assert r["category"] == MEDIA_TYPE_TV
    assert r["is_discount"] is True
    assert r["promotion_type"] == "50%"
    assert r["tv_info"] is not None  # 剧集解析

def test_map_row_skips_invalid():
    a = _adapter()
    assert a._map_row({"id": 1}) is None       # 缺 title
    assert a._map_row({"title": "X"}) is None   # 缺 id


def test_fetch_resources_end_to_end(monkeypatch):
    a = _adapter()

    async def fake_csrf():
        a._csrf_token = "tok"
    async def fake_request(url, method="GET", **kwargs):
        return _FakeResp(payload=TNODE_RESPONSE)

    monkeypatch.setattr(a, "_ensure_csrf_token", fake_csrf)
    monkeypatch.setattr(a, "_make_request", fake_request)

    import asyncio
    result = asyncio.run(a.fetch_resources(page=1, limit=100, keyword="x"))
    assert len(result["resources"]) == 2
    assert result["total"] == 250
    # total=250, page_size=100 -> 3 页
    assert result["total_pages"] == 3
    assert result["page_number"] == 1


def test_csrf_header_injected_when_token_present():
    a = _adapter()
    a._csrf_token = "abc123"
    headers = a._get_headers()
    assert headers["X-CSRF-TOKEN"] == "abc123"
    assert headers["Content-Type"].startswith("application/json")
    assert headers["Cookie"] == "c=1"
