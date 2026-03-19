# -*- coding: utf-8 -*-
"""
事件系统包

统一管理所有事件相关的组件：
    - bus: 事件总线核心
    - manager: 生命周期管理
    - handlers: 事件处理器

使用示例:
    from app.events import event_bus, event_bus_manager

    # 发布事件
    await event_bus.publish("download_completed", {...})

    # 启动事件系统
    await event_bus_manager.start()
"""
from app.events.bus import EventBus, event_bus
from app.events.manager import EventBusManager, event_bus_manager

__all__ = [
    "EventBus",
    "event_bus",
    "EventBusManager",
    "event_bus_manager",
]
