# -*- coding: utf-8 -*-
"""
测试通知系统脚本

用法:
    python test_notification.py
"""
import asyncio
import logging

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from app.core.database import async_session_local
from app.events.bus import event_bus
from app.events.manager import event_bus_manager
from app.services.notification.notification_dispatch_service import NotificationDispatchService


async def test_notification():
    """测试通知系统"""

    # 1. 启动事件总线
    print("=" * 60)
    print("Step 1: Start event bus")
    print("=" * 60)
    await event_bus_manager.start()
    stats = event_bus_manager.get_stats()
    print(f"OK Event bus started")
    print(f"   - Event types: {stats['total_event_types']}")
    print(f"   - Listeners: {stats['total_listeners']}")

    # 2. 测试通过事件总线发布
    print("\n" + "=" * 60)
    print("Step 2: Publish event via event bus")
    print("=" * 60)

    test_event_data = {
        "user_id": 1,
        "task_name": "Test Task",
        "duration": "10s",
        "result": "Success"
    }

    print(f"Publishing event: task_completed")
    print(f"Event data: {test_event_data}")

    await event_bus.publish("task_completed", test_event_data)

    # 等待异步处理完成
    await asyncio.sleep(2)

    # 3. 测试直接调度
    print("\n" + "=" * 60)
    print("Step 3: Direct dispatch (bypass event bus)")
    print("=" * 60)

    async with async_session_local() as db:
        result = await NotificationDispatchService.dispatch_event(
            db,
            event_type="task_completed",
            event_data=test_event_data,
            user_id=1,
            broadcast=False
        )

        print(f"OK Dispatch completed")
        print(f"   - Rules matched: {result['total_rules']}")
        print(f"   - In-app sent: {result['in_app_sent']}")
        print(f"   - Channel sent: {result['channel_sent']}")
        print(f"   - Failed: {result['failed']}")
        print(f"   - Skipped: {result['skipped']}")
        print(f"   - Log IDs: {result['logs']}")

        # 检查是否有通知
        from app.services.notification.notification_internal_service import NotificationInternalService
        notifications, total = await NotificationInternalService.get_user_notifications(
            db, user_id=1, limit=5
        )

        print(f"\n   User notifications count: {len(notifications)} (total: {total})")
        if notifications:
            print("   Recent notifications:")
            for idx, notif in enumerate(notifications[:3], 1):
                print(f"     #{idx} type={notif.notification_type}, priority={notif.priority}")

    # 4. 停止事件总线
    print("\n" + "=" * 60)
    print("Step 4: Stop event bus")
    print("=" * 60)
    await event_bus_manager.stop()
    print("OK Event bus stopped")


if __name__ == "__main__":
    asyncio.run(test_notification())
