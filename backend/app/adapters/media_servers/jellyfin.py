# -*- coding: utf-8 -*-
"""
Jellyfin 适配器
"""
import httpx
import logging
from typing import Dict, Any, List, Optional

from app.adapters.media_servers.base import BaseMediaServerAdapter

logger = logging.getLogger(__name__)


class JellyfinAdapter(BaseMediaServerAdapter):
    """Jellyfin 适配器"""

    # 类级别缓存，按 (base_url, api_key) 存储 user_id，跨实例复用
    _user_id_cache: Dict[str, str] = {}

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

        # 构建基础 URL
        protocol = "https" if self.use_ssl else "http"
        self.base_url = f"{protocol}://{self.host}:{self.port}"

        # HTTP 客户端配置
        self.client_config = {
            "timeout": httpx.Timeout(30.0),
            "follow_redirects": True,
        }

    async def _get_user_id(self) -> str:
        """
        获取用户 ID（类级别缓存，跨请求复用）

        Returns:
            str: 用户 ID

        Raises:
            ValueError: 如果媒体服务器中没有用户
        """
        cache_key = f"{self.base_url}:{self.api_key}"
        if cache_key not in JellyfinAdapter._user_id_cache:
            users = await self.get_users()
            if not users:
                raise ValueError("No users found in media server")
            JellyfinAdapter._user_id_cache[cache_key] = users[0]["id"]
        return JellyfinAdapter._user_id_cache[cache_key]

    async def test_connection(self) -> bool:
        """
        测试 Jellyfin 连接

        Returns:
            bool: 连接是否成功
        """
        try:
            async with httpx.AsyncClient(**self.client_config) as client:
                response = await client.get(
                    f"{self.base_url}/System/Info", headers={"X-Emby-Token": self.api_key}
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Jellyfin connection test failed: {str(e)}")
            return False

    async def get_libraries(self) -> List[Dict[str, Any]]:
        """
        获取 Jellyfin 媒体库列表

        Returns:
            List[Dict]: 标准化的媒体库列表
        """
        try:
            async with httpx.AsyncClient(**self.client_config) as client:
                response = await client.get(
                    f"{self.base_url}/Library/VirtualFolders", headers={"X-Emby-Token": self.api_key}
                )
                response.raise_for_status()
                libraries = response.json()

                # 标准化返回格式
                result = []
                # 获取用户ID（同步库统计需要用户权限）
                users = await self.get_users()
                user_id = users[0]["id"] if users else ""

                for lib in libraries:
                    # Jellyfin 的 CollectionType 映射到标准类型
                    collection_type = lib.get("CollectionType", "unknown")
                    standard_type = self._map_collection_type(collection_type)
                    lib_id = lib.get("ItemId")
                    # 获取条目数量
                    item_count = 0
                    if user_id and lib_id:
                        try:
                            # 尝试获取该父节点下的所有子项目总数
                            # 移除 IncludeItemTypes 以包含所有被 Jellyfin 索引的文件
                            count_params = {
                                "ParentId": lib_id,
                                "Recursive": "true",
                                "Limit": 0,
                                "Fields": "BasicSyncInfo" # 最小化字段
                            }
                            count_res = await client.get(
                                f"{self.base_url}/Users/{user_id}/Items",
                                headers={"X-Emby-Token": self.api_key},
                                params=count_params
                            )
                            if count_res.status_code == 200:
                                res_json = count_res.json()
                                item_count = res_json.get("TotalRecordCount", 0)
                                # 记录一下如果还是 0 的情况
                                if item_count == 0:
                                    logger.debug(f"Jellyfin library {lib_id} ({lib.get('Name')}) returned 0 items. URL: {count_res.url}")
                        except Exception as e:
                            logger.error(f"Failed to get item count for library {lib_id}: {str(e)}")

                    result.append(
                        {
                            "id": lib_id,
                            "name": lib.get("Name"),
                            "type": standard_type,
                            "locations": lib.get("Locations", []),
                            "image_url": f"/Items/{lib_id}/Images/Primary",
                            "web_url": f"{self.base_url}/web/index.html#!/home?parentId={lib_id}",
                            "item_count": item_count,
                            "last_scan_at": None, # Jellyfin 库级别接口不直接暴露扫描时间，后续可通过任务历史获取
                        }
                    )

                return result
        except Exception as e:
            logger.error(f"Failed to get Jellyfin libraries: {str(e)}")
            raise

    async def refresh_library(self, library_id: str = None) -> bool:
        """
        刷新 Jellyfin 媒体库

        Args:
            library_id: 媒体库ID，如果为None则刷新所有媒体库

        Returns:
            bool: 刷新操作是否成功触发
        """
        try:
            async with httpx.AsyncClient(**self.client_config) as client:
                if library_id:
                    # 刷新指定媒体库
                    endpoint = f"/Items/{library_id}/Refresh"
                else:
                    # 全局刷新
                    endpoint = "/Library/Refresh"

                response = await client.post(f"{self.base_url}{endpoint}", headers={"X-Emby-Token": self.api_key})
                return response.status_code in [200, 204]
        except Exception as e:
            logger.error(f"Failed to refresh Jellyfin library: {str(e)}")
            return False

    async def get_users(self) -> List[Dict[str, Any]]:
        """
        获取 Jellyfin 用户列表

        Returns:
            List[Dict]: 标准化的用户列表
        """
        try:
            async with httpx.AsyncClient(**self.client_config) as client:
                response = await client.get(
                    f"{self.base_url}/Users", headers={"X-Emby-Token": self.api_key}
                )
                response.raise_for_status()
                users = response.json()

                result = []
                for user in users:
                    result.append(
                        {
                            "id": user.get("Id"),
                            "name": user.get("Name"),
                            "is_admin": user.get("Policy", {}).get("IsAdministrator", False),
                        }
                    )
                return result
        except Exception as e:
            logger.error(f"Failed to get Jellyfin users: {str(e)}")
            raise

    async def get_watch_history(self, user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取用户观看历史

        Args:
            user_id: Jellyfin 用户ID
            limit: 返回记录数量限制

        Returns:
            List[Dict]: 观看历史列表（包含 Jellyfin 原始数据）
        """
        try:
            async with httpx.AsyncClient(**self.client_config) as client:
                response = await client.get(
                    f"{self.base_url}/Users/{user_id}/Items",
                    headers={"X-Emby-Token": self.api_key},
                    params={
                        "Recursive": "true",
                        "Fields": "PlayCount,UserData,Overview,Path,ProviderIds,ProductionYear,SeriesName,ParentIndexNumber,IndexNumber,ParentId,AncestorIds",
                        "Limit": limit,
                        "SortBy": "DatePlayed",
                        "SortOrder": "Descending",
                        "IncludeItemTypes": "Movie,Episode",
                    },
                )
                response.raise_for_status()
                data = response.json()
                return data.get("Items", [])
        except Exception as e:
            logger.error(f"Failed to get watch history: {str(e)}")
            raise

    async def get_library_stats(self) -> Dict[str, Any]:
        """
        获取媒体库统计信息

        Returns:
            Dict: 统计信息（Jellyfin 原始格式）
        """
        try:
            async with httpx.AsyncClient(**self.client_config) as client:
                response = await client.get(
                    f"{self.base_url}/Items/Counts", headers={"X-Emby-Token": self.api_key}
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to get library stats: {str(e)}")
            raise

    async def get_system_info(self) -> Dict[str, Any]:
        """
        获取系统信息

        Returns:
            Dict: 系统信息
        """
        try:
            async with httpx.AsyncClient(**self.client_config) as client:
                response = await client.get(
                    f"{self.base_url}/System/Info", headers={"X-Emby-Token": self.api_key}
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to get system info: {str(e)}")
            raise

    async def get_sessions(self) -> List[Dict[str, Any]]:
        """
        获取活动会话

        Returns:
            List[Dict]: 会话列表
        """
        try:
            async with httpx.AsyncClient(**self.client_config) as client:
                response = await client.get(
                    f"{self.base_url}/Sessions", headers={"X-Emby-Token": self.api_key}
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to get sessions: {str(e)}")
            raise

    async def get_latest_media(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        获取最近添加的媒体

        Args:
            limit: 返回数量限制

        Returns:
            List[Dict]: 媒体列表（精简字段）
        """
        try:
            user_id = await self._get_user_id()

            async with httpx.AsyncClient(**self.client_config) as client:
                response = await client.get(
                    f"{self.base_url}/Users/{user_id}/Items/Latest",
                    headers={"X-Emby-Token": self.api_key},
                    params={
                        "Limit": limit,
                        "IncludeItemTypes": "Movie,Episode",
                        # 只请求必要字段，减少响应体积
                        "Fields": "DateCreated,ProductionYear,PrimaryImageAspectRatio"
                    }
                )
                response.raise_for_status()
                return self._normalize_latest_items(response.json())
        except Exception as e:
            logger.error(f"Failed to get latest media: {str(e)}")
            raise

    async def get_item(self, item_id: str) -> Dict[str, Any]:
        """
        获取项目详情

        Args:
            item_id: 项目ID

        Returns:
            Dict: 项目详情
        """
        try:
            user_id = await self._get_user_id()

            async with httpx.AsyncClient(**self.client_config) as client:
                url = f"{self.base_url}/Users/{user_id}/Items/{item_id}"
                response = await client.get(
                    url, headers={"X-Emby-Token": self.api_key}
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to get item details for {item_id}: {str(e)}")
            raise

    async def search(self, query: str) -> List[Dict[str, Any]]:
        """
        搜索媒体

        Args:
            query: 搜索关键词

        Returns:
            List[Dict]: 搜索结果列表
        """
        try:
            user_id = await self._get_user_id()

            async with httpx.AsyncClient(**self.client_config) as client:
                response = await client.get(
                    f"{self.base_url}/Users/{user_id}/Items",
                    headers={"X-Emby-Token": self.api_key},
                    params={
                        "SearchTerm": query,
                        "Recursive": "true",
                        "IncludeItemTypes": "Movie,Series,Episode",
                        "Limit": 20
                    }
                )
                response.raise_for_status()
                data = response.json()
                return data.get("Items", [])
        except Exception as e:
            logger.error(f"Failed to search media: {str(e)}")
            raise

    @staticmethod
    def _normalize_latest_items(items: List[Dict]) -> List[Dict]:
        """
        标准化最新媒体项，只保留前端需要的字段

        Args:
            items: Jellyfin 原始媒体项列表

        Returns:
            List[Dict]: 精简后的媒体项列表
        """
        normalized = []
        for item in items:
            normalized.append({
                "Id": item.get("Id"),
                "Name": item.get("Name"),
                "Type": item.get("Type"),
                "ProductionYear": item.get("ProductionYear"),
                "DateCreated": item.get("DateCreated"),
                "PrimaryImageAspectRatio": item.get("PrimaryImageAspectRatio"),
                "ImageTags": item.get("ImageTags", {}),
                "SeriesName": item.get("SeriesName"),
                "ParentIndexNumber": item.get("ParentIndexNumber"),
                "IndexNumber": item.get("IndexNumber"),
            })
        return normalized

    @staticmethod
    def _map_collection_type(collection_type: str) -> str:
        """
        将 Jellyfin 的 CollectionType 映射到标准媒体类型

        Args:
            collection_type: Jellyfin 的 CollectionType

        Returns:
            str: 标准媒体类型（movies/tvshows/music/books）
        """
        type_mapping = {
            "movies": "movies",
            "tvshows": "tvshows",
            "music": "music",
            "books": "books",
            "homevideos": "other",
            "musicvideos": "music",
            "photos": "other",
        }
        return type_mapping.get(collection_type.lower(), "unknown")

