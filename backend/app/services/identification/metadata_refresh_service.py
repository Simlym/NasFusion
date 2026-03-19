# -*- coding: utf-8 -*-
"""
元数据刷新服务

从 TMDB/豆瓣 获取最新元数据并智能合并到本地记录
"""
import logging
from typing import Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.metadata import DoubanAdapter, TMDBAdapter
from app.models.unified_movie import UnifiedMovie
from app.models.unified_tv_series import UnifiedTVSeries
from app.services.identification.unified_movie_service import UnifiedMovieService
from app.services.identification.unified_tv_series_service import UnifiedTVSeriesService
from app.utils.timezone import now

logger = logging.getLogger(__name__)

# 始终用新数据覆盖的字段（这些字段会随时间变化或可能有误）
ALWAYS_UPDATE_FIELDS = {
    "tmdb": {
        "rating_tmdb", "votes_tmdb", "genres",
    },
    "douban": {
        "rating_douban", "votes_douban", "genres",
    },
}

# 仅当当前值为空时才填充的字段
FILL_IF_EMPTY_FIELDS = {
    "tmdb": {
        "title", "original_title", "overview", "poster_url", "backdrop_url",
        "directors", "actors", "writers", "imdb_id", "tagline",
        "languages", "countries", "certification",
        # 电影特有
        "release_date", "runtime",
        # TV 特有
        "first_air_date", "last_air_date", "number_of_seasons",
        "number_of_episodes", "creators", "networks",
    },
    "douban": {
        "title", "original_title", "overview", "poster_url", "backdrop_url",
        "directors", "actors", "imdb_id",
        "languages", "countries",
        # 电影特有
        "release_date", "runtime",
        # TV 特有
        "first_air_date",
    },
}


