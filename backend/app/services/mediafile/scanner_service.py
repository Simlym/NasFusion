# -*- coding: utf-8 -*-
"""
媒体扫描服务
基于os.scandir实现的高性能文件扫描
支持增量扫描(基于mtime)
"""
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from sqlalchemy import select, update, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models import MediaDirectory, MediaFile
from app.utils.timezone import now
from app.constants import (
    MEDIA_TYPE_MOVIE,
    MEDIA_TYPE_TV,
    FILE_TYPE_VIDEO,
    FILE_TYPE_SUBTITLE,
    FILE_TYPE_AUDIO,
    FILE_TYPE_OTHER,
    VIDEO_EXTENSIONS,
    SUBTITLE_EXTENSIONS,
    AUDIO_EXTENSIONS,
)

logger = logging.getLogger(__name__)

# Synology/QNAP/其他 NAS 系统目录排除列表
# 这些目录用于存储缩略图、索引、回收站等系统数据，不应被媒体库扫描
EXCLUDED_DIRECTORIES = {
    '@eaDir',           # Synology Extended Attributes (缩略图、索引)
    '@tmp',             # Synology 临时目录
    '#recycle',         # Synology/QNAP 回收站
    '.@__thumb',        # QNAP 缩略图
    '@Recycle',         # QNAP 回收站
    '.DS_Store',        # macOS 系统文件
    'Thumbs.db',        # Windows 缩略图缓存
    '@Recently-Snapshot',  # Synology 快照
    '@sharebin',        # Synology 共享回收站
}

# 蓝光原盘内部目录（不扫描其中的文件，由整理时统一处理）
BLURAY_INTERNAL_DIRECTORIES = {
    'BDMV',             # 蓝光原盘主目录
    'CERTIFICATE',      # 蓝光证书目录
}

# 需要排除的目录名前缀
EXCLUDED_PREFIXES = (
    'SYNO@',            # Synology 系统文件 (如 SYNO@.fileindexdb)
    '@',                # 所有以 @ 开头的目录 (Synology系统目录)
    '#',                # 所有以 # 开头的目录 (回收站等)
)


