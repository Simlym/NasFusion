# -*- coding: utf-8 -*-
"""
合并重复的 unified_movies 记录

问题场景：
- 同一部电影通过 TMDB 和豆瓣分别识别，创建了2条记录
- 例如：记录A只有tmdb_id，记录B只有douban_id

解决方案：
1. 找到 (title, year) 相同的重复记录组
2. 优先选择有 tmdb_id 的记录作为主记录
3. 主记录的空字段用其他记录（douban）的值覆盖
4. 自动标准化 languages 和 countries 字段（English → 英语）
5. 更新 resource_mappings 指向保留的记录
6. 删除重复记录

使用方法：
    python scripts/merge_duplicate_movies.py [--dry-run] [--verbose]

参数：
    --dry-run: 只分析不执行，预览将要合并的记录
    --verbose: 显示详细日志
"""
import asyncio
import sys
import argparse
from pathlib import Path

# 修复 Windows 控制台编码问题
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 加载环境变量
from dotenv import load_dotenv
env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file)
else:
    print(f"警告: 未找到环境变量文件 {env_file}")

from sqlalchemy import select, and_, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import async_session_local
from app.models.unified_movie import UnifiedMovie
from app.models.resource_mapping import ResourceMapping
from app.utils.timezone import now
from app.utils.metadata_normalization import MetadataNormalizer