class MetadataRefreshService:
    """元数据刷新服务"""

    @staticmethod
    async def refresh_movie_metadata(
        db: AsyncSession,
        movie_id: int,
        source: str,
    ) -> Tuple[UnifiedMovie, List[str]]:
        """
        刷新电影元数据

        Args:
            db: 数据库会话
            movie_id: 电影ID
            source: 数据源 ("tmdb" 或 "douban")

        Returns:
            (更新后的电影实体, 变更字段列表)
        """
        movie = await UnifiedMovieService.get_by_id(db, movie_id)
        if not movie:
            raise ValueError(f"电影不存在: {movie_id}")

        # 获取最新元数据
        new_metadata = await MetadataRefreshService._fetch_movie_metadata(
            db, movie, source
        )

        # 智能合并
        updated_fields = MetadataRefreshService._smart_merge_metadata(
            movie, new_metadata, source
        )

        # 更新 detail_loaded_at
        movie.detail_loaded_at = now()

        await db.commit()
        await db.refresh(movie)

        logger.info(
            f"Refreshed movie {movie_id} from {source}, "
            f"updated fields: {updated_fields}"
        )

        return movie, updated_fields

    @staticmethod
    async def refresh_tv_metadata(
        db: AsyncSession,
        tv_id: int,
        source: str,
    ) -> Tuple[UnifiedTVSeries, List[str]]:
        """
        刷新电视剧元数据

        Args:
            db: 数据库会话
            tv_id: 电视剧ID
            source: 数据源 ("tmdb" 或 "douban")

        Returns:
            (更新后的电视剧实体, 变更字段列表)
        """
        tv = await UnifiedTVSeriesService.get_by_id(db, tv_id)
        if not tv:
            raise ValueError(f"电视剧不存在: {tv_id}")

        # 获取最新元数据
        new_metadata = await MetadataRefreshService._fetch_tv_metadata(
            db, tv, source
        )

        # 智能合并
        updated_fields = MetadataRefreshService._smart_merge_metadata(
            tv, new_metadata, source
        )

        # 更新 detail_loaded_at
        tv.detail_loaded_at = now()

        await db.commit()
        await db.refresh(tv)

        logger.info(
            f"Refreshed TV {tv_id} from {source}, "
            f"updated fields: {updated_fields}"
        )

        return tv, updated_fields

    @staticmethod
    async def _fetch_movie_metadata(
        db: AsyncSession,
        movie: UnifiedMovie,
        source: str,
    ) -> Dict:
        """从指定数据源获取电影元数据"""
        if source == "tmdb":
            if not movie.tmdb_id:
                raise ValueError("该电影没有 TMDB ID，无法从 TMDB 刷新")
            adapter = await MetadataRefreshService._get_tmdb_adapter(db)
            return await adapter.get_movie_details(movie.tmdb_id)
        elif source == "douban":
            if not movie.douban_id:
                raise ValueError("该电影没有豆瓣 ID，无法从豆瓣刷新")
            adapter = await MetadataRefreshService._get_douban_adapter(db)
            return await adapter.get_movie_detail(movie.douban_id)
        else:
            raise ValueError(f"不支持的数据源: {source}")

    @staticmethod
    async def _fetch_tv_metadata(
        db: AsyncSession,
        tv: UnifiedTVSeries,
        source: str,
    ) -> Dict:
        """从指定数据源获取电视剧元数据"""
        if source == "tmdb":
            if not tv.tmdb_id:
                raise ValueError("该电视剧没有 TMDB ID，无法从 TMDB 刷新")
            adapter = await MetadataRefreshService._get_tmdb_adapter(db)
            return await adapter.get_tv_details(tv.tmdb_id)
        elif source == "douban":
            if not tv.douban_id:
                raise ValueError("该电视剧没有豆瓣 ID，无法从豆瓣刷新")
            adapter = await MetadataRefreshService._get_douban_adapter(db)
            return await adapter.get_tv_detail(tv.douban_id)
        else:
            raise ValueError(f"不支持的数据源: {source}")

    @staticmethod
    def _smart_merge_metadata(
        record,
        new_metadata: Dict,
        source: str,
    ) -> List[str]:
        """
        智能合并元数据

        根据字段分类决定更新策略：
        - 始终更新：评分、投票数、genres 等（会随时间变化）
        - 空值填充：标题、简介、图片等（仅当当前值为空时填充）

        Returns:
            变更字段列表
        """
        updated_fields = []

        always_update = ALWAYS_UPDATE_FIELDS.get(source, set())
        fill_if_empty = FILL_IF_EMPTY_FIELDS.get(source, set())

        for field in always_update:
            new_value = new_metadata.get(field)
            if new_value is not None:
                old_value = getattr(record, field, None)
                if old_value != new_value:
                    setattr(record, field, new_value)
                    updated_fields.append(field)

        for field in fill_if_empty:
            new_value = new_metadata.get(field)
            if new_value is None:
                continue
            old_value = getattr(record, field, None)
            if MetadataRefreshService._is_empty(old_value):
                setattr(record, field, new_value)
                updated_fields.append(field)

        return updated_fields

    @staticmethod
    def _is_empty(value) -> bool:
        """判断值是否为空"""
        if value is None:
            return True
        if isinstance(value, str) and value.strip() == "":
            return True
        if isinstance(value, (list, dict)) and len(value) == 0:
            return True
        return False

    @staticmethod
    async def _get_tmdb_adapter(db: AsyncSession) -> TMDBAdapter:
        """获取TMDB适配器实例"""
        from app.models.system_setting import SystemSetting
        from sqlalchemy import select

        query = select(SystemSetting).where(
            SystemSetting.category == "metadata_scraping",
            SystemSetting.key == "tmdb_api_key",
        )
        result = await db.execute(query)
        setting = result.scalar_one_or_none()

        if not setting or not setting.value:
            raise ValueError("TMDB API Key未配置")

        proxy_query = select(SystemSetting).where(
            SystemSetting.category == "metadata_scraping",
            SystemSetting.key == "tmdb_proxy",
        )
        proxy_result = await db.execute(proxy_query)
        proxy_setting = proxy_result.scalar_one_or_none()

        proxy_config = {}
        if proxy_setting and proxy_setting.value:
            proxy_config = {
                "enabled": True,
                "url": proxy_setting.value,
            }

        tmdb_config = {
            "api_key": setting.value,
            "proxy_config": proxy_config,
            "language": "zh-CN",
        }

        return TMDBAdapter(tmdb_config)

    @staticmethod
    async def _get_douban_adapter(db: AsyncSession) -> DoubanAdapter:
        """获取豆瓣适配器实例"""
        douban_config = {
            "timeout": 30,
            "max_retries": 3,
        }
        return DoubanAdapter(douban_config)
