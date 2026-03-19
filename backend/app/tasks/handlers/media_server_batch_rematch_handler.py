# -*- coding: utf-8 -*-
"""
媒体服务器批量重新匹配任务处理器
用于批量重新匹配观看历史到本地媒体资源
"""
import logging
from typing import Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.tasks.base import BaseTaskHandler
from app.models.media_server_watch_history import MediaServerWatchHistory
from app.services.media_server.media_server_watch_history_service import MediaServerWatchHistoryService
from app.services.media_server.media_server_config_service import MediaServerConfigService
from app.services.task.task_execution_service import TaskExecutionService

logger = logging.getLogger(__name__)


class MediaServerBatchRematchHandler(BaseTaskHandler):
    """批量重新匹配观看历史任务处理器"""

    @staticmethod
    async def execute(db: AsyncSession, params: Dict[str, Any], execution_id: int) -> Dict[str, Any]:
        """
        执行批量重新匹配任务

        Args:
            db: 数据库会话
            params: 任务参数
                - config_id: 媒体服务器配置ID（可选）
                - user_id: 用户ID（可选）
                - unmatched_only: 是否只匹配未关联的记录（默认 False）
            execution_id: 任务执行ID

        Returns:
            Dict: 执行结果
                {
                    "total_count": 100,
                    "matched_count": 85,
                    "skipped_count": 15,
                    "details": {...}
                }
        """
        config_id = params.get("config_id")
        user_id = params.get("user_id")
        unmatched_only = params.get("unmatched_only", False)

        await TaskExecutionService.append_log(
            db, execution_id,
            f"开始批量重新匹配任务 (config_id={config_id}, user_id={user_id}, unmatched_only={unmatched_only})"
        )

        # 构建查询条件
        query = select(MediaServerWatchHistory)

        if config_id:
            query = query.where(MediaServerWatchHistory.media_server_config_id == config_id)

        if user_id:
            query = query.where(MediaServerWatchHistory.user_id == user_id)

        if unmatched_only:
            # 只匹配未关联到统一资源的记录
            query = query.where(MediaServerWatchHistory.unified_resource_id.is_(None))

        # 执行查询
        result = await db.execute(query)
        histories = list(result.scalars().all())

        total_count = len(histories)
        matched_count = 0
        skipped_count = 0

        await TaskExecutionService.append_log(
            db, execution_id,
            f"找到 {total_count} 条观看历史记录，开始匹配..."
        )

        # 获取配置（用于路径映射）
        config_cache = {}

        # 批量匹配
        for idx, history in enumerate(histories, 1):
            try:
                # 获取配置（缓存）
                if history.media_server_config_id not in config_cache:
                    config = await MediaServerConfigService.get_by_id(db, history.media_server_config_id)
                    config_cache[history.media_server_config_id] = config
                else:
                    config = config_cache[history.media_server_config_id]

                # 执行匹配
                await MediaServerWatchHistoryService.match_local_media(db, history, config)

                # 检查匹配结果
                if history.unified_resource_id:
                    matched_count += 1
                else:
                    skipped_count += 1

                # 更新进度
                if idx % 10 == 0 or idx == total_count:
                    progress = int((idx / total_count) * 100)
                    await TaskExecutionService.update_progress(
                        db, execution_id, progress,
                        f"已处理 {idx}/{total_count} 条记录"
                    )

            except Exception as e:
                logger.error(f"Failed to match history {history.id}: {str(e)}")
                skipped_count += 1

        # 任务完成
        await TaskExecutionService.append_log(
            db, execution_id,
            f"✅ 批量匹配完成！总计: {total_count}, 匹配成功: {matched_count}, 跳过: {skipped_count}"
        )

        return {
            "total_count": total_count,
            "matched_count": matched_count,
            "skipped_count": skipped_count,
            "match_rate": f"{(matched_count / total_count * 100):.1f}%" if total_count > 0 else "0%"
        }
