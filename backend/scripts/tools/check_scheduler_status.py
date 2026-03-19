# -*- coding: utf-8 -*-
"""
检查调度器和定时任务状态

用途：
1. 检查"监听下载完成"任务是否正确配置
2. 检查任务执行历史
3. 检查调度器是否正在运行

使用方法：
    python scripts/tools/check_scheduler_status.py
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


async def check_status():
    """检查调度器状态"""
    from app.core.database import async_session_local
    from sqlalchemy import select, func
    from app.models.scheduled_task import ScheduledTask
    from app.models.task_execution import TaskExecution

    async with async_session_local() as db:
        print("\n" + "=" * 70)
        print("Scheduler Status Check")
        print("=" * 70)

        # 1. 检查定时任务配置
        print("\n[1] Checking scheduled task configuration...")
        result = await db.execute(
            select(ScheduledTask).where(
                ScheduledTask.task_type == 'sync_download_status'
            )
        )
        task = result.scalar_one_or_none()

        if task:
            print(f"  Task ID: {task.id}")
            print(f"  Task Name: {task.task_name}")
            print(f"  Enabled: {task.enabled}")
            print(f"  Schedule Type: {task.schedule_type}")
            print(f"  Schedule Config: {task.schedule_config}")
            print(f"  Next Run: {task.next_run_at}")
            print(f"  Last Run: {task.last_run_at}")
            print(f"  Last Status: {task.last_run_status}")
            print(f"  Total Runs: {task.total_runs}")
            print(f"  Success Runs: {task.success_runs}")
            print(f"  Failed Runs: {task.failed_runs}")

            if not task.enabled:
                print("\n  WARNING: Task is DISABLED!")
            elif not task.schedule_config:
                print("\n  ERROR: schedule_config is NULL!")
                print("  Run: python scripts/init/init_download_sync_task.py")
            elif not task.next_run_at:
                print("\n  WARNING: next_run_at is NULL!")
                print("  Scheduler may not have loaded this task yet.")
                print("  Please RESTART the application.")
            else:
                print("\n  OK: Task is properly configured.")
        else:
            print("  ERROR: Task not found!")
            print("  Run: python scripts/init/init_download_sync_task.py")
            return

        # 2. 检查最近执行历史
        print("\n[2] Checking recent execution history...")
        result = await db.execute(
            select(TaskExecution)
            .where(TaskExecution.task_type == 'sync_download_status')
            .order_by(TaskExecution.created_at.desc())
            .limit(5)
        )
        executions = result.scalars().all()

        if executions:
            print(f"  Found {len(executions)} recent executions:")
            for exe in executions:
                status_icon = "OK" if exe.status == "completed" else "!!"
                print(f"    [{status_icon}] {exe.started_at} | Status: {exe.status} | Progress: {exe.progress}%")
                if exe.result:
                    print(f"        Result: {exe.result}")
        else:
            print("  No execution history found.")
            print("  Task has never run yet.")

        # 3. 检查最近1小时内的执行
        print("\n[3] Checking executions in last hour...")
        from app.utils.timezone import now
        one_hour_ago = now() - timedelta(hours=1)
        result = await db.execute(
            select(func.count(TaskExecution.id))
            .where(
                TaskExecution.task_type == 'sync_download_status',
                TaskExecution.created_at >= one_hour_ago
            )
        )
        count = result.scalar()

        if count > 0:
            print(f"  {count} execution(s) in last hour")
            print("  OK: Task is running automatically!")
        else:
            print(f"  0 executions in last hour")
            print("  WARNING: Task may not be running!")
            print("  Please check:")
            print("    1. Is the application running?")
            print("    2. Has the application been restarted after updating schedule_config?")
            print("    3. Check application logs for errors")

        # 4. 检查进行中的下载任务
        print("\n[4] Checking active download tasks...")
        from app.models.download_task import DownloadTask
        result = await db.execute(
            select(func.count(DownloadTask.id))
            .where(DownloadTask.status.in_(['pending', 'downloading']))
        )
        active_count = result.scalar()

        print(f"  Active download tasks: {active_count}")
        if active_count > 0:
            print("  The sync task should be monitoring these downloads.")

        print("\n" + "=" * 70)
        print("Check complete!")
        print("=" * 70 + "\n")


async def main():
    """主函数"""
    try:
        await check_status()
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
