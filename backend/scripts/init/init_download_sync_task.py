# -*- coding: utf-8 -*-
"""
初始化下载状态同步定时任务

用途：
1. 创建"监听下载完成"定时任务
2. 每 1 分钟检查所有进行中的下载任务

使用方法：
    python scripts/init/init_download_sync_task.py
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select
from app.core.database import async_session_local
from app.models.scheduled_task import ScheduledTask
from app.schemas.scheduled_task import ScheduledTaskCreate
from app.services.task.scheduled_task_service import ScheduledTaskService
from app.constants import (
    TASK_TYPE_DOWNLOAD_STATUS_SYNC,  # 注意：常量名已更新
    SCHEDULE_TYPE_INTERVAL,
)


async def init_download_sync_task():
    """初始化下载状态同步任务"""
    async with async_session_local() as db:
        try:
            print("\n初始化下载状态同步定时任务")
            print("=" * 60)

            # 检查任务是否已存在
            print("[1/2] 检查任务是否已存在...")
            result = await db.execute(
                select(ScheduledTask).where(
                    ScheduledTask.task_type == TASK_TYPE_DOWNLOAD_STATUS_SYNC
                )
            )
            existing_task = result.scalar_one_or_none()

            if existing_task:
                print(f"✓ 任务已存在: {existing_task.task_name} (ID: {existing_task.id})")
                print(f"  状态: {'启用' if existing_task.enabled else '禁用'}")
                print(f"  调度类型: {existing_task.schedule_type}")
                print(f"  调度配置: {existing_task.schedule_config}")

                # 询问是否更新
                choice = input("\n是否更新任务配置? (y/n): ")
                if choice.lower() != 'y':
                    print("\n跳过更新")
                    return

                # 更新任务
                print("\n[2/2] 更新任务...")
                existing_task.schedule_type = SCHEDULE_TYPE_INTERVAL
                existing_task.schedule_config = {"minutes": 1}
                existing_task.enabled = True
                existing_task.priority = 2
                existing_task.description = "定时检查所有下载任务状态，处理完成任务"

                await db.commit()
                await db.refresh(existing_task)
                print(f"✓ 任务已更新: {existing_task.task_name}")

            else:
                # 创建新任务
                print("\n[2/2] 创建新任务...")
                task_data = ScheduledTaskCreate(
                    task_name="监听下载完成",
                    task_type=TASK_TYPE_DOWNLOAD_STATUS_SYNC,
                    handler=TASK_TYPE_DOWNLOAD_STATUS_SYNC,  # 使用任务类型作为 handler
                    handler_params={},
                    schedule_type=SCHEDULE_TYPE_INTERVAL,
                    schedule_config={"minutes": 1},
                    enabled=True,
                    priority=2,
                    max_retries=1,
                    description="定时检查所有下载任务状态，处理完成任务"
                )

                task = await ScheduledTaskService.create(db, task_data)
                print(f"✓ 任务已创建: {task.task_name} (ID: {task.id})")

            print("\n" + "=" * 60)
            print("✓ 初始化完成！")
            print("\n任务详情:")
            print(f"  - 任务名称: 监听下载完成")
            print(f"  - 任务类型: {TASK_TYPE_DOWNLOAD_STATUS_SYNC}")
            print(f"  - 调度类型: 固定间隔")
            print(f"  - 执行频率: 每 1 分钟")
            print(f"  - 优先级: 2")
            print(f"  - 状态: 启用")
            print("\n提示：重启应用后任务将自动运行")

        except Exception as e:
            await db.rollback()
            print(f"\n✗ 初始化失败：{e}")
            raise


async def main():
    """主函数"""
    try:
        await init_download_sync_task()
    except Exception as e:
        print(f"\n错误：{e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
