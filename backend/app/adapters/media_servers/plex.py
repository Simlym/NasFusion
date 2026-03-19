# -*- coding: utf-8 -*-
"""
Plex 适配器
"""
import httpx
import logging
from typing import Dict, Any, List, Optional
from app.adapters.media_servers.base import BaseMediaServerAdapter

logger = logging.getLogger(__name__)

class PlexAdapter(BaseMediaServerAdapter):
    """Plex 适配器"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.config = config
        # Plex 使用 'token' 而不是 'api_key'，但在 base connfig 中我们可能混用
        self.token = config.get("token") or config.get("api_key", "")
        
        protocol = "https" if self.use_ssl else "http"
        self.base_url = f"{protocol}://{self.host}:{self.port}"
        
        self.client_config = {
            "timeout": httpx.Timeout(30.0),
            "follow_redirects": True,
            "headers": {
                "X-Plex-Token": self.token,
                "Accept": "application/json"
            }
        }

    async def test_connection(self) -> bool:
        try:
            async with httpx.AsyncClient(**self.client_config) as client:
                response = await client.get(f"{self.base_url}/identity")
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Plex connection test failed: {str(e)}")
            return False

    async def get_system_info(self) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(**self.client_config) as client:
                response = await client.get(f"{self.base_url}/identity")
                response.raise_for_status()
                data = response.json()
                # 包装为统一格式
                container = data.get("MediaContainer", {})
                return {
                    "ServerName": container.get("machineIdentifier", "Unknown"), # Plex identity usage
                    "Version": container.get("version", ""),
                    "Id": container.get("machineIdentifier", ""),
                    "OperatingSystem": "Unknown" # Plex identity endpoint usually minimal
                }
        except Exception as e:
            logger.error(f"Failed to get Plex system info: {str(e)}")
            raise

    async def get_libraries(self) -> List[Dict[str, Any]]:
        try:
            async with httpx.AsyncClient(**self.client_config) as client:
                response = await client.get(f"{self.base_url}/library/sections")
                response.raise_for_status()
                data = response.json()
                
                result = []
                # 获取系统信息以便构造跳转链接
                server_id = ""
                try:
                    sys_info = await self.get_system_info()
                    server_id = sys_info.get("Id", "")
                except Exception:
                    pass

                from datetime import datetime, timezone
                for lib in data.get("MediaContainer", {}).get("Directory", []):
                    updated_at = lib.get("updatedAt")
                    last_scan_at = None
                    if updated_at:
                        last_scan_at = datetime.fromtimestamp(int(updated_at), tz=timezone.utc).isoformat()

                    result.append({
                        "id": lib.get("key"),
                        "name": lib.get("title"),
                        "type": lib.get("type"), # movie, show, artist
                        "locations": [loc.get("path") for loc in lib.get("Location", [])],
                        "image_url": f"/library/metadata/{lib.get('ratingKey')}/thumb" if lib.get('ratingKey') else None,
                        "web_url": f"https://app.plex.tv/desktop/#!/server/{server_id}/section/{lib.get('key')}" if server_id else f"{self.base_url}/web/index.html#!/server/{server_id}/section/{lib.get('key')}",
                        "item_count": lib.get("size", 0),
                        "last_scan_at": last_scan_at
                    })
                return result
        except Exception as e:
            logger.error(f"Failed to get Plex libraries: {str(e)}")
            raise

    async def refresh_library(self, library_id: str = None) -> bool:
        try:
            async with httpx.AsyncClient(**self.client_config) as client:
                path = f"/library/sections/{library_id}/refresh" if library_id else "/library/sections/all/refresh"
                response = await client.get(f"{self.base_url}{path}")
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to refresh Plex library: {str(e)}")
            return False

    async def get_users(self) -> List[Dict[str, Any]]:
        # Plex 本地 API 不直接提供简单的用户列表，通常通过 plex.tv 
        # 这里仅返回基本信息或需改进
        return []

    async def get_sessions(self) -> List[Dict[str, Any]]:
        try:
            async with httpx.AsyncClient(**self.client_config) as client:
                response = await client.get(f"{self.base_url}/status/sessions")
                response.raise_for_status()
                data = response.json()
                
                sessions = []
                for session in data.get("MediaContainer", {}).get("Metadata", []):
                    user = session.get("User", {})
                    sessions.append({
                        "Id": session.get("sessionKey"),
                        "UserName": user.get("title"),
                        "ItemName": session.get("title"),
                        "Type": session.get("type"),
                        "NowPlayingItem": session # 包含完整信息以便前端解析
                    })
                return sessions
        except Exception as e:
            logger.error(f"Failed to get Plex sessions: {str(e)}")
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
            async with httpx.AsyncClient(**self.client_config) as client:
                response = await client.get(
                    f"{self.base_url}/library/recentlyAdded",
                    params={"X-Plex-Container-Start": 0, "X-Plex-Container-Size": limit}
                )
                response.raise_for_status()
                data = response.json()
                items = data.get("MediaContainer", {}).get("Metadata", [])
                return self._normalize_latest_items(items)
        except Exception as e:
            logger.error(f"Failed to get Plex latest media: {str(e)}")
            raise

    async def get_item(self, item_id: str) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(**self.client_config) as client:
                response = await client.get(f"{self.base_url}/library/metadata/{item_id}")
                response.raise_for_status()
                data = response.json()
                metadata = data.get("MediaContainer", {}).get("Metadata", [])
                return metadata[0] if metadata else {}
        except Exception as e:
            logger.error(f"Failed to get Plex item {item_id}: {str(e)}")
            raise

    async def search(self, query: str) -> List[Dict[str, Any]]:
        try:
            async with httpx.AsyncClient(**self.client_config) as client:
                response = await client.get(
                    f"{self.base_url}/search",
                    params={"query": query, "limit": 20}
                )
                response.raise_for_status()
                data = response.json()
                return data.get("MediaContainer", {}).get("Metadata", [])
        except Exception as e:
            logger.error(f"Failed to search Plex: {str(e)}")
            raise

    async def get_watch_history(self, user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        # Plex 本地 API 对于非 Tautulli 场景较难获取精确历史
        return []

    async def get_library_stats(self) -> Dict[str, Any]:
         try:
            async with httpx.AsyncClient(**self.client_config) as client:
                response = await client.get(f"{self.base_url}/library/sections")
                # 简单计数逻辑需遍历所有库，此处简化返回
                return {}
         except Exception:
             return {}

    @staticmethod
    def _normalize_latest_items(items: List[Dict]) -> List[Dict]:
        """
        标准化 Plex 媒体项，只保留前端需要的字段

        Args:
            items: Plex 原始媒体项列表

        Returns:
            List[Dict]: 精简后的媒体项列表
        """
        normalized = []
        for item in items:
            normalized.append({
                "Id": item.get("ratingKey"),
                "Name": item.get("title"),
                "Type": item.get("type"),
                "ProductionYear": item.get("year"),
                "DateCreated": item.get("addedAt"),
                "thumb": item.get("thumb"),
                "art": item.get("art"),
                "grandparentTitle": item.get("grandparentTitle"),
                "parentTitle": item.get("parentTitle"),
                "index": item.get("index"),
                "parentIndex": item.get("parentIndex"),
            })
        return normalized
