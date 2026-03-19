# -*- coding: utf-8 -*-
"""
文件名解析服务
使用guessit库解析媒体文件名，提取标题、年份、季集等信息
"""
import logging
from typing import Optional, Dict, Any
from pathlib import Path

try:
    import guessit
    GUESSIT_AVAILABLE = True
except ImportError:
    GUESSIT_AVAILABLE = False
    guessit = None

logger = logging.getLogger(__name__)


class FilenameParserService:
    """文件名解析服务"""

    @staticmethod
    def is_available() -> bool:
        """检查guessit是否可用"""
        return GUESSIT_AVAILABLE

    @staticmethod
    def parse_filename(filename: str, media_type: Optional[str] = None) -> Dict[str, Any]:
        """
        解析文件名，提取媒体信息

        Args:
            filename: 文件名或路径
            media_type: 指定媒体类型 ('movie' 或 'episode')

        Returns:
            解析结果字典
        """
        if not GUESSIT_AVAILABLE:
            logger.error("guessit未安装")
            return {"error": "guessit未安装"}

        try:
            # 使用guessit解析
            options = {}
            if media_type == "movie":
                options["type"] = "movie"
            elif media_type in ("tv", "episode"):
                options["type"] = "episode"

            result = guessit.guessit(filename, options)

            # 转换为普通字典
            parsed = dict(result)

            # 标准化输出
            standardized = FilenameParserService._standardize_result(parsed)

            logger.debug(f"文件名解析结果: {filename} -> {standardized}")
            return standardized

        except Exception as e:
            logger.error(f"解析文件名失败: {filename}, 错误: {e}")
            return {"error": str(e)}

    @staticmethod
    def _standardize_result(parsed: dict) -> dict:
        """
        标准化解析结果

        Args:
            parsed: guessit原始结果

        Returns:
            标准化后的字典
        """
        result = {
            "type": parsed.get("type", "unknown"),  # movie 或 episode
            "title": None,
            "year": None,
            "season": None,
            "episode": None,
            "episode_title": None,
            "resolution": None,
            "source": None,
            "codec": None,
            "audio_codec": None,
            "release_group": None,
            "language": None,
            "subtitle_language": None,
            "raw": {k: str(v) if not isinstance(v, (str, int, float, bool, list, dict, type(None))) else v for k, v in parsed.items()},  # 保留原始数据（转换非基本类型）
        }

        # 提取标题
        if "title" in parsed:
            result["title"] = parsed["title"]

        # 提取年份
        if "year" in parsed:
            result["year"] = parsed["year"]

        # 提取季集信息（电视剧）
        if "season" in parsed:
            season = parsed["season"]
            if isinstance(season, list):
                result["season"] = season[0] if season else None
            else:
                result["season"] = season

        if "episode" in parsed:
            episode = parsed["episode"]
            if isinstance(episode, list):
                result["episode"] = episode[0] if episode else None
            else:
                result["episode"] = episode

        if "episode_title" in parsed:
            result["episode_title"] = parsed["episode_title"]

        # 提取视频质量信息
        if "screen_size" in parsed:
            result["resolution"] = parsed["screen_size"]

        if "source" in parsed:
            source = parsed["source"]
            if isinstance(source, list):
                result["source"] = source[0] if source else None
            else:
                result["source"] = source

        if "video_codec" in parsed:
            result["codec"] = parsed["video_codec"]

        if "audio_codec" in parsed:
            audio = parsed["audio_codec"]
            if isinstance(audio, list):
                result["audio_codec"] = audio[0] if audio else None
            else:
                result["audio_codec"] = audio

        # 提取发布组
        if "release_group" in parsed:
            result["release_group"] = parsed["release_group"]

        # 提取语言
        if "language" in parsed:
            lang = parsed["language"]
            if isinstance(lang, list):
                result["language"] = [str(l) for l in lang]
            else:
                result["language"] = [str(lang)]

        if "subtitle_language" in parsed:
            sub_lang = parsed["subtitle_language"]
            if isinstance(sub_lang, list):
                result["subtitle_language"] = [str(l) for l in sub_lang]
            else:
                result["subtitle_language"] = [str(sub_lang)]

        return result

    @staticmethod
    def parse_media_file(file_path: str) -> Dict[str, Any]:
        """
        解析媒体文件路径

        Args:
            file_path: 完整文件路径

        Returns:
            解析结果
        """
        path = Path(file_path)
        filename = path.name

        # 首先尝试从文件名解析
        result = FilenameParserService.parse_filename(filename)

        # 如果文件名解析失败或信息不足，尝试从父目录获取信息
        if not result.get("title") or result.get("error"):
            parent_name = path.parent.name
            if parent_name and parent_name != ".":
                parent_result = FilenameParserService.parse_filename(parent_name)
                if parent_result.get("title") and not parent_result.get("error"):
                    # 合并信息，文件名优先
                    for key, value in parent_result.items():
                        if key not in result or not result[key]:
                            result[key] = value

        result["file_name"] = filename
        result["file_path"] = str(path)

        return result

    @staticmethod
    def guess_media_type(parsed_result: dict) -> str:
        """
        根据解析结果猜测媒体类型

        Args:
            parsed_result: 解析结果

        Returns:
            媒体类型: movie, tv, anime, unknown
        """
        guessit_type = parsed_result.get("type", "unknown")

        if guessit_type == "movie":
            return "movie"
        elif guessit_type == "episode":
            # 判断是否是动漫
            title = parsed_result.get("title", "").lower()
            anime_keywords = ["anime", "ova", "oad"]

            if any(kw in title for kw in anime_keywords):
                return "anime"

            # 可以通过其他规则判断是否为动漫
            # 例如：发布组包含动漫相关词汇
            release_group = str(parsed_result.get("release_group", "")).lower()
            if any(kw in release_group for kw in anime_keywords):
                return "anime"

            return "tv"
        else:
            return "unknown"

    @staticmethod
    def build_search_query(parsed_result: dict) -> dict:
        """
        根据解析结果构建搜索查询

        Args:
            parsed_result: 文件名解析结果

        Returns:
            搜索查询参数
        """
        query = {
            "query": parsed_result.get("title", ""),
            "year": parsed_result.get("year"),
            "media_type": FilenameParserService.guess_media_type(parsed_result),
        }

        # 清理查询字符串
        if query["query"]:
            # 移除一些常见的干扰词
            clean_title = query["query"]
            # 可以添加更多清理逻辑
            query["query"] = clean_title.strip()

        return query


# 示例用法
if __name__ == "__main__":
    # 测试解析
    test_files = [
        "Inception.2010.1080p.BluRay.x264-GROUP.mkv",
        "Breaking.Bad.S01E01.720p.BluRay.x264.mkv",
        "The.Matrix.1999.2160p.UHD.BluRay.REMUX.HDR.HEVC.Atmos-EPSiLON.mkv",
        "Game.of.Thrones.S08E06.The.Iron.Throne.1080p.mkv",
    ]

    for f in test_files:
        print(f"File: {f}")
        result = FilenameParserService.parse_filename(f)
        print(f"Result: {result}")
        print(f"Search Query: {FilenameParserService.build_search_query(result)}")
        print("-" * 50)
