# -*- coding: utf-8 -*-
"""
演职员关系回填处理器

将已识别的电影/电视剧中 JSON 列（actors/directors/creators）的数据
回填到 movie_credits / tv_series_credits 关联表中。
"""
import logging
from typing import Dict, Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.unified_movie import UnifiedMovie
from app.models.unified_person import MovieCredit, TVSeriesCredit
from app.models.unified_tv_series import UnifiedTVSeries
from app.services.identification.person_service import PersonService
from app.services.task.task_execution_service import TaskExecutionService
from app.tasks.base import BaseTaskHandler

logger = logging.getLogger(__name__)


class CreditsBackfillHandler(BaseTaskHandler):
    """演职员关系回填处理器"""

    @staticmethod
    async def execute(
        db: AsyncSession,
        params: Dict[str, Any],
        execution_id: int,
    ) -> Dict[str, Any]:
        """
        执行演职员关系回填

        Args:
            db: 数据库会话
            params: 处理器参数
                - limit: 每次处理的最大数量 (默认 100)
                - source: 元数据来源过滤 ("tmdb" / "douban"，为空则不过滤)
            execution_id: 任务执行ID

        Returns:
            回填结果
        """
        limit = params.get("limit", 100)
        source = params.get("source")  # None 表示不过滤

        source_desc = f"来源: {source}" if source else "来源: 全部"
        await TaskExecutionService.append_log(
            db, execution_id,
            f"开始演职员关系回填，限制: {limit} 条，{source_desc}"
        )

        # 回填电影
        movie_result = await CreditsBackfillHandler._backfill_movies(
            db, execution_id, limit, source
        )

        await TaskExecutionService.update_progress(db, execution_id, 50)

        # 回填电视剧
        tv_result = await CreditsBackfillHandler._backfill_tv(
            db, execution_id, limit, source
        )

        await TaskExecutionService.update_progress(db, execution_id, 100)

        total_success = movie_result["success"] + tv_result["success"]
        total_failed = movie_result["failed"] + tv_result["failed"]
        total_skipped = movie_result["skipped"] + tv_result["skipped"]

        await TaskExecutionService.append_log(
            db,
            execution_id,
            f"演职员关系回填完成: "
            f"电影 {movie_result['success']}/{movie_result['total']}，"
            f"电视剧 {tv_result['success']}/{tv_result['total']}，"
            f"共成功 {total_success}，跳过 {total_skipped}，失败 {total_failed}"
        )

        return {
            "movies": movie_result,
            "tv_series": tv_result,
            "total_success": total_success,
            "total_failed": total_failed,
            "total_skipped": total_skipped,
        }

    @staticmethod
    async def _backfill_movies(
        db: AsyncSession,
        execution_id: int,
        limit: int,
        source: Optional[str] = None,
    ) -> Dict[str, Any]:
        """回填电影演职员关系"""
        # 查找有 actors 数据但 movie_credits 中无记录的电影
        credits_count_subq = (
            select(
                MovieCredit.movie_id,
                func.count(MovieCredit.id).label("credit_count"),
            )
            .group_by(MovieCredit.movie_id)
            .subquery()
        )

        conditions = [
            UnifiedMovie.actors.isnot(None),
            (credits_count_subq.c.credit_count.is_(None))
            | (credits_count_subq.c.credit_count == 0),
        ]

        if source:
            conditions.append(UnifiedMovie.metadata_source == source)

        stmt = (
            select(UnifiedMovie)
            .outerjoin(
                credits_count_subq,
                UnifiedMovie.id == credits_count_subq.c.movie_id,
            )
            .where(*conditions)
            .order_by(UnifiedMovie.id.asc())
            .limit(limit)
        )

        result = await db.execute(stmt)
        movies = result.scalars().all()

        # 预提取所有数据，避免 commit 后 lazy load 导致 greenlet 错误
        movie_data_list = [
            {
                "id": m.id,
                "title": m.title,
                "actors": m.actors or [],
                "directors": m.directors or [],
            }
            for m in movies
        ]

        total = len(movie_data_list)
        success = 0
        failed = 0
        skipped = 0
        errors = []

        await TaskExecutionService.append_log(
            db, execution_id, f"找到 {total} 部电影需要回填演职员关系"
        )

        for data in movie_data_list:
            try:
                if not data["actors"] and not data["directors"]:
                    skipped += 1
                    continue

                # 重新加载 movie 对象（commit 后原对象已 expired）
                movie = await db.get(UnifiedMovie, data["id"])
                if not movie:
                    skipped += 1
                    continue

                credits_data = {
                    "actors": data["actors"],
                    "directors": data["directors"],
                    "writers": [],
                }
                await PersonService.sync_movie_credits(db, movie, credits_data)
                success += 1
            except Exception as e:
                failed += 1
                errors.append(f"电影 {data['id']} ({data['title']}): {str(e)}")
                logger.error(f"Backfill credits for movie {data['id']} failed: {e}")
                await db.rollback()

        if errors:
            for err in errors[:10]:
                await TaskExecutionService.append_log(db, execution_id, f"  错误: {err}")

        return {
            "total": total,
            "success": success,
            "failed": failed,
            "skipped": skipped,
        }

    @staticmethod
    async def _backfill_tv(
        db: AsyncSession,
        execution_id: int,
        limit: int,
        source: Optional[str] = None,
    ) -> Dict[str, Any]:
        """回填电视剧演职员关系"""
        credits_count_subq = (
            select(
                TVSeriesCredit.tv_series_id,
                func.count(TVSeriesCredit.id).label("credit_count"),
            )
            .group_by(TVSeriesCredit.tv_series_id)
            .subquery()
        )

        conditions = [
            UnifiedTVSeries.actors.isnot(None),
            (credits_count_subq.c.credit_count.is_(None))
            | (credits_count_subq.c.credit_count == 0),
        ]

        if source:
            conditions.append(UnifiedTVSeries.metadata_source == source)

        stmt = (
            select(UnifiedTVSeries)
            .outerjoin(
                credits_count_subq,
                UnifiedTVSeries.id == credits_count_subq.c.tv_series_id,
            )
            .where(*conditions)
            .order_by(UnifiedTVSeries.id.asc())
            .limit(limit)
        )

        result = await db.execute(stmt)
        tv_list = result.scalars().all()

        # 预提取所有数据，避免 commit 后 lazy load 导致 greenlet 错误
        tv_data_list = [
            {
                "id": t.id,
                "title": t.title,
                "actors": t.actors or [],
                "directors": t.directors or [],
                "creators": t.creators or [],
            }
            for t in tv_list
        ]

        total = len(tv_data_list)
        success = 0
        failed = 0
        skipped = 0
        errors = []

        await TaskExecutionService.append_log(
            db, execution_id, f"找到 {total} 部电视剧需要回填演职员关系"
        )

        for data in tv_data_list:
            try:
                if not data["actors"] and not data["directors"] and not data["creators"]:
                    skipped += 1
                    continue

                tv = await db.get(UnifiedTVSeries, data["id"])
                if not tv:
                    skipped += 1
                    continue

                credits_data = {
                    "actors": data["actors"],
                    "directors": data["directors"],
                    "creators": data["creators"],
                }
                await PersonService.sync_tv_credits(db, tv, credits_data)
                success += 1
            except Exception as e:
                failed += 1
                errors.append(f"电视剧 {data['id']} ({data['title']}): {str(e)}")
                logger.error(f"Backfill credits for TV {data['id']} failed: {e}")
                await db.rollback()

        if errors:
            for err in errors[:10]:
                await TaskExecutionService.append_log(db, execution_id, f"  错误: {err}")

        return {
            "total": total,
            "success": success,
            "failed": failed,
            "skipped": skipped,
        }
