# -*- coding: utf-8 -*-
"""
媒体信息服务
提取和管理媒体文件的技术信息
"""
import logging
from pathlib import Path
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.media_file import MediaFile
from app.utils.mediainfo_parser import (
    extract_simplified_info,
    is_mediainfo_available,
    parse_media_file,
    MediaInfoParserError,
)

logger = logging.getLogger(__name__)


class MediaInfoService:
    """媒体信息服务"""

    @staticmethod
    def check_availability() -> bool:
        """
        检查MediaInfo是否可用

        Returns:
            是否可用
        """
        return is_mediainfo_available()

    @staticmethod
    async def extract_and_update(db: AsyncSession, media_file: MediaFile) -> bool:
        """
        提取媒体文件的技术信息并更新数据库

        Args:
            db: 数据库会话
            media_file: 媒体文件对象

        Returns:
            是否成功

        Raises:
            MediaInfoParserError: 解析失败
        """
        if not is_mediainfo_available():
            logger.warning("pymediainfo未安装，跳过MediaInfo提取")
            return False

        try:
            # 检查文件是否存在
            file_path = Path(media_file.file_path)
            if not file_path.exists():
                logger.error(f"文件不存在: {media_file.file_path}")
                media_file.error_message = "文件不存在"
                media_file.error_step = "mediainfo_extract"
                await db.commit()
                return False

            # 解析媒体文件
            logger.info(f"开始提取MediaInfo: {media_file.file_path}")
            parsed_data = parse_media_file(file_path)

            if not parsed_data:
                logger.error(f"MediaInfo解析失败: {media_file.file_path}")
                media_file.error_message = "MediaInfo解析失败"
                media_file.error_step = "mediainfo_extract"
                await db.commit()
                return False

            # 提取简化信息
            simplified = extract_simplified_info(parsed_data)

            # 写入模型实际列：resolution、video_codec、duration
            media_file.duration = simplified.get("duration")
            media_file.resolution = simplified.get("resolution")
            media_file.video_codec = simplified.get("codec_video")

            # 其余技术信息写入 tech_info JSON 列
            tech_info = {
                "width": simplified.get("width"),
                "height": simplified.get("height"),
                "codec_audio": simplified.get("codec_audio"),
                "bitrate_video": simplified.get("bitrate_video"),
                "bitrate_audio": simplified.get("bitrate_audio"),
                "fps": simplified.get("fps"),
                "audio_channels": simplified.get("audio_channels"),
                "audio_tracks": simplified.get("audio_tracks"),
                "subtitle_tracks": simplified.get("subtitle_tracks"),
            }
            media_file.tech_info = tech_info

            await db.commit()
            await db.refresh(media_file)

            logger.info(
                f"MediaInfo提取成功: {media_file.file_name}, "
                f"分辨率: {media_file.resolution}, "
                f"视频编码: {media_file.codec_video}, "
                f"时长: {media_file.duration}秒"
            )
            return True

        except MediaInfoParserError as e:
            logger.error(f"MediaInfo解析异常: {media_file.file_path}, 错误: {e}")
            media_file.error_message = str(e)
            media_file.error_step = "mediainfo_extract"
            await db.commit()
            return False
        except Exception as e:
            logger.exception(f"提取MediaInfo时发生未知错误: {media_file.file_path}")
            media_file.error_message = f"未知错误: {e}"
            media_file.error_step = "mediainfo_extract"
            await db.commit()
            return False

    @staticmethod
    async def extract_info_dict(file_path: str) -> Optional[dict]:
        """
        提取媒体文件信息（不更新数据库，用于预览）

        Args:
            file_path: 文件路径

        Returns:
            简化的信息字典，失败返回None
        """
        if not is_mediainfo_available():
            logger.warning("pymediainfo未安装")
            return None

        try:
            parsed_data = parse_media_file(file_path)
            if parsed_data:
                return extract_simplified_info(parsed_data)
            return None
        except Exception as e:
            logger.error(f"提取MediaInfo失败: {file_path}, 错误: {e}")
            return None
