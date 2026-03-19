# -*- coding: utf-8 -*-
"""
通知调度 API
"""
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.services.notification.notification_dispatch_service import NotificationDispatchService

router = APIRouter(prefix="/notification-dispatch", tags=["notification-dispatch"])
logger = logging.getLogger(__name__)


class DispatchEventRequest(BaseModel):
    """调度事件请求"""

    event_type: str
    event_data: Dict[str, Any]
    user_id: Optional[int] = None
    broadcast: bool = False


class TestNotificationRequest(BaseModel):
    """测试通知请求"""

    channel_id: int


@router.post("/dispatch")
async def dispatch_event(
    request: DispatchEventRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    调度事件通知

    手动触发事件通知，用于测试或特殊场景。

    请求体示例:
    ```json
    {
        "event_type": "subscription_matched",
        "event_data": {
            "media_name": "复仇者联盟4",
            "quality": "1080p",
            "size_gb": 15.5,
            "site_name": "MTeam",
            "promotion_type": "free"
        },
        "user_id": 1,
        "broadcast": false
    }
    ```

    响应示例:
    ```json
    {
        "total_rules": 2,
        "in_app_sent": 1,
        "channel_sent": 2,
        "failed": 0,
        "skipped": 0,
        "logs": [1, 2]
    }
    ```
    """
    try:
        # 如果未指定 user_id，使用当前用户
        if request.user_id is None and not request.broadcast:
            request.user_id = current_user.id

        # 仅管理员可发送广播消息
        if request.broadcast and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="仅管理员可发送广播消息")

        # 调度事件
        result = await NotificationDispatchService.dispatch_event(
            db,
            event_type=request.event_type,
            event_data=request.event_data,
            user_id=request.user_id,
            broadcast=request.broadcast,
        )

        logger.info(
            f"用户 {current_user.username} 手动调度事件: {request.event_type}, 结果: {result}"
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"调度事件时发生异常: {str(e)}")
        raise HTTPException(status_code=500, detail="调度事件失败")


@router.post("/test")
async def send_test_notification(
    request: TestNotificationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    发送测试通知

    向指定渠道发送测试消息，验证配置是否正确。

    请求体示例:
    ```json
    {
        "channel_id": 1
    }
    ```

    响应示例:
    ```json
    {
        "success": true,
        "message": "Telegram 消息发送成功",
        "message_id": "123456"
    }
    ```
    """
    try:
        result = await NotificationDispatchService.send_test_notification(
            db, channel_id=request.channel_id, user_id=current_user.id
        )

        if result["success"]:
            logger.info(
                f"用户 {current_user.username} 测试渠道 {request.channel_id}: 成功"
            )
        else:
            logger.warning(
                f"用户 {current_user.username} 测试渠道 {request.channel_id}: 失败 - {result.get('message')}"
            )

        return result

    except Exception as e:
        logger.exception(f"发送测试通知时发生异常: {str(e)}")
        raise HTTPException(status_code=500, detail="发送测试通知失败")


@router.get("/statistics")
async def get_dispatch_statistics(
    days: int = Query(7, ge=1, le=90, description="统计天数"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取通知发送统计

    查询最近N天的通知发送统计数据。

    - **days**: 统计天数（1-90）

    响应示例:
    ```json
    {
        "total": 150,
        "success": 145,
        "failed": 5,
        "success_rate": 96.67,
        "days": 7,
        "by_event_type": [
            {"event_type": "subscription_matched", "count": 80},
            {"event_type": "download_completed", "count": 60}
        ],
        "by_channel": [
            {"channel_id": 1, "count": 100},
            {"channel_id": 2, "count": 45}
        ]
    }
    ```
    """
    try:
        statistics = await NotificationDispatchService.get_dispatch_statistics(
            db, user_id=current_user.id, days=days
        )

        return statistics

    except Exception as e:
        logger.exception(f"获取通知统计时发生异常: {str(e)}")
        raise HTTPException(status_code=500, detail="获取通知统计失败")
