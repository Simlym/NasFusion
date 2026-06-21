# -*- coding: utf-8 -*-
"""
UNIT3D 框架站点适配器

基于 UNIT3D 框架（BLU / Aither / Blutopia 等国际 PT 站）的通用适配器，
默认通过网页解析 /torrents 列表页获取资源信息。

选择器默认值依据 UNIT3D-Community-Edition 的 torrent/results.blade.php，
并参考 PT-depiler 的 Unit3D schema 与 MoviePilot 的 unit3d 解析。

异形 UNIT3D 站点（如资料页改版）可通过预设 unit3d_config.selectors 覆盖默认选择器，
或写一个薄子类 override _parse_torrent_row。
"""
import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse, parse_qs

import httpx
from bs4 import BeautifulSoup

from app.adapters.base import BasePTSiteAdapter
from app.adapters.pt_sites._http_mixin import HttpClientMixin
from app.adapters.pt_sites._resource_schema import normalize_resource, make_page_result
from app.utils.tv_parser import extract_tv_info
from app.constants import (
    MEDIA_TYPE_ANIME,
    MEDIA_TYPE_MOVIE,
    MEDIA_TYPE_MUSIC,
    MEDIA_TYPE_OTHER,
    MEDIA_TYPE_TV,
)
from app.constants.site_presets import get_site_preset

logger = logging.getLogger(__name__)


# UNIT3D 列表页默认选择器
# 兼容新版（torrent-search--list__*）与旧版（table-responsive）布局
DEFAULT_UNIT3D_SELECTORS: Dict[str, Any] = {
    # 行容器（多个候选，按顺序尝试）
    "torrent_rows": [
        "div.torrent-search--list__results table > tbody > tr",
        "div.table-responsive table > tbody > tr",
        "table.torrents > tbody > tr",
    ],
    # 标题 / 详情链接
    "title": ["a.view-torrent", "a.torrent-search--list__name"],
    # 大小
    "size": ["td.torrent-search--list__size", 'td > span.text-blue'],
    # 做种 / 下载 / 完成
    "seeders": ['a[href*="/peers"] > span.text-green', "td.torrent-search--list__seeders"],
    "leechers": ['a[href*="/peers"] > span.text-red', "td.torrent-search--list__leechers"],
    "completions": ['a[href*="/history"] > span.text-orange', "td.torrent-search--list__completed"],
    # 分类图标
    "category": [
        'a[href*="/categories/"] img[data-original-title]',
        'a[href*="/categories/"] img[alt]',
        "div.torrent-search--list__category img",
    ],
    # 发布时间
    "published_at": ["time"],
    # 下载链接
    "download_link": ['a[href*="/download/"]', 'a[href*="/download_check/"]'],
    # 促销标识（freeleech / double upload）
    "free": (
        "i.fa-star.text-gold, i.fa-globe, i.torrent-icons__freeleech, "
        "i[title*='100%'], span[title*='100%'], i[data-original-title*='Free']"
    ),
    "double_up": (
        "i.fa-gem.text-green, i.fa-chevron-double-up, i.torrent-icons__double-upload, "
        "i[title*='Double Upload'], i[data-original-title*='Double Upload']"
    ),
    "half_down": "i[title*='50%'], span[title*='50%']",
}


