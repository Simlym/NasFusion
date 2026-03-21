"""
MTeam PT站点适配器

使用x-api-key认证，通过POST方式调用搜索API获取资源
"""
import asyncio
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx

from app.adapters.base import BasePTSiteAdapter
from app.utils.timezone import now, parse_pt_site_time
from app.utils.tv_parser import extract_tv_info
from app.constants import (
    MEDIA_TYPE_ANIME,
    MEDIA_TYPE_BOOK,
    MEDIA_TYPE_GAME,
    MEDIA_TYPE_MOVIE,
    MEDIA_TYPE_MUSIC,
    MEDIA_TYPE_OTHER,
    MEDIA_TYPE_TV,
)

logger = logging.getLogger(__name__)




# MTeam 用户等级 role ID -> 等级名称映射
MTEAM_ROLE_MAP = {
    "1": "User",
    "2": "Power User",
    "3": "Elite User",
    "4": "Crazy User",
    "5": "Insane User",
    "6": "Veteran User",
    "7": "Extreme User",
    "8": "Ultimate User",
    "9": "Nexus Master",
    "10": "VIP",
    "11": "Retiree",
    "12": "Uploader",
    "13": "Moderator",
    "14": "Administrator",
    "15": "SysOp",
    "16": "Staff Leader",
}


