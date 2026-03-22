# -*- coding: utf-8 -*-
"""
存储挂载点模型
用于管理下载目录和媒体库目录的挂载点配置
"""
from sqlalchemy import Column, Integer, String, BigInteger, Boolean, Text, Index, CheckConstraint

from app.core.db_types import TZDateTime
from app.models.base import Base
from app.utils.timezone import now
from app.constants import MEDIA_TYPES


class StorageMount(Base):
    """存储挂载点表 - 管理下载目录和媒体库目录的挂载点"""
    __tablename__ = "storage_mounts"

    # 主键
    id = Column(Integer, primary_key=True, index=True, autoincrement=True, comment="主键ID")

    # 挂载点基本信息
    name = Column(String(100), unique=True, nullable=False, index=True, comment="挂载点名称")
    mount_type = Column(String(20), nullable=False, index=True, comment="挂载点类型: download/library")
    
    # 路径信息
    container_path = Column(String(500), nullable=False, comment="容器内路径 (Docker模式) 或实际路径 (本地模式)")
    host_path = Column(String(500), nullable=True, comment="宿主机路径 (Docker模式下使用)")
    
    # 设备信息 (用于同盘检测)
    device_id = Column(Integer, nullable=True, index=True, comment="设备ID (用于同盘检测)")
    disk_group = Column(String(50), nullable=True, index=True, comment="磁盘组 (手动指定同盘组)")
    
    # 媒体库专用配置 (mount_type='library' 时使用)
    media_category = Column(String(50), nullable=True, index=True, comment="媒体分类: movie/tv/music/book/anime/adult/game/other")
    priority = Column(Integer, default=0, comment="优先级 (数值越大优先级越高)")
    is_default = Column(Boolean, default=False, comment="是否为该分类的默认挂载点")
    
    # 状态信息
    is_enabled = Column(Boolean, default=True, comment="是否启用")
    is_accessible = Column(Boolean, default=True, comment="是否可访问")
    
    # 磁盘空间信息
    total_space = Column(BigInteger, nullable=True, comment="总空间 (字节)")
    used_space = Column(BigInteger, nullable=True, comment="已用空间 (字节)")
    free_space = Column(BigInteger, nullable=True, comment="可用空间 (字节)")
    
    # 自定义标签和备注
    custom_label = Column(String(100), nullable=True, comment="自定义标签 (如: 大容量盘、SSD快盘)")
    description = Column(Text, nullable=True, comment="备注说明")
    
    # 扫描信息
    last_scan_at = Column(TZDateTime(), nullable=True, comment="最后扫描时间")
    
    # 时间戳
    created_at = Column(TZDateTime(), default=now, nullable=False, comment="创建时间")
    updated_at = Column(TZDateTime(), default=now, onupdate=now, nullable=False, comment="更新时间")

    # 约束和索引
    __table_args__ = (
        # 挂载点类型约束
        CheckConstraint(
            "mount_type IN ('download', 'library')",
            name="check_storage_mount_type"
        ),
        # 媒体分类约束 (仅当 mount_type='library' 时)
        CheckConstraint(
            f"media_category IS NULL OR media_category IN {tuple(MEDIA_TYPES)}",
            name="check_storage_mount_media_category"
        ),
        # 复合索引
        Index("idx_storage_mount_type_category", "mount_type", "media_category"),
        Index("idx_storage_mount_category_default", "media_category", "is_default"),
        Index("idx_storage_mount_device_type", "device_id", "mount_type"),
    )

    def __repr__(self):
        return f"<StorageMount(id={self.id}, name={self.name}, type={self.mount_type}, category={self.media_category})>"
    
    @property
    def usage_percent(self) -> float | None:
        """计算磁盘使用率"""
        if self.total_space and self.total_space > 0:
            return round((self.used_space or 0) / self.total_space * 100, 2)
        return None
    
    @property
    def is_same_as_host(self) -> bool:
        """判断是否为本地模式 (容器路径=宿主机路径)"""
        return self.container_path == self.host_path or self.host_path is None
