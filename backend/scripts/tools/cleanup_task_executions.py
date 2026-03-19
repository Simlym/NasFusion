# -*- coding: utf-8 -*-
"""
清理任务执行历史记录

用途：
1. 删除指定天数之前的已完成任务执行记录
2. 保留失败的任务记录用于调试
3. 可配置保留策略

使用方法：
    python scripts/tools/cleanup_task_executions.py --days 7
    python scripts/tools/cleanup_task_executions.py --days 30 --keep-failed
"""
import asyncio
import sys
import argparse
from pathlib import Path
from datetime import timedelta

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


async def cleanup_executions(days: int, keep_failed: bool = True, dry_run: bool = False):
    """
    清理任务执行记录

    Args:
        days: 保留最近N天的记录
        keep_failed: 是否保留失败的记录
        dry_run: 只统计，不实际删除
    """
    from app.core.database import async_session_local
    from sqlalchemy import select, delete, func, and_
    from app.models.task_execution import TaskExecution
    from app.utils.timezone import now

    async with async_session_local() as db:
        cutoff_date = now() - timedelta(days=days)

        print(f"\nTask Execution Cleanup")
        print("=" * 60)
        print(f"  Cutoff date: {cutoff_date}")
        print(f"  Keep failed: {keep_failed}")
        print(f"  Dry run: {dry_run}")
        print()

        # 构建删除条件
        conditions = [
            TaskExecution.completed_at < cutoff_date,
            TaskExecution.status == 'completed'
        ]

        if not keep_failed:
            # 如果不保留失败记录，移除 status 条件
            conditions = [TaskExecution.completed_at < cutoff_date]

        # 统计将要删除的记录
        count_result = await db.execute(
            select(func.count(TaskExecution.id))
            .where(and_(*conditions))
        )
        total_to_delete = count_result.scalar()

        # 按任务类型统计
        stats_result = await db.execute(
            select(
                TaskExecution.task_type,
                func.count(TaskExecution.id).label('count')
            )
            .where(and_(*conditions))
            .group_by(TaskExecution.task_type)
        )
        stats = stats_result.all()

        print(f"Records to delete: {total_to_delete}")
        print("\nBreakdown by task type:")
        for task_type, count in stats:
            print(f"  - {task_type}: {count}")

        if dry_run:
            print("\n[DRY RUN] No records deleted.")
        else:
            # 执行删除
            result = await db.execute(
                delete(TaskExecution)
                .where(and_(*conditions))
            )
            await db.commit()

            print(f"\nDeleted {result.rowcount} records.")

        # 统计剩余记录
        remaining_result = await db.execute(
            select(func.count(TaskExecution.id))
        )
        remaining = remaining_result.scalar()

        print(f"\nRemaining records: {remaining}")
        print("=" * 60 + "\n")


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='清理任务执行历史记录')
    parser.add_argument(
        '--days',
        type=int,
        default=7,
        help='保留最近N天的记录（默认：7天）'
    )
    parser.add_argument(
        '--keep-failed',
        action='store_true',
        default=True,
        help='保留失败的记录（默认：保留）'
    )
    parser.add_argument(
        '--delete-failed',
        action='store_true',
        help='同时删除失败的记录'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='只统计，不实际删除'
    )

    args = parser.parse_args()

    keep_failed = not args.delete_failed if args.delete_failed else args.keep_failed

    try:
        await cleanup_executions(
            days=args.days,
            keep_failed=keep_failed,
            dry_run=args.dry_run
        )
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
