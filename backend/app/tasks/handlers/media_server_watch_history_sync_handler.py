# -*- coding: utf-8 -*-
"""
媒体服务器观看历史同步任务处理器（通用）
"""
import logging
from typing import Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.tasks.base import BaseTaskHandler
from app.services.media_server.media_server_watch_history_service import MediaServerWatchHistoryService
from app.services.media_server.media_server_config_service import MediaServerConfigService
from app.services.task.task_execution_service import TaskExecutionService
from app.constants.event import EVENT_MEDIA_SERVER_WATCH_HISTORY_SYNCED
from app.events.bus import event_bus

logger = logging.getLogger(__name__)


class MediaServerWatchHistorySyncHandler(BaseTaskHandler):
    """媒体服务器观看历史同步任务（通用）"""

    @staticmethod
    async def execute(
        db: AsyncSession,
        params: Dict[str, Any],
        execution_id: int,
    ) -> Dict[str, Any]:
        """
        执行观看历史同步

        Args:
            db: 数据库会话
            params: 处理器参数
                - media_server_config_id: 媒体服务器配置ID (必需)
            execution_id: 任务执行ID

        Returns:
            同步结果
        """
        media_server_config_id = params.get("media_server_config_id")
        
        if media_server_config_id:
            # 同步单个服务器
            config = await MediaServerConfigService.get_by_id(db, media_server_config_id)
            if not config:
                raise ValueError(f"Media server config not found: {media_server_config_id}")

            await TaskExecutionService.append_log(
                db, execution_id, f"开始同步观看历史: {config.name} ({config.type})"
            )

            # 执行同步
            result = await MediaServerWatchHistoryService.sync_watch_history(db, media_server_config_id)

            # 更新进度
            await TaskExecutionService.update_progress(db, execution_id, 100, progress_detail=result)
            await TaskExecutionService.append_log(
                db, execution_id, f"同步完成: 同步 {result.get('synced_count', 0)} 条记录"
            )

            # 发布同步完成事件
            await event_bus.publish(
                EVENT_MEDIA_SERVER_WATCH_HISTORY_SYNCED,
                {
                    "user_id": config.user_id,  # 媒体服务器配置的所有者
                    "media_server_config_id": config.id,
                    "server_type": config.type,
                    "server_name": config.name,
                    "synced_count": result.get("synced_count", 0),
                    "new_count": result.get("new_count", 0),
                    "updated_count": result.get("updated_count", 0),
                    "related_type": "media_server_config",
                    "related_id": config.id,
                },
            )
            return result
        else:
            # 同步所有已启用同步的服务器
            configs = await MediaServerConfigService.get_all_with_sync_enabled(db)
            if not configs:
                await TaskExecutionService.append_log(db, execution_id, "没有启用观看历史同步的媒体服务器")
                return {"synced_count": 0, "server_count": 0}

            await TaskExecutionService.append_log(
                db, execution_id, f"发现 {len(configs)} 个已启用同步的媒体服务器，开始自动同步..."
            )

            total_synced = 0
            total_new = 0
            total_updated = 0
            
            from app.utils.timezone import now
            from datetime import timedelta

            for i, config in enumerate(configs):
                # 检查是否到了同步时间
                should_sync = False
                if not config.last_sync_at:
                    should_sync = True
                else:
                    from app.utils.timezone import to_system_tz
                    last_sync = to_system_tz(config.last_sync_at)
                    interval = config.watch_history_sync_interval or 60
                    if last_sync + timedelta(minutes=interval) <= now():
                        should_sync = True
                
                if not should_sync:
                    await TaskExecutionService.append_log(
                        db, execution_id, f"跳过 {config.name}: 尚未到同步间隔时间"
                    )
                    continue

                await TaskExecutionService.append_log(
                    db, execution_id, f"[{i+1}/{len(configs)}] 正在同步: {config.name}..."
                )
                
                try:
                    res = await MediaServerWatchHistoryService.sync_watch_history(db, config.id)
                    total_synced += res.get("synced_count", 0)
                    total_new += res.get("new_count", 0)
                    total_updated += res.get("updated_count", 0)
                    
                    await TaskExecutionService.append_log(
                        db, execution_id, 
                        f"  - 完成: 新增 {res.get('new_count', 0)}, 更新 {res.get('updated_count', 0)}"
                    )
                except Exception as e:
                    await TaskExecutionService.append_log(
                        db, execution_id, f"  - 失败: {str(e)}"
                    )
                    logger.error(f"Failed to sync watch history for {config.name}: {str(e)}")

                # 更新整体进度
                progress = int((i + 1) / len(configs) * 100)
                await TaskExecutionService.update_progress(db, execution_id, progress)

            summary = {
                "synced_count": total_synced,
                "new_count": total_new,
                "updated_count": total_updated,
                "server_count": len(configs)
            }
            
            await TaskExecutionService.append_log(
                db, execution_id, 
                f"全局同步完成: 共同步 {total_synced} 条记录 ({len(configs)} 个服务器)"
            )
            
            return summary
