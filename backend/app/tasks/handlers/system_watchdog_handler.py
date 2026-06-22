# -*- coding: utf-8 -*-
"""
系统巡检处理器（Watchdog）

定时主动巡检系统健康状况，发现异常即通过事件总线推送通知，实现无人值守预警。
当前覆盖两类目前无人主动检查的隐患：

1. 磁盘空间告警：挂载点不可访问 / 使用率过高 / 剩余空间不足
   （EVENT_DISK_SPACE_LOW 此前无任何发布者）
2. PT 站点健康：Cookie 已过期或即将过期、最近一次同步失败
   （站点事件发布此前被注释掉，处于真空状态）

设计：只读巡检，不修改业务数据；问题以现有事件类型发布，通知模板缺失时
NotificationDispatchService 会回退使用事件里的 title/content 渲染。
"""
import logging
from datetime import timedelta
from typing import Any, Dict, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.event import (
    EVENT_DISK_SPACE_LOW,
    EVENT_SITE_AUTH_EXPIRED,
    EVENT_SITE_CONNECTION_FAILED,
)
from app.events.bus import event_bus
from app.models import PTSite
from app.services.storage.storage_mount_service import StorageMountService
from app.services.task.task_execution_service import TaskExecutionService
from app.tasks.base import BaseTaskHandler
from app.utils.timezone import now

logger = logging.getLogger(__name__)

# 默认阈值（可被 handler_params 覆盖）
_DEFAULT_USAGE_WARN_PERCENT = 90.0
_DEFAULT_FREE_WARN_GB = 20.0
_DEFAULT_COOKIE_WARN_DAYS = 3
_SITE_SYNC_STATUS_FAILED = "failed"


def _gb(num_bytes: Any) -> float:
    if not num_bytes:
        return 0.0
    return round(num_bytes / (1024 ** 3), 2)


class SystemWatchdogHandler(BaseTaskHandler):
    """系统巡检：磁盘与站点健康"""

    @staticmethod
    async def execute(
        db: AsyncSession,
        params: Dict[str, Any],
        execution_id: int,
    ) -> Dict[str, Any]:
        usage_warn = float(params.get("usage_warn_percent", _DEFAULT_USAGE_WARN_PERCENT))
        free_warn_bytes = float(params.get("free_warn_gb", _DEFAULT_FREE_WARN_GB)) * 1024 ** 3
        cookie_warn_days = int(params.get("cookie_expiry_warn_days", _DEFAULT_COOKIE_WARN_DAYS))

        await TaskExecutionService.append_log(db, execution_id, "开始系统巡检")

        disk_alerts = await SystemWatchdogHandler._check_disk(db, usage_warn, free_warn_bytes)
        await TaskExecutionService.update_progress(db, execution_id, 50)

        site_alerts = await SystemWatchdogHandler._check_sites(db, cookie_warn_days)
        await TaskExecutionService.update_progress(db, execution_id, 100)

        total = len(disk_alerts) + len(site_alerts)
        await TaskExecutionService.append_log(
            db,
            execution_id,
            f"巡检完成：磁盘告警 {len(disk_alerts)}，站点告警 {len(site_alerts)}",
        )

        return {
            "disk_alert_count": len(disk_alerts),
            "site_alert_count": len(site_alerts),
            "alerts_published": total,
            "disk_alerts": disk_alerts,
            "site_alerts": site_alerts,
        }

    # ==================== 磁盘巡检 ====================

    @staticmethod
    async def _check_disk(
        db: AsyncSession,
        usage_warn: float,
        free_warn_bytes: float,
    ) -> List[Dict[str, Any]]:
        try:
            await StorageMountService.refresh_disk_info(db)
        except Exception as e:
            logger.warning(f"刷新磁盘信息失败: {e}")

        mounts = await StorageMountService.get_all_mounts(db, is_enabled=True)
        alerts: List[Dict[str, Any]] = []

        for m in mounts:
            reason = None
            if not m.is_accessible:
                reason = f"挂载点不可访问：{m.container_path}"
            else:
                percent = m.usage_percent
                if percent is not None and percent >= usage_warn:
                    reason = f"使用率已达 {percent}%"
                elif m.free_space is not None and m.free_space < free_warn_bytes:
                    reason = f"剩余空间仅 {_gb(m.free_space)}GB"

            if not reason:
                continue

            content = f"存储挂载点「{m.name}」{reason}，请及时清理或扩容。"
            await event_bus.publish(
                EVENT_DISK_SPACE_LOW,
                {
                    "broadcast": True,
                    "title": "⚠️ 磁盘空间告警",
                    "content": content,
                    "mount_name": m.name,
                    "mount_path": m.container_path,
                    "free_gb": _gb(m.free_space),
                    "usage_percent": m.usage_percent,
                    "related_type": "storage_mount",
                    "related_id": m.id,
                },
            )
            alerts.append({"mount": m.name, "reason": reason})
            logger.info(f"磁盘巡检告警: {m.name} - {reason}")

        return alerts

    # ==================== 站点巡检 ====================

    @staticmethod
    async def _check_sites(
        db: AsyncSession,
        cookie_warn_days: int,
    ) -> List[Dict[str, Any]]:
        result = await db.execute(
            select(PTSite).where(PTSite.sync_enabled == True)  # noqa: E712
        )
        sites = list(result.scalars().all())

        current = now()
        warn_before = current + timedelta(days=cookie_warn_days)
        alerts: List[Dict[str, Any]] = []

        for site in sites:
            # Cookie 过期 / 即将过期
            if site.cookie_expire_at is not None:
                if site.cookie_expire_at <= current:
                    await SystemWatchdogHandler._publish_site(
                        EVENT_SITE_AUTH_EXPIRED,
                        site,
                        "🔑 站点 Cookie 已过期",
                        f"站点「{site.name}」的 Cookie 已过期，同步与签到将失败，请尽快更新。",
                    )
                    alerts.append({"site": site.name, "issue": "cookie_expired"})
                    continue
                if site.cookie_expire_at <= warn_before:
                    days_left = max((site.cookie_expire_at - current).days, 0)
                    await SystemWatchdogHandler._publish_site(
                        EVENT_SITE_AUTH_EXPIRED,
                        site,
                        "🔑 站点 Cookie 即将过期",
                        f"站点「{site.name}」的 Cookie 将在约 {days_left} 天后过期，请及时更新。",
                    )
                    alerts.append({"site": site.name, "issue": "cookie_expiring"})
                    continue

            # 最近一次同步失败
            if site.last_sync_status == _SITE_SYNC_STATUS_FAILED:
                detail = site.last_sync_error or "未知错误"
                await SystemWatchdogHandler._publish_site(
                    EVENT_SITE_CONNECTION_FAILED,
                    site,
                    "🔌 站点同步失败",
                    f"站点「{site.name}」最近一次同步失败：{detail[:200]}",
                )
                alerts.append({"site": site.name, "issue": "sync_failed"})

        return alerts

    @staticmethod
    async def _publish_site(event_type: str, site: PTSite, title: str, content: str) -> None:
        await event_bus.publish(
            event_type,
            {
                "broadcast": True,
                "title": title,
                "content": content,
                "site_name": site.name,
                "related_type": "pt_site",
                "related_id": site.id,
            },
        )
        logger.info(f"站点巡检告警: {site.name} - {title}")
