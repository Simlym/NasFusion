# -*- coding: utf-8 -*-
"""
通知规则服务层
"""
import logging
from datetime import datetime, time, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import NotificationExternal, NotificationRule
from app.schemas.notification import NotificationRuleCreate, NotificationRuleUpdate
from app.utils.timezone import now

logger = logging.getLogger(__name__)


class NotificationRuleService:
    """通知规则服务"""

    @staticmethod
    async def create_rule(
        db: AsyncSession, rule_data: NotificationRuleCreate
    ) -> NotificationRule:
        """
        创建通知规则

        Args:
            db: 数据库会话
            rule_data: 规则数据

        Returns:
            创建的规则记录
        """
        rule = NotificationRule(
            user_id=rule_data.user_id,
            name=rule_data.name,
            enabled=rule_data.enabled,
            event_type=rule_data.event_type,
            conditions=rule_data.conditions,
            channel_ids=rule_data.channel_ids,
            send_in_app=rule_data.send_in_app,
            template_id=rule_data.template_id,
            silent_hours=rule_data.silent_hours,
            deduplication_window=rule_data.deduplication_window,
            priority=rule_data.priority,
        )

        db.add(rule)
        await db.commit()
        await db.refresh(rule)

        logger.info(
            f"创建通知规则: {rule.name} (用户ID: {rule.user_id}, 事件: {rule.event_type})"
        )
        return rule

    @staticmethod
    async def get_by_id(db: AsyncSession, rule_id: int) -> Optional[NotificationRule]:
        """根据ID获取规则"""
        result = await db.execute(
            select(NotificationRule).where(NotificationRule.id == rule_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_rules(
        db: AsyncSession,
        user_id: int,
        enabled: Optional[bool] = None,
        event_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[NotificationRule]:
        """
        获取用户的通知规则列表

        Args:
            db: 数据库会话
            user_id: 用户ID
            enabled: 启用状态筛选（None 表示不筛选）
            event_type: 事件类型筛选
            skip: 跳过记录数
            limit: 返回记录数

        Returns:
            规则列表
        """
        query = select(NotificationRule).where(NotificationRule.user_id == user_id)

        if enabled is not None:
            query = query.where(NotificationRule.enabled == enabled)

        if event_type:
            query = query.where(NotificationRule.event_type == event_type)

        # 按优先级倒序排序
        query = query.order_by(NotificationRule.priority.desc())

        # 分页
        query = query.offset(skip).limit(limit)

        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def count_user_rules(
        db: AsyncSession,
        user_id: int,
        enabled: Optional[bool] = None,
        event_type: Optional[str] = None,
    ) -> int:
        """
        统计用户的通知规则数量

        Args:
            db: 数据库会话
            user_id: 用户ID
            enabled: 启用状态筛选（None 表示不筛选）
            event_type: 事件类型筛选

        Returns:
            规则数量
        """
        query = select(func.count(NotificationRule.id)).where(
            NotificationRule.user_id == user_id
        )

        if enabled is not None:
            query = query.where(NotificationRule.enabled == enabled)

        if event_type:
            query = query.where(NotificationRule.event_type == event_type)

        result = await db.execute(query)
        return result.scalar_one()

    @staticmethod
    async def get_rules_for_event(
        db: AsyncSession, user_id: int, event_type: str
    ) -> List[NotificationRule]:
        """
        获取事件对应的启用规则

        Args:
            db: 数据库会话
            user_id: 用户ID
            event_type: 事件类型

        Returns:
            匹配的规则列表
        """
        return await NotificationRuleService.get_user_rules(
            db, user_id, enabled=True, event_type=event_type
        )

    @staticmethod
    async def update_rule(
        db: AsyncSession, rule_id: int, update_data: NotificationRuleUpdate
    ) -> Optional[NotificationRule]:
        """
        更新通知规则

        Args:
            db: 数据库会话
            rule_id: 规则ID
            update_data: 更新数据

        Returns:
            更新后的规则记录
        """
        rule = await NotificationRuleService.get_by_id(db, rule_id)

        if not rule:
            return None

        # 更新字段
        update_dict = update_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(rule, key, value)

        await db.commit()
        await db.refresh(rule)

        logger.info(f"更新通知规则: {rule.name} (ID: {rule.id})")
        return rule

    @staticmethod
    async def delete_rule(db: AsyncSession, rule_id: int) -> bool:
        """
        删除通知规则

        Args:
            db: 数据库会话
            rule_id: 规则ID

        Returns:
            是否删除成功
        """
        rule = await NotificationRuleService.get_by_id(db, rule_id)

        if not rule:
            return False

        await db.delete(rule)
        await db.commit()

        logger.info(f"删除通知规则: {rule.name} (ID: {rule.id})")
        return True

    @staticmethod
    def check_conditions(
        rule: NotificationRule, event_data: Dict[str, Any]
    ) -> bool:
        """
        检查事件数据是否满足规则条件

        Args:
            rule: 通知规则
            event_data: 事件数据

        Returns:
            是否满足条件
        """
        if not rule.conditions:
            # 无条件限制，直接通过
            return True

        conditions = rule.conditions

        # 检查文件大小条件
        if "min_size_gb" in conditions:
            size = event_data.get("size_bytes", 0)
            size_gb = size / (1024**3) if size else 0
            if size_gb < conditions["min_size_gb"]:
                logger.debug(
                    f"规则 {rule.name}: 文件大小不满足 ({size_gb:.2f}GB < {conditions['min_size_gb']}GB)"
                )
                return False

        if "max_size_gb" in conditions:
            size = event_data.get("size_bytes", 0)
            size_gb = size / (1024**3) if size else 0
            if size_gb > conditions["max_size_gb"]:
                logger.debug(
                    f"规则 {rule.name}: 文件大小超限 ({size_gb:.2f}GB > {conditions['max_size_gb']}GB)"
                )
                return False

        # 检查质量条件
        if "quality" in conditions and event_data.get("quality"):
            allowed_qualities = conditions["quality"]
            if isinstance(allowed_qualities, list):
                if event_data["quality"] not in allowed_qualities:
                    logger.debug(
                        f"规则 {rule.name}: 质量不匹配 ({event_data['quality']} not in {allowed_qualities})"
                    )
                    return False

        # 检查促销类型条件
        if "promotion_types" in conditions and event_data.get("promotion_type"):
            allowed_promotions = conditions["promotion_types"]
            if isinstance(allowed_promotions, list):
                if event_data["promotion_type"] not in allowed_promotions:
                    logger.debug(
                        f"规则 {rule.name}: 促销类型不匹配 ({event_data['promotion_type']} not in {allowed_promotions})"
                    )
                    return False

        # 检查站点条件
        if "sites" in conditions and event_data.get("site_name"):
            allowed_sites = conditions["sites"]
            if isinstance(allowed_sites, list):
                if event_data["site_name"] not in allowed_sites:
                    logger.debug(
                        f"规则 {rule.name}: 站点不匹配 ({event_data['site_name']} not in {allowed_sites})"
                    )
                    return False

        # 检查媒体类型条件
        if "media_types" in conditions and event_data.get("media_type"):
            allowed_types = conditions["media_types"]
            if isinstance(allowed_types, list):
                if event_data["media_type"] not in allowed_types:
                    logger.debug(
                        f"规则 {rule.name}: 媒体类型不匹配 ({event_data['media_type']} not in {allowed_types})"
                    )
                    return False

        logger.debug(f"规则 {rule.name}: 所有条件满足")
        return True

    @staticmethod
    def is_in_silent_hours(rule: NotificationRule) -> bool:
        """
        检查当前时间是否在静默时段

        Args:
            rule: 通知规则

        Returns:
            是否在静默时段
        """
        if not rule.silent_hours or not rule.silent_hours.get("enabled"):
            return False

        current_time = now()
        current_weekday = current_time.strftime("%a").lower()  # mon, tue, wed, ...
        current_hour_minute = current_time.time()

        periods = rule.silent_hours.get("periods", [])

        for period in periods:
            # 检查星期是否匹配
            if "days" in period:
                allowed_days = [day.lower() for day in period["days"]]
                if current_weekday not in allowed_days:
                    continue

            # 解析时间
            start_str = period.get("start", "00:00")
            end_str = period.get("end", "23:59")

            try:
                start_hour, start_minute = map(int, start_str.split(":"))
                end_hour, end_minute = map(int, end_str.split(":"))

                start_time = time(start_hour, start_minute)
                end_time = time(end_hour, end_minute)

                # 检查时间是否在范围内
                if start_time <= end_time:
                    # 正常时间范围（如 08:00 - 22:00）
                    if start_time <= current_hour_minute <= end_time:
                        logger.debug(
                            f"规则 {rule.name}: 当前时间在静默时段 ({start_str} - {end_str})"
                        )
                        return True
                else:
                    # 跨午夜时间范围（如 22:00 - 08:00）
                    if current_hour_minute >= start_time or current_hour_minute <= end_time:
                        logger.debug(
                            f"规则 {rule.name}: 当前时间在静默时段 ({start_str} - {end_str})"
                        )
                        return True

            except (ValueError, AttributeError) as e:
                logger.warning(f"解析静默时段失败: {period}, error: {e}")
                continue

        return False

    @staticmethod
    async def should_deduplicate(
        db: AsyncSession, rule: NotificationRule, event_data: Dict[str, Any]
    ) -> bool:
        """
        检查是否应该去重（最近是否发送过类似通知）

        Args:
            db: 数据库会话
            rule: 通知规则
            event_data: 事件数据

        Returns:
            是否应该去重（True 表示重复，不应发送）
        """
        if not rule.deduplication_window or rule.deduplication_window <= 0:
            return False

        # 计算去重时间窗口
        cutoff_time = now() - timedelta(seconds=rule.deduplication_window)

        # 查询去重窗口内的相似通知
        query = select(NotificationExternal).where(
            and_(
                NotificationExternal.user_id == rule.user_id,
                NotificationExternal.notification_type == rule.event_type,
                NotificationExternal.created_at >= cutoff_time,
            )
        )

        # 如果有 related_id，使用它作为去重键
        if event_data.get("related_id"):
            query = query.where(
                NotificationExternal.extra_data["related_id"].astext
                == str(event_data["related_id"])
            )

        result = await db.execute(query.limit(1))
        recent_notification = result.scalar_one_or_none()

        if recent_notification:
            logger.debug(
                f"规则 {rule.name}: 在去重窗口内发现重复通知 "
                f"(窗口: {rule.deduplication_window}s, 最近: {recent_notification.id})"
            )
            return True

        return False