class Unit3dAdapter(HttpClientMixin, BasePTSiteAdapter):
    """
    UNIT3D 框架通用适配器（网页解析模式）。

    认证：Cookie（网页访问）。下载链接形如 /torrents/download/{id}，附 Cookie 即可。
    """

    def __init__(self, config: Dict[str, Any], metadata_mappings: Optional[Dict] = None):
        super().__init__(config)

        # 共享 HTTP 基础设施
        self._init_http(config)

        # 预设
        self.preset_id = config.get("preset_id")
        self.preset = get_site_preset(self.preset_id) if self.preset_id else None

        self.passkey = config.get("auth_passkey", "")
        self.domain = config.get("domain", "")
        self.metadata_mappings = metadata_mappings or {}
        self.site_id = None

        # UNIT3D 特有配置（预设 unit3d_config 与 config 合并）
        u3d = config.get("unit3d_config") or {}
        if self.preset and "unit3d_config" in self.preset:
            u3d = {**self.preset["unit3d_config"], **u3d}

        self.torrents_page = u3d.get("torrents_page", "/torrents")
        self.selectors = {**DEFAULT_UNIT3D_SELECTORS, **(u3d.get("selectors") or {})}

        # 分类映射（从预设的 category_details / categories 构建）
        self.category_map = self._build_category_map()

    def _build_category_map(self) -> Dict[str, str]:
        """从预设构建 {分类ID: 媒体类型} 映射。"""
        if not self.preset:
            return {}
        if "category_details" in self.preset:
            return {
                cat_id: details["mapped_category"]
                for cat_id, details in self.preset["category_details"].items()
            }
        if "categories" in self.preset:
            return dict(self.preset["categories"])
        return {}

    # ==================== 选择器工具 ====================

    @staticmethod
    def _select_one(scope, selectors):
        """按候选选择器列表依次尝试，返回第一个命中的元素。"""
        if isinstance(selectors, str):
            selectors = [selectors]
        for sel in selectors:
            elem = scope.select_one(sel)
            if elem is not None:
                return elem
        return None

    def _text(self, scope, selectors) -> str:
        elem = self._select_one(scope, selectors)
        return elem.get_text(strip=True) if elem else ""

    # ==================== 认证 / 健康检查 ====================

    async def authenticate(self) -> bool:
        """验证 Cookie 是否有效（能访问到种子列表）。"""
        try:
            if not self.cookie:
                logger.warning(f"[{self.site_name}] Cookie 未配置")
                return False
            url = urljoin(self.base_url, self.torrents_page)
            response = await self._make_request(url)
            if "/login" in str(response.url):
                logger.warning(f"[{self.site_name}] Cookie 已失效，重定向到登录页")
                return False
            soup = BeautifulSoup(response.text, "html.parser")
            rows = self._select_rows(soup)
            if not rows:
                logger.warning(f"[{self.site_name}] 未找到种子列表，可能 Cookie 无效")
                return False
            logger.info(f"[{self.site_name}] Cookie 验证成功")
            return True
        except httpx.HTTPStatusError as e:
            logger.error(f"[{self.site_name}] HTTP错误: {e.response.status_code}")
            return False
        except Exception as e:
            logger.error(f"[{self.site_name}] 认证失败: {e}")
            return False

    async def health_check(self) -> bool:
        try:
            result = await self.fetch_resources(page=1, limit=1)
            return len(result.get("resources", [])) > 0
        except Exception as e:
            logger.error(f"[{self.site_name}] 健康检查失败: {e}")
            return False

    # ==================== 资源列表 ====================

    async def fetch_resources(
        self, page: int = 1, limit: int = 50, **filters
    ) -> Dict[str, Any]:
        """
        获取资源列表。

        Args:
            page: 页码（从1开始）
            limit: 每页数量
            **filters: keyword / category 等过滤条件
        """
        try:
            url = self._build_search_url(page, limit, **filters)
            logger.info(f"[{self.site_name}] 请求URL: {url} (filters: {filters})")

            response = await self._make_request(url)
            soup = BeautifulSoup(response.text, "html.parser")

            resources = self._parse_torrent_list(soup)
            total_pages = self._parse_total_pages(soup, page)

            return make_page_result(resources, page, total_pages=total_pages)
        except Exception as e:
            logger.error(f"[{self.site_name}] 获取资源列表失败: {e}")
            raise

    def _build_search_url(self, page: int = 1, limit: int = 50, **filters) -> str:
        """构建 UNIT3D 搜索URL（/torrents?perPage=&name=&page=）。"""
        url = urljoin(self.base_url, self.torrents_page)
        params = [f"perPage={min(limit, 100)}"]

        keyword = filters.get("keyword")
        if keyword:
            params.append(f"name={keyword}")

        # UNIT3D 分类参数：categoryIds[]=
        category = filters.get("category") or filters.get("categories")
        if category:
            if isinstance(category, list):
                params.extend(f"categoryIds[]={c}" for c in category)
            else:
                params.append(f"categoryIds[]={category}")

        # 促销过滤：free[]=100
        if filters.get("promotion") == "free":
            params.append("free[]=100")

        if page > 1:
            params.append(f"page={page}")

        return f"{url}?{'&'.join(params)}"

    def _select_rows(self, soup: BeautifulSoup) -> List[Any]:
        """按候选 row 选择器依次尝试，返回非空的行集合。"""
        for sel in self.selectors["torrent_rows"]:
            rows = soup.select(sel)
            # 过滤出真正含种子链接的行（排除表头/分组行）
            rows = [
                r for r in rows
                if r.select_one("a[href*='/torrents/']") is not None
                and r.select_one("a[href*='/download']") is not None
            ]
            if rows:
                return rows
        return []

    def _parse_torrent_list(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        rows = self._select_rows(soup)
        if not rows:
            logger.warning(f"[{self.site_name}] 未找到种子行")
            return []

        resources = []
        for row in rows:
            try:
                resource = self._parse_torrent_row(row)
                if resource:
                    resources.append(resource)
            except Exception as e:
                logger.debug(f"[{self.site_name}] 解析行失败: {e}")
                continue

        logger.info(f"[{self.site_name}] 解析到 {len(resources)} 个资源")
        return resources

    def _parse_torrent_row(self, row) -> Optional[Dict[str, Any]]:
        """解析单行 UNIT3D 种子信息。"""
        # 标题与详情链接
        title_elem = self._select_one(row, self.selectors["title"])
        if not title_elem:
            return None
        title = title_elem.get_text(strip=True)
        detail_href = title_elem.get("href", "")

        torrent_id = self._extract_torrent_id(detail_href)
        if not torrent_id:
            return None

        # 大小
        size_bytes = self._parse_size(self._text(row, self.selectors["size"]))

        # 做种 / 下载 / 完成
        seeders = self._parse_int(self._text(row, self.selectors["seeders"]))
        leechers = self._parse_int(self._text(row, self.selectors["leechers"]))
        completions = self._parse_int(self._text(row, self.selectors["completions"]))

        # 分类
        category = self._parse_category(row)

        # 发布时间
        published_at = None
        time_elem = self._select_one(row, self.selectors["published_at"])
        if time_elem:
            time_val = (
                time_elem.get("title")
                or time_elem.get("datetime")
                or time_elem.get_text(strip=True)
            )
            published_at = self._parse_time(time_val)

        # 促销
        is_free = bool(row.select_one(self.selectors["free"]))
        is_double_up = bool(row.select_one(self.selectors["double_up"]))
        is_half_down = bool(row.select_one(self.selectors["half_down"]))
        if is_free and is_double_up:
            promotion_type = "free_2x"
        elif is_free:
            promotion_type = "free"
        elif is_double_up:
            promotion_type = "2x"
        elif is_half_down:
            promotion_type = "50%"
        else:
            promotion_type = "none"

        # 下载链接：UNIT3D 规范为 /torrents/download/{id}。
        # 页面里可能是 download_check 链接或省略 /torrents 前缀，统一回退到按 id 构造，
        # 避免拼出 /download/{id} 这类无效路径（参考 PT-depiler getTorrentDownloadLink）。
        dl_elem = self._select_one(row, self.selectors["download_link"])
        download_url = ""
        if dl_elem:
            href = dl_elem.get("href", "").replace("/download_check/", "/download/")
            if "/torrents/download/" in href:
                download_url = urljoin(self.base_url, href)
        if not download_url:
            download_url = self._build_download_url(torrent_id)

        # 电视剧信息
        tv_info = None
        if category in (MEDIA_TYPE_TV, MEDIA_TYPE_ANIME):
            tv_info = extract_tv_info(title, "")

        return normalize_resource({
            "torrent_id": torrent_id,
            "title": title,
            "subtitle": "",  # UNIT3D 列表页无副标题
            "category": category,
            "original_category_id": self._extract_category_id(row),
            "size_bytes": size_bytes,
            "seeders": seeders,
            "leechers": leechers,
            "completions": completions,
            "published_at": published_at,
            "is_free": is_free,
            "is_double_upload": is_double_up,
            "is_discount": is_half_down,
            "promotion_type": promotion_type,
            "download_url": download_url,
            "detail_url": urljoin(self.base_url, detail_href),
            "tv_info": tv_info,
        })

    def _parse_category(self, row) -> str:
        """解析分类（先取分类ID映射，否则按图标 title/alt 文本回退）。"""
        cat_id = self._extract_category_id(row)
        if cat_id and self.category_map:
            mapped = self.category_map.get(str(cat_id))
            if mapped:
                return mapped

        # 回退：按图标 title / alt 文本粗略判断
        cat_elem = self._select_one(row, self.selectors["category"])
        if cat_elem:
            label = (
                cat_elem.get("data-original-title")
                or cat_elem.get("title")
                or cat_elem.get("alt")
                or ""
            ).lower()
            if "movie" in label:
                return MEDIA_TYPE_MOVIE
            if "tv" in label or "episode" in label or "season" in label:
                return MEDIA_TYPE_TV
            if "anime" in label:
                return MEDIA_TYPE_ANIME
            if "music" in label or "audio" in label:
                return MEDIA_TYPE_MUSIC
        return MEDIA_TYPE_OTHER

    def _extract_category_id(self, row) -> Optional[str]:
        """从 a[href*='/categories/{id}'] 提取分类ID。"""
        cat_link = row.select_one("a[href*='/categories/']")
        if cat_link:
            match = re.search(r"/categories/(\d+)", cat_link.get("href", ""))
            if match:
                return match.group(1)
        return None

    def _extract_torrent_id(self, href: str) -> Optional[str]:
        """从 /torrents/{id} 提取种子ID。"""
        if not href:
            return None
        match = re.search(r"/torrents/(\d+)", href)
        if match:
            return match.group(1)
        # 兜底：查询参数 id
        params = parse_qs(urlparse(href).query)
        if "id" in params:
            return params["id"][0]
        return None

    def _build_download_url(self, torrent_id: str) -> str:
        """构造 UNIT3D 下载链接 /torrents/download/{id}。"""
        url = urljoin(self.base_url, f"/torrents/download/{torrent_id}")
        # 部分站点需要 rsskey/passkey 附在链接上
        if self.passkey:
            url = f"{url}?rsskey={self.passkey}"
        return url

    def _parse_total_pages(self, soup: BeautifulSoup, current_page: int) -> int:
        """从分页组件解析总页数。"""
        max_page = current_page
        for link in soup.select("ul.pagination a[href*='page='], nav a[href*='page=']"):
            match = re.search(r"page=(\d+)", link.get("href", ""))
            if match:
                max_page = max(max_page, int(match.group(1)))
        return max_page

    # ==================== 详情 / 下载 ====================

    async def get_resource_detail(self, resource_id: str) -> Dict[str, Any]:
        """获取资源详情页信息（描述 / mediainfo / imdb / tmdb）。"""
        try:
            url = urljoin(self.base_url, f"/torrents/{resource_id}")
            response = await self._make_request(url)
            soup = BeautifulSoup(response.text, "html.parser")

            detail: Dict[str, Any] = {
                "torrent_id": resource_id,
                "detail_fetched": True,
            }

            desc_elem = soup.select_one(".torrent-description, #description, .panelV2 .bbcode-rendered")
            if desc_elem:
                detail["description"] = desc_elem.get_text(strip=True)

            mediainfo_elem = soup.select_one("pre.mediainfo, code.mediainfo, pre")
            if mediainfo_elem:
                detail["mediainfo"] = mediainfo_elem.get_text(strip=True)

            imdb_elem = soup.select_one("a[href*='imdb.com/title']")
            if imdb_elem:
                m = re.search(r"tt\d+", imdb_elem.get("href", ""))
                if m:
                    detail["imdb_id"] = m.group(0)

            tmdb_elem = soup.select_one("a[href*='themoviedb.org']")
            if tmdb_elem:
                m = re.search(r"/(movie|tv)/(\d+)", tmdb_elem.get("href", ""))
                if m:
                    detail["tmdb_id"] = m.group(2)

            return detail
        except Exception as e:
            logger.error(f"[{self.site_name}] 获取资源详情失败: {e}")
            raise

    async def download_torrent(self, resource_id: str, download_url: str = None) -> bytes:
        """下载种子文件（Cookie 认证；链接 /torrents/download/{id}）。"""
        try:
            url = download_url or self._build_download_url(resource_id)
            logger.info(f"[{self.site_name}] 下载种子: {self._mask_proxy_url(url)}")

            response = await self._make_request(url)
            content = response.content

            if not content.startswith(b"d"):
                if b"<html" in content.lower() or b"<!doctype" in content.lower():
                    raise ValueError("下载返回HTML页面，可能未登录或无下载权限")
                raise ValueError("下载的内容不是有效的种子文件")

            logger.info(f"[{self.site_name}] 种子下载成功: {len(content)} bytes")
            return content
        except Exception as e:
            logger.error(f"[{self.site_name}] 下载种子失败: {e}")
            raise

    # ==================== 用户资料 ====================

    async def fetch_user_profile(self) -> Optional[Dict[str, Any]]:
        """解析 UNIT3D 用户信息（/ 取用户名，/users/{name} 取详情）。"""
        try:
            index_resp = await self._make_request(urljoin(self.base_url, "/"))
            soup = BeautifulSoup(index_resp.text, "html.parser")

            username = self._extract_username(soup)
            if not username:
                logger.warning(f"[{self.site_name}] 无法解析用户名")
                return None

            profile: Dict[str, Any] = {"username": username}

            detail_resp = await self._make_request(
                urljoin(self.base_url, f"/users/{username}")
            )
            detail_soup = BeautifulSoup(detail_resp.text, "html.parser")

            # 上传/下载量（图标方式）
            up_elem = detail_soup.select_one(
                "li.ratio-bar__uploaded a, span:has(> i.fa-arrow-up)"
            )
            if up_elem:
                profile["uploaded"] = self._parse_size_text(up_elem.get_text(strip=True))
            dl_elem = detail_soup.select_one(
                "li.ratio-bar__downloaded a, span:has(> i.fa-arrow-down)"
            )
            if dl_elem:
                profile["downloaded"] = self._parse_size_text(dl_elem.get_text(strip=True))

            # 分享率
            ratio_elem = detail_soup.select_one(
                "li.ratio-bar__ratio a, span:has(> i.fa-sync-alt)"
            )
            if ratio_elem:
                m = re.search(r"[\d.]+", ratio_elem.get_text(strip=True).replace(",", ""))
                if m:
                    profile["ratio"] = float(m.group(0))

            # 等级
            level_elem = detail_soup.select_one("span.badge-user, a.user-tag__link[title]")
            if level_elem:
                profile["user_class"] = (
                    level_elem.get("title") or level_elem.get_text(strip=True)
                )

            # 魔力 / 积分
            bonus_elem = detail_soup.select_one(
                "li.ratio-bar__points a, span:has(> i.fa-coins)"
            )
            if bonus_elem:
                m = re.search(r"[\d,.]+", bonus_elem.get_text(strip=True))
                if m:
                    profile["bonus"] = float(m.group(0).replace(",", ""))

            # 字段名映射回退（Ratio/Seeding Size 等 td/dd 结构）
            self._fill_profile_from_labels(detail_soup, profile)

            logger.info(f"[{self.site_name}] Fetched user profile: {username}")
            return profile
        except Exception as e:
            logger.error(f"[{self.site_name}] 获取用户信息失败: {e}")
            return None

    @staticmethod
    def _extract_username(soup: BeautifulSoup) -> Optional[str]:
        """从首页的 /users/{name}/settings 链接提取用户名。"""
        link = soup.select_one("a[href*='/users/'][href*='settings']")
        if link:
            m = re.search(r"/users/([^/]+)/settings", link.get("href", ""))
            if m:
                return m.group(1)
        # 回退：任意 /users/{name} 链接
        link = soup.select_one("a[href*='/users/']")
        if link:
            m = re.search(r"/users/([^/?#]+)", link.get("href", ""))
            if m:
                return m.group(1)
        return None

    def _fill_profile_from_labels(self, soup: BeautifulSoup, profile: Dict[str, Any]) -> None:
        """通过标签文本（td:contains / dt:contains）补充缺失字段。"""
        label_map = {
            "seeding_count": ["Seeding", "做种"],
            "seeding_size": ["Seeding Size", "做种体积"],
            "join_date": ["Registration date", "注册日期", "註冊日期"],
        }
        text = soup.get_text("\n")
        for field, keys in label_map.items():
            if profile.get(field):
                continue
            for key in keys:
                m = re.search(rf"{re.escape(key)}[:：\s]+([^\n]+)", text)
                if not m:
                    continue
                val = m.group(1).strip()
                if field == "seeding_count":
                    iv = self._parse_int(val)
                    if iv:
                        profile[field] = iv
                elif field == "seeding_size":
                    sv = self._parse_size_text(val)
                    if sv:
                        profile[field] = sv
                elif field == "join_date":
                    dm = re.search(r"\d{4}-\d{2}-\d{2}", val)
                    if dm:
                        profile[field] = dm.group(0)
                break

    # ==================== 分类同步 ====================

    async def fetch_categories(self) -> List[Dict[str, Any]]:
        """从预设的 category_details 返回分类（与 NexusPHP 一致）。"""
        categories: List[Dict[str, Any]] = []
        if not self.preset:
            return categories
        category_details = self.preset.get("category_details", {})
        order = 0
        for cat_id, details in category_details.items():
            categories.append({
                "id": cat_id,
                "nameChs": details.get("name_chs", ""),
                "nameEng": details.get("name_eng", ""),
                "nameCht": details.get("name_cht"),
                "parent": None,
                "order": order,
                "image": None,
                "_mapped_category": details.get("mapped_category"),
            })
            order += 1
        logger.info(f"[{self.site_name}] 从预设加载 {len(categories)} 个分类")
        return categories

    async def load_category_mappings(self, db) -> None:
        """与 NexusPHP 一致：分类映射来自预设，无需额外加载。"""
        return None


__all__ = ["Unit3dAdapter", "DEFAULT_UNIT3D_SELECTORS"]
