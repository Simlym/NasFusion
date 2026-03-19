# -*- coding: utf-8 -*-
"""
刮削服务
下载海报、背景图等媒体资源，整合NFO生成
"""
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import UNIFIED_TABLE_MOVIES, UNIFIED_TABLE_TV, UNIFIED_TABLE_ADULT
from app.models.media_file import MediaFile
from app.models.organize_config import OrganizeConfig
from app.models.unified_movie import UnifiedMovie
from app.models.unified_tv_series import UnifiedTVSeries
from app.models.unified_adult import UnifiedAdult
from app.services.mediafile.nfo_generator_service import NFOGeneratorService
from app.utils.file_operations import ensure_dir

logger = logging.getLogger(__name__)


class ScraperService:
    """刮削服务"""

    @staticmethod
    async def scrape_media_file(
        db: AsyncSession,
        media_file: MediaFile,
        config: OrganizeConfig,
    ) -> Dict[str, Any]:
        """
        刮削媒体文件（下载海报、背景图、生成NFO）

        Args:
            db: 数据库会话
            media_file: 媒体文件对象
            config: 整理配置

        Returns:
            刮削结果
        """
        result = {
            "success": True,
            "nfo_generated": False,
            "poster_downloaded": False,
            "backdrop_downloaded": False,
            "nfo_path": None,
            "poster_path": None,
            "backdrop_path": None,
            "errors": [],
        }

        # 检查文件是否已整理
        if not media_file.organized_path:
            result["success"] = False
            result["errors"].append("媒体文件未整理，无法刮削")
            return result

        # 检查文件是否已识别
        if not media_file.unified_resource_id or not media_file.unified_table_name:
            result["success"] = False
            result["errors"].append("媒体文件未识别，无法刮削")
            return result

        try:
            # 获取目标目录（整理后的文件所在目录）
            organized_path = Path(media_file.organized_path)
            target_dir = organized_path.parent

            # 根据统一资源表名获取元数据
            if media_file.unified_table_name == UNIFIED_TABLE_MOVIES:
                metadata = await db.get(UnifiedMovie, media_file.unified_resource_id)
            elif media_file.unified_table_name == UNIFIED_TABLE_TV:
                metadata = await db.get(UnifiedTVSeries, media_file.unified_resource_id)
            elif media_file.unified_table_name == UNIFIED_TABLE_ADULT:
                metadata = await db.get(UnifiedAdult, media_file.unified_resource_id)
            else:
                result["success"] = False
                result["errors"].append(f"不支持的统一资源表: {media_file.unified_table_name}，当前仅支持 {UNIFIED_TABLE_MOVIES}、{UNIFIED_TABLE_TV} 和 {UNIFIED_TABLE_ADULT}")
                return result

            if not metadata:
                result["success"] = False
                result["errors"].append("未找到关联的元数据资源")
                return result

            # 1. 生成NFO文件
            if config.generate_nfo:
                try:
                    nfo_path = await NFOGeneratorService.generate_nfo(db, media_file, config)
                    if nfo_path:
                        result["nfo_generated"] = True
                        result["nfo_path"] = nfo_path
                        logger.info(f"NFO生成成功: {nfo_path}")
                except Exception as e:
                    logger.error(f"NFO生成失败: {e}")
                    result["errors"].append(f"NFO生成失败: {str(e)}")

            # 2. 下载图片（区分电影、电视剧和成人资源）
            if media_file.unified_table_name == UNIFIED_TABLE_TV:
                await ScraperService._process_tv_images(
                    db, media_file, metadata, target_dir, config, result
                )
            elif media_file.unified_table_name == UNIFIED_TABLE_ADULT:
                # 成人资源处理逻辑
                await ScraperService._process_adult_images(
                    db, media_file, metadata, target_dir, config, result
                )
            else:
                # 电影处理逻辑
                # 海报
                if config.download_poster and metadata.poster_url:
                    try:
                        poster_path = target_dir / f"{config.poster_filename}.jpg"
                        success = await ScraperService.download_image(
                            metadata.poster_url,
                            poster_path,
                            overwrite=config.overwrite_poster,
                        )
                        if success:
                            result["poster_downloaded"] = True
                            result["poster_path"] = str(poster_path)
                            media_file.has_poster = True
                            media_file.poster_path = str(poster_path)
                            logger.info(f"海报下载成功: {poster_path}")
                    except Exception as e:
                        logger.error(f"海报下载失败: {e}")
                        result["errors"].append(f"海报下载失败: {str(e)}")

                # 背景图
                if config.download_backdrop and metadata.backdrop_url:
                    try:
                        backdrop_path = target_dir / f"{config.backdrop_filename}.jpg"
                        success = await ScraperService.download_image(
                            metadata.backdrop_url,
                            backdrop_path,
                            overwrite=config.overwrite_backdrop,
                        )
                        if success:
                            result["backdrop_downloaded"] = True
                            result["backdrop_path"] = str(backdrop_path)
                            media_file.has_backdrop = True
                            media_file.backdrop_path = str(backdrop_path)
                            logger.info(f"背景图下载成功: {backdrop_path}")
                    except Exception as e:
                        logger.error(f"背景图下载失败: {e}")
                        result["errors"].append(f"背景图下载失败: {str(e)}")

            # 提交数据库更新
            await db.commit()

            # 检查是否有任何错误
            if result["errors"]:
                result["success"] = False

            return result

        except Exception as e:
            logger.exception(f"刮削媒体文件失败: {media_file.id}")
            result["success"] = False
            result["errors"].append(f"刮削失败: {str(e)}")
            return result

    @staticmethod
    async def download_image(
        url: str,
        save_path: Path,
        overwrite: bool = False,
        timeout: float = 60.0,
    ) -> bool:
        """
        下载图片（海报/背景图）

        Args:
            url: 图片URL
            save_path: 保存路径
            overwrite: 是否覆盖已存在的文件
            timeout: 超时时间（秒）

        Returns:
            是否成功
        """
        if save_path.exists() and not overwrite:
            logger.debug(f"图片已存在，跳过下载: {save_path}")
            return True

        try:
            # 构建请求头（防止防盗链）
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            }

            # 如果是豆瓣图片，添加Referer
            if "doubanio.com" in url or "douban.com" in url:
                headers["Referer"] = "https://movie.douban.com/"

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=headers,
                    timeout=timeout,
                    follow_redirects=True
                )
                response.raise_for_status()

                # 确保目录存在
                ensure_dir(save_path.parent)

                # 写入文件
                with open(save_path, "wb") as f:
                    f.write(response.content)

                logger.info(f"下载图片成功: {save_path}")
                return True

        except httpx.TimeoutException:
            logger.error(f"下载图片超时: {url}")
            return False
        except httpx.HTTPStatusError as e:
            logger.error(f"下载图片HTTP错误: {url}, 状态码: {e.response.status_code}")
            return False
        except Exception as e:
            logger.error(f"下载图片失败: {url}, 错误: {e}")
            return False

    @staticmethod
    async def _process_tv_images(
        db: AsyncSession,
        media_file: MediaFile,
        metadata: UnifiedTVSeries,
        target_dir: Path,
        config: OrganizeConfig,
        result: Dict[str, Any],
    ):
        """处理电视剧图片（剧集剧照、季海报、剧集海报、背景图）"""
        try:
            # 1. 获取剧集信息（含单集剧照URL和季海报URL）
            episode_still_url, season_poster_url = await ScraperService._get_tv_episode_info(
                db, metadata, media_file
            )

            # 确定目录结构
            # 假设如果父目录名为 "Season X" 或 "Sxx"，则上一级为剧集目录
            import re
            is_season_dir = False
            show_dir = target_dir
            
            dir_name = target_dir.name
            if re.match(r"^(Season \d+|S\d+)$", dir_name, re.IGNORECASE):
                is_season_dir = True
                show_dir = target_dir.parent

            # 2. 下载剧集海报 (Show Poster) -> 剧集目录
            if config.download_poster and metadata.poster_url:
                try:
                    # 剧集海报通常命名为 poster.jpg，存放在剧集根目录
                    show_poster_path = show_dir / f"{config.poster_filename}.jpg"
                    # 剧集海报一般不覆盖，避免资源浪费
                    await ScraperService.download_image(
                        metadata.poster_url,
                        show_poster_path,
                        overwrite=False, 
                    )
                except Exception as e:
                    logger.warning(f"剧集海报下载失败: {e}")

            # 3. 下载背景图 (Show Backdrop) -> 剧集目录
            if config.download_backdrop and metadata.backdrop_url:
                try:
                    # 背景图通常存放在剧集根目录 (fanart.jpg)
                    show_backdrop_path = show_dir / f"{config.backdrop_filename}.jpg"
                    success = await ScraperService.download_image(
                        metadata.backdrop_url,
                        show_backdrop_path,
                        overwrite=False,
                    )
                    if success:
                        # 对于媒体文件，我们也记录背景图路径（哪怕它在父目录）
                        result["backdrop_downloaded"] = True
                        result["backdrop_path"] = str(show_backdrop_path)
                        media_file.has_backdrop = True
                        media_file.backdrop_path = str(show_backdrop_path)
                except Exception as e:
                    logger.warning(f"剧集背景图下载失败: {e}")
                    result["errors"].append(f"背景图下载失败: {str(e)}")

            # 4. 下载季海报 (Season Poster) -> 季目录 (如果存在)
            if config.download_poster and is_season_dir and season_poster_url:
                try:
                    # 季目录下的季海报
                    season_poster_path = target_dir / f"{config.poster_filename}.jpg"
                    await ScraperService.download_image(
                        season_poster_url,
                        season_poster_path,
                        overwrite=False,
                    )
                except Exception as e:
                    logger.warning(f"季海报下载失败: {e}")

            # 5. 下载单集剧照 (Episode Still) -> 文件同名
            poster_url_for_file = episode_still_url
            
            if config.download_poster and poster_url_for_file:
                try:
                    video_stem = Path(media_file.organized_path).stem
                    file_poster_path = target_dir / f"{video_stem}-thumb.jpg"
                    
                    success = await ScraperService.download_image(
                        poster_url_for_file,
                        file_poster_path,
                        overwrite=config.overwrite_poster,
                    )
                    if success:
                        result["poster_downloaded"] = True
                        result["poster_path"] = str(file_poster_path)
                        media_file.has_poster = True
                        media_file.poster_path = str(file_poster_path)
                        logger.info(f"单集剧照下载成功: {file_poster_path}")
                except Exception as e:
                    logger.error(f"单集剧照下载失败: {e}")
                    result["errors"].append(f"单集剧照下载失败: {str(e)}")

        except Exception as e:
             logger.error(f"处理电视剧图片失败: {e}")
             result["errors"].append(f"处理电视剧图片失败: {str(e)}")


    @staticmethod
    async def _get_tv_episode_info(
        db: AsyncSession,
        tv_series: Optional[UnifiedTVSeries],
        media_file: MediaFile,
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        获取电视剧单集信息（剧照和季海报）

        降级逻辑：
        1. 如果没有TMDB ID，尝试自动补全（豆瓣→IMDB→TMDB或标题搜索）
        2. 如果有TMDB ID，使用TMDB获取单集信息
        3. 如果TMDB失败且有TVDB ID，尝试使用TVDB

        Args:
            db: 数据库会话
            tv_series: 电视剧元数据
            media_file: 媒体文件

        Returns:
            (episode_still_url, season_poster_url)
        """
        if not tv_series:
            return None, None
        if not media_file.season_number or not media_file.episode_number:
            return None, None

        # 1. 如果没有TMDB ID，尝试自动补全
        if not tv_series.tmdb_id:
            logger.info(f"电视剧 {tv_series.title} 没有TMDB ID，尝试自动补全...")
            from app.services.mediafile.tmdb_id_resolver_service import TMDBIdResolverService
            tmdb_id, updated = await TMDBIdResolverService.resolve_tmdb_id_for_tv(db, tv_series)
            if tmdb_id:
                logger.info(f"成功补全TMDB ID: {tmdb_id}")
            else:
                logger.warning(f"无法补全TMDB ID，电视剧: {tv_series.title}")

        # 2. 使用TMDB获取单集信息
        if tv_series.tmdb_id:
            result = await ScraperService._get_episode_info_from_tmdb(
                db, tv_series.tmdb_id, media_file.season_number, media_file.episode_number
            )
            if result[0] or result[1]:  # 如果获取到任何信息
                return result

        # 3. 如果TMDB失败，尝试使用TVDB
        if not tv_series.tvdb_id:
            # 尝试补全TVDB ID
            logger.info(f"尝试补全TVDB ID: {tv_series.title}")
            from app.services.mediafile.tmdb_id_resolver_service import TMDBIdResolverService
            tvdb_id, updated = await TMDBIdResolverService.resolve_tvdb_id_for_tv(db, tv_series)

        if tv_series.tvdb_id:
            result = await ScraperService._get_episode_info_from_tvdb(
                db, tv_series.tvdb_id, media_file.season_number, media_file.episode_number
            )
            if result[0] or result[1]:
                return result

        logger.warning(f"无法获取单集信息: {tv_series.title} S{media_file.season_number:02d}E{media_file.episode_number:02d}")
        return None, None

    @staticmethod
    async def _get_episode_info_from_tmdb(
        db: AsyncSession,
        tmdb_id: int,
        season_number: int,
        episode_number: int,
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        从TMDB获取单集信息

        Args:
            db: 数据库会话
            tmdb_id: TMDB ID
            season_number: 季号
            episode_number: 集号

        Returns:
            (episode_still_url, season_poster_url)
        """
        try:
            from app.services.identification.resource_identify_service import ResourceIdentificationService

            # 获取TMDB适配器
            adapter = await ResourceIdentificationService._get_tmdb_adapter(db)

            # 获取季详情
            season_info = await adapter.get_tv_season_detail(tmdb_id, season_number)
            if not season_info:
                logger.debug(f"TMDB: 无法获取季详情: tmdb_id={tmdb_id}, season={season_number}")
                return None, None

            # 提取季海报
            season_poster_url = None
            poster_path = season_info.get("poster_path")
            if poster_path:
                # TMDB的poster_path是相对路径
                if poster_path.startswith("/"):
                    season_poster_url = f"https://image.tmdb.org/t/p/original{poster_path}"
                else:
                    season_poster_url = poster_path

            # 从季信息中提取集详情
            episode_still_url = None
            episodes = season_info.get("episodes", [])
            for ep in episodes:
                if ep.get("episode_number") == episode_number:
                    still_path = ep.get("still_path")
                    if still_path:
                        if still_path.startswith("/"):
                            episode_still_url = f"https://image.tmdb.org/t/p/original{still_path}"
                        else:
                            episode_still_url = still_path
                        logger.debug(f"TMDB: 获取单集剧照URL: S{season_number:02d}E{episode_number:02d}")
                    break

            return episode_still_url, season_poster_url

        except ValueError:
            # TMDB未配置
            logger.debug("TMDB未配置")
            return None, None
        except Exception as e:
            logger.warning(f"TMDB获取单集信息失败: {str(e)}")
            return None, None

    @staticmethod
    async def _get_episode_info_from_tvdb(
        db: AsyncSession,
        tvdb_id: int,
        season_number: int,
        episode_number: int,
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        从TVDB获取单集信息

        Args:
            db: 数据库会话
            tvdb_id: TVDB ID
            season_number: 季号
            episode_number: 集号

        Returns:
            (episode_still_url, season_poster_url)
        """
        try:
            from app.services.identification.resource_identify_service import ResourceIdentificationService

            # 获取TVDB适配器
            adapter = await ResourceIdentificationService._get_tvdb_adapter(db)
            if not adapter:
                logger.debug("TVDB未配置")
                return None, None

            # 获取季详情
            season_info = await adapter.get_tv_season_detail(tvdb_id, season_number)
            if not season_info:
                logger.debug(f"TVDB: 无法获取季详情: tvdb_id={tvdb_id}, season={season_number}")
                return None, None

            # 提取季海报（TVDB返回的是完整URL）
            season_poster_url = season_info.get("poster_path")

            # 从季信息中提取集详情
            episode_still_url = None
            episodes = season_info.get("episodes", [])
            for ep in episodes:
                if ep.get("episode_number") == episode_number:
                    still_path = ep.get("still_path")
                    if still_path:
                        episode_still_url = still_path  # TVDB返回完整URL
                        logger.debug(f"TVDB: 获取单集剧照URL: S{season_number:02d}E{episode_number:02d}")
                    break

            return episode_still_url, season_poster_url

        except Exception as e:
            logger.warning(f"TVDB获取单集信息失败: {str(e)}")
            return None, None

    @staticmethod
    async def _process_adult_images(
        db: AsyncSession,
        media_file: MediaFile,
        metadata: UnifiedAdult,
        target_dir: Path,
        config: OrganizeConfig,
        result: Dict[str, Any],
    ):
        """
        处理成人资源图片（封面、预览图）

        成人资源图片处理策略：
        1. 下载封面（poster）到目录
        2. 可选下载预览图列表

        Args:
            db: 数据库会话
            media_file: 媒体文件对象
            metadata: 成人资源元数据
            target_dir: 目标目录
            config: 整理配置
            result: 结果字典（用于更新）
        """
        try:
            # 1. 下载封面
            if config.download_poster and metadata.poster_url:
                try:
                    poster_path = target_dir / f"{config.poster_filename}.jpg"
                    success = await ScraperService.download_image(
                        metadata.poster_url,
                        poster_path,
                        overwrite=config.overwrite_poster,
                    )
                    if success:
                        result["poster_downloaded"] = True
                        result["poster_path"] = str(poster_path)
                        media_file.has_poster = True
                        media_file.poster_path = str(poster_path)
                        logger.info(f"成人资源封面下载成功: {poster_path}")
                except Exception as e:
                    logger.error(f"成人资源封面下载失败: {e}")
                    result["errors"].append(f"封面下载失败: {str(e)}")

            # 2. 下载背景图（如果有）
            if config.download_backdrop and metadata.backdrop_url:
                try:
                    backdrop_path = target_dir / f"{config.backdrop_filename}.jpg"
                    success = await ScraperService.download_image(
                        metadata.backdrop_url,
                        backdrop_path,
                        overwrite=config.overwrite_backdrop,
                    )
                    if success:
                        result["backdrop_downloaded"] = True
                        result["backdrop_path"] = str(backdrop_path)
                        media_file.has_backdrop = True
                        media_file.backdrop_path = str(backdrop_path)
                        logger.info(f"成人资源背景图下载成功: {backdrop_path}")
                except Exception as e:
                    logger.error(f"成人资源背景图下载失败: {e}")
                    result["errors"].append(f"背景图下载失败: {str(e)}")

            # 3. 如果没有poster_url但有image_list，使用第一张图作为封面
            if not metadata.poster_url and metadata.image_list and len(metadata.image_list) > 0:
                if config.download_poster:
                    try:
                        first_image = metadata.image_list[0]
                        poster_path = target_dir / f"{config.poster_filename}.jpg"
                        success = await ScraperService.download_image(
                            first_image,
                            poster_path,
                            overwrite=config.overwrite_poster,
                        )
                        if success:
                            result["poster_downloaded"] = True
                            result["poster_path"] = str(poster_path)
                            media_file.has_poster = True
                            media_file.poster_path = str(poster_path)
                            logger.info(f"成人资源封面(从image_list)下载成功: {poster_path}")
                    except Exception as e:
                        logger.error(f"成人资源封面下载失败: {e}")
                        result["errors"].append(f"封面下载失败: {str(e)}")

        except Exception as e:
            logger.error(f"处理成人资源图片失败: {e}")
            result["errors"].append(f"处理成人资源图片失败: {str(e)}")

    @staticmethod
    async def batch_scrape(
        db: AsyncSession,
        media_file_ids: list[int],
        config: OrganizeConfig,
    ) -> Dict[str, Any]:
        """
        批量刮削媒体文件

        Args:
            db: 数据库会话
            media_file_ids: 媒体文件ID列表
            config: 整理配置

        Returns:
            批量刮削结果
        """
        results = {
            "total": len(media_file_ids),
            "success_count": 0,
            "failed_count": 0,
            "details": [],
        }

        for file_id in media_file_ids:
            media_file = await db.get(MediaFile, file_id)
            if not media_file:
                results["failed_count"] += 1
                results["details"].append({
                    "file_id": file_id,
                    "success": False,
                    "errors": ["文件不存在"],
                })
                continue

            result = await ScraperService.scrape_media_file(db, media_file, config)

            if result["success"]:
                results["success_count"] += 1
            else:
                results["failed_count"] += 1

            results["details"].append({
                "file_id": file_id,
                **result,
            })

        logger.info(
            f"批量刮削完成: 成功 {results['success_count']}, "
            f"失败 {results['failed_count']}"
        )

        return results

    @staticmethod
    async def generate_nfo_only(
        db: AsyncSession,
        media_file: MediaFile,
        config: OrganizeConfig,
    ) -> Dict[str, Any]:
        """
        仅生成NFO文件（不下载图片）

        Args:
            db: 数据库会话
            media_file: 媒体文件对象
            config: 整理配置

        Returns:
            生成结果
        """
        result = {
            "success": False,
            "nfo_path": None,
            "error": None,
        }

        if not media_file.organized_path:
            result["error"] = "媒体文件未整理，无法生成NFO"
            return result

        try:
            nfo_path = await NFOGeneratorService.generate_nfo(db, media_file, config)
            if nfo_path:
                result["success"] = True
                result["nfo_path"] = nfo_path
            else:
                result["error"] = "NFO生成失败"
        except Exception as e:
            logger.exception(f"生成NFO失败: {media_file.id}")
            result["error"] = str(e)

        return result


# 全局单例
scraper_service = ScraperService()
