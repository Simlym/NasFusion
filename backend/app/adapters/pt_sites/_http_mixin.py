# -*- coding: utf-8 -*-
"""
PT 站点适配器共享 HTTP 基础设施

将原本只存在于 NexusPHPAdapter 的请求基础设施抽出为 mixin，供 NexusPHP /
Unit3D / GenericJSONAPI 等多个适配器复用：

- httpx 异步请求 + requests 同步 fallback（代理/TLS 场景更稳）
- 重试与退避
- Cloudflare 挑战检测
- 速率限制
- 代理 URL 构建与脱敏
- 通用解析工具（size / int / time）

宿主类需在 __init__ 中调用 self._init_http(config) 初始化相关属性，
并可 override _get_headers() 定制鉴权头（Cookie / x-api-key / Bearer / CSRF）。
"""
import asyncio
import logging
import re
from datetime import datetime
from typing import Any, Dict, Optional

import httpx

from app.utils.timezone import parse_pt_site_time

# requests 作为 fallback（某些代理场景下 httpx 的 TLS 握手可能失败）
try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

logger = logging.getLogger(__name__)

# 禁用 SSL 警告（仅在开发/调试时使用）
try:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except ImportError:
    pass


class HttpClientMixin:
    """
    共享 HTTP 请求基础设施。

    依赖宿主类（通过 _init_http 设置）的属性：
        self.site_name, self.base_url, self.cookie, self.user_agent,
        self.verify_ssl, self.proxy_config, self.proxy_url, self.client_config,
        self.request_interval, self.max_retries, self.retry_delay,
        self.prefer_requests, self._last_request_time
    """

    def _init_http(self, config: Dict[str, Any]) -> None:
        """
        初始化 HTTP 相关属性。宿主类 __init__ 中调用。

        Args:
            config: 站点配置字典
        """
        # 鉴权（Cookie 默认从 auth_cookie 读取；JSON-API 子类可另行处理 api_key）
        self.cookie = config.get("auth_cookie", "")
        self.proxy_config = config.get("proxy_config") or {}
        self.request_interval = config.get("request_interval", 5)
        self._last_request_time = 0.0

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

    async def _wait_for_rate_limit(self):
        """等待速率限制"""
        current_time = asyncio.get_event_loop().time()
        time_since_last = current_time - self._last_request_time
        if time_since_last < self.request_interval:
            await asyncio.sleep(self.request_interval - time_since_last)
        self._last_request_time = asyncio.get_event_loop().time()

    def _get_headers(self) -> Dict[str, str]:
        """
        获取请求头 - 模拟完整浏览器请求。

        子类可 override 注入不同鉴权头（如 x-api-key / Authorization / CSRF）。
        """
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
        """
        await self._wait_for_rate_limit()

        headers = self._get_headers()
        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))

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
        """使用 httpx 发送请求"""
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
        """使用 requests 库发送请求（fallback方案）"""
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

        # 转换为 httpx.Response 兼容对象
        return self._convert_requests_response(response)

    def _convert_requests_response(self, response: "requests.Response") -> httpx.Response:
        """将 requests.Response 转换为 httpx.Response 兼容对象"""

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

            def json(self):
                return self._resp.json()

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

    # ==================== 通用解析工具 ====================

    def _parse_size(self, size_text: str) -> int:
        """解析文件大小为字节数（兼容 IEC 单位 TiB/GiB 等）"""
        if not size_text:
            return 0

        size_text = size_text.upper().strip()

        # 同时匹配 GB 与 GIB（IEC），其中 I 可选
        match = re.search(r"([\d.]+)\s*(T|G|M|K)?I?B", size_text)
        if not match:
            return 0

        value = float(match.group(1))
        unit = (match.group(2) or "") + "B"  # 无前缀 -> "B"

        multipliers = {
            "TB": 1024 ** 4,
            "GB": 1024 ** 3,
            "MB": 1024 ** 2,
            "KB": 1024,
            "B": 1,
        }

        return int(value * multipliers.get(unit, 1))

    @staticmethod
    def _parse_size_text(size_text: str) -> int:
        """
        解析大小文本为字节数（兼容 TiB/GiB 等格式）

        Args:
            size_text: 如 "1.5 TB", "500 GB"
        """
        size_text = size_text.replace(",", "").strip()
        match = re.match(r"([\d.]+)\s*([TGMKPI]+B)", size_text, re.IGNORECASE)
        if not match:
            match = re.match(r"([\d.]+)\s*([TGMKB]+)", size_text, re.IGNORECASE)
        if not match:
            return 0

        value = float(match.group(1))
        unit = match.group(2).upper().replace("I", "")

        units = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4, "PB": 1024**5}
        return int(value * units.get(unit, 1))

    def _parse_int(self, elem) -> int:
        """从元素中解析整数（接受 BeautifulSoup 元素或字符串）"""
        if elem is None:
            return 0

        text = elem if isinstance(elem, str) else elem.get_text(strip=True)
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


__all__ = ["HttpClientMixin", "REQUESTS_AVAILABLE"]
