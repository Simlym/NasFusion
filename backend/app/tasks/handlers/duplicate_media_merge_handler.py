# -*- coding: utf-8 -*-
"""
重复影视合并处理器

合并策略：按 title + year 分组，找到相同名称和年份的重复记录进行合并。
同时支持电影（UnifiedMovie）和剧集（UnifiedTVSeries）。

主记录选择优先级：
1. 有 tmdb_id 的记录（tmdb_id 越小越优先）
2. 有 douban_id 的记录（douban_id 越小越优先）
3. ID 最小的记录

字段合并：
- 外部ID：合并所有非空ID到主记录
- 评分/文本字段：主记录为空时用副记录补充
- 数组字段：合并去重
- PT资源统计：取最大值
- 布尔标志：任一为 True 则为 True

同时更新 resource_mappings 指向保留的主记录，删除副记录。
"""
import logging
from typing import Dict, Any, List, Optional, Type

from sqlalchemy import func, select, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.unified_movie import UnifiedMovie
from app.models.unified_tv_series import UnifiedTVSeries
from app.models.resource_mapping import ResourceMapping
from app.services.task.task_execution_service import TaskExecutionService
from app.tasks.base import BaseTaskHandler
from app.utils.timezone import now
from app.utils.metadata_normalization import MetadataNormalizer

logger = logging.getLogger(__name__)


