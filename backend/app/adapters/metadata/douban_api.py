# -*- coding: utf-8 -*-
"""
豆瓣API客户端

基于Frodo移动端API实现，使用HMAC-SHA1签名认证
"""
import base64
import hashlib
import hmac
import logging
from datetime import datetime
from functools import lru_cache
from random import choice
from typing import Optional, Dict, Any, List
from urllib import parse

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


# 简单的TTL缓存装饰器
class TTLCache:
    """带TTL的LRU缓存"""

    def __init__(self, maxsize: int = 128, ttl: int = 3600):
        """
        Args:
            maxsize: 最大缓存数量
            ttl: 缓存过期时间（秒）
        """
        self.maxsize = maxsize
        self.ttl = ttl
        self.cache = {}
        self.timestamps = {}

    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        if key not in self.cache:
            return None

        # 检查是否过期
        if datetime.now().timestamp() - self.timestamps[key] > self.ttl:
            del self.cache[key]
            del self.timestamps[key]
            return None

        return self.cache[key]

    def set(self, key: str, value: Any) -> None:
        """设置缓存"""
        # 如果缓存已满，删除最旧的项
        if len(self.cache) >= self.maxsize and key not in self.cache:
            oldest_key = min(self.timestamps, key=self.timestamps.get)
            del self.cache[oldest_key]
            del self.timestamps[oldest_key]

        self.cache[key] = value
        self.timestamps[key] = datetime.now().timestamp()

    def clear(self) -> None:
        """清空缓存"""
        self.cache.clear()
        self.timestamps.clear()


class DoubanApiException(Exception):
    """豆瓣API异常基类"""
    pass


class DoubanRateLimitException(DoubanApiException):
    """豆瓣API速率限制异常"""
    pass


