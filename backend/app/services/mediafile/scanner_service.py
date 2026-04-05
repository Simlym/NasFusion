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
                    await MediaScannerService._sync_files(db, directory.id, current_path, sorted_files, directory.media_type, directory.season_number)
                    stats["files"] += len(sorted_files)

                # 3.5 尝试从NFO自动识别关联（仅对季度目录且未关联的情况）
                if (directory.season_number is not None
                        and not directory.unified_resource_id
                        and nfo_file):
                    try:
                        await MediaScannerService._auto_identify_from_nfo(
                            db, directory, nfo_file
                        )
                    except Exception as e:
                        logger.warning(f"NFO自动识别失败: {current_path}, 错误: {e}")

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
        file_entries: List[os.DirEntry],
        media_type: Optional[str] = None,
        directory_season: Optional[int] = None
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
                await MediaScannerService._create_file(db, entry, directory_id, media_type, directory_season)
            else:
                 # 检查是否需要更新关联
                 f = db_file_map[name]
                 updated = False
                 if f.media_directory_id != directory_id:
                     f.media_directory_id = directory_id
                     f.directory = dir_path # 确保path也更新
                     updated = True

                 # 对已有但缺少识别信息的文件，尝试从原始文件继承
                 if not f.unified_resource_id:
                     source_file = await MediaScannerService._find_source_file(db, f.file_path)
                     if source_file:
                         f.media_type = source_file.media_type
                         f.unified_table_name = source_file.unified_table_name
                         f.unified_resource_id = source_file.unified_resource_id
                         f.match_method = source_file.match_method
                         f.match_confidence = source_file.match_confidence
                         f.season_number = source_file.season_number
                         f.episode_number = source_file.episode_number
                         f.episode_title = source_file.episode_title
                         f.resolution = source_file.resolution
                         f.video_codec = source_file.video_codec
                         f.organized = True
                         f.organized_path = f.file_path
                         f.organized_at = source_file.organized_at
                         f.organize_mode = source_file.organize_mode
                         if f.status == "discovered":
                             f.status = source_file.status if source_file.status in ("completed",) else "discovered"
                         updated = True
                         logger.info(
                             f"补全已有文件识别信息: {name} (id={f.id}) <- source_id={source_file.id}, "
                             f"unified={source_file.unified_table_name}:{source_file.unified_resource_id}"
                         )

                 if updated:
                     db.add(f)
        
        # 2. 找出消失的文件
        for name, file_obj in db_file_map.items():
            if name not in disk_files:
                # 文件不存在了，删除
                await db.delete(file_obj)

    @staticmethod
    async def _create_file(db: AsyncSession, entry: os.DirEntry, directory_id: int, media_type: Optional[str] = None, directory_season: Optional[int] = None):
        """创建单个文件记录

        如果该文件是某个已有文件整理（硬链接/reflink等）后的产物，
        则自动继承原始文件的识别信息（媒体类型、统一资源关联、季集号等）。
        对于没有源文件的视频文件，使用guessit从文件名解析季集号和分辨率。
        """
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
            media_type=media_type or "unknown",
            extension=ext,
            modified_at=datetime.fromtimestamp(stat.st_mtime),
            status="discovered", # 默认状态
            organized=False
        )

        # 检查是否存在以该路径为 organized_path 的原始文件，继承其识别信息
        source_file = await MediaScannerService._find_source_file(db, file_path)
        if source_file:
            media_file.media_type = source_file.media_type
            media_file.unified_table_name = source_file.unified_table_name
            media_file.unified_resource_id = source_file.unified_resource_id
            media_file.match_method = source_file.match_method
            media_file.match_confidence = source_file.match_confidence
            media_file.season_number = source_file.season_number
            media_file.episode_number = source_file.episode_number
            media_file.episode_title = source_file.episode_title
            media_file.resolution = source_file.resolution
            media_file.video_codec = source_file.video_codec
            media_file.organized = True
            media_file.organized_path = file_path
            media_file.organized_at = source_file.organized_at
            media_file.organize_mode = source_file.organize_mode
            media_file.status = source_file.status if source_file.status in ("completed",) else "discovered"
            logger.info(
                f"继承原始文件识别信息: {entry.name} <- source_id={source_file.id}, "
                f"unified={source_file.unified_table_name}:{source_file.unified_resource_id}"
            )
        elif file_type == FILE_TYPE_VIDEO:
            # 没有源文件的视频，使用guessit从文件名解析季集号
            await MediaScannerService._parse_filename_info(media_file, entry.name, directory_season)

        db.add(media_file)

    @staticmethod
    async def _parse_filename_info(media_file: MediaFile, filename: str, directory_season: Optional[int] = None):
        """
        使用guessit从文件名解析季集号和分辨率等信息

        优先级：目录季号作为兜底，文件名解析的季号优先。

        Args:
            media_file: 媒体文件对象（原地修改）
            filename: 文件名
            directory_season: 目录解析出的季号
        """
        from app.services.common.filename_parser_service import FilenameParserService

        if not FilenameParserService.is_available():
            # guessit未安装，仅使用目录季号
            if directory_season:
                media_file.season_number = directory_season
            return

        try:
            parsed = FilenameParserService.parse_media_file(media_file.file_path)

            # 季号：文件名解析优先，否则用目录季号
            if parsed.get("season"):
                media_file.season_number = parsed["season"]
            elif directory_season:
                media_file.season_number = directory_season

            # 集号
            if parsed.get("episode"):
                media_file.episode_number = parsed["episode"]

            # 集标题
            if parsed.get("episode_title"):
                media_file.episode_title = parsed["episode_title"]

            # 分辨率
            if parsed.get("resolution") and not media_file.resolution:
                media_file.resolution = parsed["resolution"]

            # 如果解析出了媒体类型，更新
            if parsed.get("type") and media_file.media_type == "unknown":
                media_file.media_type = FilenameParserService.guess_media_type(parsed)

            # 标记识别方式
            if parsed.get("season") or parsed.get("episode"):
                media_file.match_method = "from_filename"

            logger.debug(
                f"文件名解析: {filename} -> S{media_file.season_number}E{media_file.episode_number}, "
                f"resolution={media_file.resolution}"
            )

        except Exception as e:
            logger.warning(f"文件名解析失败: {filename}, 错误: {e}")
            # 降级：仅使用目录季号
            if directory_season:
                media_file.season_number = directory_season

    @staticmethod
    async def _find_source_file(db: AsyncSession, file_path: str) -> Optional[MediaFile]:
        """
        查找以 file_path 为 organized_path 的原始文件

        当目录扫描发现一个新文件时，检查该文件是否是某个已有文件
        通过整理（硬链接/reflink/copy等）产生的副本。

        Args:
            db: 数据库会话
            file_path: 新发现文件的路径

        Returns:
            原始文件对象，如果没有匹配则返回 None
        """
        stmt = select(MediaFile).where(
            MediaFile.organized_path == file_path,
            MediaFile.organized == True,
            MediaFile.unified_resource_id.isnot(None),
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    def _convert_date_fields(data: dict) -> dict:
        """
        将字典中的日期字符串转换为 Python date 对象（兼容 SQLite）

        SQLite Date 类型只接受 Python date 对象，不接受字符串。
        TMDB API 返回的 first_air_date / last_air_date 是 "YYYY-MM-DD" 格式的字符串。

        Args:
            data: 包含可能为字符串日期的字典

        Returns:
            转换后的字典（原地修改并返回）
        """
        for field in ("first_air_date", "last_air_date"):
            val = data.get(field)
            if isinstance(val, str):
                try:
                    data[field] = datetime.strptime(val, "%Y-%m-%d").date()
                except (ValueError, TypeError):
                    data[field] = None
            elif val is not None and not isinstance(val, type(None)):
                # 不是字符串也不是None，尝试转换
                try:
                    data[field] = datetime.strptime(str(val)[:10], "%Y-%m-%d").date()
                except (ValueError, TypeError):
                    data[field] = None
        return data

    @staticmethod
    async def _auto_identify_from_nfo(
        db: AsyncSession,
        directory: MediaDirectory,
        nfo_path: str,
    ):
        """
        从NFO文件自动识别并关联季度目录

        策略：
        1. 解析NFO中的TMDB ID，如果有则直接关联
        2. 如果NFO无TMDB ID，尝试用NFO标题+目录名搜索TMDB自动匹配

        Args:
            db: 数据库会话
            directory: 目录对象（季度目录）
            nfo_path: NFO文件路径
        """
        from app.services.mediafile.nfo_parser_service import NFOParserService
        from app.models.unified_tv_series import UnifiedTVSeries
        from app.constants import UNIFIED_TABLE_TV

        nfo_data = await NFOParserService.parse_nfo(nfo_path)
        if not nfo_data:
            return

        tmdb_id = None
        media_type = "tv"  # 季度目录默认为TV

        # 1. 优先使用NFO中的TMDB ID
        raw_tmdb_id = nfo_data.get("tmdb_id")
        if raw_tmdb_id:
            try:
                tmdb_id = int(raw_tmdb_id)
            except (ValueError, TypeError):
                pass

        if tmdb_id:
            # 直接用TMDB ID关联
            try:
                unified_table = UNIFIED_TABLE_TV
                existing = await db.execute(
                    select(UnifiedTVSeries).where(UnifiedTVSeries.tmdb_id == tmdb_id)
                )
                unified = existing.scalar_one_or_none()

                if not unified:
                    # 尝试从TMDB获取详情并创建
                    from app.services.identification.media_identify_service import media_identify_service
                    tmdb_adapter = await media_identify_service._get_tmdb_adapter(db)
                    tmdb_detail = await tmdb_adapter.get_tv_details(tmdb_id)
                    if tmdb_detail:
                        MediaScannerService._convert_date_fields(tmdb_detail)
                        unified = UnifiedTVSeries(tmdb_id=tmdb_id, **{
                            k: v for k, v in tmdb_detail.items()
                            if k != "tmdb_id" and hasattr(UnifiedTVSeries, k)
                        })
                        db.add(unified)
                        await db.flush()

                if unified:
                    directory.unified_table_name = unified_table
                    directory.unified_resource_id = unified.id
                    if hasattr(unified, 'title') and unified.title:
                        directory.series_name = unified.title
                    # 同时更新该目录下所有文件
                    await MediaScannerService._link_directory_files(
                        db, directory.id, unified_table, unified.id, media_type
                    )
                    logger.info(
                        f"NFO自动识别成功(TMDB ID): {directory.directory_path} -> "
                        f"{unified.title} (TMDB: {tmdb_id})"
                    )
                    return
            except Exception as e:
                logger.warning(f"NFO TMDB ID关联失败: {e}")

        # 2. NFO无TMDB ID，尝试用名称搜索
        title = nfo_data.get("title") or directory.directory_name
        if not title:
            return

        try:
            from app.services.identification.media_identify_service import media_identify_service
            candidates = await media_identify_service.search_and_get_candidates(
                db, title, media_type=media_type
            )

            if not candidates:
                logger.debug(f"NFO名称搜索无结果: {title}")
                return

            # 只有唯一结果时自动匹配
            if len(candidates) == 1:
                best = candidates[0]
            else:
                # 多个结果时尝试精确匹配标题
                best = None
                title_lower = title.lower().strip()
                for c in candidates:
                    c_title = (c.get("title") or "").lower().strip()
                    c_orig = (c.get("original_title") or "").lower().strip()
                    if title_lower == c_title or title_lower == c_orig:
                        best = c
                        break

            if not best:
                logger.debug(
                    f"NFO名称搜索有{len(candidates)}个结果，无法自动匹配，等待用户选择: {title}"
                )
                return

            match_tmdb_id = best.get("tmdb_id")
            if not match_tmdb_id:
                return

            unified_table = UNIFIED_TABLE_TV
            existing = await db.execute(
                select(UnifiedTVSeries).where(UnifiedTVSeries.tmdb_id == match_tmdb_id)
            )
            unified = existing.scalar_one_or_none()

            if not unified:
                tmdb_adapter = await media_identify_service._get_tmdb_adapter(db)
                tmdb_detail = await tmdb_adapter.get_tv_details(match_tmdb_id)
                if tmdb_detail:
                    MediaScannerService._convert_date_fields(tmdb_detail)
                    unified = UnifiedTVSeries(tmdb_id=match_tmdb_id, **{
                        k: v for k, v in tmdb_detail.items()
                        if k != "tmdb_id" and hasattr(UnifiedTVSeries, k)
                    })
                    db.add(unified)
                    await db.flush()

            if unified:
                directory.unified_table_name = unified_table
                directory.unified_resource_id = unified.id
                if hasattr(unified, 'title') and unified.title:
                    directory.series_name = unified.title
                await MediaScannerService._link_directory_files(
                    db, directory.id, unified_table, unified.id, media_type
                )
                logger.info(
                    f"NFO自动识别成功(名称搜索): {directory.directory_path} -> "
                    f"{unified.title} (TMDB: {match_tmdb_id})"
                )
        except Exception as e:
            logger.warning(f"NFO名称搜索匹配失败: {title}, 错误: {e}")

    @staticmethod
    async def _link_directory_files(
        db: AsyncSession,
        directory_id: int,
        unified_table: str,
        unified_resource_id: int,
        media_type: str,
    ):
        """将目录下所有文件关联到统一资源"""
        stmt = select(MediaFile).where(MediaFile.media_directory_id == directory_id)
        files_result = await db.execute(stmt)
        files = files_result.scalars().all()
        for f in files:
            if not f.unified_resource_id:
                f.unified_table_name = unified_table
                f.unified_resource_id = unified_resource_id
                if f.media_type in ("unknown", None):
                    f.media_type = media_type

