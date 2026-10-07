"""媒体整理完成后的媒体服务器刷新任务。"""
from typing import Any, Dict

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.media_server.media_server_config_service import MediaServerConfigService
from app.services.media_server.media_server_library_service import MediaServerLibraryService
from app.services.task.task_execution_service import TaskExecutionService
from app.tasks.base import BaseTaskHandler


class MediaServerLibraryRefreshHandler(BaseTaskHandler):
    """合并刷新启用了自动刷新的媒体服务器。"""

    @staticmethod
    async def execute(
        db: AsyncSession,
        params: Dict[str, Any],
        execution_id: int,
    ) -> Dict[str, Any]:
        user_id = params.get("user_id")
        if not user_id:
            raise ValueError("媒体库刷新任务缺少 user_id")

        configs = await MediaServerConfigService.get_all_with_auto_refresh_enabled(db, user_id)
        if not configs:
            await TaskExecutionService.append_log(db, execution_id, "没有启用自动刷新的媒体服务器")
            return {"total": 0, "success": 0, "failed": 0}

        success_count = 0
        failed_names = []
        for index, config in enumerate(configs, start=1):
            await TaskExecutionService.append_log(
                db, execution_id, f"刷新媒体服务器：{config.name} ({index}/{len(configs)})"
            )
            if await MediaServerLibraryService.refresh_library(db, config.id):
                success_count += 1
            else:
                failed_names.append(config.name)
            await TaskExecutionService.update_progress(
                db, execution_id, int(index / len(configs) * 100)
            )

        if failed_names:
            raise RuntimeError(f"媒体库刷新失败：{', '.join(failed_names)}")

        return {
            "total": len(configs),
            "success": success_count,
            "failed": 0,
            "organized_count": params.get("organized_count", 0),
        }
