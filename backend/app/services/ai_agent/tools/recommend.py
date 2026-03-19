# -*- coding: utf-8 -*-
"""
推荐工具

电影和剧集推荐
"""
from typing import Any, Dict, List

from sqlalchemy import select, func, desc, String, literal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import JSONB

from app.core.config import settings
from app.constants.ai_agent import AGENT_TOOL_MOVIE_RECOMMEND, AGENT_TOOL_TV_RECOMMEND
from app.models import UnifiedMovie, UnifiedTVSeries, MediaServerWatchHistory
from app.services.ai_agent.tool_registry import BaseTool, register_tool


@register_tool
class MovieRecommendTool(BaseTool):
    """电影推荐工具"""

    name = AGENT_TOOL_MOVIE_RECOMMEND
    description = """推荐电影。可以根据用户喜好、类型、年代、评分等条件推荐电影。
    支持的推荐方式：
    - 按类型推荐（如动作片、喜剧片）
    - 按年代推荐（如2020年代新片）
    - 按评分推荐（高分电影）
    - 根据观看历史推荐（需要有观看记录）
    - 随机推荐热门电影"""

    parameters = {
        "type": "object",
        "properties": {
            "genre": {
                "type": "string",
                "description": "电影类型，如：动作、喜剧、科幻、恐怖、爱情、悬疑等",
            },
            "year_from": {
                "type": "integer",
                "description": "起始年份",
            },
            "year_to": {
                "type": "integer",
                "description": "结束年份",
            },
            "min_rating": {
                "type": "number",
                "description": "最低评分（0-10）",
            },
            "based_on_history": {
                "type": "boolean",
                "description": "是否基于观看历史推荐",
                "default": False,
            },
            "limit": {
                "type": "integer",
                "description": "推荐数量",
                "default": 5,
            },
        },
        "required": [],
    }

    @classmethod
    async def execute(
        cls,
        db: AsyncSession,
        user_id: int,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        """执行电影推荐"""
        genre = arguments.get("genre")
        year_from = arguments.get("year_from")
        year_to = arguments.get("year_to")
        min_rating = arguments.get("min_rating", 0)
        based_on_history = arguments.get("based_on_history", False)
        limit = min(arguments.get("limit", 5), 20)

        # 构建查询
        query = select(UnifiedMovie).where(UnifiedMovie.tmdb_id.isnot(None))

        # 按类型过滤
        if genre:
            if settings.database.DB_TYPE.lower() == "postgresql":
                query = query.where(UnifiedMovie.genres.cast(JSONB).contains(literal([genre], JSONB)))
            else:
                query = query.where(UnifiedMovie.genres.cast(String).like(f'%"{genre}"%'))

        # 按年份过滤
        if year_from:
            query = query.where(UnifiedMovie.year >= year_from)
        if year_to:
            query = query.where(UnifiedMovie.year <= year_to)

        # 按评分过滤
        if min_rating:
            query = query.where(
                (UnifiedMovie.rating_douban >= min_rating) |
                (UnifiedMovie.rating_tmdb >= min_rating)
            )

        # 排序：优先豆瓣评分，其次TMDB评分
        query = query.order_by(
            desc(func.coalesce(UnifiedMovie.rating_douban, UnifiedMovie.rating_tmdb, 0))
        ).limit(limit)

        result = await db.execute(query)
        movies = result.scalars().all()

        if not movies:
            # 构建详细的筛选条件说明
            filters_desc = []
            if genre:
                filters_desc.append(f"类型={genre}")
            if year_from and year_to:
                if year_from == year_to:
                    filters_desc.append(f"年份={year_from}")
                else:
                    filters_desc.append(f"年份={year_from}-{year_to}")
            elif year_from:
                filters_desc.append(f"年份>={year_from}")
            elif year_to:
                filters_desc.append(f"年份<={year_to}")
            if min_rating:
                filters_desc.append(f"评分>={min_rating}")

            filters_text = ", ".join(filters_desc) if filters_desc else "无筛选条件"

            return {
                "success": True,
                "message": f"未找到符合条件的电影。筛选条件: {filters_text}。"
                           f"建议尝试: ① 放宽筛选条件(降低评分/扩大年份) ② 更换类型 ③ 同步更多PT资源",
                "movies": [],
                "total": 0,
                "filters_applied": {
                    "genre": genre,
                    "year_from": year_from,
                    "year_to": year_to,
                    "min_rating": min_rating,
                }
            }

        # 格式化结果
        movie_list = []
        for m in movies:
            movie_list.append({
                "id": m.id,
                "title": m.title,
                "original_title": m.original_title,
                "year": m.year,
                "genres": m.genres,
                "douban_rating": float(m.rating_douban) if m.rating_douban else None,
                "tmdb_rating": float(m.rating_tmdb) if m.rating_tmdb else None,
                "overview": m.overview[:200] if m.overview else None,
                "poster_url": m.poster_url,
            })

        return {
            "success": True,
            "message": f"为您推荐以下{len(movie_list)}部电影",
            "movies": movie_list,
        }


@register_tool
class TVRecommendTool(BaseTool):
    """剧集推荐工具"""

    name = AGENT_TOOL_TV_RECOMMEND
    description = """推荐电视剧/剧集。可以根据类型、年代、评分等条件推荐剧集。
    支持国产剧、美剧、日剧、韩剧等多种类型。"""

    parameters = {
        "type": "object",
        "properties": {
            "genre": {
                "type": "string",
                "description": "剧集类型，如：剧情、喜剧、悬疑、科幻等",
            },
            "origin_country": {
                "type": "string",
                "description": "产地，如：中国、美国、日本、韩国等",
            },
            "year_from": {
                "type": "integer",
                "description": "起始年份",
            },
            "year_to": {
                "type": "integer",
                "description": "结束年份",
            },
            "min_rating": {
                "type": "number",
                "description": "最低评分（0-10）",
            },
            "status": {
                "type": "string",
                "description": "状态：连载中、已完结",
                "enum": ["连载中", "已完结"],
            },
            "limit": {
                "type": "integer",
                "description": "推荐数量",
                "default": 5,
            },
        },
        "required": [],
    }

    @classmethod
    async def execute(
        cls,
        db: AsyncSession,
        user_id: int,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        """执行剧集推荐"""
        genre = arguments.get("genre")
        origin_country = arguments.get("origin_country")
        year_from = arguments.get("year_from")
        year_to = arguments.get("year_to")
        min_rating = arguments.get("min_rating", 0)
        status = arguments.get("status")
        limit = min(arguments.get("limit", 5), 20)

        # 构建查询
        query = select(UnifiedTVSeries).where(UnifiedTVSeries.tmdb_id.isnot(None))

        # 按类型过滤
        if genre:
            if settings.database.DB_TYPE.lower() == "postgresql":
                query = query.where(UnifiedTVSeries.genres.cast(JSONB).contains(literal([genre], JSONB)))
            else:
                query = query.where(UnifiedTVSeries.genres.cast(String).like(f'%"{genre}"%'))

        # 按产地过滤
        if origin_country:
            if settings.database.DB_TYPE.lower() == "postgresql":
                query = query.where(UnifiedTVSeries.countries.cast(JSONB).contains(literal([origin_country], JSONB)))
            else:
                query = query.where(UnifiedTVSeries.countries.cast(String).like(f'%"{origin_country}"%'))

        # 按年份过滤
        if year_from:
            query = query.where(UnifiedTVSeries.year >= year_from)
        if year_to:
            query = query.where(UnifiedTVSeries.year <= year_to)

        # 按评分过滤
        if min_rating:
            query = query.where(
                (UnifiedTVSeries.rating_douban >= min_rating) |
                (UnifiedTVSeries.rating_tmdb >= min_rating)
            )

        # 按状态过滤
        if status:
            if status == "连载中":
                query = query.where(UnifiedTVSeries.status == "Returning Series")
            elif status == "已完结":
                query = query.where(UnifiedTVSeries.status == "Ended")

        # 排序
        query = query.order_by(
            desc(func.coalesce(UnifiedTVSeries.rating_douban, UnifiedTVSeries.rating_tmdb, 0))
        ).limit(limit)

        result = await db.execute(query)
        tv_series = result.scalars().all()

        if not tv_series:
            # 构建详细的筛选条件说明
            filters_desc = []
            if genre:
                filters_desc.append(f"类型={genre}")
            if origin_country:
                filters_desc.append(f"产地={origin_country}")
            if year_from and year_to:
                if year_from == year_to:
                    filters_desc.append(f"年份={year_from}")
                else:
                    filters_desc.append(f"年份={year_from}-{year_to}")
            elif year_from:
                filters_desc.append(f"年份>={year_from}")
            elif year_to:
                filters_desc.append(f"年份<={year_to}")
            if min_rating:
                filters_desc.append(f"评分>={min_rating}")
            if status:
                filters_desc.append(f"状态={status}")

            filters_text = ", ".join(filters_desc) if filters_desc else "无筛选条件"

            return {
                "success": True,
                "message": f"未找到符合条件的剧集。筛选条件: {filters_text}。"
                           f"建议尝试: ① 放宽筛选条件(降低评分/扩大年份) ② 更换类型或产地 ③ 同步更多PT资源",
                "tv_series": [],
                "total": 0,
                "filters_applied": {
                    "genre": genre,
                    "origin_country": origin_country,
                    "year_from": year_from,
                    "year_to": year_to,
                    "min_rating": min_rating,
                    "status": status,
                }
            }

        # 格式化结果
        tv_list = []
        for tv in tv_series:
            tv_list.append({
                "id": tv.id,
                "title": tv.title,
                "original_title": tv.original_title,
                "first_air_year": tv.year,
                "genres": tv.genres,
                "origin_country": tv.countries,
                "douban_rating": float(tv.rating_douban) if tv.rating_douban else None,
                "tmdb_rating": float(tv.rating_tmdb) if tv.rating_tmdb else None,
                "number_of_seasons": tv.number_of_seasons,
                "status": tv.status,
                "overview": tv.overview[:200] if tv.overview else None,
                "poster_url": tv.poster_url,
            })

        return {
            "success": True,
            "message": f"为您推荐以下{len(tv_list)}部剧集",
            "tv_series": tv_list,
        }
