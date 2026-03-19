# -*- coding: utf-8 -*-
"""
豆瓣元数据适配器

使用豆瓣Frodo移动端API获取电影/电视剧元数据
"""
import logging
import asyncio
from typing import Optional, Dict, Any, List

from .douban_api import DoubanApi, DoubanApiException, DoubanRateLimitException

logger = logging.getLogger(__name__)


class DoubanAdapter:
    """
    豆瓣元数据适配器

    封装DoubanApi，提供统一的元数据获取接口
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化豆瓣适配器

        Args:
            config: 配置信息，包含：
                - timeout: 超时时间（可选，默认30秒）
                - proxy_config: 代理配置（可选）
                - max_retries: 最大重试次数（可选，默认3次）
                - retry_delay: 重试延迟秒数（可选，默认2秒）
                - verify_ssl: 是否验证SSL证书（可选，默认True）
        """
        self.config = config or {}

        # 超时配置
        timeout = self.config.get("timeout", 30)

        # 代理配置
        proxy_url = None
        proxy_config = self.config.get("proxy_config", {})
        if proxy_config and proxy_config.get("enabled"):
            proxy_url = proxy_config.get("url")

        # 重试配置
        self.max_retries = self.config.get("max_retries", 3)
        self.retry_delay = self.config.get("retry_delay", 2)

        # SSL配置 (DoubanApi 不支持 verify_ssl 参数，且默认不需要配置)
        # verify_ssl = self.config.get("verify_ssl", True)

        # 初始化API客户端
        self.api = DoubanApi(timeout=timeout, proxy_url=proxy_url)

    @staticmethod
    def _extract_image_url(value) -> Optional[str]:
        """从图片字段提取URL（兼容字符串和字典格式）

        豆瓣API的图片字段可能返回纯URL字符串，也可能返回
        {'url': '...', 'width': ..., 'height': ..., 'size': ...} 格式的字典
        """
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            return value.get("url")
        return None

    async def close(self):
        """关闭适配器（释放底层HTTP客户端资源）"""
        if self.api:
            await self.api.close()

    async def __aenter__(self):
        """支持异步上下文管理器"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """退出时自动关闭"""
        await self.close()

    async def _retry_request(self, func, *args, **kwargs) -> Optional[Dict[str, Any]]:
        """
        带重试的请求执行

        Args:
            func: 要执行的异步函数
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            API响应数据

        Raises:
            DoubanApiException: API调用失败
        """
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                return await func(*args, **kwargs)
            except DoubanRateLimitException as e:
                logger.warning(f"豆瓣API速率限制，等待重试 ({attempt + 1}/{self.max_retries})")
                last_exception = e
                # 速率限制时使用指数退避
                await asyncio.sleep(self.retry_delay * (2 ** attempt))
            except DoubanApiException as e:
                # 404 错误不重试
                if "HTTP错误: 404" in str(e):
                    logger.warning(f"豆瓣API资源不存在 (404)，停止重试")
                    raise e

                logger.warning(f"豆瓣API请求失败，重试中 ({attempt + 1}/{self.max_retries}): {str(e)}")
                last_exception = e
                await asyncio.sleep(self.retry_delay)

        logger.error(f"豆瓣API请求失败，已达最大重试次数: {str(last_exception)}")
        raise last_exception

    # ==================== 搜索接口 ====================

    async def search(
        self,
        keyword: str,
        start: int = 0,
        count: int = 20
    ) -> List[Dict[str, Any]]:
        """
        搜索媒体

        Args:
            keyword: 搜索关键词
            start: 起始位置
            count: 返回数量

        Returns:
            搜索结果列表（统一格式）
        """
        logger.info(f"搜索豆瓣: {keyword}")

        result = await self._retry_request(self.api.search, keyword, start, count)

        if not result:
            return []

        # 转换搜索结果
        items = result.get("items", [])
        return [self._convert_search_item(item) for item in items if item.get("target")]

    async def search_by_title(
        self,
        title: str,
        year: Optional[int] = None,
        media_type: str = "movie",
        count: int = 5
    ) -> List[Dict[str, Any]]:
        """
        通过标题搜索媒体（带年份过滤）

        Args:
            title: 搜索标题
            year: 年份（可选，用于过滤结果）
            media_type: 媒体类型（movie/tv）
            count: 返回数量

        Returns:
            搜索结果列表（统一格式）
        """
        logger.info(f"通过标题搜索豆瓣 {media_type}: title={title}, year={year}")

        # 调用通用搜索接口
        results = await self.search(keyword=title, start=0, count=count * 2)

        if not results:
            return []

        # 过滤结果
        filtered_results = []
        for item in results:
            # 过滤媒体类型
            if item.get("media_type") and item["media_type"] != media_type:
                continue

            # 过滤年份（如果提供）
            if year and item.get("year") and abs(item["year"] - year) > 1:
                # 允许±1年的误差
                continue

            filtered_results.append(item)

            if len(filtered_results) >= count:
                break

        logger.info(f"搜索到 {len(filtered_results)} 条结果")
        return filtered_results

    def _convert_search_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        转换搜索结果项

        Args:
            item: API返回的搜索项

        Returns:
            统一格式的搜索结果
        """
        target = item.get("target", {})

        # 提取评分
        rating_value = None
        rating_info = target.get("rating", {})
        if rating_info and rating_info.get("value"):
            try:
                rating_value = float(rating_info["value"])
            except (ValueError, TypeError):
                pass

        # 提取年份
        year = None
        if target.get("year"):
            try:
                year = int(target["year"])
            except (ValueError, TypeError):
                pass

        return {
            "douban_id": target.get("id"),
            "title": target.get("title"),
            "year": year,
            "rating_douban": rating_value,
            "poster_url": target.get("cover_url") or self._extract_image_url(target.get("pic", {}).get("normal")),
            "media_type": target.get("type"),  # movie/tv
            "overview": target.get("card_subtitle", ""),
        }

    # ==================== 详情接口 ====================

    async def get_movie_detail(self, douban_id: str, fetch_celebrities: bool = True, fetch_photos: bool = True) -> Dict[str, Any]:
        """
        获取电影详情

        Args:
            douban_id: 豆瓣电影ID
            fetch_celebrities: 是否获取完整的演职员信息（包含ID、头像等）
            fetch_photos: 是否获取剧照（用于背景图）

        Returns:
            统一格式的电影元数据
        """
        logger.info(f"获取电影详情: {douban_id}")

        detail = await self._retry_request(self.api.movie_detail, douban_id)

        if not detail:
            raise DoubanApiException(f"无法获取电影详情: {douban_id}")

        result = self._convert_to_unified_format(detail, "movie")

        # 如果需要完整演职员信息，额外调用celebrities接口
        if fetch_celebrities:
            try:
                celebrities = await self.get_movie_celebrities(douban_id)
                if celebrities.get("directors"):
                    result["directors"] = celebrities["directors"]
                if celebrities.get("actors"):
                    result["actors"] = celebrities["actors"]
            except Exception as e:
                logger.warning(f"获取演职员详情失败，使用基本信息: {str(e)}")

        # 如果需要获取剧照（用作海报和背景图）
        if fetch_photos:
            try:
                photos = await self.get_photos_for_metadata(douban_id, "movie")
                # 如果没有海报URL，使用第一张照片作为海报
                if not result.get("poster_url") and photos.get("poster_url"):
                    result["poster_url"] = photos["poster_url"]
                    logger.info(f"从剧照获取海报: {photos['poster_url']}")
                # 如果没有背景图URL，使用剧照作为背景图
                if not result.get("backdrop_url") and photos.get("backdrop_url"):
                    result["backdrop_url"] = photos["backdrop_url"]
                    logger.info(f"从剧照获取背景图: {photos['backdrop_url']}")
            except Exception as e:
                logger.warning(f"获取剧照失败: {str(e)}")

        return result

    async def get_tv_detail(self, douban_id: str, fetch_celebrities: bool = True, fetch_photos: bool = True) -> Dict[str, Any]:
        """
        获取电视剧详情

        Args:
            douban_id: 豆瓣电视剧ID
            fetch_celebrities: 是否获取完整的演职员信息（包含ID、头像等）
            fetch_photos: 是否获取剧照（用于背景图）

        Returns:
            统一格式的电视剧元数据
        """
        logger.info(f"获取电视剧详情: {douban_id}")

        detail = await self._retry_request(self.api.tv_detail, douban_id)
        # import json
        # print('detail:',json.dumps(detail, ensure_ascii=False, indent=2))

        if not detail:
            raise DoubanApiException(f"无法获取电视剧详情: {douban_id}")

        result = self._convert_to_unified_format(detail, "tv")

        # 如果需要完整演职员信息，额外调用celebrities接口
        if fetch_celebrities:
            try:
                celebrities = await self.get_tv_celebrities(douban_id)
                if celebrities.get("directors"):
                    result["directors"] = celebrities["directors"]
                if celebrities.get("actors"):
                    result["actors"] = celebrities["actors"]
            except Exception as e:
                logger.warning(f"获取演职员详情失败，使用基本信息: {str(e)}")

        # 如果需要获取剧照（用作海报和背景图）
        if fetch_photos:
            try:
                photos = await self.get_photos_for_metadata(douban_id, "tv")
                # 如果没有海报URL，使用第一张照片作为海报
                if not result.get("poster_url") and photos.get("poster_url"):
                    result["poster_url"] = photos["poster_url"]
                    logger.info(f"从剧照获取海报: {photos['poster_url']}")
                # 如果没有背景图URL，使用剧照作为背景图
                if not result.get("backdrop_url") and photos.get("backdrop_url"):
                    result["backdrop_url"] = photos["backdrop_url"]
                    logger.info(f"从剧照获取背景图: {photos['backdrop_url']}")
            except Exception as e:
                logger.warning(f"获取剧照失败: {str(e)}")

        return result

    async def get_by_douban_id(self, douban_id: str, media_type: str = "movie") -> Dict[str, Any]:
        """
        通过豆瓣ID获取媒体信息

        Args:
            douban_id: 豆瓣ID
            media_type: 媒体类型（movie/tv）

        Returns:
            统一格式的元数据
        """
        if media_type == "tv":
            return await self.get_tv_detail(douban_id)
        else:
            return await self.get_movie_detail(douban_id)

    async def get_by_imdb_id(self, imdb_id: str) -> Dict[str, Any]:
        """
        通过IMDB ID查询豆瓣信息

        Args:
            imdb_id: IMDB ID（如tt1234567）

        Returns:
            统一格式的元数据
        """
        logger.info(f"通过IMDB ID查询: {imdb_id}")

        result = await self._retry_request(self.api.get_by_imdb_id, imdb_id)

        if not result:
            raise DoubanApiException(f"无法通过IMDB ID查询: {imdb_id}")

        # 从IMDB查询结果中获取豆瓣ID，然后获取详情
        douban_id = result.get("id")
        media_type = result.get("type", "movie")

        if douban_id:
            return await self.get_by_douban_id(str(douban_id), media_type)

        # 直接转换IMDB查询结果
        return self._convert_to_unified_format(result, media_type)

    # ==================== 演职员信息 ====================

    async def get_movie_celebrities(self, douban_id: str) -> Dict[str, Any]:
        """
        获取电影演职员信息

        Args:
            douban_id: 豆瓣电影ID

        Returns:
            演职员信息
        """
        logger.info(f"获取电影演职员: {douban_id}")

        result = await self._retry_request(self.api.movie_celebrities, douban_id)

        if not result:
            return {"directors": [], "actors": []}

        return self._convert_celebrities(result)

    async def get_tv_celebrities(self, douban_id: str) -> Dict[str, Any]:
        """
        获取电视剧演职员信息

        Args:
            douban_id: 豆瓣电视剧ID

        Returns:
            演职员信息
        """
        logger.info(f"获取电视剧演职员: {douban_id}")

        result = await self._retry_request(self.api.tv_celebrities, douban_id)

        if not result:
            return {"directors": [], "actors": []}

        return self._convert_celebrities(result)

    def _convert_celebrities(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        转换演职员信息

        Args:
            data: API返回的演职员数据

        Returns:
            统一格式的演职员信息
        """
        directors = []
        actors = []

        # 处理导演
        for director in data.get("directors", []):
            # 尝试从URI中提取subject_id (Personage ID)
            did = director.get("id")
            uri = director.get("uri")
            if uri and "subject_id=" in uri:
                try:
                    import re
                    match = re.search(r'subject_id=(\d+)', uri)
                    if match:
                        did = match.group(1)
                except:
                    pass

            directors.append({
                "douban_id": did,
                "name": director.get("name"),
                "latin_name": director.get("latin_name"),
                "thumb_url": self._extract_image_url(director.get("avatar", {}).get("normal")),
            })

        # 处理演员
        for idx, actor in enumerate(data.get("actors", []), start=1):
            # 尝试从URI中提取subject_id (Personage ID)
            # uri格式: douban://douban.com/celebrity/1054521?subject_id=27260288
            aid = actor.get("id")
            uri = actor.get("uri")
            if uri and "subject_id=" in uri:
                try:
                    import re
                    match = re.search(r'subject_id=(\d+)', uri)
                    if match:
                        aid = match.group(1)
                except:
                    pass

            actors.append({
                "douban_id": aid,
                "name": actor.get("name"),
                "latin_name": actor.get("latin_name"),
                "character": actor.get("character"),
                "thumb_url": self._extract_image_url(actor.get("avatar", {}).get("normal")),
                "order": idx,
            })

        return {
            "directors": directors,
            "actors": actors,
        }

    async def get_person_details(self, douban_id: str) -> Dict[str, Any]:
        """
        获取人物详情

        Args:
            douban_id: 豆瓣人物ID

        Returns:
            统一格式的人物详情
        """
        logger.info(f"获取人物详情: {douban_id}")
        
        detail = await self._retry_request(self.api.person_detail, douban_id)
        
        if not detail:
            logger.warning(f"获取人物详情失败: {douban_id} returned Empty")
            return None
            
        logger.info(f"获取到人物详情原始数据: {douban_id} - {str(detail)[:200]}...")
            
        # 提取各个字段
        # 兼容 Elessar (Personage) 接口和 V2 接口
        
        # 初始值
        name = detail.get("title") or detail.get("name")
        
        # 简介: 优先使用 desc (包含HTML), 其次 extra.short_info, 最后 intro/summary
        biography = detail.get("desc")
        if biography:
            # 去除HTML标签
            try:
                import re
                biography = re.compile(r'<[^>]+>').sub('', biography).strip()
                # 去除CSS样式文本 (简单处理: 如果包含 <style> 则取 <style> 之前的内容，或者已经被上面正则去除了)
                # 上上面的正则已经去除了 <style> 标签本身，但 <style>...</style> 内容可能还在
                # 如果 desc 包含 style 标签及其内容，通常 API 返回的是完整的 HTML 片段
                # 观察 API 返回: <div class="content"><p>...</p></div><style>...</style>
                # 正则 <[^>]+> 会去除 <div>, <p>, <style> 等标签，但 style 内部的内容会保留
                # 所以最好先切分 <style
                if "<style" in detail.get("desc", ""):
                    biography = detail.get("desc").split("<style")[0]
                    biography = re.compile(r'<[^>]+>').sub('', biography).strip()
            except:
                pass
        
        if not biography:
            biography = detail.get("extra", {}).get("short_info")
        if not biography:
            biography = detail.get("intro") or detail.get("summary")

        birthday = None
        place_of_birth = detail.get("birth_place") or detail.get("born_place")
        gender = 0
        other_names = []
        known_for_department = None
        family_info = None
        
        # 处理 Elessar 接口的 extra 字段
        extra = detail.get("extra", {})
        if extra:
            # Info 列表处理 (Attributes)
            # 结构: [["性别", "女"], ["出生日期", "1992年11月6日"], ...]
            info_list = extra.get("info", [])
            for item in info_list:
                if not isinstance(item, list) or len(item) < 2:
                    continue
                
                key = item[0]
                value = item[1]
                
                if "性别" in key:
                    if value == "男":
                        gender = 2
                    elif value == "女":
                        gender = 1
                elif "出生日期" in key:
                    # 尝试解析日期，可能是 "1992年11月6日" 或 "1992-11-06"
                    # 返回 ISO 格式字符串以确保 JSON 可序列化
                    try:
                        import re
                        match = re.search(r'(\d{4})[年-](\d{1,2})[月-](\d{1,2})', value)
                        if match:
                            year, month, day = match.groups()
                            birthday = f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
                        else:
                            # 尝试只提取年份
                            match_year = re.search(r'(\d{4})', value)
                            if match_year:
                                birthday = f"{int(match_year.group(1)):04d}-01-01"
                    except:
                        pass
                elif "出生地" in key:
                    place_of_birth = value
                elif "更多中文名" in key:
                    names = value.split("/")
                    other_names.extend([n.strip() for n in names])
                elif "更多外文名" in key:
                    names = value.split("/")
                    other_names.extend([n.strip() for n in names])
                elif "职业" in key:
                    roles = value.split("/")
                    if roles:
                        known_for_department = roles[0].strip()
                elif "家庭成员" in key or "relation" in key:
                    # 格式: 关系: XXX
                    family_info = value
                elif "IMDb" in key:
                    # 放入别名中以便搜索? 或者忽略
                    pass

            # 如果没有找到职业，尝试从 short_info 解析
            # short_info 格式: "演员 配音 音乐 ... / 作品 ..."
            if not known_for_department and extra.get("short_info"):
                short_info = extra.get("short_info")
                # 取斜杠前的部分
                roles_part = short_info.split("/")[0].strip()
                # 取第一个词
                if roles_part:
                    known_for_department = roles_part.split(" ")[0]

        # 旧版逻辑兜底 (V2 / Celebrity 接口)
        if not birthday:
            birthday_str = detail.get("birthday")
            if birthday_str:
                # 直接使用字符串格式，确保 JSON 可序列化
                try:
                    import re
                    match = re.search(r'(\d{4}-\d{1,2}-\d{1,2})', birthday_str)
                    if match:
                        birthday = match.group(1)
                except:
                    pass

        if gender == 0:
            gender_str = detail.get("gender")
            if gender_str == "男":
                gender = 2
            elif gender_str == "女":
                gender = 1
        
        # 别名 (AKA)
        aka = detail.get("aka", []) or []
        if isinstance(aka, list):
             # 过滤掉包含冒号的属性行 (V1接口兼容)
            request_aka = [x for x in aka if ":" not in x]
            other_names.extend(request_aka)
            
        aka_en = detail.get("aka_en", []) or []
        if isinstance(aka_en, list):
            other_names.extend(aka_en)
            
        # 去重
        other_names = list(set([n for n in other_names if n]))
        
        # 职业/部门
        if not known_for_department:
            unusual_roles = detail.get("roles", []) or detail.get("professions", [])
            known_for_department = unusual_roles[0] if unusual_roles else None
        
        # 图片处理
        # Elessar: cover_img.url 或 cover.normal.url
        # V2: cover_url 或 avatar.normal
        profile_url = None
        if detail.get("cover_img"):
            profile_url = self._extract_image_url(detail.get("cover_img"))
        elif detail.get("cover"):
            profile_url = self._extract_image_url(detail.get("cover", {}).get("normal"))
        
        if not profile_url:
            profile_url = self._extract_image_url(detail.get("cover_url")) or self._extract_image_url(detail.get("avatar", {}).get("normal")) or self._extract_image_url(detail.get("pic", {}).get("large"))

        # 转换
        return {
            "douban_id": str(detail.get("id")),
            "name": name, 
            "other_names": other_names,
            "biography": biography,
            "birthday": birthday,  # ISO 格式字符串，如 "1992-11-06"
            "deathday": None, 
            "place_of_birth": place_of_birth,
            "gender": gender,
            "homepage": detail.get("website") or detail.get("sharing_url"),
            "known_for_department": known_for_department,
            "popularity": detail.get("followed_count", 0) / 1000 if detail.get("followed_count") else None, 
            "profile_url": profile_url, 
            "metadata_source": "douban",
            "detail_loaded": True,
            "family_info": family_info
        }

    async def get_photos_for_metadata(self, douban_id: str, media_type: str = "movie") -> Dict[str, Optional[str]]:
        """
        从剧照接口获取海报和背景图URL

        Args:
            douban_id: 豆瓣ID
            media_type: 媒体类型（movie/tv）

        Returns:
            包含poster_url和backdrop_url的字典
        """
        result = {
            "poster_url": None,
            "backdrop_url": None,
        }

        try:
            # 获取所有类型的剧照（R=剧照/海报/壁纸）
            if media_type == "tv":
                photos_data = await self._retry_request(
                    self.api.tv_photos, douban_id, photo_type="R", start=0, count=10
                )
            else:
                photos_data = await self._retry_request(
                    self.api.movie_photos, douban_id, photo_type="R", start=0, count=10
                )

            if not photos_data:
                logger.debug(f"未获取到剧照数据: {douban_id}")
                return result

            # 提取照片列表
            photos = photos_data.get("photos", [])
            if not photos:
                logger.debug(f"剧照列表为空: {douban_id}")
                return result

            # 遍历照片，区分竖版（海报）和横版（背景图）
            # 豆瓣photos返回格式: {"photos": [{"image": {"large": "url"}, "width": 1080, "height": 1920, ...}]}
            for photo in photos:
                image_info = photo.get("image", {})
                width = photo.get("width", 0)
                height = photo.get("height", 0)

                # 优先使用 large，其次 normal（兼容字符串和字典格式）
                image_url = self._extract_image_url(image_info.get("large")) or self._extract_image_url(image_info.get("normal"))
                if not image_url:
                    continue

                # 判断图片方向
                if width and height:
                    aspect_ratio = width / height
                    # 竖版图片作为海报 (宽高比 < 1.0)
                    if aspect_ratio < 1.0 and not result["poster_url"]:
                        result["poster_url"] = image_url
                        logger.debug(f"找到海报图片: {douban_id} -> {image_url} ({width}x{height})")
                    # 横版图片作为背景图 (宽高比 >= 1.5)
                    elif aspect_ratio >= 1.5 and not result["backdrop_url"]:
                        result["backdrop_url"] = image_url
                        logger.debug(f"找到背景图: {douban_id} -> {image_url} ({width}x{height})")
                else:
                    # 如果没有宽高信息，第一张作为海报，第二张作为背景
                    if not result["poster_url"]:
                        result["poster_url"] = image_url
                    elif not result["backdrop_url"]:
                        result["backdrop_url"] = image_url

                # 如果两个都找到了，就退出循环
                if result["poster_url"] and result["backdrop_url"]:
                    break

            if result["poster_url"]:
                logger.info(f"成功获取海报: {douban_id}")
            if result["backdrop_url"]:
                logger.info(f"成功获取背景图: {douban_id}")

            return result

        except Exception as e:
            logger.warning(f"获取剧照失败: {douban_id}, 错误: {str(e)}")
            return result

    # ==================== 推荐接口 ====================

    async def get_movie_recommendations(
        self,
        douban_id: str,
        count: int = 10
    ) -> List[Dict[str, Any]]:
        """
        获取电影推荐

        Args:
            douban_id: 豆瓣电影ID
            count: 返回数量

        Returns:
            推荐电影列表
        """
        logger.info(f"获取电影推荐: {douban_id}")

        result = await self._retry_request(
            self.api.movie_recommendations, douban_id, 0, count
        )

        if not result:
            return []

        # 推荐API直接返回列表
        if isinstance(result, list):
            items = result
        else:
            items = result.get("items", [])

        return [self._convert_search_item({"target": item}) for item in items]

    async def get_tv_recommendations(
        self,
        douban_id: str,
        count: int = 10
    ) -> List[Dict[str, Any]]:
        """
        获取电视剧推荐

        Args:
            douban_id: 豆瓣电视剧ID
            count: 返回数量

        Returns:
            推荐电视剧列表
        """
        logger.info(f"获取电视剧推荐: {douban_id}")

        result = await self._retry_request(
            self.api.tv_recommendations, douban_id, 0, count
        )

        if not result:
            return []

        # 推荐API直接返回列表
        if isinstance(result, list):
            items = result
        else:
            items = result.get("items", [])

        return [self._convert_search_item({"target": item}) for item in items]

    # ==================== 热门/榜单接口 ====================

    async def get_hot_movies(self, start: int = 0, count: int = 20) -> List[Dict[str, Any]]:
        """
        获取热门电影

        Args:
            start: 起始位置
            count: 返回数量

        Returns:
            热门电影列表
        """
        logger.info(f"获取热门电影 (start={start}, count={count})")

        result = await self._retry_request(self.api.movie_hot, start, count)

        if not result:
            return []

        items = result.get("subject_collection_items", [])
        return [self._convert_collection_item(item) for item in items]

    async def get_hot_tv(self, start: int = 0, count: int = 20) -> List[Dict[str, Any]]:
        """
        获取热门剧集

        Args:
            start: 起始位置
            count: 返回数量

        Returns:
            热门剧集列表
        """
        logger.info(f"获取热门剧集 (start={start}, count={count})")

        result = await self._retry_request(self.api.tv_hot, start, count)

        if not result:
            return []

        items = result.get("subject_collection_items", [])
        return [self._convert_collection_item(item) for item in items]

    async def get_top250_movies(self, start: int = 0, count: int = 20) -> List[Dict[str, Any]]:
        """
        获取电影TOP250

        Args:
            start: 起始位置
            count: 返回数量

        Returns:
            TOP250电影列表
        """
        logger.info(f"获取电影TOP250 (start={start}, count={count})")

        result = await self._retry_request(self.api.movie_top250, start, count)

        if not result:
            return []

        items = result.get("subject_collection_items", [])
        return [self._convert_collection_item(item) for item in items]

    async def get_tv_animation(self, start: int = 0, count: int = 20) -> List[Dict[str, Any]]:
        """获取动画榜单"""
        logger.info(f"获取动画榜单 (start={start}, count={count})")
        result = await self._retry_request(self.api.tv_animation, start, count)
        if not result:
            return []
        items = result.get("subject_collection_items", [])
        return [self._convert_collection_item(item) for item in items]

    async def get_tv_domestic(self, start: int = 0, count: int = 20) -> List[Dict[str, Any]]:
        """获取国产剧榜单"""
        logger.info(f"获取国产剧榜单 (start={start}, count={count})")
        result = await self._retry_request(self.api.tv_domestic, start, count)
        if not result:
            return []
        items = result.get("subject_collection_items", [])
        return [self._convert_collection_item(item) for item in items]

    async def get_tv_american(self, start: int = 0, count: int = 20) -> List[Dict[str, Any]]:
        """获取美剧榜单"""
        logger.info(f"获取美剧榜单 (start={start}, count={count})")
        result = await self._retry_request(self.api.tv_american, start, count)
        if not result:
            return []
        items = result.get("subject_collection_items", [])
        return [self._convert_collection_item(item) for item in items]

    async def get_tv_japanese(self, start: int = 0, count: int = 20) -> List[Dict[str, Any]]:
        """获取日剧榜单"""
        logger.info(f"获取日剧榜单 (start={start}, count={count})")
        result = await self._retry_request(self.api.tv_japanese, start, count)
        if not result:
            return []
        items = result.get("subject_collection_items", [])
        return [self._convert_collection_item(item) for item in items]

    async def get_tv_korean(self, start: int = 0, count: int = 20) -> List[Dict[str, Any]]:
        """获取韩剧榜单"""
        logger.info(f"获取韩剧榜单 (start={start}, count={count})")
        result = await self._retry_request(self.api.tv_korean, start, count)
        if not result:
            return []
        items = result.get("subject_collection_items", [])
        return [self._convert_collection_item(item) for item in items]

    async def get_tv_chinese_weekly(self, start: int = 0, count: int = 20) -> List[Dict[str, Any]]:
        """获取华语口碑剧集周榜"""
        logger.info(f"获取华语口碑周榜 (start={start}, count={count})")
        result = await self._retry_request(self.api.tv_chinese_best_weekly, start, count)
        if not result:
            return []
        items = result.get("subject_collection_items", [])
        return [self._convert_collection_item(item) for item in items]

    async def get_tv_global_weekly(self, start: int = 0, count: int = 20) -> List[Dict[str, Any]]:
        """获取全球口碑剧集周榜"""
        logger.info(f"获取全球口碑周榜 (start={start}, count={count})")
        result = await self._retry_request(self.api.tv_global_best_weekly, start, count)
        if not result:
            return []
        items = result.get("subject_collection_items", [])
        return [self._convert_collection_item(item) for item in items]

    async def get_movie_scifi(self, start: int = 0, count: int = 20) -> List[Dict[str, Any]]:
        """获取高分经典科幻片榜"""
        logger.info(f"获取高分科幻片榜 (start={start}, count={count})")
        result = await self._retry_request(self.api.movie_scifi, start, count)
        if not result:
            return []
        items = result.get("subject_collection_items", [])
        return [self._convert_collection_item(item) for item in items]

    async def get_movie_comedy(self, start: int = 0, count: int = 20) -> List[Dict[str, Any]]:
        """获取高分经典喜剧片榜"""
        logger.info(f"获取高分喜剧片榜 (start={start}, count={count})")
        result = await self._retry_request(self.api.movie_comedy, start, count)
        if not result:
            return []
        items = result.get("subject_collection_items", [])
        return [self._convert_collection_item(item) for item in items]

    async def get_movie_action(self, start: int = 0, count: int = 20) -> List[Dict[str, Any]]:
        """获取高分经典动作片榜"""
        logger.info(f"获取高分动作片榜 (start={start}, count={count})")
        result = await self._retry_request(self.api.movie_action, start, count)
        if not result:
            return []
        items = result.get("subject_collection_items", [])
        return [self._convert_collection_item(item) for item in items]

    async def get_movie_love(self, start: int = 0, count: int = 20) -> List[Dict[str, Any]]:
        """获取高分经典爱情片榜"""
        logger.info(f"获取高分爱情片榜 (start={start}, count={count})")
        result = await self._retry_request(self.api.movie_love, start, count)
        if not result:
            return []
        items = result.get("subject_collection_items", [])
        return [self._convert_collection_item(item) for item in items]

    def _convert_collection_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        转换榜单项

        Args:
            item: API返回的榜单项

        Returns:
            统一格式的结果
        """
        # 提取评分
        rating_value = None
        rating_info = item.get("rating", {})
        if rating_info and rating_info.get("value"):
            try:
                rating_value = float(rating_info["value"])
            except (ValueError, TypeError):
                pass

        # 提取年份
        year = None
        if item.get("year"):
            try:
                year = int(item["year"])
            except (ValueError, TypeError):
                pass

        return {
            "douban_id": item.get("id"),
            "title": item.get("title"),
            "year": year,
            "rating_douban": rating_value,
            "poster_url": item.get("cover", {}).get("url") or self._extract_image_url(item.get("pic", {}).get("normal")),
            "media_type": item.get("type"),
            "overview": item.get("card_subtitle", ""),
        }

    # ==================== 数据格式转换 ====================

    def _convert_to_unified_format(
        self,
        douban_data: Dict[str, Any],
        media_type: str = "movie"
    ) -> Dict[str, Any]:
        """
        将豆瓣API数据转换为统一格式

        Args:
            douban_data: 豆瓣API返回的详情数据
            media_type: 媒体类型（movie/tv）

        Returns:
            符合UnifiedMovie/UnifiedTV模型的字段字典
        """
        # 输出原始豆瓣数据到日志（用于调试）
        import json
        logger.debug(f"🔍 豆瓣原始数据 (media_type={media_type}): {json.dumps(douban_data, ensure_ascii=False, indent=2)}")

        # 提取评分
        rating_value = None
        votes_douban = None
        rating_info = douban_data.get("rating", {})
        if rating_info:
            if rating_info.get("value"):
                try:
                    rating_value = float(rating_info["value"])
                except (ValueError, TypeError):
                    pass
            if rating_info.get("count"):
                try:
                    votes_douban = int(rating_info["count"])
                except (ValueError, TypeError):
                    pass

        # 提取年份
        year = None
        if douban_data.get("year"):
            try:
                year = int(douban_data["year"])
            except (ValueError, TypeError):
                pass

        # 提取时长
        runtime = None
        durations = douban_data.get("durations", [])
        if durations and len(durations) > 0:
            duration_str = durations[0]  # "128分钟" 或 "128"
            try:
                # 移除"分钟"字样
                runtime = int(str(duration_str).replace("分钟", "").strip())
            except (ValueError, AttributeError):
                pass

        # 提取上映/首播日期
        release_date = None
        first_air_date = None
        pubdates = douban_data.get("pubdates", [])
        if pubdates and len(pubdates) > 0:
            # 提取第一个日期，去除地区信息（如"(中国大陆)"）
            # 例如："2025-02-16(柏林电影节)" → "2025-02-16"
            first_date = pubdates[0]
            if isinstance(first_date, str):
                # 使用正则提取日期部分
                import re
                date_match = re.match(r"(\d{4}-\d{2}-\d{2})", first_date)
                if date_match:
                    date_str = date_match.group(1)
                    # 转换为 date 对象（数据库 Date 类型需要）
                    try:
                        from datetime import datetime
                        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                        if media_type == "tv":
                            first_air_date = date_obj
                        else:
                            release_date = date_obj
                    except ValueError:
                        pass

        # 转换导演信息
        # 注意：基本详情API可能只返回name，完整信息需要调用celebrities接口
        directors = []
        for director in douban_data.get("directors", []):
            if isinstance(director, str):
                # 如果只是字符串（旧版API）
                directors.append({
                    "douban_id": None,
                    "name": director,
                    "latin_name": None,
                    "thumb_url": None,
                })
            elif isinstance(director, dict):
                # 如果是字典对象
                directors.append({
                    "douban_id": director.get("id"),
                    "name": director.get("name"),
                    "latin_name": director.get("latin_name"),
                    "thumb_url": self._extract_image_url(director.get("avatar", {}).get("normal")) if isinstance(director.get("avatar"), dict) else None,
                })

        # 转换演员信息
        actors = []
        for idx, actor in enumerate(douban_data.get("actors", []), start=1):
            if isinstance(actor, str):
                # 如果只是字符串（旧版API）
                actors.append({
                    "douban_id": None,
                    "name": actor,
                    "latin_name": None,
                    "character": None,
                    "thumb_url": None,
                    "order": idx,
                })
            elif isinstance(actor, dict):
                # 如果是字典对象
                actors.append({
                    "douban_id": actor.get("id"),
                    "name": actor.get("name"),
                    "latin_name": actor.get("latin_name"),
                    "character": actor.get("character"),
                    "thumb_url": self._extract_image_url(actor.get("avatar", {}).get("normal")) if isinstance(actor.get("avatar"), dict) else None,
                    "order": idx,
                })

        # 提取海报URL
        poster_url = None
        pic_info = douban_data.get("pic", {})
        if isinstance(pic_info, dict):
            poster_url = self._extract_image_url(pic_info.get("large")) or self._extract_image_url(pic_info.get("normal"))
        elif douban_data.get("cover_url"):
            poster_url = douban_data["cover_url"]

        # 提取别名
        aka = []
        if douban_data.get("aka"):
            aka = douban_data["aka"] if isinstance(douban_data["aka"], list) else []

        # 提取类型 - 优先从 card_subtitle 获取完整类型
        # 豆瓣API的 genres 字段只返回前3个类型，不完整
        # card_subtitle 格式: "1998 / 日本 / 剧情 动作 科幻 动画 奇幻 / 导演名"
        genres = douban_data.get("genres", [])
        card_subtitle = douban_data.get("card_subtitle", "")
        if card_subtitle and " / " in card_subtitle:
            try:
                # 分割 card_subtitle，类型信息在第二个和第三个 "/" 之间
                parts = card_subtitle.split(" / ")
                if len(parts) >= 3:
                    # 提取类型部分并分割
                    genre_part = parts[2]
                    # 去掉后面的导演信息（如果有）
                    # 类型部分可能是 "剧情 动作 科幻 动画 奇幻"
                    extracted_genres = genre_part.split()
                    if extracted_genres and len(extracted_genres) > len(genres):
                        genres = extracted_genres
                        logger.info(f"从 card_subtitle 提取完整类型: {genres}")
            except Exception as e:
                logger.debug(f"从 card_subtitle 提取类型失败: {e}")

        # 提取标签（转换为字符串列表）
        tags = []
        raw_tags = douban_data.get("tags", [])
        if raw_tags:
            for tag in raw_tags:
                if isinstance(tag, dict):
                    # 如果是字典（包含 name 和 uri），提取 name
                    tags.append(tag.get("name", ""))
                elif isinstance(tag, str):
                    # 如果已经是字符串，直接使用
                    tags.append(tag)

        # 电视剧特有字段：集数信息
        episodes_count = None
        if media_type == "tv":
            # 豆瓣使用 episodes_count 字段存储总集数
            if douban_data.get("episodes_count"):
                try:
                    episodes_count = int(douban_data["episodes_count"])
                except (ValueError, TypeError):
                    pass

        result = {
            # 标识
            "douban_id": douban_data.get("id"),
            "imdb_id": douban_data.get("imdb_id"),

            # 标题
            "title": douban_data.get("title"),
            "original_title": douban_data.get("original_title"),
            "aka": aka,

            # 基础信息
            "year": year,
            "runtime": runtime,

            # 评分
            "rating_douban": rating_value,
            "votes_douban": votes_douban,

            # 分类/标签
            "genres": genres,  # 使用从 card_subtitle 提取的完整类型
            "tags": tags,
            "languages": douban_data.get("languages", []),
            "countries": douban_data.get("countries", []),

            # 人员
            "directors": directors,
            "actors": actors,

            # 内容描述
            "overview": douban_data.get("intro"),

            # 图片
            "poster_url": poster_url,
            "backdrop_url": None,  # 豆瓣详情API不返回背景图，需要额外调用photos接口获取

            # 元数据来源
            "metadata_source": "douban",
            "detail_loaded": True,
        }

        # 添加日期字段
        if media_type == "tv":
            result["first_air_date"] = first_air_date
            result["number_of_episodes"] = episodes_count
            # 注意：豆瓣API不提供季数信息，保持为None
        else:
            result["release_date"] = release_date

        return result

    # ==================== 兼容旧接口 ====================

    async def get_by_url(self, douban_url: str) -> Dict[str, Any]:
        """
        通过豆瓣URL获取电影信息（兼容旧接口）

        Args:
            douban_url: 豆瓣电影URL，如 https://movie.douban.com/subject/25954475/

        Returns:
            转换后的电影元数据
        """
        # 从URL中提取豆瓣ID
        import re
        match = re.search(r"/subject/(\d+)", douban_url)
        if not match:
            raise ValueError(f"无效的豆瓣URL: {douban_url}")

        douban_id = match.group(1)

        # 判断媒体类型
        if "/movie/" in douban_url or "movie.douban.com" in douban_url:
            return await self.get_movie_detail(douban_id)
        else:
            # 默认尝试电影
            return await self.get_movie_detail(douban_id)
