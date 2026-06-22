# -*- coding: utf-8 -*-
"""
媒体库健康检查工具（只读）

诊断媒体库的识别质量与元数据完整性，是「磁盘诊断」的自然延伸——
后者关注存储/链接，本工具关注「库里的条目是否完整、是否识别正确」。

纯数据库查询（不触碰文件系统），快速给出体检报告：
1. unidentified  ：媒体文件未关联到任何统一资源（缺识别）
2. failed        ：处理流程失败的媒体文件（带错误信息）
3. low_confidence：识别置信度偏低，可能误匹配
4. metadata      ：被媒体文件引用、但缺海报/简介/评分/TMDB ID 的统一条目

断链 / 失效硬链接请用 disk_diagnose（check=broken_links）。
"""
import logging
from typing import Any, Dict, List

from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import (
    MEDIA_FILE_STATUS_DELETED,
    MEDIA_FILE_STATUS_FAILED,
    MEDIA_FILE_STATUS_IGNORED,
)
from app.constants.ai_agent import AGENT_TOOL_MEDIA_HEALTH
from app.models import MediaFile, UnifiedMovie, UnifiedTVSeries
from app.services.ai_agent.tool_registry import BaseTool, register_tool

logger = logging.getLogger(__name__)

_DEFAULT_SAMPLE = 20
_MAX_SAMPLE = 100
_LOW_CONFIDENCE_THRESHOLD = 60
# 统一资源表名（与 media_files.unified_table_name 写入值一致）
_TABLE_MOVIES = "unified_movies"
_TABLE_TV = "unified_tv_series"


