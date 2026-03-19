# -*- coding: utf-8 -*-
"""
路径映射工具
用于将媒体服务器（Jellyfin/Emby/Plex）的文件路径映射到本地路径
"""
import os
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


def apply_path_mappings(
    server_path: str,
    mappings: Optional[List[Dict[str, str]]] = None
) -> Optional[str]:
    """
    应用路径映射规则，将媒体服务器路径转换为本地路径

    Args:
        server_path: 媒体服务器的文件路径
        mappings: 路径映射规则列表
            例如: [
                {"server_path": "/media", "local_path": "D:/media"},
                {"server_path": "/mnt/data", "local_path": "/data"}
            ]

    Returns:
        Optional[str]: 映射后的本地路径，如果没有匹配的规则则返回 None

    Examples:
        >>> mappings = [{"server_path": "/media", "local_path": "D:/media"}]
        >>> apply_path_mappings("/media/Movies/test.mkv", mappings)
        'D:/media/Movies/test.mkv'
    """
    if not server_path or not mappings:
        return None

    # 标准化路径分隔符
    normalized_server_path = normalize_path(server_path)

    # 遍历所有映射规则
    for mapping in mappings:
        server_prefix = mapping.get("server_path")
        local_prefix = mapping.get("local_path")

        if not server_prefix or not local_prefix:
            continue

        # 标准化映射规则中的路径
        normalized_server_prefix = normalize_path(server_prefix)
        normalized_local_prefix = normalize_path(local_prefix)

        # 检查是否匹配
        if normalized_server_path.startswith(normalized_server_prefix):
            # 替换前缀
            relative_path = normalized_server_path[len(normalized_server_prefix):].lstrip("/\\")
            mapped_path = os.path.join(normalized_local_prefix, relative_path)

            logger.debug(
                f"Path mapping matched: '{server_path}' -> '{mapped_path}' "
                f"(rule: {server_prefix} -> {local_prefix})"
            )

            return mapped_path

    logger.debug(f"No path mapping matched for: {server_path}")
    return None


def normalize_path(path: str) -> str:
    """
    标准化路径，处理不同操作系统的路径分隔符

    Args:
        path: 原始路径

    Returns:
        str: 标准化后的路径（使用正斜杠）

    Examples:
        >>> normalize_path("D:\\media\\Movies")
        'D:/media/Movies'
        >>> normalize_path("/media/Movies/")
        '/media/Movies'
    """
    if not path:
        return ""

    # 统一使用正斜杠
    normalized = path.replace("\\", "/")

    # 移除末尾的斜杠
    normalized = normalized.rstrip("/")

    return normalized


def validate_path_exists(path: str) -> bool:
    """
    验证路径是否存在

    Args:
        path: 文件或目录路径

    Returns:
        bool: 路径是否存在
    """
    if not path:
        return False

    return os.path.exists(path)


def batch_apply_path_mappings(
    server_paths: List[str],
    mappings: Optional[List[Dict[str, str]]] = None,
    validate_exists: bool = False
) -> Dict[str, Optional[str]]:
    """
    批量应用路径映射

    Args:
        server_paths: 媒体服务器路径列表
        mappings: 路径映射规则
        validate_exists: 是否验证映射后的路径存在

    Returns:
        Dict[str, Optional[str]]: 映射结果字典 {server_path: local_path}
    """
    result = {}

    for server_path in server_paths:
        mapped_path = apply_path_mappings(server_path, mappings)

        # 如果需要验证存在性
        if mapped_path and validate_exists:
            if not validate_path_exists(mapped_path):
                logger.warning(f"Mapped path does not exist: {mapped_path}")
                mapped_path = None

        result[server_path] = mapped_path

    return result
