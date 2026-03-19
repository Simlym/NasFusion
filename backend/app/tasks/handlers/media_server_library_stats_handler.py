# -*- coding: utf-8 -*-
"""
媒体服务器库统计更新任务处理器
"""
import logging
from typing import Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.tasks.base import BaseTaskHandler
from app.services.media_server.media_server_library_service import MediaServerLibraryService
from app.services.media_server.media_server_config_service import MediaServerConfigService
from app.services.task.task_execution_service import TaskExecutionService

logger = logging.getLogger(__name__)


class MediaServerLibraryStatsHandler(BaseTaskHandler):
    """媒体服务器库统计更新任务"""

    @staticmethod
    async def execute(
        db: AsyncSession,
        params: Dict[str, Any],
        execution_id: int,
    ) -> Dict[str, Any]:
        """
        执行媒体库统计更新

        Args:
            db: 数据库会话
            params: 处理器参数
                - media_server_config_id: 媒体服务器配置ID (必需)
            execution_id: 任务执行ID

        Returns:
            统计结果
        """
        media_server_config_id = params.get("media_server_config_id")
        
        if media_server_config_id:
            # 更新单个服务器
            config = await MediaServerConfigService.get_by_id(db, media_server_config_id)
            if not config:
                raise ValueError(f"Media server config not found: {media_server_config_id}")

            await TaskExecutionService.append_log(
                db, execution_id, f"开始更新媒体库统计: {config.name} ({config.type})"
            )

            # 执行统计更新
            result = await MediaServerLibraryService.update_library_stats(db, media_server_config_id)

            # 更新进度
            await TaskExecutionService.update_progress(db, execution_id, 100)
            await TaskExecutionService.append_log(db, execution_id, "统计更新完成")
            return result
        else:
            # 更新所有已配置的服务器
            # 注意：此处我们不仅更新启用了同步的，而是更新所有的，因为统计是基础功能
            from sqlalchemy import select
            from app.models.media_server_config import MediaServerConfig
            
            result = await db.execute(select(MediaServerConfig))
            configs = list(result.scalars().all())
            
            if not configs:
                await TaskExecutionService.append_log(db, execution_id, "未发现媒体服务器配置")
                return {"server_count": 0}

            await TaskExecutionService.append_log(
                db, execution_id, f"发现 {len(configs)} 个媒体服务器，开始自动更新统计数据..."
            )

            for i, config in enumerate(configs):
                await TaskExecutionService.append_log(
                    db, execution_id, f"[{i+1}/{len(configs)}] 正在更新: {config.name}..."
                )
                
                try:
                    await MediaServerLibraryService.update_library_stats(db, config.id)
                    await TaskExecutionService.append_log(db, execution_id, "  - 完成")
                except Exception as e:
                    await TaskExecutionService.append_log(db, execution_id, f"  - 失败: {str(e)}")
                    logger.error(f"Failed to update library stats for {config.name}: {str(e)}")

                # 更新整体进度
                progress = int((i + 1) / len(configs) * 100)
                await TaskExecutionService.update_progress(db, execution_id, progress)

            await TaskExecutionService.append_log(db, execution_id, "全局统计更新完成")
            return {"server_count": len(configs)}

        logger.info(f"Updated library stats for {config.name}: {result}")

        return result
