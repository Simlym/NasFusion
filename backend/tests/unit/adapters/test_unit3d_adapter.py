# -*- coding: utf-8 -*-
"""
Unit3dAdapter 网页解析回归测试（本地 HTML fixture，无需真实站点）。
"""
import pytest
from bs4 import BeautifulSoup

from app.adapters.pt_sites import get_adapter
from app.adapters.pt_sites.unit3d import Unit3dAdapter
from app.constants import MEDIA_TYPE_MOVIE, MEDIA_TYPE_TV

pytestmark = pytest.mark.unit


def _make_adapter():
    return get_adapter(
        "blutopia",
        {
            "name": "BLU",
            "base_url": "https://blutopia.cc",
            "domain": "blutopia.cc",
            "auth_cookie": "c=1",
            "auth_passkey": "RSSKEY123",
            "proxy_config": None,
            "request_interval": 1,
            "prefer_requests": False,
        },
    )


# 一个简化但结构真实的 UNIT3D 新版列表页（两行：一部 free 电影、一部 2x 剧集）
UNIT3D_LIST_HTML = """
<html><body>
<div class="torrent-search--list__results">
  <table><tbody>
    <tr>
      <td class="torrent-search--list__category">
        <a href="/categories/1"><img alt="Movie" data-original-title="Movie torrent"></a>
      </td>
      <td class="torrent-search--list__name">
        <a class="view-torrent" href="/torrents/1001">Dune Part Two 2024 2160p</a>
      </td>
      <td><i class="fa-star text-gold" title="100% Freeleech"></i></td>
      <td class="torrent-search--list__size">25.4 GiB</td>
      <td><a href="/torrents/1001/peers"><span class="text-green">42</span></a></td>
      <td><a href="/torrents/1001/peers"><span class="text-red">3</span></a></td>
      <td><a href="/torrents/1001/history"><span class="text-orange">128</span></a></td>
      <td><time title="2024-03-01 12:00:00">2 days ago</time></td>
      <td><a href="/torrents/download/1001">DL</a></td>
    </tr>
    <tr>
      <td class="torrent-search--list__category">
        <a href="/categories/2"><img alt="TV" data-original-title="TV torrent"></a>
      </td>
      <td class="torrent-search--list__name">
        <a class="view-torrent" href="/torrents/1002">Some Show S01 1080p</a>
      </td>
      <td><i class="fa-gem text-green" title="Double Upload"></i></td>
      <td class="torrent-search--list__size">8 GiB</td>
      <td><a href="/torrents/1002/peers"><span class="text-green">10</span></a></td>
      <td><a href="/torrents/1002/peers"><span class="text-red">1</span></a></td>
      <td><a href="/torrents/1002/history"><span class="text-orange">20</span></a></td>
      <td><time title="2024-02-20 08:30:00">1 week ago</time></td>
      <td><a href="/download_check/1002">DL</a></td>
    </tr>
  </tbody></table>
</div>
<nav><a href="/torrents?page=5">5</a></nav>
</body></html>
"""


def test_parse_torrent_list_basic():
    adapter = _make_adapter()
    soup = BeautifulSoup(UNIT3D_LIST_HTML, "html.parser")
    resources = adapter._parse_torrent_list(soup)
    assert len(resources) == 2

    movie = resources[0]
    assert movie["torrent_id"] == "1001"
    assert movie["title"] == "Dune Part Two 2024 2160p"
    assert movie["category"] == MEDIA_TYPE_MOVIE
    assert movie["original_category_id"] == "1"
    assert movie["size_bytes"] == int(25.4 * 1024 ** 3)
    assert movie["seeders"] == 42
    assert movie["leechers"] == 3
    assert movie["completions"] == 128
    assert movie["is_free"] is True
    assert movie["promotion_type"] == "free"
    assert movie["download_url"] == "https://blutopia.cc/torrents/download/1001"
    assert movie["published_at"] is not None

    tv = resources[1]
    assert tv["torrent_id"] == "1002"
    assert tv["category"] == MEDIA_TYPE_TV
    assert tv["is_double_upload"] is True
    assert tv["promotion_type"] == "2x"
    # 页面里的 download_check 链接缺少 /torrents 前缀，应回退为按 id 构造（带 rsskey）
    assert tv["download_url"] == "https://blutopia.cc/torrents/download/1002?rsskey=RSSKEY123"
    # 剧集应解析出 tv_info
    assert tv["tv_info"] is not None


def test_parse_total_pages():
    adapter = _make_adapter()
    soup = BeautifulSoup(UNIT3D_LIST_HTML, "html.parser")
    assert adapter._parse_total_pages(soup, current_page=1) == 5


def test_build_download_url_with_rsskey():
    adapter = _make_adapter()
    url = adapter._build_download_url("999")
    assert url == "https://blutopia.cc/torrents/download/999?rsskey=RSSKEY123"


def test_resource_dict_is_normalized():
    """解析结果应包含标准 schema 全部字段。"""
    adapter = _make_adapter()
    soup = BeautifulSoup(UNIT3D_LIST_HTML, "html.parser")
    r = adapter._parse_torrent_list(soup)[0]
    for key in (
        "subtitle", "subcategory", "promotion_expire_at", "detail_fetched",
        "douban_id", "imdb_id", "imdb_rating", "detail_url",
    ):
        assert key in r


def test_select_rows_filters_non_torrent_rows():
    """没有种子链接/下载链接的行应被过滤掉。"""
    adapter = _make_adapter()
    html = """
    <div class="torrent-search--list__results"><table><tbody>
      <tr><th>Header</th></tr>
      <tr><td class="torrent-search--list__name">
        <a class="view-torrent" href="/torrents/2001">X</a></td>
        <td><a href="/torrents/download/2001">DL</a></td></tr>
    </tbody></table></div>
    """
    soup = BeautifulSoup(html, "html.parser")
    rows = adapter._select_rows(soup)
    assert len(rows) == 1
