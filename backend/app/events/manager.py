# -*- coding: utf-8 -*-
"""
事件总线管理器

负责事件总线的生命周期管理和监听器注册。
单例模式，在应用启动时初始化，关闭时清理。

使用模式：
    # 在 main.py 的 lifespan 中
    await event_bus_manager.start()
    ...
    await event_bus_manager.stop()
"""
import logging
from typing import Optional

from app.events.bus import event_bus

logger = logging.getLogger(__name__)


class EventBusManager:
    """
    事件总线管理器

    职责：
        - 管理事件总线的启动和停止
        - 注册所有监听器
        - 提供统一的生命周期接口
    """

    def __init__(self):
        """初始化管理器"""
        self._started = False
        logger.debug("事件总线管理器已初始化")

    async def start(self) -> None:
        """
        启动事件总线

        执行步骤：
            1. 注册所有监听器
            2. 启动事件总线
        """
        if self._started:
            logger.warning("事件总线管理器已经启动")
            return

        logger.debug("正在启动事件总线管理器...")

        try:
            # 1. 注册监听器
            await self._register_listeners()

            # 2. 启动事件总线
            event_bus.start()

            self._started = True
            logger.info("✅ 事件总线管理器启动成功")

            # 3. 打印统计信息
            stats = event_bus.get_stats()
            logger.debug(
                f"事件总线统计: "
                f"{stats['total_event_types']} 个事件类型, "
                f"{stats['total_listeners']} 个监听器"
            )

        except Exception as e:
            logger.exception(f"事件总线管理器启动失败: {str(e)}")
            raise

    async def stop(self) -> None:
        """
        停止事件总线

        执行步骤：
            1. 停止事件总线
            2. 清理资源
        """
        if not self._started:
            logger.warning("事件总线管理器未启动")
            return

        logger.info("正在停止事件总线管理器...")

        try:
            # 停止事件总线
            event_bus.stop()

            self._started = False
            logger.info("✅ 事件总线管理器已停止")

        except Exception as e:
            logger.exception(f"事件总线管理器停止失败: {str(e)}")

    async def _register_listeners(self) -> None:
        """
        注册所有监听器

        监听器类型：
            - 通知监听器：处理系统通知
            - 工作流监听器：触发自动化任务
            - 审计监听器：记录操作日志（未来扩展）
            - 指标监听器：收集性能指标（未来扩展）
        """
        logger.debug("正在注册事件监听器...")

        # 注册通知监听器
        await self._register_notification_listener()

        # 注册工作流监听器
        await self._register_workflow_listener()

        # 注册媒体服务器监听器
        await self._register_media_server_listener()

        logger.debug("✅ 所有监听器注册完成")

    async def _register_notification_listener(self) -> None:
        """
        注册通知监听器

        订阅所有需要发送通知的事件类型
        """
        from app.constants.event import ALL_EVENTS
        from app.events.handlers.notification_handler import handle_notification_event

        for event_type in ALL_EVENTS:
            event_bus.subscribe(event_type, handle_notification_event)

        logger.debug(
            f"✅ 通知监听器已注册: {len(ALL_EVENTS)} 个事件类型"
        )

    async def _register_workflow_listener(self) -> None:
        """
        注册工作流监听器

        订阅需要触发自动化任务的事件类型
        """
        from app.constants.event import (
            EVENT_SITE_SYNC_COMPLETED,
            EVENT_DOWNLOAD_STARTED,
            EVENT_DOWNLOAD_COMPLETED,
        )
        from app.events.handlers.workflow_handler import handle_workflow_event

        # 订阅需要触发工作流的事件
        workflow_events = [
            EVENT_SITE_SYNC_COMPLETED,    # 站点同步完成 → 识别 + 订阅检查
            EVENT_DOWNLOAD_STARTED,       # 下载创建 → 状态同步
            EVENT_DOWNLOAD_COMPLETED,     # 下载完成 → 资源整理（预留）
        ]

        for event_type in workflow_events:
            event_bus.subscribe(event_type, handle_workflow_event)

        logger.debug(
            f"✅ 工作流监听器已注册: {len(workflow_events)} 个事件类型"
        )

    async def _register_media_server_listener(self) -> None:
        """
        注册媒体服务器监听器

        订阅需要触发媒体服务器操作的事件类型
        """
        from app.constants.event import EVENT_MEDIA_ORGANIZED
        from app.events.handlers.media_server_handler import handle_media_organized_event

        # 订阅媒体文件整理完成事件
        event_bus.subscribe(EVENT_MEDIA_ORGANIZED, handle_media_organized_event)

        logger.debug("✅ 媒体服务器监听器已注册: EVENT_MEDIA_ORGANIZED")

    def is_started(self) -> bool:
        """
        检查事件总线是否已启动

        Returns:
            bool: 是否已启动
        """
        return self._started

    def get_stats(self) -> dict:
        """
        获取事件总线统计信息

        Returns:
            dict: 统计数据
        """
        return {
            "manager_started": self._started,
            **event_bus.get_stats()
        }


# 全局单例实例
event_bus_manager = EventBusManager()
