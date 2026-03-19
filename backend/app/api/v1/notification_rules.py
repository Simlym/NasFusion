# -*- coding: utf-8 -*-
"""
通知规则 API
"""
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.notification import (
    NotificationRuleCreate,
    NotificationRuleListResponse,
    NotificationRuleResponse,
    NotificationRuleUpdate,
)
from app.services.notification.notification_rule_service import NotificationRuleService

router = APIRouter(prefix="/notification-rules", tags=["notification-rules"])
logger = logging.getLogger(__name__)


@router.post("", response_model=NotificationRuleResponse, status_code=201)
async def create_notification_rule(
    rule_data: NotificationRuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    创建通知规则

    创建新的通知规则，用于配置事件通知行为。

    - **event_type**: 事件类型
    - **channels**: 通知渠道 ID 列表
    - **enabled**: 是否启用
    - **priority**: 优先级过滤（可选）
    - **conditions**: 触发条件（可选）
    - **silent_hours**: 静默时段（可选）
    - **deduplication_window**: 去重窗口时间（秒）
    """
    try:
        # 设置用户 ID
        rule_data.user_id = current_user.id

        rule = await NotificationRuleService.create_rule(db, rule_data)

        logger.info(
            f"用户 {current_user.username} 创建通知规则: {rule.event_type}, 规则ID: {rule.id}"
        )

        return rule

    except ValueError as e:
        logger.warning(f"创建通知规则失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.exception(f"创建通知规则时发生异常: {str(e)}")
        raise HTTPException(status_code=500, detail="创建通知规则失败")


@router.get("", response_model=NotificationRuleListResponse)
async def get_notification_rules(
    event_type: Optional[str] = Query(None, description="事件类型筛选"),
    enabled: Optional[bool] = Query(None, description="启用状态筛选"),
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(20, ge=1, le=100, description="返回记录数"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取通知规则列表

    查询当前用户的通知规则，支持筛选和分页。

    - **event_type**: 按事件类型筛选（可选）
    - **enabled**: 按启用状态筛选（可选）
    - **skip**: 跳过记录数（分页）
    - **limit**: 返回记录数（分页）
    """
    try:
        rules = await NotificationRuleService.get_user_rules(
            db,
            user_id=current_user.id,
            event_type=event_type,
            enabled=enabled,
            skip=skip,
            limit=limit,
        )

        total = await NotificationRuleService.count_user_rules(
            db, user_id=current_user.id, event_type=event_type, enabled=enabled
        )

        return NotificationRuleListResponse(total=total, items=rules)

    except Exception as e:
        logger.exception(f"获取通知规则列表时发生异常: {str(e)}")
        raise HTTPException(status_code=500, detail="获取通知规则列表失败")


@router.get("/{rule_id}", response_model=NotificationRuleResponse)
async def get_notification_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取通知规则详情

    根据规则 ID 获取详细信息。
    """
    try:
        rule = await NotificationRuleService.get_by_id(db, rule_id)

        if not rule:
            raise HTTPException(status_code=404, detail="通知规则不存在")

        # 检查权限
        if rule.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="无权访问此通知规则")

        return rule

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"获取通知规则详情时发生异常: {str(e)}")
        raise HTTPException(status_code=500, detail="获取通知规则详情失败")


@router.put("/{rule_id}", response_model=NotificationRuleResponse)
async def update_notification_rule(
    rule_id: int,
    update_data: NotificationRuleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    更新通知规则

    更新现有通知规则的配置信息。

    - **enabled**: 是否启用
    - **channels**: 通知渠道列表
    - **priority**: 优先级过滤
    - **conditions**: 触发条件
    - **silent_hours**: 静默时段
    - **deduplication_window**: 去重窗口时间
    """
    try:
        # 检查规则是否存在
        existing_rule = await NotificationRuleService.get_by_id(db, rule_id)

        if not existing_rule:
            raise HTTPException(status_code=404, detail="通知规则不存在")

        # 检查权限
        if existing_rule.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="无权修改此通知规则")

        # 更新规则
        updated_rule = await NotificationRuleService.update_rule(
            db, rule_id, update_data
        )

        if not updated_rule:
            raise HTTPException(status_code=404, detail="通知规则不存在")

        logger.info(f"用户 {current_user.username} 更新通知规则: {rule_id}")

        return updated_rule

    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"更新通知规则失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"更新通知规则时发生异常: {str(e)}")
        raise HTTPException(status_code=500, detail="更新通知规则失败")


