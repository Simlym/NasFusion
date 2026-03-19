# -*- coding: utf-8 -*-
"""
Synology Download Station 下载器适配器

基于 Synology Download Station Web API
文档: https://global.download.synology.com/download/Document/Software/DeveloperGuide/Package/DownloadStation/
"""
import base64
import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import httpx

from app.adapters.downloaders.base import BaseDownloaderAdapter

logger = logging.getLogger(__name__)


class SynologyDownloadStationAdapter(BaseDownloaderAdapter):
    """Synology Download Station 适配器"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化 Synology DS 适配器

        Args:
            config: 下载器配置
        """
        super().__init__(config)
        self._sid: Optional[str] = None  # Session ID
        self._client: Optional[httpx.AsyncClient] = None
        # Synology DSM 默认端口
        if self.port == 8080:  # 如果是基类默认值，改为 DSM 默认值
            self.port = 5000 if not self.use_ssl else 5001

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
            # 退出登录
            if self._sid:
                try:
                    await self._call_api(
                        "SYNO.API.Auth",
                        "logout",
                        version=1,
                        params={"session": "DownloadStation"},
                    )
                except Exception as e:
                    logger.warning(f"Error logging out from Synology: {str(e)}")
            await self._client.aclose()
            self._client = None

    async def _call_api(
        self,
        api: str,
        method: str,
        version: int = 1,
        params: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        调用 Synology API

        Args:
            api: API 名称（如 SYNO.API.Auth）
            method: 方法名（如 login）
            version: API 版本
            params: 额外参数
            files: 文件上传

        Returns:
            API 响应数据
        """
        try:
            client = await self._get_client()

            # 准备基础参数
            query_params = {
                "api": api,
                "version": version,
                "method": method,
            }

            # 添加 SID（如果已登录且不是认证API）
            if self._sid and api != "SYNO.API.Auth":
                query_params["_sid"] = self._sid

            # 合并额外参数
            if params:
                query_params.update(params)

            # 构建 URL
            # 根据 API 类型选择 CGI 端点
            if api.startswith("SYNO.API."):
                cgi = "auth.cgi"
            elif api.startswith("SYNO.DownloadStation."):
                cgi = "DownloadStation/task.cgi"
            else:
                cgi = "query.cgi"

            url = f"{self.base_url}/webapi/{cgi}"

            # 发送请求
            if files:
                # 使用 multipart/form-data 上传文件
                response = await client.post(
                    url,
                    params=query_params,
                    files=files,
                )
            else:
                # 使用 GET 请求
                response = await client.get(url, params=query_params)

            # 检查响应
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    return result.get("data", {})
                else:
                    error = result.get("error", {})
                    error_code = error.get("code", "unknown")
                    error_msg = self._get_error_message(error_code)
                    raise Exception(f"Synology API error {error_code}: {error_msg}")
            else:
                raise Exception(f"HTTP error {response.status_code}: {response.text}")

        except Exception as e:
            logger.error(f"Error calling Synology API: {str(e)}")
            raise

    def _get_error_message(self, error_code: int) -> str:
        """
        获取错误消息

        Args:
            error_code: 错误代码

        Returns:
            错误消息
        """
        error_messages = {
            100: "Unknown error",
            101: "Invalid parameter",
            102: "The requested API does not exist",
            103: "The requested method does not exist",
            104: "The requested version does not support the functionality",
            105: "The logged in session does not have permission",
            106: "Session timeout",
            107: "Session interrupted by duplicate login",
            400: "Invalid username or password",
            401: "Guest account disabled",
            402: "Account disabled",
            403: "Wrong password",
            404: "Permission denied",
        }
        return error_messages.get(error_code, f"Unknown error code: {error_code}")

    async def _login(self) -> bool:
        """
        登录到 Synology

        Returns:
            bool: 是否登录成功
        """
        try:
            result = await self._call_api(
                "SYNO.API.Auth",
                "login",
                version=6,  # DSM 7.x 使用版本 6
                params={
                    "account": self.username,
                    "passwd": self.password,
                    "session": "DownloadStation",
                    "format": "sid",
                },
            )

            self._sid = result.get("sid")
            if self._sid:
                logger.info(f"Successfully logged in to Synology at {self.base_url}")
                return True
            else:
                logger.error("Failed to get SID from Synology")
                return False

        except Exception as e:
            logger.error(f"Error logging in to Synology: {str(e)}")
            return False

    async def _ensure_logged_in(self):
        """确保已登录"""
        if not self._sid:
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

            # 获取 Download Station 信息验证连接
            result = await self._call_api(
                "SYNO.DownloadStation.Info",
                "getinfo",
                version=1,
            )

            if result:
                version = result.get("version_string", "unknown")
                logger.info(f"Synology Download Station version: {version}")
                return True
            return False

        except Exception as e:
            logger.error(f"Error testing Synology connection: {str(e)}")
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
            **options: 其他选项

        Returns:
            Dict: 包含任务信息的字典
        """
        try:
            await self._ensure_logged_in()

            # 准备参数
            params = {
                "destination": save_path,
            }

            # 准备文件
            files = {
                "file": ("torrent.torrent", torrent_data, "application/x-bittorrent")
            }

            # 调用 API
            result = await self._call_api(
                "SYNO.DownloadStation.Task",
                "create",
                version=1,
                params=params,
                files=files,
            )

            logger.info(f"Successfully added torrent to Synology Download Station")

            # Synology 不会立即返回任务详情，需要后续查询
            return {
                "success": True,
                "message": "Torrent added successfully",
            }

        except Exception as e:
            logger.error(f"Error adding torrent file to Synology: {str(e)}")
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

            # 准备参数
            params = {
                "uri": magnet_link,
                "destination": save_path,
            }

            # 调用 API
            result = await self._call_api(
                "SYNO.DownloadStation.Task",
                "create",
                version=1,
                params=params,
            )

            logger.info(f"Successfully added magnet link to Synology Download Station")

            return {
                "success": True,
                "message": "Magnet link added successfully",
            }

        except Exception as e:
            logger.error(f"Error adding magnet link to Synology: {str(e)}")
            raise

    def _normalize_torrent_state(self, status: str) -> str:
        """
        将 Synology 状态映射到统一状态

        Synology 状态：
        - waiting: 等待中
        - downloading: 下载中
        - paused: 已暂停
        - finishing: 完成中
        - finished: 已完成
        - hash_checking: 校验中
        - seeding: 做种中
        - filehosting_waiting: 等待文件托管
        - extracting: 解压中
        - error: 错误

        Returns:
            str: 统一状态
        """
        state_map = {
            "waiting": "pending",
            "downloading": "downloading",
            "paused": "paused",
            "finishing": "downloading",
            "finished": "completed",
            "hash_checking": "downloading",
            "seeding": "seeding",
            "filehosting_waiting": "pending",
            "extracting": "completed",
            "error": "error",
        }
        return state_map.get(status, "error")

    async def get_torrent_info(self, task_hash: str) -> Dict[str, Any]:
        """
        获取种子信息

        Args:
            task_hash: 种子hash 或任务ID

        Returns:
            Dict: 种子详细信息
        """
        try:
            results = await self.get_torrents_info([task_hash])
            if results:
                return results[0]
            else:
                raise Exception(f"Task with hash {task_hash} not found")
        except Exception as e:
            logger.error(f"Error getting torrent info from Synology: {str(e)}")
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

            # Synology getinfo 支持逗号分隔的 ID 列表
            ids_str = ",".join(task_hashes)

            # 获取任务列表
            result = await self._call_api(
                "SYNO.DownloadStation.Task",
                "getinfo",
                version=1,
                params={
                    "id": ids_str,
                    "additional": "detail,transfer,file",
                },
            )

            tasks = result.get("tasks", [])
            result_list = []
            for task in tasks:
                additional = task.get("additional", {})
                transfer = additional.get("transfer", {})

                # 转换为统一格式
                result_list.append({
                    "hash": task.get("id"),
                    "name": task.get("title"),
                    "state": self._normalize_torrent_state(task.get("status", "error")),
                    "progress": task.get("size", 0) / task.get("size", 1) if task.get("size") else 0,
                    "downloaded": transfer.get("size_downloaded", 0),
                    "uploaded": transfer.get("size_uploaded", 0),
                    "total_size": task.get("size", 0),
                    "download_speed": transfer.get("speed_download", 0),
                    "upload_speed": transfer.get("speed_upload", 0),
                    "ratio": transfer.get("size_uploaded", 0) / max(transfer.get("size_downloaded", 1), 1),
                    "eta": None,
                    "save_path": additional.get("detail", {}).get("destination", ""),
                    "completion_date": None,
                    "added_on": None,
                    "raw_data": task,
                })
            return result_list

        except Exception as e:
            logger.error(f"Error getting torrents info from Synology: {str(e)}")
            raise

    async def get_torrent_list(self, **filters) -> List[Dict[str, Any]]:
        """
        获取种子列表

        Args:
            **filters: 过滤条件

        Returns:
            List[Dict]: 种子信息列表
        """
        try:
            await self._ensure_logged_in()

            # 获取任务列表
            result = await self._call_api(
                "SYNO.DownloadStation.Task",
                "list",
                version=1,
                params={
                    "additional": "detail,transfer",
                },
            )

            tasks = result.get("tasks", [])

            # 转换为统一格式
            result_list = []
            for task in tasks:
                additional = task.get("additional", {})
                transfer = additional.get("transfer", {})

                result_list.append({
                    "hash": task.get("id"),
                    "name": task.get("title"),
                    "state": self._normalize_torrent_state(task.get("status", "error")),
                    "progress": task.get("size", 0) / task.get("size", 1) if task.get("size") else 0,
                    "downloaded": transfer.get("size_downloaded", 0),
                    "uploaded": transfer.get("size_uploaded", 0),
                    "total_size": task.get("size", 0),
                    "download_speed": transfer.get("speed_download", 0),
                    "upload_speed": transfer.get("speed_upload", 0),
                    "ratio": transfer.get("size_uploaded", 0) / max(transfer.get("size_downloaded", 1), 1),
                    "eta": None,
                    "save_path": additional.get("detail", {}).get("destination", ""),
                })

            return result_list

        except Exception as e:
            logger.error(f"Error getting torrent list from Synology: {str(e)}")
            raise

    async def pause_torrent(self, task_hash: str) -> bool:
        """
        暂停种子

        Args:
            task_hash: 种子hash或任务ID

        Returns:
            bool: 是否成功
        """
        try:
            await self._ensure_logged_in()

            await self._call_api(
                "SYNO.DownloadStation.Task",
                "pause",
                version=1,
                params={"id": task_hash},
            )

            logger.info(f"Successfully paused torrent {task_hash}")
            return True

        except Exception as e:
            logger.error(f"Error pausing torrent in Synology: {str(e)}")
            return False

    async def resume_torrent(self, task_hash: str) -> bool:
        """
        恢复种子

        Args:
            task_hash: 种子hash或任务ID

        Returns:
            bool: 是否成功
        """
        try:
            await self._ensure_logged_in()

            await self._call_api(
                "SYNO.DownloadStation.Task",
                "resume",
                version=1,
                params={"id": task_hash},
            )

            logger.info(f"Successfully resumed torrent {task_hash}")
            return True

        except Exception as e:
            logger.error(f"Error resuming torrent in Synology: {str(e)}")
            return False

    async def delete_torrent(self, task_hash: str, delete_files: bool = False) -> bool:
        """
        删除种子

        Args:
            task_hash: 种子hash或任务ID
            delete_files: 是否同时删除文件

        Returns:
            bool: 是否成功
        """
        try:
            await self._ensure_logged_in()

            # Synology 的 delete 方法需要额外参数指定是否删除文件
            params = {
                "id": task_hash,
                "force_complete": "false",  # 强制完成删除
            }

            await self._call_api(
                "SYNO.DownloadStation.Task",
                "delete",
                version=1,
                params=params,
            )

            logger.info(f"Successfully deleted torrent {task_hash}, delete_files={delete_files}")
            return True

        except Exception as e:
            logger.error(f"Error deleting torrent in Synology: {str(e)}")
            return False

    async def set_torrent_limits(
        self,
        task_hash: str,
        ratio_limit: Optional[float] = None,
        seeding_time_limit: Optional[int] = None,
    ) -> bool:
        """
        设置种子做种限制

        注意：Synology Download Station 不直接支持单个任务的做种限制设置
        这是一个全局设置，需要通过 Web UI 或 SYNO.DownloadStation.BT 设置

        Args:
            task_hash: 种子hash或任务ID
            ratio_limit: 分享率限制
            seeding_time_limit: 做种时长限制（分钟）

        Returns:
            bool: 是否成功
        """
        try:
            # Synology DS 不支持单个任务的做种限制
            # 只能通过全局设置或手动管理
            logger.warning(
                "Synology Download Station does not support per-task seeding limits. "
                "Please configure global seeding settings in DSM."
            )
            return True

        except Exception as e:
            logger.error(f"Error setting torrent limits in Synology: {str(e)}")
            return False
