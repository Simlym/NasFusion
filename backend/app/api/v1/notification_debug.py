# -*- coding: utf-8 -*-
"""
通知系统调试接口

提供调试工具和诊断功能,帮助排查通知系统问题。
"""
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.events.bus import event_bus
from app.events.manager import event_bus_manager
from app.services.notification.notification_dispatch_service import NotificationDispatchService
from app.services.notification.notification_rule_service import NotificationRuleService

router = APIRouter(prefix="/notification-debug", tags=["notification-debug"])
logger = logging.getLogger(__name__)


@router.get("/stats")
async def get_notification_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取通知系统统计信息

    包括:
    - 事件总线状态
    - 监听器数量
    - 通知规则数量
    - 最近的通知日志
    """
    try:
        # 事件总线统计
        event_bus_stats = event_bus_manager.get_stats()

        # 用户的通知规则数量
        user_rules = await NotificationRuleService.get_user_rules(
            db, user_id=current_user.id
        )
        enabled_rules = [r for r in user_rules if r.enabled]

        # 统计每个事件类型的规则数
        event_rule_count = {}
        for rule in user_rules:
            event_type = rule.event_type
            if event_type not in event_rule_count:
                event_rule_count[event_type] = {"total": 0, "enabled": 0}
            event_rule_count[event_type]["total"] += 1
            if rule.enabled:
                event_rule_count[event_type]["enabled"] += 1

        return {
            "event_bus": event_bus_stats,
            "user_rules": {
                "total": len(user_rules),
                "enabled": len(enabled_rules),
                "disabled": len(user_rules) - len(enabled_rules),
                "by_event_type": event_rule_count,
            },
            "user_id": current_user.id,
            "username": current_user.username,
        }

    except Exception as e:
        logger.exception(f"获取通知统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取统计信息失败")


@router.post("/test-event")
async def test_notification_event(
    event_type: str = Query(..., description="事件类型"),
    test_data: Optional[Dict[str, Any]] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    测试发送通知事件

    手动触发一个通知事件,用于测试通知规则是否正常工作。

    示例:
    ```
    POST /api/v1/notification-debug/test-event?event_type=task_completed
    {
        "task_name": "测试任务",
        "duration": "5秒",
        "result": "成功"
    }
    ```
    """
    try:
        # 默认测试数据
        if test_data is None:
            test_data = {}

        # 添加用户ID(用于单用户通知)
        event_data = {
            "user_id": current_user.id,
            **test_data,
        }

        # 为不同事件类型提供默认测试数据
        if event_type == "task_completed" and not test_data:
            event_data.update({
                "task_name": "测试任务",
                "duration": "5秒",
                "result": "测试成功",
            })
        elif event_type == "download_completed" and not test_data:
            event_data.update({
                "media_name": "测试媒体",
                "size_gb": 10.5,
                "save_path": "/data/downloads/test.mkv",
                "duration": "10分钟",
                "ratio": 1.0,
            })
        elif event_type == "subscription_matched" and not test_data:
            event_data.update({
                "media_name": "测试订阅",
                "quality": "1080p",
                "size_gb": 5.2,
                "site_name": "测试站点",
                "promotion_type": "免费",
                "seeders": 100,
                "leechers": 10,
            })

        # 发布事件
        await event_bus.publish(event_type, event_data)

        logger.info(
            f"用户 {current_user.username} 测试发送事件: {event_type}, 数据: {event_data}"
        )

        return {
            "message": "测试事件已发送",
            "event_type": event_type,
            "event_data": event_data,
            "note": "请检查系统内消息或配置的通知渠道",
        }

    except Exception as e:
        logger.exception(f"测试事件发送失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"发送测试事件失败: {str(e)}")


@router.post("/dispatch-event")
async def dispatch_notification_event(
    event_data: Dict[str, Any],
    event_type: str = Query(..., description="事件类型"),
    broadcast: bool = Query(False, description="是否广播"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    直接调度通知事件(绕过事件总线)

    用于调试通知调度服务,直接调用 NotificationDispatchService。

    示例:
    ```
    POST /api/v1/notification-debug/dispatch-event?event_type=task_completed
    {
        "task_name": "测试任务",
        "duration": "5秒",
        "result": "成功"
    }
    ```
    """
    try:
        # 调度通知
        result = await NotificationDispatchService.dispatch_event(
            db,
            event_type=event_type,
            event_data=event_data,
            user_id=current_user.id if not broadcast else None,
            broadcast=broadcast,
        )

        logger.info(
            f"用户 {current_user.username} 直接调度事件: {event_type}, "
            f"结果: {result}"
        )

        return {
            "message": "通知调度完成",
            "event_type": event_type,
            "dispatch_result": result,
        }

    except Exception as e:
        logger.exception(f"调度通知失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"调度通知失败: {str(e)}")


@router.get("/check-rule/{rule_id}")
async def check_notification_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    检查通知规则配置

    显示规则的详细配置和可能的问题。
    """
    try:
        rule = await NotificationRuleService.get_by_id(db, rule_id)

        if not rule:
            raise HTTPException(status_code=404, detail="通知规则不存在")

        # 检查权限
        if rule.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="无权访问此规则")

        # 诊断信息
        diagnostics = {
            "rule_id": rule.id,
            "rule_name": rule.name,
            "enabled": rule.enabled,
            "event_type": rule.event_type,
            "send_in_app": rule.send_in_app,
            "channel_ids": rule.channel_ids,
            "template_id": rule.template_id,
            "issues": [],
        }

        # 检查问题
        if not rule.enabled:
            diagnostics["issues"].append("❌ 规则未启用")

        if not rule.send_in_app and not rule.channel_ids:
            diagnostics["issues"].append("❌ 未配置任何通知渠道(站内消息和外部渠道都未启用)")

        if rule.channel_ids:
            diagnostics["issues"].append(
                f"⚠️ 配置了 {len(rule.channel_ids)} 个外部渠道(需检查渠道状态)"
            )

        if not rule.template_id:
            diagnostics["issues"].append("⚠️ 未指定模板(将使用系统默认模板)")

        if not diagnostics["issues"]:
            diagnostics["issues"].append("✅ 配置正常")

        return diagnostics

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"检查规则失败: {str(e)}")
        raise HTTPException(status_code=500, detail="检查规则失败")
