# -*- coding: utf-8 -*-
"""
媒体服务器适配器基类（支持 Jellyfin/Emby/Plex）
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List


class BaseMediaServerAdapter(ABC):
    """媒体服务器适配器基类（支持 Jellyfin/Emby/Plex）"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化适配器

        Args:
            config: 适配器配置字典
                - name: 服务器名称
                - host: 服务器地址
                - port: 端口号
                - use_ssl: 是否使用SSL
                - api_key: API Key（Jellyfin/Emby使用）
                - token: 访问令牌（Plex使用）
        """
        self.config = config
        self.server_name = config.get("name", "Unknown")
        self.host = config.get("host", "")
        self.port = config.get("port", 8096)
        self.use_ssl = config.get("use_ssl", False)
        self.api_key = config.get("api_key", "")

    @abstractmethod
    async def test_connection(self) -> bool:
        """
        测试连接

        Returns:
            bool: 连接是否成功
        """
        pass

    @abstractmethod
    async def get_libraries(self) -> List[Dict[str, Any]]:
        """
        获取媒体库列表

        Returns:
            List[Dict]: 媒体库列表，标准化格式：
                [
                    {
                        "id": "library_id",
                        "name": "Movies",
                        "type": "movies",  # movies/tvshows/music/books
                        "locations": ["/path/to/library"],
                        "image_url": "relative/path/to/image",
                        "web_url": "http://server:port/web/index.html#!/home?parentId=xxx"
                    },
                    ...
                ]
        """
        pass

    @abstractmethod
    async def refresh_library(self, library_id: str = None) -> bool:
        """
        刷新媒体库

        Args:
            library_id: 媒体库ID，如果为None则刷新所有媒体库

        Returns:
            bool: 刷新操作是否成功触发
        """
        pass

    @abstractmethod
    async def get_users(self) -> List[Dict[str, Any]]:
        """
        获取媒体服务器用户列表

        Returns:
            List[Dict]: 用户列表，标准化格式：
                [
                    {
                        "id": "user_id",
                        "name": "username",
                        "is_admin": True
                    },
                    ...
                ]
        """
        pass

    @abstractmethod
    async def get_watch_history(self, user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取用户观看历史

        Args:
            user_id: 媒体服务器的用户ID
            limit: 返回记录数量限制

        Returns:
            List[Dict]: 观看历史列表，包含服务器原始数据
        """
        pass

    @abstractmethod
    async def get_library_stats(self) -> Dict[str, Any]:
        """
        获取媒体库统计信息

        Returns:
            Dict: 统计信息，不同服务器格式可能不同
                {
                    "MovieCount": 150,
                    "SeriesCount": 50,
                    "EpisodeCount": 500,
                    ...
                }
        """
        pass

    @abstractmethod
    async def get_system_info(self) -> Dict[str, Any]:
        """
        获取系统信息

        Returns:
            Dict: 系统信息
                {
                    "Id": "server_id",
                    "ServerName": "server_name",
                    "Version": "10.8.0",
                    "OperatingSystem": "Linux",
                    ...
                }
        """
        pass

    @abstractmethod
    async def get_sessions(self) -> List[Dict[str, Any]]:
        """
        获取活动会话

        Returns:
            List[Dict]: 会话列表
        """
        pass

    @abstractmethod
    async def get_latest_media(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        获取最近添加的媒体

        Args:
            limit: 返回数量限制

        Returns:
            List[Dict]: 媒体列表
        """
        pass

    @abstractmethod
    async def get_item(self, item_id: str) -> Dict[str, Any]:
        """
        获取项目详情

        Args:
            item_id: 项目ID

        Returns:
            Dict: 项目详情
        """
        pass

    @abstractmethod
    async def search(self, query: str) -> List[Dict[str, Any]]:
        """
        搜索媒体

        Args:
            query: 搜索关键词

        Returns:
            List[Dict]: 搜索结果列表
        """
        pass
