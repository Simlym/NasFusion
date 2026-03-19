# -*- coding: utf-8 -*-
"""
通知系统 API
"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.notification import (
    NotificationMarkAsReadRequest,
    NotificationQuery,
    NotificationInternalCreate,
    NotificationInternalListResponse,
    NotificationInternalResponse,
    NotificationInternalUpdate,
    NotificationExternalListResponse,
    NotificationExternalResponse,
    UnreadCountResponse,
)
from app.services.notification.notification_internal_service import NotificationInternalService
from app.services.notification.notification_external_service import NotificationExternalService

router = APIRouter(prefix="/notifications", tags=["通知系统"])


@router.get(
    "/unread-count",
    response_model=UnreadCountResponse,
    summary="获取未读消息数量",
)
async def get_unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取当前用户未读消息数量"""
    count = await NotificationInternalService.get_unread_count(db, current_user.id)
    return UnreadCountResponse(count=count)


@router.get(
    "",
    response_model=NotificationInternalListResponse,
    summary="获取通知列表",
)
async def get_notifications(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    status: Optional[str] = Query(None, description="状态筛选: unread/read/archived"),
    notification_type: Optional[str] = Query(None, description="通知类型筛选"),
    priority: Optional[str] = Query(None, description="优先级筛选: low/normal/high/urgent"),
    start_date: Optional[datetime] = Query(None, description="开始日期"),
    end_date: Optional[datetime] = Query(None, description="结束日期"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取当前用户的通知列表

    - 包含用户专属通知和系统广播通知
    - 自动过滤已过期的通知
    - 支持分页、状态筛选、类型筛选、优先级筛选
    """
    skip = (page - 1) * page_size

    notifications, total = await NotificationInternalService.get_user_notifications(
        db=db,
        user_id=current_user.id,
        skip=skip,
        limit=page_size,
        status=status,
        notification_type=notification_type,
        priority=priority,
        start_date=start_date,
        end_date=end_date,
        include_broadcast=True,
    )

    # 获取未读数量
    unread_count = await NotificationInternalService.get_unread_count(db, current_user.id)

    # 转换为 Pydantic 模型
    items = [NotificationInternalResponse.model_validate(n) for n in notifications]

    return NotificationInternalListResponse(
        total=total, items=items, unread_count=unread_count
    )


# ============================================================================
# 站外通知历史 API (External Notifications History)
# ============================================================================
# 注意：这些路由必须在 /{notification_id} 之前定义，避免路由冲突


@router.get(
    "/external",
    response_model=NotificationExternalListResponse,
    summary="获取站外通知历史",
)
async def get_external_notifications(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    status: Optional[str] = Query(None, description="状态筛选: pending/sent/failed"),
    channel_type: Optional[str] = Query(None, description="渠道类型筛选: telegram/email/webhook"),
    notification_type: Optional[str] = Query(None, description="通知类型筛选"),
    start_date: Optional[datetime] = Query(None, description="开始日期"),
    end_date: Optional[datetime] = Query(None, description="结束日期"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取站外通知历史记录

    - 查询通过外部渠道（Telegram/Email/Webhook）发送的通知
    - 支持按状态、渠道类型、通知类型、日期范围筛选
    - 支持分页查询
    """
    skip = (page - 1) * page_size

    # 使用 NotificationExternalService 查询
    logs, total = await NotificationExternalService.get_user_logs(
        db=db,
        user_id=current_user.id,
        skip=skip,
        limit=page_size,
        status=status,
        channel_type=channel_type,
        notification_type=notification_type,
        start_date=start_date,
        end_date=end_date,
    )

    # 转换为 Pydantic 模型
    items = [NotificationExternalResponse.model_validate(log) for log in logs]

    return NotificationExternalListResponse(total=total, items=items)


@router.get(
    "/external/{notification_id}",
    response_model=NotificationExternalResponse,
    summary="获取站外通知详情",
)
async def get_external_notification(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取单个站外通知的详细信息"""
    # 使用 NotificationExternalService 查询
    notification = await NotificationExternalService.get_by_id(db, notification_id)

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"站外通知 {notification_id} 不存在"
        )

    # 权限检查：只能查看自己的通知
    if notification.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权限访问此通知"
        )

    return NotificationExternalResponse.model_validate(notification)


# ============================================================================
# 站内通知 API (Internal Notifications)
# ============================================================================


@router.get(
    "/{notification_id}",
    response_model=NotificationInternalResponse,
    summary="获取通知详情",
)
async def get_notification(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取单个通知的详细信息"""
    notification = await NotificationInternalService.get_by_id(db, notification_id)

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"通知 {notification_id} 不存在"
        )

    # 权限检查：只能查看自己的通知或系统广播
    if notification.user_id is not None and notification.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="无权限访问此通知"
        )

    return NotificationInternalResponse.model_validate(notification)


@router.post(
    "",
    response_model=NotificationInternalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建通知（仅管理员）",
)
async def create_notification(
    notification_data: NotificationInternalCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    创建系统内通知（仅管理员）

    - 管理员可创建任意用户的通知或系统广播
    - 普通用户只能创建自己的通知
    """
    # 权限检查
    if not current_user.is_admin:
        # 普通用户只能创建自己的通知
        if notification_data.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="普通用户只能创建自己的通知"
            )

    notification = await NotificationInternalService.create_notification(db, notification_data)
    return NotificationInternalResponse.model_validate(notification)


@router.put(
    "/{notification_id}/read",
    response_model=NotificationInternalResponse,
    summary="标记通知为已读",
)
async def mark_notification_as_read(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """标记单个通知为已读"""
    notification = await NotificationInternalService.mark_as_read(
        db, notification_id, user_id=current_user.id
    )

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="通知不存在或无权限访问"
        )

    return NotificationInternalResponse.model_validate(notification)


@router.put(
    "/read-all",
    summary="标记所有通知为已读",
)
async def mark_all_as_read(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """标记当前用户所有未读通知为已读"""
    count = await NotificationInternalService.mark_all_as_read(db, current_user.id)

    return {"message": f"成功标记 {count} 条通知为已读", "count": count}


@router.post(
    "/mark-read",
    summary="批量标记通知为已读",
)
async def mark_notifications_as_read(
    request: NotificationMarkAsReadRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """批量标记指定通知为已读"""
    success_count = 0
    failed_ids = []

    for notification_id in request.notification_ids:
        notification = await NotificationInternalService.mark_as_read(
            db, notification_id, user_id=current_user.id
        )
        if notification:
            success_count += 1
        else:
            failed_ids.append(notification_id)

    return {
        "message": f"成功标记 {success_count} 条通知为已读",
        "success_count": success_count,
        "failed_ids": failed_ids,
    }


@router.put(
    "/{notification_id}",
    response_model=NotificationInternalResponse,
    summary="更新通知",
)
async def update_notification(
    notification_id: int,
    update_data: NotificationInternalUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新通知状态或内容（仅限用户自己的通知）"""
    notification = await NotificationInternalService.update_notification(
        db, notification_id, update_data, user_id=current_user.id
    )

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="通知不存在或无权限修改"
        )

    return NotificationInternalResponse.model_validate(notification)


@router.delete(
    "/{notification_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除通知",
)
async def delete_notification(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除通知（仅限用户自己的通知）"""
    success = await NotificationInternalService.delete_notification(
        db, notification_id, user_id=current_user.id
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="通知不存在或无权限删除"
        )

    return None


@router.post(
    "/cleanup-expired",
    summary="清理过期通知（仅管理员）",
)
async def cleanup_expired_notifications(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """清理所有过期的通知（仅管理员）"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="仅管理员可执行此操作"
        )

    count = await NotificationInternalService.cleanup_expired(db)

    return {"message": f"成功清理 {count} 条过期通知", "count": count}


@router.post(
    "/archive-old",
    summary="归档旧通知",
)
async def archive_old_notifications(
    days_old: int = Query(30, ge=1, le=365, description="多少天前的已读通知"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """归档当前用户指定天数前的已读通知"""
    count = await NotificationInternalService.archive_read_notifications(
        db, current_user.id, days_old
    )

    return {"message": f"成功归档 {count} 条旧通知", "count": count}
