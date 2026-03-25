# -*- coding: utf-8 -*-
"""
媒体文件整理服务
核心文件整理逻辑，根据配置整理媒体文件到目标目录
"""
import logging
from pathlib import Path
from typing import Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import (
    MEDIA_FILE_STATUS_COMPLETED,
    MEDIA_FILE_STATUS_ORGANIZING,
    MEDIA_FILE_STATUS_SCRAPING,
    MEDIA_TYPE_ADULT,
    UNIFIED_TABLE_MOVIES,
    UNIFIED_TABLE_TV,
    UNIFIED_TABLE_ADULT,
)
from app.models.media_file import MediaFile
from app.models.organize_config import OrganizeConfig
from app.models.unified_movie import UnifiedMovie
from app.models.unified_tv_series import UnifiedTVSeries
from app.models.unified_adult import UnifiedAdult
from app.services.mediafile.organize_config_service import OrganizeConfigService
from app.services.mediafile.scraper_service import ScraperService
from app.utils.file_operations import (
    FileOperationError,
    ensure_dir,
    is_bluray_directory,
    organize_directory,
    organize_file,
    organize_with_associated_files,
    sanitize_filename,
)
from app.utils.timezone import now

logger = logging.getLogger(__name__)


class MediaOrganizerService:
    """媒体文件整理服务"""

    @staticmethod
    async def organize_media_file(
        db: AsyncSession,
        media_file: MediaFile,
        config: Optional[OrganizeConfig] = None,
        dry_run: bool = False,
        force: bool = False,
        storage_mount_id: Optional[int] = None,
    ) -> Dict:
        """
        整理媒体文件

        Args:
            db: 数据库会话
            media_file: 媒体文件对象
            config: 整理配置（可选，默认使用该媒体类型的默认配置）
            dry_run: 是否仅模拟运行（不实际移动文件）
            force: 强制重新整理（忽略已整理状态）

        Returns:
            包含status和message的字典
        """
        try:
            # 检查文件是否已整理（force=True 时忽略）
            if not force and media_file.organized and config and config.skip_existed:
                return {
                    "status": "skipped",
                    "message": "文件已整理，跳过",
                    "organized_path": media_file.organized_path,
                }

            # 获取配置
            if not config:
                config = await OrganizeConfigService.get_default(db, media_file.media_type)
                if not config:
                    return {
                        "status": "error",
                        "message": f"未找到媒体类型 {media_file.media_type} 的默认配置",
                    }

            # 检查配置是否启用
            if not config.is_enabled:
                return {"status": "skipped", "message": "配置未启用"}

            # 检查文件是否已识别
            if not media_file.unified_resource_id or not media_file.unified_table_name:
                if media_file.media_type == MEDIA_TYPE_ADULT:
                    auto_ok = await MediaOrganizerService._auto_identify_adult(db, media_file)
                    if not auto_ok:
                        return {"status": "error", "message": "成人资源自动识别失败，无法整理"}
                else:
                    return {"status": "error", "message": "文件未识别，无法整理"}

            # 更新状态为整理中
            if not dry_run:
                media_file.status = MEDIA_FILE_STATUS_ORGANIZING
                await db.commit()

            # 根据统一资源表名调用不同的整理方法
            # 这样 anime 等媒体类型可以复用 movie/tv 的整理逻辑
            if media_file.unified_table_name == UNIFIED_TABLE_MOVIES:
                result = await MediaOrganizerService._organize_movie(
                    db, media_file, config, dry_run, storage_mount_id
                )
            elif media_file.unified_table_name == UNIFIED_TABLE_TV:
                result = await MediaOrganizerService._organize_tv(
                    db, media_file, config, dry_run, storage_mount_id
                )
            elif media_file.unified_table_name == UNIFIED_TABLE_ADULT:
                result = await MediaOrganizerService._organize_adult(
                    db, media_file, config, dry_run, storage_mount_id
                )
            else:
                return {
                    "status": "error",
                    "message": f"不支持的统一资源表: {media_file.unified_table_name}，当前仅支持 {UNIFIED_TABLE_MOVIES}、{UNIFIED_TABLE_TV} 和 {UNIFIED_TABLE_ADULT}"
                }

            # 如果成功且不是模拟运行，更新数据库
            if result["status"] == "success" and not dry_run:
                media_file.organized = True
                media_file.organized_path = result.get("organized_path")
                media_file.organized_at = now()
                media_file.organize_mode = config.organize_mode
                media_file.status = MEDIA_FILE_STATUS_COMPLETED

                # 更新配置统计
                config.total_organized_count += 1
                config.last_organized_at = now()

                await db.commit()

                # 自动刮削（下载海报、背景图、生成NFO）
                if config.generate_nfo or config.download_poster or config.download_backdrop:
                    media_file.status = MEDIA_FILE_STATUS_SCRAPING
                    await db.commit()

                    scrape_result = await ScraperService.scrape_media_file(db, media_file, config)
                    result["scrape_result"] = scrape_result

                    # 恢复状态
                    media_file.status = MEDIA_FILE_STATUS_COMPLETED
                    await db.commit()

                    if not scrape_result.get("success"):
                        logger.warning(f"刮削过程有错误: {scrape_result.get('errors')}")

            return result

        except Exception as e:
            logger.exception(f"整理媒体文件失败: {media_file.id}")
            if not dry_run:
                media_file.error_message = str(e)
                media_file.error_step = "organizing"
                await db.commit()
            return {"status": "error", "message": str(e)}

    @staticmethod
    async def _organize_movie(
        db: AsyncSession,
        media_file: MediaFile,
        config: OrganizeConfig,
        dry_run: bool,
        storage_mount_id: Optional[int] = None,
    ) -> Dict:
        """
        整理电影文件

        Args:
            db: 数据库会话
            media_file: 媒体文件对象
            config: 整理配置
            dry_run: 是否仅模拟运行

        Returns:
            包含status和message的字典
        """
        # 获取电影元数据
        movie = await db.get(UnifiedMovie, media_file.unified_resource_id)
        if not movie:
            return {"status": "error", "message": "未找到关联的电影资源"}

        # 准备模板变量
        variables = {
            "title": sanitize_filename(movie.title or "Unknown"),
            "original_title": sanitize_filename(movie.original_title or ""),
            "year": movie.year or "Unknown",
            "resolution": media_file.resolution or "Unknown",
            "quality": media_file.resolution or "Unknown",
        }

        # 解析目录模板
        dir_name = OrganizeConfigService.parse_template(config.dir_template, variables)

        # 解析文件名模板
        filename_base = OrganizeConfigService.parse_template(config.filename_template, variables)

        # 使用挂载点系统选择目标路径（优先同盘）
        # 注意：使用配置的 media_type 而非文件的 media_type
        # 这样 anime 类型的文件可以使用 tv 类型的整理规则和挂载点
        from app.services.storage.storage_mount_service import StorageMountService

        if storage_mount_id:
            target_mount = await StorageMountService.get_mount_by_id(db, storage_mount_id)
            if not target_mount:
                raise ValueError(f"指定的存储挂载点 {storage_mount_id} 不存在")
        else:
            target_mount = await StorageMountService.get_organize_target(
                db,
                media_category=config.media_type,
                source_path=media_file.file_path
            )

        if not target_mount:
            raise ValueError(f"未找到媒体类型 {config.media_type} 的可用挂载点，请在存储配置中添加")

        logger.info(f"选择目标挂载点: {target_mount.name} ({target_mount.container_path})")
        target_base = Path(target_mount.container_path)

        # 构建完整路径
        target_dir = target_base / dir_name
        target_filename = f"{filename_base}{media_file.extension}"
        target_path = target_dir / target_filename

        # 检查目标文件是否已存在
        if target_path.exists() and config.skip_existed:
            return {
                "status": "skipped",
                "message": "目标文件已存在",
                "organized_path": str(target_path),
            }

        # 检查是否为蓝光原盘目录
        source_path = Path(media_file.file_path)
        source_dir = source_path.parent
        is_bluray = is_bluray_directory(source_dir)

        # 如果不是模拟运行，执行整理
        if not dry_run:
            try:
                if is_bluray:
                    # 蓝光原盘：整目录硬链接
                    # 目标路径为：目标目录/电影名/原盘目录名
                    bluray_dest = target_dir / source_dir.name
                    organize_directory(
                        source_dir=source_dir,
                        dest_dir=bluray_dest,
                        mode=config.organize_mode,
                        overwrite=not config.skip_existed,
                    )
                    logger.info(
                        f"蓝光原盘整理成功: {source_dir.name} -> {bluray_dest}, "
                        f"模式: {config.organize_mode}"
                    )
                    return {
                        "status": "success",
                        "message": "蓝光原盘整理成功",
                        "organized_path": str(bluray_dest),
                        "organize_mode": config.organize_mode,
                        "is_bluray": True,
                    }
                else:
                    # 普通视频：整理视频及附属文件（字幕等）
                    organize_result = organize_with_associated_files(
                        video_path=media_file.file_path,
                        dest_dir=target_dir,
                        dest_filename_base=filename_base,
                        mode=config.organize_mode,
                        include_subtitles=config.organize_subtitles if hasattr(config, 'organize_subtitles') else True,
                        include_samples=False,  # 一般不需要预览视频
                        overwrite=not config.skip_existed,
                    )

                    if organize_result["errors"]:
                        logger.warning(f"部分附属文件整理失败: {organize_result['errors']}")

                    logger.info(
                        f"电影文件整理成功: {media_file.file_name} -> {target_path}, "
                        f"模式: {config.organize_mode}, "
                        f"字幕: {len(organize_result['subtitles'])} 个"
                    )

                    return {
                        "status": "success",
                        "message": "整理成功",
                        "organized_path": str(target_path),
                        "organize_mode": config.organize_mode,
                        "subtitles": organize_result["subtitles"],
                        "errors": organize_result["errors"],
                    }

            except FileOperationError as e:
                logger.error(f"文件整理失败: {e}")
                return {"status": "error", "message": str(e)}

        else:
            # 模拟运行，仅返回预期路径
            result = {
                "status": "success",
                "message": "模拟运行成功（未实际移动文件）",
                "organized_path": str(target_path) if not is_bluray else str(target_dir / source_dir.name),
                "organize_mode": config.organize_mode,
            }
            if is_bluray:
                result["is_bluray"] = True
                result["message"] = "模拟运行成功（蓝光原盘，未实际移动文件）"
            return result

    @staticmethod
    async def _organize_tv(
        db: AsyncSession,
        media_file: MediaFile,
        config: OrganizeConfig,
        dry_run: bool,
        storage_mount_id: Optional[int] = None,
    ) -> Dict:
        """
        整理电视剧文件

        Args:
            db: 数据库会话
            media_file: 媒体文件对象
            config: 整理配置
            dry_run: 是否仅模拟运行

        Returns:
            包含status和message的字典
        """
        # 获取电视剧元数据
        tv_series = await db.get(UnifiedTVSeries, media_file.unified_resource_id)
        if not tv_series:
            return {"status": "error", "message": "未找到关联的电视剧资源"}

        # 检查季数和集数
        if not media_file.season_number or not media_file.episode_number:
            return {"status": "error", "message": "缺少季数或集数信息"}

        # 查找关联的订阅（获取覆写信息）
        from app.services.mediafile.nfo_generator_service import NFOGeneratorService
        
        subscription = await NFOGeneratorService._find_subscription_for_media_file(db, media_file)
        
        # 应用覆写字段
        title = tv_series.title or "Unknown"
        year = tv_series.year or "Unknown"
        override_folder_name = None
        
        if subscription:
            if subscription.override_title:
                title = subscription.override_title
                logger.info(f"使用订阅覆写标题: {title}")
            if subscription.override_year:
                year = subscription.override_year
                logger.info(f"使用订阅覆写年份: {year}")
            if subscription.override_folder:
                override_folder_name = subscription.override_folder
                logger.info(f"使用订阅覆写目录名: {override_folder_name}")

        # 准备模板变量
        variables = {
            "title": sanitize_filename(title),
            "original_title": sanitize_filename(tv_series.original_title or ""),
            "year": year,
            "season": media_file.season_number,
            "episode": media_file.episode_number,
            "episode_title": sanitize_filename(media_file.episode_title or ""),
            "resolution": media_file.resolution or "Unknown",
        }

        # 解析目录模板
        if override_folder_name:
            # 如果订阅指定了覆写目录名，直接使用
            dir_name = sanitize_filename(override_folder_name)
            logger.info(f"使用覆写目录名: {dir_name}")
        else:
            # 否则使用模板解析
            dir_name = OrganizeConfigService.parse_template(config.dir_template, variables)

        # 解析文件名模板
        filename_base = OrganizeConfigService.parse_template(config.filename_template, variables)

        # 使用挂载点系统选择目标路径（优先同盘）
        # 注意：使用配置的 media_type 而非文件的 media_type
        # 这样 anime 类型的文件可以使用 tv 类型的整理规则和挂载点
        from app.services.storage.storage_mount_service import StorageMountService

        if storage_mount_id:
            target_mount = await StorageMountService.get_mount_by_id(db, storage_mount_id)
            if not target_mount:
                raise ValueError(f"指定的存储挂载点 {storage_mount_id} 不存在")
        else:
            target_mount = await StorageMountService.get_organize_target(
                db,
                media_category=config.media_type,
                source_path=media_file.file_path
            )

        if not target_mount:
            raise ValueError(f"未找到媒体类型 {config.media_type} 的可用挂载点，请在存储配置中添加")

        logger.info(f"选择目标挂载点: {target_mount.name} ({target_mount.container_path})")
        target_base = Path(target_mount.container_path)

        # 构建完整路径
        target_dir = target_base / dir_name
        target_filename = f"{filename_base}{media_file.extension}"
        target_path = target_dir / target_filename

        # 检查目标文件是否已存在
        if target_path.exists() and config.skip_existed:
            return {
                "status": "skipped",
                "message": "目标文件已存在",
                "organized_path": str(target_path),
            }

        # 检查是否为蓝光原盘目录
        source_path = Path(media_file.file_path)
        source_dir = source_path.parent
        is_bluray = is_bluray_directory(source_dir)

        # 如果不是模拟运行，执行整理
        if not dry_run:
            try:
                if is_bluray:
                    # 蓝光原盘：整目录硬链接
                    bluray_dest = target_dir / source_dir.name
                    organize_directory(
                        source_dir=source_dir,
                        dest_dir=bluray_dest,
                        mode=config.organize_mode,
                        overwrite=not config.skip_existed,
                    )
                    logger.info(
                        f"蓝光原盘整理成功: {source_dir.name} -> {bluray_dest}, "
                        f"模式: {config.organize_mode}"
                    )
                    return {
                        "status": "success",
                        "message": "蓝光原盘整理成功",
                        "organized_path": str(bluray_dest),
                        "organize_mode": config.organize_mode,
                        "is_bluray": True,
                    }
                else:
                    # 普通视频：整理视频及附属文件（字幕等）
                    organize_result = organize_with_associated_files(
                        video_path=media_file.file_path,
                        dest_dir=target_dir,
                        dest_filename_base=filename_base,
                        mode=config.organize_mode,
                        include_subtitles=config.organize_subtitles if hasattr(config, 'organize_subtitles') else True,
                        include_samples=False,
                        overwrite=not config.skip_existed,
                    )

                    if organize_result["errors"]:
                        logger.warning(f"部分附属文件整理失败: {organize_result['errors']}")

                    logger.info(
                        f"电视剧文件整理成功: {media_file.file_name} -> {target_path}, "
                        f"模式: {config.organize_mode}, "
                        f"字幕: {len(organize_result['subtitles'])} 个"
                    )

                    return {
                        "status": "success",
                        "message": "整理成功",
                        "organized_path": str(target_path),
                        "organize_mode": config.organize_mode,
                        "subtitles": organize_result["subtitles"],
                        "errors": organize_result["errors"],
                    }

            except FileOperationError as e:
                logger.error(f"文件整理失败: {e}")
                return {"status": "error", "message": str(e)}

        else:
            # 模拟运行，仅返回预期路径
            result = {
                "status": "success",
                "message": "模拟运行成功（未实际移动文件）",
                "organized_path": str(target_path) if not is_bluray else str(target_dir / source_dir.name),
                "organize_mode": config.organize_mode,
            }
            if is_bluray:
                result["is_bluray"] = True
                result["message"] = "模拟运行成功（蓝光原盘，未实际移动文件）"
            return result

    @staticmethod
    async def _organize_adult(
        db: AsyncSession,
        media_file: MediaFile,
        config: OrganizeConfig,
        dry_run: bool,
        storage_mount_id: Optional[int] = None,
    ) -> Dict:
        """
        整理成人资源文件

        成人资源整理策略：
        1. 如果有产品番号，使用番号作为目录名
        2. 如果没有番号，使用标题作为目录名
        3. 文件名保持原名或使用配置的模板

        Args:
            db: 数据库会话
            media_file: 媒体文件对象
            config: 整理配置
            dry_run: 是否仅模拟运行

        Returns:
            包含status和message的字典
        """
        # 获取成人资源元数据
        adult = await db.get(UnifiedAdult, media_file.unified_resource_id)
        if not adult:
            return {"status": "error", "message": "未找到关联的成人资源"}

        # 准备模板变量
        # 提取番号（如果数据库中没有）
        product_number = adult.product_number
        if not product_number:
            from app.services.identification.adult_identify_service import AdultIdentifyService
            product_number = AdultIdentifyService.extract_product_number(media_file.file_name)

        # 确保标题存在
        title = adult.title
        if not title:
            title = Path(media_file.file_path).stem

        # 成人资源使用番号或标题作为目录名
        if product_number:
            default_dir_name = product_number
            # 默认使用番号或标题
            dir_name = default_dir_name
        else:
            default_dir_name = sanitize_filename(title[:100])

        variables = {
            "title": sanitize_filename(title[:100]),
            "product_number": product_number or "",
            "year": adult.year or "Unknown",
            "maker": sanitize_filename(adult.maker or "") if adult.maker else "",
            "actress": sanitize_filename(adult.actresses[0] if adult.actresses else "") if adult.actresses else "",
            "resolution": media_file.resolution or "Unknown",
        }

        # 解析目录模板（如果配置了）
        if config.dir_template:
            dir_name = OrganizeConfigService.parse_template(config.dir_template, variables)
        else:
            # 默认使用番号或标题
            dir_name = default_dir_name

        # 解析文件名模板
        if config.filename_template:
            filename_base = OrganizeConfigService.parse_template(config.filename_template, variables)
        else:
            # 默认保持原文件名（不含扩展名）
            filename_base = Path(media_file.file_path).stem

        # 使用挂载点系统选择目标路径
        from app.services.storage.storage_mount_service import StorageMountService

        if storage_mount_id:
            target_mount = await StorageMountService.get_mount_by_id(db, storage_mount_id)
            if not target_mount:
                raise ValueError(f"指定的存储挂载点 {storage_mount_id} 不存在")
        else:
            target_mount = await StorageMountService.get_organize_target(
                db,
                media_category=config.media_type,
                source_path=media_file.file_path
            )

        if not target_mount:
            raise ValueError(f"未找到媒体类型 {config.media_type} 的可用挂载点，请在存储配置中添加")

        logger.info(f"选择目标挂载点: {target_mount.name} ({target_mount.container_path})")
        target_base = Path(target_mount.container_path)

        # 构建完整路径
        target_dir = target_base / dir_name
        target_filename = f"{filename_base}{media_file.extension}"
        target_path = target_dir / target_filename

        # 检查目标文件是否已存在
        if target_path.exists() and config.skip_existed:
            return {
                "status": "skipped",
                "message": "目标文件已存在",
                "organized_path": str(target_path),
            }

        # 检查是否为蓝光原盘目录
        source_path = Path(media_file.file_path)
        source_dir = source_path.parent
        is_bluray = is_bluray_directory(source_dir)

        # 如果不是模拟运行，执行整理
        if not dry_run:
            try:
                if is_bluray:
                    # 蓝光原盘：整目录硬链接
                    bluray_dest = target_dir / source_dir.name
                    organize_directory(
                        source_dir=source_dir,
                        dest_dir=bluray_dest,
                        mode=config.organize_mode,
                        overwrite=not config.skip_existed,
                    )
                    logger.info(
                        f"蓝光原盘整理成功: {source_dir.name} -> {bluray_dest}, "
                        f"模式: {config.organize_mode}"
                    )
                    return {
                        "status": "success",
                        "message": "蓝光原盘整理成功",
                        "organized_path": str(bluray_dest),
                        "organize_mode": config.organize_mode,
                        "is_bluray": True,
                    }
                else:
                    # 普通视频：整理视频及附属文件
                    organize_result = organize_with_associated_files(
                        video_path=media_file.file_path,
                        dest_dir=target_dir,
                        dest_filename_base=filename_base,
                        mode=config.organize_mode,
                        include_subtitles=config.organize_subtitles if hasattr(config, 'organize_subtitles') else True,
                        include_samples=False,
                        overwrite=not config.skip_existed,
                    )

                    if organize_result["errors"]:
                        logger.warning(f"部分附属文件整理失败: {organize_result['errors']}")

                    logger.info(
                        f"成人资源整理成功: {media_file.file_name} -> {target_path}, "
                        f"模式: {config.organize_mode}"
                    )

                    return {
                        "status": "success",
                        "message": "整理成功",
                        "organized_path": str(target_path),
                        "organize_mode": config.organize_mode,
                        "subtitles": organize_result.get("subtitles", []),
                        "errors": organize_result.get("errors", []),
                    }

            except FileOperationError as e:
                logger.error(f"文件整理失败: {e}")
                return {"status": "error", "message": str(e)}

        else:
            # 模拟运行
            result = {
                "status": "success",
                "message": "模拟运行成功（未实际移动文件）",
                "organized_path": str(target_path) if not is_bluray else str(target_dir / source_dir.name),
                "organize_mode": config.organize_mode,
            }
            if is_bluray:
                result["is_bluray"] = True
                result["message"] = "模拟运行成功（蓝光原盘，未实际移动文件）"
            return result

    @staticmethod
    async def _auto_identify_adult(db: AsyncSession, media_file: MediaFile) -> bool:
        """
        自动识别成人资源文件

        使用与资源页面一致的识别逻辑：
        1. 通过番号匹配已有的 UnifiedAdult 记录
        2. 匹配不到则通过DMM API或简化模式自动创建记录

        Args:
            db: 数据库会话
            media_file: 媒体文件对象

        Returns:
            是否识别成功
        """
        try:
            from app.services.identification.media_identify_service import media_identify_service

            parsed_info = {"title": media_file.file_name or ""}
            result = await media_identify_service._identify_adult(db, media_file, parsed_info)

            if result.get("auto_matched") and media_file.unified_resource_id:
                logger.info(f"成人资源自动识别成功: {media_file.file_name}")
                return True

            logger.warning(f"成人资源自动识别失败: {media_file.file_name}")
            return False

        except Exception as e:
            logger.error(f"成人资源自动识别异常: {media_file.file_name}, 错误: {e}")
            return False

    @staticmethod
    async def batch_organize(
        db: AsyncSession,
        media_file_ids: list[int],
        config_id: Optional[int] = None,
        dry_run: bool = False,
        force: bool = False,
        storage_mount_id: Optional[int] = None,
    ) -> Dict:
        """
        批量整理媒体文件

        Args:
            db: 数据库会话
            media_file_ids: 媒体文件ID列表
            config_id: 配置ID（可选）
            dry_run: 是否仅模拟运行
            force: 强制重新整理（忽略已整理状态）

        Returns:
            包含success_count、failed_count和details的字典
        """
        config = None
        if config_id:
            config = await OrganizeConfigService.get_by_id(db, config_id)
            if not config:
                return {"status": "error", "message": f"配置不存在: {config_id}"}

        results = {"success_count": 0, "failed_count": 0, "skipped_count": 0, "details": []}

        for file_id in media_file_ids:
            media_file = await db.get(MediaFile, file_id)
            if not media_file:
                results["failed_count"] += 1
                results["details"].append({"file_id": file_id, "status": "error", "message": "文件不存在"})
                continue

            result = await MediaOrganizerService.organize_media_file(
                db, media_file, config, dry_run, force, storage_mount_id
            )

            if result["status"] == "success":
                results["success_count"] += 1
            elif result["status"] == "skipped":
                results["skipped_count"] += 1
            else:
                results["failed_count"] += 1

            results["details"].append({"file_id": file_id, **result})

        logger.info(
            f"批量整理完成: 成功 {results['success_count']}, "
            f"失败 {results['failed_count']}, "
            f"跳过 {results['skipped_count']}"
        )

        return results