@router.delete("/{rule_id}")
async def delete_notification_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    删除通知规则

    删除指定的通知规则。
    """
    try:
        # 检查规则是否存在
        existing_rule = await NotificationRuleService.get_by_id(db, rule_id)

        if not existing_rule:
            raise HTTPException(status_code=404, detail="通知规则不存在")

        # 检查权限
        if existing_rule.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="无权删除此通知规则")

        # 删除规则
        success = await NotificationRuleService.delete_rule(db, rule_id)

        if not success:
            raise HTTPException(status_code=404, detail="通知规则不存在")

        logger.info(f"用户 {current_user.username} 删除通知规则: {rule_id}")

        return {"message": "通知规则已删除"}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"删除通知规则时发生异常: {str(e)}")
        raise HTTPException(status_code=500, detail="删除通知规则失败")


@router.post("/{rule_id}/test")
async def test_notification_rule(
    rule_id: int,
    event_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    测试通知规则

    使用示例事件数据测试规则的触发条件和静默时段。

    请求体示例:
    ```json
    {
        "size_bytes": 5368709120,
        "quality": "1080p",
        "promotion_type": "free",
        "site_id": 1,
        "media_type": "movie"
    }
    ```

    响应示例:
    ```json
    {
        "rule_id": 1,
        "event_type": "subscription_matched",
        "should_notify": true,
        "conditions_met": true,
        "in_silent_hours": false,
        "would_deduplicate": false,
        "details": {
            "size_gb": 5.0,
            "quality_matched": true,
            "promotion_matched": true
        }
    }
    ```
    """
    try:
        # 检查规则是否存在
        rule = await NotificationRuleService.get_by_id(db, rule_id)

        if not rule:
            raise HTTPException(status_code=404, detail="通知规则不存在")

        # 检查权限
        if rule.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="无权测试此通知规则")

        # 检查条件是否满足
        conditions_met = NotificationRuleService.check_conditions(rule, event_data)

        # 检查是否在静默时段
        in_silent_hours = NotificationRuleService.is_in_silent_hours(rule)

        # 检查是否会被去重
        would_deduplicate = await NotificationRuleService.should_deduplicate(
            db, rule, event_data
        )

        # 判断是否应该发送通知
        should_notify = (
            rule.enabled and conditions_met and not in_silent_hours and not would_deduplicate
        )

        # 构建详细信息
        details = {}
        if rule.conditions:
            # 文件大小检查
            if "min_size_gb" in rule.conditions:
                size_gb = event_data.get("size_bytes", 0) / (1024**3)
                details["size_gb"] = round(size_gb, 2)
                details["size_check"] = size_gb >= rule.conditions["min_size_gb"]

            if "max_size_gb" in rule.conditions:
                size_gb = event_data.get("size_bytes", 0) / (1024**3)
                details["size_gb"] = round(size_gb, 2)
                details["size_check"] = size_gb <= rule.conditions["max_size_gb"]

            # 质量检查
            if "quality" in rule.conditions:
                details["quality_matched"] = (
                    event_data.get("quality") in rule.conditions["quality"]
                )

            # 促销类型检查
            if "promotion_type" in rule.conditions:
                details["promotion_matched"] = (
                    event_data.get("promotion_type")
                    in rule.conditions["promotion_type"]
                )

            # 站点检查
            if "site_ids" in rule.conditions:
                details["site_matched"] = (
                    event_data.get("site_id") in rule.conditions["site_ids"]
                )

            # 媒体类型检查
            if "media_types" in rule.conditions:
                details["media_type_matched"] = (
                    event_data.get("media_type") in rule.conditions["media_types"]
                )

        logger.info(
            f"用户 {current_user.username} 测试通知规则 {rule_id}: should_notify={should_notify}"
        )

        return {
            "rule_id": rule_id,
            "event_type": rule.event_type,
            "should_notify": should_notify,
            "conditions_met": conditions_met,
            "in_silent_hours": in_silent_hours,
            "would_deduplicate": would_deduplicate,
            "details": details,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"测试通知规则时发生异常: {str(e)}")
        raise HTTPException(status_code=500, detail="测试通知规则失败")


@router.post("/{rule_id}/toggle")
async def toggle_notification_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    切换通知规则启用状态

    快速启用/禁用通知规则。
    """
    try:
        # 检查规则是否存在
        rule = await NotificationRuleService.get_by_id(db, rule_id)

        if not rule:
            raise HTTPException(status_code=404, detail="通知规则不存在")

        # 检查权限
        if rule.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="无权修改此通知规则")

        # 切换状态
        update_data = NotificationRuleUpdate(enabled=not rule.enabled)
        updated_rule = await NotificationRuleService.update_rule(
            db, rule_id, update_data
        )

        logger.info(
            f"用户 {current_user.username} 切换通知规则 {rule_id} 状态: {updated_rule.enabled}"
        )

        return {
            "rule_id": rule_id,
            "enabled": updated_rule.enabled,
            "message": f"通知规则已{'启用' if updated_rule.enabled else '禁用'}",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"切换通知规则状态时发生异常: {str(e)}")
        raise HTTPException(status_code=500, detail="切换通知规则状态失败")
