# -*- coding: utf-8 -*-
"""
NFO 解析服务
读取和解析本地 NFO 文件（Kodi/Jellyfin/Emby 标准格式）
"""
import logging
import os
from typing import Dict, Any, Optional, List
from xml.etree import ElementTree as ET
from pathlib import Path

logger = logging.getLogger(__name__)


class NFOParserService:
    """NFO 解析服务 - 读取和解析本地 NFO 文件"""

    @staticmethod
    async def parse_nfo(nfo_path: str) -> Optional[Dict[str, Any]]:
        """
        解析 NFO 文件

        Args:
            nfo_path: NFO 文件路径

        Returns:
            解析后的数据字典，如果解析失败返回 None
        """
        try:
            if not os.path.exists(nfo_path):
                logger.warning(f"NFO 文件不存在: {nfo_path}")
                return None

            # 读取 XML 文件
            tree = ET.parse(nfo_path)
            root = tree.getroot()

            # 根据根节点标签判断NFO类型
            if root.tag == "movie":
                return NFOParserService._parse_movie_nfo(root)
            elif root.tag == "tvshow":
                return NFOParserService._parse_tv_show_nfo(root)
            elif root.tag == "episodedetails":
                return NFOParserService._parse_episode_nfo(root)
            elif root.tag == "season":
                return NFOParserService._parse_season_nfo(root)
            else:
                logger.warning(f"未知的NFO类型: {root.tag}, 文件: {nfo_path}")
                return None

        except ET.ParseError as e:
            logger.error(f"NFO XML 解析失败: {nfo_path}, 错误: {e}")
            return None
        except Exception as e:
            logger.exception(f"NFO 解析异常: {nfo_path}")
            return None

    @staticmethod
    def _parse_movie_nfo(root: ET.Element) -> Dict[str, Any]:
        """
        解析电影 NFO

        Returns:
            {
                "type": "movie",
                "title": "标题",
                "original_title": "原始标题",
                "plot": "剧情简介",
                "rating": 8.5,
                "year": 2024,
                "genres": ["剧情", "家庭"],
                "actors": [{"name": "演员名", "role": "角色名", "thumb": "头像URL"}],
                "director": "导演",
                "runtime": 120,
                "premiered": "2024-05-07",
                "studio": "制片公司",
                ...
            }
        """
        data = {"type": "movie"}

        # 基础信息
        data["title"] = NFOParserService._get_text(root, "title")
        data["original_title"] = NFOParserService._get_text(root, "originaltitle")
        data["plot"] = NFOParserService._get_text(root, "plot")
        data["outline"] = NFOParserService._get_text(root, "outline")
        data["tagline"] = NFOParserService._get_text(root, "tagline")

        # 评分
        rating_value = NFOParserService._get_text(root, "rating")
        if rating_value:
            try:
                data["rating"] = float(rating_value)
            except ValueError:
                pass

        # 年份
        year_value = NFOParserService._get_text(root, "year")
        if year_value:
            try:
                data["year"] = int(year_value)
            except ValueError:
                pass

        # 时长（分钟）
        runtime_value = NFOParserService._get_text(root, "runtime")
        if runtime_value:
            try:
                # 可能是 "120" 或 "120 min"
                data["runtime"] = int(runtime_value.split()[0])
            except (ValueError, IndexError):
                pass

        # 日期
        data["premiered"] = NFOParserService._get_text(root, "premiered")
        data["releasedate"] = NFOParserService._get_text(root, "releasedate")

        # 分类和制片公司
        data["genres"] = NFOParserService._get_list(root, "genre")
        data["tags"] = NFOParserService._get_list(root, "tag")
        data["studios"] = NFOParserService._get_list(root, "studio")
        data["studio"] = data["studios"][0] if data["studios"] else None
        data["countries"] = NFOParserService._get_list(root, "country")

        # 导演和编剧
        data["directors"] = NFOParserService._get_list(root, "director")
        data["director"] = data["directors"][0] if data["directors"] else None
        data["writers"] = NFOParserService._get_list(root, "credits")

        # 演员
        data["actors"] = NFOParserService._parse_actors(root)

        # 海报和背景图
        data["poster"] = NFOParserService._get_text(root, "thumb")
        data["fanart"] = NFOParserService._get_text(root, "fanart")

        # IMDB/TMDB/Douban ID
        data["imdb_id"] = NFOParserService._get_text(root, "id")
        data["tmdb_id"] = NFOParserService._get_text(root, "tmdbid")
        data["douban_id"] = NFOParserService._get_text(root, "doubanid")

        # 从 <uniqueid> 标签提取ID（TMM等工具的标准格式）
        NFOParserService._parse_unique_ids(root, data)

        return data

    @staticmethod
    def _parse_tv_show_nfo(root: ET.Element) -> Dict[str, Any]:
        """
        解析剧集 NFO（tvshow.nfo）

        Returns:
            {
                "type": "tvshow",
                "title": "剧集名",
                "plot": "剧情简介",
                "rating": 9.0,
                "premiered": "2016-09-20",
                "genres": ["剧情", "家庭"],
                "actors": [...],
                ...
            }
        """
        data = {"type": "tvshow"}

        # 基础信息
        data["title"] = NFOParserService._get_text(root, "title")
        data["original_title"] = NFOParserService._get_text(root, "originaltitle")
        data["plot"] = NFOParserService._get_text(root, "plot")
        data["outline"] = NFOParserService._get_text(root, "outline")

        # 评分
        rating_value = NFOParserService._get_text(root, "rating")
        if rating_value:
            try:
                data["rating"] = float(rating_value)
            except ValueError:
                pass

        # 日期
        data["premiered"] = NFOParserService._get_text(root, "premiered")
        data["year"] = NFOParserService._get_text(root, "year")

        # 状态
        data["status"] = NFOParserService._get_text(root, "status")

        # 分类
        data["genres"] = NFOParserService._get_list(root, "genre")
        data["tags"] = NFOParserService._get_list(root, "tag")
        data["studios"] = NFOParserService._get_list(root, "studio")
        data["studio"] = data["studios"][0] if data["studios"] else None

        # 演员
        data["actors"] = NFOParserService._parse_actors(root)

        # ID
        data["tvdb_id"] = NFOParserService._get_text(root, "id")
        data["tmdb_id"] = NFOParserService._get_text(root, "tmdbid")
        data["imdb_id"] = NFOParserService._get_text(root, "imdbid")
        data["douban_id"] = NFOParserService._get_text(root, "doubanid")

        # 从 <uniqueid> 标签提取ID（TMM等工具的标准格式）
        NFOParserService._parse_unique_ids(root, data)

        return data

    @staticmethod
    def _parse_episode_nfo(root: ET.Element) -> Dict[str, Any]:
        """
        解析单集 NFO

        Returns:
            {
                "type": "episode",
                "title": "集标题",
                "season": 1,
                "episode": 1,
                "plot": "本集简介",
                "runtime": 45,
                ...
            }
        """
        data = {"type": "episode"}

        # 基础信息
        data["title"] = NFOParserService._get_text(root, "title")
        data["plot"] = NFOParserService._get_text(root, "plot")

        # 季集信息
        season_value = NFOParserService._get_text(root, "season")
        if season_value:
            try:
                data["season"] = int(season_value)
            except ValueError:
                pass

        episode_value = NFOParserService._get_text(root, "episode")
        if episode_value:
            try:
                data["episode"] = int(episode_value)
            except ValueError:
                pass

        # 评分
        rating_value = NFOParserService._get_text(root, "rating")
        if rating_value:
            try:
                data["rating"] = float(rating_value)
            except ValueError:
                pass

        # 时长
        runtime_value = NFOParserService._get_text(root, "runtime")
        if runtime_value:
            try:
                data["runtime"] = int(runtime_value.split()[0])
            except (ValueError, IndexError):
                pass

        # 日期
        data["aired"] = NFOParserService._get_text(root, "aired")

        # 导演和编剧
        data["directors"] = NFOParserService._get_list(root, "director")
        data["director"] = data["directors"][0] if data["directors"] else None
        data["writers"] = NFOParserService._get_list(root, "credits")

        # 演员（通常继承自剧集）
        data["actors"] = NFOParserService._parse_actors(root)

        return data

    @staticmethod
    def _parse_season_nfo(root: ET.Element) -> Dict[str, Any]:
        """
        解析季度 NFO

        Returns:
            {
                "type": "season",
                "title": "第 1 季",
                "season": 1,
                "plot": "季度简介",
                ...
            }
        """
        data = {"type": "season"}

        # 基础信息
        data["title"] = NFOParserService._get_text(root, "title")
        data["plot"] = NFOParserService._get_text(root, "plot")
        data["outline"] = NFOParserService._get_text(root, "outline")

        # 季度编号
        season_value = NFOParserService._get_text(root, "seasonnumber")
        if season_value:
            try:
                data["season"] = int(season_value)
            except ValueError:
                pass

        # 海报（从 <art><poster> 标签）
        art = root.find("art")
        if art is not None:
            poster = art.find("poster")
            if poster is not None and poster.text:
                data["poster"] = poster.text.strip()

        return data

    @staticmethod
    def _parse_unique_ids(root: ET.Element, data: Dict[str, Any]):
        """
        从 <uniqueid> 标签提取各平台ID

        TMM/Kodi标准格式：
          <uniqueid type="tmdb">12345</uniqueid>
          <uniqueid type="imdb">tt1234567</uniqueid>
          <uniqueid type="douban">1234567</uniqueid>
          <uniqueid type="tvdb">12345</uniqueid>

        只在对应字段为空时才填充，避免覆盖已解析的专用标签值。
        """
        for uid_elem in root.findall("uniqueid"):
            uid_type = (uid_elem.get("type") or "").lower()
            uid_value = uid_elem.text.strip() if uid_elem.text else None
            if not uid_value:
                continue

            if uid_type == "tmdb" and not data.get("tmdb_id"):
                data["tmdb_id"] = uid_value
            elif uid_type == "imdb" and not data.get("imdb_id"):
                data["imdb_id"] = uid_value
            elif uid_type == "douban" and not data.get("douban_id"):
                data["douban_id"] = uid_value
            elif uid_type == "tvdb" and not data.get("tvdb_id"):
                data["tvdb_id"] = uid_value

    @staticmethod
    def _get_text(root: ET.Element, tag: str) -> Optional[str]:
        """获取XML标签文本内容"""
        element = root.find(tag)
        if element is not None and element.text:
            return element.text.strip()
        return None

    @staticmethod
    def _get_list(root: ET.Element, tag: str) -> List[str]:
        """获取XML标签列表（多个同名标签）"""
        elements = root.findall(tag)
        return [el.text.strip() for el in elements if el.text]

    @staticmethod
    def _parse_actors(root: ET.Element) -> List[Dict[str, Any]]:
        """
        解析演员信息

        Returns:
            [{"name": "演员名", "role": "角色名", "thumb": "头像URL"}, ...]
        """
        actors = []
        for actor_elem in root.findall("actor"):
            actor = {}

            name = actor_elem.find("name")
            if name is not None and name.text:
                actor["name"] = name.text.strip()
            else:
                continue  # 没有名字的演员跳过

            role = actor_elem.find("role")
            if role is not None and role.text:
                actor["role"] = role.text.strip()

            thumb = actor_elem.find("thumb")
            if thumb is not None and thumb.text:
                actor["thumb"] = thumb.text.strip()

            actors.append(actor)

        return actors
