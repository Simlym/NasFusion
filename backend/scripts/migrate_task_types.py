# -*- coding: utf-8 -*-
"""
数据库迁移脚本：更新任务类型命名

此脚本用于将数据库中的旧任务类型值更新为新的命名规范。

执行前请备份数据库！

使用方法：
    python scripts/migrate_task_types.py
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, update
from app.core.database import async_session_local
from app.models.scheduled_task import ScheduledTask
from app.models.task_execution import TaskExecution


# 任务类型映射表（旧值 -> 新值）
TASK_TYPE_MIGRATION_MAP = {
    "pt_sync": "pt_resource_sync",
    "batch_identify": "pt_resource_identify",
    "cleanup": "task_execution_cleanup",
    "create_download": "download_create",
    "scan_media": "media_file_scan",
    "sync_download_status": "download_status_sync",
}


async def migrate_scheduled_tasks():
    """迁移 scheduled_tasks 表"""
    async with async_session_local() as db:
        updated_count = 0

        for old_type, new_type in TASK_TYPE_MIGRATION_MAP.items():
            result = await db.execute(
                update(ScheduledTask)
                .where(ScheduledTask.task_type == old_type)
                .values(task_type=new_type)
            )
            count = result.rowcount
            updated_count += count
            if count > 0:
                print(f"  [OK] scheduled_tasks: {old_type} -> {new_type} ({count} 条记录)")

        await db.commit()
        return updated_count


async def migrate_task_executions():
    """迁移 task_executions 表"""
    async with async_session_local() as db:
        updated_count = 0

        for old_type, new_type in TASK_TYPE_MIGRATION_MAP.items():
            result = await db.execute(
                update(TaskExecution)
                .where(TaskExecution.task_type == old_type)
                .values(task_type=new_type)
            )
            count = result.rowcount
            updated_count += count
            if count > 0:
                print(f"  [OK] task_executions: {old_type} -> {new_type} ({count} 条记录)")

        await db.commit()
        return updated_count


async def verify_migration():
    """验证迁移结果"""
    async with async_session_local() as db:
        print("\n验证迁移结果:")

        # 检查 scheduled_tasks
        result = await db.execute(select(ScheduledTask.task_type).distinct())
        task_types = [row[0] for row in result.all()]
        print(f"  scheduled_tasks 表的任务类型: {task_types}")

        # 检查 task_executions
        result = await db.execute(select(TaskExecution.task_type).distinct())
        task_types = [row[0] for row in result.all()]
        print(f"  task_executions 表的任务类型: {task_types}")

        # 检查是否还有旧的任务类型
        old_types = list(TASK_TYPE_MIGRATION_MAP.keys())
        remaining_old = [t for t in task_types if t in old_types]
        if remaining_old:
            print(f"\n[WARNING] 警告：仍存在旧的任务类型: {remaining_old}")
            return False
        else:
            print(f"\n[SUCCESS] 迁移验证通过！")
            return True


async def main():
    print("=" * 60)
    print("任务类型命名迁移脚本")
    print("=" * 60)
    print("\n[WARNING] 警告：此操作将修改数据库，执行前请确保已备份数据库！\n")

    # 显示迁移映射
    print("迁移映射表:")
    for old_type, new_type in TASK_TYPE_MIGRATION_MAP.items():
        print(f"  {old_type:25} -> {new_type}")

    # 确认执行
    confirm = input("\n是否继续执行迁移？(yes/no): ")
    if confirm.lower() != "yes":
        print("已取消迁移。")
        return

    print("\n开始迁移...")

    # 执行迁移
    try:
        print("\n1. 迁移 scheduled_tasks 表:")
        scheduled_count = await migrate_scheduled_tasks()
        print(f"  共更新 {scheduled_count} 条记录")

        print("\n2. 迁移 task_executions 表:")
        execution_count = await migrate_task_executions()
        print(f"  共更新 {execution_count} 条记录")

        # 验证迁移
        success = await verify_migration()

        if success:
            print("\n" + "=" * 60)
            print("[SUCCESS] 迁移完成！")
            print("=" * 60)
            print(f"\n总计更新:")
            print(f"  - scheduled_tasks: {scheduled_count} 条")
            print(f"  - task_executions: {execution_count} 条")
            print(f"  - 合计: {scheduled_count + execution_count} 条\n")
        else:
            print("\n" + "=" * 60)
            print("[WARNING] 迁移可能未完全成功，请检查数据库！")
            print("=" * 60)

    except Exception as e:
        print(f"\n[ERROR] 迁移失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
