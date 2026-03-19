# -*- coding: utf-8 -*-
"""
文件系统操作服务
提供路径验证、磁盘信息、目录浏览等功能
"""
import asyncio
import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from app.core.config import settings


class FileSystemService:
    """文件系统操作服务"""

    @staticmethod
    async def validate_path(path: str) -> Dict:
        """
        验证路径有效性

        Args:
            path: 路径字符串

        Returns:
            {
                "exists": bool,
                "is_directory": bool,
                "readable": bool,
                "writable": bool,
                "disk_info": {
                    "total": int,
                    "used": int,
                    "free": int,
                    "percent": float
                },
                "error": str | None
            }
        """
        def _validate():
            try:
                path_obj = Path(path)

                # 检查路径是否存在
                exists = path_obj.exists()

                if not exists:
                    return {
                        "exists": False,
                        "is_directory": False,
                        "readable": False,
                        "writable": False,
                        "disk_info": None,
                        "error": None
                    }

                # 检查是否是目录
                is_directory = path_obj.is_dir()

                # 检查权限
                readable = os.access(path, os.R_OK)
                writable = os.access(path, os.W_OK)

                # 获取磁盘信息
                disk_info = None
                if exists:
                    try:
                        usage = shutil.disk_usage(path)
                        disk_info = {
                            "total": usage.total,
                            "used": usage.used,
                            "free": usage.free,
                            "percent": round((usage.used / usage.total) * 100, 2)
                        }
                    except Exception as e:
                        # 磁盘信息获取失败不影响主流程
                        pass

                return {
                    "exists": exists,
                    "is_directory": is_directory,
                    "readable": readable,
                    "writable": writable,
                    "disk_info": disk_info,
                    "error": None
                }

            except Exception as e:
                return {
                    "exists": False,
                    "is_directory": False,
                    "readable": False,
                    "writable": False,
                    "disk_info": None,
                    "error": str(e)
                }

        # 使用线程池执行同步操作
        return await asyncio.to_thread(_validate)

    @staticmethod
    async def get_disk_info(path: str) -> Optional[Dict]:
        """
        获取磁盘信息

        Args:
            path: 路径字符串

        Returns:
            {
                "total": int,
                "used": int,
                "free": int,
                "percent": float
            } or None
        """
        def _get_info():
            try:
                path_obj = Path(path)
                if not path_obj.exists():
                    return None

                usage = shutil.disk_usage(path)
                return {
                    "total": usage.total,
                    "used": usage.used,
                    "free": usage.free,
                    "percent": round((usage.used / usage.total) * 100, 2)
                }
            except Exception:
                return None

        return await asyncio.to_thread(_get_info)

    @staticmethod
    async def browse_directory(
        path: str,
        show_hidden: bool = False
    ) -> Dict:
        """
        浏览目录结构

        Args:
            path: 路径字符串
            show_hidden: 是否显示隐藏文件

        Returns:
            {
                "current_path": str,
                "parent_path": str | None,
                "directories": [
                    {
                        "name": str,
                        "path": str,
                        "size": int,
                        "modified_at": str,
                        "is_accessible": bool
                    }
                ]
            }
        """
        def _browse():
            try:
                path_obj = Path(path).resolve()

                # 检查路径是否存在且是目录
                if not path_obj.exists():
                    raise ValueError(f"路径不存在: {path}")

                if not path_obj.is_dir():
                    raise ValueError(f"路径不是目录: {path}")

                # 获取父目录路径
                parent_path = str(path_obj.parent) if path_obj.parent != path_obj else None

                # 获取子目录列表
                directories = []

                try:
                    for item in path_obj.iterdir():
                        # 跳过隐藏文件（除非显式要求）
                        if not show_hidden and item.name.startswith('.'):
                            continue

                        # 只列出目录
                        if not item.is_dir():
                            continue

                        try:
                            # 获取目录信息
                            stat = item.stat()
                            is_accessible = os.access(item, os.R_OK)

                            directories.append({
                                "name": item.name,
                                "path": str(item),
                                "size": stat.st_size,
                                "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                                "is_accessible": is_accessible
                            })
                        except (PermissionError, OSError):
                            # 无权限访问的目录也显示，但标记为不可访问
                            directories.append({
                                "name": item.name,
                                "path": str(item),
                                "size": 0,
                                "modified_at": None,
                                "is_accessible": False
                            })

                except PermissionError:
                    raise ValueError(f"无权限访问目录: {path}")

                # 按名称排序
                directories.sort(key=lambda x: x["name"].lower())

                return {
                    "current_path": str(path_obj),
                    "parent_path": parent_path,
                    "directories": directories
                }

            except Exception as e:
                raise ValueError(f"浏览目录失败: {str(e)}")

        return await asyncio.to_thread(_browse)

    @staticmethod
    async def create_directory(
        path: str,
        recursive: bool = True
    ) -> Dict:
        """
        创建目录

        Args:
            path: 路径字符串
            recursive: 是否递归创建父目录

        Returns:
            {
                "success": bool,
                "path": str,
                "created": bool,  # 是否新创建（false表示已存在）
                "error": str | None
            }
        """
        def _create():
            try:
                path_obj = Path(path)

                # 检查是否已存在
                if path_obj.exists():
                    if path_obj.is_dir():
                        return {
                            "success": True,
                            "path": str(path_obj),
                            "created": False,
                            "error": None
                        }
                    else:
                        return {
                            "success": False,
                            "path": str(path_obj),
                            "created": False,
                            "error": "路径已存在但不是目录"
                        }

                # 创建目录
                if recursive:
                    path_obj.mkdir(parents=True, exist_ok=True)
                else:
                    path_obj.mkdir(exist_ok=True)

                return {
                    "success": True,
                    "path": str(path_obj),
                    "created": True,
                    "error": None
                }

            except PermissionError:
                return {
                    "success": False,
                    "path": path,
                    "created": False,
                    "error": "无权限创建目录"
                }
            except Exception as e:
                return {
                    "success": False,
                    "path": path,
                    "created": False,
                    "error": str(e)
                }

        return await asyncio.to_thread(_create)

    @staticmethod
    async def check_permissions(path: str) -> Dict:
        """
        检查目录权限

        Args:
            path: 路径字符串

        Returns:
            {
                "readable": bool,
                "writable": bool,
                "executable": bool
            }
        """
        def _check():
            try:
                return {
                    "readable": os.access(path, os.R_OK),
                    "writable": os.access(path, os.W_OK),
                    "executable": os.access(path, os.X_OK)
                }
            except Exception:
                return {
                    "readable": False,
                    "writable": False,
                    "executable": False
                }

        return await asyncio.to_thread(_check)
