# -*- coding: utf-8 -*-
"""
MediaInfo解析工具模块
提取视频文件的技术信息（分辨率、编码、音轨、字幕等）
"""
import json
from pathlib import Path
from typing import Optional

try:
    from pymediainfo import MediaInfo

    PYMEDIAINFO_AVAILABLE = True
except ImportError:
    PYMEDIAINFO_AVAILABLE = False


class MediaInfoParserError(Exception):
    """MediaInfo解析异常"""

    pass


def is_mediainfo_available() -> bool:
    """
    检查pymediainfo是否可用

    Returns:
        是否可用
    """
    return PYMEDIAINFO_AVAILABLE


def parse_media_file(file_path: str | Path) -> Optional[dict]:
    """
    解析媒体文件，提取技术信息

    Args:
        file_path: 文件路径

    Returns:
        包含技术信息的字典，如果解析失败返回None

    Raises:
        MediaInfoParserError: 解析失败
    """
    if not PYMEDIAINFO_AVAILABLE:
        raise MediaInfoParserError("pymediainfo库未安装，请运行: pip install pymediainfo")

    path = Path(file_path)
    if not path.exists():
        raise MediaInfoParserError(f"文件不存在: {file_path}")

    try:
        media_info = MediaInfo.parse(str(path))

        result = {
            "general": {},
            "video": [],
            "audio": [],
            "subtitle": [],
            "raw": None,
        }

        # 解析各个轨道
        for track in media_info.tracks:
            if track.track_type == "General":
                result["general"] = _parse_general_track(track)
            elif track.track_type == "Video":
                result["video"].append(_parse_video_track(track))
            elif track.track_type == "Audio":
                result["audio"].append(_parse_audio_track(track))
            elif track.track_type == "Text":
                result["subtitle"].append(_parse_subtitle_track(track))

        # 保存完整的MediaInfo JSON数据
        result["raw"] = json.loads(media_info.to_json())

        return result
    except Exception as e:
        raise MediaInfoParserError(f"解析媒体文件失败: {file_path}, 错误: {e}")


def _parse_general_track(track) -> dict:
    """解析General轨道"""
    return {
        "format": getattr(track, "format", None),
        "file_size": getattr(track, "file_size", None),
        "duration": getattr(track, "duration", None),  # 毫秒
        "overall_bit_rate": getattr(track, "overall_bit_rate", None),
        "encoded_date": getattr(track, "encoded_date", None),
        "writing_application": getattr(track, "writing_application", None),
    }


def _parse_video_track(track) -> dict:
    """解析Video轨道"""
    width = getattr(track, "width", None)
    height = getattr(track, "height", None)

    # 计算分辨率标签
    resolution_label = None
    if height:
        if height >= 2160:
            resolution_label = "2160p"
        elif height >= 1080:
            resolution_label = "1080p"
        elif height >= 720:
            resolution_label = "720p"
        elif height >= 480:
            resolution_label = "480p"
        else:
            resolution_label = f"{height}p"

    return {
        "codec": getattr(track, "format", None),
        "codec_id": getattr(track, "codec_id", None),
        "width": width,
        "height": height,
        "resolution": resolution_label,
        "aspect_ratio": getattr(track, "display_aspect_ratio", None),
        "frame_rate": getattr(track, "frame_rate", None),
        "bit_rate": getattr(track, "bit_rate", None),
        "bit_depth": getattr(track, "bit_depth", None),
        "color_space": getattr(track, "color_space", None),
        "chroma_subsampling": getattr(track, "chroma_subsampling", None),
        "duration": getattr(track, "duration", None),  # 毫秒
        "encoded_library": getattr(track, "encoded_library_name", None),
    }