class MTeamAdapter(BasePTSiteAdapter):
    """MTeam站点适配器"""

    def __init__(self, config: Dict[str, Any], metadata_mappings: Optional[Dict] = None):
        """
        初始化MTeam适配器

        Args:
            config: 站点配置字典，包含：
                - name: 站点名称
                - base_url: 基础URL（例如：https://kp.m-team.cc）
                - domain: 域名
                - auth_passkey: x-api-key（用于API认证）
                - proxy_config: 代理配置（可选）
                - request_interval: 请求间隔（秒）
            metadata_mappings: 元数据映射字典（可选），包含：
                - video_codecs: {id: mapped_value}
                - audio_codecs: {id: mapped_value}
                - standards: {id: mapped_value}
                - sources: {id: mapped_value}
        """
        super().__init__(config)
        self.api_key = config.get("auth_passkey", "")  # MTeam使用passkey字段存储api_key
        # 下载种子时需要使用 tp cookie，优先使用 auth_passkey，如果没有则使用 auth_cookie
        self.tp_cookie = self.api_key or config.get("auth_cookie", "")
        self.domain = config.get("domain", "kp.m-team.cc")
        self.proxy_config = config.get("proxy_config", {})
        self.request_interval = config.get("request_interval", 2)
        self._last_request_time = 0.0

        # 元数据映射（优先使用传入的动态映射，否则使用硬编码fallback）
        self.metadata_mappings = metadata_mappings or {}

        # 站点ID，用于加载分类映射
        self.site_id = None  # 将在初始化时设置

        # API基础URL（使用api子域名）
        # 根据配置中的base_url动态设置
        base_url = config.get("base_url", "")
        if base_url:
            self.api_base_url = base_url
        else:
            self.api_base_url = "https://api.m-team.cc"

        # User-Agent
        self.user_agent = config.get(
            "user_agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        # HTTP客户端配置
        self.client_config = {
            "timeout": httpx.Timeout(30.0),
            "follow_redirects": True,
        }

        # 如果有代理配置，添加到客户端配置
        if self.proxy_config:
            proxy_url = self.proxy_config.get("url")
            
            # 如果没有直接提供url，尝试从组件构建
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

            if proxy_url:
                self.client_config["proxies"] = proxy_url
                # logger.info(f"Proxy configured: {proxy_url}") # Security risk to log full url with password

        # MTeam API端点
        self.api_endpoints = {
            "search": "/api/torrent/search",  # 资源搜索API
            "detail": "/api/torrent/detail",  # 资源详情API
            "download": "/api/torrent/genDlToken",  # 生成下载token
            "category_list": "/api/torrent/categoryList",  # 分类列表API
            "video_codec_list": "/api/torrent/videoCodecList",  # 视频编码列表API
            "audio_codec_list": "/api/torrent/audioCodecList",  # 音频编码列表API
            "standard_list": "/api/torrent/standardList",  # 分辨率/标准列表API
            "source_list": "/api/torrent/sourceList",  # 来源列表API
            "langs": "/api/system/langs",  # 语言列表API
            "country_list": "/api/system/countryList",  # 国家/地区列表API
            "douban_info": "/api/media/douban/infoV2",  # 豆瓣信息API
        }

        # 分类映射将从数据库动态加载
        self.category_map = None  # 将在初始化时从数据库加载

        # 分辨率映射
        self.resolution_map = {
            "1": "1080p",  # 1080p
            "2": "1080i",  # 1080i
            "3": "720p",  # 720p
            "4": "720i",  # 720i
            "5": "480p",  # 480p
            "6": "2160p",  # 4K/2160p
            "7": "8K",  # 8K
        }

        # 来源映射
        self.source_map = {
            "1": "BluRay",  # 蓝光
            "2": "DVD",  # DVD
            "3": "HDTV",  # HDTV
            "4": "WEB-DL",  # WEB-DL
            "5": "Remux",  # Remux
            "6": "Encode",  # 压制
            "7": "CD",  # CD
            "8": "WEB-DL",  # WEB (映射到WEB-DL)
            "9": "HDTV",  # HDTV Rip
            "10": "Other",  # 其他
        }

        # 视频编码映射
        self.video_codec_map = {
            "1": "H.264",  # H.264/AVC
            "2": "VC-1",  # VC-1
            "3": "MPEG-2",  # MPEG-2
            "4": "MPEG-4",  # MPEG-4
            "5": "XVID",  # XVID
            "6": "H.265",  # H.265/HEVC
            "16": "H.265",  # H.265/HEVC (另一个值)
        }

        # 音频编码映射 (fallback，当metadata未同步时使用)
        self.audio_codec_map = {
            "1": "AAC",
            "2": "AC3",
            "3": "DD",  # Dolby Digital
            "4": "DTS",
            "5": "TrueHD",
            "6": "AAC",  # AAC 2.0
            "7": "LPCM",
            "8": "MP3",
            "9": "FLAC",
            "10": "APE",
            "11": "WAV",
            "12": "DTS-HD",
        }

    def _get_mapped_value(self, metadata_type: str, original_id: str, fallback_map: Dict[str, str]) -> Optional[str]:
        """
        获取映射值，优先使用动态映射，其次使用fallback映射

        Args:
            metadata_type: 元数据类型 (video_codecs/audio_codecs/standards/sources)
            original_id: 原始ID
            fallback_map: 后备映射字典

        Returns:
            映射值，如果都没找到返回None
        """
        # 1. 优先使用动态映射
        if metadata_type in self.metadata_mappings:
            mapped_value = self.metadata_mappings[metadata_type].get(original_id)
            if mapped_value:
                return mapped_value

        # 2. 使用fallback映射
        return fallback_map.get(original_id)

    async def load_category_mappings(self, db) -> None:
        """
        从数据库加载分类映射

        Args:
            db: 数据库会话
        """
        try:
            from app.services.pt.pt_category_service import PTCategoryService

            # 获取站点所有分类
            categories = await PTCategoryService.get_site_categories(db, self.site_id)

            # 构建分类映射字典
            self.category_map = {}
            for category in categories:
                if category.is_active:
                    self.category_map[str(category.category_id)] = category.mapped_category

            logger.info(f"Loaded {len(self.category_map)} category mappings from database for site {self.site_id}")

        except Exception as e:
            logger.warning(f"Failed to load category mappings from database: {str(e)}")
            # 使用硬编码fallback映射
            self.category_map = {
                "401": MEDIA_TYPE_MOVIE, "419": MEDIA_TYPE_MOVIE, "403": MEDIA_TYPE_TV, "402": MEDIA_TYPE_TV,
                "404": MEDIA_TYPE_OTHER, "405": MEDIA_TYPE_ANIME, "406": MEDIA_TYPE_MUSIC, "407": MEDIA_TYPE_MUSIC,
                "408": MEDIA_TYPE_OTHER, "409": MEDIA_TYPE_OTHER, "423": MEDIA_TYPE_GAME, "427": MEDIA_TYPE_BOOK, "434": MEDIA_TYPE_MUSIC
            }

    def _get_headers(self) -> Dict[str, str]:
        """
        获取请求头

        注意：MTeam API 对请求头比较敏感，保持最简单的配置
        不要设置 Referer 和 Origin，避免跨域问题导致 403
        """
        return {
            "User-Agent": self.user_agent,
            "Accept": "*/*",
            "Connection": "keep-alive",
            "x-api-key": self.api_key,
        }

    async def _wait_for_rate_limit(self):
        """等待满足速率限制要求"""
        current_time = asyncio.get_event_loop().time()
        time_since_last_request = current_time - self._last_request_time

        if time_since_last_request < self.request_interval:
            wait_time = self.request_interval - time_since_last_request
            logger.debug(f"Rate limiting: waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)

        self._last_request_time = asyncio.get_event_loop().time()

    async def _make_request(
        self,
        endpoint: str,
        method: str = "POST",
        json_data: Optional[Dict] = None,
        form_data: Optional[Dict] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        发起HTTP请求

        Args:
            endpoint: API端点
            method: HTTP方法
            json_data: JSON请求体
            form_data: Form Data请求体（application/x-www-form-urlencoded）
            **kwargs: 其他请求参数

        Returns:
            API响应JSON

        Raises:
            httpx.HTTPError: 请求失败
        """
        await self._wait_for_rate_limit()

        url = f"{self.api_base_url}{endpoint}"
        headers = self._get_headers()

        # 添加调试信息
        logger.debug(f"API Base URL: {self.api_base_url}")
        logger.debug(f"Full request URL: {url}")
        logger.debug(f"Request method: {method}")
        logger.debug(f"Headers: {headers}")
        logger.debug(f"JSON data: {json_data}")
        logger.debug(f"Form data: {form_data}")
        logger.debug(f"API Key (first 10 chars): {self.api_key[:10] if self.api_key else 'None'}...")

        async with httpx.AsyncClient(**self.client_config) as client:
            logger.debug(f"Making {method} request to {url}")
            if "proxies" in self.client_config:
                logger.info(f"Using proxy: {self.client_config['proxies']}")
            else:
                logger.debug("No proxy configured for this request")

            # 根据数据类型选择发送方式
            if form_data is not None:
                # 使用 Form Data 格式（application/x-www-form-urlencoded）
                logger.info(f"Sending Form Data: {form_data}")
                response = await client.request(method, url, headers=headers, data=form_data, **kwargs)
            else:
                # 使用 JSON 格式
                logger.info(f"Sending JSON Data: {json_data}")
                response = await client.request(method, url, headers=headers, json=json_data, **kwargs)

            # 记录响应状态
            logger.debug(f"=== Response Details ===")
            logger.debug(f"Status Code: {response.status_code}")
            logger.debug(f"Response Headers: {dict(response.headers)}")
            logger.debug(f"Response Content Length: {len(response.content)}")

            response.raise_for_status()

            result = response.json()

            # 检查MTeam API响应格式
            if result.get("code") != "0":
                error_msg = result.get("message", "Unknown error")
                logger.error(f"API Error Response: {result}")
                raise Exception(f"MTeam API error: {error_msg}")

            # 记录响应摘要
            if "data" in result:
                data = result.get("data", {})
                if isinstance(data, dict):
                    logger.info(f"Response Data Keys: {list(data.keys())}")
                    if "data" in data:
                        items = data.get("data", [])
                        logger.info(f"Items Count: {len(items) if isinstance(items, list) else 'N/A'}")
            logger.debug(f"=======================")

            return result

    async def authenticate(self) -> bool:
        """
        验证API Key是否有效

        Returns:
            是否认证成功
        """
        try:
            logger.info(f"Authenticating with MTeam site: {self.site_name}")

            # 通过获取第一页资源来验证API Key
            result = await self.health_check()
            if result:
                logger.info(f"Authentication successful for {self.site_name}")
            else:
                logger.warning(f"Authentication failed for {self.site_name}")

            return result
        except Exception as e:
            logger.error(f"Authentication error for {self.site_name}: {str(e)}")
            return False

    async def fetch_resources(
        self, page: int = 1, limit: int = 100, **filters
    ) -> Dict[str, Any]:
        """
        获取资源列表

        Args:
            page: 页码（从1开始）
            limit: 每页数量（最大100）
            **filters: 额外的过滤参数
                - mode: 资源模式（normal/movie/tvshow/adult，默认normal）
                - categories: 分类列表（例如：["405"]表示动漫）
                - upload_date_start: 上传开始时间（格式：YYYY-MM-DD HH:MM:SS）
                - upload_date_end: 上传结束时间（格式：YYYY-MM-DD HH:MM:SS）

        Returns:
            包含资源列表和分页信息的字典：
                - resources: 资源列表
                - total_pages: 总页数
                - total: 总记录数
                - page_number: 当前页码
                - page_size: 每页大小
        """
        try:
            logger.info(f"Fetching resources from {self.site_name}, page={page}, limit={limit}")

            # 限制每页最大数量
            page_size = min(limit, 100)

            # 构建搜索参数
            search_params = {
                "mode": filters.get("mode", "normal"),  # normal（普通资源）/movie（电影）/tvshow（电视剧）/adult（成人）
                "visible": 1,  # 仅显示可见资源
                "categories": filters.get("categories", []),  # 分类列表（用于区分电影、电视剧、动漫等）
                "pageNumber": page,
                "pageSize": page_size,
            }

            # 添加时间范围参数（如果提供）
            if "upload_date_start" in filters and filters["upload_date_start"]:
                search_params["uploadDateStart"] = filters["upload_date_start"]

            if "upload_date_end" in filters and filters["upload_date_end"]:
                search_params["uploadDateEnd"] = filters["upload_date_end"]

            if "keyword" in filters and filters["keyword"]:
                search_params["keyword"] = filters["keyword"]

            if "sortField" in filters and filters["sortField"]:
                search_params["sortField"] = filters["sortField"]

            if "sortDirection" in filters and filters["sortDirection"]:
                search_params["sortDirection"] = filters["sortDirection"]

            # 发起请求
            endpoint = self.api_endpoints["search"]

            # 输出完整的请求信息
            full_url = f"{self.api_base_url}{endpoint}"
            logger.info(f"=== Request Details ===")
            logger.info(f"URL: {full_url}")
            logger.info(f"Method: POST")
            logger.info(f"Request Body: {search_params}")
            logger.info(f"Filters: {filters}")
            logger.info(f"======================")

            data = await self._make_request(endpoint, method="POST", json_data=search_params)

            # 解析响应
            response_data = data.get("data", {})
            items = response_data.get("data", [])

            # 提取分页信息
            total_pages = int(response_data.get("totalPages", 0))
            total = int(response_data.get("total", 0))
            page_number = int(response_data.get("pageNumber", page))
            page_size = int(response_data.get("pageSize", limit))

            # 转换为标准格式
            resources = []
            for item in items:
                resource = self._parse_resource_item(item)
                if resource:
                    resources.append(resource)

            logger.info(f"Fetched {len(resources)} resources from {self.site_name}, page {page_number}/{total_pages}, total: {total}")
            
            # 返回包含分页信息的字典
            return {
                "resources": resources,
                "total_pages": total_pages,
                "total": total,
                "page_number": page_number,
                "page_size": page_size,
            }

        except httpx.HTTPError as e:
            logger.error(f"HTTP error while fetching resources from {self.site_name}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error fetching resources from {self.site_name}: {str(e)}")
            raise

    def _parse_resource_item(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        解析单个资源项

        Args:
            item: API返回的原始资源数据

        Returns:
            标准化的资源字典
        """
        try:
            status = item.get("status", {})
            torrent_id = str(item.get("id", ""))

            # 提取IMDB和豆瓣ID
            imdb_url = item.get("imdb", "")
            douban_url = item.get("douban", "")

            imdb_id = self._extract_imdb_id(imdb_url) if imdb_url else None
            douban_id = self._extract_douban_id(douban_url) if douban_url else None

            # 映射分类 (使用数据库动态映射)
            category_id = str(item.get("category", ""))
            if self.category_map is None:
                # 如果分类映射未加载，使用默认值
                category = MEDIA_TYPE_OTHER
            else:
                category = self.category_map.get(category_id, MEDIA_TYPE_OTHER)

            # MTeam 没有子分类概念，暂时留空
            subcategory = None

            # 映射分辨率 (使用动态映射)
            standard_id = str(item.get("standard", ""))
            resolution = self._get_mapped_value("standards", standard_id, self.resolution_map)

            # 映射来源 (使用动态映射)
            source_id = str(item.get("source", ""))
            source = self._get_mapped_value("sources", source_id, self.source_map)

            # 映射编码 (使用动态映射)
            video_codec_id = str(item.get("videoCodec", ""))
            video_codec = self._get_mapped_value("video_codecs", video_codec_id, self.video_codec_map)

            audio_codec_id = str(item.get("audioCodec", ""))
            audio_codec = self._get_mapped_value("audio_codecs", audio_codec_id, self.audio_codec_map)

            # 促销类型
            discount = status.get("discount", "NORMAL")
            promotion_type = discount.lower() if discount != "NORMAL" else None
            is_free = discount == "FREE"
            is_discount = discount in ["_2X_FREE", "PERCENT_50", "_2X_50_PERCENT"]
            is_double_upload = discount in ["_2X", "_2X_FREE", "_2X_50_PERCENT"]

            # 构建下载URL
            download_url = f"https://{self.domain}/api/torrent/download/{torrent_id}"

            # 提取电视剧季度/集数信息（仅当category为tv或anime时）
            tv_info = None
            if category in (MEDIA_TYPE_TV, MEDIA_TYPE_ANIME):
                title = item.get("name", "")
                subtitle = item.get("smallDescr", "")
                tv_info = extract_tv_info(title, subtitle)
                if tv_info:
                    logger.debug(f"提取到电视剧信息: {title} -> {tv_info}")

            resource = {
                # 基础信息
                "torrent_id": torrent_id,
                "title": item.get("name", ""),
                "subtitle": item.get("smallDescr", ""),
                "category": category,
                "original_category_id": category_id,
                "subcategory": subcategory,
                # 文件信息
                "size_bytes": int(item.get("size", 0)),
                "file_count": int(item.get("numfiles", 1)),
                "torrent_hash": None,  # MTeam API不直接返回hash
                # 做种信息
                "seeders": int(status.get("seeders", 0)),
                "leechers": int(status.get("leechers", 0)),
                "completions": int(status.get("timesCompleted", 0)),
                "last_seeder_update_at": self._parse_datetime(status.get("lastSeederAction")),
                # 促销信息
                "promotion_type": promotion_type,
                "promotion_expire_at": self._parse_datetime(status.get("discountEndTime")),
                "is_free": is_free,
                "is_discount": is_discount,
                "is_double_upload": is_double_upload,
                # HR信息 (MTeam似乎没有明确的HR字段，暂时设为False)
                "has_hr": False,
                "hr_days": None,
                "hr_seed_time": None,
                "hr_ratio": None,
                # 质量信息
                "resolution": resolution,
                "source": source,
                "codec": video_codec,
                "audio": [audio_codec] if audio_codec else None,
                "subtitle_info": None,  # MTeam API未提供字幕信息
                "quality_tags": item.get("labelsNew", []),
                # 电视剧季度/集数信息
                "tv_info": tv_info,
                # 关联ID
                "imdb_id": imdb_id,
                "douban_id": douban_id,
                "tmdb_id": None,  # MTeam API未提供TMDB ID
                # 评分信息 (列表API中也有)
                "imdb_rating": self._parse_rating(item.get("imdbRating")),
                "douban_rating": self._parse_rating(item.get("doubanRating")),
                # URL
                "detail_url": f"https://kp.{self.domain}/detail/{torrent_id}",
                "download_url": download_url,
                "magnet_link": None,  # 需要单独请求
                # 原始数据
                "raw_page_json": item,
                # 状态和时间
                "is_active": status.get("visible", True) and not status.get("banned", False),
                "last_check_at": now(),
                "published_at": self._parse_datetime(item.get("createdDate")),
                "image_list":item.get("imageList", ""),
            }

            return resource

        except Exception as e:
            logger.error(f"Error parsing resource item: {str(e)}, item id: {item.get('id')}")
            logger.debug(f"Item data: {item}")
            return None

    def _extract_imdb_id(self, imdb_url: str) -> Optional[str]:
        """从IMDB URL中提取ID"""
        if not imdb_url:
            return None
        # 匹配 tt后跟数字
        match = re.search(r"tt\d+", imdb_url)
        return match.group(0) if match else None

    def _extract_douban_id(self, douban_url: str) -> Optional[str]:
        """从豆瓣URL中提取ID"""
        if not douban_url:
            return None
        # 匹配 subject/ 后面的数字
        match = re.search(r"subject/(\d+)", douban_url)
        return match.group(1) if match else None

    def _parse_datetime(self, dt_value: Any) -> Optional[datetime]:
        """
        解析日期时间（MTeam 返回的时间假定为系统时区）

        Args:
            dt_value: 时间值（字符串、datetime对象或时间戳）

        Returns:
            系统时区的 datetime 对象
        """
        if not dt_value:
            return None

        try:
            if isinstance(dt_value, datetime):
                # 如果已经是 datetime 对象，确保有时区信息
                if dt_value.tzinfo is None:
                    from app.utils.timezone import get_system_timezone
                    tz = get_system_timezone()
                    return tz.localize(dt_value)
                return dt_value
            elif isinstance(dt_value, str):
                # MTeam使用格式: "2025-11-07 11:48:14"（假定为系统时区）
                try:
                    return parse_pt_site_time(dt_value, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    # 尝试其他格式
                    formats = [
                        "%Y-%m-%dT%H:%M:%S",
                        "%Y-%m-%d",
                    ]
                    for fmt in formats:
                        try:
                            return parse_pt_site_time(dt_value, fmt)
                        except ValueError:
                            continue

                    # 如果包含 'Z' 后缀，说明是 UTC 时间，需要转换
                    if dt_value.endswith('Z'):
                        try:
                            utc_dt = datetime.strptime(dt_value, "%Y-%m-%dT%H:%M:%SZ")
                            from datetime import timezone
                            from app.utils.timezone import to_system_tz
                            utc_dt = utc_dt.replace(tzinfo=timezone.utc)
                            return to_system_tz(utc_dt)
                        except ValueError:
                            pass

            elif isinstance(dt_value, (int, float)):
                # Unix时间戳（假定为 UTC）
                from datetime import timezone
                from app.utils.timezone import to_system_tz
                utc_dt = datetime.fromtimestamp(dt_value, tz=timezone.utc)
                return to_system_tz(utc_dt)
        except Exception as e:
            logger.warning(f"Failed to parse datetime: {dt_value}, error: {e}")

        return None

    async def get_resource_detail(self, resource_id: str) -> Dict[str, Any]:
        """
        获取资源详情（包含完整描述、MediaInfo等）

        Args:
            resource_id: 资源ID

        Returns:
            资源详情字典（包含额外的detail字段）
        """
        try:
            logger.info(f"Fetching resource detail for {resource_id} from {self.site_name}")

            # 确保 ID 是整数类型（MTeam API 要求）
            try:
                torrent_id = int(resource_id)
            except ValueError:
                raise Exception(f"Invalid torrent ID: {resource_id}, must be a number")

            # MTeam的详情API（使用 Form Data 格式，不是 JSON）
            endpoint = self.api_endpoints["detail"]
            data = await self._make_request(
                endpoint, method="POST", form_data={"id": str(torrent_id)}
            )

            # 解析详情
            detail_data = data.get("data", {})

            # 检查 API 返回
            if not detail_data:
                logger.error(f"MTeam API returned empty data for resource {resource_id}")
                logger.debug(f"Full API response: {data}")
                return {}

            # 首先用通用方法解析基础信息
            resource = self._parse_resource_item(detail_data)

            if not resource:
                logger.error(f"Failed to parse resource item for {resource_id}")
                logger.debug(f"Detail data: {detail_data}")
                return {}

            # 添加detail特有的额外信息
            resource.update({
                # 评分信息
                "imdb_rating": self._parse_rating(detail_data.get("imdbRating")),
                "douban_rating": self._parse_rating(detail_data.get("doubanRating")),

                # 详细描述
                "description": detail_data.get("descr", ""),
                "mediainfo": detail_data.get("mediainfo", ""),
                "origin_file_name": detail_data.get("originFileName", ""),

                # 图片列表
                "image_list": detail_data.get("imageList", []),

                # 标记已获取详情
                "detail_fetched": True,
                "detail_fetched_at": now(),

                # 保存原始detail数据
                "raw_detail_json": detail_data,
            })

            logger.info(f"Successfully fetched detail for resource {resource_id}")
            return resource

        except Exception as e:
            logger.error(f"Error fetching resource detail for {resource_id}: {str(e)}")
            raise

    def _parse_rating(self, rating_str: str) -> Optional[float]:
        """解析评分字符串"""
        if not rating_str:
            return None
        try:
            rating = float(rating_str)
            # 验证评分范围（通常是0-10）
            if 0 <= rating <= 10:
                return rating
            return None
        except (ValueError, TypeError):
            return None

    async def download_torrent(self, resource_id: str, download_url: str = None) -> bytes:
        """
        下载种子文件

        MTeam 下载流程（参考官方脚本）：
        1. 调用 genDlToken API 获取 dlv2 临时链接
        2. 请求 dlv2 链接（会 302 重定向到 az1.halomt.com）
        3. 跟随重定向下载真实的 .torrent 文件

        Args:
            resource_id: 资源ID
            download_url: 完整下载URL（MTeam 不使用此参数，使用 API 获取）

        Returns:
            种子文件字节流
        """
        try:
            logger.info(f"Downloading torrent {resource_id} from {self.site_name}")

            # Step 1: 调用 genDlToken 获取 dlv2 临时链接
            logger.info(f"Generating download token for torrent {resource_id}")

            # genDlToken API 使用 URL 查询参数（不是 JSON body）
            endpoint = f"{self.api_endpoints['download']}?id={resource_id}"
            logger.info(f"Calling genDlToken API endpoint: {endpoint}")

            # 发送 POST 请求，参数在 URL 中
            await self._wait_for_rate_limit()
            url = f"{self.api_base_url}{endpoint}"
            headers = self._get_headers()

            logger.debug(f"genDlToken request URL: {url}")
            logger.debug(f"genDlToken request headers: {headers}")

            async with httpx.AsyncClient(**self.client_config) as client:
                response = await client.post(url, headers=headers)
                response.raise_for_status()
                token_response = response.json()

                logger.debug(f"genDlToken raw response: {token_response}")

                # 检查MTeam API响应格式
                if token_response.get("code") != "0":
                    error_msg = token_response.get("message", "Unknown error")
                    raise Exception(f"MTeam API error: {error_msg}")

            logger.info(f"genDlToken API response code: {token_response.get('code')}")

            # genDlToken 返回的 data 字段直接是 URL 字符串
            dlv2_url = token_response.get("data")

            if not dlv2_url or not isinstance(dlv2_url, str):
                raise Exception(
                    f"Failed to get dlv2 URL from genDlToken API. Response: {token_response}"
                )

            logger.debug(f"Got dlv2 URL: {dlv2_url}")

            # Step 2: 下载种子文件（跟随重定向）
            await self._wait_for_rate_limit()

            # 构建 Cookie 头（使用 tp cookie）
            # 优先使用 auth_passkey，如果没有则使用 auth_cookie
            headers = {
                "User-Agent": self.user_agent,
                "Accept": "application/x-bittorrent, */*",
                "Cookie": f"tp={self.tp_cookie}",  # MTeam 下载需要 tp cookie
            }

            # 配置客户端：允许重定向
            client_config = self.client_config.copy()
            client_config["follow_redirects"] = True

            async with httpx.AsyncClient(**client_config) as client:
                # 请求 dlv2 URL，自动跟随 302 到 az1.halomt.com
                response = await client.get(dlv2_url, headers=headers)

                logger.debug(f"Response status code: {response.status_code}")
                logger.debug(f"Response URL: {response.url}")
                logger.debug(f"Response headers: {dict(response.headers)}")
                logger.debug(f"Response content length: {len(response.content)}")

                response.raise_for_status()

                # 验证是否为种子文件
                content_type = response.headers.get("content-type", "")
                is_torrent = (
                    "torrent" in content_type.lower()
                    or "bittorrent" in content_type.lower()
                    or "application/octet-stream" in content_type.lower()
                    or response.content.startswith(b"d")  # Bencoded 数据以 'd' 开头
                )

                if not is_torrent:
                    logger.warning(
                        f"Unexpected content type for torrent download: {content_type}"
                    )
                    # 如果返回的是JSON（可能是错误信息），尝试解析
                    if "application/json" in content_type:
                        try:
                            error_data = response.json()
                            error_msg = error_data.get("message", "Unknown error from API")
                            raise Exception(f"API returned error: {error_msg}")
                        except Exception as json_error:
                            logger.warning(f"Could not parse JSON response: {json_error}")
                    else:
                        # 显示前100个字节以便调试
                        logger.warning(
                            f"Response content preview (first 100 bytes): {response.content[:100]}"
                        )

                logger.info(
                    f"Successfully downloaded torrent {resource_id}, size: {len(response.content)} bytes"
                )
                return response.content

        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code} error downloading torrent {resource_id}"
            if e.response.content:
                try:
                    error_data = e.response.json()
                    error_msg += f": {error_data.get('message', str(error_data))}"
                except:
                    error_msg += f": {e.response.text[:200]}"
            logger.error(error_msg)
            raise Exception(error_msg)
        except httpx.RequestError as e:
            error_msg = f"Request error downloading torrent {resource_id}: {type(e).__name__} - {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Error downloading torrent {resource_id}: {type(e).__name__} - {str(e) or 'Unknown error'}"
            logger.error(error_msg)
            raise Exception(error_msg)

    async def fetch_user_profile(self) -> Optional[Dict[str, Any]]:
        """
        获取MTeam站点用户信息

        Returns:
            用户信息字典
        """
        try:
            logger.info(f"Fetching user profile from {self.site_name}")

            result = await self._make_request("/api/member/profile", method="POST", json_data={})
            data = result.get("data", {})

            if not data:
                logger.warning(f"Empty user profile data from {self.site_name}")
                return None

            # 解析用户信息
            member_count = data.get("memberCount", {})
            profile = {
                "id": str(data.get("id", "")),
                "email": data.get("email", ""),
                "username": data.get("username", ""),
                "user_class": MTEAM_ROLE_MAP.get(str(data.get("role", "")), str(data.get("role", ""))),
                "uploaded": int(member_count.get("uploaded", 0)),
                "downloaded": int(member_count.get("downloaded", 0)),
                "ratio": float(member_count.get("shareRate", 0)),
                "seeding_count": int(member_count.get("seedingCount", 0) or 0),
                "seeding_size": int(member_count.get("seedingSize", 0) or 0),
                "bonus": float(member_count.get("bonus", 0)),
                "publish_count": int(member_count.get("publishCount", 0) or 0),
                "join_date": data.get("createdDate", ""),
            }

            logger.info(f"Fetched user profile for {profile['username']} from {self.site_name}")
            return profile

        except Exception as e:
            logger.error(f"Error fetching user profile from {self.site_name}: {str(e)}")
            return None

    async def health_check(self) -> bool:
        """
        健康检查

        Returns:
            站点是否正常
        """
        try:
            logger.debug(f"Performing health check for {self.site_name}")

            # 通过获取第一页资源来验证API是否可用
            resources = await self.fetch_resources(page=1, limit=1)

            is_healthy = resources is not None  # 只要能成功获取数据就算健康
            logger.debug(f"Health check result for {self.site_name}: {is_healthy}")

            return is_healthy

        except Exception as e:
            logger.warning(f"Health check failed for {self.site_name}: {str(e)}")
            return False

    async def fetch_categories(self) -> List[Dict[str, Any]]:
        """
        获取站点分类列表

        Returns:
            分类列表
        """
        try:
            logger.info(f"Fetching categories from {self.site_name}")

            # 调用分类列表API
            endpoint = self.api_endpoints["category_list"]
            data = await self._make_request(endpoint, method="POST", json_data={})

            # 解析响应
            response_data = data.get("data", {})
            category_list = response_data.get("list", [])

            logger.info(f"Fetched {len(category_list)} categories from {self.site_name}")

            return category_list

        except Exception as e:
            logger.error(f"Error fetching categories from {self.site_name}: {str(e)}")
            raise

    async def fetch_metadata(self) -> Dict[str, Any]:
        """
        获取站点所有元数据

        Returns:
            包含所有元数据的字典
        """
        try:
            logger.info(f"Fetching metadata from {self.site_name}")

            metadata = {}

            # 获取视频编码列表
            try:
                endpoint = self.api_endpoints["video_codec_list"]
                data = await self._make_request(endpoint, method="POST", json_data={})
                metadata["video_codecs"] = data.get("data", [])
                logger.info(f"Fetched {len(metadata['video_codecs'])} video codecs")
            except Exception as e:
                logger.warning(f"Failed to fetch video codecs: {str(e)}")
                metadata["video_codecs"] = []

            # 获取音频编码列表
            try:
                endpoint = self.api_endpoints["audio_codec_list"]
                data = await self._make_request(endpoint, method="POST", json_data={})
                metadata["audio_codecs"] = data.get("data", [])
                logger.info(f"Fetched {len(metadata['audio_codecs'])} audio codecs")
            except Exception as e:
                logger.warning(f"Failed to fetch audio codecs: {str(e)}")
                metadata["audio_codecs"] = []

            # 获取分辨率/标准列表
            try:
                endpoint = self.api_endpoints["standard_list"]
                data = await self._make_request(endpoint, method="POST", json_data={})
                metadata["standards"] = data.get("data", [])
                logger.info(f"Fetched {len(metadata['standards'])} standards")
            except Exception as e:
                logger.warning(f"Failed to fetch standards: {str(e)}")
                metadata["standards"] = []

            # 获取来源列表
            try:
                endpoint = self.api_endpoints["source_list"]
                data = await self._make_request(endpoint, method="POST", json_data={})
                metadata["sources"] = data.get("data", [])
                logger.info(f"Fetched {len(metadata['sources'])} sources")
            except Exception as e:
                logger.warning(f"Failed to fetch sources: {str(e)}")
                metadata["sources"] = []

            # 获取语言列表
            try:
                endpoint = self.api_endpoints["langs"]
                data = await self._make_request(endpoint, method="POST", json_data={})
                metadata["languages"] = data.get("data", [])
                logger.info(f"Fetched {len(metadata['languages'])} languages")
            except Exception as e:
                logger.warning(f"Failed to fetch languages: {str(e)}")
                metadata["languages"] = []

            # 获取国家/地区列表
            try:
                endpoint = self.api_endpoints["country_list"]
                data = await self._make_request(endpoint, method="POST", json_data={})
                metadata["countries"] = data.get("data", [])
                logger.info(f"Fetched {len(metadata['countries'])} countries")
            except Exception as e:
                logger.warning(f"Failed to fetch countries: {str(e)}")
                metadata["countries"] = []

            logger.info(f"Successfully fetched all metadata from {self.site_name}")
            return metadata

        except Exception as e:
            logger.error(f"Error fetching metadata from {self.site_name}: {str(e)}")
            raise

    async def fetch_douban_info(self, douban_url: str) -> Dict[str, Any]:
        """
        获取豆瓣详细信息

        Args:
            douban_url: 豆瓣URL（如：https://movie.douban.com/subject/35295960/）

        Returns:
            豆瓣详细信息字典
        """
        try:
            logger.info(f"Fetching douban info from {self.site_name} for URL: {douban_url}")

            # 调用豆瓣信息API（注意：需要使用 Form Data 而非 JSON）
            endpoint = self.api_endpoints["douban_info"]
            data = await self._make_request(
                endpoint, method="POST", form_data={"code": douban_url}
            )

            # 解析响应
            douban_data = data.get("data", {})

            # 处理 pubdate（上映日期数组 → release_date）
            release_date = None
            pubdate_list = douban_data.get("pubdate")
            if pubdate_list and isinstance(pubdate_list, list) and len(pubdate_list) > 0:
                # 提取第一个日期，去除括号内的信息（如"(柏林电影节)"）
                # 例如："2025-02-16(柏林电影节)" → "2025-02-16"
                first_date = pubdate_list[0]
                if isinstance(first_date, str):
                    # 使用正则提取日期部分
                    date_match = re.match(r"(\d{4}-\d{2}-\d{2})", first_date)
                    if date_match:
                        date_str = date_match.group(1)
                        # 转换为 date 对象（数据库 Date 类型需要）
                        try:
                            from datetime import datetime
                            release_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                        except ValueError:
                            pass

            # 处理 durations（时长数组 → runtime）
            runtime = None
            durations_list = douban_data.get("durations")
            if durations_list and isinstance(durations_list, list) and len(durations_list) > 0:
                # 提取第一个时长，解析为整数（分钟）
                # 例如："120分钟" → 120
                first_duration = durations_list[0]
                if isinstance(first_duration, str):
                    # 使用正则提取数字部分
                    duration_match = re.search(r"(\d+)", first_duration)
                    if duration_match:
                        try:
                            runtime = int(duration_match.group(1))
                        except ValueError:
                            pass

            # 处理 aka（别名列表，确保是数组）
            aka = douban_data.get("aka")
            if aka is None or not isinstance(aka, list):
                aka = []

            # 构建标准化的豆瓣信息
            douban_info = {
                "subject_id": douban_data.get("subjectId"),
                "imdb_id": douban_data.get("imdbId"),
                "type": douban_data.get("type"),  # movie/tv
                "title": douban_data.get("title"),
                "original_title": douban_data.get("originalTitle"),
                "cover_url": douban_data.get("coverUrl"),
                "subtitle": douban_data.get("subtitle"),
                "score": douban_data.get("score"),
                "rating": douban_data.get("rating"),
                "year": int(douban_data.get("year")) if douban_data.get("year") else None,
                "intro": douban_data.get("intro"),
                "format": douban_data.get("format"),  # BB代码格式的描述
                "aka": aka,  # 别名列表（已处理，确保是数组）
                "languages": douban_data.get("languages", []),
                "genres": douban_data.get("genres", []),  # 类型
                "release_date": release_date,  # 上映日期（从 pubdate 转换）
                "runtime": runtime,  # 时长（从 durations 转换）
                "countries": douban_data.get("countries", []),
                "directors": douban_data.get("directors", []),
                "actors": douban_data.get("actors", []),
                "tags": douban_data.get("tags", []),
                "raw_data": douban_data,  # 保存原始数据
            }

            logger.info(f"Successfully fetched douban info for {douban_url}")
            return douban_info

        except Exception as e:
            logger.error(f"Error fetching douban info for {douban_url}: {str(e)}")
            raise

    async def fetch_dmm_info(self, dmm_code: str) -> Dict[str, Any]:
        """
        获取DMM详细信息（成人内容元数据）

        MTeam 提供了 /api/dmm/dmmInfo 接口，可以通过DMM URL获取详细信息

        Args:
            dmm_code: DMM URL 或产品番号
                - 完整URL: https://www.dmm.co.jp/mono/dvd/-/detail/=/cid=nsps485so/
                - 产品番号: nsps485so

        Returns:
            DMM详细信息字典：
            {
                "url": "https://www.dmm.co.jp/mono/dvd/-/detail/=/cid=nsps485/",
                "product_number": "nsps485so",
                "title": "...",
                "original_title": "...",  # 日文标题
                "release_date": date,
                "duration": "93分",
                "maker": "ながえスタイル",
                "label": "ながえSTYLE",
                "series": "夫公認！",
                "director": "富丈太郎",
                "actresses": ["佐々木あき"],
                "genres": ["人妻・主婦", "不倫", ...],
                "overview": "...",
                "poster_url": "...",
                "image_list": [...],
                "rating": 0.0,
                "raw_data": {...}
            }
        """
        try:
            logger.info(f"Fetching DMM info for: {dmm_code}")

            # 如果不是完整URL，构建URL
            if not dmm_code.startswith("http"):
                # 尝试构建DMM URL
                dmm_url = f"https://www.dmm.co.jp/mono/dvd/-/detail/=/cid={dmm_code}/"
            else:
                dmm_url = dmm_code


            # MTeam DMM API 使用 form-data 格式
            # 注意：需要 _timestamp 和 _sgin 参数（签名），但API可能不强制要求
            await self._wait_for_rate_limit()

            url = f"{self.api_base_url}/api/dmm/dmmInfo"
            headers = self._get_headers()
            headers["Content-Type"] = "application/x-www-form-urlencoded"

            form_data = {
                "dmmCode": dmm_url,
            }

            async with httpx.AsyncClient(**self.client_config) as client:
                response = await client.post(url, headers=headers, data=form_data)
                response.raise_for_status()
                result = response.json()
                print(result)

            # 检查API响应
            if result.get("code") != "0":
                error_msg = result.get("message", "Unknown error")
                logger.warning(f"DMM API returned error: {error_msg}")
                return None

            dmm_data = result.get("data", {})
            if not dmm_data:
                logger.warning(f"DMM API returned empty data for: {dmm_code}")
                return None

            # 解析发行日期
            release_date = None
            release_date_str = dmm_data.get("releaseDate")
            if release_date_str:
                try:
                    from datetime import datetime
                    release_date = datetime.strptime(release_date_str, "%Y/%m/%d").date()
                except ValueError:
                    pass

            # 解析时长（提取数字）
            duration = dmm_data.get("duration", "")
            duration_minutes = None
            if duration:
                duration_match = re.search(r"(\d+)", duration)
                if duration_match:
                    duration_minutes = int(duration_match.group(1))

            # 解析图片列表
            pic_data = dmm_data.get("picData", "")
            image_list = []
            if pic_data:
                image_list = [url.strip() for url in pic_data.split(",") if url.strip()]

            # 提取年份
            year = None
            if release_date:
                year = release_date.year

            # 解析评分
            rating = None
            score_str = dmm_data.get("score")
            if score_str:
                try:
                    rating = float(score_str)
                except (ValueError, TypeError):
                    pass

            # 构建标准化的DMM信息
            poster_url = dmm_data.get("pic1")
            if not poster_url and image_list:
                poster_url = image_list[0]
            
            backdrop_url = dmm_data.get("pic2")

            dmm_info = {
                "url": dmm_data.get("url"),
                "product_number": dmm_data.get("productNumber"),
                "title": dmm_data.get("title"),
                "original_title": dmm_data.get("title"),  # 日文标题
                "release_date": release_date,
                "duration": duration,
                "duration_minutes": duration_minutes,
                "year": year,
                "maker": dmm_data.get("maker"),
                "label": dmm_data.get("label"),
                "series": dmm_data.get("series"),
                "director": dmm_data.get("director"),
                "actresses": dmm_data.get("actressList", []),
                "genres": dmm_data.get("keywordList", []),
                "overview": dmm_data.get("textData"),
                "poster_url": poster_url,
                "backdrop_url": backdrop_url,
                "image_list": image_list,
                "rating": rating,
                "raw_data": dmm_data,
            }

            logger.info(f"Successfully fetched DMM info for {dmm_code}: {dmm_info.get('title', 'N/A')}")
            return dmm_info

        except Exception as e:
            logger.error(f"Error fetching DMM info for {dmm_code}: {str(e)}")
            return None

    @staticmethod
    def extract_dmm_code_from_title(title: str, subtitle: str = "") -> str:
        """
        从PT资源标题中提取DMM番号

        Args:
            title: 资源标题
            subtitle: 资源副标题

        Returns:
            DMM番号，如果未找到返回None
        """
        import re

        # 合并标题和副标题
        full_text = f"{title} {subtitle}".upper()

        # 常见番号模式
        # 格式1: ABC-123 或 ABC123 (字母+数字)
        # 格式2: 123ABC-456 (数字+字母+数字)
        patterns = [
            r'\b([A-Z]{2,6})-?(\d{2,5})\b',  # NSPS-485, ABP123
            r'\b(\d{1,3})([A-Z]{2,6})-?(\d{2,5})\b',  # 118ABW-123
        ]

        for pattern in patterns:
            match = re.search(pattern, full_text)
            if match:
                groups = match.groups()
                if len(groups) == 2:
                    return f"{groups[0].lower()}{groups[1]}"
                elif len(groups) == 3:
                    return f"{groups[0]}{groups[1].lower()}{groups[2]}"

        return None
