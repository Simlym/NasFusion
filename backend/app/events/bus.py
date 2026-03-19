# -*- coding: utf-8 -*-
"""
事件总线核心模块

提供发布-订阅模式的事件分发机制，用于解耦业务逻辑和通知系统。

架构设计：
    业务服务 → event_bus.publish() → 异步监听器

优势：
    - 业务代码与通知逻辑解耦
    - 支持多个监听器（通知/日志/指标）
    - 异步并发执行，不阻塞主流程
    - 易于测试和扩展

使用示例：
    # 发布事件
    await event_bus.publish("download_completed", {
        "task_id": 123,
        "user_id": 1,
        "file_name": "movie.mkv"
    })

    # 订阅事件
    async def my_listener(event_type: str, event_data: dict):
        print(f"收到事件: {event_type}")

    event_bus.subscribe("download_completed", my_listener)
"""
import asyncio
import logging
from typing import Any, Callable, Dict, List, Coroutine

logger = logging.getLogger(__name__)


class EventBus:
    """
    事件总线

    核心组件，负责事件的发布和订阅。
    使用单例模式，确保全局唯一实例。
    """

    def __init__(self):
        """初始化事件总线"""
        self._listeners: Dict[str, List[Callable]] = {}
        self._is_started = False
        logger.debug("事件总线已初始化")

    def subscribe(
        self,
        event_type: str,
        handler: Callable[[str, Dict[str, Any]], Coroutine[Any, Any, None]]
    ) -> None:
        """
        订阅事件

        Args:
            event_type: 事件类型（如: "download_completed"）
            handler: 异步处理函数，签名: async def handler(event_type: str, event_data: dict)

        示例:
            async def on_download(event_type: str, event_data: dict):
                print(f"下载完成: {event_data['file_name']}")

            event_bus.subscribe("download_completed", on_download)
        """
        if event_type not in self._listeners:
            self._listeners[event_type] = []

        self._listeners[event_type].append(handler)

        logger.debug(
            f"已订阅事件: {event_type} -> {handler.__module__}.{handler.__name__}"
        )

    def unsubscribe(
        self,
        event_type: str,
        handler: Callable[[str, Dict[str, Any]], Coroutine[Any, Any, None]]
    ) -> bool:
        """
        取消订阅事件

        Args:
            event_type: 事件类型
            handler: 处理函数

        Returns:
            bool: 是否成功取消订阅
        """
        if event_type not in self._listeners:
            return False

        try:
            self._listeners[event_type].remove(handler)
            logger.debug(
                f"已取消订阅: {event_type} -> {handler.__module__}.{handler.__name__}"
            )
            return True
        except ValueError:
            return False

    async def publish(
        self,
        event_type: str,
        event_data: Dict[str, Any],
        wait: bool = False
    ) -> None:
        """
        发布事件

        Args:
            event_type: 事件类型（如: "download_completed"）
            event_data: 事件数据（字典格式）
            wait: 是否等待所有监听器执行完成（默认 False，异步触发后立即返回）

        说明:
            - 默认情况下（wait=False），事件发布后立即返回，不阻塞业务流程
            - 设置 wait=True 时，会等待所有监听器执行完成（用于测试或关键事件）
            - 监听器执行异常不会中断其他监听器，会记录日志

        示例:
            # 异步触发（推荐）
            await event_bus.publish("download_completed", {
                "task_id": 123,
                "user_id": 1
            })

            # 同步等待（测试场景）
            await event_bus.publish("critical_event", {...}, wait=True)
        """
        if not self._is_started:
            logger.warning(f"事件总线未启动，跳过事件: {event_type}")
            return

        # 获取订阅此事件的监听器
        handlers = self._listeners.get(event_type, [])

        if not handlers:
            logger.debug(f"事件 {event_type} 没有监听器")
            return

        logger.debug(
            f"发布事件: {event_type}, 监听器数量: {len(handlers)}, "
            f"等待执行: {wait}"
        )

        # 创建所有监听器任务
        tasks = [
            self._execute_handler(handler, event_type, event_data)
            for handler in handlers
        ]

        if wait:
            # 同步等待所有监听器执行完成
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 统计执行结果
            success_count = sum(1 for r in results if not isinstance(r, Exception))
            error_count = len(results) - success_count

            logger.debug(
                f"事件 {event_type} 执行完成: "
                f"成功 {success_count}, 失败 {error_count}"
            )
        else:
            # 异步触发，不等待结果
            asyncio.gather(*tasks, return_exceptions=True)
            logger.debug(f"事件 {event_type} 已异步触发")

    async def _execute_handler(
        self,
        handler: Callable[[str, Dict[str, Any]], Coroutine[Any, Any, None]],
        event_type: str,
        event_data: Dict[str, Any]
    ) -> None:
        """
        执行单个监听器

        Args:
            handler: 监听器函数
            event_type: 事件类型
            event_data: 事件数据
        """
        handler_name = f"{handler.__module__}.{handler.__name__}"

        try:
            logger.debug(f"执行监听器: {handler_name} for {event_type}")
            await handler(event_type, event_data)
            logger.debug(f"监听器执行成功: {handler_name}")

        except Exception as e:
            logger.exception(
                f"监听器执行失败: {handler_name} for {event_type}, "
                f"错误: {str(e)}"
            )

    def start(self) -> None:
        """启动事件总线"""
        if self._is_started:
            logger.warning("事件总线已经启动")
            return

        self._is_started = True
        logger.info(
            f"事件总线已启动, 已注册 {len(self._listeners)} 个事件类型, "
            f"共 {sum(len(handlers) for handlers in self._listeners.values())} 个监听器"
        )

    def stop(self) -> None:
        """停止事件总线"""
        if not self._is_started:
            logger.warning("事件总线未启动")
            return

        self._is_started = False
        logger.info("事件总线已停止")

    def get_stats(self) -> Dict[str, Any]:
        """
        获取事件总线统计信息

        Returns:
            统计数据
        """
        return {
            "is_started": self._is_started,
            "event_types": list(self._listeners.keys()),
            "total_event_types": len(self._listeners),
            "total_listeners": sum(len(handlers) for handlers in self._listeners.values()),
            "listeners_by_event": {
                event_type: len(handlers)
                for event_type, handlers in self._listeners.items()
            }
        }


# 全局单例实例
event_bus = EventBus()
