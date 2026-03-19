# -*- coding: utf-8 -*-
"""
通知调度服务层

核心调度引擎，负责：
- 接收事件并分发通知
- 根据规则匹配渠道
- 使用模板渲染消息
- 记录发送日志
"""
import asyncio
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.notification_channels import get_channel_adapter
from app.constants.notification import (
    EVENT_PRIORITY_MAPPING,
    NOTIFICATION_SEND_STATUS_FAILED,
    NOTIFICATION_SEND_STATUS_SENT,
    NOTIFICATION_PRIORITY_NORMAL,
)
from app.models.notification import NotificationExternal, NotificationInternal
from app.schemas.notification import NotificationExternalCreate, NotificationInternalCreate
from app.services.notification.notification_channel_service import NotificationChannelService
from app.services.notification.notification_external_service import NotificationExternalService
from app.services.notification.notification_internal_service import NotificationInternalService
from app.services.notification.notification_rule_service import NotificationRuleService
from app.services.notification.notification_template_service import NotificationTemplateService
from app.utils.timezone import now

logger = logging.getLogger(__name__)


class NotificationDispatchService:
    """通知调度服务"""

    @staticmethod
    async def dispatch_event(
        db: AsyncSession,
        event_type: str,
        event_data: Dict[str, Any],
        user_id: Optional[int] = None,
        broadcast: bool = False,
    ) -> Dict[str, Any]:
        """
        调度事件通知

        这是通知系统的核心入口，负责完整的通知流程。

        Args:
            db: 数据库会话
            event_type: 事件类型（如: subscription_matched, download_completed）
            event_data: 事件数据（包含渲染模板所需的变量）
            user_id: 用户ID（广播消息时可为 None）
            broadcast: 是否广播消息（发送给所有用户）

        Returns:
            调度结果统计
            {
                "total_rules": int,       # 匹配到的规则数
                "in_app_sent": int,        # 站内消息发送数
                "channel_sent": int,       # 渠道消息发送数
                "failed": int,             # 失败数
                "skipped": int,            # 跳过数（条件不满足、静默时段、去重）
                "logs": List[int]          # 日志ID列表
            }

        示例:
            # 订阅匹配通知
            await NotificationDispatchService.dispatch_event(
                db,
                event_type="subscription_matched",
                event_data={
                    "media_name": "复仇者联盟4",
                    "quality": "1080p",
                    "size_gb": 15.5,
                    "site_name": "MTeam",
                    "promotion_type": "free"
                },
                user_id=1
            )
        """
        result = {
            "total_rules": 0,
            "in_app_sent": 0,
            "channel_sent": 0,
            "failed": 0,
            "skipped": 0,
            "logs": [],
        }

        # 广播消息：发送站内通知给所有用户
        if broadcast:
            await NotificationDispatchService._send_broadcast_notification(
                db, event_type, event_data
            )
            result["in_app_sent"] = 1
            return result

        # 单用户通知：查找用户的通知规则
        if not user_id:
            logger.warning(f"事件 {event_type} 缺少 user_id，无法发送通知")
            return result

        # 获取用户针对此事件的所有启用规则
        rules = await NotificationRuleService.get_rules_for_event(
            db, user_id, event_type
        )

        result["total_rules"] = len(rules)
        logger.debug(f"[DEBUG] dispatch_event: event_type={event_type}, user_id={user_id}, total_rules={len(rules)}")

        if not rules:
            logger.debug(f"用户 {user_id} 没有配置事件 {event_type} 的通知规则")
            return result

        logger.info(
            f"开始调度通知: event_type={event_type}, user_id={user_id}, rules={len(rules)}"
        )

        # 逐个处理规则
        for rule in rules:
            try:
                # 检查规则条件
                if not NotificationRuleService.check_conditions(rule, event_data):
                    logger.debug(f"规则 {rule.name} 条件不满足，跳过")
                    result["skipped"] += 1
                    continue

                # 检查静默时段
                if NotificationRuleService.is_in_silent_hours(rule):
                    logger.debug(f"规则 {rule.name} 当前在静默时段，跳过")
                    result["skipped"] += 1
                    continue

                # 检查去重
                if await NotificationRuleService.should_deduplicate(
                    db, rule, event_data
                ):
                    logger.debug(f"规则 {rule.name} 触发去重，跳过")
                    result["skipped"] += 1
                    continue

                # 获取并渲染模板
                template = await NotificationTemplateService.get_template_for_event(
                    db,
                    event_type=event_type,
                    user_id=user_id,
                    language=event_data.get("language", "zh-CN"),
                )

                if template:
                    rendered = NotificationTemplateService.render_template(
                        template, event_data
                    )
                    title = rendered["title"]
                    content = rendered["content"]
                else:
                    # 没有模板时使用默认格式
                    title = event_data.get("title", f"通知: {event_type}")
                    content = event_data.get("content", str(event_data))
                    logger.warning(
                        f"未找到事件 {event_type} 的模板，使用默认格式"
                    )

                # 确定优先级 (使用事件类型映射，而非规则优先级)
                # 注意: rule.priority 是规则排序优先级 (1-10 整数)
                # 这里需要的是通知优先级 ("normal", "high", "urgent" 字符串)
                priority = EVENT_PRIORITY_MAPPING.get(
                    event_type, NOTIFICATION_PRIORITY_NORMAL
                )

                # 1. 发送站内通知
                if rule.send_in_app:
                    logger.debug(f"[DEBUG] 规则 {rule.name}: 准备发送站内通知, in_app_sent={result['in_app_sent']}")
                    try:
                        notification = await NotificationInternalService.send_in_app_notification(
                            db,
                            event_type=event_type,
                            title=title,
                            content=content,
                            user_id=user_id,
                            related_type=event_data.get("related_type"),
                            related_id=event_data.get("related_id"),
                            extra_data=event_data,
                            priority=priority,
                        )
                        logger.debug(f"[DEBUG] 规则 {rule.name}: 通知已创建 ID={notification.id}")
                        result["in_app_sent"] += 1
                        logger.debug(f"[DEBUG] 规则 {rule.name}: 站内通知发送成功, in_app_sent={result['in_app_sent']}")
                    except Exception as e:
                        logger.exception(
                            f"规则 {rule.name}: 站内通知发送失败 - {str(e)}"
                        )
                        result["failed"] += 1
                        logger.debug(f"[DEBUG] 规则 {rule.name}: 站内通知发送失败, failed={result['failed']}")

                # 2. 通过外部渠道发送（并发发送优化）
                if rule.channel_ids:
                    # 创建所有渠道的发送任务
                    channel_tasks = [
                        NotificationDispatchService._send_via_channel(
                            db,
                            channel_id=channel_id,
                            user_id=user_id,
                            event_type=event_type,
                            title=title,
                            content=content,
                            priority=priority,
                            extra_data=event_data,
                        )
                        for channel_id in rule.channel_ids
                    ]

                    # 并发执行所有渠道发送，使用 return_exceptions=True 避免单个失败影响其他
                    channel_results = await asyncio.gather(
                        *channel_tasks, return_exceptions=True
                    )

                    # 统计结果
                    for idx, log_id_or_error in enumerate(channel_results):
                        if isinstance(log_id_or_error, Exception):
                            # 发送过程中发生异常
                            logger.error(
                                f"规则 {rule.name} 渠道 {rule.channel_ids[idx]} 发送异常: {log_id_or_error}"
                            )
                            result["failed"] += 1
                        elif log_id_or_error:
                            # 发送成功，返回了日志ID
                            result["logs"].append(log_id_or_error)
                            result["channel_sent"] += 1
                        else:
                            # 发送失败，返回 None
                            result["failed"] += 1

                    logger.debug(
                        f"规则 {rule.name}: 并发发送到 {len(rule.channel_ids)} 个渠道完成"
                    )

            except Exception as e:
                logger.exception(f"处理规则 {rule.name} 时发生异常: {str(e)}")
                result["failed"] += 1

        logger.info(
            f"通知调度完成: event_type={event_type}, "
            f"规则数={result['total_rules']}, "
            f"站内={result['in_app_sent']}, "
            f"渠道={result['channel_sent']}, "
            f"失败={result['failed']}, "
            f"跳过={result['skipped']}"
        )
        logger.debug(f"[DEBUG] dispatch_event: Final result = {result}")

        return result

    @staticmethod
    async def _send_via_channel(
        db: AsyncSession,
        channel_id: int,
        user_id: int,
        event_type: str,
        title: str,
        content: str,
        priority: str,
        extra_data: Optional[Dict[str, Any]] = None,
    ) -> Optional[int]:
        """
        通过指定渠道发送通知

        Args:
            db: 数据库会话
            channel_id: 渠道ID
            user_id: 用户ID
            event_type: 事件类型
            title: 通知标题
            content: 通知内容
            priority: 优先级
            metadata: 元数据

        Returns:
            通知日志ID（发送失败返回 None）
        """
        try:
            # 获取渠道对象
            channel = await NotificationChannelService.get_by_id(db, channel_id)

            # 发送通知
            send_result = await NotificationChannelService.send_via_channel(
                db,
                channel_id=channel_id,
                title=title,
                content=content,
                priority=priority,
            )

            # 记录日志
            log_data = NotificationExternalCreate(
                user_id=user_id,
                channel_id=channel_id,
                channel_type=channel.channel_type if channel else None,
                notification_type=event_type,
                title=title,
                content=content,
                status=(
                    NOTIFICATION_SEND_STATUS_SENT
                    if send_result["success"]
                    else NOTIFICATION_SEND_STATUS_FAILED
                ),
                error_message=(
                    send_result.get("error") if not send_result["success"] else None
                ),
                sent_at=now() if send_result["success"] else None,
                extra_data={
                    **(extra_data or {}),
                    "response": send_result.get("response_data", {}),
                    "message_id": send_result.get("message_id"),
                },
            )

            # 使用 NotificationExternalService 创建日志
            log = await NotificationExternalService.create_log(db, log_data)

            if send_result["success"]:
                logger.info(
                    f"渠道 {channel_id} 发送成功: {title}, 日志ID: {log.id}"
                )
                return log.id
            else:
                logger.error(
                    f"渠道 {channel_id} 发送失败: {title}, 错误: {send_result.get('error')}"
                )
                return None

        except Exception as e:
            logger.exception(f"通过渠道 {channel_id} 发送通知时发生异常: {str(e)}")

            # 尝试记录失败日志
            try:
                # 尝试获取渠道对象(可能失败)
                channel = await NotificationChannelService.get_by_id(db, channel_id)

                log_data = NotificationExternalCreate(
                    user_id=user_id,
                    channel_id=channel_id,
                    channel_type=channel.channel_type if channel else None,
                    notification_type=event_type,
                    title=title,
                    content=content,
                    status=NOTIFICATION_SEND_STATUS_FAILED,
                    error_message=str(e),
                    extra_data=extra_data,
                )
                await NotificationExternalService.create_log(db, log_data)
            except Exception:
                logger.exception("记录失败日志时发生异常")

            return None

    @staticmethod
    async def _send_broadcast_notification(
        db: AsyncSession, event_type: str, event_data: Dict[str, Any]
    ) -> None:
        """
        发送广播通知（站内消息）

        Args:
            db: 数据库会话
            event_type: 事件类型
            event_data: 事件数据
        """
        try:
            # 尝试获取并渲染模板
            template = await NotificationTemplateService.get_template_for_event(
                db,
                event_type=event_type,
                user_id=None,  # 广播消息使用系统模板
                language=event_data.get("language", "zh-CN"),
            )

            if template:
                # 使用模板渲染
                rendered = NotificationTemplateService.render_template(
                    template, event_data
                )
                title = rendered["title"]
                content = rendered["content"]
            else:
                # 没有模板时使用event_data中的字段或默认格式
                title = event_data.get("title", f"系统通知: {event_type}")
                content = event_data.get("content", "")
                logger.warning(
                    f"未找到事件 {event_type} 的广播模板，使用默认格式"
                )

            priority = event_data.get(
                "priority",
                EVENT_PRIORITY_MAPPING.get(event_type, NOTIFICATION_PRIORITY_NORMAL),
            )

            # 直接创建通知对象，避免在 create_notification 中 refresh 后再次访问导致 session 失效
            from app.constants import DEFAULT_NOTIFICATION_EXPIRE_DAYS, NOTIFICATION_STATUS_UNREAD
            from datetime import timedelta

            expires_at = event_data.get("expires_at")
            if expires_at is None:
                expires_at = now() + timedelta(days=DEFAULT_NOTIFICATION_EXPIRE_DAYS)

            notification = NotificationInternal(
                user_id=None,  # 广播消息
                notification_type=event_type,
                title=title,
                content=content,
                priority=priority,
                status=NOTIFICATION_STATUS_UNREAD,
                related_type=event_data.get("related_type"),
                related_id=event_data.get("related_id"),
                extra_data=event_data,
                expires_at=expires_at,
            )

            db.add(notification)
            await db.commit()
            # 不需要 refresh，因为不需要使用这个对象的 ID 等属性

            logger.info(f"广播通知发送成功: {title}")

        except Exception as e:
            logger.exception(f"发送广播通知时发生异常: {str(e)}")

    @staticmethod
    async def send_test_notification(
        db: AsyncSession, channel_id: int, user_id: int
    ) -> Dict[str, Any]:
        """
        发送测试通知

        用于测试通知渠道配置是否正确。

        Args:
            db: 数据库会话
            channel_id: 渠道ID
            user_id: 用户ID

        Returns:
            发送结果
        """
        try:
            # 获取渠道
            channel = await NotificationChannelService.get_by_id(db, channel_id)

            if not channel:
                return {"success": False, "message": "通知渠道不存在"}

            if channel.user_id != user_id:
                return {"success": False, "message": "无权访问此通知渠道"}

            # 发送测试消息
            result = await NotificationChannelService.send_via_channel(
                db,
                channel_id=channel_id,
                title="NasFusion 测试通知",
                content="这是一条测试消息，用于验证通知渠道配置是否正确。如果您收到此消息，说明配置成功！",
                priority=NOTIFICATION_PRIORITY_NORMAL,
            )

            # 记录日志
            log_data = NotificationExternalCreate(
                user_id=user_id,
                channel_id=channel_id,
                channel_type=channel.channel_type if channel else None,
                notification_type="test",
                title="测试通知",
                content="测试消息",
                status=(
                    NOTIFICATION_SEND_STATUS_SENT
                    if result["success"]
                    else NOTIFICATION_SEND_STATUS_FAILED
                ),
                error_message=result.get("error") if not result["success"] else None,
                sent_at=now() if result["success"] else None,
                extra_data={"test": True, "response": result.get("response_data", {})},
            )
            await NotificationExternalService.create_log(db, log_data)

            return result

        except Exception as e:
            logger.exception(f"发送测试通知时发生异常: {str(e)}")
            return {"success": False, "message": f"发送失败: {str(e)}"}
