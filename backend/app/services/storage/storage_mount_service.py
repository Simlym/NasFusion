# -*- coding: utf-8 -*-
"""
存储挂载点服务
管理下载目录和媒体库目录的挂载点配置，支持 Docker 和本地两种部署模式
"""
import logging
import os
import re
from pathlib import Path
from typing import Optional

from sqlalchemy import select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.storage_mount import StorageMount
from app.constants import MEDIA_TYPES

logger = logging.getLogger(__name__)


class StorageMountService:
    """存储挂载点服务"""

    # Docker 模式下的卷挂载基础目录
    DOCKER_VOLUME_BASE = Path("/mnt")
    
    # 卷目录名正则 (volume1, volume2, ...)
    VOLUME_DIR_PATTERN = re.compile(r"^volume(\d+)$")
    
    # 兼容旧模式的常量（保留以支持本地模式）
    DOCKER_DOWNLOAD_BASE = Path("/app/data/downloads")
    DOCKER_LIBRARY_BASE = Path("/app/data/library")
    MOUNT_DIR_PATTERN = re.compile(r"^mount_(\d+)$")

    # ==================== 环境检测 ====================

    @staticmethod
    def is_docker_environment() -> bool:
        """
        检测是否在 Docker 容器中运行
        
        Returns:
            bool: 如果在 Docker 容器中运行返回 True
        """
        return os.path.exists('/.dockerenv') or os.environ.get('DOCKER_CONTAINER') == 'true'

    # ==================== 挂载点扫描 ====================

    @classmethod
    async def scan_and_init_mounts(cls, db: AsyncSession) -> int:
        """
        扫描并初始化存储挂载点
        
        根据运行环境自动选择扫描模式：
        - Docker 模式：扫描预定义的 mount_* 目录
        - 本地模式：从环境变量读取配置
        
        Args:
            db: 数据库会话
            
        Returns:
            int: 扫描到的挂载点数量
        """
        if cls.is_docker_environment():
            logger.debug("检测到 Docker 环境，使用 Docker 模式扫描挂载点")
            return await cls._scan_docker_mounts(db)
        else:
            logger.debug("检测到本地环境，使用本地模式扫描挂载点")
            return await cls._scan_local_mounts(db)

    @classmethod
    async def _scan_docker_mounts(cls, db: AsyncSession) -> int:
        """
        Docker 模式：扫描 /mnt/volumeN 目录
        
        新逻辑：
        - 扫描 /mnt 下所有 volumeN 目录
        - 每个 volumeN 作为一个"卷挂载点"记录
        - 同一 volumeN 内的所有路径共享 device_id，支持硬链接
        
        目录结构：
        - /mnt/volume1, volume2, ...
        """
        count = 0
        
        # 扫描卷挂载点
        if cls.DOCKER_VOLUME_BASE.exists():
            for volume_dir in cls.DOCKER_VOLUME_BASE.iterdir():
                if volume_dir.is_dir() and cls.VOLUME_DIR_PATTERN.match(volume_dir.name):
                    volume_num = cls.VOLUME_DIR_PATTERN.match(volume_dir.name).group(1)
                    name = f"volume_{volume_num}"
                    host_path = os.environ.get(f"VOLUME_{volume_num}_PATH")
                    
                    # 检查是否是有效的挂载（不是 /dev/null 等占位符）
                    if not volume_dir.is_mount() and len(list(volume_dir.iterdir())) == 0:
                        logger.debug(f"跳过空卷目录: {volume_dir}")
                        continue
                    
                    await cls._create_or_update_mount(
                        db,
                        name=name,
                        mount_type="volume",  # 新类型：卷
                        container_path=str(volume_dir),
                        host_path=host_path,
                    )
                    count += 1
                    logger.info(f"扫描到存储卷: {name} -> {volume_dir} (宿主机: {host_path})")
        else:
            logger.warning(f"卷挂载基础目录不存在: {cls.DOCKER_VOLUME_BASE}")
        
        await db.commit()
        logger.info(f"Docker 模式扫描完成，共 {count} 个存储卷")
        return count

    @classmethod
    async def _scan_local_mounts(cls, db: AsyncSession) -> int:
        """
        本地模式：从环境变量读取配置
        
        环境变量格式：
        - STORAGE_DOWNLOAD_PATHS: 多个路径用逗号分隔
        - STORAGE_LIBRARY_PATHS: 格式为 "路径:分类:是否默认" (如 /data/movies:movie:true)
        """
        count = 0
        
        # 解析下载目录
        download_paths = os.environ.get("STORAGE_DOWNLOAD_PATHS", "")
        if download_paths:
            for i, path in enumerate(download_paths.split(","), 1):
                path = path.strip()
                if path and Path(path).exists():
                    name = f"download_local_{i}"
                    await cls._create_or_update_mount(
                        db,
                        name=name,
                        mount_type="download",
                        container_path=path,
                        host_path=path,  # 本地模式下相同
                    )
                    count += 1
                    logger.debug(f"配置下载挂载点: {name} -> {path}")
        
        # 解析媒体库目录 (格式: 路径:分类:是否默认)
        library_paths = os.environ.get("STORAGE_LIBRARY_PATHS", "")
        if library_paths:
            for i, config in enumerate(library_paths.split(","), 1):
                parts = config.strip().split(":")
                if len(parts) >= 1:
                    path = parts[0].strip()
                    media_category = parts[1].strip() if len(parts) > 1 else None
                    is_default = parts[2].strip().lower() == "true" if len(parts) > 2 else False
                    
                    if path and Path(path).exists():
                        name = f"library_local_{i}"
                        await cls._create_or_update_mount(
                            db,
                            name=name,
                            mount_type="library",
                            container_path=path,
                            host_path=path,
                            media_category=media_category,
                            is_default=is_default,
                        )
                        count += 1
                        logger.debug(f"配置媒体库挂载点: {name} -> {path} (分类: {media_category})")

        await db.commit()
        logger.info(f"本地模式扫描完成，共 {count} 个挂载点")
        return count

    @classmethod
    async def _create_or_update_mount(
        cls,
        db: AsyncSession,
        name: str,
        mount_type: str,
        container_path: str,
        host_path: Optional[str] = None,
        media_category: Optional[str] = None,
        is_default: bool = False,
    ) -> StorageMount:
        """
        创建或更新挂载点
        
        Args:
            db: 数据库会话
            name: 挂载点名称
            mount_type: 挂载点类型 (download/library)
            container_path: 容器内路径
            host_path: 宿主机路径
            media_category: 媒体分类 (仅 library 类型)
            is_default: 是否为默认挂载点
            
        Returns:
            StorageMount: 挂载点对象
        """
        # 查找现有挂载点
        result = await db.execute(
            select(StorageMount).where(StorageMount.name == name)
        )
        mount = result.scalar_one_or_none()
        
        # 获取设备 ID (用于同盘检测)
        device_id = cls._get_device_id(container_path)
        
        # 检查路径是否可访问
        is_accessible = Path(container_path).exists() and os.access(container_path, os.R_OK)
        
        if mount:
            # 更新现有挂载点
            mount.container_path = container_path
            mount.host_path = host_path or mount.host_path
            mount.device_id = device_id
            mount.is_accessible = is_accessible
            if media_category and mount.mount_type == "library":
                mount.media_category = media_category
            if is_default:
                mount.is_default = is_default
            logger.debug(f"更新挂载点: {name}")
        else:
            # 创建新挂载点
            mount = StorageMount(
                name=name,
                mount_type=mount_type,
                container_path=container_path,
                host_path=host_path,
                device_id=device_id,
                media_category=media_category if mount_type == "library" else None,
                is_default=is_default,
                is_accessible=is_accessible,
            )
            db.add(mount)
            logger.debug(f"创建挂载点: {name}")
        
        # 刷新磁盘空间信息
        await cls._update_disk_info(mount)
        
        return mount

    # ==================== 查询方法 ====================

    @classmethod
    async def get_all_mounts(
        cls,
        db: AsyncSession,
        mount_type: Optional[str] = None,
        media_category: Optional[str] = None,
        is_enabled: bool = True,
    ) -> list[StorageMount]:
        """
        获取所有挂载点
        
        Args:
            db: 数据库会话
            mount_type: 筛选挂载点类型
            media_category: 筛选媒体分类
            is_enabled: 是否只返回启用的挂载点
            
        Returns:
            list[StorageMount]: 挂载点列表
        """
        conditions = []
        if mount_type:
            conditions.append(StorageMount.mount_type == mount_type)
        if media_category:
            conditions.append(StorageMount.media_category == media_category)
        if is_enabled:
            conditions.append(StorageMount.is_enabled == True)
        
        query = select(StorageMount)
        if conditions:
            query = query.where(and_(*conditions))
        query = query.order_by(StorageMount.priority.desc(), StorageMount.id)
        
        result = await db.execute(query)
        return list(result.scalars().all())

    @classmethod
    async def get_download_mounts_for_media(
        cls,
        db: AsyncSession,
        media_category: str,
        target_library_mount_id: Optional[int] = None,
    ) -> list[StorageMount]:
        """
        获取适合指定媒体分类的下载挂载点列表
        优先返回与目标媒体库同盘的挂载点
        
        Args:
            db: 数据库会话
            media_category: 目标媒体分类
            target_library_mount_id: 目标媒体库挂载点 ID (用于同盘优先排序)
            
        Returns:
            list[StorageMount]: 按优先级排序的下载挂载点列表
        """
        # 获取所有启用的下载挂载点
        download_mounts = await cls.get_all_mounts(db, mount_type="download")
        
        if not download_mounts:
            return []
        
        # 如果指定了目标媒体库挂载点，获取其设备 ID
        target_device_id = None
        if target_library_mount_id:
            result = await db.execute(
                select(StorageMount).where(StorageMount.id == target_library_mount_id)
            )
            target_mount = result.scalar_one_or_none()
            if target_mount:
                target_device_id = target_mount.device_id
        else:
            # 获取该分类的默认媒体库挂载点的设备 ID
            result = await db.execute(
                select(StorageMount).where(
                    and_(
                        StorageMount.mount_type == "library",
                        StorageMount.media_category == media_category,
                        StorageMount.is_default == True,
                        StorageMount.is_enabled == True,
                    )
                )
            )
            default_library = result.scalar_one_or_none()
            if default_library:
                target_device_id = default_library.device_id
        
        # 标记是否同盘并排序
        for mount in download_mounts:
            mount.is_same_disk = (
                target_device_id is not None 
                and mount.device_id is not None 
                and mount.device_id == target_device_id
            )
        
        # 同盘优先，然后按剩余空间排序
        return sorted(
            download_mounts,
            key=lambda m: (not m.is_same_disk, -(m.free_space or 0))
        )

    @classmethod
    async def get_library_mounts_by_category(
        cls,
        db: AsyncSession,
        media_category: str,
    ) -> list[StorageMount]:
        """
        获取指定分类的媒体库挂载点
        
        Args:
            db: 数据库会话
            media_category: 媒体分类
            
        Returns:
            list[StorageMount]: 按优先级排序的媒体库挂载点列表
        """
        return await cls.get_all_mounts(
            db, 
            mount_type="library", 
            media_category=media_category
        )

    @classmethod
    async def get_organize_target(
        cls,
        db: AsyncSession,
        source_path: str,
        media_category: str,
    ) -> Optional[StorageMount]:
        """
        获取整理目标挂载点
        优先选择与源文件同盘的挂载点（支持硬链接）
        
        Args:
            db: 数据库会话
            source_path: 源文件路径
            media_category: 媒体分类
            
        Returns:
            Optional[StorageMount]: 目标挂载点，如果没有找到返回 None
        """
        # 获取源文件的设备 ID
        source_device_id = cls._get_device_id(source_path)
        
        # 获取该分类的所有媒体库挂载点
        library_mounts = await cls.get_library_mounts_by_category(db, media_category)
        
        if not library_mounts:
            return None
        
        # 优先选择同盘的挂载点
        for mount in library_mounts:
            if source_device_id and mount.device_id == source_device_id:
                logger.info(f"找到同盘挂载点: {mount.name} (支持硬链接)")
                return mount
        
        # 如果没有同盘的，返回默认挂载点或第一个
        default_mount = next((m for m in library_mounts if m.is_default), None)
        return default_mount or library_mounts[0]

    # ==================== 同盘检测 ====================

    @classmethod
    def check_same_disk(cls, path1: str, path2: str) -> dict:
        """
        检查两个路径是否在同一磁盘
        
        Args:
            path1: 第一个路径
            path2: 第二个路径
            
        Returns:
            dict: 包含 same_disk 和 can_hardlink 的字典
        """
        device_id_1 = cls._get_device_id(path1)
        device_id_2 = cls._get_device_id(path2)
        
        # 如果任一路径不存在或无法获取设备 ID
        if device_id_1 is None or device_id_2 is None:
            return {
                "same_disk": False,
                "can_hardlink": False,
                "reason": "无法获取设备信息",
            }
        
        same_disk = device_id_1 == device_id_2
        
        return {
            "same_disk": same_disk,
            "can_hardlink": same_disk,  # 同盘才支持硬链接
            "device_id_1": device_id_1,
            "device_id_2": device_id_2,
        }

    @staticmethod
    def _get_device_id(path: str) -> Optional[int]:
        """
        获取路径所在的设备 ID
        
        Args:
            path: 文件或目录路径
            
        Returns:
            Optional[int]: 设备 ID，如果路径不存在返回 None
        """
        # SQLite BIGINT 最大值 (2^63 - 1)
        MAX_SQLITE_INT = 9223372036854775807
        
        def normalize_device_id(dev_id: int) -> int:
            """将设备 ID 限制在 SQLite 可存储的范围内"""
            if dev_id > MAX_SQLITE_INT:
                # 使用取模确保值在有效范围内，同时保持唯一性
                return dev_id % MAX_SQLITE_INT
            return dev_id
        
        try:
            path_obj = Path(path)
            if not path_obj.exists():
                # 尝试获取父目录的设备 ID
                for parent in path_obj.parents:
                    if parent.exists():
                        return normalize_device_id(os.stat(parent).st_dev)
                return None
            return normalize_device_id(os.stat(path).st_dev)
        except (OSError, ValueError) as e:
            logger.warning(f"获取设备 ID 失败: {path}, 错误: {e}")
            return None

    # ==================== 磁盘信息 ====================

    @classmethod
    async def refresh_disk_info(
        cls,
        db: AsyncSession,
        mount_id: Optional[int] = None,
    ) -> int:
        """
        刷新磁盘空间信息
        
        Args:
            db: 数据库会话
            mount_id: 指定挂载点 ID，如果为 None 则刷新所有
            
        Returns:
            int: 刷新的挂载点数量
        """
        if mount_id:
            result = await db.execute(
                select(StorageMount).where(StorageMount.id == mount_id)
            )
            mounts = [result.scalar_one_or_none()]
            mounts = [m for m in mounts if m]
        else:
            result = await db.execute(select(StorageMount))
            mounts = list(result.scalars().all())
        
        count = 0
        for mount in mounts:
            await cls._update_disk_info(mount)
            count += 1
        
        await db.commit()
        logger.info(f"刷新了 {count} 个挂载点的磁盘信息")
        return count

    @classmethod
    async def _update_disk_info(cls, mount: StorageMount) -> None:
        """
        更新单个挂载点的磁盘空间信息
        
        Args:
            mount: 挂载点对象
        """
        try:
            path = Path(mount.container_path)
            if path.exists():
                import shutil
                usage = shutil.disk_usage(path)
                mount.total_space = usage.total
                mount.used_space = usage.used
                mount.free_space = usage.free
                mount.is_accessible = True
            else:
                mount.is_accessible = False
        except (OSError, ValueError) as e:
            logger.warning(f"获取磁盘信息失败: {mount.container_path}, 错误: {e}")
            mount.is_accessible = False

    # ==================== 配置更新 ====================

    @classmethod
    async def update_mount_config(
        cls,
        db: AsyncSession,
        mount_id: int,
        **kwargs,
    ) -> Optional[StorageMount]:
        """
        更新挂载点配置
        
        Args:
            db: 数据库会话
            mount_id: 挂载点 ID
            **kwargs: 要更新的字段
            
        Returns:
            Optional[StorageMount]: 更新后的挂载点对象
        """
        result = await db.execute(
            select(StorageMount).where(StorageMount.id == mount_id)
        )
        mount = result.scalar_one_or_none()
        
        if not mount:
            return None
        
        # 处理默认挂载点的唯一性
        if kwargs.get("is_default") and mount.media_category:
            # 取消同分类的其他默认挂载点
            await db.execute(
                update(StorageMount)
                .where(
                    and_(
                        StorageMount.media_category == mount.media_category,
                        StorageMount.id != mount_id,
                    )
                )
                .values(is_default=False)
            )

        # 更新字段
        allowed_fields = {
            "container_path", "host_path", "media_category", "priority",
            "is_default", "is_enabled", "custom_label", "description", "disk_group"
        }

        # 检查是否需要更新 container_path 相关的字段
        update_device_info = "container_path" in kwargs

        for key, value in kwargs.items():
            if key in allowed_fields and hasattr(mount, key):
                setattr(mount, key, value)

        # 如果更新了 container_path，需要重新计算 device_id 和 is_accessible
        if update_device_info:
            mount.device_id = cls._get_device_id(mount.container_path)
            mount.is_accessible = Path(mount.container_path).exists() and os.access(mount.container_path, os.R_OK)
            # 刷新磁盘空间信息
            await cls._update_disk_info(mount)

        await db.commit()
        await db.refresh(mount)
        return mount

    @classmethod
    async def get_mount_by_id(
        cls,
        db: AsyncSession,
        mount_id: int,
    ) -> Optional[StorageMount]:
        """
        根据 ID 获取挂载点

        Args:
            db: 数据库会话
            mount_id: 挂载点 ID

        Returns:
            Optional[StorageMount]: 挂载点对象
        """
        result = await db.execute(
            select(StorageMount).where(StorageMount.id == mount_id)
        )
        return result.scalar_one_or_none()

    # ==================== 创建和删除 ====================

    @classmethod
    async def create_mount(
        cls,
        db: AsyncSession,
        name: str,
        mount_type: str,
        container_path: str,
        host_path: Optional[str] = None,
        media_category: Optional[str] = None,
        is_default: bool = False,
        priority: int = 0,
    ) -> StorageMount:
        """
        手动创建挂载点

        Args:
            db: 数据库会话
            name: 挂载点名称
            mount_type: 挂载点类型 (download/library)
            container_path: 容器内路径
            host_path: 宿主机路径
            media_category: 媒体分类 (仅 library 类型)
            is_default: 是否为默认挂载点
            priority: 优先级

        Returns:
            StorageMount: 创建的挂载点对象
        """
        # 检查名称是否已存在
        result = await db.execute(
            select(StorageMount).where(StorageMount.name == name)
        )
        if result.scalar_one_or_none():
            raise ValueError(f"挂载点名称 '{name}' 已存在")

        # 获取设备 ID
        device_id = cls._get_device_id(container_path)

        # 检查路径是否可访问
        is_accessible = Path(container_path).exists() and os.access(container_path, os.R_OK)

        # 创建挂载点
        mount = StorageMount(
            name=name,
            mount_type=mount_type,
            container_path=container_path,
            host_path=host_path,
            device_id=device_id,
            media_category=media_category if mount_type == "library" else None,
            is_default=is_default,
            is_accessible=is_accessible,
            priority=priority,
            is_enabled=True,
        )
        db.add(mount)

        # 刷新磁盘空间信息
        await cls._update_disk_info(mount)

        await db.commit()
        await db.refresh(mount)
        logger.info(f"创建挂载点: {name} ({mount_type})")
        return mount

    @classmethod
    async def delete_mount(
        cls,
        db: AsyncSession,
        mount_id: int,
    ) -> bool:
        """
        删除挂载点

        Args:
            db: 数据库会话
            mount_id: 挂载点 ID

        Returns:
            bool: 是否删除成功
        """
        result = await db.execute(
            select(StorageMount).where(StorageMount.id == mount_id)
        )
        mount = result.scalar_one_or_none()

        if not mount:
            return False

        name = mount.name
        await db.delete(mount)
        await db.commit()
        logger.info(f"删除挂载点: {name}")
        return True
