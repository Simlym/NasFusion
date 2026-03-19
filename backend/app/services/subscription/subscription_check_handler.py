# -*- coding: utf-8 -*-
"""
订阅检查处理器
"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import ACTION_DOWNLOAD, ACTION_NONE, ACTION_NOTIFICATION, CHECK_TYPE_PT_SEARCH
from app.models import Subscription, PTResource
from app.services.subscription.subscription_service import SubscriptionService
from app.services.subscription.subscription_check_log_service import SubscriptionCheckLogService
from app.utils.timezone import now

logger = logging.getLogger(__name__)


class SubscriptionCheckHandler:
    """订阅检查处理器"""

    @staticmethod
    async def check_all_subscriptions(db: AsyncSession) -> Dict[str, Any]:
        """
        检查所有活跃订阅

        Args:
            db: 数据库会话

        Returns:
            Dict: 检查结果统计
        """
        # 获取需要检查的订阅列表
        subscriptions = await SubscriptionService.get_active_subscriptions_for_check(db)

        if not subscriptions:
            logger.info("没有需要检查的订阅")
            return {
                "total": 0,
                "checked": 0,
                "matched": 0,
                "downloaded": 0,
                "errors": 0,
            }

        logger.info(f"开始检查 {len(subscriptions)} 个订阅")

        stats = {
            "total": len(subscriptions),
            "checked": 0,
            "matched": 0,
            "downloaded": 0,
            "errors": 0,
        }

        # 逐个检查订阅
        for subscription in subscriptions:
            try:
                result = await SubscriptionCheckHandler.check_subscription(db, subscription.id)

                stats["checked"] += 1
                if result["matched_count"] > 0:
                    stats["matched"] += 1
                if result.get("downloaded", False):
                    stats["downloaded"] += 1

            except Exception as e:
                logger.error(f"检查订阅失败: 订阅{subscription.id}, 错误: {e}")
                stats["errors"] += 1

        logger.info(f"订阅检查完成: {stats}")
        return stats

    @staticmethod
    async def check_subscription(
        db: AsyncSession, subscription_id: int
    ) -> Dict[str, Any]:
        """
        检查单个订阅

        Args:
            db: 数据库会话
            subscription_id: 订阅ID

        Returns:
            Dict: 检查结果
        """
        start_time = now()

        # 获取订阅
        subscription = await SubscriptionService.get_by_id(db, subscription_id)
        if not subscription:
            raise ValueError(f"订阅不存在: {subscription_id}")

        if not subscription.is_active:
            logger.debug(f"订阅未激活: {subscription_id}")
            return {"matched_count": 0}

        logger.info(f"开始检查订阅: {subscription_id} - {subscription.title}")

        # 查找匹配的PT资源
        matched_resources = await SubscriptionService.find_matched_resources(
            db, subscription_id
        )

        # 准备检查结果
        check_result = {
            "has_resources": len(matched_resources) > 0,
            "resource_count": len(matched_resources),
            "matched_count": len(matched_resources),
            "best_quality": None,
            "downloaded": False,
        }

        # 确定最佳资源
        best_resource = None
        if matched_resources:
            # 按质量优先级排序
            rules = subscription.rules or {}
            quality_priority = rules.get("quality_priority", [])

            if quality_priority:
                # 按质量优先级排序
                for quality in quality_priority:
                    for resource in matched_resources:
                        if resource.resolution == quality:
                            best_resource = resource
                            break
                    if best_resource:
                        break

            # 如果没有按优先级找到，选第一个
            if not best_resource and matched_resources:
                best_resource = matched_resources[0]

            if best_resource:
                check_result["best_quality"] = best_resource.resolution

        # 触发的动作
        action_triggered = ACTION_NONE
        action_detail = {}

        # 如果有匹配资源，触发相应动作
        if best_resource:
            # 判断是否需要下载
            if subscription.auto_download:
                # 调用下载服务
                download_result = await SubscriptionCheckHandler._trigger_download(
                    db, subscription, best_resource
                )

                if download_result.get("success"):
                    action_triggered = ACTION_DOWNLOAD
                    action_detail = download_result
                    check_result["downloaded"] = True

                    logger.info(
                        f"订阅{subscription_id}已触发下载: PT资源{best_resource.id}"
                    )

            # 发送通知
            if subscription.notify_on_match and action_triggered != ACTION_DOWNLOAD:
                action_triggered = ACTION_NOTIFICATION
                action_detail = {
                    "type": "match",
                    "resource_id": best_resource.id,
                    "resource_title": best_resource.title,
                    "quality": best_resource.resolution,
                }

                # 调度通知
                await SubscriptionCheckHandler._send_match_notification(
                    db, subscription, best_resource
                )

                logger.info(f"订阅{subscription_id}已发送匹配通知")

            # 如果触发了下载且需要通知
            elif subscription.notify_on_download and check_result["downloaded"]:
                # 这里可以同时记录通知和下载
                action_detail["notification"] = {
                    "type": "download",
                    "resource_title": best_resource.title,
                }

                # 调度下载通知
                await SubscriptionCheckHandler._send_download_notification(
                    db, subscription, best_resource
                )

                logger.info(f"订阅{subscription_id}已发送下载通知")

        # 计算执行时间
        execution_time = int((now() - start_time).total_seconds())

        # 记录检查日志
        await SubscriptionCheckLogService.create_log(
            db,
            subscription_id=subscription_id,
            sites_searched=1,  # TODO: 实际搜索的站点数
            resources_found=len(matched_resources),
            match_count=len(matched_resources),
            best_match={
                "pt_resource_id": best_resource.id if best_resource else None,
                "title": best_resource.title if best_resource else None,
                "quality": best_resource.resolution if best_resource else None,
                "seeders": best_resource.seeders if best_resource else None,
            }
            if best_resource
            else None,
            action_triggered=action_triggered,
            action_detail=action_detail,
            execution_time=execution_time,
            success=True,
            task_execution_id=None,  # TODO: 从调用上下文获取任务执行ID
        )

        # 更新订阅统计
        await SubscriptionService.update_subscription_stats(
            db, subscription_id, check_result
        )

        # 检查订阅是否完成
        await SubscriptionService.check_subscription_completion(db, subscription_id)

        logger.info(
            f"订阅检查完成: {subscription_id}, 匹配{len(matched_resources)}个资源"
        )

        return check_result

    @staticmethod
    async def _trigger_download(
        db: AsyncSession, subscription: Subscription, pt_resource: PTResource
    ) -> Dict[str, Any]:
        """
        触发下载

        Args:
            db: 数据库会话
            subscription: 订阅对象
            pt_resource: PT资源对象

        Returns:
            Dict: 下载结果
        """
        try:
            # 导入下载服务（延迟导入避免循环依赖）
            from app.services.download.download_task_service import DownloadTaskService
            from app.schemas.downloader import DownloadTaskCreate

            # 检查是否已经下载过
            existing_task = await DownloadTaskService.get_by_pt_resource_id(
                db, pt_resource.id
            )
            if existing_task:
                logger.info(f"PT资源{pt_resource.id}已存在下载任务，跳过")
                return {
                    "success": True,
                    "skipped": True,
                    "reason": "already_downloading",
                    "download_task_id": existing_task.id,
                }

            # 确定统一资源表名和ID（多态关联）
            unified_table_name = None
            unified_resource_id = None
            if subscription.media_type == "movie":
                unified_table_name = "unified_movies"
                unified_resource_id = subscription.unified_movie_id
            elif subscription.media_type == "tv":
                unified_table_name = "unified_tv_series"
                unified_resource_id = subscription.unified_tv_id

            # 创建下载任务（torrent_name 会从种子文件自动提取）
            download_data = DownloadTaskCreate(
                pt_resource_id=pt_resource.id,
                media_type=subscription.media_type,
                unified_table_name=unified_table_name,
                unified_resource_id=unified_resource_id,
                # save_path 会由下载服务自动设置
            )

            download_task = await DownloadTaskService.create(db, download_data)

            logger.info(
                f"创建下载任务成功: 订阅{subscription.id}, 任务{download_task.id}"
            )

            return {
                "success": True,
                "download_task_id": download_task.id,
                "pt_resource_id": pt_resource.id,
            }

        except Exception as e:
            logger.error(f"触发下载失败: 订阅{subscription.id}, 错误: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    async def _send_match_notification(
        db: AsyncSession, subscription: Subscription, pt_resource: PTResource
    ) -> None:
        """
        发送订阅匹配通知

        Args:
            db: 数据库会话
            subscription: 订阅对象
            pt_resource: 匹配的PT资源
        """
        try:
            from app.constants.event import EVENT_SUBSCRIPTION_MATCHED
            from app.events.bus import event_bus

            # 准备事件数据
            event_data = {
                "user_id": subscription.user_id,
                "media_name": subscription.title,
                "quality": pt_resource.resolution or "未知",
                "size_gb": round(pt_resource.size / (1024**3), 2)
                if pt_resource.size
                else 0,
                "size_bytes": pt_resource.size or 0,
                "site_name": pt_resource.site.name if pt_resource.site else "未知",
                "promotion_type": pt_resource.promotion_type or "无",
                "seeders": pt_resource.seeders or 0,
                "related_type": "pt_resource",
                "related_id": pt_resource.id,
                "subscription_id": subscription.id,
                "subscription_title": subscription.title,
            }

            # 发布事件（异步触发，不阻塞）
            await event_bus.publish(
                EVENT_SUBSCRIPTION_MATCHED,
                event_data
            )

            logger.debug(
                f"订阅匹配事件已发布: 订阅{subscription.id}, PT资源{pt_resource.id}"
            )

        except Exception as e:
            logger.exception(f"发布订阅匹配事件失败: 订阅{subscription.id}, 错误: {e}")

    @staticmethod
    async def _send_download_notification(
        db: AsyncSession, subscription: Subscription, pt_resource: PTResource
    ) -> None:
        """
        发送下载通知

        Args:
            db: 数据库会话
            subscription: 订阅对象
            pt_resource: PT资源
        """
        try:
            from app.constants.event import EVENT_SUBSCRIPTION_DOWNLOADED
            from app.events.bus import event_bus

            # 准备事件数据
            event_data = {
                "user_id": subscription.user_id,
                "media_name": subscription.title,
                "quality": pt_resource.resolution or "未知",
                "size_gb": round(pt_resource.size / (1024**3), 2)
                if pt_resource.size
                else 0,
                "size_bytes": pt_resource.size or 0,
                "site_name": pt_resource.site.name if pt_resource.site else "未知",
                "promotion_type": pt_resource.promotion_type or "无",
                "related_type": "pt_resource",
                "related_id": pt_resource.id,
                "subscription_id": subscription.id,
                "subscription_title": subscription.title,
            }

            # 发布事件（异步触发，不阻塞）
            await event_bus.publish(
                EVENT_SUBSCRIPTION_DOWNLOADED,
                event_data
            )

            logger.debug(
                f"订阅下载事件已发布: 订阅{subscription.id}, PT资源{pt_resource.id}"
            )

        except Exception as e:
            logger.exception(f"发布订阅下载事件失败: 订阅{subscription.id}, 错误: {e}")