class MediaScannerService:
    """媒体扫描服务 - V2架构核心"""

    @staticmethod
    def _should_skip_entry(name: str) -> bool:
        """
        检查是否应该跳过该目录/文件

        Args:
            name: 文件或目录名

        Returns:
            True 表示应该跳过，False 表示应该处理
        """
        # 跳过隐藏文件/目录（以 . 开头）
        if name.startswith('.'):
            return True

        # 跳过已知的系统目录
        if name in EXCLUDED_DIRECTORIES:
            return True

        # 跳过以特定前缀开头的目录
        if name.startswith(EXCLUDED_PREFIXES):
            return True

        return False

    @staticmethod
    def _is_bluray_internal_dir(name: str) -> bool:
        """
        检查是否为蓝光原盘内部目录（BDMV/CERTIFICATE）

        这些目录下的文件不应该被单独扫描入库，
        而是在整理时作为一个整体处理

        Args:
            name: 目录名

        Returns:
            True 表示是蓝光内部目录
        """
        return name.upper() in BLURAY_INTERNAL_DIRECTORIES or name in BLURAY_INTERNAL_DIRECTORIES

    @staticmethod
    async def scan_root(
        db: AsyncSession, 
        root_path: str, 
        media_type: Optional[str] = None,
        force: bool = False
    ) -> Dict[str, int]:
        """
        扫描根目录
        
        Args:
            db: 数据库会话
            root_path: 根目录路径
            media_type: 媒体类型 (movie/tv)
            force: 是否强制全量扫描 (忽略mtime)
            
        Returns:
            统计信息 {"directories_created": int, "directories_updated": int, "files": int}
        """
        stats = {"directories_created": 0, "directories_updated": 0, "files": 0}
        
        root = Path(root_path)
        if not root.exists() or not root.is_dir():
            logger.error(f"扫描路径不存在: {root_path}")
            return stats

        # 1. 规范化路径
        root_path = root.resolve().as_posix()
        
        logger.info(f"开始扫描目录(模式={'全量' if force else '增量'}): {root_path}")
        
        # 2. 递归扫描
        await MediaScannerService._scan_recursive(
            db, root_path, None, media_type, force, stats
        )
        
        return stats

    @staticmethod
    async def _scan_recursive(
        db: AsyncSession,
        current_path: str,
        parent_id: Optional[int],
        media_type: Optional[str],
        force: bool,
        stats: Dict[str, int]
    ):
        """递归扫描目录"""
        try:
            # 获取当前目录的mtime
            current_stat = os.stat(current_path)
            current_mtime = int(current_stat.st_mtime)
            dir_name = os.path.basename(current_path)

            # 1. 处理目录记录
            directory, upsert_status = await MediaScannerService._upsert_directory(
                db, current_path, dir_name, parent_id, media_type, current_mtime
            )
            
            # 统计目录创建/更新
            if upsert_status == 'created':
                stats["directories_created"] += 1
            elif upsert_status == 'updated':
                stats["directories_updated"] += 1
            # 'unchanged' 不计数
            
            # 如果是增量扫描，且mtime未变，且已经扫描过，则检查是否可以直接跳过子树
            # 注意: 如果子目录被修改，父目录mtime通常也会变，但也有一致性风险
            # 策略：如果目录本身没变，我们仍然需要进去看子目录，因为底层文件变动可能不冒泡到顶层
            # 但我们可以跳过"文件扫描"步骤如果该目录被标记为"干净"
            # 为了最稳妥，我们暂时不依赖父目录跳过子目录，而是每个目录都检查自己的mtime
            
            should_scan_files = True
            if not force and directory.scanned_at and directory.source_mtime == current_mtime:
                # 目录未变，跳过文件扫描？
                # 只有当所有的子目录和文件都没有变动时才安全。
                # TMM逻辑：如果目录mtime没变，则文件列表没变。
                # 这是一个强假设，但用于媒体库通常是够的。
                should_scan_files = False
                logger.debug(f"跳过未变更目录: {current_path}")

            if should_scan_files or force:
                # 扫描当前目录下的条目
                with os.scandir(current_path) as it:
                    entries = list(it)
                
                # 分离文件和子目录
                # 2. 收集文件并区分类型用于元数据检查
                disk_files = [] # 所有文件的DirEntry
                sorted_files = [] # 仅媒体文件(需要入库的)
                
                nfo_file = None
                poster_file = None
                backdrop_file = None
                
                subdirs = [] # Initialize subdirs list
                
                for entry in entries:
                    # 跳过系统目录和隐藏文件 (@eaDir, #recycle, .开头等)
                    if MediaScannerService._should_skip_entry(entry.name): 
                        continue
                    if entry.is_file():
                        disk_files.append(entry)
                        ext = Path(entry.name).suffix.lower()
                        
                        # 检查元数据文件
                        lower_name = entry.name.lower()
                        if ext == '.nfo':
                            nfo_file = entry.path
                        elif lower_name in ['poster.jpg', 'poster.png', 'folder.jpg']:
                            poster_file = entry.path
                        elif lower_name in ['backdrop.jpg', 'backdrop.png', 'fanart.jpg']:
                            backdrop_file = entry.path
                        
                        # 筛选需要入库的媒体文件
                        if (ext in VIDEO_EXTENSIONS or 
                            ext in SUBTITLE_EXTENSIONS or 
                            ext in AUDIO_EXTENSIONS):
                            sorted_files.append(entry)
                            
                    elif entry.is_dir():
                        # 跳过蓝光原盘内部目录（BDMV/CERTIFICATE）
                        # 这些目录下的文件在整理时作为整体处理，不需要单独入库
                        if MediaScannerService._is_bluray_internal_dir(entry.name):
                            logger.debug(f"跳过蓝光原盘内部目录: {entry.path}")
                            continue
                        # 只添加非系统目录到子目录列表
                        subdirs.append(entry)

                # 更新目录元数据状态
                has_changes = False
                if nfo_file and (not directory.has_nfo or directory.nfo_path != nfo_file):
                    directory.has_nfo = True
                    directory.nfo_path = str(nfo_file).replace('\\', '/')
                    has_changes = True
                if poster_file and (not directory.has_poster or directory.poster_path != poster_file):
                    directory.has_poster = True
                    directory.poster_path = str(poster_file).replace('\\', '/')
                    has_changes = True
                if backdrop_file and (not directory.has_backdrop or directory.backdrop_path != backdrop_file):
                    directory.has_backdrop = True
                    directory.backdrop_path = str(backdrop_file).replace('\\', '/')
                    has_changes = True
                
                if has_changes:
                    # 提交元数据变更
                    db.add(directory)
                    await db.flush()

                # 3. 处理文件同步
                if sorted_files:
                    await MediaScannerService._sync_files(db, directory.id, current_path, sorted_files)
                    stats["files"] += len(sorted_files)
                
                # 更新统计信息
                directory.scanned_at = now()
                directory.total_files = len(sorted_files)
                await db.commit()
                
                # 4. 递归处理子目录
                for subdir in subdirs:
                    await MediaScannerService._scan_recursive(
                        db, subdir.path, directory.id, media_type, force, stats
                    )
            else:
                # 即使跳过了文件扫描，也要递归检查子目录
                with os.scandir(current_path) as it:
                    for entry in it:
                        # 跳过系统目录、隐藏文件和蓝光内部目录
                        if entry.is_dir() and not MediaScannerService._should_skip_entry(entry.name):
                            # 跳过蓝光原盘内部目录
                            if MediaScannerService._is_bluray_internal_dir(entry.name):
                                continue
                            await MediaScannerService._scan_recursive(
                                db, entry.path, directory.id, media_type, force, stats
                            )
            
        except PermissionError:
            logger.warning(f"没有权限扫描目录: {current_path}")
        except Exception as e:
            logger.exception(f"扫描目录出错: {current_path}")

    @staticmethod
    async def _upsert_directory(
        db: AsyncSession,
        path: str,
        name: str,
        parent_id: Optional[int],
        media_type: Optional[str],
        mtime: int
    ) -> Tuple[MediaDirectory, str]:
        """更新或插入目录记录，返回 (目录对象, 状态)
        
        状态: 'created' | 'updated' | 'unchanged'
        """
        # 标准化路径
        path = path.replace('\\', '/')
        
        stmt = select(MediaDirectory).where(MediaDirectory.directory_path == path)
        result = await db.execute(stmt)
        directory = result.scalar_one_or_none()

        if directory:
            # 更新
            updated = False
            if directory.source_mtime != mtime:
                directory.source_mtime = mtime
                updated = True
            
            # 修复层级关系：如果parent_id不匹配（例如目录移动了），更新它
            # 注意：只有当传入的parent_id不仅是None时才更新，或者我们确信当前是根扫描
            if parent_id is not None and directory.parent_id != parent_id:
                directory.parent_id = parent_id
                updated = True
            
            # 尝试解析季号 (如果没有)
            if directory.season_number is None:
                import re
                match = re.search(r'(?:Season|S)\s*(\d+)', name, re.IGNORECASE)
                if match:
                    directory.season_number = int(match.group(1))
                    updated = True

            if updated:
                db.add(directory)
                await db.flush()
                return directory, 'updated'
            return directory, 'unchanged'  # 已存在且无变化
        else:
            # 解析季号
            import re
            season_number = None
            match = re.search(r'(?:Season|S)\s*(\d+)', name, re.IGNORECASE)
            if match:
                season_number = int(match.group(1))

            # 插入
            directory = MediaDirectory(
                directory_path=path,
                directory_name=name,
                parent_id=parent_id,
                media_type=media_type,
                source_mtime=mtime,
                season_number=season_number,
                created_at=now()
            )
            db.add(directory)
            await db.flush()
            return directory, 'created'

    @staticmethod
    async def _sync_files(
        db: AsyncSession,
        directory_id: int,
        dir_path: str,
        file_entries: List[os.DirEntry]
    ):
        """同步目录下的文件：添加新文件，标记丢失文件"""
        
        # 标准化路径
        dir_path = dir_path.replace('\\', '/')

        # 构造当前磁盘上的文件映射 {filename: entry}
        disk_files = {}
        for entry in file_entries:
            disk_files[entry.name] = entry

        # 查询数据库中该目录下的文件
        # 必须使用 directory_id 强关联，或者 directory 路径匹配
        # 为了准确性，优先使用 media_directory_id
        # 查询数据库中该目录下的文件
        # 必须使用 directory_id 强关联，或者 directory 路径匹配
        # 为了准确性，优先使用 media_directory_id
        # 使用 or_ 同时查询 ID 和 路径，防止因 ID 缺失或不一致导致的重复插入
        stmt = select(MediaFile).where(
            or_(
                MediaFile.media_directory_id == directory_id,
                MediaFile.directory == dir_path
            )
        )
        result = await db.execute(stmt)
        db_files = result.scalars().all()

        db_file_map = {f.file_name: f for f in db_files}
        
        # 1. 找出新增的文件
        for name, entry in disk_files.items():
            if name not in db_file_map:
                # 新增文件
                await MediaScannerService._create_file(db, entry, directory_id)
            else:
                 # 检查是否需要更新关联
                 f = db_file_map[name]
                 if f.media_directory_id != directory_id:
                     f.media_directory_id = directory_id
                     f.directory = dir_path # 确保path也更新
                     db.add(f)
        
        # 2. 找出消失的文件
        for name, file_obj in db_file_map.items():
            if name not in disk_files:
                # 文件不存在了，删除
                await db.delete(file_obj)

    @staticmethod
    async def _create_file(db: AsyncSession, entry: os.DirEntry, directory_id: int):
        """创建单个文件记录"""
        from app.utils.file_operations import get_file_type
        
        ext = Path(entry.name).suffix.lower()
        stat = entry.stat()
        
        file_type = "other"
        if ext in VIDEO_EXTENSIONS: file_type = FILE_TYPE_VIDEO
        elif ext in SUBTITLE_EXTENSIONS: file_type = FILE_TYPE_SUBTITLE
        elif ext in AUDIO_EXTENSIONS: file_type = FILE_TYPE_AUDIO
        
        # 统一路径分隔符
        file_path = entry.path.replace('\\', '/')
        directory_path = os.path.dirname(entry.path).replace('\\', '/')
        
        media_file = MediaFile(
            file_path=file_path,
            file_name=entry.name,
            directory=directory_path,
            media_directory_id=directory_id,
            file_size=stat.st_size,
            file_type=file_type,
            extension=ext,
            modified_at=datetime.fromtimestamp(stat.st_mtime),
            status="discovered", # 默认状态
            organized=False
        )
        db.add(media_file)

