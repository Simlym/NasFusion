"""
适配器基类
定义外部系统集成的统一接口
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BasePTSiteAdapter(ABC):
    """PT站点适配器基类"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化适配器

        Args:
            config: 站点配置字典
        """
        self.config = config
        self.site_name = config.get("name", "Unknown")
        self.base_url = config.get("base_url", "")

    @abstractmethod
    async def authenticate(self) -> bool:
        """
        认证

        Returns:
            是否认证成功
        """
        pass

    @abstractmethod
    async def fetch_resources(
        self, page: int = 1, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        获取资源列表

        Args:
            page: 页码
            limit: 每页数量

        Returns:
            资源列表
        """
        pass

    @abstractmethod
    async def get_resource_detail(self, resource_id: str) -> Dict[str, Any]:
        """
        获取资源详情

        Args:
            resource_id: 资源ID

        Returns:
            资源详情字典
        """
        pass

    @abstractmethod
    async def download_torrent(self, resource_id: str, download_url: str = None) -> bytes:
        """
        下载种子文件

        Args:
            resource_id: 资源ID
            download_url: 完整下载URL（可选，可能包含认证信息）

        Returns:
            种子文件字节流
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        健康检查

        Returns:
            站点是否正常
        """
        pass

    async def fetch_user_profile(self) -> Optional[Dict[str, Any]]:
        """
        获取站点用户信息

        Returns:
            用户信息字典，包含字段如：
            - username: 用户名
            - user_class: 等级
            - uploaded: 上传量（字节）
            - downloaded: 下载量（字节）
            - ratio: 分享率
            - seeding_count: 做种数
            - seeding_size: 做种量（字节）
            - bonus: 积分/魔力值
            - join_date: 入站时间
            - publish_count: 发布数

            未实现时返回 None
        """
        return None


class BaseDownloaderAdapter(ABC):
    """下载器适配器基类"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    @abstractmethod
    async def add_torrent(
        self, torrent_file: bytes, save_path: str, **kwargs
    ) -> str:
        """添加种子任务"""
        pass

    @abstractmethod
    async def get_torrent_status(self, torrent_id: str) -> Dict[str, Any]:
        """获取任务状态"""
        pass

    @abstractmethod
    async def pause_torrent(self, torrent_id: str) -> bool:
        """暂停任务"""
        pass

    @abstractmethod
    async def resume_torrent(self, torrent_id: str) -> bool:
        """恢复任务"""
        pass

    @abstractmethod
    async def remove_torrent(self, torrent_id: str, delete_files: bool = False) -> bool:
        """删除任务"""
        pass


class BaseNotificationAdapter(ABC):
    """通知适配器基类"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    @abstractmethod
    async def send(self, title: str, message: str, **kwargs) -> bool:
        """发送通知"""
        pass

    @abstractmethod
    async def test_connection(self) -> bool:
        """测试连接"""
        pass