@register_tool
class MediaHealthTool(BaseTool):
    """媒体库健康检查（只读）"""

    name = AGENT_TOOL_MEDIA_HEALTH
    description = (
        "媒体库健康体检（只读，不修改数据）。"
        "check=unidentified 统计未识别（未关联统一资源）的媒体文件；"
        "check=failed 统计处理失败的媒体文件及错误；"
        "check=low_confidence 统计识别置信度偏低、可能误匹配的文件；"
        "check=metadata 统计已入库但缺海报/简介/评分/TMDB ID 的影视条目；"
        "check=all 全部执行。适合回答「媒体库有没有问题」「哪些没识别/缺元数据」。"
        "注意：断链/失效链接请用 disk_diagnose。"
    )

    parameters = {
        "type": "object",
        "properties": {
            "check": {
                "type": "string",
                "description": "体检项，默认 all",
                "enum": ["all", "unidentified", "failed", "low_confidence", "metadata"],
                "default": "all",
            },
            "limit": {
                "type": "integer",
                "description": "每项返回的明细样本数，默认 20，最大 100",
                "default": _DEFAULT_SAMPLE,
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
        check = arguments.get("check", "all")
        try:
            limit = min(max(int(arguments.get("limit", _DEFAULT_SAMPLE)), 1), _MAX_SAMPLE)
        except (TypeError, ValueError):
            limit = _DEFAULT_SAMPLE

        checks: Dict[str, Any] = {}
        warnings: List[str] = []

        if check in ("all", "unidentified"):
            checks["unidentified"] = await cls._check_unidentified(db, limit, warnings)
        if check in ("all", "failed"):
            checks["failed"] = await cls._check_failed(db, limit, warnings)
        if check in ("all", "low_confidence"):
            checks["low_confidence"] = await cls._check_low_confidence(db, limit, warnings)
        if check in ("all", "metadata"):
            checks["metadata"] = await cls._check_metadata(db, limit, warnings)

        return {
            "success": True,
            "checks": checks,
            "has_warnings": bool(warnings),
            "warnings": warnings,
            "message": (
                f"体检完成，发现 {len(warnings)} 项需关注：{'；'.join(warnings)}"
                if warnings
                else "体检完成，媒体库状态良好，未发现明显问题"
            ),
            "note": "本工具只读；可用资源识别 / 元数据刮削相关功能修复发现的问题。",
        }

    # ==================== 各体检项 ====================

    @classmethod
    async def _count(cls, db: AsyncSession, condition) -> int:
        result = await db.execute(
            select(func.count()).select_from(MediaFile).where(condition)
        )
        return result.scalar() or 0

    @classmethod
    async def _check_unidentified(
        cls, db: AsyncSession, limit: int, warnings: List[str]
    ) -> Dict[str, Any]:
        # 未关联统一资源、且不属于已忽略/已删除的文件
        condition = and_(
            MediaFile.unified_resource_id.is_(None),
            MediaFile.status.notin_([MEDIA_FILE_STATUS_IGNORED, MEDIA_FILE_STATUS_DELETED]),
        )
        total = await cls._count(db, condition)
        result = await db.execute(
            select(MediaFile).where(condition).order_by(MediaFile.id.desc()).limit(limit)
        )
        samples = [
            {"id": f.id, "name": f.file_name, "status": f.status, "attempts": f.match_attempts}
            for f in result.scalars().all()
        ]
        if total:
            warnings.append(f"未识别媒体文件 {total} 个")
        return {"count": total, "samples": samples}

    @classmethod
    async def _check_failed(
        cls, db: AsyncSession, limit: int, warnings: List[str]
    ) -> Dict[str, Any]:
        condition = MediaFile.status == MEDIA_FILE_STATUS_FAILED
        total = await cls._count(db, condition)
        result = await db.execute(
            select(MediaFile).where(condition).order_by(MediaFile.id.desc()).limit(limit)
        )
        samples = [
            {
                "id": f.id,
                "name": f.file_name,
                "error_step": f.error_step,
                "error": (f.error_message or "")[:200],
            }
            for f in result.scalars().all()
        ]
        if total:
            warnings.append(f"处理失败媒体文件 {total} 个")
        return {"count": total, "samples": samples}

    @classmethod
    async def _check_low_confidence(
        cls, db: AsyncSession, limit: int, warnings: List[str]
    ) -> Dict[str, Any]:
        # 已识别但置信度偏低，可能误匹配
        condition = and_(
            MediaFile.unified_resource_id.isnot(None),
            MediaFile.match_confidence.isnot(None),
            MediaFile.match_confidence < _LOW_CONFIDENCE_THRESHOLD,
        )
        total = await cls._count(db, condition)
        result = await db.execute(
            select(MediaFile)
            .where(condition)
            .order_by(MediaFile.match_confidence.asc())
            .limit(limit)
        )
        samples = [
            {
                "id": f.id,
                "name": f.file_name,
                "confidence": f.match_confidence,
                "match_method": f.match_method,
            }
            for f in result.scalars().all()
        ]
        if total:
            warnings.append(f"低置信度识别 {total} 个（阈值 {_LOW_CONFIDENCE_THRESHOLD}）")
        return {
            "count": total,
            "threshold": _LOW_CONFIDENCE_THRESHOLD,
            "samples": samples,
        }

    @classmethod
    async def _check_metadata(
        cls, db: AsyncSession, limit: int, warnings: List[str]
    ) -> Dict[str, Any]:
        movies = await cls._scan_metadata(db, UnifiedMovie, _TABLE_MOVIES, limit)
        tv = await cls._scan_metadata(db, UnifiedTVSeries, _TABLE_TV, limit)
        total = movies["count"] + tv["count"]
        if total:
            warnings.append(f"元数据缺失条目 {total} 个（电影 {movies['count']}，剧集 {tv['count']}）")
        return {"count": total, "movies": movies, "tv_series": tv}

    @classmethod
    async def _scan_metadata(
        cls, db: AsyncSession, model, table_name: str, limit: int
    ) -> Dict[str, Any]:
        """统计「被媒体文件引用、但缺关键元数据」的统一条目。"""
        referenced = exists().where(
            and_(
                MediaFile.unified_table_name == table_name,
                MediaFile.unified_resource_id == model.id,
            )
        )
        missing = or_(
            model.poster_url.is_(None),
            model.overview.is_(None),
            model.tmdb_id.is_(None),
            and_(model.rating_douban.is_(None), model.rating_tmdb.is_(None)),
        )
        condition = and_(referenced, missing)

        count_result = await db.execute(
            select(func.count()).select_from(model).where(condition)
        )
        total = count_result.scalar() or 0

        result = await db.execute(
            select(model).where(condition).order_by(model.id.desc()).limit(limit)
        )
        samples = []
        for r in result.scalars().all():
            missing_fields = []
            if r.poster_url is None:
                missing_fields.append("海报")
            if r.overview is None:
                missing_fields.append("简介")
            if r.tmdb_id is None:
                missing_fields.append("TMDB ID")
            if r.rating_douban is None and r.rating_tmdb is None:
                missing_fields.append("评分")
            samples.append({
                "id": r.id,
                "title": r.title,
                "year": r.year,
                "missing": missing_fields,
            })
        return {"count": total, "samples": samples}
