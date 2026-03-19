# -*- coding: utf-8 -*-
"""
NexusPHP站点通用适配器

基于NexusPHP框架的PT站点通用适配器，通过网页解析获取资源信息
支持大多数国内PT站点

参考项目：
- PT-Plugin-Plus: https://github.com/pt-plugins/PT-Plugin-Plus
"""

import asyncio
import logging
import re
import ssl
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse, parse_qs

import httpx
from bs4 import BeautifulSoup

# requests 作为 fallback（某些代理场景下 httpx 的 TLS 握手可能失败）
try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

from app.adapters.base import BasePTSiteAdapter
from app.utils.timezone import now, parse_pt_site_time
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

# 禁用 SSL 警告（仅在开发/调试时使用）
try:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except ImportError:
    pass


class NexusPHPAdapter(BasePTSiteAdapter):
    """
    NexusPHP站点通用适配器

    处理基于NexusPHP框架的PT站点，通过Cookie认证，解析网页获取资源信息
    """

    def __init__(self, config: Dict[str, Any], metadata_mappings: Optional[Dict] = None):
        """
        初始化NexusPHP适配器

        Args:
            config: 站点配置字典，包含：
                - name: 站点名称
                - base_url: 基础URL
                - domain: 域名
                - auth_cookie: Cookie（用于网页访问）
                - auth_passkey: Passkey（用于下载种子）
                - proxy_config: 代理配置（可选）
                - request_interval: 请求间隔（秒）
                - preset_id: 预设ID（可选，用于加载默认配置）
                - verify_ssl: 是否验证SSL证书（默认False）
                - prefer_requests: 是否优先使用requests库（默认False）
            metadata_mappings: 元数据映射字典（可选）
        """
        super().__init__(config)

        # 加载预设配置
        self.preset_id = config.get("preset_id")
        self.preset = get_site_preset(self.preset_id) if self.preset_id else None

        # 基础配置
        self.cookie = config.get("auth_cookie", "")
        self.passkey = config.get("auth_passkey", "")
        self.domain = config.get("domain", "")
        self.proxy_config = config.get("proxy_config") or {}
        self.request_interval = config.get("request_interval", 5)
        self._last_request_time = 0.0

        # 验证 Cookie 格式
        if self.cookie:
            cookie_preview = self.cookie[:50] if len(self.cookie) > 50 else self.cookie
            logger.info(
                f"[{self.site_name}] Cookie 已配置: 长度={len(self.cookie)}, "
                f"预览='{cookie_preview}...'"
            )
            if self.cookie.startswith("gAAAAA"):
                logger.error(
                    f"[{self.site_name}] Cookie 似乎仍是加密状态！请检查解密逻辑"
                )
        else:
            logger.warning(f"[{self.site_name}] Cookie 未配置")

        # 元数据映射
        self.metadata_mappings = metadata_mappings or {}

        # 站点ID
        self.site_id = None

        # User-Agent
        self.user_agent = config.get(
            "user_agent",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        # SSL配置（默认禁用验证以兼容更多站点）
        self.verify_ssl = config.get("verify_ssl", False)

        # 重试配置
        self.max_retries = config.get("max_retries", 3)
        self.retry_delay = config.get("retry_delay", 2)  # 秒

        # 是否优先使用 requests 库（在代理场景下更稳定）
        self.prefer_requests = config.get("prefer_requests", True)

        # HTTP客户端配置
        self.client_config = {
            "timeout": httpx.Timeout(30.0),
            "follow_redirects": True,
            "verify": self.verify_ssl,
            "http2": False,  # 禁用HTTP/2，避免某些站点兼容问题
        }

        # 代理配置
        self.proxy_url = None
        if self.proxy_config:
            self.proxy_url = self._build_proxy_url()
            if self.proxy_url:
                self.client_config["proxy"] = self.proxy_url
                logger.info(f"[{self.site_name}] 代理已启用: {self._mask_proxy_url(self.proxy_url)}")
            else:
                logger.warning(f"[{self.site_name}] 代理配置存在但无法构建URL: {self.proxy_config}")
        else:
            logger.info(f"[{self.site_name}] 未配置代理，直连模式")

        # NexusPHP特有配置（从预设或config加载）
        nexusphp_config = config.get("nexusphp_config") or {}
        if self.preset and "nexusphp_config" in self.preset:
            preset_nexusphp = self.preset["nexusphp_config"]
            nexusphp_config = {**preset_nexusphp, **nexusphp_config}

        self.torrents_page = nexusphp_config.get("torrents_page", "/torrents.php")
        self.details_page = nexusphp_config.get("details_page", "/details.php")
        self.download_page = nexusphp_config.get("download_page", "/download.php")
        self.search_params = nexusphp_config.get("search_params", {
            "search": "{keyword}",
            "cat": "{category}",
            "page": "{page}",
        })
        self.selectors = nexusphp_config.get("selectors", self._get_default_selectors())

        # 分类映射（从预设加载）
        # 优先从 category_details 构建，兼容旧的 categories 格式
        self.category_map = None
        if self.preset:
            if "category_details" in self.preset:
                # 从 category_details 构建: {cat_id: mapped_category}
                self.category_map = {
                    cat_id: details["mapped_category"]
                    for cat_id, details in self.preset["category_details"].items()
                }
            elif "categories" in self.preset:
                # 兼容旧格式
                self.category_map = self.preset["categories"]

    def _build_proxy_url(self) -> Optional[str]:
        """构建代理URL"""
        proxy_url = self.proxy_config.get("url")

        if not proxy_url and self.proxy_config.get("host"):
            p_type = self.proxy_config.get("type", "http")
            p_host = self.proxy_config.get("host")
            p_port = self.proxy_config.get("port")
            p_user = self.proxy_config.get("username")
            p_pass = self.proxy_config.get("password")

            auth_part = ""
            if p_user and p_pass:
                auth_part = f"{p_user}:{p_pass}@"

            if p_host and p_port:
                proxy_url = f"{p_type}://{auth_part}{p_host}:{p_port}"

        return proxy_url

    def _mask_proxy_url(self, proxy_url: str) -> str:
        """掩码代理URL中的敏感信息"""
        if not proxy_url:
            return "None"
        return re.sub(r"://([^:]+):([^@]+)@", r"://***:***@", proxy_url)

    def _get_default_selectors(self) -> Dict[str, str]:
        """获取默认的CSS选择器配置"""
        return {
            "torrent_table": "table.torrents",
            "torrent_row": "tr:not(:first-child)",
            "title": "a[href*='details.php']",
            "subtitle": "td.embedded > span, td.torrentname > span.small",
            "category": "td:first-child a[href*='cat='] img",
            "size": "td:nth-child(5)",
            "seeders": "td:nth-child(6)",
            "leechers": "td:nth-child(7)",
            "completions": "td:nth-child(8)",
            "published_at": "td:nth-child(4) > span, td.rowfollow nobr span",
            "download_link": "a[href*='download.php']",
            # 促销标识
            "free": "img.pro_free, img.pro_free2up, font.free, span.free",
            "double_up": "img.pro_2up, img.pro_free2up, font.twoup, span.twoup",
            "half_down": "img.pro_50pctdown, font.halfdown, span.halfdown",
            # 详情页
            "detail_description": "#kdescr, .bbcode",
            "detail_mediainfo": "#mediainfo, pre",
            "detail_imdb": "a[href*='imdb.com/title']",
            "detail_douban": "a[href*='douban.com/subject']",
        }

    async def _wait_for_rate_limit(self):
        """等待速率限制"""
        current_time = asyncio.get_event_loop().time()
        time_since_last = current_time - self._last_request_time
        if time_since_last < self.request_interval:
            await asyncio.sleep(self.request_interval - time_since_last)
        self._last_request_time = asyncio.get_event_loop().time()

    def _get_headers(self) -> Dict[str, str]:
        """获取请求头 - 模拟完整浏览器请求"""
        headers = {
            "User-Agent": self.user_agent,
            "Cookie": self.cookie,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Cache-Control": "max-age=0",
            "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
        }
        if self.base_url:
            headers["Referer"] = self.base_url
        return headers

    async def _make_request(
        self,
        url: str,
        method: str = "GET",
        **kwargs,
    ) -> httpx.Response:
        """
        发送HTTP请求（带重试和fallback机制）

        优先使用httpx异步请求，如果失败则尝试使用requests同步请求。

        Args:
            url: 请求URL
            method: 请求方法
            **kwargs: 其他请求参数

        Returns:
            HTTP响应
        """
        await self._wait_for_rate_limit()

        headers = self._get_headers()
        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))

        # 简化日志
        logger.info(f"[{self.site_name}] Requesting {url}")

        # 如果配置了优先使用 requests，直接使用 requests
        if self.prefer_requests and REQUESTS_AVAILABLE:
            return await self._make_request_with_requests(url, method, headers, **kwargs)

        # 尝试使用 httpx
        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = await self._make_request_with_httpx(url, method, headers, **kwargs)
                return response
            except (httpx.ConnectError, httpx.ConnectTimeout, httpx.RemoteProtocolError) as e:
                # 连接错误、TLS握手失败、协议错误直接尝试 fallback
                # RemoteProtocolError 包括 "peer closed connection" 等情况
                last_error = e
                logger.warning(
                    f"[{self.site_name}] httpx 连接/协议失败 ({type(e).__name__}): {e}"
                )
                break  # 不重试，直接尝试 requests
            except httpx.HTTPStatusError as e:
                # HTTP状态错误不重试，直接抛出
                logger.error(f"[{self.site_name}] HTTP状态错误: {e.response.status_code}")
                raise
            except Exception as e:
                # 其他错误（包括 ReadTimeout）重试
                last_error = e
                logger.warning(
                    f"[{self.site_name}] 请求失败 (重试 {attempt}/{self.max_retries}): "
                    f"{type(e).__name__}: {e}"
                )
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay * attempt)

        # httpx 失败，尝试 fallback 到 requests
        if REQUESTS_AVAILABLE:
            logger.warning(f"[{self.site_name}] httpx 请求失败，尝试使用 requests 库...")
            try:
                return await self._make_request_with_requests(url, method, headers, **kwargs)
            except Exception as e:
                logger.error(f"[{self.site_name}] requests 也失败了: {e}")
                if last_error:
                    raise last_error
                raise

        # 如果 requests 不可用，抛出原始错误
        if last_error:
            raise last_error
        raise Exception(f"[{self.site_name}] 请求失败，未知错误")

    async def _make_request_with_httpx(
        self,
        url: str,
        method: str,
        headers: Dict[str, str],
        **kwargs,
    ) -> httpx.Response:
        """
        使用 httpx 发送请求

        Args:
            url: 请求URL
            method: 请求方法
            headers: 请求头
            **kwargs: 其他请求参数

        Returns:
            HTTP响应
        """
        async with httpx.AsyncClient(**self.client_config) as client:
            if method.upper() == "GET":
                response = await client.get(url, headers=headers, **kwargs)
            else:
                response = await client.post(url, headers=headers, **kwargs)
            response.raise_for_status()

            logger.info(
                f"[{self.site_name}] Response: status={response.status_code}, "
                f"content_length={len(response.content)} bytes"
            )
            return response

    async def _make_request_with_requests(
        self,
        url: str,
        method: str,
        headers: Dict[str, str],
        **kwargs,
    ) -> httpx.Response:
        """
        使用 requests 库发送请求（fallback方案）

        Args:
            url: 请求URL
            method: 请求方法
            headers: 请求头
            **kwargs: 其他请求参数

        Returns:
            模拟的httpx.Response对象
        """
        if not REQUESTS_AVAILABLE:
            raise ImportError("requests 库未安装")

        # 创建带重试的 session
        session = requests.Session()

        # 配置重试策略
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # 代理配置
        proxies = None
        if self.proxy_url:
            proxies = {
                "http": self.proxy_url,
                "https": self.proxy_url,
            }

        # 在线程池中执行同步请求
        loop = asyncio.get_event_loop()

        def do_request():
            try:
                if method.upper() == "GET":
                    return session.get(
                        url,
                        headers=headers,
                        proxies=proxies,
                        verify=self.verify_ssl,
                        timeout=30,
                    )
                else:
                    return session.post(
                        url,
                        headers=headers,
                        proxies=proxies,
                        verify=self.verify_ssl,
                        timeout=30,
                        **kwargs,
                    )
            finally:
                session.close()

        response = await loop.run_in_executor(None, do_request)

        logger.info(
            f"[{self.site_name}] [requests] Response: "
            f"status={response.status_code}, content_length={len(response.content)} bytes"
        )

        # 检查 Cloudflare 挑战
        if self._is_cloudflare_challenge(response.text):
            logger.error(f"[{self.site_name}] 检测到 Cloudflare 挑战，需要浏览器仿真")
            raise Exception("Cloudflare challenge detected, browser emulation required")

        response.raise_for_status()
        # print(response.content)

        # 转换为 httpx.Response 兼容对象
        return self._convert_requests_response(response)

    def _convert_requests_response(self, response: "requests.Response") -> httpx.Response:
        """
        将 requests.Response 转换为 httpx.Response 兼容对象

        Args:
            response: requests响应对象

        Returns:
            httpx.Response兼容对象
        """
        # 创建一个简单的包装类
        class ResponseWrapper:
            def __init__(self, requests_resp):
                self._resp = requests_resp
                self.status_code = requests_resp.status_code
                self.headers = requests_resp.headers
                self.text = requests_resp.text
                self.content = requests_resp.content
                self._content = requests_resp.content
                self.url = requests_resp.url
                self.http_version = "HTTP/1.1"

        return ResponseWrapper(response)

    def _is_cloudflare_challenge(self, html: str) -> bool:
        """检测是否是 Cloudflare 挑战页面"""
        if not html:
            return False
        cloudflare_indicators = [
            "cf-browser-verification",
            "cf_chl_opt",
            "challenge-platform",
            "Checking your browser",
            "DDoS protection by Cloudflare",
            "Ray ID:",
            "_cf_chl_tk",
        ]
        return any(indicator in html for indicator in cloudflare_indicators)

    async def authenticate(self) -> bool:
        """
        验证Cookie是否有效

        Returns:
            是否认证成功
        """
        try:
            if not self.cookie:
                logger.warning(f"[{self.site_name}] Cookie未配置")
                return False

            # 访问种子列表页面验证Cookie
            url = urljoin(self.base_url, self.torrents_page)
            response = await self._make_request(url)

            # 检查是否被重定向到登录页面
            if "login.php" in str(response.url) or "takelogin.php" in response.text:
                logger.warning(f"[{self.site_name}] Cookie已失效，需要重新登录")
                return False

            # 检查是否存在种子表格
            soup = BeautifulSoup(response.text, "html.parser")
            table = soup.select_one(self.selectors["torrent_table"])
            if not table:
                logger.warning(f"[{self.site_name}] 无法找到种子列表，可能Cookie无效")
                return False

            logger.info(f"[{self.site_name}] Cookie验证成功")
            return True

        except httpx.HTTPStatusError as e:
            logger.error(f"[{self.site_name}] HTTP错误: {e.response.status_code}")
            return False
        except Exception as e:
            logger.error(f"[{self.site_name}] 认证失败: {e}")
            return False

    async def fetch_resources(
        self, page: int = 1, limit: int = 50, **filters
    ) -> Dict[str, Any]:
        """
        获取资源列表

        Args:
            page: 页码（从1开始）
            limit: 每页数量（NexusPHP通常固定为50或100）
            **filters: 过滤条件
                - keyword: 搜索关键词
                - category: 分类ID
                - promotion: 促销类型

        Returns:
            包含资源列表和分页信息的字典
        """
        try:
            # 构建搜索URL
            url = self._build_search_url(page, **filters)
            logger.info(f"[{self.site_name}] 请求URL: {url} (filters: {filters})")

            response = await self._make_request(url)
            soup = BeautifulSoup(response.text, "html.parser")

            # 解析种子列表
            resources = self._parse_torrent_list(soup)

            # 解析分页信息
            pagination = self._parse_pagination(soup)

            return {
                "resources": resources,
                "total_pages": pagination.get("total_pages", 1),
                "total": pagination.get("total", len(resources)),
                "page_number": page,
                "page_size": len(resources),
            }

        except Exception as e:
            logger.error(f"[{self.site_name}] 获取资源列表失败: {e}")
            raise

    def _build_search_url(self, page: int = 1, **filters) -> str:
        """
        构建搜索URL

        支持的过滤参数：
        - keyword: 关键词搜索
        - category/categories: 分类过滤
        - promotion: 促销类型 (free, 2x, free2x)
        - sortField: 排序字段 (1-7: 标题/评论数/存活时间/大小/种子数/下载数/完成数)
        - sortDirection: 排序方向 (asc/desc)
        """
        url = urljoin(self.base_url, self.torrents_page)

        params = []

        # 页码
        if page > 1:
            # NexusPHP页码从0开始
            params.append(f"page={page - 1}")

        # 关键词搜索
        keyword = filters.get("keyword")
        if keyword:
            params.append(f"search={keyword}")

        # 分类过滤（支持 category 或 categories）
        category = filters.get("category") or filters.get("categories")
        if category:
            if isinstance(category, list):
                for cat in category:
                    params.append(f"cat{cat}=1")
            else:
                params.append(f"cat{category}=1")

        # 促销过滤
        promotion = filters.get("promotion")
        if promotion == "free":
            params.append("spstate=2")
        elif promotion == "2x":
            params.append("spstate=3")
        elif promotion == "free2x":
            params.append("spstate=4")

        # 排序字段 (1-7)
        sort_field = filters.get("sortField")
        if sort_field:
            params.append(f"sort={sort_field}")

        # 排序方向 (asc/desc)
        sort_direction = filters.get("sortDirection")
        if sort_direction:
            # 统一转换大小写
            params.append(f"type={sort_direction.lower()}")

        if params:
            url = f"{url}?{'&'.join(params)}"

        return url

    def _parse_torrent_list(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        解析种子列表页面

        Args:
            soup: BeautifulSoup对象

        Returns:
            种子列表
        """
        resources = []

        # 找到种子表格
        table = soup.select_one(self.selectors["torrent_table"])
        if not table:
            logger.warning(f"[{self.site_name}] 未找到种子表格")
            return resources

        # 遍历每一行
        rows = table.select(self.selectors["torrent_row"])
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
        """
        解析单行种子信息

        Args:
            row: BeautifulSoup元素（tr行）

        Returns:
            种子信息字典
        """
        # 标题和链接
        title_elem = row.select_one(self.selectors["title"])
        if not title_elem:
            return None

        title = title_elem.get_text(strip=True)
        detail_href = title_elem.get("href", "")

        # 提取种子ID
        torrent_id = self._extract_torrent_id(detail_href)
        if not torrent_id:
            return None

        # 副标题 - 改进解析逻辑
        subtitle = self._parse_subtitle(row, title_elem)

        # 分类
        category = MEDIA_TYPE_OTHER
        # 尝试使用配置的选择器
        category_elem = row.select_one(self.selectors["category"])

        # 如果选中了img但没成功提取ID，或者是通过宽泛选择器选中的
        cat_id = None
        if category_elem:
            cat_img_src = category_elem.get("src", "")
            cat_id = self._extract_category_id(cat_img_src)

            # try getting from parent a tag if img src fails
            if not cat_id:
                parent_a = category_elem.find_parent("a")
                if parent_a:
                     # 检查 href是否包含 cat=
                    href = parent_a.get("href", "")
                    match = re.search(r"cat=(\d+)", href)
                    if match:
                        cat_id = match.group(1)

        # Fallback: 如果上面的方法没找到，在整个行内查找 a[href*='cat=']
        if not cat_id:
            cat_link = row.select_one("a[href*='?cat=']") or row.select_one("a[href*='&cat=']")
            if cat_link:
                href = cat_link.get("href", "")
                match = re.search(r"cat=(\d+)", href)
                if match:
                    cat_id = match.group(1)

        if cat_id and self.category_map:
            category = self.category_map.get(cat_id, MEDIA_TYPE_OTHER)

        # Debug Log
        if category == MEDIA_TYPE_OTHER and cat_id:
             logger.debug(f"[{self.site_name}] Unmapped Category ID: {cat_id}")

        # NexusPHP 站点通常没有子分类概念
        subcategory = None

        # 大小 - 改进解析逻辑，遍历所有 td.rowfollow 找到包含大小信息的
        size_bytes = 0
        size_elem = row.select_one(self.selectors["size"])
        if size_elem:
            size_text = size_elem.get_text(strip=True)
            size_bytes = self._parse_size(size_text)

        # 如果默认选择器没找到，尝试遍历所有 td.rowfollow
        if size_bytes == 0:
            for td in row.select("td.rowfollow"):
                td_text = td.get_text(strip=True)
                if re.search(r"[\d.]+\s*(TB|GB|MB|KB)", td_text, re.IGNORECASE):
                    size_bytes = self._parse_size(td_text)
                    if size_bytes > 0:
                        break

        # 做种/下载/完成数
        seeders = self._parse_int(row.select_one(self.selectors["seeders"]))
        leechers = self._parse_int(row.select_one(self.selectors["leechers"]))
        completions = self._parse_int(row.select_one(self.selectors["completions"]))

        # 发布时间
        published_at = None
        time_elem = row.select_one(self.selectors["published_at"])
        if time_elem:
            time_title = time_elem.get("title") or time_elem.get_text(strip=True)
            published_at = self._parse_time(time_title)

        # 促销信息
        is_free = bool(row.select_one(self.selectors["free"]))
        is_double_up = bool(row.select_one(self.selectors["double_up"]))
        is_half_down = bool(row.select_one(self.selectors["half_down"]))

        # 确定促销类型
        promotion_type = "none"
        if is_free and is_double_up:
            promotion_type = "free_2x"
        elif is_free:
            promotion_type = "free"
        elif is_double_up:
            promotion_type = "2x"
        elif is_half_down:
            promotion_type = "50%"

        # 下载链接
        download_url = ""
        download_elem = row.select_one(self.selectors["download_link"])
        if download_elem:
            download_href = download_elem.get("href", "")
            download_url = urljoin(self.base_url, download_href)

        # 促销过期时间提取
        promotion_expire_at = None
        # 查找包含优惠剩余时间的元素
        try:
            embedded_td = row.select_one("td.embedded")
            if embedded_td:
                for span in embedded_td.find_all("span", attrs={"title": True}):
                    title_val = span.get("title", "")
                    # 验证格式 YYYY-MM-DD HH:MM:SS
                    if re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", title_val):
                        # 检查上下文: span文本只是时间，关键词在父级或更上层
                        # 检查span的直接父级（例如 <b>）
                        parent = span.parent
                        # 检查span的父级的父级（例如 subtitle 容器）
                        grandparent = parent.parent if parent else None
                        
                        context_text = ""
                        if parent:
                            context_text += parent.get_text()
                        if grandparent:
                            context_text += grandparent.get_text()
                        
                        # 检查前一个兄弟文本节点（针对 <b> 前面的文本）
                        prev_sibling = span.previous_sibling
                        if prev_sibling and isinstance(prev_sibling, str):
                            context_text += prev_sibling
                        
                        if parent and parent.previous_sibling and isinstance(parent.previous_sibling, str):
                            context_text += parent.previous_sibling

                        if "优惠" in context_text or "剩余" in context_text:
                            promotion_expire_at = self._parse_time(title_val)
                            break
        except Exception as e:
            logger.debug(f"[{self.site_name}] 提取促销过期时间失败: {e}")

        # 从列表页解析豆瓣/IMDB信息
        douban_id, douban_rating = self._parse_douban_info(row)
        imdb_id, imdb_rating = self._parse_imdb_info(row)

        # 电视剧信息解析
        tv_info = None
        if category in (MEDIA_TYPE_TV, MEDIA_TYPE_ANIME):
            tv_info = extract_tv_info(title, subtitle)

        return {
            "torrent_id": torrent_id,
            "title": title,
            "subtitle": subtitle,
            "category": category,
            "original_category_id": cat_id,
            "subcategory": subcategory,
            "size_bytes": size_bytes,
            "seeders": seeders,
            "leechers": leechers,
            "completions": completions,
            "published_at": published_at,
            "is_free": is_free,
            "is_double_upload": is_double_up,
            "is_discount": is_half_down,
            "promotion_type": promotion_type,
            "promotion_expire_at": promotion_expire_at,
            "download_url": download_url,
            "detail_url": urljoin(self.base_url, detail_href),
            "tv_info": tv_info,
            "detail_fetched": False,
            "douban_id": douban_id,
            "douban_rating": douban_rating,
            "imdb_id": imdb_id,
            "imdb_rating": imdb_rating,
        }

    def _parse_subtitle(self, row, title_elem) -> str:
        """
        解析副标题

        NexusPHP 站点副标题通常在 td.embedded 中，位于标题链接 <a> 标签之后。
        常见结构：
        1. <td class="embedded"><a>标题</a><br/><span>副标题</span></td>
        2. <td class="embedded"><a>标题</a><span>副标题</span></td>

        Args:
            row: BeautifulSoup元素（tr行）
            title_elem: 标题元素

        Returns:
            副标题字符串
        """
        subtitle = ""

        # 查找 td.embedded
        embedded_td = row.select_one("td.embedded")
        if not embedded_td:
            embedded_td = row.select_one("table.torrentname td.embedded")

        if not embedded_td:
            return subtitle

        # 获取标题文本用于排除
        title_text = title_elem.get_text(strip=True) if title_elem else ""

        # 方法1：查找 td.embedded 的直接子元素 span（在 <a> 标签之后）
        # 遍历直接子元素，跳过 <a> 标签内的 span
        found_title_link = False
        for child in embedded_td.children:
            # 检查是否是标题链接
            if hasattr(child, "name") and child.name == "a":
                href = child.get("href", "")
                if "details.php" in href:
                    found_title_link = True
                    continue

            # 跳过 br 标签
            if hasattr(child, "name") and child.name == "br":
                continue

            # 只在找到标题链接之后处理 span
            if found_title_link and hasattr(child, "name") and child.name == "span":
                span_class = child.get("class", [])
                # 排除标签类（optiontag）
                if span_class and "optiontag" in span_class:
                    continue

                text = child.get_text(strip=True)
                # 排除与标题相同的文本
                if text and text != title_text:
                    # 清理文本，移除促销时间等信息
                    text = re.sub(r"\[优惠剩余时间：.*?\]", "", text).strip()
                    if text:
                        subtitle = text
                        break

        # 方法2：如果方法1没找到，尝试查找较长的直接子 span
        if not subtitle:
            for child in embedded_td.children:
                if not hasattr(child, "name") or child.name != "span":
                    continue

                span_class = child.get("class", [])
                if span_class and "optiontag" in span_class:
                    continue

                text = child.get_text(strip=True)
                # 副标题通常较长（>15字符）且不等于标题
                if text and len(text) > 15 and text != title_text:
                    text = re.sub(r"\[优惠剩余时间：.*?\]", "", text).strip()
                    if text:
                        subtitle = text
                        break

        return subtitle

    def _parse_douban_info(self, row) -> tuple:
        """
        从列表页解析豆瓣信息

        Args:
            row: BeautifulSoup元素（tr行）

        Returns:
            (douban_id, douban_rating) 元组
        """
        douban_id = None
        douban_rating = None

        # 查找豆瓣链接
        douban_elem = row.select_one("a[href*='douban.com/subject']")
        if douban_elem:
            href = douban_elem.get("href", "")
            # 提取豆瓣 ID
            match = re.search(r"subject/(\d+)", href)
            if match:
                douban_id = match.group(1)

            # 提取评分（链接文本中的数字）
            text = douban_elem.get_text(strip=True)
            rating_match = re.search(r"([\d.]+)", text)
            if rating_match:
                try:
                    rating = float(rating_match.group(1))
                    # 验证评分范围（豆瓣评分0-10）
                    if 0 <= rating <= 10:
                        douban_rating = rating
                except (ValueError, TypeError):
                    pass

        return douban_id, douban_rating

    def _parse_imdb_info(self, row) -> tuple:
        """
        从列表页解析 IMDB 信息

        Args:
            row: BeautifulSoup元素（tr行）

        Returns:
            (imdb_id, imdb_rating) 元组
        """
        imdb_id = None
        imdb_rating = None

        # 查找 IMDB 链接
        imdb_elem = row.select_one("a[href*='imdb.com/title']")
        if imdb_elem:
            href = imdb_elem.get("href", "")
            # 提取 IMDB ID (tt开头的ID)
            match = re.search(r"(tt\d+)", href)
            if match:
                imdb_id = match.group(1)

            # 提取评分（链接文本中的数字）
            text = imdb_elem.get_text(strip=True)
            rating_match = re.search(r"([\d.]+)", text)
            if rating_match:
                try:
                    rating = float(rating_match.group(1))
                    # 验证评分范围（IMDB评分0-10）
                    if 0 <= rating <= 10:
                        imdb_rating = rating
                except (ValueError, TypeError):
                    pass

        return imdb_id, imdb_rating

    def _extract_torrent_id(self, href: str) -> Optional[str]:
        """从链接中提取种子ID"""
        if not href:
            return None

        # 尝试从URL参数中提取
        parsed = urlparse(href)
        params = parse_qs(parsed.query)
        if "id" in params:
            return params["id"][0]

        # 尝试正则匹配
        match = re.search(r"id=(\d+)", href)
        if match:
            return match.group(1)

        return None

    def _extract_category_id(self, src: str) -> Optional[str]:
        """从分类图片src中提取分类ID"""
        if not src:
            return None

        # 常见格式：/pic/category/401.gif 或 cat401.gif
        match = re.search(r"(\d{3})\.(?:gif|png|jpg)", src)
        if match:
            return match.group(1)

        return None

    def _parse_size(self, size_text: str) -> int:
        """解析文件大小为字节数"""
        if not size_text:
            return 0

        size_text = size_text.upper().strip()

        # 匹配数字和单位
        match = re.search(r"([\d.]+)\s*(TB|GB|MB|KB|B)", size_text)
        if not match:
            return 0

        value = float(match.group(1))
        unit = match.group(2)

        multipliers = {
            "TB": 1024 ** 4,
            "GB": 1024 ** 3,
            "MB": 1024 ** 2,
            "KB": 1024,
            "B": 1,
        }

        return int(value * multipliers.get(unit, 1))

    def _parse_int(self, elem) -> int:
        """从元素中解析整数"""
        if not elem:
            return 0

        text = elem.get_text(strip=True)
        # 移除逗号和空格
        text = re.sub(r"[,\s]", "", text)

        try:
            return int(text)
        except (ValueError, TypeError):
            return 0

    def _parse_time(self, time_str: str) -> Optional[datetime]:
        """解析时间字符串"""
        if not time_str:
            return None

        try:
            return parse_pt_site_time(time_str)
        except Exception:
            pass

        # 尝试常见格式
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
            "%m-%d %H:%M",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(time_str.strip(), fmt)
            except ValueError:
                continue

        return None

    def _parse_pagination(self, soup: BeautifulSoup) -> Dict[str, int]:
        """
        解析分页信息

        Args:
            soup: BeautifulSoup对象

        Returns:
            包含 total_pages 和 total 的字典
        """
        pagination = {"total_pages": 1, "total": 0}

        # 尝试从分页元素获取
        pager = soup.select_one("p.nexus-pagination, div.pagination, td.embedded")
        if pager:
            # 查找最大页码
            page_links = pager.select("a[href*='page=']")
            max_page = 1
            for link in page_links:
                href = link.get("href", "")
                match = re.search(r"page=(\d+)", href)
                if match:
                    page_num = int(match.group(1)) + 1  # NexusPHP页码从0开始
                    max_page = max(max_page, page_num)

            pagination["total_pages"] = max_page

            # 查找总数
            text = pager.get_text()
            total_match = re.search(r"共\s*(\d+)\s*条", text)
            if total_match:
                pagination["total"] = int(total_match.group(1))

        return pagination

    async def get_resource_detail(self, resource_id: str) -> Dict[str, Any]:
        """
        获取资源详情

        Args:
            resource_id: 种子ID

        Returns:
            资源详情字典
        """
        try:
            url = f"{urljoin(self.base_url, self.details_page)}?id={resource_id}"
            response = await self._make_request(url)
            soup = BeautifulSoup(response.text, "html.parser")

            detail = {
                "torrent_id": resource_id,
                "detail_fetched": True,
            }

            # 描述
            desc_elem = soup.select_one(self.selectors["detail_description"])
            if desc_elem:
                detail["description"] = desc_elem.get_text(strip=True)

            # MediaInfo
            mediainfo_elem = soup.select_one(self.selectors["detail_mediainfo"])
            if mediainfo_elem:
                detail["mediainfo"] = mediainfo_elem.get_text(strip=True)

            # IMDB链接
            imdb_elem = soup.select_one(self.selectors["detail_imdb"])
            if imdb_elem:
                imdb_href = imdb_elem.get("href", "")
                imdb_match = re.search(r"tt\d+", imdb_href)
                if imdb_match:
                    detail["imdb_id"] = imdb_match.group(0)

            # 豆瓣链接
            douban_elem = soup.select_one(self.selectors["detail_douban"])
            if douban_elem:
                douban_href = douban_elem.get("href", "")
                douban_match = re.search(r"subject/(\d+)", douban_href)
                if douban_match:
                    detail["douban_id"] = douban_match.group(1)

            return detail

        except Exception as e:
            logger.error(f"[{self.site_name}] 获取资源详情失败: {e}")
            raise

    async def _get_download_url_from_details(self, resource_id: str) -> str:
        """
        从详情页面获取完整的下载链接（包含 sign 等认证参数）

        某些 NexusPHP 站点（如 HDSky）的下载链接需要 sign 参数，
        这个参数只能从详情页面获取。

        Args:
            resource_id: 种子ID

        Returns:
            完整的下载链接，如果获取失败返回空字符串
        """
        try:
            url = f"{urljoin(self.base_url, self.details_page)}?id={resource_id}"
            logger.info(f"[{self.site_name}] 从详情页面获取下载链接: {url}")
            response = await self._make_request(url)
            soup = BeautifulSoup(response.text, "html.parser")

            # 方式1: 查找带 passkey 的直接下载链接（优先，更稳定）
            # 格式: download.php?id=xxx&passkey=xxx&sign=xxx
            passkey_link = soup.select_one('a[href*="download.php"][href*="passkey="]')
            if passkey_link:
                href = passkey_link.get("href", "")
                if href:
                    full_url = urljoin(self.base_url, href)
                    logger.info(f"[{self.site_name}] 找到带 passkey 的下载链接")
                    return full_url

            # 方式2: 查找表单提交方式的下载链接
            # 格式: download.php?id=xxx&t=xxx&sign=xxx
            form = soup.select_one('form[action*="download.php"]')
            if form:
                action = form.get("action", "")
                if action and "sign=" in action:
                    full_url = urljoin(self.base_url, action)
                    logger.info(f"[{self.site_name}] 找到表单下载链接")
                    return full_url

            # 方式3: 查找任何带 sign 参数的下载链接
            sign_link = soup.select_one('a[href*="download.php"][href*="sign="]')
            if sign_link:
                href = sign_link.get("href", "")
                if href:
                    full_url = urljoin(self.base_url, href)
                    logger.info(f"[{self.site_name}] 找到带 sign 的下载链接")
                    return full_url

            logger.warning(f"[{self.site_name}] 详情页面未找到完整下载链接")
            return ""

        except Exception as e:
            logger.error(f"[{self.site_name}] 从详情页面获取下载链接失败: {e}")
            return ""

    async def download_torrent(self, resource_id: str, download_url: str = None) -> bytes:
        """
        下载种子文件

        NexusPHP站点下载种子的认证方式：
        1. 使用 Cookie 认证（通过请求头传递）
        2. 使用 passkey 参数（URL中添加）
        3. 使用 sign 参数（某些站点如 HDSky 需要）
        4. 以上组合使用（更可靠）

        如果链接不包含必要认证参数，则从详情页面获取。

        Args:
            resource_id: 种子ID
            download_url: 完整下载URL（可选，从资源记录获取）

        Returns:
            种子文件字节流
        """
        try:
            # 构建下载URL
            url = None

            if download_url:
                # 检查下载链接是否包含必要的认证参数
                has_passkey = "passkey=" in download_url
                has_sign = "sign=" in download_url

                if has_passkey or has_sign:
                    # 链接已包含认证参数，直接使用
                    url = download_url
                    logger.info(f"[{self.site_name}] 使用已有的完整下载链接")
                else:
                    # 链接不完整，尝试从详情页面获取
                    logger.info(f"[{self.site_name}] 下载链接缺少认证参数，尝试从详情页面获取")
                    detail_url = await self._get_download_url_from_details(resource_id)
                    if detail_url:
                        url = detail_url
                    else:
                        # 回退：使用原链接并添加 passkey
                        url = download_url
                        if self.passkey and "passkey=" not in url:
                            separator = "&" if "?" in url else "?"
                            url = f"{url}{separator}passkey={self.passkey}"
                        logger.warning(f"[{self.site_name}] 使用回退方式构建下载链接")
            else:
                # 没有传入下载链接，尝试从详情页面获取
                detail_url = await self._get_download_url_from_details(resource_id)
                if detail_url:
                    url = detail_url
                else:
                    # 回退：自行构建下载URL
                    base_download_url = urljoin(self.base_url, self.download_page)
                    if self.passkey:
                        url = f"{base_download_url}?id={resource_id}&passkey={self.passkey}"
                    else:
                        url = f"{base_download_url}?id={resource_id}"
                    logger.warning(f"[{self.site_name}] 使用回退方式构建下载链接")

            logger.info(f"[{self.site_name}] 下载种子: {self._mask_url(url)}")

            response = await self._make_request(url)

            # 检查响应内容
            content = response.content

            if b"download" in content.lower() and b"torrent" in content.lower():
                # 可能是首次下载确认页面
                if "下载种子文件".encode("utf-8") in content or b"first time" in content.lower():
                    logger.info(f"[{self.site_name}] 检测到首次下载确认页面，尝试跳过...")
                    content = await self._handle_first_download_page(url, content)

            # 验证是否为种子文件（种子文件以 'd' 开头，是 bencode 格式）
            if not content.startswith(b"d"):
                # 检查是否返回了HTML错误页面
                if b"<html" in content.lower() or b"<!doctype" in content.lower():
                    # 尝试从HTML中提取错误信息
                    error_msg = self._extract_error_from_html(content)
                    logger.error(f"[{self.site_name}] 下载返回HTML页面: {error_msg}")
                    raise ValueError(f"下载失败: {error_msg}")
                logger.error(f"[{self.site_name}] 下载的内容不是有效的种子文件")
                raise ValueError("下载的内容不是有效的种子文件")

            logger.info(f"[{self.site_name}] 种子下载成功: {len(content)} bytes")
            return content

        except Exception as e:
            logger.error(f"[{self.site_name}] 下载种子失败: {e}")
            raise

    def _mask_url(self, url: str) -> str:
        """掩码URL中的敏感信息（passkey、sign）"""
        if not url:
            return url
        url = re.sub(r"passkey=[a-zA-Z0-9]+", "passkey=***", url)
        url = re.sub(r"sign=[a-zA-Z0-9]+", "sign=***", url)
        return url

    def _extract_error_from_html(self, content: bytes) -> str:
        """从HTML响应中提取错误信息"""
        try:
            text = content.decode("utf-8", errors="ignore")
            soup = BeautifulSoup(text, "html.parser")
            # 尝试找到错误消息
            error_elem = soup.select_one("h2, .error, #error, .warning, .alert")
            if error_elem:
                return error_elem.get_text(strip=True)[:200]
            # 提取body文本
            body = soup.select_one("body")
            if body:
                return body.get_text(strip=True)[:200]
            return "未知错误"
        except Exception:
            return "解析错误页面失败"

    async def _handle_first_download_page(self, url: str, content: bytes) -> bytes:
        """
        处理首次下载确认页面

        Args:
            url: 原始下载URL
            content: 确认页面内容

        Returns:
            种子文件字节流
        """
        try:
            text = content.decode("utf-8", errors="ignore")
            # 查找表单
            forms = re.findall(r'<form.*?action="(.*?)".*?>(.*?)</form>', text, re.S)
            for action, form_content in forms:
                if action == "?" or not action:
                    action = url
                # 解析表单输入
                inputs = re.findall(r'<input.*?name="(.*?)".*?value="(.*?)".*?>', form_content, re.S)
                if inputs:
                    data = {name: value for name, value in inputs}
                    logger.info(f"[{self.site_name}] 提交首次下载确认表单...")
                    # POST 提交表单
                    if REQUESTS_AVAILABLE and self.prefer_requests:
                        response = await self._make_request_with_requests(
                            action, "POST", self._get_headers(), data=data
                        )
                    else:
                        async with httpx.AsyncClient(**self.client_config) as client:
                            response = await client.post(
                                action, headers=self._get_headers(), data=data
                            )
                    if response.content.startswith(b"d"):
                        logger.info(f"[{self.site_name}] 首次下载确认成功")
                        return response.content
            # 未能处理，返回原始内容
            return content
        except Exception as e:
            logger.warning(f"[{self.site_name}] 处理首次下载确认失败: {e}")
            return content

    async def health_check(self) -> bool:
        """
        健康检查

        Returns:
            站点是否正常
        """
        try:
            result = await self.fetch_resources(page=1, limit=1)
            return len(result.get("resources", [])) > 0
        except Exception as e:
            logger.error(f"[{self.site_name}] 健康检查失败: {e}")
            return False

    async def fetch_categories(self) -> List[Dict[str, Any]]:
        """
        获取站点分类列表

        NexusPHP站点没有分类API，从预设配置中获取分类信息。
        返回格式与 MTeam API 兼容，以便统一使用 sync_site_categories 处理。

        Returns:
            分类数据列表，格式：[{id, nameChs, nameEng, order, ...}, ...]
        """
        categories = []

        if not self.preset:
            logger.warning(f"[{self.site_name}] 无预设配置，无法获取分类信息")
            return categories

        category_details = self.preset.get("category_details", {})
        if not category_details:
            logger.warning(f"[{self.site_name}] 预设中无 category_details 配置")
            return categories

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
                # 保留 mapped_category 供 sync_site_categories 使用
                "_mapped_category": details.get("mapped_category"),
            })
            order += 1

        logger.info(f"[{self.site_name}] 从预设加载 {len(categories)} 个分类")
        return categories

    async def load_category_mappings(self, db) -> None:
        """
        从数据库加载分类映射

        Args:
            db: 数据库会话
        """
        if self.category_map:
            return
        pass


class HDSkyAdapter(NexusPHPAdapter):
    """
    天空站（HDSky）适配器

    继承自NexusPHP通用适配器，处理HDSky特有的配置
    """

    def __init__(self, config: Dict[str, Any], metadata_mappings: Optional[Dict] = None):
        config["preset_id"] = "hdsky"
        super().__init__(config, metadata_mappings)


class CHDBitsAdapter(NexusPHPAdapter):
    """
    彩虹岛（CHDBits）适配器
    """

    def __init__(self, config: Dict[str, Any], metadata_mappings: Optional[Dict] = None):
        config["preset_id"] = "chdbits"
        super().__init__(config, metadata_mappings)


class PTHomeAdapter(NexusPHPAdapter):
    """
    铂金家（PTHome）适配器
    """

    def __init__(self, config: Dict[str, Any], metadata_mappings: Optional[Dict] = None):
        config["preset_id"] = "pthome"
        super().__init__(config, metadata_mappings)


class OurBitsAdapter(NexusPHPAdapter):
    """
    我堡（OurBits）适配器
    """

    def __init__(self, config: Dict[str, Any], metadata_mappings: Optional[Dict] = None):
        config["preset_id"] = "ourbits"
        super().__init__(config, metadata_mappings)


__all__ = [
    "NexusPHPAdapter",
    "HDSkyAdapter",
    "CHDBitsAdapter",
    "PTHomeAdapter",
    "OurBitsAdapter",
]
