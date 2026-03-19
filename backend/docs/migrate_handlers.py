# -*- coding: utf-8 -*-
"""
数据库迁移脚本：修复 handler 字段格式

将旧的 handler 格式迁移到新的任务类型格式:
- tasks.pt_sync.sync_site → pt_resource_sync
- app.services.subscription_check_handler.SubscriptionCheckHandler.check_all_subscriptions → subscription_check
- sync_all_download_status → download_status_sync
- cleanup_task_executions → task_execution_cleanup
"""
import asyncio
from sqlalchemy import select, update
from app.core.database import async_session_local
from app.models.scheduled_task import ScheduledTask
from app.constants import (
    TASK_TYPE_PT_RESOURCE_SYNC,
    TASK_TYPE_SUBSCRIPTION_CHECK,
    TASK_TYPE_DOWNLOAD_STATUS_SYNC,
    TASK_TYPE_TASK_EXECUTION_CLEANUP,
)

# Handler 映射表
HANDLER_MIGRATION_MAP = {
    "tasks.pt_sync.sync_site": TASK_TYPE_PT_RESOURCE_SYNC,
    "app.services.subscription_check_handler.SubscriptionCheckHandler.check_all_subscriptions": TASK_TYPE_SUBSCRIPTION_CHECK,
    "sync_all_download_status": TASK_TYPE_DOWNLOAD_STATUS_SYNC,
    "cleanup_task_executions": TASK_TYPE_TASK_EXECUTION_CLEANUP,
}


async def migrate_handlers():
    """迁移 handler 字段"""
    async with async_session_local() as session:
        # 查询所有任务
        result = await session.execute(select(ScheduledTask))
        tasks = result.scalars().all()

        print(f"\n开始迁移 {len(tasks)} 个调度任务的 handler 字段...")
        print("=" * 80)

        migrated_count = 0
        skipped_count = 0

        for task in tasks:
            old_handler = task.handler
            new_handler = HANDLER_MIGRATION_MAP.get(old_handler)

            if new_handler:
                # 需要迁移
                task.handler = new_handler
                migrated_count += 1
                print(f"\n[OK] [ID {task.id}] {task.task_name}")
                print(f"     旧值: {old_handler}")
                print(f"     新值: {new_handler}")
            elif old_handler in [
                TASK_TYPE_PT_RESOURCE_SYNC,
                TASK_TYPE_SUBSCRIPTION_CHECK,
                TASK_TYPE_DOWNLOAD_STATUS_SYNC,
                TASK_TYPE_TASK_EXECUTION_CLEANUP,
            ]:
                # 已经是新格式,跳过
                skipped_count += 1
                print(f"\n[SKIP] [ID {task.id}] {task.task_name} (已是新格式)")
            else:
                # 未知格式,警告
                print(f"\n[WARN] [ID {task.id}] {task.task_name}")
                print(f"       未知的 handler 格式: {old_handler}")

        # 提交更改
        if migrated_count > 0:
            await session.commit()
            print("\n" + "=" * 80)
            print(f"[SUCCESS] 迁移完成: {migrated_count} 个任务已更新, {skipped_count} 个任务已跳过")
        else:
            print("\n" + "=" * 80)
            print(f"[INFO] 无需迁移: 所有任务的 handler 格式已是最新")


if __name__ == "__main__":
    asyncio.run(migrate_handlers())
