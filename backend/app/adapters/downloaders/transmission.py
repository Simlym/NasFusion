# -*- coding: utf-8 -*-
"""
Transmission下载器适配器

基于 Transmission RPC API
文档: https://github.com/transmission/transmission/blob/main/docs/rpc-spec.md
"""
import base64
import logging
from typing import Any, Dict, List, Optional

import httpx

from app.adapters.downloaders.base import BaseDownloaderAdapter

logger = logging.getLogger(__name__)


class TransmissionAdapter(BaseDownloaderAdapter):
    """Transmission适配器"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化Transmission适配器

        Args:
            config: 下载器配置
        """
        super().__init__(config)
        self._session_id: Optional[str] = None
        self._client: Optional[httpx.AsyncClient] = None
        # Transmission 默认端口是 9091
        if self.port == 8080:  # 如果是基类默认值，改为 Transmission 默认值
            self.port = 9091
        # Transmission RPC 路径
        self.rpc_path = config.get("rpc_path", "/transmission/rpc")

    async def _get_client(self) -> httpx.AsyncClient:
        """获取HTTP客户端（复用连接）"""
        if self._client is None:
            # 准备认证头
            auth_header = None
            if self.username and self.password:
                credentials = f"{self.username}:{self.password}"
                auth_header = base64.b64encode(credentials.encode()).decode()

            headers = {}
            if auth_header:
                headers["Authorization"] = f"Basic {auth_header}"

            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0),
                follow_redirects=True,
                headers=headers,
            )
        return self._client

    async def close(self):
        """关闭HTTP客户端"""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _call_rpc(self, method: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        调用Transmission RPC方法

        Args:
            method: RPC方法名
            arguments: 方法参数

        Returns:
            RPC响应结果
        """
        try:
            client = await self._get_client()
            url = f"{self.base_url}{self.rpc_path}"

            # 准备请求体
            payload = {
                "method": method,
            }
            if arguments:
                payload["arguments"] = arguments

            # 添加Session ID（如果有）
            headers = {}
            if self._session_id:
                headers["X-Transmission-Session-Id"] = self._session_id

            # 发送请求
            response = await client.post(url, json=payload, headers=headers)

            # 处理 409 Conflict（需要更新 Session ID）
            if response.status_code == 409:
                # 从响应头获取新的 Session ID
                self._session_id = response.headers.get("X-Transmission-Session-Id")
                if self._session_id:
                    logger.debug("Updated Transmission Session ID")
                    # 重试请求
                    headers["X-Transmission-Session-Id"] = self._session_id
                    response = await client.post(url, json=payload, headers=headers)
                else:
                    raise Exception("Failed to get Transmission Session ID")

            # 检查响应
            if response.status_code == 200:
                result = response.json()
                if result.get("result") == "success":
                    return result.get("arguments", {})
                else:
                    error_msg = result.get("result", "Unknown error")
                    raise Exception(f"Transmission RPC error: {error_msg}")
            else:
                raise Exception(f"Transmission RPC failed with status {response.status_code}: {response.text}")

        except Exception as e:
            logger.error(f"Error calling Transmission RPC: {str(e)}")
            raise

    async def test_connection(self) -> bool:
        """
        测试连接

        Returns:
            bool: 连接是否成功
        """
        try:
            # 调用 session-get 方法测试连接
            result = await self._call_rpc("session-get")
            if result:
                version = result.get("version", "unknown")
                logger.info(f"Transmission version: {version}")
                return True
            return False

        except Exception as e:
            logger.error(f"Error testing Transmission connection: {str(e)}")
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
                - paused: 是否暂停添加
                - labels: 标签列表

        Returns:
            Dict: 包含任务信息的字典
        """
        try:
            # 将种子文件转换为base64
            metainfo = base64.b64encode(torrent_data).decode()

            # 准备参数
            arguments = {
                "metainfo": metainfo,
                "download-dir": save_path,
            }

            # 添加可选参数
            if "paused" in options:
                arguments["paused"] = bool(options["paused"])

            if "labels" in options:
                arguments["labels"] = options["labels"]

            # 调用RPC
            result = await self._call_rpc("torrent-add", arguments)

            # Transmission 返回两种情况：
            # 1. torrent-added: 成功添加新种子
            # 2. torrent-duplicate: 种子已存在
            if "torrent-added" in result:
                torrent = result["torrent-added"]
                logger.info(f"Successfully added torrent to Transmission: {torrent.get('name')}")
                return {
                    "hash": torrent.get("hashString"),
                    "name": torrent.get("name"),
                    "id": torrent.get("id"),
                    "success": True,
                }
            elif "torrent-duplicate" in result:
                torrent = result["torrent-duplicate"]
                logger.info(f"Torrent already exists in Transmission: {torrent.get('name')}")
                return {
                    "hash": torrent.get("hashString"),
                    "name": torrent.get("name"),
                    "id": torrent.get("id"),
                    "success": True,
                    "duplicate": True,
                }
            else:
                raise Exception("Unexpected response from Transmission")

        except Exception as e:
            logger.error(f"Error adding torrent file to Transmission: {str(e)}")
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
            # 准备参数
            arguments = {
                "filename": magnet_link,
                "download-dir": save_path,
            }

            # 添加可选参数
            if "paused" in options:
                arguments["paused"] = bool(options["paused"])

            if "labels" in options:
                arguments["labels"] = options["labels"]

            # 调用RPC
            result = await self._call_rpc("torrent-add", arguments)

            # 处理响应
            if "torrent-added" in result:
                torrent = result["torrent-added"]
                logger.info(f"Successfully added magnet link to Transmission: {torrent.get('name', 'unknown')}")
                return {
                    "hash": torrent.get("hashString"),
                    "name": torrent.get("name", ""),
                    "id": torrent.get("id"),
                    "success": True,
                }
            elif "torrent-duplicate" in result:
                torrent = result["torrent-duplicate"]
                logger.info(f"Magnet link already exists in Transmission: {torrent.get('name', 'unknown')}")
                return {
                    "hash": torrent.get("hashString"),
                    "name": torrent.get("name", ""),
                    "id": torrent.get("id"),
                    "success": True,
                    "duplicate": True,
                }
            else:
                raise Exception("Unexpected response from Transmission")

        except Exception as e:
            logger.error(f"Error adding magnet link to Transmission: {str(e)}")
            raise

    def _normalize_torrent_state(self, status: int) -> str:
        """
        将Transmission状态映射到统一状态

        Transmission状态码：
        - 0: 已停止 (TR_STATUS_STOPPED)
        - 1: 队列中等待校验 (TR_STATUS_CHECK_WAIT)
        - 2: 校验中 (TR_STATUS_CHECK)
        - 3: 队列中等待下载 (TR_STATUS_DOWNLOAD_WAIT)
        - 4: 下载中 (TR_STATUS_DOWNLOAD)
        - 5: 队列中等待做种 (TR_STATUS_SEED_WAIT)
        - 6: 做种中 (TR_STATUS_SEED)

        Returns:
            str: 统一状态
        """
        state_map = {
            0: "paused",  # 已停止
            1: "pending",  # 等待校验
            2: "downloading",  # 校验中
            3: "pending",  # 等待下载
            4: "downloading",  # 下载中
            5: "pending",  # 等待做种
            6: "seeding",  # 做种中
        }
        return state_map.get(status, "error")

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
            logger.error(f"Error getting torrent info from Transmission: {str(e)}")
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
            # 准备要获取的字段
            fields = [
                "id",
                "hashString",
                "name",
                "status",
                "percentDone",
                "downloadedEver",
                "uploadedEver",
                "totalSize",
                "rateDownload",
                "rateUpload",
                "uploadRatio",
                "eta",
                "downloadDir",
                "doneDate",
                "addedDate",
                "error",
                "errorString",
                "labels",
            ]

            # 调用RPC
            result = await self._call_rpc(
                "torrent-get",
                {
                    "fields": fields,
                    "ids": task_hashes,
                }
            )

            torrents = result.get("torrents", [])
            result_list = []
            for torrent in torrents:
                # 转换为统一格式
                result_list.append({
                    "hash": torrent.get("hashString"),
                    "name": torrent.get("name"),
                    "state": self._normalize_torrent_state(torrent.get("status", 0)),
                    "progress": torrent.get("percentDone", 0),  # 0-1
                    "downloaded": torrent.get("downloadedEver", 0),
                    "uploaded": torrent.get("uploadedEver", 0),
                    "total_size": torrent.get("totalSize", 0),
                    "download_speed": torrent.get("rateDownload", 0),
                    "upload_speed": torrent.get("rateUpload", 0),
                    "ratio": torrent.get("uploadRatio", 0),
                    "eta": torrent.get("eta", -1) if torrent.get("eta", -1) >= 0 else None,
                    "save_path": torrent.get("downloadDir"),
                    "completion_date": torrent.get("doneDate", 0) if torrent.get("doneDate", 0) > 0 else None,
                    "added_on": torrent.get("addedDate"),
                    "error": torrent.get("error", 0),
                    "error_string": torrent.get("errorString", ""),
                    "labels": torrent.get("labels", []),
                    "raw_data": torrent,
                })
            return result_list

        except Exception as e:
            logger.error(f"Error getting torrents info from Transmission: {str(e)}")
            raise

    async def get_torrent_list(self, **filters) -> List[Dict[str, Any]]:
        """
        获取种子列表

        Args:
            **filters: 过滤条件，支持：
                - labels: 标签列表

        Returns:
            List[Dict]: 种子信息列表
        """
        try:
            # 准备要获取的字段
            fields = [
                "id",
                "hashString",
                "name",
                "status",
                "percentDone",
                "downloadedEver",
                "uploadedEver",
                "totalSize",
                "rateDownload",
                "rateUpload",
                "uploadRatio",
                "eta",
                "downloadDir",
                "labels",
            ]

            # 调用RPC（不指定ids表示获取所有）
            result = await self._call_rpc(
                "torrent-get",
                {"fields": fields}
            )

            torrents = result.get("torrents", [])

            # 转换为统一格式
            result_list = []
            for torrent in torrents:
                # 应用标签过滤
                if "labels" in filters:
                    torrent_labels = torrent.get("labels", [])
                    filter_labels = filters["labels"]
                    if not any(label in torrent_labels for label in filter_labels):
                        continue

                result_list.append({
                    "hash": torrent.get("hashString"),
                    "name": torrent.get("name"),
                    "state": self._normalize_torrent_state(torrent.get("status", 0)),
                    "progress": torrent.get("percentDone", 0),
                    "downloaded": torrent.get("downloadedEver", 0),
                    "uploaded": torrent.get("uploadedEver", 0),
                    "total_size": torrent.get("totalSize", 0),
                    "download_speed": torrent.get("rateDownload", 0),
                    "upload_speed": torrent.get("rateUpload", 0),
                    "ratio": torrent.get("uploadRatio", 0),
                    "eta": torrent.get("eta", -1) if torrent.get("eta", -1) >= 0 else None,
                    "save_path": torrent.get("downloadDir"),
                    "labels": torrent.get("labels", []),
                })

            return result_list

        except Exception as e:
            logger.error(f"Error getting torrent list from Transmission: {str(e)}")
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
            await self._call_rpc(
                "torrent-stop",
                {"ids": [task_hash]}
            )
            logger.info(f"Successfully paused torrent {task_hash}")
            return True

        except Exception as e:
            logger.error(f"Error pausing torrent in Transmission: {str(e)}")
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
            await self._call_rpc(
                "torrent-start",
                {"ids": [task_hash]}
            )
            logger.info(f"Successfully resumed torrent {task_hash}")
            return True

        except Exception as e:
            logger.error(f"Error resuming torrent in Transmission: {str(e)}")
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
            await self._call_rpc(
                "torrent-remove",
                {
                    "ids": [task_hash],
                    "delete-local-data": delete_files,
                }
            )
            logger.info(f"Successfully deleted torrent {task_hash}, delete_files={delete_files}")
            return True

        except Exception as e:
            logger.error(f"Error deleting torrent in Transmission: {str(e)}")
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
            ratio_limit: 分享率限制
            seeding_time_limit: 做种时长限制（分钟）

        Returns:
            bool: 是否成功
        """
        try:
            arguments = {"ids": [task_hash]}

            if ratio_limit is not None:
                # Transmission 使用 seedRatioMode 和 seedRatioLimit
                # seedRatioMode: 0=全局设置, 1=单独设置, 2=无限制
                if ratio_limit < 0:
                    arguments["seedRatioMode"] = 0  # 使用全局设置
                else:
                    arguments["seedRatioMode"] = 1  # 单独设置
                    arguments["seedRatioLimit"] = ratio_limit

            if seeding_time_limit is not None:
                # Transmission 使用 seedIdleMode 和 seedIdleLimit（以分钟为单位）
                # seedIdleMode: 0=全局设置, 1=单独设置, 2=无限制
                if seeding_time_limit < 0:
                    arguments["seedIdleMode"] = 0  # 使用全局设置
                else:
                    arguments["seedIdleMode"] = 1  # 单独设置
                    arguments["seedIdleLimit"] = seeding_time_limit

            await self._call_rpc("torrent-set", arguments)
            logger.info(f"Successfully set share limits for torrent {task_hash}")
            return True

        except Exception as e:
            logger.error(f"Error setting torrent limits in Transmission: {str(e)}")
            return False
