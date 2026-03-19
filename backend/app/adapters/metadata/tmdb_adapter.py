# -*- coding: utf-8 -*-
"""
TMDB元数据适配器
"""
import asyncio
import logging
from typing import Optional, Dict, Any, List, Callable, TypeVar
import httpx
from app.utils.metadata_normalization import MetadataNormalizer

logger = logging.getLogger(__name__)

T = TypeVar('T')


class TMDBApiException(Exception):
    """TMDB API异常基类"""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class TMDBRateLimitException(TMDBApiException):
    """TMDB速率限制异常（HTTP 429）"""

    def __init__(self, message: str = "TMDB API速率限制", retry_after: Optional[int] = None):
        super().__init__(message, status_code=429)
        self.retry_after = retry_after  # TMDB返回的Retry-After头


class TMDBAdapter:
    """
    TMDB (The Movie Database) 元数据适配器

    使用TMDB API v3获取电影元数据
    官方文档: https://developers.themoviedb.org/3
    需要API Key认证
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化TMDB适配器

        Args:
            config: 配置信息，包含：
                - api_key: TMDB API Key（必需）
                - api_base_url: API基础URL（可选，默认https://api.themoviedb.org/3）
                - proxy_config: 代理配置（可选）
                - timeout: 超时时间（可选，默认30秒）
                - language: 语言（可选，默认zh-CN）
        """
        self.config = config or {}

        # API Key（必需）
        self.api_key = self.config.get("api_key", "")
        if not self.api_key:
            logger.warning("TMDBAdapter initialized without api_key, requests will likely fail")

        # API URL配置
        self.api_base_url = self.config.get("api_base_url", "https://api.themoviedb.org/3")

        # 超时配置
        self.timeout = self.config.get("timeout", 30)

        # 代理配置
        self.proxy_config = self.config.get("proxy_config", {})

        # 语言配置
        self.language = self.config.get("language", "zh-CN")

        # User-Agent
        self.user_agent = self.config.get(
            "user_agent",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        # TMDB图片基础URL
        self.image_base_url = "https://image.tmdb.org/t/p/"

        # 重试配置
        self.max_retries = self.config.get("max_retries", 3)
        self.retry_delay = self.config.get("retry_delay", 2)  # 基础重试延迟（秒）

    def _get_headers(self) -> Dict[str, str]:
        """
        构建请求头

        Returns:
            Dict: HTTP请求头
        """
        return {
            "User-Agent": self.user_agent,
            "Accept": "application/json",
            "Connection": "keep-alive",
        }

    def _get_client_config(self) -> Dict[str, Any]:
        """
        构建HTTP客户端配置

        Returns:
            Dict: httpx客户端配置
        """
        config = {
            "timeout": httpx.Timeout(self.timeout),
            "follow_redirects": True,
        }

        # 添加代理配置
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
        """
        带重试机制的请求包装器

        处理429速率限制，使用指数退避策略重试。

        Args:
            request_func: 异步请求函数
            *args: 传递给请求函数的位置参数
            **kwargs: 传递给请求函数的关键字参数

        Returns:
            请求函数的返回值

        Raises:
            TMDBRateLimitException: 重试次数用尽后仍触发限流
            TMDBApiException: 其他API错误
            httpx.HTTPError: HTTP请求错误
        """
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                return await request_func(*args, **kwargs)

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    # 获取Retry-After头（如果有）
                    retry_after = e.response.headers.get("Retry-After")
                    if retry_after:
                        try:
                            wait_time = int(retry_after)
                        except ValueError:
                            wait_time = self.retry_delay * (2 ** attempt)
                    else:
                        # 指数退避: 2秒, 4秒, 8秒...
                        wait_time = self.retry_delay * (2 ** attempt)

                    logger.warning(
                        f"TMDB API速率限制 (429), 第{attempt + 1}次重试, "
                        f"等待{wait_time}秒..."
                    )

                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        raise TMDBRateLimitException(
                            f"TMDB API速率限制，已重试{self.max_retries}次",
                            retry_after=int(retry_after) if retry_after else None
                        )
                else:
                    # 其他HTTP错误，不重试
                    raise TMDBApiException(
                        f"TMDB API错误: {e.response.status_code}",
                        status_code=e.response.status_code
                    )

            except httpx.HTTPError as e:
                # 网络错误，重试
                last_exception = e
                wait_time = self.retry_delay * (2 ** attempt)
                logger.warning(
                    f"TMDB请求失败: {str(e)}, 第{attempt + 1}次重试, "
                    f"等待{wait_time}秒..."
                )

                if attempt < self.max_retries - 1:
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise

            except Exception as e:
                # 其他异常，不重试
                logger.error(f"TMDB请求异常: {str(e)}")
                raise

        # 不应该到达这里，但以防万一
        if last_exception:
            raise last_exception

    async def _make_request(
        self,
        url: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        发起HTTP GET请求（带重试机制）

        Args:
            url: 请求URL
            params: 请求参数

        Returns:
            Dict: JSON响应
        """
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

    async def find_by_imdb_id(self, imdb_id: str) -> Optional[Dict[str, Any]]:
        """
        通过IMDB ID查找电影

        Args:
            imdb_id: IMDB ID，如 "tt1234567"

        Returns:
            Dict: 转换后的电影元数据，如果未找到返回None

        Raises:
            TMDBRateLimitException: 触发速率限制
            TMDBApiException: API错误
            httpx.HTTPError: HTTP请求错误
        """
        logger.info(f"Finding movie by IMDB ID: {imdb_id}")

        # 确保IMDB ID格式正确
        if not imdb_id.startswith("tt"):
            imdb_id = f"tt{imdb_id}"

        # 使用find API查找外部ID
        url = f"{self.api_base_url}/find/{imdb_id}"
        params = {
            "api_key": self.api_key,
            "language": self.language,
            "external_source": "imdb_id",
        }

        try:
            result = await self._make_request(url, params)

            # 提取电影结果
            movie_results = result.get("movie_results", [])
            if not movie_results:
                logger.warning(f"No movie found for IMDB ID: {imdb_id}")
                return None

            # 获取第一个结果的详细信息
            tmdb_id = movie_results[0]["id"]
            return await self.get_movie_details(tmdb_id)

        except (TMDBRateLimitException, TMDBApiException):
            raise
        except Exception as e:
            logger.error(f"通过IMDB ID查找电影失败: {str(e)}")
            raise

    async def search_by_title(
        self,
        title: str,
        year: Optional[int] = None,
        include_adult: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        通过标题搜索电影

        Args:
            title: 电影标题
            year: 年份（可选，提高搜索准确度）
            include_adult: 是否包含成人内容（默认False）

        Returns:
            List[Dict]: 搜索结果列表（已转换为统一格式）

        Raises:
            TMDBRateLimitException: 触发速率限制
            TMDBApiException: API错误
            httpx.HTTPError: HTTP请求错误
        """
        logger.info(f"Searching movies by title: {title}, year: {year}")

        url = f"{self.api_base_url}/search/movie"
        params = {
            "api_key": self.api_key,
            "language": self.language,
            "query": title,
            "include_adult": include_adult,
        }

        if year:
            params["year"] = year

        try:
            result = await self._make_request(url, params)

            results = result.get("results", [])
            if not results:
                logger.warning(f"No movies found for title: {title}")
                return []

            # 获取前3个结果的详细信息
            detailed_results = []
            for movie in results[:3]:
                try:
                    details = await self.get_movie_details(movie["id"])
                    if details:
                        detailed_results.append(details)
                except TMDBRateLimitException:
                    # 限流时停止获取更多详情
                    logger.warning("触发限流，停止获取更多电影详情")
                    break
                except Exception as e:
                    logger.warning(f"Failed to get details for movie {movie['id']}: {str(e)}")
                    continue

            return detailed_results

        except (TMDBRateLimitException, TMDBApiException):
            raise
        except Exception as e:
            logger.error(f"通过标题搜索电影失败: {str(e)}")
            raise

    async def get_person_details(self, tmdb_id: int) -> Dict[str, Any]:
        """
        获取人员详细信息，并转换为统一格式（known_for_department 标准化为中文）
        """
        url = f"{self.api_base_url}/person/{tmdb_id}"
        params = {
            "api_key": self.api_key,
            "language": self.language,
        }

        try:
            data = await self._make_request(url, params)
            if not data:
                return None

            # 标准化 known_for_department（TMDB 返回英文，转换为中文）
            raw_dept = data.get("known_for_department")
            normalized_dept = MetadataNormalizer.normalize_department(raw_dept)

            # 解析生日
            birthday = None
            birthday_str = data.get("birthday")
            if birthday_str:
                birthday = birthday_str  # 已是 ISO 格式 "YYYY-MM-DD"

            # 解析忌日
            deathday = None
            deathday_str = data.get("deathday")
            if deathday_str:
                deathday = deathday_str

            # 性别: TMDB: 1=女, 2=男, 0=未指定
            gender = data.get("gender", 0)

            return {
                "tmdb_id": data.get("id"),
                "name": data.get("name"),
                "biography": data.get("biography"),
                "birthday": birthday,
                "deathday": deathday,
                "place_of_birth": MetadataNormalizer.normalize_place_of_birth(data.get("place_of_birth")),
                "gender": gender,
                "homepage": data.get("homepage"),
                "known_for_department": normalized_dept,
                "popularity": data.get("popularity"),
                "profile_url": self._build_image_url(data.get("profile_path"), "w185"),
                "other_names": data.get("also_known_as") or [],
                "metadata_source": "tmdb",
                "detail_loaded": True,
                "family_info": None,
                "raw_data": data,
            }
        except Exception as e:
            logger.error(f"Failed to fetch person details for {tmdb_id}: {e}")
            return None

    # ========== 电影相关方法 ==========

    async def get_movie_details(self, tmdb_id: int) -> Dict[str, Any]:
        """
        获取电影详细信息

        Args:
            tmdb_id: TMDB电影ID

        Returns:
            Dict: 转换后的电影元数据

        Raises:
            TMDBRateLimitException: 触发速率限制
            TMDBApiException: API错误
            httpx.HTTPError: HTTP请求错误
        """
        logger.info(f"Fetching movie details for TMDB ID: {tmdb_id}")

        url = f"{self.api_base_url}/movie/{tmdb_id}"
        params = {
            "api_key": self.api_key,
            "language": self.language,
            "append_to_response": "credits,external_ids,release_dates,alternative_titles",
        }

        try:
            tmdb_data = await self._make_request(url, params)
            # 转换为统一格式
            return self._convert_to_unified_format(tmdb_data)

        except (TMDBRateLimitException, TMDBApiException):
            raise
        except Exception as e:
            logger.error(f"获取电影详情失败: {str(e)}")
            raise

    def _convert_to_unified_format(self, tmdb_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        将TMDB API数据转换为UnifiedMovie格式

        Args:
            tmdb_data: TMDB API返回的电影数据

        Returns:
            Dict: 符合UnifiedMovie模型的字段字典
        """
        # 提取外部ID
        external_ids = tmdb_data.get("external_ids", {})
        imdb_id = external_ids.get("imdb_id")

        # 提取年份
        year = None
        if tmdb_data.get("release_date"):
            try:
                year = int(tmdb_data["release_date"][:4])
            except (ValueError, TypeError, IndexError):
                pass

        # 提取演职人员
        credits = tmdb_data.get("credits", {})

        # 导演列表
        directors = []
        crew = credits.get("crew", [])
        for person in crew:
            if person.get("job") == "Director":
                directors.append({
                    "tmdb_id": person.get("id"),
                    "name": person.get("name"),
                    "thumb_url": self._build_image_url(person.get("profile_path"), "w185"),
                })

        # 编剧列表
        writers = []
        for person in crew:
            if person.get("job") in ("Writer", "Screenplay", "Story"):
                writers.append({
                    "tmdb_id": person.get("id"),
                    "name": person.get("name"),
                    "job": person.get("job"),
                    "thumb_url": self._build_image_url(person.get("profile_path"), "w185"),
                })

        # 演员列表
        actors = []
        cast = credits.get("cast", [])
        for idx, person in enumerate(cast[:10], start=1):  # 只取前10个主演
            actors.append({
                "tmdb_id": person.get("id"),
                "name": person.get("name"),
                "character": person.get("character"),
                "thumb_url": self._build_image_url(person.get("profile_path"), "w185"),
                "order": idx,
            })

        # 提取类型
        genres = [genre["name"] for genre in tmdb_data.get("genres", [])]

        # 提取别名（alternative_titles）
        aka = []
        alternative_titles = tmdb_data.get("alternative_titles", {})
        if alternative_titles:
            titles = alternative_titles.get("titles", [])
            # 提取所有别名，去重
            seen_titles = set()
            for item in titles:
                title = item.get("title")
                if title and title not in seen_titles:
                    seen_titles.add(title)
                    aka.append(title)

        # 提取国家
        countries = []
        production_countries = tmdb_data.get("production_countries", [])
        for country in production_countries:
            # 优先使用 iso_3166_1 代码
            name = country.get("iso_3166_1") or country.get("name")
            countries.append(MetadataNormalizer.normalize_country(name))

        # 提取语言
        languages = []
        spoken_languages = tmdb_data.get("spoken_languages", [])
        for lang in spoken_languages:
            # 优先使用 iso_639_1 代码
            name = lang.get("iso_639_1") or lang.get("name")
            languages.append(MetadataNormalizer.normalize_language(name))

        # 提取制作公司
        production_companies = []
        for company in tmdb_data.get("production_companies", []):
            production_companies.append({
                "id": company.get("id"),
                "name": company.get("name"),
                "logo_url": self._build_image_url(company.get("logo_path"), "w185"),
                "origin_country": company.get("origin_country"),
            })

        # 提取分级信息 (certification)
        certification = None
        release_dates = tmdb_data.get("release_dates", {})
        if release_dates:
            # 优先查找美国 (US) 的分级
            us_releases = None
            for result in release_dates.get("results", []):
                if result.get("iso_3166_1") == "US":
                    us_releases = result.get("release_dates", [])
                    break

            # 从美国发行信息中提取分级
            if us_releases:
                for release in us_releases:
                    cert = release.get("certification")
                    if cert:
                        certification = cert
                        break

        # 提取系列信息
        collection = tmdb_data.get("belongs_to_collection")
        collection_id = None
        collection_name = None
        if collection:
            collection_id = collection.get("id")
            collection_name = collection.get("name")

        # 解析上映日期
        release_date = None
        if tmdb_data.get("release_date"):
            try:
                from datetime import datetime
                release_date = datetime.strptime(tmdb_data["release_date"], "%Y-%m-%d").date()
            except (ValueError, TypeError):
                pass

        return {
            # 标识
            "tmdb_id": tmdb_data.get("id"),
            "imdb_id": imdb_id,

            # 标题
            "title": tmdb_data.get("title"),
            "original_title": tmdb_data.get("original_title"),
            "aka": aka,

            # 基础信息
            "year": year,
            "release_date": release_date,
            "runtime": tmdb_data.get("runtime"),

            # 评分
            "rating_tmdb": tmdb_data.get("vote_average"),
            "votes_tmdb": tmdb_data.get("vote_count"),

            # 分类/标签
            "genres": genres,
            "languages": languages,
            "countries": countries,

            # 人员（保留完整对象）
            "directors": directors,
            "actors": actors,
            "writers": writers,

            # 内容描述
            "overview": tmdb_data.get("overview"),
            "tagline": tmdb_data.get("tagline"),

            # 分级/系列
            "certification": certification,
            "collection_id": collection_id,
            "collection_name": collection_name,

            # 制作信息
            "budget": tmdb_data.get("budget"),
            "revenue": tmdb_data.get("revenue"),
            "production_companies": production_companies,
            "status": tmdb_data.get("status"),

            # 图片
            "poster_url": self._build_image_url(tmdb_data.get("poster_path"), "w500"),
            "backdrop_url": self._build_image_url(tmdb_data.get("backdrop_path"), "w1280"),

            # 元数据来源
            "metadata_source": "tmdb",
            "detail_loaded": True,
        }

    def _build_image_url(self, path: Optional[str], size: str = "original") -> Optional[str]:
        """
        构建TMDB图片URL

        Args:
            path: 图片路径，如 "/abc123.jpg"
            size: 图片尺寸，如 "w500", "original"

        Returns:
            str: 完整图片URL
        """
        if not path:
            return None

        return f"{self.image_base_url}{size}{path}"

    # ========== 电视剧相关方法 ==========

    async def search_tv_by_title(
        self,
        title: str,
        first_air_date_year: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        通过标题搜索电视剧

        Args:
            title: 剧名
            first_air_date_year: 首播年份（可选）

        Returns:
            List[Dict]: 搜索结果列表（已转换为统一格式）

        Raises:
            TMDBRateLimitException: 触发速率限制
            TMDBApiException: API错误
            httpx.HTTPError: HTTP请求错误
        """
        logger.info(f"Searching TV series by title: {title}, year: {first_air_date_year}")

        url = f"{self.api_base_url}/search/tv"
        params = {
            "api_key": self.api_key,
            "language": self.language,
            "query": title,
        }

        if first_air_date_year:
            params["first_air_date_year"] = first_air_date_year

        try:
            result = await self._make_request(url, params)

            results = result.get("results", [])
            if not results:
                logger.warning(f"No TV series found for title: {title}")
                return []

            # 获取前3个结果的详细信息
            detailed_results = []
            for tv in results[:3]:
                try:
                    details = await self.get_tv_details(tv["id"])
                    if details:
                        detailed_results.append(details)
                except TMDBRateLimitException:
                    # 限流时停止获取更多详情
                    logger.warning("触发限流，停止获取更多电视剧详情")
                    break
                except Exception as e:
                    logger.warning(f"Failed to get details for TV {tv['id']}: {str(e)}")
                    continue

            return detailed_results

        except (TMDBRateLimitException, TMDBApiException):
            raise
        except Exception as e:
            logger.error(f"通过标题搜索电视剧失败: {str(e)}")
            raise

    async def get_tv_details(self, tmdb_id: int) -> Dict[str, Any]:
        """
        获取电视剧详细信息

        Args:
            tmdb_id: TMDB电视剧ID

        Returns:
            Dict: 转换后的电视剧元数据

        Raises:
            TMDBRateLimitException: 触发速率限制
            TMDBApiException: API错误
            httpx.HTTPError: HTTP请求错误
        """
        logger.info(f"Fetching TV details for TMDB ID: {tmdb_id}")

        url = f"{self.api_base_url}/tv/{tmdb_id}"
        params = {
            "api_key": self.api_key,
            "language": self.language,
            "append_to_response": "credits,external_ids,alternative_titles",
        }

        try:
            tmdb_data = await self._make_request(url, params)
            # 转换为统一格式
            return self._convert_tv_to_unified_format(tmdb_data)

        except (TMDBRateLimitException, TMDBApiException):
            raise
        except Exception as e:
            logger.error(f"获取电视剧详情失败: {str(e)}")
            raise

    async def find_tv_by_imdb_id(self, imdb_id: str) -> Optional[Dict[str, Any]]:
        """
        通过IMDB ID查找电视剧

        Args:
            imdb_id: IMDB ID

        Returns:
            Dict: 转换后的电视剧元数据

        Raises:
            TMDBRateLimitException: 触发速率限制
            TMDBApiException: API错误
            httpx.HTTPError: HTTP请求错误
        """
        logger.info(f"Finding TV series by IMDB ID: {imdb_id}")

        if not imdb_id.startswith("tt"):
            imdb_id = f"tt{imdb_id}"

        url = f"{self.api_base_url}/find/{imdb_id}"
        params = {
            "api_key": self.api_key,
            "language": self.language,
            "external_source": "imdb_id",
        }

        try:
            result = await self._make_request(url, params)

            # 提取电视剧结果
            tv_results = result.get("tv_results", [])
            if not tv_results:
                logger.warning(f"No TV series found for IMDB ID: {imdb_id}")
                return None

            tmdb_id = tv_results[0]["id"]
            return await self.get_tv_details(tmdb_id)

        except (TMDBRateLimitException, TMDBApiException):
            raise
        except Exception as e:
            logger.error(f"通过IMDB ID查找电视剧失败: {str(e)}")
            raise

    def _convert_tv_to_unified_format(self, tmdb_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        将TMDB TV数据转换为统一格式

        Args:
            tmdb_data: TMDB API返回的电视剧数据

        Returns:
            Dict: 符合UnifiedTV格式的字段字典
        """
        # 提取外部ID
        external_ids = tmdb_data.get("external_ids", {})
        imdb_id = external_ids.get("imdb_id")
        tvdb_id = external_ids.get("tvdb_id")

        # 提取年份
        year = None
        if tmdb_data.get("first_air_date"):
            try:
                year = int(tmdb_data["first_air_date"][:4])
            except (ValueError, TypeError, IndexError):
                pass

        # 提取演职人员
        credits = tmdb_data.get("credits", {})

        # 演员列表
        actors = []
        cast = credits.get("cast", [])
        for idx, person in enumerate(cast[:10], start=1):
            actors.append({
                "tmdb_id": person.get("id"),
                "name": person.get("name"),
                "character": person.get("character"),
                "thumb_url": self._build_image_url(person.get("profile_path"), "w185"),
                "order": idx,
            })

        # 创作者列表
        creators = []
        for person in tmdb_data.get("created_by", []):
            creators.append({
                "tmdb_id": person.get("id"),
                "name": person.get("name"),
                "thumb_url": self._build_image_url(person.get("profile_path"), "w185"),
            })

        # 提取类型
        genres = [genre["name"] for genre in tmdb_data.get("genres", [])]

        # 提取别名（alternative_titles）
        aka = []
        alternative_titles = tmdb_data.get("alternative_titles", {})
        if alternative_titles:
            # 注意：TV的alternative_titles结构是 {"results": [...]}
            titles = alternative_titles.get("results", [])
            # 提取所有别名，去重
            seen_titles = set()
            for item in titles:
                title = item.get("title")
                if title and title not in seen_titles:
                    seen_titles.add(title)
                    aka.append(title)

        # 提取国家
        countries = []
        for country in tmdb_data.get("origin_country", []):
            # TV的origin_country通常就是ISO代码列表，但也可能是名字
            # 如果是纯大写字母且长度为2，假设是ISO代码
            countries.append(MetadataNormalizer.normalize_country(country))

        # 提取语言
        languages = []
        spoken_languages = tmdb_data.get("spoken_languages", [])
        for lang in spoken_languages:
            # 优先使用 iso_639_1 代码
            name = lang.get("iso_639_1") or lang.get("name")
            languages.append(MetadataNormalizer.normalize_language(name))

        return {
            # 标识
            "tmdb_id": tmdb_data.get("id"),
            "imdb_id": imdb_id,
            "tvdb_id": tvdb_id,

            # 标题
            "title": tmdb_data.get("name"),
            "original_title": tmdb_data.get("original_name"),
            "aka": aka,

            # 基础信息
            "year": year,
            "first_air_date": tmdb_data.get("first_air_date"),
            "status": tmdb_data.get("status"),
            "number_of_seasons": tmdb_data.get("number_of_seasons"),
            "number_of_episodes": tmdb_data.get("number_of_episodes"),

            # 评分
            "rating_tmdb": tmdb_data.get("vote_average"),
            "votes_tmdb": tmdb_data.get("vote_count"),

            # 分类/标签
            "genres": genres,
            "languages": languages,
            "countries": countries,

            # 人员
            "creators": creators,
            "actors": actors,

            # 内容描述
            "overview": tmdb_data.get("overview"),

            # 图片
            "poster_url": self._build_image_url(tmdb_data.get("poster_path"), "w500"),
            "backdrop_url": self._build_image_url(tmdb_data.get("backdrop_path"), "w1280"),

            # 元数据来源
            "metadata_source": "tmdb",
            "media_type": "tv",
            "detail_loaded": True,
        }

    async def get_popular_movies(self, page: int = 1, fetch_details: bool = False) -> List[Dict[str, Any]]:
        """
        获取热门电影列表

        Args:
            page: 页码
            fetch_details: 是否获取详细信息（默认False，仅返回基础信息）
        """
        logger.info(f"Fetching popular movies (page={page}, fetch_details={fetch_details})")

        url = f"{self.api_base_url}/movie/popular"
        params = {
            "api_key": self.api_key,
            "language": self.language,
            "page": page,
        }

        try:
            result = await self._make_request(url, params)
            results = result.get("results", [])

            if fetch_details:
                # 获取详细信息（用于需要完整数据的场景）
                detailed_results = []
                for movie in results[:20]:
                    try:
                        details = await self.get_movie_details(movie["id"])
                        if details:
                            detailed_results.append(details)
                    except TMDBRateLimitException:
                        logger.warning("触发限流，停止获取更多电影详情")
                        break
                    except Exception as e:
                        logger.warning(f"Failed to get details for movie {movie['id']}: {str(e)}")
                        continue
                logger.info(f"成功获取 {len(detailed_results)} 部热门电影（含详情）")
                return detailed_results
            else:
                # 快速模式：仅返回基础信息（用于榜单同步阶段一）
                basic_results = [self._convert_list_item_to_basic(m, "movie") for m in results[:20]]
                logger.info(f"成功获取 {len(basic_results)} 部热门电影（基础信息）")
                return basic_results

        except (TMDBRateLimitException, TMDBApiException):
            raise
        except Exception as e:
            logger.error(f"获取热门电影失败: {str(e)}")
            raise

    async def get_top_rated_movies(self, page: int = 1, fetch_details: bool = False) -> List[Dict[str, Any]]:
        """
        获取高分电影列表

        Args:
            page: 页码
            fetch_details: 是否获取详细信息（默认False，仅返回基础信息）
        """
        logger.info(f"Fetching top rated movies (page={page}, fetch_details={fetch_details})")

        url = f"{self.api_base_url}/movie/top_rated"
        params = {
            "api_key": self.api_key,
            "language": self.language,
            "page": page,
        }

        try:
            result = await self._make_request(url, params)
            results = result.get("results", [])

            if fetch_details:
                detailed_results = []
                for movie in results[:20]:
                    try:
                        details = await self.get_movie_details(movie["id"])
                        if details:
                            detailed_results.append(details)
                    except TMDBRateLimitException:
                        logger.warning("触发限流，停止获取更多电影详情")
                        break
                    except Exception as e:
                        logger.warning(f"Failed to get details for movie {movie['id']}: {str(e)}")
                        continue
                logger.info(f"成功获取 {len(detailed_results)} 部高分电影（含详情）")
                return detailed_results
            else:
                basic_results = [self._convert_list_item_to_basic(m, "movie") for m in results[:20]]
                logger.info(f"成功获取 {len(basic_results)} 部高分电影（基础信息）")
                return basic_results

        except (TMDBRateLimitException, TMDBApiException):
            raise
        except Exception as e:
            logger.error(f"获取高分电影失败: {str(e)}")
            raise

    async def get_popular_tv(self, page: int = 1, fetch_details: bool = False) -> List[Dict[str, Any]]:
        """
        获取热门剧集列表

        Args:
            page: 页码
            fetch_details: 是否获取详细信息（默认False，仅返回基础信息）
        """
        logger.info(f"Fetching popular TV series (page={page}, fetch_details={fetch_details})")

        url = f"{self.api_base_url}/tv/popular"
        params = {
            "api_key": self.api_key,
            "language": self.language,
            "page": page,
        }

        try:
            result = await self._make_request(url, params)
            results = result.get("results", [])

            if fetch_details:
                detailed_results = []
                for tv in results[:20]:
                    try:
                        details = await self.get_tv_details(tv["id"])
                        if details:
                            detailed_results.append(details)
                    except TMDBRateLimitException:
                        logger.warning("触发限流，停止获取更多电视剧详情")
                        break
                    except Exception as e:
                        logger.warning(f"Failed to get details for TV {tv['id']}: {str(e)}")
                        continue
                logger.info(f"成功获取 {len(detailed_results)} 部热门剧集（含详情）")
                return detailed_results
            else:
                basic_results = [self._convert_list_item_to_basic(t, "tv") for t in results[:20]]
                logger.info(f"成功获取 {len(basic_results)} 部热门剧集（基础信息）")
                return basic_results

        except (TMDBRateLimitException, TMDBApiException):
            raise
        except Exception as e:
            logger.error(f"获取热门剧集失败: {str(e)}")
            raise

    async def get_top_rated_tv(self, page: int = 1, fetch_details: bool = False) -> List[Dict[str, Any]]:
        """
        获取高分剧集列表

        Args:
            page: 页码
            fetch_details: 是否获取详细信息（默认False，仅返回基础信息）
        """
        logger.info(f"Fetching top rated TV series (page={page}, fetch_details={fetch_details})")

        url = f"{self.api_base_url}/tv/top_rated"
        params = {
            "api_key": self.api_key,
            "language": self.language,
            "page": page,
        }

        try:
            result = await self._make_request(url, params)
            results = result.get("results", [])

            if fetch_details:
                detailed_results = []
                for tv in results[:20]:
                    try:
                        details = await self.get_tv_details(tv["id"])
                        if details:
                            detailed_results.append(details)
                    except TMDBRateLimitException:
                        logger.warning("触发限流，停止获取更多电视剧详情")
                        break
                    except Exception as e:
                        logger.warning(f"Failed to get details for TV {tv['id']}: {str(e)}")
                        continue
                logger.info(f"成功获取 {len(detailed_results)} 部高分剧集（含详情）")
                return detailed_results
            else:
                basic_results = [self._convert_list_item_to_basic(t, "tv") for t in results[:20]]
                logger.info(f"成功获取 {len(basic_results)} 部高分剧集（基础信息）")
                return basic_results

        except (TMDBRateLimitException, TMDBApiException):
            raise
        except Exception as e:
            logger.error(f"获取高分剧集失败: {str(e)}")
            raise

    def _convert_list_item_to_basic(self, item: Dict[str, Any], media_type: str) -> Dict[str, Any]:
        """
        将 TMDB 列表项转换为基础信息格式（用于快速落表）

        Args:
            item: TMDB API 返回的列表项
            media_type: 媒体类型 movie/tv

        Returns:
            基础信息字典，包含 tmdb_id、标题、海报、评分等
        """
        if media_type == "movie":
            # 提取年份
            year = None
            if item.get("release_date"):
                try:
                    year = int(item["release_date"][:4])
                except (ValueError, TypeError, IndexError):
                    pass

            return {
                "tmdb_id": item.get("id"),
                "title": item.get("title"),
                "original_title": item.get("original_title"),
                "year": year,
                "overview": item.get("overview"),
                "rating_tmdb": item.get("vote_average"),
                "votes_tmdb": item.get("vote_count"),
                "poster_url": self._build_image_url(item.get("poster_path"), "w500"),
                "backdrop_url": self._build_image_url(item.get("backdrop_path"), "w1280"),
                "genres": [],  # 列表接口不返回详细类型
                "metadata_source": "tmdb",
                "media_type": "movie",
                "detail_loaded": False,  # 标记为未加载详情
            }
        else:  # tv
            year = None
            if item.get("first_air_date"):
                try:
                    year = int(item["first_air_date"][:4])
                except (ValueError, TypeError, IndexError):
                    pass

            return {
                "tmdb_id": item.get("id"),
                "title": item.get("name"),
                "original_title": item.get("original_name"),
                "year": year,
                "first_air_date": item.get("first_air_date"),
                "overview": item.get("overview"),
                "rating_tmdb": item.get("vote_average"),
                "votes_tmdb": item.get("vote_count"),
                "poster_url": self._build_image_url(item.get("poster_path"), "w500"),
                "backdrop_url": self._build_image_url(item.get("backdrop_path"), "w1280"),
                "genres": [],
                "countries": item.get("origin_country", []),
                "metadata_source": "tmdb",
                "media_type": "tv",
                "detail_loaded": False,
            }

    async def get_tv_season_detail(
        self,
        tmdb_id: int,
        season_number: int,
    ) -> Optional[Dict[str, Any]]:
        """
        获取电视剧季的详情（包含各集信息）

        TMDB API: GET /tv/{tv_id}/season/{season_number}

        Args:
            tmdb_id: TMDB电视剧ID
            season_number: 季数

        Returns:
            Dict: 季详情，包含 episodes 数组，每集含：
                - id: 集ID
                - name: 集标题
                - overview: 简介
                - air_date: 播出日期
                - vote_average: 评分
                - episode_number: 集数
                - crew: 制作人员（含导演）
                - guest_stars: 客串演员
                - still_path: 剧照路径

        Raises:
            TMDBRateLimitException: 触发速率限制
            TMDBApiException: API错误
            httpx.HTTPError: HTTP请求错误
        """
        logger.info(f"Fetching TV season detail: tmdb_id={tmdb_id}, season={season_number}")

        url = f"{self.api_base_url}/tv/{tmdb_id}/season/{season_number}"
        params = {
            "api_key": self.api_key,
            "language": self.language,
            "append_to_response": "credits",
        }

        try:
            result = await self._make_request(url, params)
            return result

        except (TMDBRateLimitException, TMDBApiException):
            raise
        except Exception as e:
            logger.error(f"获取电视剧季详情失败: tmdb_id={tmdb_id}, season={season_number}, 错误: {str(e)}")
            return None

