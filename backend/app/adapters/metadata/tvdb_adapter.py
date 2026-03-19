# -*- coding: utf-8 -*-
"""
TVDB元数据适配器

使用TVDB API v4获取电视剧元数据
官方文档: https://thetvdb.github.io/v4-api/
"""
import asyncio
import logging
from typing import Optional, Dict, Any, List, Callable, TypeVar

import httpx

logger = logging.getLogger(__name__)

T = TypeVar('T')


class TVDBApiException(Exception):
    """TVDB API异常基类"""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class TVDBRateLimitException(TVDBApiException):
    """TVDB速率限制异常"""

    def __init__(self, message: str = "TVDB API速率限制", retry_after: Optional[int] = None):
        super().__init__(message, status_code=429)
        self.retry_after = retry_after


class TVDBAdapter:
    """
    TVDB (The TV Database) 元数据适配器

    使用TVDB API v4获取电视剧元数据
    官方文档: https://thetvdb.github.io/v4-api/
    需要API Key认证
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化TVDB适配器

        Args:
            config: 配置信息，包含：
                - api_key: TVDB API Key（必需）
                - pin: TVDB PIN（可选，部分项目需要）
                - api_base_url: API基础URL（可选，默认https://api4.thetvdb.com/v4）
                - proxy_config: 代理配置（可选）
                - timeout: 超时时间（可选，默认30秒）
                - language: 语言（可选，默认zho）
        """
        self.config = config or {}

        # API Key（必需）
        self.api_key = self.config.get("api_key", "")
        if not self.api_key:
            logger.warning("TVDBAdapter initialized without api_key, requests will likely fail")

        # PIN（可选）
        self.pin = self.config.get("pin", "")

        # API URL配置
        self.api_base_url = self.config.get("api_base_url", "https://api4.thetvdb.com/v4")

        # 超时配置
        self.timeout = self.config.get("timeout", 30)

        # 代理配置
        self.proxy_config = self.config.get("proxy_config", {})

        # 语言配置（TVDB使用ISO 639-2语言代码，如 zho=中文, eng=英语）
        self.language = self.config.get("language", "zho")

        # User-Agent
        self.user_agent = self.config.get(
            "user_agent",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )

        # TVDB图片基础URL
        self.image_base_url = "https://artworks.thetvdb.com"

        # 重试配置
        self.max_retries = self.config.get("max_retries", 3)
        self.retry_delay = self.config.get("retry_delay", 2)

        # 认证Token（登录后获取）
        self._token: Optional[str] = None
        self._token_expires: Optional[float] = None

    async def _login(self) -> str:
        """
        登录TVDB获取认证Token

        Returns:
            认证Token
        """
        url = f"{self.api_base_url}/login"
        payload = {"apikey": self.api_key}
        if self.pin:
            payload["pin"] = self.pin

        client_config = self._get_client_config()
        async with httpx.AsyncClient(**client_config) as client:
            response = await client.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            data = response.json()

            token = data.get("data", {}).get("token")
            if not token:
                raise TVDBApiException("TVDB登录失败：未获取到token")

            self._token = token
            # Token有效期约30天，这里设置29天后过期
            import time
            self._token_expires = time.time() + 29 * 24 * 3600

            logger.info("TVDB登录成功")
            return token

    async def _ensure_token(self) -> str:
        """确保有有效的认证Token"""
        import time
        if not self._token or (self._token_expires and time.time() > self._token_expires):
            await self._login()
        return self._token

    def _get_headers(self) -> Dict[str, str]:
        """构建请求头"""
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    def _get_client_config(self) -> Dict[str, Any]:
        """构建HTTP客户端配置"""
        config = {
            "timeout": httpx.Timeout(self.timeout),
            "follow_redirects": True,
        }

        if self.proxy_config and self.proxy_config.get("enabled"):
            proxy_url = self.proxy_config.get("url")
            if proxy_url:
                config["proxies"] = proxy_url

        return config

    async def _retry_request(
        self,
        request_func: Callable[..., T],
        *args,
        **kwargs
    ) -> T:
        """带重试机制的请求包装器"""
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                return await request_func(*args, **kwargs)

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    retry_after = e.response.headers.get("Retry-After")
                    if retry_after:
                        try:
                            wait_time = int(retry_after)
                        except ValueError:
                            wait_time = self.retry_delay * (2 ** attempt)
                    else:
                        wait_time = self.retry_delay * (2 ** attempt)

                    logger.warning(
                        f"TVDB API速率限制 (429), 第{attempt + 1}次重试, "
                        f"等待{wait_time}秒..."
                    )

                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        raise TVDBRateLimitException(
                            f"TVDB API速率限制，已重试{self.max_retries}次",
                            retry_after=int(retry_after) if retry_after else None
                        )
                elif e.response.status_code == 401:
                    # Token过期，重新登录
                    logger.warning("TVDB Token过期，重新登录...")
                    self._token = None
                    await self._ensure_token()
                    if attempt < self.max_retries - 1:
                        continue
                    else:
                        raise TVDBApiException(
                            f"TVDB认证失败",
                            status_code=401
                        )
                else:
                    raise TVDBApiException(
                        f"TVDB API错误: {e.response.status_code}",
                        status_code=e.response.status_code
                    )

            except httpx.HTTPError as e:
                last_exception = e
                wait_time = self.retry_delay * (2 ** attempt)
                logger.warning(
                    f"TVDB请求失败: {str(e)}, 第{attempt + 1}次重试, "
                    f"等待{wait_time}秒..."
                )

                if attempt < self.max_retries - 1:
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise

            except Exception as e:
                logger.error(f"TVDB请求异常: {str(e)}")
                raise

        if last_exception:
            raise last_exception

    async def _make_request(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """发起HTTP GET请求（带重试机制）"""
        await self._ensure_token()

        async def do_request():
            client_config = self._get_client_config()
            async with httpx.AsyncClient(**client_config) as client:
                response = await client.get(
                    url,
                    params=params,
                    headers=self._get_headers(),
                )
                response.raise_for_status()
                return response.json()

        return await self._retry_request(do_request)

    # ========== 电视剧搜索方法 ==========

    async def search_by_imdb_id(self, imdb_id: str) -> Optional[Dict[str, Any]]:
        """
        通过IMDB ID查找电视剧

        Args:
            imdb_id: IMDB ID，如 "tt1234567"

        Returns:
            电视剧基本信息，如果未找到返回None
        """
        logger.info(f"TVDB: 通过IMDB ID查找电视剧: {imdb_id}")

        if not imdb_id.startswith("tt"):
            imdb_id = f"tt{imdb_id}"

        url = f"{self.api_base_url}/search/remoteid/{imdb_id}"

        try:
            result = await self._make_request(url)
            data = result.get("data", [])

            if not data:
                logger.warning(f"TVDB: 未找到IMDB ID对应的内容: {imdb_id}")
                return None

            # 从结果中提取电视剧信息
            # 注意：API可能返回多个结果，我们需要找到类型为series的
            for item in data:
                if item.get("series"):
                    series = item["series"]
                    tvdb_id = series.get("id")
                    if tvdb_id:
                        # 获取详细信息
                        return await self.get_series_extended(tvdb_id)

            # 如果没有找到series，尝试返回第一个结果
            if data:
                first_item = data[0]
                if first_item.get("series"):
                    tvdb_id = first_item["series"].get("id")
                    if tvdb_id:
                        return await self.get_series_extended(tvdb_id)

            logger.warning(f"TVDB: IMDB ID结果中未找到电视剧: {imdb_id}")
            return None

        except TVDBApiException:
            raise
        except Exception as e:
            logger.error(f"TVDB: 通过IMDB ID查找电视剧失败: {str(e)}")
            return None

    async def search_by_title(
        self,
        title: str,
        year: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        通过标题搜索电视剧

        Args:
            title: 剧名
            year: 年份（可选）

        Returns:
            搜索结果列表
        """
        logger.info(f"TVDB: 通过标题搜索电视剧: {title}, year={year}")

        url = f"{self.api_base_url}/search"
        params = {
            "query": title,
            "type": "series",
        }
        if year:
            params["year"] = year

        try:
            result = await self._make_request(url, params)
            data = result.get("data", [])

            if not data:
                logger.warning(f"TVDB: 未找到标题对应的电视剧: {title}")
                return []

            # 获取前3个结果的详细信息
            detailed_results = []
            for item in data[:3]:
                tvdb_id = item.get("tvdb_id") or item.get("id")
                if tvdb_id:
                    try:
                        details = await self.get_series_extended(int(tvdb_id))
                        if details:
                            detailed_results.append(details)
                    except Exception as e:
                        logger.warning(f"TVDB: 获取电视剧详情失败: {tvdb_id}, {str(e)}")

            return detailed_results

        except TVDBApiException:
            raise
        except Exception as e:
            logger.error(f"TVDB: 通过标题搜索电视剧失败: {str(e)}")
            return []

    # ========== 电视剧详情方法 ==========

    async def get_series(self, tvdb_id: int) -> Optional[Dict[str, Any]]:
        """
        获取电视剧基本信息

        Args:
            tvdb_id: TVDB电视剧ID

        Returns:
            电视剧基本信息
        """
        logger.info(f"TVDB: 获取电视剧基本信息: {tvdb_id}")

        url = f"{self.api_base_url}/series/{tvdb_id}"

        try:
            result = await self._make_request(url)
            return result.get("data")
        except Exception as e:
            logger.error(f"TVDB: 获取电视剧基本信息失败: {str(e)}")
            return None

    async def get_series_extended(self, tvdb_id: int) -> Optional[Dict[str, Any]]:
        """
        获取电视剧详细信息（含季信息）

        Args:
            tvdb_id: TVDB电视剧ID

        Returns:
            转换后的电视剧元数据
        """
        logger.info(f"TVDB: 获取电视剧详细信息: {tvdb_id}")

        url = f"{self.api_base_url}/series/{tvdb_id}/extended"

        try:
            result = await self._make_request(url)
            data = result.get("data")
            if data:
                return self._convert_to_unified_format(data)
            return None
        except Exception as e:
            logger.error(f"TVDB: 获取电视剧详细信息失败: {str(e)}")
            return None

    async def get_season_extended(self, season_id: int) -> Optional[Dict[str, Any]]:
        """
        获取季详细信息（含单集信息）

        Args:
            season_id: TVDB季ID

        Returns:
            季详情，包含episodes列表
        """
        logger.info(f"TVDB: 获取季详细信息: {season_id}")

        url = f"{self.api_base_url}/seasons/{season_id}/extended"

        try:
            result = await self._make_request(url)
            return result.get("data")
        except Exception as e:
            logger.error(f"TVDB: 获取季详细信息失败: {str(e)}")
            return None

    async def get_series_episodes(
        self,
        tvdb_id: int,
        season_number: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        获取电视剧的所有集信息

        Args:
            tvdb_id: TVDB电视剧ID
            season_number: 季号（可选，不指定则返回所有季的集）

        Returns:
            包含seasons和episodes的字典
        """
        logger.info(f"TVDB: 获取电视剧集列表: tvdb_id={tvdb_id}, season={season_number}")

        # 使用 /series/{id}/episodes/default 端点获取默认排序的集
        url = f"{self.api_base_url}/series/{tvdb_id}/episodes/default"
        params = {"page": 0}
        if season_number is not None:
            params["season"] = season_number

        try:
            result = await self._make_request(url, params)
            return result.get("data")
        except Exception as e:
            logger.error(f"TVDB: 获取电视剧集列表失败: {str(e)}")
            return None

    async def get_tv_season_detail(
        self,
        tvdb_id: int,
        season_number: int,
    ) -> Optional[Dict[str, Any]]:
        """
        获取电视剧季的详情（包含各集信息）

        兼容TMDB适配器的接口签名

        Args:
            tvdb_id: TVDB电视剧ID
            season_number: 季数

        Returns:
            季详情，包含episodes数组
        """
        logger.info(f"TVDB: 获取电视剧季详情: tvdb_id={tvdb_id}, season={season_number}")

        try:
            # 首先获取电视剧详情，找到对应季的season_id
            series_data = await self.get_series_extended(tvdb_id)
            if not series_data:
                return None

            # 从原始数据中查找季ID
            # 注意：get_series_extended返回的是转换后的数据，我们需要原始数据
            url = f"{self.api_base_url}/series/{tvdb_id}/extended"
            result = await self._make_request(url)
            raw_data = result.get("data", {})

            seasons = raw_data.get("seasons", [])
            target_season = None
            for season in seasons:
                # TVDB的season可能有不同的type，我们通常需要"Aired Order"
                season_type = season.get("type", {})
                type_name = season_type.get("name", "") if isinstance(season_type, dict) else ""

                if season.get("number") == season_number:
                    # 优先选择 Aired Order 类型
                    if type_name == "Aired Order" or not target_season:
                        target_season = season

            if not target_season:
                logger.warning(f"TVDB: 未找到第{season_number}季")
                return None

            season_id = target_season.get("id")
            if not season_id:
                return None

            # 获取季详情（含单集）
            season_detail = await self.get_season_extended(season_id)
            if not season_detail:
                return None

            # 转换为兼容TMDB的格式
            return self._convert_season_to_tmdb_format(season_detail, season_number)

        except Exception as e:
            logger.error(f"TVDB: 获取电视剧季详情失败: {str(e)}")
            return None

    # ========== 数据格式转换 ==========

    def _convert_to_unified_format(self, tvdb_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        将TVDB数据转换为统一格式

        Args:
            tvdb_data: TVDB API返回的电视剧数据

        Returns:
            符合UnifiedTV格式的字段字典
        """
        # 提取年份
        year = None
        first_aired = tvdb_data.get("firstAired")
        if first_aired:
            try:
                year = int(first_aired[:4])
            except (ValueError, TypeError, IndexError):
                pass

        # 提取外部ID
        remote_ids = tvdb_data.get("remoteIds", [])
        imdb_id = None
        tmdb_id = None
        for remote in remote_ids:
            source_name = remote.get("sourceName", "")
            remote_id = remote.get("id")
            if source_name == "IMDB" and remote_id:
                imdb_id = remote_id
            elif source_name == "TheMovieDB.com" and remote_id:
                try:
                    tmdb_id = int(remote_id)
                except ValueError:
                    pass

        # 提取类型
        genres = []
        for genre in tvdb_data.get("genres", []):
            if isinstance(genre, dict):
                genres.append(genre.get("name", ""))
            elif isinstance(genre, str):
                genres.append(genre)

        # 提取演员
        actors = []
        characters = tvdb_data.get("characters", [])
        for idx, char in enumerate(characters[:10], start=1):
            if char.get("type") == 3:  # type 3 是演员
                actors.append({
                    "tvdb_id": char.get("id"),
                    "name": char.get("personName"),
                    "character": char.get("name"),
                    "thumb_url": char.get("image"),
                    "order": idx,
                })

        # 提取语言
        original_language = tvdb_data.get("originalLanguage")
        languages = [original_language] if original_language else []

        # 提取国家
        original_country = tvdb_data.get("originalCountry")
        countries = [original_country] if original_country else []

        # 提取海报
        poster_url = None
        backdrop_url = None
        if tvdb_data.get("image"):
            poster_url = tvdb_data["image"]
        artworks = tvdb_data.get("artworks", [])
        for artwork in artworks:
            artwork_type = artwork.get("type")
            # type 1 = banner, 2 = poster, 3 = background/fanart
            if artwork_type == 2 and not poster_url:
                poster_url = artwork.get("image")
            elif artwork_type == 3 and not backdrop_url:
                backdrop_url = artwork.get("image")

        # 计算季数和集数
        seasons = tvdb_data.get("seasons", [])
        # 过滤掉特别季（season 0）和非aired order的季
        aired_seasons = [
            s for s in seasons
            if s.get("number", 0) > 0 and
               (s.get("type", {}).get("name") == "Aired Order" if isinstance(s.get("type"), dict) else True)
        ]
        number_of_seasons = len(set(s.get("number") for s in aired_seasons))

        # 集数需要从episodes获取
        number_of_episodes = tvdb_data.get("episodes") if isinstance(tvdb_data.get("episodes"), int) else None

        return {
            # 标识
            "tvdb_id": tvdb_data.get("id"),
            "imdb_id": imdb_id,
            "tmdb_id": tmdb_id,

            # 标题
            "title": tvdb_data.get("name"),
            "original_title": tvdb_data.get("name"),
            "aka": tvdb_data.get("aliases", []),

            # 基础信息
            "year": year,
            "first_air_date": first_aired,
            "status": tvdb_data.get("status", {}).get("name") if isinstance(tvdb_data.get("status"), dict) else None,
            "number_of_seasons": number_of_seasons,
            "number_of_episodes": number_of_episodes,

            # 分类/标签
            "genres": genres,
            "languages": languages,
            "countries": countries,

            # 人员
            "actors": actors,

            # 内容描述
            "overview": tvdb_data.get("overview"),

            # 图片
            "poster_url": poster_url,
            "backdrop_url": backdrop_url,

            # 元数据来源
            "metadata_source": "tvdb",
            "media_type": "tv",
            "detail_loaded": True,
        }

    def _convert_season_to_tmdb_format(
        self,
        season_data: Dict[str, Any],
        season_number: int,
    ) -> Dict[str, Any]:
        """
        将TVDB季数据转换为兼容TMDB的格式

        Args:
            season_data: TVDB季详情
            season_number: 季号

        Returns:
            兼容TMDB格式的季详情
        """
        episodes = []
        for ep in season_data.get("episodes", []):
            episode = {
                "id": ep.get("id"),
                "name": ep.get("name"),
                "overview": ep.get("overview"),
                "air_date": ep.get("aired"),
                "episode_number": ep.get("number"),
                "season_number": season_number,
                "still_path": ep.get("image"),  # TVDB直接返回完整URL
                "vote_average": ep.get("runtime"),  # TVDB没有评分，用runtime占位
                "crew": [],
                "guest_stars": [],
            }

            # 提取导演
            for person in ep.get("characters", []):
                if person.get("type") == 1:  # 导演
                    episode["crew"].append({
                        "id": person.get("id"),
                        "name": person.get("personName"),
                        "job": "Director",
                    })

            episodes.append(episode)

        # 提取季海报
        poster_path = season_data.get("image")

        return {
            "id": season_data.get("id"),
            "name": season_data.get("name") or f"第 {season_number} 季",
            "overview": season_data.get("overview"),
            "air_date": season_data.get("firstAired"),
            "season_number": season_number,
            "poster_path": poster_path,
            "episodes": episodes,
        }

    def _build_image_url(self, path: Optional[str]) -> Optional[str]:
        """
        构建TVDB图片URL

        Args:
            path: 图片路径

        Returns:
            完整图片URL
        """
        if not path:
            return None

        # TVDB的图片URL可能已经是完整的
        if path.startswith("http"):
            return path

        return f"{self.image_base_url}{path}"
