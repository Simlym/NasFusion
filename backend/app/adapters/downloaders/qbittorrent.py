# -*- coding: utf-8 -*-
"""
qBittorrent下载器适配器

基于 qBittorrent Web API v2
文档: https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-(qBittorrent-4.1)
"""
import logging
from typing import Any, Dict, List, Optional

import httpx

from app.adapters.downloaders.base import BaseDownloaderAdapter

logger = logging.getLogger(__name__)


class QBittorrentAdapter(BaseDownloaderAdapter):
    """qBittorrent适配器"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化qBittorrent适配器

        Args:
            config: 下载器配置
        """
        super().__init__(config)
        self._cookies: Optional[Dict[str, str]] = None
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """获取HTTP客户端（复用连接）"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0),
                follow_redirects=True,
            )
        return self._client

    async def close(self):
        """关闭HTTP客户端"""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _login(self) -> bool:
        """
        登录qBittorrent

        Returns:
            bool: 是否登录成功
        """
        try:
            client = await self._get_client()
            url = f"{self.base_url}/api/v2/auth/login"

            response = await client.post(
                url,
                data={
                    "username": self.username,
                    "password": self.password,
                },
            )

            if response.status_code == 200 and response.text == "Ok.":
                # 保存cookie
                self._cookies = dict(response.cookies)
                logger.info(f"Successfully logged in to qBittorrent at {self.base_url}")
                return True
            else:
                logger.error(f"Failed to login to qBittorrent: {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error logging in to qBittorrent: {str(e)}")
            return False

    async def _ensure_logged_in(self):
        """确保已登录"""
        if not self._cookies:
            await self._login()

    async def test_connection(self) -> bool:
        """
        测试连接

        Returns:
            bool: 连接是否成功
        """
        try:
            # 尝试登录
            if not await self._login():
                return False

            # 获取qBittorrent版本信息验证连接
            client = await self._get_client()
            url = f"{self.base_url}/api/v2/app/version"
            response = await client.get(url, cookies=self._cookies)

            if response.status_code == 200:
                version = response.text
                logger.info(f"qBittorrent version: {version}")
                return True
            else:
                logger.error(f"Failed to get qBittorrent version: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error testing qBittorrent connection: {str(e)}")
            return False

    async def add_torrent_file(
        self,
        torrent_data: bytes,
        save_path: str,
        **options,
    ) -> Dict[str, Any]:
        """
        添加种子文件

        Args:
            torrent_data: 种子文件字节流
            save_path: 保存路径
            **options: 其他选项，支持：
                - category: 分类
                - tags: 标签（逗号分隔）
                - paused: 是否暂停添加
                - ratio_limit: 分享率限制
                - seeding_time_limit: 做种时长限制（分钟）

        Returns:
            Dict: 包含任务信息的字典
        """
        try:
            await self._ensure_logged_in()

            client = await self._get_client()
            url = f"{self.base_url}/api/v2/torrents/add"

            # 准备表单数据
            data = {
                "savepath": save_path,
            }

            # 添加可选参数
            if "category" in options:
                data["category"] = options["category"]
            if "tags" in options:
                data["tags"] = options["tags"]
            if "paused" in options:
                data["paused"] = "true" if options["paused"] else "false"

            # 设置分享限制
            if "ratio_limit" in options:
                data["ratioLimit"] = str(options["ratio_limit"])
            if "seeding_time_limit" in options:
                data["seedingTimeLimit"] = str(options["seeding_time_limit"])

            # 上传种子文件
            files = {"torrents": ("torrent.torrent", torrent_data, "application/x-bittorrent")}

            response = await client.post(
                url,
                data=data,
                files=files,
                cookies=self._cookies,
            )

            if response.status_code == 200 and response.text == "Ok.":
                logger.info(f"Successfully added torrent to qBittorrent")
                # qBittorrent 不会立即返回hash，需要从种子数据解析
                # 这里返回成功标识，实际hash会在后续同步中获取
                return {
                    "success": True,
                    "message": "Torrent added successfully",
                }
            else:
                error_msg = response.text
                logger.error(f"Failed to add torrent: {error_msg}")
                raise Exception(f"Failed to add torrent: {error_msg}")

        except Exception as e:
            logger.error(f"Error adding torrent file to qBittorrent: {str(e)}")
            raise

    async def add_torrent_magnet(
        self,
        magnet_link: str,
        save_path: str,
        **options,
    ) -> Dict[str, Any]:
        """
        添加磁力链接

        Args:
            magnet_link: 磁力链接
            save_path: 保存路径
            **options: 其他选项

        Returns:
            Dict: 包含任务信息的字典
        """
        try:
            await self._ensure_logged_in()

            client = await self._get_client()
            url = f"{self.base_url}/api/v2/torrents/add"

            # 准备表单数据
            data = {
                "urls": magnet_link,
                "savepath": save_path,
            }

            # 添加可选参数
            if "category" in options:
                data["category"] = options["category"]
            if "tags" in options:
                data["tags"] = options["tags"]
            if "paused" in options:
                data["paused"] = "true" if options["paused"] else "false"

            # 设置分享限制
            if "ratio_limit" in options:
                data["ratioLimit"] = str(options["ratio_limit"])
            if "seeding_time_limit" in options:
                data["seedingTimeLimit"] = str(options["seeding_time_limit"])

            response = await client.post(
                url,
                data=data,
                cookies=self._cookies,
            )

            if response.status_code == 200 and response.text == "Ok.":
                logger.info(f"Successfully added magnet link to qBittorrent")
                return {
                    "success": True,
                    "message": "Magnet link added successfully",
                }
            else:
                error_msg = response.text
                logger.error(f"Failed to add magnet link: {error_msg}")
                raise Exception(f"Failed to add magnet link: {error_msg}")

        except Exception as e:
            logger.error(f"Error adding magnet link to qBittorrent: {str(e)}")
            raise

    def _normalize_torrent_state(self, qb_state: str) -> str:
        """
        将qBittorrent状态映射到统一状态

        qBittorrent状态：
        - downloading: 下载中
        - pausedDL: 暂停下载
        - stalledDL: 下载停滞
        - metaDL: 获取元数据中
        - uploading: 做种中
        - pausedUP: 暂停做种
        - stalledUP: 做种停滞
        - checkingDL: 检查中
        - checkingUP: 检查中
        - queuedDL: 排队下载
        - queuedUP: 排队做种
        - error: 错误
        - missingFiles: 文件缺失
        - allocating: 分配空间中

        Returns:
            str: 统一状态
        """
        state_map = {
            "downloading": "downloading",
            "pausedDL": "paused",
            "stalledDL": "downloading",
            "metaDL": "downloading",
            "uploading": "seeding",
            "pausedUP": "paused",
            "stalledUP": "seeding",
            "checkingDL": "downloading",
            "checkingUP": "seeding",
            "queuedDL": "pending",
            "queuedUP": "seeding",  # 已下载完成，排队等待做种
            "error": "error",
            "missingFiles": "error",
            "allocating": "downloading",
        }
        return state_map.get(qb_state, "error")

    async def get_torrent_info(self, task_hash: str) -> Dict[str, Any]:
        """
        获取种子信息

        Args:
            task_hash: 种子hash

        Returns:
            Dict: 种子详细信息
        """
        try:
            results = await self.get_torrents_info([task_hash])
            if results:
                return results[0]
            else:
                raise Exception(f"Torrent with hash {task_hash} not found")
        except Exception as e:
            logger.error(f"Error getting torrent info from qBittorrent: {str(e)}")
            raise

    async def get_torrents_info(self, task_hashes: List[str]) -> List[Dict[str, Any]]:
        """
        批量获取种子信息

        Args:
            task_hashes: 种子hash列表

        Returns:
            List[Dict]: 种子详细信息列表
        """
        try:
            await self._ensure_logged_in()

            client = await self._get_client()
            url = f"{self.base_url}/api/v2/torrents/info"

            # qBittorrent 支持使用 | 分隔多个 hash
            hashes_str = "|".join(task_hashes)

            response = await client.get(
                url,
                params={"hashes": hashes_str},
                cookies=self._cookies,
            )

            if response.status_code == 200:
                torrents = response.json()
                result_list = []
                for torrent in torrents:
                    # 转换为统一格式
                    result_list.append({
                        "hash": torrent["hash"],
                        "name": torrent["name"],
                        "state": self._normalize_torrent_state(torrent["state"]),
                        "progress": torrent["progress"],  # 0-1
                        "downloaded": torrent["downloaded"],
                        "uploaded": torrent["uploaded"],
                        "total_size": torrent["size"],
                        "download_speed": torrent["dlspeed"],
                        "upload_speed": torrent["upspeed"],
                        "ratio": torrent["ratio"],
                        "eta": torrent["eta"] if torrent["eta"] != 8640000 else None,
                        "save_path": torrent["save_path"],
                        "completion_date": torrent.get("completion_on"),
                        "added_on": torrent.get("added_on"),
                        "raw_data": torrent,
                    })
                return result_list
            else:
                raise Exception(f"Failed to get torrents info: {response.status_code}")

        except Exception as e:
            logger.error(f"Error getting torrents info from qBittorrent: {str(e)}")
            raise

    async def get_torrent_list(self, **filters) -> List[Dict[str, Any]]:
        """
        获取种子列表

        Args:
            **filters: 过滤条件，支持：
                - category: 分类
                - tag: 标签
                - filter: 状态过滤（all/downloading/seeding/completed/paused/active/inactive）

        Returns:
            List[Dict]: 种子信息列表
        """
        try:
            await self._ensure_logged_in()

            client = await self._get_client()
            url = f"{self.base_url}/api/v2/torrents/info"

            params = {}
            if "category" in filters:
                params["category"] = filters["category"]
            if "tag" in filters:
                params["tag"] = filters["tag"]
            if "filter" in filters:
                params["filter"] = filters["filter"]

            response = await client.get(
                url,
                params=params,
                cookies=self._cookies,
            )

            if response.status_code == 200:
                torrents = response.json()
                # 转换为统一格式
                result = []
                for torrent in torrents:
                    result.append({
                        "hash": torrent["hash"],
                        "name": torrent["name"],
                        "state": self._normalize_torrent_state(torrent["state"]),
                        "progress": torrent["progress"],
                        "downloaded": torrent["downloaded"],
                        "uploaded": torrent["uploaded"],
                        "total_size": torrent["size"],
                        "download_speed": torrent["dlspeed"],
                        "upload_speed": torrent["upspeed"],
                        "ratio": torrent["ratio"],
                        "eta": torrent["eta"] if torrent["eta"] != 8640000 else None,
                        "save_path": torrent["save_path"],
                    })
                return result
            else:
                raise Exception(f"Failed to get torrent list: {response.status_code}")

        except Exception as e:
            logger.error(f"Error getting torrent list from qBittorrent: {str(e)}")
            raise

    async def pause_torrent(self, task_hash: str) -> bool:
        """
        暂停种子

        Args:
            task_hash: 种子hash

        Returns:
            bool: 是否成功
        """
        try:
            await self._ensure_logged_in()

            client = await self._get_client()
            url = f"{self.base_url}/api/v2/torrents/pause"

            response = await client.post(
                url,
                data={"hashes": task_hash},
                cookies=self._cookies,
            )

            if response.status_code == 200:
                logger.info(f"Successfully paused torrent {task_hash}")
                return True
            else:
                logger.error(f"Failed to pause torrent: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error pausing torrent in qBittorrent: {str(e)}")
            return False

    async def resume_torrent(self, task_hash: str) -> bool:
        """
        恢复种子

        Args:
            task_hash: 种子hash

        Returns:
            bool: 是否成功
        """
        try:
            await self._ensure_logged_in()

            client = await self._get_client()
            url = f"{self.base_url}/api/v2/torrents/resume"

            response = await client.post(
                url,
                data={"hashes": task_hash},
                cookies=self._cookies,
            )

            if response.status_code == 200:
                logger.info(f"Successfully resumed torrent {task_hash}")
                return True
            else:
                logger.error(f"Failed to resume torrent: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error resuming torrent in qBittorrent: {str(e)}")
            return False

    async def delete_torrent(self, task_hash: str, delete_files: bool = False) -> bool:
        """
        删除种子

        Args:
            task_hash: 种子hash
            delete_files: 是否同时删除文件

        Returns:
            bool: 是否成功
        """
        try:
            await self._ensure_logged_in()

            client = await self._get_client()
            url = f"{self.base_url}/api/v2/torrents/delete"

            response = await client.post(
                url,
                data={
                    "hashes": task_hash,
                    "deleteFiles": "true" if delete_files else "false",
                },
                cookies=self._cookies,
            )

            if response.status_code == 200:
                logger.info(f"Successfully deleted torrent {task_hash}, delete_files={delete_files}")
                return True
            else:
                logger.error(f"Failed to delete torrent: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error deleting torrent in qBittorrent: {str(e)}")
            return False

    async def set_torrent_limits(
        self,
        task_hash: str,
        ratio_limit: Optional[float] = None,
        seeding_time_limit: Optional[int] = None,
    ) -> bool:
        """
        设置种子做种限制

        Args:
            task_hash: 种子hash
            ratio_limit: 分享率限制（-2=全局，-1=无限制）
            seeding_time_limit: 做种时长限制（分钟，-2=全局，-1=无限制）

        Returns:
            bool: 是否成功
        """
        try:
            await self._ensure_logged_in()

            client = await self._get_client()
            url = f"{self.base_url}/api/v2/torrents/setShareLimits"

            data = {"hashes": task_hash}

            if ratio_limit is not None:
                data["ratioLimit"] = str(ratio_limit)
            if seeding_time_limit is not None:
                data["seedingTimeLimit"] = str(seeding_time_limit)

            response = await client.post(
                url,
                data=data,
                cookies=self._cookies,
            )

            if response.status_code == 200:
                logger.info(f"Successfully set share limits for torrent {task_hash}")
                return True
            else:
                logger.error(f"Failed to set share limits: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error setting torrent limits in qBittorrent: {str(e)}")
            return False
