# -*- coding: utf-8 -*-
"""
媒体文件服务
管理媒体文件的CRUD、扫描、识别等操作
"""
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.constants import (
    FILE_TYPE_VIDEO,
    MATCH_METHOD_FROM_DOWNLOAD,
    MATCH_METHOD_FROM_FILENAME,
    MATCH_METHOD_NONE,
    MEDIA_FILE_STATUS_DISCOVERED,
    MEDIA_FILE_STATUS_IDENTIFIED,
    MEDIA_FILE_STATUS_IDENTIFYING,
    MEDIA_TYPE_ADULT,
    MEDIA_TYPE_ANIME,
    MEDIA_TYPE_MOVIE,
    MEDIA_TYPE_TV,
    UNIFIED_TABLE_ADULT,
    UNIFIED_TABLE_MOVIES,
    UNIFIED_TABLE_TV,
)

# 预览/样本视频的关键词（用于过滤）
SAMPLE_KEYWORDS = ["sample", "trailer", "preview", "预告", "featurette", "extra", "bonus"]
from app.models.download_task import DownloadTask
from app.models.media_file import MediaFile
from app.models.pt_resource import PTResource
from app.utils.file_operations import (
    find_files_in_directory,
    get_file_size,
    get_file_type,
    is_video_file,
)
from app.utils.timezone import now

logger = logging.getLogger(__name__)


def normalize_path(path: str | Path) -> str:
    """
    规范化路径为统一格式
    - 统一使用正斜杠
    - 添加 ./ 前缀（如果是相对路径）
    - 移除多余的斜杠

    Args:
        path: 原始路径

    Returns:
        规范化后的路径字符串
    """
    # 转换为 Path 对象
    p = Path(path) if not isinstance(path, Path) else path

    # 转换为 POSIX 风格路径（正斜杠）
    normalized = p.as_posix()

    # 如果是相对路径且不以 ./ 开头，添加 ./
    if not p.is_absolute() and not normalized.startswith('./'):
        normalized = './' + normalized

    return normalized


