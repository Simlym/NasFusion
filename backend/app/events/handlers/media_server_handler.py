# -*- coding: utf-8 -*-
"""
媒体服务器事件处理器
"""
import logging
from typing import Dict, Any

from app.core.database import async_session_local
from app.services.media_server.media_server_config_service import MediaServerConfigService
from app.services.media_server.media_server_library_service import MediaServerLibraryService

logger = logging.getLogger(__name__)


async def handle_media_organized_event(event_type: str, event_data: Dict[str, Any]) -> None:
    """
    处理媒体文件整理完成事件
    自动通知所有启用自动刷新的媒体服务器刷新媒体库

    Args:
        event_type: 事件类型
        event_data: 事件数据
            - user_id: 用户ID
            - media_file_id: 媒体文件ID
            - organized_path: 整理后的路径
            - media_type: 媒体类型
    """
    async with async_session_local() as db:
        try:
            user_id = event_data.get("user_id")
            media_file_id = event_data.get("media_file_id")
            organized_path = event_data.get("organized_path")

            if not user_id:
                logger.warning("Missing user_id in media_organized event")
                return

            # 获取用户所有启用自动刷新的媒体服务器配置
            configs = await MediaServerConfigService.get_all_with_auto_refresh_enabled(db, user_id)

            if not configs:
                logger.debug(f"No media server configs with auto_refresh enabled for user {user_id}")
                return

            # 遍历所有配置，逐个刷新
            for config in configs:
                try:
                    success = await MediaServerLibraryService.refresh_library(db, config.id)

                    if success:
                        logger.info(
                            f"Media server library refreshed: type={config.type}, "
                            f"name={config.name}, file={organized_path}"
                        )
                    else:
                        logger.warning(
                            f"Failed to refresh media server library: type={config.type}, " f"name={config.name}"
                        )
                except Exception as e:
                    logger.error(f"Error refreshing media server {config.name}: {str(e)}", exc_info=True)
                    # 继续处理下一个配置，不中断流程
                    continue

        except Exception as e:
            logger.exception(f"Failed to handle media_organized event: {str(e)}")
