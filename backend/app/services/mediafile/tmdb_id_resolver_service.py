# -*- coding: utf-8 -*-
"""
TMDB ID 自动补全服务

实现降级逻辑：
1. 如果只有豆瓣ID，调用豆瓣API获取IMDB ID
2. 如果有IMDB ID，调用TMDB的find by external id获取TMDB ID
3. 如果还是获取不到，使用标题+年份在TMDB搜索
"""
import logging
from typing import Optional, Dict, Any, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.unified_tv_series import UnifiedTVSeries
from app.models.unified_movie import UnifiedMovie
from app.constants import UNIFIED_TABLE_TV, UNIFIED_TABLE_MOVIES

logger = logging.getLogger(__name__)


class TMDBIdResolverService:
    """
    TMDB ID 自动补全服务

    用于在刮削时自动解析和补全TMDB ID
    """

    @staticmethod
    async def resolve_tmdb_id_for_tv(
        db: AsyncSession,
        tv_series: UnifiedTVSeries,
    ) -> Tuple[Optional[int], bool]:
        """
        为电视剧解析TMDB ID

        降级逻辑：
        1. 如果已有TMDB ID，直接返回
        2. 如果有IMDB ID，通过TMDB的find API获取
        3. 如果只有豆瓣ID，先获取IMDB ID，再获取TMDB ID
        4. 如果还是获取不到，使用标题+年份在TMDB搜索

        Args:
            db: 数据库会话
            tv_series: 电视剧对象

        Returns:
            (tmdb_id, updated): TMDB ID和是否更新了数据库
        """
        # 1. 已有TMDB ID
        if tv_series.tmdb_id:
            logger.debug(f"电视剧已有TMDB ID: {tv_series.tmdb_id}")
            return tv_series.tmdb_id, False

        updated = False
        tmdb_id = None
        imdb_id = tv_series.imdb_id

        # 2. 如果没有IMDB ID但有豆瓣ID，尝试从豆瓣获取IMDB ID
        if not imdb_id and tv_series.douban_id:
            logger.info(f"尝试从豆瓣获取IMDB ID: douban_id={tv_series.douban_id}")
            imdb_id = await TMDBIdResolverService._get_imdb_from_douban(
                db, tv_series.douban_id, "tv"
            )
            if imdb_id:
                logger.info(f"从豆瓣获取到IMDB ID: {imdb_id}")
                # 更新数据库
                tv_series.imdb_id = imdb_id
                updated = True

        # 3. 如果有IMDB ID，通过TMDB查找
        if imdb_id:
            logger.info(f"尝试通过IMDB ID获取TMDB ID: imdb_id={imdb_id}")
            tmdb_id = await TMDBIdResolverService._get_tmdb_from_imdb(
                db, imdb_id, "tv"
            )
            if tmdb_id:
                logger.info(f"通过IMDB ID获取到TMDB ID: {tmdb_id}")
                tv_series.tmdb_id = tmdb_id
                updated = True
                await db.commit()
                return tmdb_id, updated

        # 4. 使用标题+年份搜索TMDB
        if tv_series.title:
            logger.info(f"尝试通过标题搜索TMDB: title={tv_series.title}, year={tv_series.year}")
            tmdb_id = await TMDBIdResolverService._search_tmdb_by_title(
                db, tv_series.title, tv_series.year, "tv"
            )
            if tmdb_id:
                logger.info(f"通过标题搜索获取到TMDB ID: {tmdb_id}")
                tv_series.tmdb_id = tmdb_id
                updated = True

        if updated:
            await db.commit()

        return tmdb_id, updated

    @staticmethod
    async def resolve_tmdb_id_for_movie(
        db: AsyncSession,
        movie: UnifiedMovie,
    ) -> Tuple[Optional[int], bool]:
        """
        为电影解析TMDB ID

        Args:
            db: 数据库会话
            movie: 电影对象

        Returns:
            (tmdb_id, updated): TMDB ID和是否更新了数据库
        """
        # 1. 已有TMDB ID
        if movie.tmdb_id:
            return movie.tmdb_id, False

        updated = False
        tmdb_id = None
        imdb_id = movie.imdb_id

        # 2. 如果没有IMDB ID但有豆瓣ID，尝试从豆瓣获取IMDB ID
        if not imdb_id and movie.douban_id:
            logger.info(f"尝试从豆瓣获取IMDB ID: douban_id={movie.douban_id}")
            imdb_id = await TMDBIdResolverService._get_imdb_from_douban(
                db, movie.douban_id, "movie"
            )
            if imdb_id:
                logger.info(f"从豆瓣获取到IMDB ID: {imdb_id}")
                movie.imdb_id = imdb_id
                updated = True

        # 3. 如果有IMDB ID，通过TMDB查找
        if imdb_id:
            logger.info(f"尝试通过IMDB ID获取TMDB ID: imdb_id={imdb_id}")
            tmdb_id = await TMDBIdResolverService._get_tmdb_from_imdb(
                db, imdb_id, "movie"
            )
            if tmdb_id:
                logger.info(f"通过IMDB ID获取到TMDB ID: {tmdb_id}")
                movie.tmdb_id = tmdb_id
                updated = True
                await db.commit()
                return tmdb_id, updated

        # 4. 使用标题+年份搜索TMDB
        if movie.title:
            logger.info(f"尝试通过标题搜索TMDB: title={movie.title}, year={movie.year}")
            tmdb_id = await TMDBIdResolverService._search_tmdb_by_title(
                db, movie.title, movie.year, "movie"
            )
            if tmdb_id:
                logger.info(f"通过标题搜索获取到TMDB ID: {tmdb_id}")
                movie.tmdb_id = tmdb_id
                updated = True

        if updated:
            await db.commit()

        return tmdb_id, updated

    @staticmethod
    async def _get_imdb_from_douban(
        db: AsyncSession,
        douban_id: str,
        media_type: str,
    ) -> Optional[str]:
        """
        从豆瓣获取IMDB ID

        Args:
            db: 数据库会话
            douban_id: 豆瓣ID
            media_type: 媒体类型 (movie/tv)

        Returns:
            IMDB ID，未找到返回None
        """
        try:
            from app.services.identification.resource_identify_service import ResourceIdentificationService

            # 获取豆瓣适配器
            adapter = await ResourceIdentificationService._get_douban_adapter(db)

            # 根据类型获取详情
            if media_type == "tv":
                detail = await adapter.get_tv_detail(douban_id, fetch_celebrities=False)
            else:
                detail = await adapter.get_movie_detail(douban_id, fetch_celebrities=False)

            return detail.get("imdb_id") if detail else None

        except Exception as e:
            logger.warning(f"从豆瓣获取IMDB ID失败: douban_id={douban_id}, 错误: {str(e)}")
            return None

    @staticmethod
    async def _get_tmdb_from_imdb(
        db: AsyncSession,
        imdb_id: str,
        media_type: str,
    ) -> Optional[int]:
        """
        通过IMDB ID获取TMDB ID

        Args:
            db: 数据库会话
            imdb_id: IMDB ID
            media_type: 媒体类型 (movie/tv)

        Returns:
            TMDB ID，未找到返回None
        """
        try:
            from app.services.identification.resource_identify_service import ResourceIdentificationService

            # 获取TMDB适配器
            adapter = await ResourceIdentificationService._get_tmdb_adapter(db)

            # 根据类型查找
            if media_type == "tv":
                result = await adapter.find_tv_by_imdb_id(imdb_id)
            else:
                result = await adapter.find_by_imdb_id(imdb_id)

            return result.get("tmdb_id") if result else None

        except Exception as e:
            logger.warning(f"通过IMDB ID获取TMDB ID失败: imdb_id={imdb_id}, 错误: {str(e)}")
            return None

    @staticmethod
    async def _search_tmdb_by_title(
        db: AsyncSession,
        title: str,
        year: Optional[int],
        media_type: str,
    ) -> Optional[int]:
        """
        通过标题+年份在TMDB搜索

        Args:
            db: 数据库会话
            title: 标题
            year: 年份
            media_type: 媒体类型 (movie/tv)

        Returns:
            TMDB ID，未找到返回None
        """
        try:
            from app.services.identification.resource_identify_service import ResourceIdentificationService

            # 获取TMDB适配器
            adapter = await ResourceIdentificationService._get_tmdb_adapter(db)

            # 根据类型搜索
            if media_type == "tv":
                results = await adapter.search_tv_by_title(title, year)
            else:
                results = await adapter.search_by_title(title, year)

            if not results:
                return None

            # 返回第一个结果的TMDB ID
            # 如果有年份，优先匹配年份相同的结果
            if year:
                for result in results:
                    result_year = result.get("year")
                    if result_year and abs(result_year - year) <= 1:
                        return result.get("tmdb_id")

            # 返回第一个结果
            return results[0].get("tmdb_id") if results else None

        except Exception as e:
            logger.warning(f"通过标题搜索TMDB失败: title={title}, 错误: {str(e)}")
            return None

    @staticmethod
    async def resolve_tvdb_id_for_tv(
        db: AsyncSession,
        tv_series: UnifiedTVSeries,
    ) -> Tuple[Optional[int], bool]:
        """
        为电视剧解析TVDB ID

        降级逻辑：
        1. 如果已有TVDB ID，直接返回
        2. 如果有IMDB ID，通过TVDB的search API获取

        Args:
            db: 数据库会话
            tv_series: 电视剧对象

        Returns:
            (tvdb_id, updated): TVDB ID和是否更新了数据库
        """
        # 1. 已有TVDB ID
        if tv_series.tvdb_id:
            return tv_series.tvdb_id, False

        updated = False
        tvdb_id = None
        imdb_id = tv_series.imdb_id

        # 2. 如果没有IMDB ID但有豆瓣ID，尝试从豆瓣获取IMDB ID
        if not imdb_id and tv_series.douban_id:
            logger.info(f"尝试从豆瓣获取IMDB ID: douban_id={tv_series.douban_id}")
            imdb_id = await TMDBIdResolverService._get_imdb_from_douban(
                db, tv_series.douban_id, "tv"
            )
            if imdb_id:
                tv_series.imdb_id = imdb_id
                updated = True

        # 3. 如果有IMDB ID，通过TVDB查找
        if imdb_id:
            logger.info(f"尝试通过IMDB ID获取TVDB ID: imdb_id={imdb_id}")
            tvdb_id = await TMDBIdResolverService._get_tvdb_from_imdb(db, imdb_id)
            if tvdb_id:
                logger.info(f"通过IMDB ID获取到TVDB ID: {tvdb_id}")
                tv_series.tvdb_id = tvdb_id
                updated = True

        if updated:
            await db.commit()

        return tvdb_id, updated

    @staticmethod
    async def _get_tvdb_from_imdb(
        db: AsyncSession,
        imdb_id: str,
    ) -> Optional[int]:
        """
        通过IMDB ID获取TVDB ID

        Args:
            db: 数据库会话
            imdb_id: IMDB ID

        Returns:
            TVDB ID，未找到返回None
        """
        try:
            from app.services.identification.resource_identify_service import ResourceIdentificationService

            # 获取TVDB适配器
            adapter = await ResourceIdentificationService._get_tvdb_adapter(db)
            if not adapter:
                return None

            result = await adapter.search_by_imdb_id(imdb_id)
            return result.get("tvdb_id") if result else None

        except Exception as e:
            logger.warning(f"通过IMDB ID获取TVDB ID失败: imdb_id={imdb_id}, 错误: {str(e)}")
            return None
