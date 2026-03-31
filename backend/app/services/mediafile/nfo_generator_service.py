# -*- coding: utf-8 -*-
"""
NFO生成服务
生成Jellyfin/Emby/Plex/Kodi兼容的NFO文件
"""
import logging
from pathlib import Path
from typing import Optional
from xml.dom import minidom
from xml.etree import ElementTree as ET

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import (
    NFO_FORMAT_JELLYFIN,
    NFO_FORMAT_EMBY,
    NFO_FORMAT_KODI,
    NFO_FORMAT_PLEX,
    UNIFIED_TABLE_MOVIES,
    UNIFIED_TABLE_TV,
    UNIFIED_TABLE_ADULT,
)
from app.models.media_file import MediaFile
from app.models.organize_config import OrganizeConfig
from app.models.subscription import Subscription
from app.models.unified_movie import UnifiedMovie
from app.models.unified_tv_series import UnifiedTVSeries
from app.models.unified_adult import UnifiedAdult
from app.utils.file_operations import ensure_dir

logger = logging.getLogger(__name__)


class NFOGeneratorService:
    """NFO生成服务"""

    @staticmethod
    async def generate_nfo(
        db: AsyncSession,
        media_file: MediaFile,
        config: OrganizeConfig,
        force: bool = False,
    ) -> Optional[str]:
        """
        生成NFO文件

        Args:
            db: 数据库会话
            media_file: 媒体文件对象
            config: 整理配置
            force: 强制覆盖已存在的NFO文件

        Returns:
            生成的NFO文件路径，失败返回None
        """
        if not config.generate_nfo:
            logger.debug("配置中未启用NFO生成")
            return None

        if not media_file.organized_path:
            logger.error("媒体文件未整理，无法生成NFO")
            return None

        try:
            # 根据统一资源表名生成不同的NFO（这样 anime、adult 等类型可以复用 movie/tv 的NFO生成逻辑）
            if media_file.unified_table_name == UNIFIED_TABLE_MOVIES:
                return await NFOGeneratorService._generate_movie_nfo(
                    db, media_file, config, force=force
                )
            elif media_file.unified_table_name == UNIFIED_TABLE_TV:
                return await NFOGeneratorService._generate_tv_episode_nfo(
                    db, media_file, config, force=force
                )
            elif media_file.unified_table_name == UNIFIED_TABLE_ADULT:
                return await NFOGeneratorService._generate_adult_nfo(
                    db, media_file, config, force=force
                )
            else:
                logger.warning(f"不支持的统一资源表: {media_file.unified_table_name}，当前仅支持 {UNIFIED_TABLE_MOVIES}、{UNIFIED_TABLE_TV} 和 {UNIFIED_TABLE_ADULT}")
                return None

        except Exception as e:
            logger.exception(f"生成NFO失败: {media_file.id}")
            return None

    @staticmethod
    async def _generate_movie_nfo(
        db: AsyncSession,
        media_file: MediaFile,
        config: OrganizeConfig,
        force: bool = False,
    ) -> Optional[str]:
        """
        生成电影NFO文件

        Args:
            db: 数据库会话
            media_file: 媒体文件对象
            config: 整理配置

        Returns:
            NFO文件路径
        """
        # 获取电影元数据
        movie = await db.get(UnifiedMovie, media_file.unified_resource_id)
        if not movie:
            logger.error(f"未找到电影资源: {media_file.unified_resource_id}")
            return None

        # 构建NFO文件路径
        organized_path = Path(media_file.organized_path)
        nfo_path = organized_path.with_suffix(".nfo")

        # 检查是否跳过已存在的NFO
        if nfo_path.exists() and not (force or config.overwrite_nfo):
            logger.debug(f"NFO文件已存在，跳过: {nfo_path}")
            media_file.has_nfo = True
            media_file.nfo_path = str(nfo_path)
            await db.commit()
            return str(nfo_path)

        # 生成NFO XML内容
        xml_content = NFOGeneratorService._build_movie_xml(movie, config.nfo_format)

        # 写入文件
        try:
            with open(nfo_path, "w", encoding="utf-8") as f:
                f.write(xml_content)

            logger.info(f"生成电影NFO成功: {nfo_path}")

            # 更新MediaFile
            media_file.has_nfo = True
            media_file.nfo_path = str(nfo_path)
            await db.commit()

            return str(nfo_path)

        except Exception as e:
            logger.error(f"写入NFO文件失败: {nfo_path}, 错误: {e}")
            return None

    @staticmethod
    def _build_movie_xml(movie: UnifiedMovie, nfo_format: str) -> str:
        """
        构建电影NFO XML内容

        Args:
            movie: 电影对象
            nfo_format: NFO格式

        Returns:
            格式化的XML字符串
        """
        # Jellyfin/Emby使用相同的格式
        root = ET.Element("movie")

        # ============ uniqueid 标签（Jellyfin/Emby推荐格式）============
        if movie.tmdb_id:
            uniqueid_tmdb = ET.SubElement(root, "uniqueid", type="tmdb", default="true")
            uniqueid_tmdb.text = str(movie.tmdb_id)
        if movie.imdb_id:
            uniqueid_imdb = ET.SubElement(root, "uniqueid", type="imdb", default="false")
            uniqueid_imdb.text = movie.imdb_id
        if movie.douban_id:
            uniqueid_douban = ET.SubElement(root, "uniqueid", type="douban", default="false")
            uniqueid_douban.text = movie.douban_id

        # 基本信息
        if movie.title:
            ET.SubElement(root, "title").text = movie.title
        if movie.original_title:
            ET.SubElement(root, "originaltitle").text = movie.original_title
        if movie.year:
            ET.SubElement(root, "year").text = str(movie.year)
        if movie.release_date:
            ET.SubElement(root, "premiered").text = str(movie.release_date)
        if movie.runtime:
            ET.SubElement(root, "runtime").text = str(movie.runtime)

        # 评分 (使用标准的 ratings 结构)
        has_rating = movie.rating_tmdb or movie.rating_imdb or movie.rating_douban
        if has_rating:
            ratings = ET.SubElement(root, "ratings")

            # TMDB评分（默认）
            if movie.rating_tmdb:
                rating_tmdb = ET.SubElement(ratings, "rating", name="tmdb", max="10", default="true")
                ET.SubElement(rating_tmdb, "value").text = str(movie.rating_tmdb)
                if movie.votes_tmdb:
                    ET.SubElement(rating_tmdb, "votes").text = str(movie.votes_tmdb)

            # IMDB评分
            if movie.rating_imdb:
                rating_imdb = ET.SubElement(ratings, "rating", name="imdb", max="10", default="false")
                ET.SubElement(rating_imdb, "value").text = str(movie.rating_imdb)
                if movie.votes_imdb:
                    ET.SubElement(rating_imdb, "votes").text = str(movie.votes_imdb)

            # 豆瓣评分
            if movie.rating_douban:
                rating_douban = ET.SubElement(ratings, "rating", name="douban", max="10", default="false")
                ET.SubElement(rating_douban, "value").text = str(movie.rating_douban)
                if movie.votes_douban:
                    ET.SubElement(rating_douban, "votes").text = str(movie.votes_douban)

        # 兼容旧格式：添加简单的 rating 标签
        if movie.rating_tmdb:
            ET.SubElement(root, "rating").text = str(movie.rating_tmdb)

        # 简介
        if movie.overview:
            ET.SubElement(root, "plot").text = movie.overview
        if movie.tagline:
            ET.SubElement(root, "tagline").text = movie.tagline

        # ID标识
        if movie.tmdb_id:
            ET.SubElement(root, "tmdbid").text = str(movie.tmdb_id)
        if movie.imdb_id:
            ET.SubElement(root, "imdbid").text = movie.imdb_id
        if movie.douban_id:
            ET.SubElement(root, "doubanid").text = movie.douban_id

        # 类型
        if movie.genres:
            for genre in movie.genres:
                ET.SubElement(root, "genre").text = genre

        # 演员
        if movie.actors:
            for actor in movie.actors:
                actor_elem = ET.SubElement(root, "actor")
                ET.SubElement(actor_elem, "name").text = actor.get("name", "")
                # 兼容两种字段名: character (TMDB) 和 role (通用)
                character = actor.get("character") or actor.get("role")
                if character:
                    ET.SubElement(actor_elem, "role").text = character
                # 兼容两种字段名: thumb_url (TMDB) 和 thumb (通用)
                thumb = actor.get("thumb_url") or actor.get("thumb")
                if thumb:
                    ET.SubElement(actor_elem, "thumb").text = thumb
                # 添加TMDB ID
                if actor.get("tmdb_id"):
                    ET.SubElement(actor_elem, "tmdbid").text = str(actor["tmdb_id"])

        # 导演
        if movie.directors:
            for director in movie.directors:
                if isinstance(director, dict):
                    director_elem = ET.SubElement(root, "director")
                    director_elem.text = director.get("name", "")
                    # 添加TMDB ID
                    if director.get("tmdb_id"):
                        director_elem.set("tmdbid", str(director["tmdb_id"]))
                else:
                    ET.SubElement(root, "director").text = str(director)

        # 编剧
        if movie.writers:
            for writer in movie.writers:
                if isinstance(writer, dict):
                    credits_elem = ET.SubElement(root, "credits")
                    credits_elem.text = writer.get("name", "")
                    # 添加TMDB ID
                    if writer.get("tmdb_id"):
                        credits_elem.set("tmdbid", str(writer["tmdb_id"]))
                else:
                    ET.SubElement(root, "credits").text = str(writer)

        # 国家/语言
        if movie.countries:
            for country in movie.countries:
                ET.SubElement(root, "country").text = country
        if movie.languages:
            for language in movie.languages:
                ET.SubElement(root, "language").text = language

        # 图片
        if movie.poster_url:
            ET.SubElement(root, "thumb").text = movie.poster_url
        if movie.backdrop_url:
            ET.SubElement(root, "fanart").text = movie.backdrop_url

        # 格式化XML
        xml_str = ET.tostring(root, encoding="unicode")
        dom = minidom.parseString(xml_str)
        return dom.toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")

    @staticmethod
    async def _find_subscription_for_media_file(
        db: AsyncSession,
        media_file: MediaFile,
    ) -> Optional[Subscription]:
        """
        查找与媒体文件关联的订阅（用于获取覆写信息）

        Args:
            db: 数据库会话
            media_file: 媒体文件对象

        Returns:
            关联的订阅对象，如果没有则返回None
        """
        if not media_file.unified_resource_id:
            return None

        # 根据统一资源表名查找订阅
        from app.constants import SUBSCRIPTION_STATUS_ACTIVE, SUBSCRIPTION_STATUS_COMPLETED

        if media_file.unified_table_name == UNIFIED_TABLE_TV:
            # 查找TV订阅：主资源ID匹配 或 在关联资源列表中
            # 优先查找有覆写信息的订阅
            query = (
                select(Subscription)
                .where(
                    Subscription.media_type == "tv",
                    Subscription.status.in_([SUBSCRIPTION_STATUS_ACTIVE, SUBSCRIPTION_STATUS_COMPLETED]),
                )
                .order_by(
                    # 优先返回有覆写标题的订阅
                    Subscription.override_title.is_(None).asc(),
                    Subscription.updated_at.desc(),
                )
            )
            result = await db.execute(query)
            subscriptions = result.scalars().all()

            # 检查哪个订阅匹配该资源
            for sub in subscriptions:
                matched_tv_ids = sub.all_matched_tv_ids
                if media_file.unified_resource_id in matched_tv_ids:
                    return sub

        elif media_file.unified_table_name == UNIFIED_TABLE_MOVIES:
            # 查找电影订阅
            query = (
                select(Subscription)
                .where(
                    Subscription.media_type == "movie",
                    Subscription.unified_movie_id == media_file.unified_resource_id,
                    Subscription.status.in_([SUBSCRIPTION_STATUS_ACTIVE, SUBSCRIPTION_STATUS_COMPLETED]),
                )
                .order_by(Subscription.updated_at.desc())
                .limit(1)
            )
            result = await db.execute(query)
            return result.scalar_one_or_none()

        return None

    @staticmethod
    async def _generate_tv_episode_nfo(
        db: AsyncSession,
        media_file: MediaFile,
        config: OrganizeConfig,
        force: bool = False,
    ) -> Optional[str]:
        """
        生成电视剧剧集NFO文件

        Args:
            db: 数据库会话
            media_file: 媒体文件对象
            config: 整理配置

        Returns:
            NFO文件路径
        """
        # 获取电视剧元数据
        tv_series = await db.get(UnifiedTVSeries, media_file.unified_resource_id)
        if not tv_series:
            logger.error(f"未找到电视剧资源: {media_file.unified_resource_id}")
            return None

        # 查找关联的订阅（获取覆写信息）
        subscription = await NFOGeneratorService._find_subscription_for_media_file(db, media_file)
        override_info = None
        if subscription and (subscription.override_title or subscription.override_year):
            override_info = {
                "title": subscription.override_title,
                "year": subscription.override_year,
            }
            logger.debug(f"使用订阅覆写信息: {override_info}")

        # 构建NFO文件路径
        organized_path = Path(media_file.organized_path)
        nfo_path = organized_path.with_suffix(".nfo")

        # 检查是否跳过已存在的NFO
        if nfo_path.exists() and not (force or config.overwrite_nfo):
            logger.debug(f"NFO文件已存在，跳过: {nfo_path}")
            media_file.has_nfo = True
            media_file.nfo_path = str(nfo_path)
            await db.commit()
            return str(nfo_path)

        # 尝试从TMDB获取单集详情（带降级逻辑）
        episode_info = None
        if media_file.season_number and media_file.episode_number:
            episode_info = await NFOGeneratorService._fetch_episode_info_with_fallback(
                db,
                tv_series,
                media_file.season_number,
                media_file.episode_number,
            )

        # 生成NFO XML内容
        xml_content = NFOGeneratorService._build_tv_episode_xml(
            tv_series, media_file, config.nfo_format, episode_info, override_info
        )

        # 写入文件
        try:
            with open(nfo_path, "w", encoding="utf-8") as f:
                f.write(xml_content)

            logger.info(f"生成剧集NFO成功: {nfo_path}")

            # 更新MediaFile
            media_file.has_nfo = True
            media_file.nfo_path = str(nfo_path)
            await db.commit()

            return str(nfo_path)

        except Exception as e:
            logger.error(f"写入NFO文件失败: {nfo_path}, 错误: {e}")
            return None

    @staticmethod
    async def _fetch_episode_info_with_fallback(
        db: AsyncSession,
        tv_series: UnifiedTVSeries,
        season_number: int,
        episode_number: int,
    ) -> Optional[dict]:
        """
        获取单集详情（带降级逻辑）

        降级逻辑：
        1. 如果没有TMDB ID，尝试自动补全（豆瓣→IMDB→TMDB或标题搜索）
        2. 如果有TMDB ID，使用TMDB获取单集信息
        3. 如果TMDB失败且有TVDB ID，尝试使用TVDB

        Args:
            db: 数据库会话
            tv_series: 电视剧对象
            season_number: 季数
            episode_number: 集数

        Returns:
            单集详情dict，失败返回None
        """
        # 1. 如果没有TMDB ID，尝试自动补全
        if not tv_series.tmdb_id:
            logger.info(f"电视剧 {tv_series.title} 没有TMDB ID，尝试自动补全...")
            from app.services.mediafile.tmdb_id_resolver_service import TMDBIdResolverService
            tmdb_id, updated = await TMDBIdResolverService.resolve_tmdb_id_for_tv(db, tv_series)
            if tmdb_id:
                logger.info(f"成功补全TMDB ID: {tmdb_id}")

        # 2. 使用TMDB获取单集信息
        if tv_series.tmdb_id:
            episode_info = await NFOGeneratorService._fetch_episode_info_from_tmdb(
                db, tv_series.tmdb_id, season_number, episode_number
            )
            if episode_info:
                return episode_info

        # 3. 如果TMDB失败，尝试使用TVDB
        if not tv_series.tvdb_id:
            logger.info(f"尝试补全TVDB ID: {tv_series.title}")
            from app.services.mediafile.tmdb_id_resolver_service import TMDBIdResolverService
            tvdb_id, updated = await TMDBIdResolverService.resolve_tvdb_id_for_tv(db, tv_series)

        if tv_series.tvdb_id:
            episode_info = await NFOGeneratorService._fetch_episode_info_from_tvdb(
                db, tv_series.tvdb_id, season_number, episode_number
            )
            if episode_info:
                return episode_info

        logger.warning(f"无法获取单集详情: {tv_series.title} S{season_number:02d}E{episode_number:02d}")
        return None

    @staticmethod
    async def _fetch_episode_info_from_tmdb(
        db: AsyncSession,
        tmdb_id: int,
        season_number: int,
        episode_number: int,
    ) -> Optional[dict]:
        """
        从TMDB获取单集详情

        Args:
            db: 数据库会话
            tmdb_id: TMDB电视剧ID
            season_number: 季数
            episode_number: 集数

        Returns:
            单集详情dict，失败返回None
        """
        try:
            from app.services.identification.resource_identify_service import ResourceIdentificationService

            # 使用统一的方法获取TMDB适配器
            adapter = await ResourceIdentificationService._get_tmdb_adapter(db)

            # 获取季详情
            season_info = await adapter.get_tv_season_detail(tmdb_id, season_number)
            if not season_info:
                logger.debug(f"TMDB: 无法获取季详情: tmdb_id={tmdb_id}, season={season_number}")
                return None

            # 从季信息中提取集详情
            episodes = season_info.get("episodes", [])
            for ep in episodes:
                if ep.get("episode_number") == episode_number:
                    logger.debug(f"TMDB: 成功获取集详情: S{season_number:02d}E{episode_number:02d} - {ep.get('name')}")
                    return ep

            logger.debug(f"TMDB: 未找到集详情: S{season_number:02d}E{episode_number:02d}")
            return None

        except ValueError as e:
            # TMDB未配置
            logger.debug(f"TMDB未配置: {str(e)}")
            return None
        except Exception as e:
            logger.warning(f"TMDB获取集详情失败: {str(e)}")
            return None

    @staticmethod
    async def _fetch_episode_info_from_tvdb(
        db: AsyncSession,
        tvdb_id: int,
        season_number: int,
        episode_number: int,
    ) -> Optional[dict]:
        """
        从TVDB获取单集详情

        Args:
            db: 数据库会话
            tvdb_id: TVDB电视剧ID
            season_number: 季数
            episode_number: 集数

        Returns:
            单集详情dict，失败返回None
        """
        try:
            from app.services.identification.resource_identify_service import ResourceIdentificationService

            # 获取TVDB适配器
            adapter = await ResourceIdentificationService._get_tvdb_adapter(db)
            if not adapter:
                logger.debug("TVDB未配置")
                return None

            # 获取季详情
            season_info = await adapter.get_tv_season_detail(tvdb_id, season_number)
            if not season_info:
                logger.debug(f"TVDB: 无法获取季详情: tvdb_id={tvdb_id}, season={season_number}")
                return None

            # 从季信息中提取集详情
            episodes = season_info.get("episodes", [])
            for ep in episodes:
                if ep.get("episode_number") == episode_number:
                    logger.debug(f"TVDB: 成功获取集详情: S{season_number:02d}E{episode_number:02d} - {ep.get('name')}")
                    return ep

            logger.debug(f"TVDB: 未找到集详情: S{season_number:02d}E{episode_number:02d}")
            return None

        except Exception as e:
            logger.warning(f"TVDB获取集详情失败: {str(e)}")
            return None

    @staticmethod
    def _build_tv_episode_xml(
        tv_series: UnifiedTVSeries,
        media_file: MediaFile,
        nfo_format: str,
        episode_info: Optional[dict] = None,
        override_info: Optional[dict] = None,
    ) -> str:
        """
        构建电视剧剧集NFO XML内容

        Args:
            tv_series: 电视剧对象
            media_file: 媒体文件对象
            nfo_format: NFO格式
            episode_info: TMDB单集详情（可选）
            override_info: 覆写信息（来自订阅），包含 title 和 year

        Returns:
            格式化的XML字符串
        """
        root = ET.Element("episodedetails")

        # ============ uniqueid 标签 ============
        if episode_info and episode_info.get("id"):
            uniqueid = ET.SubElement(root, "uniqueid", type="tmdb", default="true")
            uniqueid.text = str(episode_info["id"])

        # ============ 基本信息 ============
        # 剧集标题（showtitle）：优先使用覆写标题
        show_title = None
        if override_info and override_info.get("title"):
            show_title = override_info["title"]
        elif tv_series.title:
            show_title = tv_series.title
        if show_title:
            ET.SubElement(root, "showtitle").text = show_title

        # 单集标题（优先从TMDB获取）
        episode_title = None
        if episode_info and episode_info.get("name"):
            episode_title = episode_info["name"]
        else:
            # TMDB 没有集名称时，生成标准格式标题
            # 不使用 media_file.episode_title（通常是从文件名解析的格式化字符串，如 "剑来 - S02E11"）
            ep_num = media_file.episode_number if media_file.episode_number is not None else 0
            episode_title = f"第 {ep_num} 集"
        ET.SubElement(root, "title").text = episode_title

        # 季数和集数（使用 is not None 检查，避免 season=0 被跳过）
        if media_file.season_number is not None:
            ET.SubElement(root, "season").text = str(media_file.season_number)
        if media_file.episode_number is not None:
            ET.SubElement(root, "episode").text = str(media_file.episode_number)

        # ============ 时长 ============
        # 优先使用单集时长，降级使用剧集平均时长
        runtime = None
        if episode_info and episode_info.get("runtime"):
            runtime = episode_info["runtime"]
        elif tv_series.episode_runtime:
            # episode_runtime 是JSON数组，取第一个值
            if isinstance(tv_series.episode_runtime, list) and tv_series.episode_runtime:
                runtime = tv_series.episode_runtime[0]
        if runtime:
            ET.SubElement(root, "runtime").text = str(runtime)

        # ============ 简介 ============
        plot_text = ""
        if episode_info and episode_info.get("overview"):
            plot_text = episode_info["overview"]
        elif tv_series.overview:
            plot_text = tv_series.overview
        if plot_text:
            ET.SubElement(root, "plot").text = plot_text
            ET.SubElement(root, "outline").text = plot_text

        # ============ 播出日期和年份 ============
        air_date = episode_info.get("air_date") if episode_info else None
        if air_date:
            ET.SubElement(root, "aired").text = air_date

        # 年份：优先使用覆写年份
        year_value = None
        if override_info and override_info.get("year"):
            year_value = str(override_info["year"])
        elif air_date and len(air_date) >= 4:
            year_value = air_date[:4]
        elif tv_series.year:
            year_value = str(tv_series.year)

        if year_value:
            ET.SubElement(root, "year").text = year_value

        # 如果没有单集播出日期但有剧集首播日期，也添加aired
        if not air_date and tv_series.first_air_date:
            ET.SubElement(root, "aired").text = str(tv_series.first_air_date)

        # ============ 评分（使用标准ratings结构）============
        # 优先使用单集评分，降级使用剧集评分
        episode_rating = None
        episode_votes = None
        if episode_info and episode_info.get("vote_average"):
            episode_rating = episode_info["vote_average"]
            episode_votes = episode_info.get("vote_count")
        elif tv_series.rating_tmdb:
            episode_rating = tv_series.rating_tmdb
            episode_votes = tv_series.votes_tmdb

        if episode_rating:
            # 标准ratings结构
            ratings = ET.SubElement(root, "ratings")
            rating_elem = ET.SubElement(ratings, "rating", name="tmdb", max="10", default="true")
            ET.SubElement(rating_elem, "value").text = str(episode_rating)
            if episode_votes:
                ET.SubElement(rating_elem, "votes").text = str(episode_votes)

            # 兼容旧格式
            ET.SubElement(root, "rating").text = str(episode_rating)

        # ============ ID标识 ============
        if tv_series.tmdb_id:
            ET.SubElement(root, "tmdbid").text = str(tv_series.tmdb_id)
        if tv_series.imdb_id:
            ET.SubElement(root, "imdbid").text = tv_series.imdb_id
        if tv_series.tvdb_id:
            ET.SubElement(root, "tvdbid").text = str(tv_series.tvdb_id)

        # ============ 导演（从单集crew中提取）============
        if episode_info:
            crew = episode_info.get("crew", [])
            for person in crew:
                if person.get("job") == "Director" or person.get("known_for_department") == "Directing":
                    director_elem = ET.SubElement(root, "director")
                    director_elem.text = person.get("name", "")
                    if person.get("id"):
                        director_elem.set("tmdbid", str(person["id"]))

        # ============ 编剧（从单集crew或剧集writers中获取）============
        writers_added = False
        if episode_info:
            crew = episode_info.get("crew", [])
            for person in crew:
                if person.get("job") in ("Writer", "Screenplay", "Story"):
                    credits_elem = ET.SubElement(root, "credits")
                    credits_elem.text = person.get("name", "")
                    if person.get("id"):
                        credits_elem.set("tmdbid", str(person["id"]))
                    writers_added = True

        # 如果单集没有编剧信息，使用剧集编剧
        if not writers_added and tv_series.writers:
            for writer in tv_series.writers[:5]:  # 限制数量
                if isinstance(writer, dict):
                    credits_elem = ET.SubElement(root, "credits")
                    credits_elem.text = writer.get("name", "")
                    if writer.get("tmdb_id"):
                        credits_elem.set("tmdbid", str(writer["tmdb_id"]))
                else:
                    ET.SubElement(root, "credits").text = str(writer)

        # ============ 制作公司（Studio）============
        if tv_series.production_companies:
            for company in tv_series.production_companies[:5]:  # 限制数量
                if isinstance(company, dict):
                    ET.SubElement(root, "studio").text = company.get("name", "")
                else:
                    ET.SubElement(root, "studio").text = str(company)

        # ============ 演员 ============
        # 优先使用单集客串演员
        if episode_info and episode_info.get("guest_stars"):
            for actor in episode_info["guest_stars"][:10]:  # 限制数量
                if actor.get("known_for_department") == "Acting" or actor.get("name"):
                    actor_elem = ET.SubElement(root, "actor")
                    ET.SubElement(actor_elem, "name").text = actor.get("name", "")
                    ET.SubElement(actor_elem, "type").text = "GuestStar"
                    if actor.get("character"):
                        ET.SubElement(actor_elem, "role").text = actor["character"]
                    if actor.get("id"):
                        ET.SubElement(actor_elem, "tmdbid").text = str(actor["id"])
                    if actor.get("profile_path"):
                        ET.SubElement(actor_elem, "thumb").text = f"https://image.tmdb.org/t/p/original{actor['profile_path']}"

        # 追加剧集主演员
        if tv_series.actors:
            for actor in tv_series.actors[:10]:  # 限制数量
                actor_elem = ET.SubElement(root, "actor")
                ET.SubElement(actor_elem, "name").text = actor.get("name", "")
                ET.SubElement(actor_elem, "type").text = "Actor"
                if actor.get("character") or actor.get("role"):
                    ET.SubElement(actor_elem, "role").text = actor.get("character") or actor.get("role", "")
                if actor.get("thumb_url") or actor.get("thumb"):
                    ET.SubElement(actor_elem, "thumb").text = actor.get("thumb_url") or actor.get("thumb", "")

        # ============ 剧照 ============
        if episode_info and episode_info.get("still_path"):
            ET.SubElement(root, "thumb").text = f"https://image.tmdb.org/t/p/original{episode_info['still_path']}"

        # 格式化XML
        xml_str = ET.tostring(root, encoding="unicode")
        dom = minidom.parseString(xml_str)
        return dom.toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")

    @staticmethod
    async def _generate_adult_nfo(
        db: AsyncSession,
        media_file: MediaFile,
        config: OrganizeConfig,
        force: bool = False,
    ) -> Optional[str]:
        """
        生成成人资源NFO文件

        Args:
            db: 数据库会话
            media_file: 媒体文件对象
            config: 整理配置

        Returns:
            NFO文件路径
        """
        # 获取成人资源元数据
        adult = await db.get(UnifiedAdult, media_file.unified_resource_id)
        if not adult:
            logger.error(f"未找到成人资源: {media_file.unified_resource_id}")
            return None

        # 构建NFO文件路径（放在视频同目录）
        organized_path = Path(media_file.organized_path)
        nfo_path = organized_path.with_suffix(".nfo")

        # 检查是否跳过已存在的NFO
        if nfo_path.exists() and not (force or config.overwrite_nfo):
            logger.debug(f"NFO文件已存在，跳过: {nfo_path}")
            media_file.has_nfo = True
            media_file.nfo_path = str(nfo_path)
            await db.commit()
            return str(nfo_path)

        # 生成NFO XML内容
        xml_content = NFOGeneratorService._build_adult_xml(adult, config.nfo_format)

        # 写入文件
        try:
            with open(nfo_path, "w", encoding="utf-8") as f:
                f.write(xml_content)

            logger.info(f"生成成人资源NFO成功: {nfo_path}")

            # 更新MediaFile
            media_file.has_nfo = True
            media_file.nfo_path = str(nfo_path)
            await db.commit()

            return str(nfo_path)

        except Exception as e:
            logger.error(f"写入NFO文件失败: {nfo_path}, 错误: {e}")
            return None

    @staticmethod
    def _build_adult_xml(
        adult: UnifiedAdult,
        nfo_format: str = NFO_FORMAT_JELLYFIN,
    ) -> str:
        """
        构建成人资源NFO XML内容

        使用类似电影的NFO格式，但包含成人资源特有的信息

        Args:
            adult: 成人资源对象
            nfo_format: NFO格式

        Returns:
            XML字符串
        """
        root = ET.Element("movie")

        # ============ 基础信息 ============
        ET.SubElement(root, "title").text = adult.title
        if adult.original_title:
            ET.SubElement(root, "originaltitle").text = adult.original_title

        # 番号作为排序标题
        if adult.product_number:
            ET.SubElement(root, "sorttitle").text = adult.product_number.upper()

        # ============ 简介 ============
        if adult.overview:
            ET.SubElement(root, "plot").text = adult.overview
            ET.SubElement(root, "outline").text = adult.overview[:500] if len(adult.overview) > 500 else adult.overview

        # ============ 年份和日期 ============
        if adult.year:
            ET.SubElement(root, "year").text = str(adult.year)
        if adult.release_date:
            ET.SubElement(root, "releasedate").text = str(adult.release_date)
            ET.SubElement(root, "premiered").text = str(adult.release_date)

        # ============ 时长 ============
        if adult.duration:
            ET.SubElement(root, "runtime").text = adult.duration

        # ============ 番号 ============
        if adult.product_number:
            ET.SubElement(root, "num").text = adult.product_number
            # 使用唯一标识
            uniqueid = ET.SubElement(root, "uniqueid", type="num", default="true")
            uniqueid.text = adult.product_number

        # ============ 制作信息 ============
        if adult.maker:
            ET.SubElement(root, "studio").text = adult.maker
        if adult.label:
            ET.SubElement(root, "label").text = adult.label
        if adult.series:
            ET.SubElement(root, "set").text = adult.series
        if adult.director:
            ET.SubElement(root, "director").text = adult.director

        # ============ 演员 ============
        if adult.actresses:
            for actress in adult.actresses:
                actor_elem = ET.SubElement(root, "actor")
                if isinstance(actress, dict):
                    ET.SubElement(actor_elem, "name").text = actress.get("name", "")
                    if actress.get("thumb"):
                        ET.SubElement(actor_elem, "thumb").text = actress["thumb"]
                else:
                    ET.SubElement(actor_elem, "name").text = str(actress)

        # ============ 类型/标签 ============
        if adult.genres:
            for genre in adult.genres:
                ET.SubElement(root, "genre").text = str(genre)

        if adult.tags:
            for tag in adult.tags:
                ET.SubElement(root, "tag").text = str(tag)

        # ============ 评分 ============
        if adult.rating:
            ratings = ET.SubElement(root, "ratings")
            rating_elem = ET.SubElement(ratings, "rating", name="dmm", max="10", default="true")
            ET.SubElement(rating_elem, "value").text = str(adult.rating)

        # ============ 图片 ============
        if adult.poster_url:
            ET.SubElement(root, "thumb", aspect="poster").text = adult.poster_url
        if adult.backdrop_url:
            fanart = ET.SubElement(root, "fanart")
            ET.SubElement(fanart, "thumb").text = adult.backdrop_url

        # ============ DMM链接 ============
        if adult.dmm_url:
            ET.SubElement(root, "website").text = adult.dmm_url

        # 格式化XML
        xml_str = ET.tostring(root, encoding="unicode")
        dom = minidom.parseString(xml_str)
        return dom.toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")

    @staticmethod
    async def download_image(
        url: str,
        save_path: Path,
        overwrite: bool = False,
    ) -> bool:
        """
        下载图片（海报/背景图）

        Args:
            url: 图片URL
            save_path: 保存路径
            overwrite: 是否覆盖已存在的文件

        Returns:
            是否成功
        """
        if save_path.exists() and not overwrite:
            logger.debug(f"图片已存在，跳过下载: {save_path}")
            return True

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=30.0)
                response.raise_for_status()

                # 确保目录存在
                ensure_dir(save_path.parent)

                # 写入文件
                with open(save_path, "wb") as f:
                    f.write(response.content)

                logger.info(f"下载图片成功: {save_path}")
                return True

        except Exception as e:
            logger.error(f"下载图片失败: {url}, 错误: {e}")
            return False
