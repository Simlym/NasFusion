# -*- coding: utf-8 -*-
"""
媒体识别服务
整合文件名解析、TMDB搜索、下载任务信息，实现媒体文件识别
"""
import logging
from typing import Optional, List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.media_file import MediaFile
from app.models.unified_movie import UnifiedMovie
from app.models.unified_tv_series import UnifiedTVSeries
from app.models.unified_adult import UnifiedAdult
from app.adapters.metadata.tmdb_adapter import TMDBAdapter
from app.services.common.filename_parser_service import FilenameParserService
from app.services.common.system_setting_service import SystemSettingService
from app.constants import MEDIA_TYPE_MOVIE, MEDIA_TYPE_TV, MEDIA_TYPE_ADULT, UNIFIED_TABLE_ADULT
from app.services.identification.adult_identify_service import AdultIdentifyService

logger = logging.getLogger(__name__)


class MediaIdentifyService:
    """媒体识别服务"""

    def __init__(self):
        # TMDB适配器将在首次使用时从数据库配置初始化
        self._tmdb_adapter: Optional[TMDBAdapter] = None
        self._adapter_initialized = False

    async def _get_tmdb_adapter(self, db: AsyncSession) -> TMDBAdapter:
        """
        获取TMDB适配器，从数据库读取配置

        配置从 system_settings 表读取：
        - category: "metadata_scraping"
        - keys: "tmdb_api_key", "tmdb_language"
        """
        if self._tmdb_adapter is not None and self._adapter_initialized:
            return self._tmdb_adapter

        # 从数据库读取配置
        api_key_setting = await SystemSettingService.get_by_key(db, "metadata_scraping", "tmdb_api_key")
        language_setting = await SystemSettingService.get_by_key(db, "metadata_scraping", "tmdb_language")

        if not api_key_setting or not api_key_setting.value:
            raise ValueError("TMDB API Key未配置，请在系统设置中配置 metadata_scraping.tmdb_api_key")

        api_key = api_key_setting.value
        language = language_setting.value if language_setting else "zh-CN"

        logger.info(f"从数据库加载TMDB配置: language={language}")

        self._tmdb_adapter = TMDBAdapter({
            "api_key": api_key,
            "language": language,
        })
        self._adapter_initialized = True

        return self._tmdb_adapter

    async def identify_media_file(
        self,
        db: AsyncSession,
        media_file: MediaFile,
        force_search: bool = False,
    ) -> Dict[str, Any]:
        """
        识别媒体文件

        策略：
        1. 如果有下载任务，尝试从下载任务获取信息
        2. 否则，从文件名解析并搜索TMDB

        Args:
            db: 数据库会话
            media_file: 媒体文件对象
            force_search: 强制搜索（忽略已有关联）

        Returns:
            识别结果：
            {
                "success": bool,
                "candidates": [...],  # TMDB搜索结果候选列表
                "auto_matched": bool,  # 是否自动匹配
                "matched_id": int,    # 匹配的资源ID（如果自动匹配）
                "match_source": str,  # 匹配来源：download_task, filename, manual
                "parsed_info": {...}, # 文件名解析信息
                "error": str,         # 错误信息（如果失败）
            }
        """
        result = {
            "success": False,
            "candidates": [],
            "auto_matched": False,
            "matched_id": None,
            "match_source": None,
            "parsed_info": None,
            "error": None,
        }

        # 检查是否已识别
        if not force_search and media_file.unified_resource_id:
            logger.info(f"媒体文件已识别: {media_file.file_name}")
            result["success"] = True
            result["auto_matched"] = True
            result["matched_id"] = media_file.unified_resource_id
            result["match_source"] = "already_identified"
            return result

        # 策略1：尝试从下载任务获取信息
        if media_file.download_task_id:
            try:
                task_result = await self._identify_from_download_task(db, media_file)
                if task_result.get("success"):
                    return task_result
            except Exception as e:
                logger.warning(f"从下载任务识别失败: {e}")

        # 策略2：从文件名解析
        parsed_info = FilenameParserService.parse_media_file(media_file.file_path)
        result["parsed_info"] = parsed_info

        if parsed_info.get("error"):
            result["error"] = f"文件名解析失败: {parsed_info['error']}"
            return result

        # 确定媒体类型
        media_type = media_file.media_type or FilenameParserService.guess_media_type(parsed_info)

        # 成人资源使用专门的识别流程
        if media_type == MEDIA_TYPE_ADULT:
            return await self._identify_adult(db, media_file, parsed_info)

        # 搜索TMDB
        try:
            if media_type in (MEDIA_TYPE_MOVIE, "movie"):
                candidates = await self._search_movie(db, parsed_info)
            elif media_type in (MEDIA_TYPE_TV, "tv", "episode"):
                candidates = await self._search_tv(db, parsed_info)
            else:
                # 尝试两种搜索
                candidates = await self._search_movie(db, parsed_info)
                if not candidates:
                    candidates = await self._search_tv(db, parsed_info)

            result["candidates"] = candidates
            result["success"] = True

            # 自动匹配逻辑
            if candidates and len(candidates) == 1:
                # 只有一个结果，自动匹配
                result["auto_matched"] = True
                result["matched_id"] = candidates[0].get("tmdb_id")
                result["match_source"] = "filename_auto"
            elif candidates and len(candidates) > 1:
                # 多个结果，检查是否有高置信度匹配
                best_match = self._find_best_match(parsed_info, candidates)
                if best_match:
                    result["auto_matched"] = True
                    result["matched_id"] = best_match.get("tmdb_id")
                    result["match_source"] = "filename_auto"

        except Exception as e:
            logger.error(f"TMDB搜索失败: {e}")
            result["error"] = f"TMDB搜索失败: {str(e)}"

        return result

    async def _identify_from_download_task(
        self, db: AsyncSession, media_file: MediaFile
    ) -> Dict[str, Any]:
        """
        从下载任务获取识别信息

        如果下载任务关联了PT资源，PT资源可能已有TMDB/IMDB ID
        """
        result = {
            "success": False,
            "candidates": [],
            "auto_matched": False,
            "matched_id": None,
            "match_source": None,
            "parsed_info": None,
            "error": None,
        }

        # 加载下载任务
        if not media_file.download_task:
            await db.refresh(media_file, ["download_task"])

        task = media_file.download_task
        if not task:
            return result

        # 检查下载任务是否关联了统一资源
        if task.unified_table_name and task.unified_resource_id:
            # 已有关联，直接使用
            result["success"] = True
            result["auto_matched"] = True
            result["matched_id"] = task.unified_resource_id
            result["match_source"] = "download_task"
            logger.info(
                f"从下载任务获取关联: {task.unified_table_name}:{task.unified_resource_id}"
            )
            return result

        # 检查PT资源是否有IMDB ID
        # TODO: 加载PT资源并检查IMDB ID
        # 这里可以扩展以从PT资源获取更多信息

        return result

    async def _search_movie(self, db: AsyncSession, parsed_info: dict) -> List[Dict[str, Any]]:
        """搜索电影"""
        title = parsed_info.get("title")
        year = parsed_info.get("year")

        if not title:
            return []

        logger.info(f"搜索电影: {title}, 年份: {year}")
        adapter = await self._get_tmdb_adapter(db)
        return await adapter.search_by_title(title, year)

    async def _search_tv(self, db: AsyncSession, parsed_info: dict) -> List[Dict[str, Any]]:
        """搜索电视剧"""
        title = parsed_info.get("title")
        year = parsed_info.get("year")

        if not title:
            return []

        logger.info(f"搜索电视剧: {title}, 年份: {year}")
        adapter = await self._get_tmdb_adapter(db)
        return await adapter.search_tv_by_title(title, year)

    def _find_best_match(
        self, parsed_info: dict, candidates: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        从候选列表中找到最佳匹配

        匹配规则：
        1. 标题完全匹配（忽略大小写）
        2. 年份匹配
        3. 评分和投票数考量
        """
        if not candidates:
            return None

        parsed_title = (parsed_info.get("title") or "").lower()
        parsed_year = parsed_info.get("year")

        best_candidate = None
        best_score = 0

        for candidate in candidates:
            score = 0

            # 标题匹配
            candidate_title = (candidate.get("title") or "").lower()
            original_title = (candidate.get("original_title") or "").lower()

            if parsed_title == candidate_title or parsed_title == original_title:
                score += 100  # 完全匹配
            elif parsed_title in candidate_title or parsed_title in original_title:
                score += 50  # 部分匹配

            # 年份匹配
            if parsed_year and candidate.get("year") == parsed_year:
                score += 50

            # 评分权重（高评分更可信）
            rating = candidate.get("rating_tmdb") or 0
            votes = candidate.get("votes_tmdb") or 0
            if votes > 100 and rating > 6:
                score += 10

            if score > best_score:
                best_score = score
                best_candidate = candidate

        # 只有分数足够高才自动匹配
        if best_score >= 100:  # 至少标题完全匹配
            return best_candidate

        return None

    async def link_to_unified_resource(
        self,
        db: AsyncSession,
        media_file: MediaFile,
        tmdb_data: Dict[str, Any],
        media_type: str,
    ) -> Optional[int]:
        """
        将媒体文件关联到统一资源

        如果统一资源不存在，则创建新的

        Args:
            db: 数据库会话
            media_file: 媒体文件
            tmdb_data: TMDB元数据
            media_type: 媒体类型 (movie/tv)

        Returns:
            统一资源ID
        """
        tmdb_id = tmdb_data.get("tmdb_id")
        if not tmdb_id:
            logger.error("TMDB数据缺少tmdb_id")
            return None

        if media_type == MEDIA_TYPE_MOVIE or media_type == "movie":
            return await self._link_to_movie(db, media_file, tmdb_data)
        elif media_type in (MEDIA_TYPE_TV, "tv", "episode"):
            return await self._link_to_tv_series(db, media_file, tmdb_data)
        else:
            logger.error(f"不支持的媒体类型: {media_type}")
            return None

    async def _link_to_movie(
        self, db: AsyncSession, media_file: MediaFile, tmdb_data: dict
    ) -> Optional[int]:
        """关联到电影资源"""
        tmdb_id = tmdb_data.get("tmdb_id")

        # 查找是否已存在
        stmt = select(UnifiedMovie).where(UnifiedMovie.tmdb_id == tmdb_id)
        result = await db.execute(stmt)
        movie = result.scalar_one_or_none()

        if not movie:
            # 创建新的统一电影资源
            movie = UnifiedMovie(
                tmdb_id=tmdb_id,
                imdb_id=tmdb_data.get("imdb_id"),
                title=tmdb_data.get("title"),
                original_title=tmdb_data.get("original_title"),
                year=tmdb_data.get("year"),
                runtime=tmdb_data.get("runtime"),
                rating_tmdb=tmdb_data.get("rating_tmdb"),
                votes_tmdb=tmdb_data.get("votes_tmdb"),
                genres=tmdb_data.get("genres"),
                languages=tmdb_data.get("languages"),
                countries=tmdb_data.get("countries"),
                directors=tmdb_data.get("directors"),
                actors=tmdb_data.get("actors"),
                overview=tmdb_data.get("overview"),
                poster_url=tmdb_data.get("poster_url"),
                backdrop_url=tmdb_data.get("backdrop_url"),
                local_file_count=1,
                has_local=True,
            )
            db.add(movie)
            await db.flush()
            logger.info(f"创建新的统一电影资源: {movie.title} (TMDB: {tmdb_id})")
        else:
            # 更新本地文件计数
            movie.local_file_count = (movie.local_file_count or 0) + 1
            movie.has_local = True

        # 更新媒体文件关联
        media_file.unified_table_name = "unified_movies"
        media_file.unified_resource_id = movie.id
        media_file.media_type = MEDIA_TYPE_MOVIE
        media_file.status = "identified"
        media_file.match_method = "from_filename"

        await db.commit()
        logger.info(f"媒体文件已关联到电影: {media_file.file_name} -> {movie.title}")

        return movie.id

    async def _link_to_tv_series(
        self, db: AsyncSession, media_file: MediaFile, tmdb_data: dict
    ) -> Optional[int]:
        """关联到电视剧资源"""
        tmdb_id = tmdb_data.get("tmdb_id")

        # 查找是否已存在
        stmt = select(UnifiedTVSeries).where(UnifiedTVSeries.tmdb_id == tmdb_id)
        result = await db.execute(stmt)
        tv_series = result.scalar_one_or_none()

        if not tv_series:
            # 创建新的统一电视剧资源
            tv_series = UnifiedTVSeries(
                tmdb_id=tmdb_id,
                imdb_id=tmdb_data.get("imdb_id"),
                tvdb_id=tmdb_data.get("tvdb_id"),
                title=tmdb_data.get("title"),
                original_title=tmdb_data.get("original_title"),
                year=tmdb_data.get("year"),
                status=tmdb_data.get("status"),
                number_of_seasons=tmdb_data.get("number_of_seasons"),
                number_of_episodes=tmdb_data.get("number_of_episodes"),
                rating_tmdb=tmdb_data.get("rating_tmdb"),
                votes_tmdb=tmdb_data.get("votes_tmdb"),
                genres=tmdb_data.get("genres"),
                languages=tmdb_data.get("languages"),
                countries=tmdb_data.get("countries"),
                creators=tmdb_data.get("creators"),
                actors=tmdb_data.get("actors"),
                overview=tmdb_data.get("overview"),
                poster_url=tmdb_data.get("poster_url"),
                backdrop_url=tmdb_data.get("backdrop_url"),
                local_file_count=1,
                has_local=True,
            )
            db.add(tv_series)
            await db.flush()
            logger.info(f"创建新的统一电视剧资源: {tv_series.title} (TMDB: {tmdb_id})")
        else:
            # 更新本地文件计数
            tv_series.local_file_count = (tv_series.local_file_count or 0) + 1
            tv_series.has_local = True

        # 更新媒体文件关联
        media_file.unified_table_name = "unified_tv_series"
        media_file.unified_resource_id = tv_series.id
        media_file.media_type = MEDIA_TYPE_TV
        media_file.status = "identified"
        media_file.match_method = "from_filename"

        # 如果有季集信息，更新（从 match_detail 中读取）
        parsed = media_file.match_detail or {}
        if isinstance(parsed, dict):
            if parsed.get("season"):
                media_file.season_number = parsed["season"]
            if parsed.get("episode"):
                media_file.episode_number = parsed["episode"]

        await db.commit()
        logger.info(f"媒体文件已关联到电视剧: {media_file.file_name} -> {tv_series.title}")

        return tv_series.id

    async def search_and_get_candidates(
        self, db: AsyncSession, title: str, year: Optional[int] = None, media_type: str = "movie"
    ) -> List[Dict[str, Any]]:
        """
        手动搜索TMDB获取候选列表

        Args:
            db: 数据库会话
            title: 标题
            year: 年份（可选）
            media_type: 媒体类型

        Returns:
            候选列表
        """
        adapter = await self._get_tmdb_adapter(db)

        if media_type == "movie":
            return await adapter.search_by_title(title, year)
        elif media_type in ("tv", "episode"):
            return await adapter.search_tv_by_title(title, year)
        else:
            # 尝试两种
            results = await adapter.search_by_title(title, year)
            if not results:
                results = await adapter.search_tv_by_title(title, year)
            return results

    async def _identify_adult(
        self, db: AsyncSession, media_file: MediaFile, parsed_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        识别成人资源

        与资源页面(/resources)保持一致的识别逻辑：
        1. 尝试从文件名提取番号，匹配已有UnifiedAdult记录
        2. 若未匹配到，尝试通过下载任务关联的PT资源获取MTeam适配器
        3. 通过DMM API或简化模式自动创建UnifiedAdult记录

        Args:
            db: 数据库会话
            media_file: 媒体文件对象
            parsed_info: 文件名解析信息

        Returns:
            识别结果
        """
        result = {
            "success": False,
            "candidates": [],
            "auto_matched": False,
            "matched_id": None,
            "match_source": None,
            "parsed_info": parsed_info,
            "error": None,
        }

        try:
            # 尝试从文件名提取番号
            product_number = AdultIdentifyService.extract_product_number(
                parsed_info.get("title", ""),
                media_file.file_name or ""
            )

            if product_number:
                # 检查是否已存在统一成人资源
                # 1. 精确匹配
                stmt = select(UnifiedAdult).where(UnifiedAdult.product_number == product_number)
                existing = await db.execute(stmt)
                unified_adult = existing.scalar_one_or_none()
                
                # 2. 如果精确匹配失败，尝试查找简化版记录（带后缀的）
                # 格式：{product_number}_SIM_{random}
                if not unified_adult:
                    stmt = select(UnifiedAdult).where(UnifiedAdult.product_number.like(f"{product_number}_SIM_%"))
                    existing = await db.execute(stmt)
                    # 可能有多个，取第一个即可
                    unified_adult = existing.scalars().first()

                if unified_adult:
                    # 已存在，自动关联
                    await self._link_adult_media_file(db, media_file, unified_adult)
                    result["success"] = True
                    result["auto_matched"] = True
                    result["matched_id"] = unified_adult.id
                    result["match_source"] = "adult_product_number"
                    result["candidates"] = [{
                        "id": unified_adult.id,
                        "product_number": unified_adult.product_number,
                        "title": unified_adult.title,
                        "poster_url": unified_adult.poster_url,
                        "year": unified_adult.year,
                    }]
                    logger.info(f"成人资源识别成功(已有记录): {media_file.file_name} -> {unified_adult.product_number}")
                    return result

            # 未找到现有记录，使用与资源页面一致的逻辑自动创建
            unified_adult = await self._create_adult_from_media_file(db, media_file, parsed_info, product_number)

            if unified_adult:
                await self._link_adult_media_file(db, media_file, unified_adult)
                match_source = "dmm" if unified_adult.metadata_source == "dmm" else "simplified"
                result["success"] = True
                result["auto_matched"] = True
                result["matched_id"] = unified_adult.id
                result["match_source"] = match_source
                result["candidates"] = [{
                    "id": unified_adult.id,
                    "product_number": unified_adult.product_number,
                    "title": unified_adult.title,
                    "poster_url": unified_adult.poster_url,
                    "year": unified_adult.year,
                }]
                if product_number:
                    result["parsed_info"]["product_number"] = product_number
                logger.info(f"成人资源识别成功({match_source}): {media_file.file_name} -> ID {unified_adult.id}")
            else:
                result["success"] = True
                result["candidates"] = []
                if product_number:
                    result["parsed_info"]["product_number"] = product_number
                logger.warning(f"成人资源识别失败，无法创建记录: {media_file.file_name}")

            return result

        except Exception as e:
            logger.error(f"成人资源识别失败: {e}")
            result["error"] = f"成人资源识别失败: {str(e)}"
            return result

    async def _create_adult_from_media_file(
        self,
        db: AsyncSession,
        media_file: MediaFile,
        parsed_info: Dict[str, Any],
        product_number: Optional[str],
    ) -> Optional[UnifiedAdult]:
        """
        为媒体文件创建UnifiedAdult记录（与资源页面逻辑一致）

        策略：
        1. 通过下载任务关联的PT资源获取MTeam适配器和资源信息
        2. 如果有PT资源，走AdultIdentifyService标准流程（DMM→简化）
        3. 如果没有PT资源，直接创建简化记录

        Args:
            db: 数据库会话
            media_file: 媒体文件对象
            parsed_info: 文件名解析信息
            product_number: 提取的番号

        Returns:
            UnifiedAdult对象，失败返回None
        """
        from app.adapters.pt_sites.mteam import MTeamAdapter
        from app.models.pt_site import PTSite
        from app.models.pt_resource import PTResource
        from app.models.download_task import DownloadTask
        from app.services.pt.pt_resource_service import PTResourceService

        pt_resource = None
        mteam_adapter = None

        # 尝试通过下载任务获取PT资源和适配器
        if media_file.download_task_id:
            try:
                download_task = await db.get(DownloadTask, media_file.download_task_id)
                if download_task and download_task.pt_resource_id:
                    pt_resource = await db.get(PTResource, download_task.pt_resource_id)

                    if pt_resource and pt_resource.site_id:
                        site = await db.get(PTSite, pt_resource.site_id)
                        if site:
                            try:
                                adapter = await PTResourceService._get_site_adapter(site, db)
                                if isinstance(adapter, MTeamAdapter):
                                    mteam_adapter = adapter
                            except Exception as e:
                                logger.warning(f"获取MTeam适配器失败，将使用简化模式: {e}")
            except Exception as e:
                logger.warning(f"获取下载任务关联信息失败: {e}")

        # 如果有PT资源，使用AdultIdentifyService标准流程（与资源页面一致）
        if pt_resource and pt_resource.category == MEDIA_TYPE_ADULT:
            # 先尝试raw_page_json中的dmmCode（与资源页面逻辑一致）
            dmm_code = None
            if pt_resource.raw_page_json and isinstance(pt_resource.raw_page_json, dict):
                dmm_code = pt_resource.raw_page_json.get("dmmCode")

            if dmm_code and mteam_adapter:
                try:
                    dmm_info = await mteam_adapter.fetch_dmm_info(dmm_code)
                    if dmm_info:
                        from app.utils.timezone import now
                        pn = dmm_info.get("product_number") or product_number or AdultIdentifyService.extract_product_number(
                            pt_resource.title, pt_resource.subtitle or ""
                        )
                        # 去重检查
                        if pn:
                            stmt = select(UnifiedAdult).where(UnifiedAdult.product_number == pn)
                            existing_result = await db.execute(stmt)
                            existing = existing_result.scalar_one_or_none()
                            if existing:
                                return existing

                        unified_adult = UnifiedAdult(
                            product_number=pn,
                            dmm_url=dmm_info.get("url"),
                            title=dmm_info.get("title") or pt_resource.title,
                            original_title=dmm_info.get("original_title"),
                            release_date=dmm_info.get("release_date"),
                            duration=dmm_info.get("duration"),
                            year=dmm_info.get("year"),
                            maker=dmm_info.get("maker"),
                            label=dmm_info.get("label"),
                            series=dmm_info.get("series"),
                            director=dmm_info.get("director"),
                            actresses=dmm_info.get("actresses"),
                            genres=dmm_info.get("genres"),
                            overview=dmm_info.get("overview"),
                            rating=dmm_info.get("rating"),
                            poster_url=dmm_info.get("poster_url"),
                            backdrop_url=dmm_info.get("backdrop_url"),
                            image_list=dmm_info.get("image_list"),
                            detail_loaded=True,
                            detail_loaded_at=now(),
                            metadata_source="dmm",
                            raw_dmm_data=dmm_info.get("raw_data"),
                        )
                        db.add(unified_adult)
                        await db.flush()
                        logger.info(f"创建统一成人资源(DMM via dmmCode): {pn} - {unified_adult.title}")
                        return unified_adult
                except Exception as e:
                    logger.warning(f"通过dmmCode进行DMM识别失败: {e}")

            # 降级到AdultIdentifyService标准流程（DMM→简化）
            unified_adult = await AdultIdentifyService.identify_adult_resource(
                db, pt_resource, mteam_adapter
            )
            return unified_adult

        # 没有PT资源关联，创建简化记录
        return await self.link_adult_file_simplified(db, media_file)

    @staticmethod
    async def _link_adult_media_file(
        db: AsyncSession, media_file: MediaFile, unified_adult: UnifiedAdult
    ) -> None:
        """
        将媒体文件关联到统一成人资源

        Args:
            db: 数据库会话
            media_file: 媒体文件对象
            unified_adult: 统一成人资源对象
        """
        media_file.unified_table_name = UNIFIED_TABLE_ADULT
        media_file.unified_resource_id = unified_adult.id
        media_file.media_type = MEDIA_TYPE_ADULT
        media_file.status = "identified"
        media_file.match_method = "from_filename"
        await db.commit()

    async def link_adult_file_simplified(
        self, db: AsyncSession, media_file: MediaFile
    ) -> Optional[UnifiedAdult]:
        """
        使用简化模式关联成人资源文件

        当无法通过DMM获取元数据时，直接使用文件信息创建简化记录

        Args:
            db: 数据库会话
            media_file: 媒体文件对象

        Returns:
            统一成人资源对象
        """
        # 尝试提取番号
        product_number = AdultIdentifyService.extract_product_number(
            media_file.file_name or "",
            ""
        )

        import uuid
        if product_number:
            # 如果有提取出的番号，附加随机后缀以保证唯一性，同时保留一部分可读性
            final_product_number = f"{product_number}_SIM_{uuid.uuid4().hex[:6]}"
        else:
            final_product_number = f"SIM_{uuid.uuid4().hex[:8]}"
            
        # 创建简化模式的统一成人资源
        unified_adult = UnifiedAdult(
            product_number=final_product_number,
            title=media_file.file_name or "Unknown",
            detail_loaded=False,
            metadata_source="simplified",
        )
        db.add(unified_adult)
        await db.flush()

        logger.info(f"创建简化模式统一成人资源(无PT资源): {media_file.file_name} -> ID {unified_adult.id}")
        
        # 关联媒体文件
        await self._link_adult_media_file(db, media_file, unified_adult)
        
        return unified_adult


# 全局单例（每次请求会重新初始化adapter配置）
media_identify_service = MediaIdentifyService()
