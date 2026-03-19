# -*- coding: utf-8 -*-
"""
重复人物合并处理器

合并策略一: detail_loaded=True 且 name+birthday 相同的记录进行合并
合并策略二: name + profile_url 相同的记录进行合并（适用于未加载详情但头像URL一致的情况）

同时迁移 movie_credits 和 tv_series_credits。

主记录选择优先级:
- 优先保留 birthday 或 place_of_birth 有值的记录
- 其次优先保留有 douban_id 的记录
- 再次优先保留有 tmdb_id 的记录
- 最后选 id 较小的

字段合并:
- 将副记录的 ID（tmdb_id/douban_id/imdb_id）补充到主记录
- 迁移副记录的演职表到主记录（处理冲突）
- 删除副记录
"""
import logging
from typing import Dict, Any, List, Optional

from sqlalchemy import func, select, update, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.unified_person import UnifiedPerson, MovieCredit, TVSeriesCredit
from app.services.task.task_execution_service import TaskExecutionService
from app.tasks.base import BaseTaskHandler
from app.utils.timezone import now

logger = logging.getLogger(__name__)


class PersonMergeHandler(BaseTaskHandler):
    """重复人物合并处理器"""

    @staticmethod
    async def execute(
        db: AsyncSession,
        params: Dict[str, Any],
        execution_id: int,
    ) -> Dict[str, Any]:
        """
        执行重复人物合并

        Args:
            db: 数据库会话
            params: 处理器参数
                - dry_run: 是否仅预览不实际执行 (默认 False)
                - limit: 最大处理分组数 (默认 100)
            execution_id: 任务执行ID

        Returns:
            合并结果
        """
        dry_run = params.get("dry_run", False)
        limit = params.get("limit", 100)

        mode_desc = "预览模式" if dry_run else "执行模式"
        await TaskExecutionService.append_log(
            db, execution_id,
            f"开始重复人物合并 ({mode_desc})，最大处理分组: {limit}"
        )

        # 1. 查找重复分组
        # 策略一: detail_loaded=True, birthday IS NOT NULL, 同名同生日有多条
        birthday_groups = await PersonMergeHandler._find_birthday_duplicate_groups(db, limit)
        await TaskExecutionService.append_log(
            db, execution_id,
            f"策略一（同名+同生日）: 发现 {len(birthday_groups)} 组重复人物"
        )

        # 策略二: 同名 + 同头像URL 有多条
        profile_groups = await PersonMergeHandler._find_profile_url_duplicate_groups(db, limit)
        await TaskExecutionService.append_log(
            db, execution_id,
            f"策略二（同名+同头像）: 发现 {len(profile_groups)} 组重复人物"
        )

        # 合并去重：将两种策略的分组合并（避免重复处理同一组人）
        seen_keys = set()
        duplicate_groups = []
        for g in birthday_groups:
            key = (g["name"], g.get("birthday"), g.get("profile_url"))
            if key not in seen_keys:
                seen_keys.add(key)
                duplicate_groups.append(g)
        for g in profile_groups:
            key = (g["name"], g.get("birthday"), g.get("profile_url"))
            if key not in seen_keys:
                seen_keys.add(key)
                duplicate_groups.append(g)

        total_groups = len(duplicate_groups)
        if total_groups == 0:
            await TaskExecutionService.append_log(
                db, execution_id, "未发现重复人物记录"
            )
            await TaskExecutionService.update_progress(db, execution_id, 100)
            return {
                "total_groups": 0,
                "merged": 0,
                "failed": 0,
                "records_removed": 0,
                "credits_migrated": 0,
                "dry_run": dry_run,
            }

        await TaskExecutionService.append_log(
            db, execution_id, f"合计 {total_groups} 组重复人物（去重后）"
        )

        merged = 0
        failed = 0
        records_removed = 0
        credits_migrated = 0
        errors = []

        for idx, group in enumerate(duplicate_groups):
            try:
                result = await PersonMergeHandler._merge_group(
                    db, group, dry_run, execution_id
                )
                if result["success"]:
                    merged += 1
                    records_removed += result["removed"]
                    credits_migrated += result["credits_migrated"]
                else:
                    failed += 1
                    errors.append(result.get("error", "未知错误"))
            except Exception as e:
                failed += 1
                group_desc = group['name']
                if group.get('birthday'):
                    group_desc += f" ({group['birthday']})"
                elif group.get('profile_url'):
                    group_desc += f" (头像: {group['profile_url'][:60]}...)"
                error_msg = f"合并分组 {group_desc} 失败: {e}"
                errors.append(error_msg)
                logger.error(error_msg, exc_info=True)
                await db.rollback()

            # 更新进度
            progress = int((idx + 1) / total_groups * 100)
            await TaskExecutionService.update_progress(db, execution_id, progress)

        # 记录结果日志
        await TaskExecutionService.append_log(
            db, execution_id,
            f"重复人物合并完成 ({mode_desc}): "
            f"共 {total_groups} 组，成功合并 {merged} 组，"
            f"删除 {records_removed} 条副记录，"
            f"迁移 {credits_migrated} 条演职表记录，"
            f"失败 {failed} 组"
        )

        if errors:
            for err in errors[:10]:
                await TaskExecutionService.append_log(
                    db, execution_id, f"  错误: {err}"
                )

        return {
            "total_groups": total_groups,
            "merged": merged,
            "failed": failed,
            "records_removed": records_removed,
            "credits_migrated": credits_migrated,
            "dry_run": dry_run,
            "errors": errors[:20],
        }

    @staticmethod
    async def _find_birthday_duplicate_groups(
        db: AsyncSession, limit: int
    ) -> List[Dict[str, Any]]:
        """
        查找重复人物分组（策略一）

        条件: detail_loaded=True, birthday IS NOT NULL, 同 name+birthday 有 2+ 条记录
        """
        stmt = (
            select(
                UnifiedPerson.name,
                UnifiedPerson.birthday,
                func.count(UnifiedPerson.id).label("cnt"),
            )
            .where(
                UnifiedPerson.detail_loaded == True,
                UnifiedPerson.birthday.isnot(None),
            )
            .group_by(UnifiedPerson.name, UnifiedPerson.birthday)
            .having(func.count(UnifiedPerson.id) >= 2)
            .order_by(func.count(UnifiedPerson.id).desc())
            .limit(limit)
        )

        result = await db.execute(stmt)
        groups = result.all()

        return [
            {
                "name": row.name,
                "birthday": row.birthday,
                "match_type": "birthday",
                "count": row.cnt,
            }
            for row in groups
        ]

    @staticmethod
    async def _find_profile_url_duplicate_groups(
        db: AsyncSession, limit: int
    ) -> List[Dict[str, Any]]:
        """
        查找重复人物分组（策略二）

        条件: name 相同, profile_url 相同且非空, 有 2+ 条记录
        不要求 detail_loaded=True，适用于未加载详情但头像URL一致的场景。
        """
        stmt = (
            select(
                UnifiedPerson.name,
                UnifiedPerson.profile_url,
                func.count(UnifiedPerson.id).label("cnt"),
            )
            .where(
                UnifiedPerson.profile_url.isnot(None),
                UnifiedPerson.profile_url != "",
            )
            .group_by(UnifiedPerson.name, UnifiedPerson.profile_url)
            .having(func.count(UnifiedPerson.id) >= 2)
            .order_by(func.count(UnifiedPerson.id).desc())
            .limit(limit)
        )

        result = await db.execute(stmt)
        groups = result.all()

        return [
            {
                "name": row.name,
                "profile_url": row.profile_url,
                "match_type": "profile_url",
                "count": row.cnt,
            }
            for row in groups
        ]

    @staticmethod
    async def _merge_group(
        db: AsyncSession,
        group: Dict[str, Any],
        dry_run: bool,
        execution_id: int,
    ) -> Dict[str, Any]:
        """
        合并一组重复人物

        主记录选择优先级:
        1. 优先保留 birthday 或 place_of_birth 有值的记录
        2. 其次有 douban_id 的记录（中国用户优先豆瓣）
        3. 再次有 tmdb_id 的记录
        4. id 最小的记录
        """
        name = group["name"]
        match_type = group.get("match_type", "birthday")

        # 根据匹配类型构造查询条件
        if match_type == "birthday":
            birthday = group["birthday"]
            stmt = (
                select(UnifiedPerson)
                .where(
                    UnifiedPerson.name == name,
                    UnifiedPerson.birthday == birthday,
                    UnifiedPerson.detail_loaded == True,
                )
                .order_by(UnifiedPerson.id.asc())
            )
        else:
            # match_type == "profile_url"
            profile_url = group["profile_url"]
            stmt = (
                select(UnifiedPerson)
                .where(
                    UnifiedPerson.name == name,
                    UnifiedPerson.profile_url == profile_url,
                )
                .order_by(UnifiedPerson.id.asc())
            )

        result = await db.execute(stmt)
        persons = result.scalars().all()

        if len(persons) < 2:
            return {"success": True, "removed": 0, "credits_migrated": 0}

        # 选择主记录
        primary = PersonMergeHandler._select_primary(persons)
        secondaries = [p for p in persons if p.id != primary.id]

        # 预提取数据，避免 commit 后 lazy load 问题
        primary_id = primary.id
        primary_name = primary.name
        secondary_ids = [s.id for s in secondaries]
        secondary_data = []
        for s in secondaries:
            secondary_data.append({
                "id": s.id,
                "tmdb_id": s.tmdb_id,
                "imdb_id": s.imdb_id,
                "douban_id": s.douban_id,
                "birthday": s.birthday,
                "deathday": s.deathday,
                "biography": s.biography,
                "gender": s.gender,
                "place_of_birth": s.place_of_birth,
                "homepage": s.homepage,
                "known_for_department": s.known_for_department,
                "popularity": s.popularity,
                "family_info": s.family_info,
                "profile_url": s.profile_url,
                "other_names": s.other_names or [],
                "raw_data": s.raw_data,
                "detail_loaded": s.detail_loaded,
                "detail_loaded_at": s.detail_loaded_at,
                "metadata_source": s.metadata_source,
            })

        log_msg = (
            f"{'[预览] ' if dry_run else ''}合并: {primary_name} "
            f"(主记录 ID={primary_id}) <- "
            f"副记录 IDs={secondary_ids}"
        )
        await TaskExecutionService.append_log(db, execution_id, log_msg)

        if dry_run:
            return {
                "success": True,
                "removed": len(secondaries),
                "credits_migrated": 0,
            }

        total_credits_migrated = 0

        # 重新加载主记录
        primary = await db.get(UnifiedPerson, primary_id)

        # 合并每个副记录
        for sec_info in secondary_data:
            sec_id = sec_info["id"]

            # 合并字段到主记录
            PersonMergeHandler._merge_fields(primary, sec_info)

            # 迁移演职表
            migrated = await PersonMergeHandler._migrate_credits(
                db, primary_id, sec_id
            )
            total_credits_migrated += migrated

            # 删除副记录
            await db.execute(
                delete(UnifiedPerson).where(UnifiedPerson.id == sec_id)
            )

        primary.updated_at = now()
        db.add(primary)
        await db.commit()

        return {
            "success": True,
            "removed": len(secondary_data),
            "credits_migrated": total_credits_migrated,
        }

    @staticmethod
    def _select_primary(persons: List[UnifiedPerson]) -> UnifiedPerson:
        """
        选择主记录

        优先级:
        1. 有 birthday 或 place_of_birth 的记录（信息更完整）
        2. 有 douban_id 的记录（中国用户优先豆瓣）
        3. 有 tmdb_id 的记录
        4. id 最小的记录
        """
        # 优先选有 birthday 或 place_of_birth 的（信息更完整的记录）
        detail_persons = [p for p in persons if p.birthday or p.place_of_birth]
        if detail_persons:
            # 在有详情的记录中，再按 douban_id > tmdb_id > id 排序
            return PersonMergeHandler._select_by_source(detail_persons)

        # 其次按数据来源选择
        return PersonMergeHandler._select_by_source(persons)

    @staticmethod
    def _select_by_source(persons: List[UnifiedPerson]) -> UnifiedPerson:
        """
        根据数据来源选择主记录

        优先级:
        1. 有 douban_id 的记录
        2. 有 tmdb_id 的记录
        3. id 最小的记录
        """
        douban_persons = [p for p in persons if p.douban_id]
        if douban_persons:
            return douban_persons[0]

        tmdb_persons = [p for p in persons if p.tmdb_id]
        if tmdb_persons:
            return tmdb_persons[0]

        return persons[0]

    @staticmethod
    def _merge_fields(
        primary: UnifiedPerson, secondary_data: Dict[str, Any]
    ) -> None:
        """
        将副记录的字段合并到主记录（仅填充主记录缺失的字段）
        """
        # 合并外部 ID
        if secondary_data["tmdb_id"] and not primary.tmdb_id:
            primary.tmdb_id = secondary_data["tmdb_id"]
        if secondary_data["imdb_id"] and not primary.imdb_id:
            primary.imdb_id = secondary_data["imdb_id"]
        if secondary_data["douban_id"] and not primary.douban_id:
            primary.douban_id = secondary_data["douban_id"]

        # 合并基本信息（仅在主记录缺失时填充）
        if secondary_data.get("birthday") and not primary.birthday:
            primary.birthday = secondary_data["birthday"]
        if secondary_data.get("deathday") and not primary.deathday:
            primary.deathday = secondary_data["deathday"]
        if secondary_data["biography"] and not primary.biography:
            primary.biography = secondary_data["biography"]
        if secondary_data["gender"] and not primary.gender:
            primary.gender = secondary_data["gender"]
        if secondary_data["place_of_birth"] and not primary.place_of_birth:
            primary.place_of_birth = secondary_data["place_of_birth"]
        if secondary_data["homepage"] and not primary.homepage:
            primary.homepage = secondary_data["homepage"]
        if secondary_data["known_for_department"] and not primary.known_for_department:
            primary.known_for_department = secondary_data["known_for_department"]
        if secondary_data["popularity"] and not primary.popularity:
            primary.popularity = secondary_data["popularity"]
        if secondary_data["family_info"] and not primary.family_info:
            primary.family_info = secondary_data["family_info"]
        if secondary_data["profile_url"] and not primary.profile_url:
            primary.profile_url = secondary_data["profile_url"]
        if secondary_data.get("detail_loaded") and not primary.detail_loaded:
            primary.detail_loaded = True
            primary.detail_loaded_at = secondary_data.get("detail_loaded_at")
        if secondary_data.get("metadata_source") and not primary.metadata_source:
            primary.metadata_source = secondary_data["metadata_source"]

        # 合并别名（去重）
        existing_aka = primary.other_names or []
        new_aka = secondary_data.get("other_names") or []
        if new_aka:
            merged_aka = list(set(existing_aka + new_aka))
            primary.other_names = merged_aka

    @staticmethod
    async def _migrate_credits(
        db: AsyncSession, primary_id: int, secondary_id: int
    ) -> int:
        """
        将副记录的演职表迁移到主记录

        处理冲突: 如果主记录已有同一部影视+同一职位的 credit，则删除副记录的

        Returns:
            迁移的 credit 条数
        """
        migrated = 0

        # --- 迁移 movie_credits ---
        # 查出副记录的所有 movie credits
        stmt = select(MovieCredit).where(MovieCredit.person_id == secondary_id)
        result = await db.execute(stmt)
        sec_movie_credits = result.scalars().all()

        for credit in sec_movie_credits:
            # 检查主记录是否已有同一部电影+同一职位的 credit
            conflict_stmt = select(MovieCredit).where(
                MovieCredit.person_id == primary_id,
                MovieCredit.movie_id == credit.movie_id,
                MovieCredit.job == credit.job,
            )
            conflict_result = await db.execute(conflict_stmt)
            existing = conflict_result.scalars().first()

            if existing:
                # 冲突: 删除副记录的 credit
                await db.execute(
                    delete(MovieCredit).where(MovieCredit.id == credit.id)
                )
            else:
                # 无冲突: 迁移到主记录
                await db.execute(
                    update(MovieCredit)
                    .where(MovieCredit.id == credit.id)
                    .values(person_id=primary_id)
                )
                migrated += 1

        # --- 迁移 tv_series_credits ---
        stmt = select(TVSeriesCredit).where(
            TVSeriesCredit.person_id == secondary_id
        )
        result = await db.execute(stmt)
        sec_tv_credits = result.scalars().all()

        for credit in sec_tv_credits:
            conflict_stmt = select(TVSeriesCredit).where(
                TVSeriesCredit.person_id == primary_id,
                TVSeriesCredit.tv_series_id == credit.tv_series_id,
                TVSeriesCredit.job == credit.job,
            )
            conflict_result = await db.execute(conflict_stmt)
            existing = conflict_result.scalars().first()

            if existing:
                await db.execute(
                    delete(TVSeriesCredit).where(TVSeriesCredit.id == credit.id)
                )
            else:
                await db.execute(
                    update(TVSeriesCredit)
                    .where(TVSeriesCredit.id == credit.id)
                    .values(person_id=primary_id)
                )
                migrated += 1

        return migrated
