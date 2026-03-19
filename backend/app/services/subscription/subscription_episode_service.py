# -*- coding: utf-8 -*-
"""
订阅集数状态管理服务
"""
import logging
import copy
from typing import Dict, Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.constants.subscription import (
    EPISODE_STATUS_AVAILABLE,
    EPISODE_STATUS_DOWNLOADED,
    EPISODE_STATUS_DOWNLOADING,
    EPISODE_STATUS_WAITING,
    EPISODE_STATUS_FAILED,
    EPISODE_STATUS_IGNORED,
)
from app.models import DownloadTask, MediaFile, PTResource, ResourceMapping, Subscription
from app.services.subscription.subscription_service import SubscriptionService
from app.utils.timezone import now

logger = logging.getLogger(__name__)


class SubscriptionEpisodeService:
    """订阅集数状态管理服务"""

    @staticmethod
    async def refresh_episodes_status(
        db: AsyncSession, subscription_id: int
    ) -> Dict[str, Dict]:
        """
        全量刷新订阅的集数状态 (批量化处理)
        """
        subscription = await SubscriptionService.get_by_id(db, subscription_id)
        if not subscription or not subscription.is_tv_subscription:
            logger.warning(f"订阅{subscription_id}不是电视剧订阅，无法刷新集数状态")
            return {}

        unified_tv_id = subscription.unified_tv_id
        season = subscription.current_season
        total_episodes = subscription.total_episodes or 0
        start_episode = subscription.start_episode or 1
        target_tv_ids = subscription.all_matched_tv_ids or [unified_tv_id]

        if not unified_tv_id or not season:
            logger.warning(f"订阅{subscription_id}缺少 unified_tv_id 或 season")
            return {}

        # 1. 批量获取数据
        # 1.1 获取物理文件
        media_files_query = select(MediaFile).where(
            MediaFile.unified_table_name == "unified_tv_series",
            MediaFile.unified_resource_id.in_(target_tv_ids),
            MediaFile.season_number == season,
            MediaFile.status.in_(["identified", "completed"]),
        )
        media_files_result = await db.execute(media_files_query)
        all_media_files = media_files_result.scalars().all()

        # 1.2 获取下载任务
        pt_mapping_query = select(ResourceMapping.pt_resource_id).where(
            ResourceMapping.unified_table_name == "unified_tv_series",
            ResourceMapping.unified_resource_id.in_(target_tv_ids),
        )
        pt_mapping_result = await db.execute(pt_mapping_query)
        mapped_pt_ids = [row[0] for row in pt_mapping_result.all()]

        download_tasks_query = select(DownloadTask).where(
            (
                (DownloadTask.unified_table_name == "unified_tv_series") & 
                (DownloadTask.unified_resource_id.in_(target_tv_ids))
            ) | (
                DownloadTask.pt_resource_id.in_(mapped_pt_ids)
            )
        )
        download_tasks_result = await db.execute(download_tasks_query)
        all_download_tasks = download_tasks_result.scalars().all()

        # 1.3 获取 PT 资源
        pt_resources_query = select(PTResource).where(
            PTResource.id.in_(mapped_pt_ids)
        )
        pt_resources_result = await db.execute(pt_resources_query)
        all_pt_resources = pt_resources_result.scalars().all()
        pt_resource_map = {r.id: r for r in all_pt_resources}

        # 获取当前已有的状态，用于保留手动标记
        existing_status = subscription.episodes_status or {}

        # 2. 建立索引映射
        ep_media_files = {str(mf.episode_number): mf for mf in all_media_files}
        
        ep_downloading = {}
        for dt in all_download_tasks:
            pt_res = pt_resource_map.get(dt.pt_resource_id)
            if not pt_res or not pt_res.tv_info: continue
            if season not in (pt_res.tv_info.get("seasons") or []): continue
            ep_range = pt_res.tv_info.get("episodes", {}).get(str(season))
            if ep_range:
                start, end = ep_range.get("start"), ep_range.get("end")
                if start is not None and end is not None:
                    for ep in range(start, end + 1):
                        ep_downloading[str(ep)] = dt

        ep_pt_resources = {}
        for pr in all_pt_resources:
            if not pr.tv_info: continue
            if season not in (pr.tv_info.get("seasons") or []): continue
            ep_range = pr.tv_info.get("episodes", {}).get(str(season))
            if ep_range:
                start, end = ep_range.get("start"), ep_range.get("end")
                if start is not None and end is not None:
                    for ep in range(start, end + 1):
                        k = str(ep)
                        if k not in ep_pt_resources: ep_pt_resources[k] = []
                        ep_pt_resources[k].append(pr)

        # 3. 决定最终状态
        new_episodes_status = {}
        actual_end = max(total_episodes, start_episode)
        for episode in range(start_episode, actual_end + 1):
            ep_key = str(episode)
            
            # 使用决策树获取状态
            resolved = SubscriptionEpisodeService._resolve_status(
                ep_key,
                ep_media_files.get(ep_key),
                ep_downloading.get(ep_key),
                existing_status.get(ep_key, {}),
                ep_pt_resources.get(ep_key, [])
            )
            new_episodes_status[ep_key] = resolved

        # 4. 更新数据库
        subscription.episodes_status = new_episodes_status
        flag_modified(subscription, "episodes_status")
        await db.commit()

        logger.info(f"订阅{subscription_id}状态全量刷新完成")
        return new_episodes_status

    @staticmethod
    def _resolve_status(ep_key: str, mf: Optional[MediaFile], dt: Optional[DownloadTask], old_status: Dict, pt_list: List[PTResource]) -> Dict:
        """单集状态决策核心逻辑"""
        
        # Priority 1: 物理文件
        if mf:
            return {
                "status": EPISODE_STATUS_DOWNLOADED,
                "fileId": mf.id,
                "quality": mf.resolution,
                "fileSize": mf.file_size,
                "filePath": mf.file_path,
                "downloadedAt": mf.organized_at or mf.created_at,
            }

        # Priority 2: 下载任务
        if dt:
            if dt.progress == 100 or dt.status == "completed":
                return {
                    "status": EPISODE_STATUS_DOWNLOADED,
                    "taskId": dt.id,
                    "downloadedAt": dt.completed_at or dt.updated_at,
                    "note": "下载已完成 (任务进度)",
                }
            elif dt.status == "error":
                return {
                    "status": EPISODE_STATUS_FAILED,
                    "taskId": dt.id,
                    "error": dt.error_message,
                    "failedAt": dt.error_at,
                    "progress": dt.progress,
                }
            else:
                return {
                    "status": EPISODE_STATUS_DOWNLOADING,
                    "taskId": dt.id,
                    "progress": dt.progress,
                    "startedAt": dt.started_at or dt.created_at,
                }

        # Priority 3: 用户手动标记
        # 如果标记是被设为 waiting，视为“重置信号”，不在这里拦截，落入 Priority 4
        if (old_status.get("note") == "手动标记" or old_status.get("status") == EPISODE_STATUS_IGNORED):
            if old_status.get("status") != EPISODE_STATUS_WAITING:
                return old_status

        # Priority 4: PT 资源发现
        if pt_list:
            quality_priority = {"2160p": 4, "1080p": 3, "720p": 2, "480p": 1}
            best_res = max(pt_list, key=lambda r: quality_priority.get(r.resolution or "", 0), default=pt_list[0])
            return {
                "status": EPISODE_STATUS_AVAILABLE,
                "resourceIds": [r.id for r in pt_list],
                "qualities": list(set(r.resolution for r in pt_list if r.resolution)),
                "bestQuality": best_res.resolution,
                "resourceCount": len(pt_list),
                "foundAt": max((r.created_at for r in pt_list), default=now()),
            }

        # Priority 5: 等待中
        return {
            "status": EPISODE_STATUS_WAITING,
            "checkedAt": now()
        }

    @staticmethod
    async def update_episode_status(
        db: AsyncSession, subscription_id: int, episode: int, status_data: Dict
    ):
        """
        手动更新单集状态
        """
        subscription = await SubscriptionService.get_by_id(db, subscription_id)
        if not subscription: return

        current_status = subscription.episodes_status or {}
        new_status_map = copy.deepcopy(current_status)
        
        # 如果手动设置为 waiting，我们立即触发一次针对该集的刷新，以防其实是有资源的
        if status_data.get("status") == EPISODE_STATUS_WAITING:
            # 这里虽然是单集，但为了逻辑统一，目前调用全量刷新（批量模式性能很高，可以接受）
            await SubscriptionEpisodeService.refresh_episodes_status(db, subscription_id)
            return

        new_status_map[str(episode)] = status_data
        subscription.episodes_status = new_status_map
        flag_modified(subscription, "episodes_status")
        await db.commit()
        logger.info(f"手动更新订阅{subscription_id}第{episode}集状态为 {status_data.get('status')}")

    @staticmethod
    async def get_episodes_status_stats(episodes_status: Dict[str, Dict]) -> Dict:
        """计算统计信息"""
        if not episodes_status:
            return {"total": 0, "downloaded": 0, "downloading": 0, "available": 0, "waiting": 0, "failed": 0, "ignored": 0}

        def count_status(s): return sum(1 for e in episodes_status.values() if e.get("status") == s)
        
        return {
            "total": len(episodes_status),
            "downloaded": count_status(EPISODE_STATUS_DOWNLOADED),
            "downloading": count_status(EPISODE_STATUS_DOWNLOADING),
            "available": count_status(EPISODE_STATUS_AVAILABLE),
            "waiting": count_status(EPISODE_STATUS_WAITING),
            "failed": count_status(EPISODE_STATUS_FAILED),
            "ignored": count_status(EPISODE_STATUS_IGNORED),
        }
