# -*- coding: utf-8 -*-
"""
下载器适配器基类
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseDownloaderAdapter(ABC):
    """下载器适配器基类"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化下载器适配器

        Args:
            config: 下载器配置字典，包含：
                - host: 主机地址
                - port: 端口号
                - username: 用户名
                - password: 密码
                - use_ssl: 是否使用SSL
        """
        self.config = config
        self.host = config.get("host", "localhost")
        self.port = config.get("port", 8080)
        self.username = config.get("username", "")
        self.password = config.get("password", "")
        self.use_ssl = config.get("use_ssl", False)

    @property
    def base_url(self) -> str:
        """获取基础URL"""
        protocol = "https" if self.use_ssl else "http"
        return f"{protocol}://{self.host}:{self.port}"

    @abstractmethod
    async def test_connection(self) -> bool:
        """
        测试连接

        Returns:
            bool: 连接是否成功
        """
        pass

    @abstractmethod
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
            **options: 其他选项（如分类、标签等）

        Returns:
            Dict: 包含任务信息的字典，至少包含：
                - hash: 种子hash
                - name: 任务名称
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    async def get_torrent_info(self, task_hash: str) -> Dict[str, Any]:
        """
        获取种子信息

        Args:
            task_hash: 种子hash

        Returns:
            Dict: 种子详细信息，包含：
                - hash: 种子hash
                - name: 任务名称
                - state: 状态（downloading/paused/seeding/completed/error等）
                - progress: 进度 0-1
                - downloaded: 已下载字节数
                - uploaded: 已上传字节数
                - total_size: 总大小
                - download_speed: 下载速度（字节/秒）
                - upload_speed: 上传速度
                - ratio: 分享率
                - eta: 预计剩余时间（秒）
        """
        pass

    async def get_torrents_info(self, task_hashes: List[str]) -> List[Dict[str, Any]]:
        """
        批量获取种子信息

        Args:
            task_hashes: 种子hash列表

        Returns:
            List[Dict]: 种子详细信息列表
        """
        # 默认实现为循环调用，建议子类覆盖以优化
        results = []
        for h in task_hashes:
            try:
                info = await self.get_torrent_info(h)
                results.append(info)
            except Exception as e:
                # 记录日志但不中断其他任务的同步
                from app.adapters.downloaders.base import logger
                logger.error(f"Error getting info for hash {h}: {e}")
        return results

    @abstractmethod
    async def get_torrent_list(self, **filters) -> List[Dict[str, Any]]:
        """
        获取种子列表

        Args:
            **filters: 过滤条件

        Returns:
            List[Dict]: 种子信息列表
        """
        pass

    @abstractmethod
    async def pause_torrent(self, task_hash: str) -> bool:
        """
        暂停种子

        Args:
            task_hash: 种子hash

        Returns:
            bool: 是否成功
        """
        pass

    @abstractmethod
    async def resume_torrent(self, task_hash: str) -> bool:
        """
        恢复种子

        Args:
            task_hash: 种子hash

        Returns:
            bool: 是否成功
        """
        pass

    @abstractmethod
    async def delete_torrent(self, task_hash: str, delete_files: bool = False) -> bool:
        """
        删除种子

        Args:
            task_hash: 种子hash
            delete_files: 是否同时删除文件

        Returns:
            bool: 是否成功
        """
        pass

    @abstractmethod
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
        pass