def _parse_audio_track(track) -> dict:
    """解析Audio轨道"""
    channels = getattr(track, "channel_s", None)

    # 格式化声道信息（如 2 -> "2.0", 6 -> "5.1"）
    channels_format = None
    if channels:
        if channels == 2:
            channels_format = "2.0"
        elif channels == 6:
            channels_format = "5.1"
        elif channels == 8:
            channels_format = "7.1"
        else:
            channels_format = str(channels)

    return {
        "codec": getattr(track, "format", None),
        "codec_id": getattr(track, "codec_id", None),
        "channels": channels,
        "channels_format": channels_format,
        "sampling_rate": getattr(track, "sampling_rate", None),
        "bit_rate": getattr(track, "bit_rate", None),
        "bit_depth": getattr(track, "bit_depth", None),
        "language": getattr(track, "language", None),
        "title": getattr(track, "title", None),
        "default": getattr(track, "default", None) == "Yes",
        "forced": getattr(track, "forced", None) == "Yes",
    }


def _parse_subtitle_track(track) -> dict:
    """解析Subtitle轨道"""
    return {
        "codec": getattr(track, "format", None),
        "language": getattr(track, "language", None),
        "title": getattr(track, "title", None),
        "default": getattr(track, "default", None) == "Yes",
        "forced": getattr(track, "forced", None) == "Yes",
    }


def extract_simplified_info(parsed_data: dict) -> dict:
    """
    从完整解析结果中提取简化信息（用于存储到数据库）

    Args:
        parsed_data: parse_media_file返回的完整数据

    Returns:
        简化的字典，可直接用于MediaFile模型
    """
    result = {
        "duration": None,
        "resolution": None,
        "width": None,
        "height": None,
        "codec_video": None,
        "codec_audio": None,
        "bitrate_video": None,
        "bitrate_audio": None,
        "fps": None,
        "audio_channels": None,
        "audio_tracks": [],
        "subtitle_tracks": [],
        "mediainfo_full": parsed_data,
    }

    # 从General轨道获取时长
    general = parsed_data.get("general", {})
    if general.get("duration"):
        result["duration"] = int(general["duration"] / 1000)  # 转换为秒

    # 从第一条Video轨道获取视频信息
    video_tracks = parsed_data.get("video", [])
    if video_tracks:
        video = video_tracks[0]
        result["resolution"] = video.get("resolution")
        result["width"] = video.get("width")
        result["height"] = video.get("height")
        result["codec_video"] = video.get("codec")
        result["bitrate_video"] = video.get("bit_rate")
        result["fps"] = str(video.get("frame_rate")) if video.get("frame_rate") else None

    # 从第一条Audio轨道获取音频信息
    audio_tracks = parsed_data.get("audio", [])
    if audio_tracks:
        audio = audio_tracks[0]
        result["codec_audio"] = audio.get("codec")
        result["bitrate_audio"] = audio.get("bit_rate")
        result["audio_channels"] = audio.get("channels_format")

    # 保存所有音轨和字幕轨信息
    result["audio_tracks"] = [
        {
            "codec": track.get("codec"),
            "language": track.get("language"),
            "channels": track.get("channels_format"),
            "title": track.get("title"),
        }
        for track in audio_tracks
    ]

    result["subtitle_tracks"] = [
        {
            "codec": track.get("codec"),
            "language": track.get("language"),
            "title": track.get("title"),
        }
        for track in parsed_data.get("subtitle", [])
    ]

    return result


def get_video_duration_seconds(file_path: str | Path) -> Optional[int]:
    """
    快速获取视频时长（秒）

    Args:
        file_path: 文件路径

    Returns:
        时长（秒），失败返回None
    """
    try:
        parsed = parse_media_file(file_path)
        duration_ms = parsed.get("general", {}).get("duration")
        if duration_ms:
            return int(duration_ms / 1000)
        return None
    except Exception:
        return None


def get_video_resolution(file_path: str | Path) -> Optional[str]:
    """
    快速获取视频分辨率标签

    Args:
        file_path: 文件路径

    Returns:
        分辨率标签（如 "1080p"），失败返回None
    """
    try:
        parsed = parse_media_file(file_path)
        video_tracks = parsed.get("video", [])
        if video_tracks:
            return video_tracks[0].get("resolution")
        return None
    except Exception:
        return None
