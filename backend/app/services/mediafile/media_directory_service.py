# -*- coding: utf-8 -*-
"""
媒体目录服务
提供目录树构建、问题检测、统计等功能
"""
import os
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, delete, String
from sqlalchemy.orm import selectinload
from pathlib import Path

from app.models import MediaDirectory, MediaFile
from app.core.config import settings
from app.constants import (
    ISSUE_TYPE_MISSING_POSTER,
    ISSUE_TYPE_MISSING_NFO,
    ISSUE_TYPE_UNIDENTIFIED,
    ISSUE_TYPE_DUPLICATE,
    ISSUE_TYPE_MISSING_FILES,
    MEDIA_TYPE_TV,
    FILE_TYPE_VIDEO,
)
from app.utils.timezone import now


class MediaDirectoryService:
    """媒体目录服务"""

    @staticmethod
    async def get_by_id(db: AsyncSession, directory_id: int) -> Optional[MediaDirectory]:
        """通过ID获取目录"""
        result = await db.execute(
            select(MediaDirectory).where(MediaDirectory.id == directory_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_path(db: AsyncSession, directory_path: str) -> Optional[MediaDirectory]:
        """通过路径获取目录"""
        result = await db.execute(
            select(MediaDirectory).where(MediaDirectory.directory_path == directory_path)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_tree(
        db: AsyncSession,
        media_type: Optional[str] = None,
        parent_id: Optional[int] = None,
        load_children: bool = False,
        issues: Optional[List[str]] = None,
        sort_by: Optional[str] = None
    ) -> List[MediaDirectory]:
        """
        获取目录树

        Args:
            db: 数据库会话
            media_type: 媒体类型筛选
            parent_id: 父目录ID (None表示根目录)
            load_children: 是否预加载子目录
            issues: 问题筛选列表 (如 ['missing_poster', 'missing_nfo'])
            sort_by: 排序方式 (name=按名称, mtime=按文件修改时间, updated_at=按更新时间)
        """
        # 如果指定了问题筛选，使用扁平化查询模式 (搜索模式)
        if issues and len(issues) > 0:
            query = select(MediaDirectory)
            
            # 媒体类型筛选
            if media_type:
                query = query.where(MediaDirectory.media_type == media_type)
                
            # 问题筛选 (OR 关系，只要满足任意一个选中的问题即可)
            # JSONB 包含判断: issue_flags @> {"missing_poster": true}
            # 对于 SQLite/Generic JSON，通常使用 cast 或 func
            # 这里的 issue_flags 是 JSON 类型
            
            # 构建问题筛选条件
            # 使用 cast(JSON, String) + LIKE 适配 SQLite 和 PostgreSQL JSON 列
            # PostgreSQL JSONB 支持 @> 运算符，但 JSON 类型不支持，统一用文本匹配
            issue_conditions = []
            for issue in issues:
                issue_conditions.append(MediaDirectory.issue_flags.cast(String).like(f'%"{issue}"%'))

            if issue_conditions:
                query = query.where(or_(*issue_conditions))

            # 排序
            query = query.order_by(MediaDirectoryService._get_order_clause(sort_by, default="name"))

            result = await db.execute(query)
            return list(result.scalars().all())

        # 原有的层级浏览模式
        # 如果是请求根目录且指定了媒体类型，尝试“穿透”顶层分类目录直接显示其内容
        if parent_id is None and media_type:
            # 1. 找到该媒体类型的所有顶层根目录（通常是挂载点）
            root_stmt = select(MediaDirectory.id).where(
                MediaDirectory.parent_id == None,
                MediaDirectory.media_type == media_type
            )
            root_ids_res = await db.execute(root_stmt)
            root_ids = [r for r in root_ids_res.scalars().all()]
            
            if root_ids:
                # 2. 返回这些根目录的直接子目录
                query = select(MediaDirectory).where(MediaDirectory.parent_id.in_(root_ids))
            else:
                # 兜底：如果没找到根目录（可能还没有建立层级），则按原逻辑执行
                query = select(MediaDirectory).where(MediaDirectory.parent_id == parent_id)
                query = query.where(MediaDirectory.media_type == media_type)
        else:
            query = select(MediaDirectory).where(MediaDirectory.parent_id == parent_id)
            if media_type:
                query = query.where(MediaDirectory.media_type == media_type)

        if load_children:
            query = query.options(selectinload(MediaDirectory.children))

        query = query.order_by(MediaDirectoryService._get_order_clause(sort_by, default="mtime"))

        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    def _get_order_clause(sort_by: Optional[str], default: str = "mtime"):
        """获取排序子句"""
        sort = sort_by or default
        if sort == "name":
            return MediaDirectory.directory_name.asc()
        elif sort == "mtime":
            return MediaDirectory.source_mtime.desc()
        else:  # updated_at
            return MediaDirectory.updated_at.desc()

    @staticmethod
    async def get_directory_detail(
        db: AsyncSession,
        directory_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        获取目录详情(包含文件列表和统计)

        Returns:
            {
                "directory": MediaDirectory对象,
                "files": 文件列表,
                "statistics": {
                    "total_files": 总文件数,
                    "total_size": 总大小,
                    "video_files": 视频文件数,
                    "identified_files": 已识别文件数
                }
            }
        """
        # 获取目录
        directory = await MediaDirectoryService.get_by_id(db, directory_id)
        if not directory:
            return None

        # 获取目录下的文件(包含Jellyfin关联信息)
        from app.models.media_server_item import MediaServerItem
        from app.models.media_server_config import MediaServerConfig
        from sqlalchemy.orm import selectinload

        files_result = await db.execute(
            select(MediaFile)
            .where(MediaFile.media_directory_id == directory_id)
            .order_by(MediaFile.file_name)
        )
        files = list(files_result.scalars().all())

        # 获取这些文件的Jellyfin关联信息
        if files:
            file_ids = [f.id for f in files]
            media_server_items_result = await db.execute(
                select(MediaServerItem)
                .where(MediaServerItem.media_file_id.in_(file_ids))
                .where(MediaServerItem.is_active == True)
            )
            media_server_items = {item.media_file_id: item for item in media_server_items_result.scalars().all()}

            # 获取所有相关的媒体服务器配置（用于构建 web_url）
            server_config_ids = set(item.media_server_config_id for item in media_server_items.values())
            server_configs = {}
            if server_config_ids:
                configs_result = await db.execute(
                    select(MediaServerConfig).where(MediaServerConfig.id.in_(server_config_ids))
                )
                server_configs = {cfg.id: cfg for cfg in configs_result.scalars().all()}

            # 为每个文件添加jellyfin_web_url属性
            for file in files:
                if file.id in media_server_items:
                    item = media_server_items[file.id]
                    config = server_configs.get(item.media_server_config_id)
                    if config:
                        # 构建 base_url
                        protocol = "https" if config.use_ssl else "http"
                        base_url = f"{protocol}://{config.host}:{config.port}"
                        # 生成 web_url（Jellyfin/Emby 格式）
                        file.jellyfin_web_url = f"{base_url}/web/index.html#!/details?id={item.server_item_id}"
                    else:
                        file.jellyfin_web_url = None
                else:
                    file.jellyfin_web_url = None

        # 统计（防止 file_size 为 None 导致计算错误）
        total_files = len(files)
        total_size = sum(f.file_size or 0 for f in files)
        video_files = sum(1 for f in files if f.file_type == FILE_TYPE_VIDEO)
        identified_files = sum(1 for f in files if f.unified_resource_id is not None)

        return {
            "directory": directory,
            "files": files,
            "statistics": {
                "total_files": total_files,
                "total_size": total_size,
                "video_files": video_files,
                "identified_files": identified_files
            }
        }

    @staticmethod
    async def scan_root(
        db: AsyncSession, 
        base_directory: str,
        force: bool = False
    ) -> Dict[str, int]:
        """
        扫描媒体库目录 (代理到 MediaScannerService)
        
        Args:
            db: 数据库会话
            base_directory: 基础目录路径
            force: 是否强制重新扫描所有文件
            
        Returns:
            {"directories": int, "files": int}
        """
        from app.services.mediafile.scanner_service import MediaScannerService
        return await MediaScannerService.scan_root(db, base_directory, force=force)

    @staticmethod
    async def sync_from_files(db: AsyncSession, base_directory: str) -> Dict[str, int]:
        """
        (已弃用) 兼容旧接口，内部调用 scan_root
        """
        result = await MediaDirectoryService.scan_root(db, base_directory)
        # 适配旧返回格式
        return {"created": result.get("directories", 0), "updated": 0}

    @staticmethod
    async def _check_metadata_file(
        directory_path: str,
        extensions: any,
        check_parent: bool = False,
        is_season_dir: bool = False
    ) -> tuple[bool, Optional[str]]:
        """
        检查目录下是否存在元数据文件

        Args:
            directory_path: 目录路径
            extensions: 文件扩展名或扩展名列表
            check_parent: 是否检查父目录（用于季度目录查找剧集海报/背景图）
            is_season_dir: 是否为季度目录（用于特殊NFO命名检测）

        Returns:
            (是否存在, 文件路径)
        """
        if isinstance(extensions, str):
            extensions = [extensions]

        # 构建检测模式列表
        patterns = []
        dir_name = Path(directory_path).name

        for ext in extensions:
            # 如果扩展名以 "-" 开头（如 "-poster.jpg"），去掉前缀 "-" 后添加到模式
            if ext.startswith("-"):
                # 去掉前导 "-"，添加标准文件名和目录名前缀文件名
                clean_ext = ext[1:]  # 去掉 "-"，得到 "poster.jpg"
                patterns.append(clean_ext)  # 添加 "poster.jpg"
                patterns.append(f"{dir_name}-{clean_ext}")  # 添加 "目录名-poster.jpg"
            elif ext.startswith("."):
                # 扩展名（如 ".nfo"），直接添加目录名 + 扩展名
                patterns.append(f"{dir_name}{ext}")  # 添加 "目录名.nfo"
            else:
                # 普通文件名（如 "poster.jpg"），添加标准文件名和目录名前缀文件名
                patterns.append(ext)  # 添加 "poster.jpg"
                patterns.append(f"{dir_name}-{ext}")  # 添加 "目录名-poster.jpg"

        # 特殊处理：NFO 文件的标准命名
        if ".nfo" in extensions:
            if is_season_dir:
                # 季度目录：season.nfo, tvshow.nfo
                patterns.extend(["season.nfo", "tvshow.nfo"])
            else:
                # 电影/剧集根目录：movie.nfo, tvshow.nfo
                patterns.extend(["movie.nfo", "tvshow.nfo"])

        # 1. 检查当前目录
        for pattern in patterns:
            file_path = os.path.join(directory_path, pattern)
            if os.path.exists(file_path):
                return True, file_path

        # 2. 如果需要，检查父目录（用于季度目录的海报/背景图）
        if check_parent:
            parent_path = str(Path(directory_path).parent)
            if parent_path != directory_path:  # 确保不是根目录
                for pattern in patterns:
                    file_path = os.path.join(parent_path, pattern)
                    if os.path.exists(file_path):
                        return True, file_path

        return False, None

    @staticmethod
    def check_metadata_realtime(directory_path: str, season_number: Optional[int] = None) -> Dict[str, Any]:
        """
        实时检查目录的元数据文件是否存在
        """
        result = {
            "has_nfo": False,
            "nfo_path": None,
            "has_poster": False,
            "poster_path": None,
            "has_backdrop": False,
            "backdrop_path": None,
        }

        if not os.path.exists(directory_path):
            return result

        is_season = season_number is not None

        # 策略 1: 检查标准命名 (快速)
        nfo_candidates = []
        poster_candidates = []
        backdrop_candidates = []
        
        dir_name = Path(directory_path).name

        if is_season:
            parent_dir = str(Path(directory_path).parent)
            # NFO
            nfo_candidates.extend([
                os.path.join(parent_dir, "tvshow.nfo"),
                os.path.join(directory_path, "season.nfo"),
            ])
            # Poster
            for ext in [".jpg", ".png"]:
                poster_candidates.extend([
                    os.path.join(parent_dir, f"season{season_number:02d}-poster{ext}"),
                    os.path.join(directory_path, f"season-poster{ext}"),
                    os.path.join(directory_path, f"poster{ext}"),
                ])
            # Backdrop - 通常借用父目录
            for ext in [".jpg", ".png"]:
                backdrop_candidates.extend([
                    os.path.join(parent_dir, f"fanart{ext}"),
                    os.path.join(parent_dir, f"backdrop{ext}"),
                ])
        else:
            # Movie / TV Root
            nfo_candidates.extend([
                os.path.join(directory_path, "movie.nfo"),
                os.path.join(directory_path, "tvshow.nfo"),
                os.path.join(directory_path, f"{dir_name}.nfo"),
            ])
            for ext in [".jpg", ".png"]:
                poster_candidates.extend([
                    os.path.join(directory_path, f"poster{ext}"),
                    os.path.join(directory_path, f"folder{ext}"),
                    os.path.join(directory_path, f"{dir_name}-poster{ext}"),
                ])
                backdrop_candidates.extend([
                    os.path.join(directory_path, f"fanart{ext}"),
                    os.path.join(directory_path, f"backdrop{ext}"),
                    os.path.join(directory_path, f"{dir_name}-fanart{ext}"),
                ])

        # 执行标准检查
        for c in nfo_candidates:
            if os.path.exists(c):
                result["has_nfo"] = True
                result["nfo_path"] = c
                break
        
        for c in poster_candidates:
            if os.path.exists(c):
                result["has_poster"] = True
                result["poster_path"] = c
                break

        for c in backdrop_candidates:
            if os.path.exists(c):
                result["has_backdrop"] = True
                result["backdrop_path"] = c
                break

        # 策略 2: 如果标准检查失败，遍历目录查找 (慢但全面)
        # 只要还缺某项，就进行扫描
        if not (result["has_nfo"] and result["has_poster"] and result["has_backdrop"]):
            try:
                with os.scandir(directory_path) as it:
                    for entry in it:
                        if entry.is_file():
                            lower_name = entry.name.lower()
                            ext = Path(entry.name).suffix.lower()
                            
                            # 查找任意 NFO
                            if not result["has_nfo"] and ext == '.nfo':
                                result["has_nfo"] = True
                                result["nfo_path"] = entry.path

                            # 查找非标准海报 (folder.jpg 已在上面涵盖，这里查漏补缺)
                            if not result["has_poster"]:
                                if lower_name in ['poster.jpg', 'poster.png', 'folder.jpg', 'cover.jpg', 'cover.png']:
                                    result["has_poster"] = True
                                    result["poster_path"] = entry.path
                                elif lower_name.endswith('-poster.jpg') or lower_name.endswith('-poster.png'):
                                    result["has_poster"] = True
                                    result["poster_path"] = entry.path

                            # 查找非标准背景
                            if not result["has_backdrop"]:
                                if lower_name in ['backdrop.jpg', 'backdrop.png', 'fanart.jpg']:
                                    result["has_backdrop"] = True
                                    result["backdrop_path"] = entry.path
                                elif lower_name.endswith('-fanart.jpg') or lower_name.endswith('-fanart.png') or lower_name.endswith('-backdrop.jpg') or lower_name.endswith('-backdrop.png'):
                                    result["has_backdrop"] = True
                                    result["backdrop_path"] = entry.path
            except Exception:
                pass

        return result

    @staticmethod
    async def detect_issues(
        db: AsyncSession,
        directory_id: Optional[int] = None,
        media_type: Optional[str] = None
    ) -> Dict[str, int]:
        """
        检测目录问题并更新issue_flags

        Args:
            db: 数据库会话
            directory_id: 目录ID (None表示检测所有目录)
            media_type: 媒体类型 (None表示所有类型)

        Returns:
            {"missing_poster": 数量, "missing_nfo": 数量, ...}
        """
        import logging
        logger = logging.getLogger(__name__)

        # 查询目录
        query = select(MediaDirectory)
        if directory_id:
            query = query.where(MediaDirectory.id == directory_id)
        if media_type:
            query = query.where(MediaDirectory.media_type == media_type)

        result = await db.execute(query)
        directories = list(result.scalars().all())

        # 获取所有拥有子目录的目录ID集合 (即充当父目录的ID)
        # 用于判断一个目录是否为叶子节点
        parent_ids_stmt = select(MediaDirectory.parent_id).where(MediaDirectory.parent_id.is_not(None)).distinct()
        parent_ids_res = await db.execute(parent_ids_stmt)
        parent_directories = set(parent_ids_res.scalars().all())

        issue_counts = {
            ISSUE_TYPE_MISSING_POSTER: 0,
            ISSUE_TYPE_MISSING_NFO: 0,
            ISSUE_TYPE_UNIDENTIFIED: 0,
            ISSUE_TYPE_DUPLICATE: 0,
            ISSUE_TYPE_MISSING_FILES: 0,
        }

        for directory in directories:
            issues = {}

            # 实时检查元数据文件是否存在
            metadata = MediaDirectoryService.check_metadata_realtime(
                directory.directory_path,
                directory.season_number
            )

            # 检查缺少海报（只统计有文件的目录）
            if not metadata["has_poster"] and directory.total_files > 0:
                issues[ISSUE_TYPE_MISSING_POSTER] = True
                issue_counts[ISSUE_TYPE_MISSING_POSTER] += 1
                logger.info(f"Missing poster: {directory.directory_name} ({directory.directory_path})")

            # 检查缺少NFO（只统计有文件的目录）
            if not metadata["has_nfo"] and directory.total_files > 0:
                issues[ISSUE_TYPE_MISSING_NFO] = True
                issue_counts[ISSUE_TYPE_MISSING_NFO] += 1
                logger.info(f"Missing NFO: {directory.directory_name} ({directory.directory_path})")

            # 检查未识别（只统计有文件的目录）
            if not directory.unified_resource_id and directory.total_files > 0:
                issues[ISSUE_TYPE_UNIDENTIFIED] = True
                issue_counts[ISSUE_TYPE_UNIDENTIFIED] += 1

            # 检查缺少文件 (必须是非父目录，且真的没有文件)
            # 如果目录有子文件夹（即它是父目录），则不视为错误
            if directory.id not in parent_directories and directory.total_files == 0:
                issues[ISSUE_TYPE_MISSING_FILES] = True
                issue_counts[ISSUE_TYPE_MISSING_FILES] += 1

            # TODO: 检查重复文件(需要对比hash)

            directory.issue_flags = issues

        await db.commit()

        return issue_counts

    @staticmethod
    async def delete_by_id(db: AsyncSession, directory_id: int) -> bool:
        """删除目录记录"""
        directory = await MediaDirectoryService.get_by_id(db, directory_id)
        if not directory:
            return False

        await db.delete(directory)
        await db.commit()
        return True

    @staticmethod
    async def delete_orphaned_directories(db: AsyncSession, base_directory: str) -> int:
        """
        删除不存在的目录记录（级联删除目录下的文件和子目录）

        Args:
            db: 数据库会话
            base_directory: 基础目录路径

        Returns:
            删除的目录数量
        """
        import logging
        logger = logging.getLogger(__name__)

        base_directory = base_directory.replace('\\', '/')

        # 查询所有属于该扫描根目录下的目录记录
        result = await db.execute(
            select(MediaDirectory).where(
                MediaDirectory.directory_path.like(f"{base_directory}%")
            )
        )
        directories = list(result.scalars().all())

        # 筛选出磁盘上不存在的目录
        orphaned_dirs = [d for d in directories if not os.path.exists(d.directory_path)]
        if not orphaned_dirs:
            return 0

        # 收集所有孤立目录的ID和路径
        orphaned_ids = [d.id for d in orphaned_dirs]
        orphaned_paths = [d.directory_path for d in orphaned_dirs]

        # 先删除孤立目录下的文件记录
        for dir_path in orphaned_paths:
            await db.execute(
                delete(MediaFile).where(
                    or_(
                        MediaFile.media_directory_id.in_(orphaned_ids),
                        MediaFile.directory.like(f"{dir_path}%")
                    )
                )
            )

        # 再删除孤立目录记录（先删子目录再删父目录，按路径深度降序排列）
        orphaned_dirs.sort(key=lambda d: d.directory_path.count('/'), reverse=True)
        for directory in orphaned_dirs:
            await db.delete(directory)

        await db.commit()

        logger.info(f"清理孤立目录: {len(orphaned_dirs)} 个目录及其文件记录已删除")
        return len(orphaned_dirs)