class MovieMerger:
    """电影记录合并器"""

    def __init__(self, dry_run=False, verbose=False):
        self.dry_run = dry_run
        self.verbose = verbose
        self.merged_count = 0
        self.deleted_count = 0
        self.updated_mappings_count = 0
        self.failed_count = 0

    def log(self, message: str, level="INFO"):
        """日志输出"""
        if self.verbose or level in ["WARNING", "ERROR"]:
            print(f"[{level}] {message}")

    @staticmethod
    def normalize_and_deduplicate_list(items: list, field_type: str = None) -> list:
        """
        标准化并去重列表

        Args:
            items: 原始列表
            field_type: 字段类型 ('language', 'country', 或 None)

        Returns:
            去重后的列表
        """
        if not items:
            return []

        normalized = []
        seen = set()

        for item in items:
            if not item:
                continue

            # 标准化处理
            if field_type == 'language':
                normalized_item = MetadataNormalizer.normalize_language(item)
            elif field_type == 'country':
                normalized_item = MetadataNormalizer.normalize_country(item)
            else:
                normalized_item = item

            # 去重（不区分大小写）
            item_key = normalized_item.lower() if isinstance(normalized_item, str) else str(normalized_item)
            if item_key not in seen:
                normalized.append(normalized_item)
                seen.add(item_key)

        return normalized

    async def find_duplicate_groups(self, db: AsyncSession):
        """
        找到所有重复的电影组（按 title + year 分组）

        Returns:
            List[Tuple[str, int, int]]: [(title, year, count), ...]
        """
        query = (
            select(
                UnifiedMovie.title,
                UnifiedMovie.year,
                func.count().label("count")
            )
            .group_by(UnifiedMovie.title, UnifiedMovie.year)
            .having(func.count() > 1)
        )
        result = await db.execute(query)
        duplicates = result.all()

        self.log(f"发现 {len(duplicates)} 组重复记录")
        return duplicates

    async def get_duplicate_movies(self, db: AsyncSession, title: str, year: int):
        """
        获取指定 title 和 year 的所有重复记录

        Returns:
            List[UnifiedMovie]: 按优先级排序
                1. 优先：有 tmdb_id 的记录（tmdb_id 越小越优先）
                2. 其次：有 douban_id 的记录（douban_id 越小越优先）
                3. 最后：按 ID 升序排序
        """
        query = (
            select(UnifiedMovie)
            .where(
                and_(
                    UnifiedMovie.title == title,
                    UnifiedMovie.year == year
                )
            )
            .order_by(
                # 优先级1：有 tmdb_id 的记录排在前面（NULL 排最后）
                UnifiedMovie.tmdb_id.asc().nulls_last(),
                # 优先级2：有 douban_id 的记录排在前面（NULL 排最后）
                UnifiedMovie.douban_id.asc().nulls_last(),
                # 优先级3：ID 最小的记录
                UnifiedMovie.id.asc()
            )
        )
        result = await db.execute(query)
        return result.scalars().all()

    def merge_metadata(self, primary: UnifiedMovie, others: list[UnifiedMovie]) -> dict:
        """
        合并元数据，主记录（tmdb_id）的空字段用其他记录（douban）覆盖

        策略：
        1. 外部ID：合并所有非空的ID
        2. 评分：主记录为空时，使用其他记录的值
        3. 文本字段：主记录为空时，使用其他记录的值
        4. 数组字段：主记录为空时，使用其他记录的值；否则合并去重
        5. PT资源统计：取最大值

        优先级：primary（tmdb_id记录）> others（douban记录）
        """
        updates = {}

        # 1. 合并外部ID（补充主记录缺失的ID）
        for record in others:
            if record.tmdb_id and not primary.tmdb_id:
                updates['tmdb_id'] = record.tmdb_id
            if record.douban_id and not primary.douban_id:
                updates['douban_id'] = record.douban_id
            if record.imdb_id and not primary.imdb_id:
                updates['imdb_id'] = record.imdb_id

        # 2. 合并评分（主记录为空时，使用其他记录的值）
        for record in others:
            if record.rating_tmdb and not primary.rating_tmdb:
                updates['rating_tmdb'] = record.rating_tmdb
            if record.rating_douban and not primary.rating_douban:
                updates['rating_douban'] = record.rating_douban
            if record.rating_imdb and not primary.rating_imdb:
                updates['rating_imdb'] = record.rating_imdb
            if record.votes_count and not primary.votes_count:
                updates['votes_count'] = record.votes_count

        # 3. 合并标题和文本字段（主记录为空时，使用其他记录的值）
        for field in ['original_title', 'overview', 'tagline']:
            if not getattr(primary, field):
                for record in others:
                    val = getattr(record, field)
                    if val:
                        updates[field] = val
                        break

        # 4. 合并数组字段（主记录为空时，使用其他记录的值；否则合并去重）
        for field in ['genres', 'tags', 'languages', 'countries', 'aka']:
            primary_val = getattr(primary, field)

            # 确定字段类型（用于标准化）
            field_type = None
            if field == 'languages':
                field_type = 'language'
            elif field == 'countries':
                field_type = 'country'

            if not primary_val or len(primary_val) == 0:
                # 主记录为空，使用第一个非空的其他记录的值
                for record in others:
                    val = getattr(record, field)
                    if val and isinstance(val, list) and len(val) > 0:
                        # 标准化并去重
                        normalized_val = self.normalize_and_deduplicate_list(val, field_type)
                        if normalized_val:
                            updates[field] = normalized_val
                        break
            else:
                # 主记录非空，合并去重
                merged = list(primary_val)  # 从主记录开始
                for record in others:
                    val = getattr(record, field)
                    if val and isinstance(val, list):
                        merged.extend(val)

                # 标准化并去重整个合并后的列表
                normalized_merged = self.normalize_and_deduplicate_list(merged, field_type)
                if normalized_merged != primary_val:
                    updates[field] = normalized_merged

        # 5. 合并人员信息（导演、演员、编剧）- 主记录为空时使用其他记录
        for field in ['directors', 'actors', 'writers']:
            primary_val = getattr(primary, field)
            if not primary_val or len(primary_val) == 0:
                # 主记录为空，使用第一个非空的其他记录的值
                for record in others:
                    val = getattr(record, field)
                    if val and isinstance(val, list) and len(val) > 0:
                        updates[field] = val
                        break
            else:
                # 主记录非空，合并去重（按 id 或 name）
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

        # 6. 合并图片URL（主记录为空时使用其他记录的值）
        for field in ['poster_url', 'backdrop_url', 'logo_url', 'clearart_url', 'banner_url']:
            if not getattr(primary, field):
                for record in others:
                    val = getattr(record, field)
                    if val:
                        updates[field] = val
                        break

        # 7. 合并PT资源统计（取最大值）
        all_records = [primary] + others
        for field in ['pt_resource_count', 'best_seeder_count', 'local_file_count']:
            max_val = max((getattr(r, field) or 0 for r in all_records), default=0)
            if max_val > (getattr(primary, field) or 0):
                updates[field] = max_val

        # 8. 合并布尔标志（任一为True则为True）
        for field in ['has_free_resource', 'has_local', 'detail_loaded']:
            if any(getattr(r, field) for r in all_records):
                if not getattr(primary, field):
                    updates[field] = True

        # 9. 其他字段（主记录为空时使用其他记录的值）
        for field in ['runtime', 'certification', 'collection_id', 'collection_name',
                      'budget', 'revenue', 'production_companies', 'status',
                      'best_quality', 'local_images_dir', 'metadata_source', 'release_date']:
            if not getattr(primary, field):
                for record in others:
                    val = getattr(record, field)
                    if val:
                        updates[field] = val
                        break

        return updates

    async def update_resource_mappings(
        self,
        db: AsyncSession,
        primary_id: int,
        duplicate_ids: list[int]
    ):
        """
        更新 resource_mappings，将重复记录的映射指向主记录

        Args:
            db: 数据库会话
            primary_id: 保留的主记录ID
            duplicate_ids: 要删除的重复记录ID列表
        """
        for dup_id in duplicate_ids:
            # 查询指向重复记录的映射
            query = select(ResourceMapping).where(
                and_(
                    ResourceMapping.unified_table_name == "unified_movies",
                    ResourceMapping.unified_resource_id == dup_id
                )
            )
            result = await db.execute(query)
            mappings = result.scalars().all()

            # 更新映射指向主记录
            for mapping in mappings:
                mapping.unified_resource_id = primary_id
                self.updated_mappings_count += 1
                self.log(
                    f"  更新映射 ResourceMapping(id={mapping.id}, pt_resource_id={mapping.pt_resource_id}) "
                    f"从 unified_resource_id={dup_id} → {primary_id}",
                    level="DEBUG"
                )

        # 注意：不在这里 commit，而是在整个合并流程结束后统一 commit

    async def delete_duplicate_records(self, db: AsyncSession, duplicate_ids: list[int]):
        """删除重复记录"""
        for dup_id in duplicate_ids:
            if not self.dry_run:
                await db.execute(
                    delete(UnifiedMovie).where(UnifiedMovie.id == dup_id)
                )
            self.deleted_count += 1
            self.log(f"  删除重复记录 UnifiedMovie(id={dup_id})")

        if not self.dry_run:
            # 统一提交整个合并流程的所有操作：
            # 1. 清除冲突的外部ID
            # 2. 更新主记录的元数据
            # 3. 更新 resource_mappings
            # 4. 删除重复记录
            await db.commit()

    async def clear_conflicting_external_ids(
        self,
        db: AsyncSession,
        primary_id: int,
        duplicate_ids: list[int],
        updates: dict
    ):
        """
        清除与待更新外部ID冲突的其他记录的外部ID

        Args:
            db: 数据库会话
            primary_id: 主记录ID
            duplicate_ids: 重复记录ID列表
            updates: 待更新的字段字典
        """
        # 检查待更新的外部ID
        external_id_fields = ['tmdb_id', 'douban_id', 'imdb_id']
        exclude_ids = [primary_id] + duplicate_ids
        has_conflicts = False

        for field in external_id_fields:
            if field not in updates:
                continue

            new_value = updates[field]
            if not new_value:
                continue

            # 查询是否有其他记录使用了这个外部ID
            query = select(UnifiedMovie).where(
                and_(
                    getattr(UnifiedMovie, field) == new_value,
                    ~UnifiedMovie.id.in_(exclude_ids)  # 排除当前合并组的记录
                )
            )
            result = await db.execute(query)
            conflicting_records = result.scalars().all()

            # 清除冲突记录的外部ID
            for record in conflicting_records:
                has_conflicts = True
                self.log(
                    f"  ⚠️  清除冲突: UnifiedMovie(id={record.id}, title=\"{record.title}\") "
                    f"的 {field}={new_value}（与主记录冲突）",
                    level="WARNING"
                )
                if not self.dry_run:
                    setattr(record, field, None)
                    record.updated_at = now()

        # 注意：不在这里 commit，而是在整个合并流程结束后统一 commit
        # 这样可以确保所有操作在同一个事务中

    async def remove_conflicting_updates(
        self,
        db: AsyncSession,
        primary_id: int,
        duplicate_ids: list[int],
        updates: dict
    ):
        """
        在 dry-run 模式下，从 updates 中移除会导致冲突的外部ID

        Args:
            db: 数据库会话
            primary_id: 主记录ID
            duplicate_ids: 重复记录ID列表
            updates: 待更新的字段字典（会被修改）
        """
        external_id_fields = ['tmdb_id', 'douban_id', 'imdb_id']
        exclude_ids = [primary_id] + duplicate_ids

        for field in external_id_fields:
            if field not in updates:
                continue

            new_value = updates[field]
            if not new_value:
                continue

            # 查询是否有其他记录使用了这个外部ID
            query = select(UnifiedMovie).where(
                and_(
                    getattr(UnifiedMovie, field) == new_value,
                    ~UnifiedMovie.id.in_(exclude_ids)
                )
            )
            result = await db.execute(query)
            conflicting_records = result.scalars().all()

            # 如果有冲突，从 updates 中移除这个字段
            if conflicting_records:
                self.log(
                    f"  ⚠️  跳过更新: 主记录的 {field}={new_value} 与其他记录冲突（dry-run模式）",
                    level="WARNING"
                )
                del updates[field]

    async def merge_group(self, db: AsyncSession, title: str, year: int):
        """
        合并一组重复记录

        Args:
            db: 数据库会话
            title: 电影标题
            year: 年份
        """
        # 获取所有重复记录（按ID升序，保留第一条）
        movies = await self.get_duplicate_movies(db, title, year)
        if len(movies) < 2:
            return

        primary = movies[0]  # 保留的主记录
        duplicates = movies[1:]  # 要删除的记录

        self.log(f"\n合并: {title} ({year}) - {len(movies)} 条记录")
        self.log(f"  主记录: UnifiedMovie(id={primary.id}, tmdb_id={primary.tmdb_id}, "
                 f"douban_id={primary.douban_id}, imdb_id={primary.imdb_id})")

        for dup in duplicates:
            self.log(f"  重复记录: UnifiedMovie(id={dup.id}, tmdb_id={dup.tmdb_id}, "
                     f"douban_id={dup.douban_id}, imdb_id={dup.imdb_id})")

        # 1. 合并元数据
        updates = self.merge_metadata(primary, duplicates)

        # 1.5. 清除与待更新外部ID冲突的其他记录
        duplicate_ids = [dup.id for dup in duplicates]

        # 在 dry-run 模式下，检查冲突并跳过冲突字段
        if self.dry_run:
            await self.clear_conflicting_external_ids(db, primary.id, duplicate_ids, updates)
            await self.remove_conflicting_updates(db, primary.id, duplicate_ids, updates)
        else:
            # 在实际执行模式下，先清除冲突，然后在同一事务中更新主记录
            await self.clear_conflicting_external_ids(db, primary.id, duplicate_ids, updates)

        if updates:
            self.log(f"  合并元数据: {len(updates)} 个字段")
            if self.verbose:
                for key, value in updates.items():
                    # 限制输出长度
                    val_str = str(value)
                    if len(val_str) > 100:
                        val_str = val_str[:100] + "..."
                    self.log(f"    {key}: {val_str}", level="DEBUG")

            if not self.dry_run:
                for key, value in updates.items():
                    setattr(primary, key, value)
                primary.updated_at = now()
                # 注意：这里不 commit，等到删除重复记录后再统一 commit
                # await db.commit()
                # await db.refresh(primary)

        # 2. 更新 resource_mappings
        duplicate_ids = [dup.id for dup in duplicates]
        await self.update_resource_mappings(db, primary.id, duplicate_ids)

        # 3. 删除重复记录
        await self.delete_duplicate_records(db, duplicate_ids)

        self.merged_count += 1

    async def run(self):
        """执行合并任务"""
        async with async_session_local() as db:
            # 1. 查找重复记录组
            duplicate_groups = await self.find_duplicate_groups(db)

            if not duplicate_groups:
                print("✅ 没有发现重复记录")
                return

            # 2. 逐组合并
            for title, year, count in duplicate_groups:
                try:
                    await self.merge_group(db, title, year)
                except Exception as e:
                    self.failed_count += 1
                    self.log(
                        f"\n❌ 合并失败: {title} ({year}) - {type(e).__name__}: {str(e)}",
                        level="ERROR"
                    )
                    self.log(f"   跳过此记录，继续处理后续合并...", level="WARNING")
                    # 回滚当前事务
                    if not self.dry_run:
                        await db.rollback()
                    continue

            # 3. 输出统计
            print("\n" + "="*60)
            if self.dry_run:
                print("【预览模式 - 未执行实际操作】")
            else:
                print("【合并完成】")
            print(f"合并组数: {self.merged_count}")
            print(f"删除记录: {self.deleted_count}")
            print(f"更新映射: {self.updated_mappings_count}")
            if self.failed_count > 0:
                print(f"失败记录: {self.failed_count} ⚠️")
            print("="*60)


async def main():
    parser = argparse.ArgumentParser(description="合并重复的 unified_movies 记录")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只分析不执行，预览将要合并的记录"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="显示详细日志"
    )
    args = parser.parse_args()

    merger = MovieMerger(dry_run=args.dry_run, verbose=args.verbose)
    await merger.run()


if __name__ == "__main__":
    asyncio.run(main())