class DuplicateMediaMergeHandler(BaseTaskHandler):
    """重复影视合并处理器"""

    @staticmethod
    async def execute(
        db: AsyncSession,
        params: Dict[str, Any],
        execution_id: int,
    ) -> Dict[str, Any]:
        """
        执行重复影视合并

        Args:
            db: 数据库会话
            params: 处理器参数
                - dry_run: 是否仅预览不实际执行 (默认 False)
                - media_type: 合并类型 "movie"/"tv"/"all" (默认 "all")
                - limit: 最大处理分组数 (默认 100)
            execution_id: 任务执行ID
        """
        dry_run = params.get("dry_run", False)
        media_type = params.get("media_type", "all")
        limit = params.get("limit", 100)

        mode_desc = "预览模式" if dry_run else "执行模式"
        await TaskExecutionService.append_log(
            db, execution_id,
            f"开始重复影视合并 ({mode_desc})，类型: {media_type}，最大处理分组: {limit}"
        )

        results = {
            "dry_run": dry_run,
            "movies": {"total_groups": 0, "merged": 0, "failed": 0, "records_removed": 0, "mappings_updated": 0},
            "tv_series": {"total_groups": 0, "merged": 0, "failed": 0, "records_removed": 0, "mappings_updated": 0},
            "errors": [],
        }

        # 处理电影
        if media_type in ("movie", "all"):
            movie_result = await DuplicateMediaMergeHandler._merge_for_model(
                db, UnifiedMovie, "unified_movies", "电影", dry_run, limit, execution_id
            )
            results["movies"] = movie_result
            if movie_result.get("errors"):
                results["errors"].extend(movie_result["errors"])

        # 处理剧集
        if media_type in ("tv", "all"):
            tv_result = await DuplicateMediaMergeHandler._merge_for_model(
                db, UnifiedTVSeries, "unified_tv_series", "剧集", dry_run, limit, execution_id
            )
            results["tv_series"] = tv_result
            if tv_result.get("errors"):
                results["errors"].extend(tv_result["errors"])

        # 汇总日志
        movie = results["movies"]
        tv = results["tv_series"]
        await TaskExecutionService.append_log(
            db, execution_id,
            f"重复影视合并完成 ({mode_desc}): "
            f"电影 {movie['merged']}/{movie['total_groups']} 组，删除 {movie['records_removed']} 条；"
            f"剧集 {tv['merged']}/{tv['total_groups']} 组，删除 {tv['records_removed']} 条"
        )

        await TaskExecutionService.update_progress(db, execution_id, 100)

        return results

    @staticmethod
    async def _merge_for_model(
        db: AsyncSession,
        model_class: Type,
        table_name: str,
        label: str,
        dry_run: bool,
        limit: int,
        execution_id: int,
    ) -> Dict[str, Any]:
        """对指定模型执行合并"""
        # 1. 查找重复分组
        duplicate_groups = await DuplicateMediaMergeHandler._find_duplicate_groups(
            db, model_class, limit
        )

        total_groups = len(duplicate_groups)
        await TaskExecutionService.append_log(
            db, execution_id,
            f"{label}: 发现 {total_groups} 组重复记录"
        )

        if total_groups == 0:
            return {
                "total_groups": 0, "merged": 0, "failed": 0,
                "records_removed": 0, "mappings_updated": 0, "errors": [],
            }

        merged = 0
        failed = 0
        records_removed = 0
        mappings_updated = 0
        errors = []

        for idx, (title, year, count) in enumerate(duplicate_groups):
            try:
                result = await DuplicateMediaMergeHandler._merge_group(
                    db, model_class, table_name, title, year, dry_run, execution_id
                )
                merged += 1
                records_removed += result["records_removed"]
                mappings_updated += result["mappings_updated"]
            except Exception as e:
                failed += 1
                error_msg = f"{label}合并失败 {title} ({year}): {e}"
                errors.append(error_msg)
                logger.error(error_msg, exc_info=True)
                if not dry_run:
                    await db.rollback()

            progress = int((idx + 1) / total_groups * 50)
            await TaskExecutionService.update_progress(db, execution_id, progress)

        return {
            "total_groups": total_groups,
            "merged": merged,
            "failed": failed,
            "records_removed": records_removed,
            "mappings_updated": mappings_updated,
            "errors": errors[:20],
        }

    @staticmethod
    async def _find_duplicate_groups(
        db: AsyncSession,
        model_class: Type,
        limit: int,
    ) -> list:
        """按 title + year 查找重复分组"""
        query = (
            select(
                model_class.title,
                model_class.year,
                func.count().label("count"),
            )
            .group_by(model_class.title, model_class.year)
            .having(func.count() > 1)
            .order_by(func.count().desc())
            .limit(limit)
        )
        result = await db.execute(query)
        return result.all()

    @staticmethod
    async def _get_duplicates(
        db: AsyncSession,
        model_class: Type,
        title: str,
        year: Optional[int],
    ) -> list:
        """获取指定 title+year 的所有重复记录，按优先级排序"""
        conditions = [model_class.title == title]
        if year is not None:
            conditions.append(model_class.year == year)
        else:
            conditions.append(model_class.year.is_(None))

        query = (
            select(model_class)
            .where(and_(*conditions))
            .order_by(
                model_class.tmdb_id.asc().nulls_last(),
                model_class.douban_id.asc().nulls_last(),
                model_class.id.asc(),
            )
        )
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def _merge_group(
        db: AsyncSession,
        model_class: Type,
        table_name: str,
        title: str,
        year: Optional[int],
        dry_run: bool,
        execution_id: int,
    ) -> Dict[str, Any]:
        """合并一组重复记录"""
        records = await DuplicateMediaMergeHandler._get_duplicates(
            db, model_class, title, year
        )
        if len(records) < 2:
            return {"records_removed": 0, "mappings_updated": 0}

        primary = records[0]
        duplicates = records[1:]
        duplicate_ids = [d.id for d in duplicates]

        log_msg = (
            f"{'[预览] ' if dry_run else ''}合并 {title} ({year}): "
            f"主记录 ID={primary.id} <- 副记录 IDs={duplicate_ids}"
        )
        await TaskExecutionService.append_log(db, execution_id, log_msg)

        if dry_run:
            return {"records_removed": len(duplicates), "mappings_updated": 0}

        # 1. 合并元数据
        updates = DuplicateMediaMergeHandler._merge_metadata(primary, duplicates)

        # 2. 清除与其他记录冲突的外部ID
        await DuplicateMediaMergeHandler._clear_conflicting_ids(
            db, model_class, primary.id, duplicate_ids, updates, execution_id
        )

        # 3. 更新主记录
        if updates:
            for key, value in updates.items():
                setattr(primary, key, value)
            primary.updated_at = now()

        # 4. 更新 resource_mappings
        mappings_count = await DuplicateMediaMergeHandler._update_resource_mappings(
            db, table_name, primary.id, duplicate_ids
        )

        # 5. 删除副记录
        for dup_id in duplicate_ids:
            await db.execute(
                delete(model_class).where(model_class.id == dup_id)
            )

        await db.commit()

        return {"records_removed": len(duplicate_ids), "mappings_updated": mappings_count}

    @staticmethod
    def _merge_metadata(primary, others: list) -> dict:
        """
        合并元数据，主记录的空字段用副记录补充

        策略：
        1. 外部ID：补充主记录缺失的ID
        2. 评分：主记录为空时使用副记录值
        3. 文本字段：主记录为空时使用副记录值
        4. 数组字段：合并去重
        5. PT资源统计：取最大值
        """
        updates = {}

        # 1. 合并外部ID
        for record in others:
            if record.tmdb_id and not primary.tmdb_id:
                updates['tmdb_id'] = record.tmdb_id
            if record.douban_id and not primary.douban_id:
                updates['douban_id'] = record.douban_id
            if record.imdb_id and not primary.imdb_id:
                updates['imdb_id'] = record.imdb_id
            # TV Series 特有字段
            if hasattr(record, 'tvdb_id') and record.tvdb_id and not getattr(primary, 'tvdb_id', None):
                updates['tvdb_id'] = record.tvdb_id

        # 2. 合并评分
        rating_fields = ['rating_tmdb', 'rating_douban', 'rating_imdb']
        if hasattr(primary, 'votes_tmdb'):
            rating_fields.extend(['votes_tmdb', 'votes_douban', 'votes_imdb'])
        else:
            rating_fields.extend(['votes_count'])

        for record in others:
            for field in rating_fields:
                if hasattr(record, field):
                    val = getattr(record, field)
                    if val and not getattr(primary, field):
                        updates[field] = val

        # 3. 合并文本字段
        text_fields = ['original_title', 'overview', 'tagline']
        for field in text_fields:
            if not getattr(primary, field):
                for record in others:
                    val = getattr(record, field)
                    if val:
                        updates[field] = val
                        break

        # 4. 合并数组字段（标准化去重）
        array_fields_with_type = [
            ('genres', None),
            ('tags', None),
            ('languages', 'language'),
            ('countries', 'country'),
            ('aka', None),
        ]
        # TV Series 特有
        if hasattr(primary, 'networks'):
            array_fields_with_type.append(('networks', None))

        for field, field_type in array_fields_with_type:
            if not hasattr(primary, field):
                continue
            primary_val = getattr(primary, field)

            if not primary_val or len(primary_val) == 0:
                for record in others:
                    val = getattr(record, field)
                    if val and isinstance(val, list) and len(val) > 0:
                        normalized = DuplicateMediaMergeHandler._normalize_and_deduplicate(val, field_type)
                        if normalized:
                            updates[field] = normalized
                        break
            else:
                merged = list(primary_val)
                for record in others:
                    val = getattr(record, field)
                    if val and isinstance(val, list):
                        merged.extend(val)
                normalized = DuplicateMediaMergeHandler._normalize_and_deduplicate(merged, field_type)
                if normalized != primary_val:
                    updates[field] = normalized

        # 5. 合并人员信息
        person_fields = ['directors', 'actors', 'writers']
        # TV Series 特有
        if hasattr(primary, 'creators'):
            person_fields.append('creators')

        for field in person_fields:
            if not hasattr(primary, field):
                continue
            primary_val = getattr(primary, field)
            if not primary_val or len(primary_val) == 0:
                for record in others:
                    val = getattr(record, field)
                    if val and isinstance(val, list) and len(val) > 0:
                        updates[field] = val
                        break
            else:
                merged = list(primary_val)
                seen_ids = set()
                for person in primary_val:
                    person_id = person.get('id') or person.get('name')
                    if person_id:
                        seen_ids.add(person_id)
                for record in others:
                    val = getattr(record, field)
                    if val and isinstance(val, list):
                        for person in val:
                            person_id = person.get('id') or person.get('name')
                            if person_id and person_id not in seen_ids:
                                merged.append(person)
                                seen_ids.add(person_id)
                if merged != primary_val:
                    updates[field] = merged

        # 6. 合并图片URL
        image_fields = ['poster_url', 'backdrop_url', 'logo_url', 'clearart_url', 'banner_url']
        for field in image_fields:
            if not getattr(primary, field):
                for record in others:
                    val = getattr(record, field)
                    if val:
                        updates[field] = val
                        break

        # 7. 合并PT资源统计（取最大值）
        all_records = [primary] + others
        for field in ['pt_resource_count', 'best_seeder_count', 'local_file_count']:
            if not hasattr(primary, field):
                continue
            max_val = max((getattr(r, field) or 0 for r in all_records), default=0)
            if max_val > (getattr(primary, field) or 0):
                updates[field] = max_val

        # 8. 合并布尔标志
        for field in ['has_free_resource', 'has_local', 'detail_loaded']:
            if not hasattr(primary, field):
                continue
            if any(getattr(r, field) for r in all_records):
                if not getattr(primary, field):
                    updates[field] = True

        # 9. 其他字段
        other_fields = ['certification', 'metadata_source', 'best_quality', 'local_images_dir']
        # Movie 特有
        if hasattr(primary, 'runtime'):
            other_fields.extend(['runtime', 'collection_id', 'collection_name', 'budget', 'revenue',
                                 'production_companies', 'status', 'release_date'])
        # TV Series 特有
        if hasattr(primary, 'number_of_seasons'):
            other_fields.extend(['number_of_seasons', 'number_of_episodes', 'status',
                                 'type', 'first_air_date', 'last_air_date',
                                 'episode_runtime', 'production_companies', 'content_ratings',
                                 'seasons_info'])

        for field in other_fields:
            if not hasattr(primary, field):
                continue
            if not getattr(primary, field):
                for record in others:
                    val = getattr(record, field)
                    if val:
                        updates[field] = val
                        break

        return updates

    @staticmethod
    def _normalize_and_deduplicate(items: list, field_type: str = None) -> list:
        """标准化并去重列表"""
        if not items:
            return []

        normalized = []
        seen = set()

        for item in items:
            if not item:
                continue

            if field_type == 'language':
                normalized_item = MetadataNormalizer.normalize_language(item)
            elif field_type == 'country':
                normalized_item = MetadataNormalizer.normalize_country(item)
            else:
                normalized_item = item

            item_key = normalized_item.lower() if isinstance(normalized_item, str) else str(normalized_item)
            if item_key not in seen:
                normalized.append(normalized_item)
                seen.add(item_key)

        return normalized

    @staticmethod
    async def _clear_conflicting_ids(
        db: AsyncSession,
        model_class: Type,
        primary_id: int,
        duplicate_ids: list,
        updates: dict,
        execution_id: int,
    ):
        """清除与其他记录冲突的外部ID"""
        external_id_fields = ['tmdb_id', 'douban_id', 'imdb_id']
        if hasattr(model_class, 'tvdb_id'):
            external_id_fields.append('tvdb_id')

        exclude_ids = [primary_id] + duplicate_ids

        for field in external_id_fields:
            if field not in updates:
                continue
            new_value = updates[field]
            if not new_value:
                continue

            query = select(model_class).where(
                and_(
                    getattr(model_class, field) == new_value,
                    ~model_class.id.in_(exclude_ids),
                )
            )
            result = await db.execute(query)
            conflicting = result.scalars().all()

            for record in conflicting:
                await TaskExecutionService.append_log(
                    db, execution_id,
                    f"  清除冲突: ID={record.id} 的 {field}={new_value}"
                )
                setattr(record, field, None)
                record.updated_at = now()

    @staticmethod
    async def _update_resource_mappings(
        db: AsyncSession,
        table_name: str,
        primary_id: int,
        duplicate_ids: list,
    ) -> int:
        """更新 resource_mappings 指向主记录"""
        count = 0
        for dup_id in duplicate_ids:
            query = select(ResourceMapping).where(
                and_(
                    ResourceMapping.unified_table_name == table_name,
                    ResourceMapping.unified_resource_id == dup_id,
                )
            )
            result = await db.execute(query)
            mappings = result.scalars().all()

            for mapping in mappings:
                mapping.unified_resource_id = primary_id
                count += 1

        return count
