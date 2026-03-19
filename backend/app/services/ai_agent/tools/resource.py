# -*- coding: utf-8 -*-
"""
资源工具

PT资源搜索和识别
"""
from typing import Any, Dict, List

from sqlalchemy import select, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.ai_agent import AGENT_TOOL_RESOURCE_SEARCH, AGENT_TOOL_RESOURCE_IDENTIFY
from app.models import PTResource, PTSite
from app.services.ai_agent.tool_registry import BaseTool, register_tool


@register_tool
class ResourceSearchTool(BaseTool):
    """资源搜索工具"""

    name = AGENT_TOOL_RESOURCE_SEARCH
    description = """在PT站点搜索影视资源。可以按名称、类型、分辨率、促销状态等条件搜索。
    搜索已同步到本地数据库的PT资源。"""

    parameters = {
        "type": "object",
        "properties": {
            "keyword": {
                "type": "string",
                "description": "搜索关键词（电影/剧集名称）",
            },
            "media_type": {
                "type": "string",
                "description": "媒体类型",
                "enum": ["movie", "tv", "anime", "music", "adult"],
            },
            "resolution": {
                "type": "string",
                "description": "分辨率",
                "enum": ["2160p", "1080p", "720p", "480p"],
            },
            "promotion": {
                "type": "string",
                "description": "促销类型",
                "enum": ["free", "2x_free", "50_off", "none"],
            },
            "site_name": {
                "type": "string",
                "description": "站点名称（如：MTeam）",
            },
            "limit": {
                "type": "integer",
                "description": "结果数量",
                "default": 10,
            },
        },
        "required": ["keyword"],
    }

    @classmethod
    async def execute(
        cls,
        db: AsyncSession,
        user_id: int,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        """执行资源搜索"""
        keyword = arguments.get("keyword", "")
        media_type = arguments.get("media_type")
        resolution = arguments.get("resolution")
        promotion = arguments.get("promotion")
        site_name = arguments.get("site_name")
        limit = min(arguments.get("limit", 10), 50)

        if not keyword:
            return {
                "success": False,
                "error": "请提供搜索关键词",
            }

        # 构建查询
        query = select(PTResource).where(
            or_(
                PTResource.title.ilike(f"%{keyword}%"),
                PTResource.subtitle.ilike(f"%{keyword}%"),
            )
        )

        # 按媒体类型过滤
        if media_type:
            query = query.where(PTResource.category == media_type)

        # 按分辨率过滤
        if resolution:
            query = query.where(PTResource.resolution == resolution)

        # 按促销过滤
        if promotion:
            if promotion == "free":
                query = query.where(PTResource.promotion_type.in_(["free", "2x_free"]))
            elif promotion == "2x_free":
                query = query.where(PTResource.promotion_type == "2x_free")
            elif promotion == "50_off":
                query = query.where(PTResource.promotion_type == "50_off")
            elif promotion == "none":
                query = query.where(
                    or_(PTResource.promotion_type.is_(None), PTResource.promotion_type == "none")
                )

        # 按站点过滤
        if site_name:
            site_result = await db.execute(
                select(PTSite).where(PTSite.name.ilike(f"%{site_name}%"))
            )
            site = site_result.scalar_one_or_none()
            if site:
                query = query.where(PTResource.site_id == site.id)

        # 排序：优先免费资源，然后按发布时间
        query = query.order_by(
            desc(PTResource.is_free),
            desc(PTResource.published_at),
        ).limit(limit)

        result = await db.execute(query)
        resources = result.scalars().all()

        if not resources:
            return {
                "success": True,
                "message": f"未找到关键词「{keyword}」相关的资源",
                "resources": [],
            }

        # 格式化结果
        resource_list = []
        for r in resources:
            resource_list.append({
                "id": r.id,
                "title": r.title,
                "subtitle": r.subtitle,
                "category": r.category,
                "resolution": r.resolution,
                "size": r.size_bytes,
                "size_str": cls._format_size(r.size_bytes) if r.size_bytes else None,
                "seeders": r.seeders,
                "leechers": r.leechers,
                "promotion_type": r.promotion_type,
                "is_free": r.is_free,
                "published_at": r.published_at.isoformat() if r.published_at else None,
            })

        return {
            "success": True,
            "message": f"找到{len(resource_list)}个相关资源",
            "resources": resource_list,
        }

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """格式化文件大小"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.2f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.2f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


@register_tool
class ResourceIdentifyTool(BaseTool):
    """资源识别工具"""

    name = AGENT_TOOL_RESOURCE_IDENTIFY
    description = """识别文件名或资源标题对应的影视作品信息。
    可以从文件名中提取电影/剧集名称、年份、分辨率、季集信息等。
    这对于识别规则覆盖不到的资源特别有用。"""

    parameters = {
        "type": "object",
        "properties": {
            "filename": {
                "type": "string",
                "description": "需要识别的文件名或资源标题",
            },
            "hints": {
                "type": "object",
                "description": "辅助提示信息",
                "properties": {
                    "media_type": {
                        "type": "string",
                        "description": "媒体类型提示：movie或tv",
                    },
                    "year": {
                        "type": "integer",
                        "description": "年份提示",
                    },
                },
            },
        },
        "required": ["filename"],
    }

    @classmethod
    async def execute(
        cls,
        db: AsyncSession,
        user_id: int,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        """执行资源识别"""
        filename = arguments.get("filename", "")
        hints = arguments.get("hints", {})

        if not filename:
            return {
                "success": False,
                "error": "请提供文件名",
            }

        # 导入解析服务
        from app.services.common.filename_parser_service import FilenameParserService

        # 解析文件名
        parsed = FilenameParserService.parse(filename)

        # 如果有提示信息，补充
        if hints:
            if hints.get("media_type"):
                parsed["media_type"] = hints["media_type"]
            if hints.get("year"):
                parsed["year"] = hints["year"]

        # 尝试从数据库查找匹配
        matched_media = None
        if parsed.get("title"):
            title = parsed["title"]
            year = parsed.get("year")

            # 先查电影
            movie_query = select(UnifiedMovie).where(
                or_(
                    UnifiedMovie.title.ilike(f"%{title}%"),
                    UnifiedMovie.original_title.ilike(f"%{title}%"),
                )
            )
            if year:
                movie_query = movie_query.where(UnifiedMovie.year == year)
            movie_query = movie_query.limit(1)

            movie_result = await db.execute(movie_query)
            movie = movie_result.scalar_one_or_none()

            if movie:
                matched_media = {
                    "type": "movie",
                    "id": movie.id,
                    "title": movie.title,
                    "original_title": movie.original_title,
                    "year": movie.year,
                    "tmdb_id": movie.tmdb_id,
                    "douban_id": movie.douban_id,
                }
            else:
                # 查剧集
                from app.models import UnifiedTVSeries
                tv_query = select(UnifiedTVSeries).where(
                    or_(
                        UnifiedTVSeries.title.ilike(f"%{title}%"),
                        UnifiedTVSeries.original_title.ilike(f"%{title}%"),
                    )
                )
                if year:
                    tv_query = tv_query.where(UnifiedTVSeries.year == year)
                tv_query = tv_query.limit(1)

                tv_result = await db.execute(tv_query)
                tv = tv_result.scalar_one_or_none()

                if tv:
                    matched_media = {
                        "type": "tv",
                        "id": tv.id,
                        "title": tv.title,
                        "original_title": tv.original_title,
                        "year": tv.year,
                        "tmdb_id": tv.tmdb_id,
                        "douban_id": tv.douban_id,
                    }

        return {
            "success": True,
            "filename": filename,
            "parsed": parsed,
            "matched_media": matched_media,
            "message": "识别完成" + (
                f"，匹配到：{matched_media['title']}" if matched_media else "，未找到匹配的媒体"
            ),
        }
