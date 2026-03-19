# -*- coding: utf-8 -*-
"""
通知渠道 API
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.notification import NotificationChannel
from app.models.user import User
from app.schemas.notification import (
    NotificationChannelCreate,
    NotificationChannelListResponse,
    NotificationChannelResponse,
    NotificationChannelTestResponse,
    NotificationChannelUpdate,
)
from app.services.notification.notification_channel_service import NotificationChannelService
from app.utils.timezone import now

router = APIRouter(prefix="/notification-channels", tags=["notification-channels"])
logger = logging.getLogger(__name__)


@router.get("", response_model=NotificationChannelListResponse)
async def get_notification_channels(
    channel_type: Optional[str] = Query(None, description="渠道类型筛选"),
    enabled: Optional[bool] = Query(None, description="启用状态筛选"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取通知渠道列表

    查询当前用户的通知渠道，支持筛选。

    - **channel_type**: 按渠道类型筛选（可选）
    - **enabled**: 按启用状态筛选（可选）
    """
    try:
        channels = await NotificationChannelService.get_user_channels(
            db,
            user_id=current_user.id,
            enabled_only=enabled if enabled is not None else False,
            channel_type=channel_type,
        )

        # 转换为响应模型
        items = [NotificationChannelResponse.model_validate(ch) for ch in channels]

        return NotificationChannelListResponse(total=len(items), items=items)

    except Exception as e:
        logger.exception(f"获取通知渠道列表失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取通知渠道列表失败",
        )


@router.get("/{channel_id}", response_model=NotificationChannelResponse)
async def get_notification_channel(
    channel_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取通知渠道详情"""
    channel = await NotificationChannelService.get_by_id(db, channel_id)

    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"通知渠道 {channel_id} 不存在",
        )

    # 权限检查：只能查看自己的渠道
    if channel.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="无权限访问此渠道"
        )

    return NotificationChannelResponse.model_validate(channel)


@router.post(
    "", response_model=NotificationChannelResponse, status_code=status.HTTP_201_CREATED
)
async def create_notification_channel(
    channel_data: NotificationChannelCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    创建通知渠道

    创建新的通知渠道配置。

    - **name**: 渠道名称
    - **channel_type**: 渠道类型 (telegram/email/webhook)
    - **config**: 渠道配置（根据类型不同配置不同）
    - **enabled**: 是否启用
    """
    try:
        # 创建渠道
        channel = NotificationChannel(
            user_id=current_user.id,
            name=channel_data.name,
            channel_type=channel_data.channel_type,
            config=channel_data.config,
            enabled=channel_data.enabled,
            priority=channel_data.priority,
            description=channel_data.description,
        )

        db.add(channel)
        await db.commit()
        await db.refresh(channel)

        logger.info(
            f"用户 {current_user.username} 创建通知渠道: {channel.name}, 类型: {channel.channel_type}"
        )

        return NotificationChannelResponse.model_validate(channel)

    except Exception as e:
        await db.rollback()
        logger.exception(f"创建通知渠道失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建通知渠道失败",
        )


@router.put("/{channel_id}", response_model=NotificationChannelResponse)
async def update_notification_channel(
    channel_id: int,
    channel_data: NotificationChannelUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    更新通知渠道

    更新现有通知渠道的配置。
    """
    try:
        # 查询渠道
        channel = await NotificationChannelService.get_by_id(db, channel_id)

        if not channel:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"通知渠道 {channel_id} 不存在",
            )

        # 权限检查：只能修改自己的渠道
        if channel.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="无权限修改此渠道"
            )

        # 更新字段
        update_data = channel_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(channel, field, value)

        channel.updated_at = now()
        await db.commit()
        await db.refresh(channel)

        logger.info(
            f"用户 {current_user.username} 更新通知渠道: {channel.name} (ID: {channel_id})"
        )

        return NotificationChannelResponse.model_validate(channel)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.exception(f"更新通知渠道失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新通知渠道失败",
        )


@router.delete("/{channel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification_channel(
    channel_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    删除通知渠道

    删除指定的通知渠道。
    """
    try:
        # 查询渠道
        channel = await NotificationChannelService.get_by_id(db, channel_id)

        if not channel:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"通知渠道 {channel_id} 不存在",
            )

        # 权限检查：只能删除自己的渠道
        if channel.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="无权限删除此渠道"
            )

        await db.delete(channel)
        await db.commit()

        logger.info(
            f"用户 {current_user.username} 删除通知渠道: {channel.name} (ID: {channel_id})"
        )

        return None

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.exception(f"删除通知渠道失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除通知渠道失败",
        )


@router.post("/{channel_id}/test", response_model=NotificationChannelTestResponse)
async def test_notification_channel(
    channel_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    测试通知渠道

    测试指定渠道的连接和配置是否正确。
    """
    try:
        # 查询渠道
        channel = await NotificationChannelService.get_by_id(db, channel_id)

        if not channel:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"通知渠道 {channel_id} 不存在",
            )

        # 权限检查：只能测试自己的渠道
        if channel.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="无权限测试此渠道"
            )

        # 执行测试
        test_result = await NotificationChannelService.test_channel(db, channel_id)

        logger.info(
            f"用户 {current_user.username} 测试通知渠道: {channel.name}, 结果: {test_result['success']}"
        )

        return NotificationChannelTestResponse(**test_result)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"测试通知渠道失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"测试通知渠道失败: {str(e)}",
        )
