# -*- coding: utf-8 -*-
"""
订阅检查处理器
"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.tasks.base import BaseTaskHandler
from app.constants import ACTION_DOWNLOAD, ACTION_NONE, ACTION_NOTIFICATION, CHECK_TYPE_PT_SEARCH
from app.models import Subscription, PTResource, PTSite
from app.services.subscription.subscription_service import SubscriptionService
from app.services.subscription.subscription_check_log_service import SubscriptionCheckLogService
from app.services.task.task_execution_service import TaskExecutionService
from app.services.pt.pt_resource_service import PTResourceService
from app.utils.timezone import now

logger = logging.getLogger(__name__)


class SubscriptionCheckHandler(BaseTaskHandler):
    """订阅检查处理器"""

    @staticmethod
    async def execute(
        db: AsyncSession,
        params: Dict[str, Any],
        execution_id: int,
    ) -> Dict[str, Any]:
        """
        执行订阅检查任务（统一入口）

        Args:
            db: 数据库会话
            params: 处理器参数
                - check_all: 是否检查所有订阅 (默认 True)
                - subscription_ids: 订阅ID列表 (可选)
                - subscription_id: 单个订阅ID (可选，向后兼容)
                - sync_resources: 是否先同步资源 (默认 False)
                - sync_max_pages: 同步最大页数 (默认 1)
                - auto_identify: 是否自动识别 (默认 False)
            execution_id: 任务执行ID

        Returns:
            检查结果统计
        """
        check_all = params.get("check_all", True)
        subscription_ids = params.get("subscription_ids", [])
        sync_resources = params.get("sync_resources", False)
        sync_max_pages = params.get("sync_max_pages", 1)
        auto_identify = params.get("auto_identify", False)

        if check_all:
            # 检查所有活跃订阅
            await TaskExecutionService.append_log(
                db, execution_id, "开始批量检查所有活跃订阅"
            )

            # 阶段1：同步资源（可选）
            sync_stats = None
            if sync_resources:
                sync_stats = await SubscriptionCheckHandler._sync_resources_for_subscriptions(
                    db, execution_id, sync_max_pages
                )

            # 阶段2：自动识别（可选）
            identify_stats = None
            if auto_identify:
                identify_stats = await SubscriptionCheckHandler._identify_resources_for_subscriptions(
                    db, execution_id
                )

            # 阶段3：订阅检查
            stats = await SubscriptionCheckHandler.check_all_subscriptions(
                db, execution_id=execution_id
            )

            # 合并统计信息
            if sync_stats:
                stats["sync"] = sync_stats
            if identify_stats:
                stats["identify"] = identify_stats

            await TaskExecutionService.update_progress(db, execution_id, 100)
            await TaskExecutionService.append_log(
                db, execution_id,
                f"批量检查完成: 检查 {stats['checked']}/{stats['total']} 个订阅, "
                f"匹配 {stats['matched']} 个, 下载 {stats['downloaded']} 个, "
                f"错误 {stats['errors']} 个"
            )

            return stats
        elif subscription_ids:
            # 检查指定订阅列表
            await TaskExecutionService.append_log(
                db, execution_id, f"开始检查 {len(subscription_ids)} 个指定订阅"
            )

            total_matched = 0
            total_downloaded = 0
            checked_count = 0
            error_count = 0

            for subscription_id in subscription_ids:
                try:
                    await TaskExecutionService.append_log(
                        db, execution_id, f"正在检查订阅 {subscription_id}"
                    )

                    result = await SubscriptionCheckHandler.check_subscription(
                        db, subscription_id, execution_id=execution_id
                    )

                    total_matched += result.get("matched_count", 0)
                    if result.get("downloaded", False):
                        total_downloaded += result.get("downloaded_count", 1)
                    checked_count += 1

                    await TaskExecutionService.append_log(
                        db, execution_id,
                        f"订阅 {subscription_id} 检查完成: 匹配 {result.get('matched_count', 0)} 个资源"
                    )

                except Exception as e:
                    error_count += 1
                    await TaskExecutionService.append_log(
                        db, execution_id,
                        f"订阅 {subscription_id} 检查失败: {str(e)}"
                    )

            await TaskExecutionService.update_progress(db, execution_id, 100)
            await TaskExecutionService.append_log(
                db, execution_id,
                f"指定订阅检查完成: 检查 {checked_count}/{len(subscription_ids)} 个订阅, "
                f"匹配 {total_matched} 个, 下载 {total_downloaded} 个, "
                f"错误 {error_count} 个"
            )

            return {
                "total": len(subscription_ids),
                "checked": checked_count,
                "matched": total_matched,
                "downloaded": total_downloaded,
                "errors": error_count,
                "subscription_ids": subscription_ids
            }
        else:
            # 兼容旧的单个订阅参数
            subscription_id = params.get("subscription_id")
            if subscription_id:
                await TaskExecutionService.append_log(
                    db, execution_id, f"开始检查订阅 {subscription_id}"
                )

                result = await SubscriptionCheckHandler.check_subscription(
                    db, subscription_id, execution_id=execution_id
                )

                await TaskExecutionService.update_progress(db, execution_id, 100)
                await TaskExecutionService.append_log(
                    db, execution_id,
                    f"订阅检查完成: 匹配 {result['matched_count']} 个资源"
                )

                return {
                    "subscription_id": subscription_id,
                    "matched_count": result["matched_count"],
                    "downloaded": result.get("downloaded", False),
                }
            else:
                # 默认检查所有订阅
                await TaskExecutionService.append_log(
                    db, execution_id, "未指定检查范围，默认检查所有活跃订阅"
                )

                stats = await SubscriptionCheckHandler.check_all_subscriptions(
                    db, execution_id=execution_id
                )

                await TaskExecutionService.update_progress(db, execution_id, 100)
                await TaskExecutionService.append_log(
                    db, execution_id,
                    f"默认检查完成: 检查 {stats['checked']}/{stats['total']} 个订阅, "
                    f"匹配 {stats['matched']} 个, 下载 {stats['downloaded']} 个, "
                    f"错误 {stats['errors']} 个"
                )

                return stats

    @staticmethod
    async def check_all_subscriptions(
        db: AsyncSession, execution_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        检查所有活跃订阅

        Args:
            db: 数据库会话
            execution_id: 任务执行ID (可选，用于日志记录)

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
                result = await SubscriptionCheckHandler.check_subscription(
                    db, subscription.id, execution_id=execution_id
                )

                stats["checked"] += 1
                if result["matched_count"] > 0:
                    stats["matched"] += 1
                if result.get("downloaded", False):
                    stats["downloaded"] += result.get("downloaded_count", 1)

            except Exception as e:
                logger.error(f"检查订阅失败: 订阅{subscription.id}, 错误: {e}")
                stats["errors"] += 1

        logger.info(f"订阅检查完成: {stats}")
        return stats

    @staticmethod
    async def check_subscription(
        db: AsyncSession, subscription_id: int, execution_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        检查单个订阅

        Args:
            db: 数据库会话
            subscription_id: 订阅ID
            execution_id: 任务执行ID (可选，用于日志记录)

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

        # 电视剧订阅：过滤掉覆盖集数全部已完成的资源，避免重复下载
        if subscription.is_tv_subscription and subscription.episodes_status and matched_resources:
            before_count = len(matched_resources)
            matched_resources = [
                r for r in matched_resources
                if not SubscriptionCheckHandler._is_resource_all_done(subscription, r)
            ]
            if len(matched_resources) < before_count:
                logger.info(
                    f"订阅{subscription_id}: 过滤已完成集数的资源 "
                    f"{before_count} → {len(matched_resources)}"
                )

        # 确定待下载资源列表
        # TV订阅：按集数分组，每集各选一个最优资源；电影：选单个最优资源
        rules = subscription.rules or {}
        quality_priority = rules.get("quality_priority", [])

        best_resource = None           # 用于日志/通知的代表性资源（第一个）
        resources_to_download = []     # 实际需要触发下载的资源列表

        if matched_resources:
            if subscription.is_tv_subscription:
                resources_to_download = SubscriptionCheckHandler._select_best_per_episode(
                    subscription, matched_resources, quality_priority
                )
                best_resource = resources_to_download[0] if resources_to_download else None
            else:
                # 电影：选单个最优资源
                if quality_priority:
                    for quality in quality_priority:
                        for resource in matched_resources:
                            if resource.resolution == quality:
                                best_resource = resource
                                break
                        if best_resource:
                            break
                if not best_resource:
                    best_resource = matched_resources[0]
                resources_to_download = [best_resource] if best_resource else []

            if best_resource:
                check_result["best_quality"] = best_resource.resolution

        # 触发的动作
        action_triggered = ACTION_NONE
        action_detail = {}

        # 如果有匹配资源，触发相应动作
        if resources_to_download:
            # 判断是否需要下载
            if subscription.auto_download:
                triggered_count = 0
                for resource in resources_to_download:
                    download_result = await SubscriptionCheckHandler._trigger_download(
                        db, subscription, resource
                    )
                    if download_result.get("success"):
                        if not download_result.get("skipped"):
                            triggered_count += 1
                            logger.info(
                                f"订阅{subscription_id}已触发下载: PT资源{resource.id}"
                            )
                        else:
                            logger.info(
                                f"订阅{subscription_id}跳过已有任务: PT资源{resource.id}"
                            )

                if triggered_count > 0:
                    action_triggered = ACTION_DOWNLOAD
                    action_detail = {"triggered_count": triggered_count}
                    check_result["downloaded"] = True
                    check_result["downloaded_count"] = triggered_count

                    # 触发下载后立即刷新集数状态为"下载中"，防止下次检查重复触发
                    if subscription.is_tv_subscription:
                        from app.services.subscription.subscription_episode_service import SubscriptionEpisodeService
                        await SubscriptionEpisodeService.refresh_episodes_status(db, subscription.id)

            # 发送通知（以 best_resource 为代表）
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
            task_execution_id=execution_id,  # 使用传入的任务执行ID
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
            from app.models.downloader_config import DownloaderConfig

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

            # 获取默认下载器配置
            downloader_query = select(DownloaderConfig).where(
                DownloaderConfig.is_enabled == True
            ).order_by(
                DownloaderConfig.is_default.desc(),
                DownloaderConfig.id.asc()
            )
            downloader_result = await db.execute(downloader_query)
            downloader_config = downloader_result.scalar_one_or_none()

            if not downloader_config:
                logger.error(
                    f"触发下载失败: 订阅{subscription.id}, "
                    f"PT资源{pt_resource.id}, 原因: 没有可用的下载器配置"
                )
                return {"success": False, "error": "没有可用的下载器配置，请先在设置中配置下载器"}

            # 确定统一资源表名和ID（多态关联）
            unified_table_name = None
            unified_resource_id = None
            if subscription.media_type == "movie":
                unified_table_name = "unified_movies"
                unified_resource_id = subscription.unified_movie_id
            elif subscription.media_type == "tv":
                unified_table_name = "unified_tv_series"
                unified_resource_id = subscription.unified_tv_id

            # 确定整理配置和存储挂载点
            from app.models.organize_config import OrganizeConfig
            from app.models.storage_mount import StorageMount

            # 优先使用订阅自身的整理设置，否则 fallback 到全局默认
            if not subscription.auto_organize:
                # 订阅明确禁用整理
                auto_organize = False
                final_organize_config_id = None
                final_storage_mount_id = None
                logger.info(f"订阅{subscription.id} 整理设置为关闭，将跳过自动整理")
            else:
                # 订阅启用整理：优先用订阅指定的配置，否则查找全局默认
                if subscription.organize_config_id:
                    final_organize_config_id = subscription.organize_config_id
                    logger.info(f"订阅{subscription.id} 使用订阅指定整理配置: organize_config_id={final_organize_config_id}")
                else:
                    # 优先取 is_default=True，找不到再取任意启用的配置
                    organize_config_query = select(OrganizeConfig).where(
                        OrganizeConfig.media_type == subscription.media_type,
                        OrganizeConfig.is_enabled == True,
                    ).order_by(
                        OrganizeConfig.is_default.desc(),
                        OrganizeConfig.id.asc(),
                    ).limit(1)
                    organize_config_result = await db.execute(organize_config_query)
                    default_organize_config = organize_config_result.scalar_one_or_none()
                    final_organize_config_id = default_organize_config.id if default_organize_config else None
                    if final_organize_config_id:
                        logger.info(
                            f"订阅{subscription.id} 使用全局默认整理配置: organize_config_id={final_organize_config_id}"
                            f"（media_type={subscription.media_type}, is_default={default_organize_config.is_default}）"
                        )
                    else:
                        logger.warning(
                            f"订阅{subscription.id} 未找到可用整理配置（media_type={subscription.media_type}，无已启用的配置）"
                        )

                if subscription.storage_mount_id:
                    final_storage_mount_id = subscription.storage_mount_id
                    logger.info(f"订阅{subscription.id} 使用订阅指定存储挂载点: storage_mount_id={final_storage_mount_id}")
                else:
                    # 优先取 is_default=True，找不到再取任意启用的库类型挂载点
                    storage_mount_query = select(StorageMount).where(
                        StorageMount.media_category == subscription.media_type,
                        StorageMount.is_enabled.is_not(False),
                        StorageMount.mount_type == "library",
                    ).order_by(
                        StorageMount.is_default.desc(),
                        StorageMount.id.asc(),
                    ).limit(1)
                    storage_mount_result = await db.execute(storage_mount_query)
                    default_storage_mount = storage_mount_result.scalar_one_or_none()
                    final_storage_mount_id = default_storage_mount.id if default_storage_mount else None
                    if final_storage_mount_id:
                        logger.info(
                            f"订阅{subscription.id} 使用全局默认存储挂载点: storage_mount_id={final_storage_mount_id}"
                            f"（media_type={subscription.media_type}, is_default={default_storage_mount.is_default}）"
                        )
                    else:
                        logger.warning(
                            f"订阅{subscription.id} 未找到可用存储挂载点（media_type={subscription.media_type}，无library类型挂载点）"
                        )

                auto_organize = final_organize_config_id is not None and final_storage_mount_id is not None
                logger.info(
                    f"订阅{subscription.id} 整理配置汇总: auto_organize={auto_organize}, "
                    f"organize_config_id={final_organize_config_id}, storage_mount_id={final_storage_mount_id}"
                )
                if not auto_organize:
                    logger.warning(
                        f"订阅{subscription.id} 未找到可用整理配置或存储挂载点"
                        f"（media_type={subscription.media_type}），将跳过自动整理"
                    )

            # 创建下载任务（torrent_name 会从种子文件自动提取）
            download_data = DownloadTaskCreate(
                pt_resource_id=pt_resource.id,
                downloader_config_id=downloader_config.id,
                media_type=subscription.media_type,
                unified_table_name=unified_table_name,
                unified_resource_id=unified_resource_id,
                auto_organize=auto_organize,
                organize_config_id=final_organize_config_id if auto_organize else None,
                storage_mount_id=final_storage_mount_id if auto_organize else None,
                # save_path 会由下载服务自动设置
            )

            download_task = await DownloadTaskService.create(db, download_data)

            logger.info(
                f"创建下载任务成功: 订阅{subscription.id}, 任务{download_task.id}, "
                f"下载器={downloader_config.name}, PT资源={pt_resource.id}"
            )

            return {
                "success": True,
                "download_task_id": download_task.id,
                "pt_resource_id": pt_resource.id,
                "downloader_config_id": downloader_config.id,
            }

        except Exception as e:
            logger.error(
                f"触发下载失败: 订阅{subscription.id}, PT资源{pt_resource.id}, "
                f"错误类型={type(e).__name__}, 错误详情: {e}",
                exc_info=True
            )
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

            # 显式查询站点名称，避免懒加载在异步上下文中触发 greenlet 错误
            site_obj = await db.get(PTSite, pt_resource.site_id) if pt_resource.site_id else None
            site_name = site_obj.name if site_obj else "未知"

            # 准备事件数据
            event_data = {
                "user_id": subscription.user_id,
                "media_name": subscription.title,
                "quality": pt_resource.resolution or "未知",
                "size_gb": pt_resource.size_gb,  # 使用属性方法
                "size_bytes": pt_resource.size_bytes or 0,  # 使用正确的字段名
                "site_name": site_name,
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

            # 显式查询站点名称，避免懒加载在异步上下文中触发 greenlet 错误
            site_obj = await db.get(PTSite, pt_resource.site_id) if pt_resource.site_id else None
            site_name = site_obj.name if site_obj else "未知"

            # 准备事件数据
            event_data = {
                "user_id": subscription.user_id,
                "media_name": subscription.title,
                "quality": pt_resource.resolution or "未知",
                "size_gb": pt_resource.size_gb,
                "size_bytes": pt_resource.size_bytes or 0,
                "site_name": site_name,
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

    @staticmethod
    def _select_best_per_episode(
        subscription: Subscription,
        resources: List[PTResource],
        quality_priority: List[str],
    ) -> List[PTResource]:
        """
        TV订阅专用：按集数分组，每组选出质量最优的资源，返回待下载列表。

        同一集（或相同集数范围）的多个资源只选一个最优的，避免重复下载。
        """
        from collections import defaultdict

        # 按「集数范围元组」分组
        group_map: Dict[tuple, List[PTResource]] = defaultdict(list)
        ungrouped: List[PTResource] = []  # 无法确定集数的资源单独列出

        for r in resources:
            ep_keys = SubscriptionCheckHandler._get_resource_episode_keys(subscription, r)
            if ep_keys:
                group_key = tuple(sorted(ep_keys))
                group_map[group_key].append(r)
            else:
                ungrouped.append(r)

        best_resources: List[PTResource] = []

        for group_resources in group_map.values():
            best = None
            if quality_priority:
                for quality in quality_priority:
                    for r in group_resources:
                        if r.resolution == quality:
                            best = r
                            break
                    if best:
                        break
            if not best:
                best = group_resources[0]
            best_resources.append(best)

        # 无法分组的资源：按质量选一个追加（保守处理）
        if ungrouped:
            best_ung = None
            if quality_priority:
                for quality in quality_priority:
                    for r in ungrouped:
                        if r.resolution == quality:
                            best_ung = r
                            break
                    if best_ung:
                        break
            if not best_ung:
                best_ung = ungrouped[0]
            best_resources.append(best_ung)

        return best_resources

    @staticmethod
    def _get_resource_episode_keys(subscription: Subscription, pt_resource: PTResource) -> List[str]:
        """
        获取资源覆盖的集数 key 列表（与 episodes_status 的 key 对应）

        Returns:
            集数 key 列表，如 ["128", "129"]；无法确定时返回空列表
        """
        from app.utils.tv_parser import extract_absolute_episode_range

        if not pt_resource.tv_info:
            return []

        if subscription.use_absolute_episode_match:
            ep_range = extract_absolute_episode_range(pt_resource.tv_info)
            if not ep_range:
                return []
            return [str(ep) for ep in range(ep_range["start"], ep_range["end"] + 1)]
        else:
            season = subscription.current_season
            tv_info_episodes = pt_resource.tv_info.get("episodes", {}).get(str(season))
            if not tv_info_episodes:
                return []
            start = tv_info_episodes.get("start")
            end = tv_info_episodes.get("end", start)
            if start is None:
                return []
            return [str(ep) for ep in range(start, end + 1)]

    @staticmethod
    def _is_resource_all_done(subscription: Subscription, pt_resource: PTResource) -> bool:
        """
        检查资源覆盖的所有集数是否均已完成（downloaded / downloading / ignored）

        Returns:
            True 表示全部已完成，可安全跳过下载
        """
        from app.constants.subscription import (
            EPISODE_STATUS_DOWNLOADED,
            EPISODE_STATUS_DOWNLOADING,
            EPISODE_STATUS_IGNORED,
        )

        episodes_status = subscription.episodes_status or {}
        if not episodes_status:
            return False

        ep_keys = SubscriptionCheckHandler._get_resource_episode_keys(subscription, pt_resource)
        if not ep_keys:
            return False  # 无法确定集数范围，保守地不过滤

        done_statuses = {EPISODE_STATUS_DOWNLOADED, EPISODE_STATUS_DOWNLOADING, EPISODE_STATUS_IGNORED}
        return all(
            episodes_status.get(ep_key, {}).get("status") in done_statuses
            for ep_key in ep_keys
        )

    @staticmethod
    async def _sync_resources_for_subscriptions(
        db: AsyncSession,
        execution_id: int,
        max_pages: int = 1,
    ) -> Dict[str, Any]:
        """
        为所有活跃订阅同步PT资源

        Args:
            db: 数据库会话
            execution_id: 任务执行ID
            max_pages: 每个关键字同步的最大页数

        Returns:
            同步统计
        """
        await TaskExecutionService.append_log(
            db, execution_id, f"[阶段1] 开始同步PT资源 (每个关键字最多 {max_pages} 页)"
        )

        # 获取所有活跃订阅
        subscriptions = await SubscriptionService.get_active_subscriptions_for_check(db)
        if not subscriptions:
            await TaskExecutionService.append_log(db, execution_id, "没有活跃的订阅")
            return {"total_subscriptions": 0, "keywords_synced": 0}

        # 收集所有搜索关键字（去重）
        keywords_map: Dict[str, List[int]] = {}  # keyword -> subscription_ids
        for sub in subscriptions:
            # 根据 use_override_for_sync 决定使用哪个标题
            if sub.use_override_for_sync and sub.override_title:
                keyword = sub.override_title.strip()
            else:
                keyword = sub.title.strip()

            if keyword:
                if keyword not in keywords_map:
                    keywords_map[keyword] = []
                keywords_map[keyword].append(sub.id)

        if not keywords_map:
            await TaskExecutionService.append_log(db, execution_id, "没有有效的搜索关键字")
            return {"total_subscriptions": len(subscriptions), "keywords_synced": 0}

        await TaskExecutionService.append_log(
            db, execution_id,
            f"从 {len(subscriptions)} 个订阅中提取了 {len(keywords_map)} 个唯一关键字"
        )

        # 获取所有启用同步的站点
        result = await db.execute(
            select(PTSite).where(PTSite.status == "active", PTSite.sync_enabled == True)
        )
        sites = result.scalars().all()

        if not sites:
            await TaskExecutionService.append_log(db, execution_id, "没有启用同步的PT站点")
            return {
                "total_subscriptions": len(subscriptions),
                "keywords_synced": 0,
                "error": "no_sites"
            }

        # 统计
        stats = {
            "total_subscriptions": len(subscriptions),
            "unique_keywords": len(keywords_map),
            "sites_count": len(sites),
            "total_new": 0,
            "total_updated": 0,
            "errors": 0,
        }

        # 对每个关键字在每个站点进行同步
        for keyword, sub_ids in keywords_map.items():
            for site in sites:
                try:
                    await TaskExecutionService.append_log(
                        db, execution_id,
                        f"同步资源: 站点={site.name}, 关键字=\"{keyword}\""
                    )

                    sync_log = await PTResourceService.sync_site_resources(
                        db,
                        site_id=site.id,
                        sync_type="manual",
                        max_pages=max_pages,
                        start_page=1,
                        task_execution_id=None,  # 不更新进度到当前任务
                        filters={"keyword": keyword}
                    )

                    stats["total_new"] += sync_log.resources_new
                    stats["total_updated"] += sync_log.resources_updated

                    if sync_log.resources_new > 0 or sync_log.resources_updated > 0:
                        logger.info(
                            f"关键字 \"{keyword}\" 在站点 {site.name}: "
                            f"新增 {sync_log.resources_new}, 更新 {sync_log.resources_updated}"
                        )

                except Exception as e:
                    stats["errors"] += 1
                    logger.error(f"同步失败: 站点={site.name}, 关键字=\"{keyword}\", 错误: {e}")

        await TaskExecutionService.append_log(
            db, execution_id,
            f"[阶段1完成] 资源同步: 新增 {stats['total_new']}, 更新 {stats['total_updated']}, 错误 {stats['errors']}"
        )

        return stats

    @staticmethod
    async def _identify_resources_for_subscriptions(
        db: AsyncSession,
        execution_id: int,
    ) -> Dict[str, Any]:
        """
        为订阅关键字匹配的未识别资源执行自动识别

        Args:
            db: 数据库会话
            execution_id: 任务执行ID

        Returns:
            识别统计
        """
        from app.services.identification.resource_identify_service import ResourceIdentificationService

        await TaskExecutionService.append_log(
            db, execution_id, "[阶段2] 开始自动识别PT资源"
        )

        # 获取所有活跃订阅的关键字
        subscriptions = await SubscriptionService.get_active_subscriptions_for_check(db)
        if not subscriptions:
            return {"total": 0, "success": 0, "failed": 0}

        # 收集所有搜索关键字
        keywords: Set[str] = set()
        for sub in subscriptions:
            if sub.use_override_for_sync and sub.override_title:
                keywords.add(sub.override_title.strip())
            else:
                keywords.add(sub.title.strip())

        if not keywords:
            await TaskExecutionService.append_log(db, execution_id, "没有有效的搜索关键字")
            return {"total": 0, "success": 0, "failed": 0}

        # 查找标题匹配这些关键字的未识别资源
        unidentified_ids: Set[int] = set()
        for keyword in keywords:
            if not keyword:
                continue

            # 查询标题包含关键字的未识别资源
            resources = await PTResourceService.search_unidentified_by_title(
                db, keyword, limit=500
            )
            for r in resources:
                unidentified_ids.add(r.id)

        if not unidentified_ids:
            await TaskExecutionService.append_log(
                db, execution_id, "没有找到需要识别的资源"
            )
            return {"total": 0, "success": 0, "failed": 0}

        await TaskExecutionService.append_log(
            db, execution_id,
            f"找到 {len(unidentified_ids)} 个未识别资源，开始批量识别"
        )

        # 执行批量识别
        result = await ResourceIdentificationService.batch_identify_resources(
            db=db,
            pt_resource_ids=list(unidentified_ids),
            media_type="auto",
            skip_errors=True,
            task_execution_id=None  # 不更新进度到当前任务
        )

        await TaskExecutionService.append_log(
            db, execution_id,
            f"[阶段2完成] 资源识别: 成功 {result['success']}, 失败 {result['failed']}, 跳过 {result['skipped']}"
        )

        return {
            "total": result["total"],
            "success": result["success"],
            "failed": result["failed"],
            "skipped": result["skipped"],
        }