class DoubanApi:
    """
    豆瓣Frodo API客户端

    使用移动端API接口，通过HMAC-SHA1签名认证
    """

    # API端点映射
    _urls = {
        # 搜索
        "search": "/search/weixin",
        "search_subject": "/search/subjects",
        "movie_search": "/search/movie",
        "tv_search": "/search/movie",
        "imdbid": "/movie/imdb/%s",

        # 详情
        "movie_detail": "/movie/",
        "tv_detail": "/tv/",
        "movie_celebrities": "/movie/%s/celebrities",
        "tv_celebrities": "/tv/%s/celebrities",
        "movie_photos": "/movie/%s/photos",
        "tv_photos": "/tv/%s/photos",

        # 推荐
        "movie_recommendations": "/movie/%s/recommendations",
        "tv_recommendations": "/tv/%s/recommendations",

        # 热门/榜单 - 电影
        "movie_hot_gaia": "/subject_collection/movie_hot_gaia/items",
        "movie_showing": "/subject_collection/movie_showing/items",
        "movie_soon": "/subject_collection/movie_soon/items",
        "movie_top250": "/subject_collection/movie_top250/items",
        "movie_scifi": "/subject_collection/movie_scifi/items",
        "movie_comedy": "/subject_collection/movie_comedy/items",
        "movie_action": "/subject_collection/movie_action/items",
        "movie_love": "/subject_collection/movie_love/items",

        # 热门/榜单 - 剧集
        "tv_hot": "/subject_collection/tv_hot/items",
        "tv_domestic": "/subject_collection/tv_domestic/items",
        "tv_american": "/subject_collection/tv_american/items",
        "tv_japanese": "/subject_collection/tv_japanese/items",
        "tv_korean": "/subject_collection/tv_korean/items",
        "tv_animation": "/subject_collection/tv_animation/items",
        "tv_variety_show": "/subject_collection/tv_variety_show/items",
        "tv_chinese_best_weekly": "/subject_collection/tv_chinese_best_weekly/items",
        "tv_global_best_weekly": "/subject_collection/tv_global_best_weekly/items",

        # 热门/榜单 - 综艺
        "show_hot": "/subject_collection/show_hot/items",
        "show_domestic": "/subject_collection/show_domestic/items",
        "show_foreign": "/subject_collection/show_foreign/items",

        # 人物
        "person_detail": "/elessar/subject/",
        "celebrity_detail": "/movie/celebrity/%s",
    }

    # User-Agent列表（模拟Android客户端）
    _user_agents = [
        "api-client/1 com.douban.frodo/7.22.0.beta9(231) Android/23 product/Mate 40 vendor/HUAWEI model/Mate 40 brand/HUAWEI  rom/android  network/wifi  platform/AndroidPad",
        "api-client/1 com.douban.frodo/7.18.0(230) Android/22 product/MI 9 vendor/Xiaomi model/MI 9 brand/Android  rom/miui6  network/wifi  platform/mobile nd/1",
        "api-client/1 com.douban.frodo/7.1.0(205) Android/29 product/perseus vendor/Xiaomi model/Mi MIX 3  rom/miui6  network/wifi  platform/mobile nd/1",
        "api-client/1 com.douban.frodo/7.3.0(207) Android/22 product/MI 9 vendor/Xiaomi model/MI 9 brand/Android  rom/miui6  network/wifi platform/mobile nd/1",
    ]

    # API密钥（从配置读取，默认使用开源社区公开密钥）
    _api_secret_key = settings.DOUBAN_API_SECRET
    _api_key = settings.DOUBAN_API_KEY
    _api_key2 = settings.DOUBAN_API_KEY2  # 用于POST请求

    # API基础URL
    _frodo_url = "https://frodo.douban.com/api/v2"
    _official_url = "https://api.douban.com/v2"

    def __init__(self, timeout: int = 30, proxy_url: Optional[str] = None, cache_ttl: int = 3600):
        """
        初始化豆瓣API客户端

        Args:
            timeout: 请求超时时间（秒）
            proxy_url: 代理URL（可选）
            cache_ttl: 缓存过期时间（秒，默认1小时）
        """
        self.timeout = timeout
        self.proxy_url = proxy_url

        # 初始化缓存
        self._cache = TTLCache(maxsize=256, ttl=cache_ttl)

        # 复用的 HTTP 客户端（延迟初始化）
        self._client: Optional[httpx.AsyncClient] = None

    @classmethod
    def _sign(cls, url: str, ts: str, method: str = "GET") -> str:
        """
        生成HMAC-SHA1签名

        Args:
            url: 请求URL
            ts: 时间戳（格式：YYYYMMDD）
            method: HTTP方法

        Returns:
            Base64编码的签名字符串
        """
        url_path = parse.urlparse(url).path
        raw_sign = "&".join([method.upper(), parse.quote(url_path, safe=""), ts])
        return base64.b64encode(
            hmac.new(
                cls._api_secret_key.encode(),
                raw_sign.encode(),
                hashlib.sha1
            ).digest()
        ).decode()

    def _get_client_config(self) -> Dict[str, Any]:
        """
        获取HTTP客户端配置

        Returns:
            httpx客户端配置字典
        """
        config = {
            "timeout": httpx.Timeout(self.timeout),
            "follow_redirects": True,
            # 连接池优化：复用连接
            "limits": httpx.Limits(max_keepalive_connections=5, max_connections=10),
            "verify": False,
        }

        if self.proxy_url:
            config["proxy"] = self.proxy_url

        return config

    async def _get_or_create_client(self) -> httpx.AsyncClient:
        """
        获取或创建复用的 HTTP 客户端

        Returns:
            httpx.AsyncClient 实例
        """
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(**self._get_client_config())
            logger.debug("创建新的 HTTP 客户端（复用连接模式）")
        return self._client

    async def close(self) -> None:
        """
        关闭 HTTP 客户端，释放资源

        应在不再使用时调用（如应用关闭时）
        """
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            logger.debug("HTTP 客户端已关闭")

    async def __aenter__(self):
        """支持异步上下文管理器"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """退出时自动关闭客户端"""
        await self.close()

    def _prepare_get_params(self, url: str, **kwargs) -> tuple[str, Dict[str, Any], Dict[str, str]]:
        """
        准备GET请求参数

        Args:
            url: API端点路径
            **kwargs: 额外参数

        Returns:
            (完整URL, 请求参数, 请求头)
        """
        req_url = self._frodo_url + url

        # 构建参数
        params = {"apiKey": self._api_key}
        if kwargs:
            params.update(kwargs)

        # 获取时间戳
        ts = params.pop("_ts", datetime.strftime(datetime.now(), "%Y%m%d"))

        # 添加签名参数
        params.update({
            "os_rom": "android",
            "apiKey": self._api_key,
            "_ts": ts,
            "_sig": self._sign(url=req_url, ts=ts),
        })

        # 构建请求头
        headers = {
            "User-Agent": choice(self._user_agents),
            "Accept": "*/*",
            "Connection": "keep-alive",
        }

        return req_url, params, headers

    def _prepare_post_params(self, url: str, **kwargs) -> tuple[str, Dict[str, Any], Dict[str, str]]:
        """
        准备POST请求参数（用于IMDB查询）

        Args:
            url: API端点路径
            **kwargs: 额外参数

        Returns:
            (完整URL, 请求数据, 请求头)
        """
        req_url = self._official_url + url

        # 构建数据
        data = {"apikey": self._api_key2}
        if kwargs:
            data.update(kwargs)

        # 移除时间戳（POST请求不需要）
        data.pop("_ts", None)

        # 构建请求头
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
            "Cookie": "bid=J9zb1zA5sJc",  # 基本的Cookie
        }

        return req_url, data, headers

    def _check_rate_limit(self, response_data: Dict[str, Any]) -> None:
        """
        检查是否触发速率限制

        Args:
            response_data: API响应数据

        Raises:
            DoubanRateLimitException: 触发速率限制时抛出
        """
        if isinstance(response_data, dict):
            msg = response_data.get("msg", "")
            if "subject_ip_rate_limit" in msg or "search_access_rate_limit" in msg:
                raise DoubanRateLimitException(f"豆瓣API速率限制: {msg}")

    def _make_cache_key(self, url: str, **kwargs) -> str:
        """
        生成缓存键

        Args:
            url: API端点路径
            **kwargs: 请求参数

        Returns:
            缓存键字符串
        """
        # 移除时间戳参数，确保缓存键一致性
        cache_params = {k: v for k, v in kwargs.items() if k != "_ts"}
        return f"{url}:{str(sorted(cache_params.items()))}"

    async def _get(self, url: str, **kwargs) -> Optional[Dict[str, Any]]:
        """
        异步GET请求（带缓存，复用客户端）

        Args:
            url: API端点路径
            **kwargs: 额外参数

        Returns:
            API响应数据
        """
        # 检查缓存
        cache_key = self._make_cache_key(url, **kwargs)
        cached_data = self._cache.get(cache_key)
        if cached_data is not None:
            logger.debug(f"缓存命中: {url}")
            return cached_data

        req_url, params, headers = self._prepare_get_params(url, **kwargs)

        # 使用复用的客户端（Docker 环境优化）
        client = await self._get_or_create_client()
            
        logger.info(f"Requests: {req_url}")
        try:
            response = await client.get(req_url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()

            # 检查速率限制
            self._check_rate_limit(data)

            # 存入缓存
            if data:
                self._cache.set(cache_key, data)

            return data
        except httpx.HTTPStatusError as e:
            logger.error(f"豆瓣API HTTP错误: {e.response.status_code} - {req_url}")
            raise DoubanApiException(f"HTTP错误: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"豆瓣API请求错误: {str(e)}", exc_info=True)
            raise DoubanApiException(f"请求错误: {str(e)}")

    async def _post(self, url: str, **kwargs) -> Optional[Dict[str, Any]]:
        """
        异步POST请求（带缓存，复用客户端）

        Args:
            url: API端点路径
            **kwargs: 额外参数

        Returns:
            API响应数据
        """
        # 检查缓存
        cache_key = self._make_cache_key(url, **kwargs)
        cached_data = self._cache.get(cache_key)
        if cached_data is not None:
            logger.debug(f"缓存命中: {url}")
            return cached_data

        req_url, data, headers = self._prepare_post_params(url, **kwargs)

        # 使用复用的客户端（Docker 环境优化）
        client = await self._get_or_create_client()
        logger.info(f"POST Requests: {req_url}")
        try:
            response = await client.post(req_url, data=data, headers=headers)
            response.raise_for_status()
            result = response.json()

            # 检查速率限制
            self._check_rate_limit(result)

            # 存入缓存
            if result:
                self._cache.set(cache_key, result)

            return result
        except httpx.HTTPStatusError as e:
            logger.error(f"豆瓣API HTTP错误: {e.response.status_code} - {req_url}")
            raise DoubanApiException(f"HTTP错误: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"豆瓣API请求错误: {str(e)}", exc_info=True)
            raise DoubanApiException(f"请求错误: {str(e)}")

    # ==================== 搜索接口 ====================

    async def search(
        self,
        keyword: str,
        start: int = 0,
        count: int = 20
    ) -> Optional[Dict[str, Any]]:
        """
        关键词搜索

        Args:
            keyword: 搜索关键词
            start: 起始位置
            count: 返回数量

        Returns:
            搜索结果
        """
        return await self._get(self._urls["search"], q=keyword, start=start, count=count)

    async def movie_search(
        self,
        keyword: str,
        start: int = 0,
        count: int = 20
    ) -> Optional[Dict[str, Any]]:
        """
        电影搜索

        Args:
            keyword: 搜索关键词
            start: 起始位置
            count: 返回数量

        Returns:
            搜索结果
        """
        return await self._get(self._urls["movie_search"], q=keyword, start=start, count=count)

    # ==================== 详情接口 ====================

    async def movie_detail(self, subject_id: str) -> Optional[Dict[str, Any]]:
        """
        获取电影详情

        Args:
            subject_id: 豆瓣电影ID

        Returns:
            电影详情数据
        """
        return await self._get(self._urls["movie_detail"] + subject_id)

    async def tv_detail(self, subject_id: str) -> Optional[Dict[str, Any]]:
        """
        获取电视剧详情

        Args:
            subject_id: 豆瓣电视剧ID

        Returns:
            电视剧详情数据
        """
        return await self._get(self._urls["tv_detail"] + subject_id)

    async def movie_celebrities(self, subject_id: str) -> Optional[Dict[str, Any]]:
        """
        获取电影演职员信息

        Args:
            subject_id: 豆瓣电影ID

        Returns:
            演职员数据
        """
        return await self._get(self._urls["movie_celebrities"] % subject_id)

    async def tv_celebrities(self, subject_id: str) -> Optional[Dict[str, Any]]:
        """
        获取电视剧演职员信息

        Args:
            subject_id: 豆瓣电视剧ID

        Returns:
            演职员数据
        """
        return await self._get(self._urls["tv_celebrities"] % subject_id)

    # ==================== 图片接口 ====================

    async def movie_photos(
        self,
        subject_id: str,
        photo_type: str = "R",
        start: int = 0,
        count: int = 30
    ) -> Optional[Dict[str, Any]]:
        """
        获取电影剧照

        Args:
            subject_id: 豆瓣电影ID
            photo_type: 图片类型，R=剧照/海报/壁纸，W=壁纸，S=剧照
            start: 起始位置
            count: 返回数量

        Returns:
            剧照数据
        """
        return await self._get(
            self._urls["movie_photos"] % subject_id,
            type=photo_type,
            start=start,
            count=count
        )

    async def tv_photos(
        self,
        subject_id: str,
        photo_type: str = "R",
        start: int = 0,
        count: int = 30
    ) -> Optional[Dict[str, Any]]:
        """
        获取电视剧剧照

        Args:
            subject_id: 豆瓣电视剧ID
            photo_type: 图片类型，R=剧照/海报/壁纸，W=壁纸，S=剧照
            start: 起始位置
            count: 返回数量

        Returns:
            剧照数据
        """
        return await self._get(
            self._urls["tv_photos"] % subject_id,
            type=photo_type,
            start=start,
            count=count
        )

    # ==================== IMDB查询 ====================

    async def get_by_imdb_id(self, imdb_id: str) -> Optional[Dict[str, Any]]:
        """
        通过IMDB ID查询豆瓣信息

        Args:
            imdb_id: IMDB ID（如tt1234567）

        Returns:
            豆瓣媒体信息
        """
        return await self._post(self._urls["imdbid"] % imdb_id)

    # ==================== 推荐/榜单接口 ====================

    async def movie_hot(self, start: int = 0, count: int = 20) -> Optional[Dict[str, Any]]:
        """
        获取热门电影

        Args:
            start: 起始位置
            count: 返回数量

        Returns:
            热门电影列表
        """
        return await self._get(self._urls["movie_hot_gaia"], start=start, count=count)

    async def tv_hot(self, start: int = 0, count: int = 20) -> Optional[Dict[str, Any]]:
        """
        获取热门剧集

        Args:
            start: 起始位置
            count: 返回数量

        Returns:
            热门剧集列表
        """
        return await self._get(self._urls["tv_hot"], start=start, count=count)

    async def movie_top250(self, start: int = 0, count: int = 20) -> Optional[Dict[str, Any]]:
        """
        获取电影TOP250

        Args:
            start: 起始位置
            count: 返回数量

        Returns:
            TOP250电影列表
        """
        return await self._get(self._urls["movie_top250"], start=start, count=count)

    async def movie_recommendations(
        self,
        subject_id: str,
        start: int = 0,
        count: int = 20
    ) -> Optional[Dict[str, Any]]:
        """
        获取电影推荐

        Args:
            subject_id: 豆瓣电影ID
            start: 起始位置
            count: 返回数量

        Returns:
            推荐电影列表
        """
        return await self._get(
            self._urls["movie_recommendations"] % subject_id,
            start=start,
            count=count
        )

    async def tv_recommendations(
        self,
        subject_id: str,
        start: int = 0,
        count: int = 20
    ) -> Optional[Dict[str, Any]]:
        """
        获取电视剧推荐

        Args:
            subject_id: 豆瓣电视剧ID
            start: 起始位置
            count: 返回数量

        Returns:
            推荐电视剧列表
        """
        return await self._get(
            self._urls["tv_recommendations"] % subject_id,
            start=start,
            count=count
        )

    # ==================== 更多榜单接口 ====================

    async def tv_animation(self, start: int = 0, count: int = 20) -> Optional[Dict[str, Any]]:
        """获取动画榜单"""
        return await self._get(self._urls["tv_animation"], start=start, count=count)

    async def tv_domestic(self, start: int = 0, count: int = 20) -> Optional[Dict[str, Any]]:
        """获取国产剧榜单"""
        return await self._get(self._urls["tv_domestic"], start=start, count=count)

    async def tv_american(self, start: int = 0, count: int = 20) -> Optional[Dict[str, Any]]:
        """获取美剧榜单"""
        return await self._get(self._urls["tv_american"], start=start, count=count)

    async def tv_japanese(self, start: int = 0, count: int = 20) -> Optional[Dict[str, Any]]:
        """获取日剧榜单"""
        return await self._get(self._urls["tv_japanese"], start=start, count=count)

    async def tv_korean(self, start: int = 0, count: int = 20) -> Optional[Dict[str, Any]]:
        """获取韩剧榜单"""
        return await self._get(self._urls["tv_korean"], start=start, count=count)

    async def tv_chinese_best_weekly(self, start: int = 0, count: int = 20) -> Optional[Dict[str, Any]]:
        """获取华语口碑周榜"""
        return await self._get(self._urls["tv_chinese_best_weekly"], start=start, count=count)

    async def tv_global_best_weekly(self, start: int = 0, count: int = 20) -> Optional[Dict[str, Any]]:
        """获取全球口碑周榜"""
        return await self._get(self._urls["tv_global_best_weekly"], start=start, count=count)

    # ==================== 电影分类榜单 ====================

    async def movie_scifi(self, start: int = 0, count: int = 20) -> Optional[Dict[str, Any]]:
        """获取高分经典科幻片榜"""
        return await self._get(self._urls["movie_scifi"], start=start, count=count)

    async def movie_comedy(self, start: int = 0, count: int = 20) -> Optional[Dict[str, Any]]:
        """获取高分经典喜剧片榜"""
        return await self._get(self._urls["movie_comedy"], start=start, count=count)

    async def movie_action(self, start: int = 0, count: int = 20) -> Optional[Dict[str, Any]]:
        """获取高分经典动作片榜"""
        return await self._get(self._urls["movie_action"], start=start, count=count)

    async def movie_love(self, start: int = 0, count: int = 20) -> Optional[Dict[str, Any]]:
        """获取高分经典爱情片榜"""
        return await self._get(self._urls["movie_love"], start=start, count=count)

    # ==================== 人物接口 ====================

    async def person_detail(self, person_id: int) -> Optional[Dict[str, Any]]:
        """
        获取人物详情 (Elessar/Personage接口)
        
        Args:
            person_id: 人物ID

        Returns:
            人物详情数据
        """
        return await self._get(self._urls["person_detail"] + str(person_id))

    async def celebrity_detail(self, person_id: str) -> Optional[Dict[str, Any]]:
        """
        获取影人详情 (Celebrity接口)

        Args:
            person_id: 影人ID

        Returns:
            影人详情数据
        """
        return await self._get(self._urls["celebrity_detail"] % str(person_id))

    # ==================== 缓存管理 ====================

    def clear_cache(self) -> None:
        """清空所有缓存"""
        self._cache.clear()
        logger.info("豆瓣API缓存已清空")