class MediaFileService:
    """媒体文件服务"""

    @staticmethod
    async def get_by_id(db: AsyncSession, file_id: int) -> Optional[MediaFile]:
        """
        根据ID获取媒体文件

        Args:
            db: 数据库会话
            file_id: 文件ID

        Returns:
            媒体文件对象，不存在返回None
        """
        result = await db.execute(select(MediaFile).where(MediaFile.id == file_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_path(db: AsyncSession, file_path: str) -> Optional[MediaFile]:
        """
        根据文件路径获取媒体文件

        Args:
            db: 数据库会话
            file_path: 文件路径

        Returns:
            媒体文件对象，不存在返回None
        """
        result = await db.execute(select(MediaFile).where(MediaFile.file_path == file_path))
        return result.scalar_one_or_none()

    @staticmethod
    async def list(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
        media_type: Optional[str] = None,
        file_type: Optional[str] = "video",
        organized: Optional[bool] = None,
        download_task_id: Optional[int] = None,
        directory: Optional[str] = None,
        resolution: Optional[str] = None,
        mount_type: Optional[str] = None,
        exclude_samples: bool = True,
    ) -> Dict:
        """
        查询媒体文件列表

        Args:
            db: 数据库会话
            skip: 跳过数量
            limit: 返回数量
            status: 文件状态过滤
            media_type: 媒体类型过滤
            file_type: 文件类型过滤（video/subtitle/audio/other），默认只显示视频
            organized: 是否已整理过滤
            download_task_id: 下载任务ID过滤
            directory: 目录前缀过滤
            resolution: 分辨率过滤
            mount_type: 按挂载点类型过滤 (如: download)
            exclude_samples: 是否排除预览/样本视频（默认True）

        Returns:
            包含total和items的字典
        """
        from sqlalchemy import and_, not_

        query = select(MediaFile).options(
            selectinload(MediaFile.download_task).selectinload(DownloadTask.pt_resource),
            selectinload(MediaFile.download_task).selectinload(DownloadTask.organize_config),
            selectinload(MediaFile.download_task).selectinload(DownloadTask.storage_mount)
        )

        # 添加过滤条件
        if status:
            query = query.where(MediaFile.status == status)
        if media_type:
            query = query.where(MediaFile.media_type == media_type)
        # 文件类型过滤（默认只显示视频）
        if file_type:
            query = query.where(MediaFile.file_type == file_type)
        if organized is not None:
            query = query.where(MediaFile.organized == organized)
        if download_task_id:
            query = query.where(MediaFile.download_task_id == download_task_id)

        # 排除预览/样本视频
        if exclude_samples and file_type == FILE_TYPE_VIDEO:
            sample_conditions = []
            for keyword in SAMPLE_KEYWORDS:
                sample_conditions.append(func.lower(MediaFile.file_name).contains(keyword.lower()))
            if sample_conditions:
                query = query.where(not_(or_(*sample_conditions)))

        # 如果指定了挂载点类型，获取所有该类型的目录
        if mount_type:
            from app.models.storage_mount import StorageMount
            stmt = select(StorageMount.container_path).where(StorageMount.mount_type == mount_type)
            result = await db.execute(stmt)
            mount_paths = [r for r in result.scalars().all()]
            
            if mount_paths:
                mount_patterns = []
                for path in mount_paths:
                    normalized = normalize_path(path)
                    plain = normalized.lstrip('./')
                    mount_patterns.append(MediaFile.directory.ilike(f"{normalized}%"))
                    mount_patterns.append(MediaFile.directory.ilike(f"{plain}%"))
                    mount_patterns.append(MediaFile.file_path.ilike(f"{normalized}%"))
                    mount_patterns.append(MediaFile.file_path.ilike(f"{plain}%"))
                
                query = query.where(or_(*mount_patterns))
            else:
                # 如果指定了类型但没找到挂载点，返回空结果
                return {"total": 0, "items": []}

        if directory:
            # 1. 基础归一化：使用与存储时相同的逻辑（转为正斜杠，处理相对路径）
            normalized_dir = normalize_path(directory)
            
            # 2. 进一步提取不带 ./ 前缀的版本，增加匹配成功率
            plain_dir = normalized_dir.lstrip('./')

            # 构建多种可能的路径匹配模式
            patterns = []

            # 匹配正斜杠版本 (数据库中存储的标准格式)
            patterns.append(MediaFile.directory.ilike(f"{normalized_dir}%"))
            patterns.append(MediaFile.directory.ilike(f"{plain_dir}%"))
            
            # 同时也尝试匹配原始输入的目录（保留反斜杠等原样）
            patterns.append(MediaFile.directory.ilike(f"{directory}%"))

            # 3. 针对 Windows 风格（反斜杠）进行显式构建匹配
            windows_dir = plain_dir.replace('/', '\\')
            patterns.append(MediaFile.directory.ilike(f"{windows_dir}%"))
            
            # 4. 同时匹配文件完整路径
            patterns.append(MediaFile.file_path.ilike(f"{normalized_dir}%"))
            patterns.append(MediaFile.file_path.ilike(f"{plain_dir}%"))
            patterns.append(MediaFile.file_path.ilike(f"{directory}%"))
            patterns.append(MediaFile.file_path.ilike(f"{windows_dir}%"))

            # 5. 宽泛匹配兜底：如果包含 data/downloads，尝试模糊匹配
            if 'data/downloads' in plain_dir.lower() or 'data\\downloads' in directory.lower():
                patterns.append(MediaFile.directory.ilike("%data/downloads%"))
                patterns.append(MediaFile.directory.ilike("%data\\downloads%"))
                patterns.append(MediaFile.file_path.ilike("%data/downloads%"))
                patterns.append(MediaFile.file_path.ilike("%data\\downloads%"))

            # 应用所有条件 (OR 关系)
            query = query.where(or_(*patterns))
        if resolution:
            query = query.where(MediaFile.resolution == resolution)

        # 统计总数
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar_one()

        # 分页查询
        query = query.order_by(MediaFile.discovered_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        items = result.scalars().all()

        return {"total": total, "items": items}

    @staticmethod
    async def create_from_download_task(
        db: AsyncSession, download_task: DownloadTask
    ) -> List[MediaFile]:
        """
        从下载任务创建媒体文件记录

        Args:
            db: 数据库会话
            download_task: 下载任务

        Returns:
            创建的媒体文件列表
        """
        if not download_task.save_path:
            logger.error(f"下载任务 {download_task.id} 没有保存路径")
            return []

        save_path = Path(download_task.save_path)
        if not save_path.exists():
            logger.error(f"下载路径不存在: {save_path}")
            return []

        media_files = []

        try:
            # 加载 PT 资源（如果有）
            pt_resource = None
            if download_task.pt_resource_id:
                pt_resource = await db.get(PTResource, download_task.pt_resource_id)
                if pt_resource:
                    logger.debug(f"加载PT资源: {pt_resource.title}, tv_info: {pt_resource.tv_info is not None}")

            # 策略：通过解析种子文件获取确切的文件列表
            # 避免扫描整个目录导致误关联无关文件
            target_files = []
            
            # 1. 尝试解析种子文件
            torrent_path = Path(download_task.torrent_file_path) if download_task.torrent_file_path else None
            if torrent_path and torrent_path.exists():
                try:
                    import bencodepy
                    torrent_data = bencodepy.decode_from_file(str(torrent_path))
                    info = torrent_data[b'info']
                    
                    # 多文件种子
                    if b'files' in info:
                        # 获取根目录名 (info['name'])
                        root_name = info[b'name'].decode('utf-8', errors='ignore')
                        for f in info[b'files']:
                            # 路径是列表形式，如 ['dir', 'subdir', 'file.ext']
                            path_parts = [p.decode('utf-8', errors='ignore') for p in f[b'path']]
                            # 完整相对路径
                            rel_path = Path(root_name).joinpath(*path_parts)
                            # 绝对路径 = save_path (通常是下载根目录) + 相对路径
                            # 注意：download_task.save_path 通常指向包含 root_name 的目录，或者是 root_name 本身？
                            # qBittorrent保存路径逻辑：save_path 参数是下载内容的父目录。
                            # 所以文件绝对路径应该是: save_path / rel_path
                            # 但有时候 save_path 已经包含了 root_name (如果是单文件或者用户指定了具体目录)
                            
                            # 这里比较棘手，因为 save_path 的语义取决于下载器和用户设置。
                            # qBittorrent: save_path 是 "Save files to location"，内容会创建一个子目录(如果是多文件)。
                            # 但在 DownloadTaskService 中，我们设置 save_path = download_mounts[0].container_path (例如 /mnt/downloads)
                            # qbt 会在 /mnt/downloads 下创建 /mnt/downloads/TorrentName/
                            
                            # 而 download_task.save_path 记录的是什么？
                            # 在 create 中: result = await downloader_adapter.add_torrent_file(..., save_path=data.save_path)
                            # data.save_path 是挂载点路径。
                            
                            # 但是！我们在数据库中记录的 save_path 也就是这个挂载点路径吗？
                            # 是的: save_path=data.save_path
                            
                            # 那么，实际文件存在于: save_path / root_name / path_parts
                            full_path = save_path / rel_path
                            target_files.append(full_path)
                            
                    # 单文件种子
                    else:
                        # name 就是文件名
                        name = info[b'name'].decode('utf-8', errors='ignore')
                        full_path = save_path / name
                        # 注意：单文件种子，如果 save_path 是目录，qbt 会直接把文件下载到该目录下，不会创建同名目录
                        # 除非 content layout 设置不同。默认通常是这样。
                        target_files.append(full_path)
                        
                    logger.info(f"从种子文件解析出 {len(target_files)} 个目标文件")
                    
                except Exception as e:
                    logger.error(f"解析种子文件失败 {torrent_path}: {e}")
                    # 解析失败，回退到下面的逻辑？或者保持 target_files 为空
            
            # 如果解析种子成功，只处理目标文件
            if target_files:
                for target_file in target_files:
                    # 检查文件是否存在 (防止种子文件列表与实际不符，或者下载未完成)
                    if target_file.exists():
                         # 验证是否是视频文件 (只需关联视频)
                        from app.utils.file_operations import is_video_file
                        if is_video_file(target_file):
                            media_file = await MediaFileService._create_media_file_from_path(
                                db=db,
                                file_path=target_file,
                                download_task=download_task,
                                pt_resource=pt_resource,
                            )
                            if media_file:
                                media_files.append(media_file)
            else:
                # 2. 如果没有种子文件或解析失败 (兼容旧逻辑，但加限制)
                logger.warning(f"无法解析种子文件，回退到目录扫描模式: {save_path}")
                
                # 如果是单个文件
                if save_path.is_file() and is_video_file(save_path):
                    media_file = await MediaFileService._create_media_file_from_path(
                        db=db,
                        file_path=save_path,
                        download_task=download_task,
                        pt_resource=pt_resource,
                    )
                    if media_file:
                        media_files.append(media_file)

                # 如果是目录
                elif save_path.is_dir():
                    logger.warning(f"无法解析种子文件，回退到目录扫描模式: {save_path}")
                    from app.constants import VIDEO_EXTENSIONS
                    video_files = find_files_in_directory(
                        save_path, extensions=VIDEO_EXTENSIONS, recursive=True
                    )
                    
                    # 获取种子名称用于过滤（避免错误关联同目录下其他种子的文件）
                    torrent_name = download_task.torrent_name if download_task else None
                    
                    for video_file in video_files:
                        # 安全过滤：只关联在种子名称对应子目录下的文件
                        if torrent_name:
                            # 获取相对于 save_path 的路径
                            try:
                                rel_path = video_file.relative_to(save_path)
                                # 检查第一级目录是否与种子名称匹配
                                # 例如: save_path=/mnt/downloads, torrent_name="Show.S01"
                                # 文件路径应该是: /mnt/downloads/Show.S01/xxx.mkv
                                if len(rel_path.parts) > 1:
                                    # 多级目录，第一级应该是种子目录
                                    first_dir = rel_path.parts[0]
                                    if first_dir != torrent_name:
                                        logger.debug(f"跳过不相关文件: {video_file.name}, 所在目录 '{first_dir}' != 种子名 '{torrent_name}'")
                                        continue
                                # 单文件情况（文件直接在 save_path 下），需要检查文件名是否匹配
                                elif len(rel_path.parts) == 1:
                                    # 单文件种子，文件名应该与种子名相似
                                    # 这种情况比较少见，暂时允许通过
                                    pass
                            except ValueError:
                                # 文件不在 save_path 下，跳过
                                logger.warning(f"文件 {video_file} 不在下载目录 {save_path} 下，跳过")
                                continue
                        
                        media_file = await MediaFileService._create_media_file_from_path(
                            db=db,
                            file_path=video_file,
                            download_task=download_task,
                            pt_resource=pt_resource,
                        )
                        if media_file:
                            media_files.append(media_file)

            logger.info(
                f"从下载任务 {download_task.id} 创建了 {len(media_files)} 个媒体文件记录"
            )

        except Exception as e:
            logger.exception(f"从下载任务创建媒体文件失败: {download_task.id}")
            # 即使部分失败，也返回已创建的
            
        return media_files

    @staticmethod
    def _extract_season_episode_from_tv_info(
        tv_info: Dict, file_path: Path
    ) -> Tuple[Optional[int], Optional[int]]:
        """
        从 PT 资源的 tv_info 提取单个文件的季集信息

        策略(根据用户需求):
        1. 优先从文件名解析季集信息
        2. 如果文件名无法解析, 使用 tv_info 的季度信息 + 第一集作为兜底

        Args:
            tv_info: PT资源的tv_info字典
            file_path: 文件路径

        Returns:
            (season_number, episode_number) 或 (None, None)
        """
        from app.utils.tv_parser import extract_tv_info

        # 策略1：优先从文件名解析（精确匹配）
        filename = file_path.stem
        parsed_tv_info = extract_tv_info(filename)

        if parsed_tv_info:
            seasons = parsed_tv_info.get("seasons", [])
            episodes = parsed_tv_info.get("episodes", {})
            if seasons:
                season = seasons[0]
                episode_range = episodes.get(str(season))
                if episode_range:
                    # 文件名解析成功，返回解析结果
                    return season, episode_range.get("start")

        # 策略2：兜底 - 使用 tv_info 的季度 + 第一集
        # 适用于整季包下载但单个文件名无季集信息的场景
        seasons = tv_info.get("seasons", [])
        if seasons:
            season = seasons[0]
            episodes = tv_info.get("episodes", {}).get(str(season))
            if episodes and isinstance(episodes, dict):
                # 注意：这里返回第一集，用户后续需要手动修改或通过识别流程纠正
                return season, episodes.get("start")

        # 无法提取
        return None, None

    @staticmethod
    async def _create_media_file_from_path(
        db: AsyncSession,
        file_path: Path,
        download_task: Optional[DownloadTask] = None,
        pt_resource: Optional["PTResource"] = None,
    ) -> Optional[MediaFile]:
        """
        从文件路径创建媒体文件记录(内部方法)

        Args:
            db: 数据库会话
            file_path: 文件路径
            download_task: 下载任务(可选)

        Returns:
            媒体文件对象, 失败返回None
        """
        try:
            # 规范化文件路径 (统一使用正斜杠)
            path_str = normalize_path(file_path)

            # 检查文件是否已存在
            existing = await MediaFileService.get_by_path(db, path_str)
            if existing:
                # 如果存在且有下载任务信息，尝试更新关联
                if download_task:
                    updated = False

                    # 安全检查：只有当文件路径在下载任务的 save_path 下时才关联
                    # 防止错误地将扫描发现的无关文件关联到下载任务
                    should_link = False
                    if existing.download_task_id is None:
                        if download_task.save_path:
                            # 规范化路径进行比较
                            task_save_path = normalize_path(download_task.save_path)
                            # 确保 save_path 以 / 结尾，避免部分匹配问题
                            if not task_save_path.endswith('/'):
                                task_save_path_prefix = task_save_path + '/'
                            else:
                                task_save_path_prefix = task_save_path

                            if existing.file_path.startswith(task_save_path_prefix):
                                should_link = True
                            else:
                                logger.warning(
                                    f"文件路径 {existing.file_path} 不在下载任务 "
                                    f"{download_task.id} 的保存路径 {task_save_path} 下，跳过关联"
                                )
                        else:
                            # 下载任务没有 save_path，无法验证，保守起见不关联
                            logger.warning(
                                f"下载任务 {download_task.id} 没有 save_path，"
                                f"跳过关联文件: {existing.file_path}"
                            )

                    # 仅在通过安全检查且尚未关联时设置 download_task_id
                    if should_link:
                        existing.download_task_id = download_task.id
                        updated = True

                    if existing.media_type != download_task.media_type:
                        existing.media_type = download_task.media_type
                        updated = True

                    if download_task.unified_table_name and download_task.unified_resource_id:
                        if (existing.unified_table_name != download_task.unified_table_name or
                            existing.unified_resource_id != download_task.unified_resource_id):
                            existing.unified_table_name = download_task.unified_table_name
                            existing.unified_resource_id = download_task.unified_resource_id
                            existing.match_confidence = 95
                            existing.status = MEDIA_FILE_STATUS_IDENTIFIED
                            updated = True

                    if updated:
                        db.add(existing)
                        await db.commit()
                        await db.refresh(existing)
                        logger.info(f"更新已有媒体文件关联: {file_path.name}, ID: {existing.id}")

                logger.debug(f"媒体文件已存在: {path_str}")
                return existing

            # 获取文件信息
            file_size = get_file_size(file_path)
            file_type = get_file_type(file_path)
            file_stat = file_path.stat()

            # 尝试自动识别季集信息
            season_number = None
            episode_number = None
            match_detail = {}

            # 优先级1：从 PT 资源的 tv_info 提取
            if pt_resource and pt_resource.tv_info and pt_resource.category in [MEDIA_TYPE_TV, MEDIA_TYPE_ANIME]:
                season_number, episode_number = MediaFileService._extract_season_episode_from_tv_info(
                    pt_resource.tv_info, file_path
                )
                if season_number:
                    match_detail["source"] = "pt_resource_tv_info"
                    match_detail["pt_resource_id"] = pt_resource.id
                    logger.debug(f"从PT资源提取季集: S{season_number}E{episode_number} - {file_path.name}")

            # 优先级2：从文件名解析
            if not season_number:
                from app.services.common.filename_parser_service import FilenameParserService
                parsed = FilenameParserService.parse_media_file(str(file_path))
                if parsed:
                    season_number = parsed.get("season")
                    episode_number = parsed.get("episode")
                    if season_number:
                        match_detail["source"] = "filename_parser"
                        match_detail["parsed_info"] = parsed
                        logger.debug(f"从文件名解析季集: S{season_number}E{episode_number} - {file_path.name}")

            # 创建媒体文件记录
            media_file = MediaFile(
                file_path=path_str,
                file_name=file_path.name,
                directory=normalize_path(file_path.parent),  # 使用规范化路径
                file_size=file_size,
                file_type=file_type,
                extension=file_path.suffix,
                modified_at=datetime.fromtimestamp(file_stat.st_mtime),
                status=MEDIA_FILE_STATUS_DISCOVERED,
                download_task_id=download_task.id if download_task else None,
                season_number=season_number,
                episode_number=episode_number,
                match_detail=match_detail if match_detail else None,
                sub_title=pt_resource.subtitle if pt_resource else None,  # 从PT资源复制副标题
            )

            # 如果有下载任务，尝试自动关联
            if download_task:
                media_file.media_type = download_task.media_type
                media_file.match_method = MATCH_METHOD_FROM_DOWNLOAD

                # 如果下载任务已关联统一资源，直接关联
                if download_task.unified_table_name and download_task.unified_resource_id:
                    media_file.unified_table_name = download_task.unified_table_name
                    media_file.unified_resource_id = download_task.unified_resource_id
                    media_file.match_confidence = 95
                    media_file.status = MEDIA_FILE_STATUS_IDENTIFIED

            db.add(media_file)
            await db.commit()
            await db.refresh(media_file)

            logger.info(f"创建媒体文件记录: {file_path.name}, ID: {media_file.id}")
            return media_file

        except Exception as e:
            logger.exception(f"创建媒体文件记录失败: {file_path}")
            return None

    @staticmethod
    async def scan_directory(
        db: AsyncSession,
        directory: str,
        recursive: bool = True,
        media_type: Optional[str] = None,
        force: bool = True,
    ) -> List[MediaFile]:
        """
        扫描目录并创建媒体文件记录 (代理到 MediaScannerService)
        
        Args:
            db: 数据库会话
            directory: 目录路径
            recursive: 是否递归扫描 (新扫描器默认支持)
            media_type: 指定媒体类型
            force: 是否强制全量扫描 (False表示增量扫描，跳过未变更目录)
            
        Returns:
            统计信息 {"directories": int, "files": int}
        """
        from app.services.mediafile.scanner_service import MediaScannerService
        
        # 调用新扫描器
        stats = await MediaScannerService.scan_root(db, directory, media_type, force=force)
        
        logger.info(f"扫描完成: {stats}")
        
        return stats

    @staticmethod
    async def update_status(
        db: AsyncSession,
        file_id: int,
        status: str,
        error_message: Optional[str] = None,
    ) -> Optional[MediaFile]:
        """
        更新媒体文件状态

        Args:
            db: 数据库会话
            file_id: 文件ID
            status: 新状态
            error_message: 错误信息(可选)

        Returns:
            更新后的媒体文件对象
        """
        media_file = await MediaFileService.get_by_id(db, file_id)
        if not media_file:
            logger.error(f"媒体文件不存在: {file_id}")
            return None

        media_file.status = status
        if error_message:
            media_file.error_message = error_message
            media_file.error_at = datetime.now()

        await db.commit()
        await db.refresh(media_file)
        return media_file

    @staticmethod
    async def link_to_unified_resource(
        db: AsyncSession,
        file_id: int,
        unified_table_name: str,
        unified_resource_id: int,
        match_method: str = MATCH_METHOD_FROM_FILENAME,
        match_confidence: int = 80,
    ) -> Optional[MediaFile]:
        """
        关联媒体文件到统一资源

        Args:
            db: 数据库会话
            file_id: 文件ID
            unified_table_name: 统一资源表名
            unified_resource_id: 统一资源ID
            match_method: 匹配方法
            match_confidence: 匹配置信度

        Returns:
            更新后的媒体文件对象
        """
        media_file = await MediaFileService.get_by_id(db, file_id)
        if not media_file:
            return None

        media_file.unified_table_name = unified_table_name
        media_file.unified_resource_id = unified_resource_id
        media_file.match_method = match_method
        media_file.match_confidence = match_confidence
        media_file.status = MEDIA_FILE_STATUS_IDENTIFIED

        # 根据表名设置媒体类型
        if unified_table_name == UNIFIED_TABLE_MOVIES:
            media_file.media_type = MEDIA_TYPE_MOVIE
        elif unified_table_name == UNIFIED_TABLE_TV:
            media_file.media_type = MEDIA_TYPE_TV
        elif unified_table_name == UNIFIED_TABLE_ADULT:
            media_file.media_type = MEDIA_TYPE_ADULT

        await db.commit()
        await db.refresh(media_file)

        logger.info(
            f"媒体文件 {file_id} 已关联到 {unified_table_name}.{unified_resource_id}, "
            f"匹配方法: {match_method}, 置信度: {match_confidence}"
        )
        return media_file

    @staticmethod
    async def delete(db: AsyncSession, file_id: int, delete_physical_file: bool = False) -> bool:
        """
        删除媒体文件记录

        Args:
            db: 数据库会话
            file_id: 文件ID
            delete_physical_file: 是否删除物理文件

        Returns:
            是否成功
        """
        media_file = await MediaFileService.get_by_id(db, file_id)
        if not media_file:
            return False

        # 删除物理文件
        if delete_physical_file:
            try:
                file_path = Path(media_file.file_path)
                if file_path.exists():
                    file_path.unlink()
                    logger.info(f"删除物理文件: {media_file.file_path}")
            except Exception as e:
                logger.error(f"删除物理文件失败: {media_file.file_path}, 错误: {e}")

        # 删除数据库记录
        await db.delete(media_file)
        await db.commit()

        logger.info(f"删除媒体文件记录: {file_id}")
        return True

    @staticmethod
    async def delete_orphaned_records(db: AsyncSession, base_directory: str) -> int:
        """
        删除不存在的文件记录(增量扫描时使用)

        Args:
            db: 数据库会话
            base_directory: 基础目录路径

        Returns:
            删除的文件数量
        """
        import os

        # 规范化基础目录路径
        normalized_base = normalize_path(base_directory)
        logger.info(f"delete_orphaned_records: 原始目录={base_directory}, 规范化后={normalized_base}")

        # 查询所有在该目录下的文件记录
        stmt = select(MediaFile).where(MediaFile.directory.like(f"{normalized_base}%"))
        result = await db.execute(stmt)
        files = list(result.scalars().all())

        deleted_count = 0
        for file in files:
            # 检查文件是否存在
            if not os.path.exists(file.file_path):
                await db.delete(file)
                deleted_count += 1
                logger.debug(f"删除不存在的文件记录: {file.file_path}")

        if deleted_count > 0:
            await db.commit()
            logger.info(f"增量扫描: 删除了 {deleted_count} 个不存在的文件记录")

        return deleted_count
