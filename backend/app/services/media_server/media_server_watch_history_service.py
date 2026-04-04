# -*- coding: utf-8 -*-
"""
观看历史服务
"""
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy import select, and_, or_, not_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.media_server_watch_history import MediaServerWatchHistory
from app.models.media_server_config import MediaServerConfig
from app.models.media_file import MediaFile
from app.models.unified_movie import UnifiedMovie
from app.models.unified_tv_series import UnifiedTVSeries
from app.services.media_server.media_server_config_service import MediaServerConfigService
from app.constants.media_server import WATCH_COMPLETE_THRESHOLD
from app.utils.timezone import now, parse_datetime
from app.utils.path_mapping import apply_path_mappings

logger = logging.getLogger(__name__)


class MediaServerWatchHistoryService:
    """观看历史服务"""

    @staticmethod
    async def sync_watch_history(db: AsyncSession, media_server_config_id: int) -> Dict[str, Any]:
        """
        同步观看历史（通用方法，支持所有服务器类型）

        Args:
            db: 数据库会话
            media_server_config_id: 媒体服务器配置ID

        Returns:
            Dict: 同步结果
                {
                    "synced_count": 10,
                    "new_count": 5,
                    "updated_count": 5
                }
        """
        # 获取配置
        config = await MediaServerConfigService.get_by_id(db, media_server_config_id)
        if not config:
            raise ValueError(f"Media server config not found: {media_server_config_id}")

        # 获取适配器
        adapter = MediaServerConfigService._get_adapter(config)

        # 获取媒体服务器用户ID
        server_user_id = config.server_config.get("server_user_id") if config.server_config else None
        
        if not server_user_id:
            logger.info(f"Media server user ID not configured for {config.name}, attempting auto-discovery...")
            try:
                users = await adapter.get_users()
                if users:
                    # 优先选择管理员，其次选择第一个用户
                    admins = [u for u in users if u.get("is_admin")]
                    target_user = admins[0] if admins else users[0]
                    server_user_id = target_user["id"]
                    
                    # 保存到配置中，以便下次使用
                    if not config.server_config:
                        config.server_config = {}
                    config.server_config["server_user_id"] = server_user_id
                    db.add(config)
                    await db.commit()
                    logger.info(f"Auto-discovered and saved user ID {server_user_id} ({target_user.get('name')}) for {config.name}")
                else:
                    raise ValueError("No users found on media server")
            except Exception as e:
                logger.error(f"Failed to auto-discover user ID: {str(e)}")
                raise ValueError(f"Media server user ID not configured and auto-discovery failed: {str(e)}")

        # 调用适配器获取观看历史
        try:
            server_history = await adapter.get_watch_history(user_id=server_user_id, limit=1000)
        except Exception as e:
            logger.error(f"Failed to fetch watch history from media server: {str(e)}")
            raise

        # 获取当前服务器的所有媒体库信息，用于匹配记录所属的库（按路径匹配更准确）
        try:
            libraries = await adapter.get_libraries()
        except Exception as e:
            logger.warning(f"Failed to fetch libraries for ID matching: {str(e)}")
            libraries = []

        # 同步到数据库
        synced_count = 0
        new_count = 0
        updated_count = 0

        for item in server_history:
            result = await MediaServerWatchHistoryService.upsert_history_record(db, config, item, libraries)
            synced_count += 1
            if result == "new":
                new_count += 1
            elif result == "updated":
                updated_count += 1

        # 更新同步时间
        config.last_sync_at = now()
        await db.commit()

        logger.info(
            f"Synced watch history for {config.name}: "
            f"total={synced_count}, new={new_count}, updated={updated_count}"
        )

        return {"synced_count": synced_count, "new_count": new_count, "updated_count": updated_count}

    @staticmethod
    async def upsert_history_record(
        db: AsyncSession, config: MediaServerConfig, server_data: Dict[str, Any], libraries: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        创建或更新观看历史记录

        Args:
            db: 数据库会话
            config: 媒体服务器配置
            server_data: 服务器原始数据

        Returns:
            str: "new" 或 "updated" 或 "skipped"
        """
        # 提取关键字段
        server_item_id = server_data.get("Id")
        server_user_id = config.server_config.get("server_user_id") if config.server_config else None

        if not server_item_id or not server_user_id:
            return "skipped"

        # 检查是否有播放记录，如果没有则跳过
        user_data = server_data.get("UserData", {})
        last_played_date = user_data.get("LastPlayedDate")
        playback_position_ticks = user_data.get("PlaybackPositionTicks", 0)
        play_count = user_data.get("PlayCount", 0)

        if not last_played_date and playback_position_ticks == 0 and play_count == 0:
            return "skipped"

        # 查询是否已存在
        query = select(MediaServerWatchHistory).where(
            and_(
                MediaServerWatchHistory.server_item_id == server_item_id,
                MediaServerWatchHistory.user_id == config.user_id,
                MediaServerWatchHistory.media_server_config_id == config.id,
            )
        )
        result = await db.execute(query)
        existing = result.scalar_one_or_none()

        # 提取媒体库 ID
        library_id = server_data.get("ParentId")
        item_path = server_data.get("Path")

        if libraries:
            # 策略 1: 路径匹配（最准确，针对 NAS 环境极其通用）
            if item_path:
                matched_lib_id = None
                for lib in libraries:
                    lib_id = lib.get("id")
                    locations = lib.get("locations", [])
                    for loc in locations:
                        if loc and item_path.startswith(loc):
                            matched_lib_id = lib_id
                            break
                    if matched_lib_id:
                        break
                
                if matched_lib_id:
                    library_id = matched_lib_id
            
            # 策略 2: AncestorIds 匹配（如果路径没对上，或者没有 Path 信息）
            if not library_id or library_id == server_data.get("ParentId"):
                ancestor_ids = server_data.get("AncestorIds", [])
                lib_id_set = {lib.get("id") for lib in libraries if lib.get("id")}
                for aid in ancestor_ids:
                    if aid in lib_id_set:
                        library_id = aid
                        break
        
        # 提取媒体信息
        media_type = MediaServerWatchHistoryService._extract_media_type(server_data)
        title = server_data.get("Name", "")
        year = server_data.get("ProductionYear")

        # 电视剧特定信息
        season_number = server_data.get("ParentIndexNumber")
        episode_number = server_data.get("IndexNumber")
        episode_title = None
        if media_type == "tv" and episode_number:
            episode_title = title
            # 获取剧集所属剧集名称
            series_name = server_data.get("SeriesName")
            if series_name:
                title = series_name

        # 播放信息
        user_data = server_data.get("UserData", {})
        play_count = user_data.get("PlayCount", 1)
        last_played_date = user_data.get("LastPlayedDate")
        last_played_at = parse_datetime(last_played_date) if last_played_date else now()

        # 计算是否看完
        playback_position_ticks = user_data.get("PlaybackPositionTicks", 0)
        runtime_ticks = server_data.get("RunTimeTicks", 0)
        is_completed = False
        play_duration_seconds = None
        runtime_seconds = None

        if runtime_ticks > 0:
            runtime_seconds = runtime_ticks // 10000000  # Ticks to seconds
            play_duration_seconds = playback_position_ticks // 10000000
            if play_duration_seconds / runtime_seconds >= WATCH_COMPLETE_THRESHOLD:
                is_completed = True

        # 标记为已完成（服务器端标记）
        if user_data.get("Played"):
            is_completed = True

        if existing:
            # 更新现有记录
            existing.title = title
            existing.year = year
            existing.season_number = season_number
            existing.episode_number = episode_number
            existing.episode_title = episode_title
            existing.play_count = play_count
            existing.last_played_at = last_played_at
            existing.play_duration_seconds = play_duration_seconds
            existing.runtime_seconds = runtime_seconds
            existing.is_completed = is_completed
            existing.library_id = library_id
            existing.server_data = server_data

            await db.commit()
            return "updated"
        else:
            # 创建新记录
            history = MediaServerWatchHistory(
                user_id=config.user_id,
                media_server_config_id=config.id,
                server_type=config.type,
                server_item_id=server_item_id,
                server_user_id=server_user_id,
                media_type=media_type,
                title=title,
                year=year,
                season_number=season_number,
                episode_number=episode_number,
                episode_title=episode_title,
                play_count=play_count,
                last_played_at=last_played_at,
                play_duration_seconds=play_duration_seconds,
                runtime_seconds=runtime_seconds,
                is_completed=is_completed,
                library_id=library_id,
                server_data=server_data,
            )

            db.add(history)
            await db.commit()
            await db.refresh(history)

            # 尝试匹配本地媒体
            await MediaServerWatchHistoryService.match_local_media(db, history, config)

            return "new"

    @staticmethod
    async def match_local_media(
        db: AsyncSession,
        history: MediaServerWatchHistory,
        config: Optional[MediaServerConfig] = None
    ) -> None:
        """
        智能匹配本地媒体文件和统一资源（增强版）

        匹配策略（按优先级）：
        1. Provider IDs 精确匹配（TMDb/IMDb/豆瓣 ID）
        2. 文件路径映射匹配
        3. 标题+年份匹配（精确）
        4. 标题模糊匹配（回退方案）

        Args:
            db: 数据库会话
            history: 观看历史记录
            config: 媒体服务器配置（可选，用于路径映射）
        """
        # 如果没有传入config，尝试获取
        if not config and history.media_server_config_id:
            config = await MediaServerConfigService.get_by_id(db, history.media_server_config_id)
        unified_id = None
        table_name = None
        match_method = "none"  # 记录匹配方式

        # ==================== 优先级 1：Provider IDs 精确匹配 ====================
        if history.server_data:
            provider_ids = history.server_data.get("ProviderIds", {})
            tmdb_id = provider_ids.get("Tmdb")
            imdb_id = provider_ids.get("Imdb")
            douban_id = provider_ids.get("Douban")

            if history.media_type == "movie":
                table_name = "unified_movies"

                # 1.1 优先用 TMDb ID 匹配
                if tmdb_id:
                    try:
                        query = select(UnifiedMovie.id).where(UnifiedMovie.tmdb_id == int(tmdb_id))
                        result = await db.execute(query)
                        unified_id = result.scalars().first()
                        if unified_id:
                            match_method = "tmdb_id"
                            logger.info(f"Matched by TMDb ID {tmdb_id}: {history.title}")
                    except (ValueError, TypeError):
                        pass

                # 1.2 其次用 IMDb ID 匹配
                if not unified_id and imdb_id:
                    query = select(UnifiedMovie.id).where(UnifiedMovie.imdb_id == imdb_id)
                    result = await db.execute(query)
                    unified_id = result.scalars().first()
                    if unified_id:
                        match_method = "imdb_id"
                        logger.info(f"Matched by IMDb ID {imdb_id}: {history.title}")

                # 1.3 最后用豆瓣 ID 匹配
                if not unified_id and douban_id:
                    query = select(UnifiedMovie.id).where(UnifiedMovie.douban_id == douban_id)
                    result = await db.execute(query)
                    unified_id = result.scalars().first()
                    if unified_id:
                        match_method = "douban_id"
                        logger.info(f"Matched by Douban ID {douban_id}: {history.title}")

            elif history.media_type == "tv":
                table_name = "unified_tv_series"

                # TV 系列同样的逻辑
                if tmdb_id:
                    try:
                        query = select(UnifiedTVSeries.id).where(UnifiedTVSeries.tmdb_id == int(tmdb_id))
                        result = await db.execute(query)
                        unified_id = result.scalars().first()
                        if unified_id:
                            match_method = "tmdb_id"
                            logger.info(f"Matched TV by TMDb ID {tmdb_id}: {history.title}")
                    except (ValueError, TypeError):
                        pass

                if not unified_id and imdb_id:
                    query = select(UnifiedTVSeries.id).where(UnifiedTVSeries.imdb_id == imdb_id)
                    result = await db.execute(query)
                    unified_id = result.scalars().first()
                    if unified_id:
                        match_method = "imdb_id"
                        logger.info(f"Matched TV by IMDb ID {imdb_id}: {history.title}")

                if not unified_id and douban_id:
                    query = select(UnifiedTVSeries.id).where(UnifiedTVSeries.douban_id == douban_id)
                    result = await db.execute(query)
                    unified_id = result.scalars().first()
                    if unified_id:
                        match_method = "douban_id"
                        logger.info(f"Matched TV by Douban ID {douban_id}: {history.title}")

        # ==================== 优先级 2：文件路径映射匹配 ====================
        if not unified_id and history.server_data and config:
            server_file_path = history.server_data.get("Path")
            if server_file_path and config.library_path_mappings:
                # 应用路径映射
                local_path = apply_path_mappings(server_file_path, config.library_path_mappings)

                if local_path:
                    # 直接按路径查找媒体文件
                    query = select(MediaFile).where(MediaFile.file_path == local_path)
                    result = await db.execute(query)
                    matched_file = result.scalars().first()

                    if matched_file:
                        # 找到文件，直接使用其关联的统一资源
                        history.media_file_id = matched_file.id
                        if matched_file.unified_table_name and matched_file.unified_resource_id:
                            history.unified_table_name = matched_file.unified_table_name
                            history.unified_resource_id = matched_file.unified_resource_id
                            unified_id = matched_file.unified_resource_id
                            table_name = matched_file.unified_table_name
                            match_method = "path_mapping"
                            logger.info(
                                f"✅ Matched by path mapping: {server_file_path} -> {local_path}"
                            )
                            await db.commit()
                            return  # 路径映射成功，直接返回
                    else:
                        logger.debug(f"Path mapped but file not found in database: {local_path}")

        # ==================== 优先级 3：标题+年份匹配 ====================
        if not unified_id:
            if history.media_type == "movie":
                table_name = "unified_movies"

                # 2.1 精确标题匹配
                query = select(UnifiedMovie.id).where(UnifiedMovie.title.ilike(history.title))
                if history.year:
                    query = query.where(UnifiedMovie.year == history.year)
                result = await db.execute(query)
                unified_id = result.scalars().first()
                if unified_id:
                    match_method = "title_exact"
                    logger.info(f"Matched by exact title: {history.title}")

                # 2.2 模糊标题匹配（回退）
                if not unified_id:
                    query = select(UnifiedMovie.id).where(UnifiedMovie.title.ilike(f"%{history.title}%"))
                    if history.year:
                        query = query.where(UnifiedMovie.year == history.year)
                    result = await db.execute(query)
                    unified_id = result.scalars().first()
                    if unified_id:
                        match_method = "title_fuzzy"
                        logger.info(f"Matched by fuzzy title: {history.title}")

            elif history.media_type == "tv":
                table_name = "unified_tv_series"

                # TV 系列同样的逻辑
                query = select(UnifiedTVSeries.id).where(UnifiedTVSeries.title.ilike(history.title))
                if history.year:
                    query = query.where(UnifiedTVSeries.year == history.year)
                result = await db.execute(query)
                unified_id = result.scalars().first()
                if unified_id:
                    match_method = "title_exact"
                    logger.info(f"Matched TV by exact title: {history.title}")

                if not unified_id:
                    query = select(UnifiedTVSeries.id).where(UnifiedTVSeries.title.ilike(f"%{history.title}%"))
                    if history.year:
                        query = query.where(UnifiedTVSeries.year == history.year)
                    result = await db.execute(query)
                    unified_id = result.scalars().first()
                    if unified_id:
                        match_method = "title_fuzzy"
                        logger.info(f"Matched TV by fuzzy title: {history.title}")

        # ==================== 更新统一资源关联 ====================
        if unified_id:
            history.unified_table_name = table_name
            history.unified_resource_id = unified_id

            # ==================== 匹配本地文件 ====================
            # 3.1 优先通过统一资源关联匹配
            file_query = select(MediaFile).where(
                and_(
                    MediaFile.unified_table_name == table_name,
                    MediaFile.unified_resource_id == unified_id
                )
            )

            # 如果是电视剧，进一步匹配季和集
            if history.media_type == "tv":
                if history.season_number:
                    file_query = file_query.where(MediaFile.season_number == history.season_number)
                if history.episode_number:
                    file_query = file_query.where(MediaFile.episode_number == history.episode_number)

            file_result = await db.execute(file_query)
            matched_file = file_result.scalars().first()

            if matched_file:
                history.media_file_id = matched_file.id
                logger.info(
                    f"✅ Matched viewing history to local file ({match_method}): "
                    f"{history.title} -> {matched_file.file_path}"
                )
            else:
                logger.info(
                    f"⚠️  Matched to unified resource ({match_method}) {table_name}:{unified_id}, "
                    f"but no matching local file found yet: {history.title}"
                )

            await db.commit()
        else:
            logger.warning(f"❌ Failed to match viewing history: {history.title} ({history.year})")


    @staticmethod
    async def get_user_watch_history(
        db: AsyncSession,
        user_id: int,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[List[MediaServerWatchHistory], int]:
        """
        查询用户观看历史

        Args:
            db: 数据库会话
            user_id: 用户ID
            filters: 过滤条件
                - config_id: 媒体服务器配置ID
                - media_type: 媒体类型
                - is_completed: 是否看完
            limit: 每页数量
            offset: 偏移量

        Returns:
            Tuple[List[MediaServerWatchHistory], int]: (记录列表, 总数)
        """
        query = select(MediaServerWatchHistory).where(MediaServerWatchHistory.user_id == user_id)

        # 应用过滤条件
        if filters:
            if filters.get("config_id"):
                query = query.where(MediaServerWatchHistory.media_server_config_id == filters["config_id"])
            if filters.get("media_type"):
                query = query.where(MediaServerWatchHistory.media_type == filters["media_type"])
            if filters.get("is_completed") is not None:
                query = query.where(MediaServerWatchHistory.is_completed == filters["is_completed"])
        
        # ==================== 应用媒体库排除过滤（强制生效） ====================
        config_id_filter = filters.get("config_id") if filters else None
        
        if config_id_filter:
            # 特定服务器视图：仅应用该服务器的排除规则
            excluded_ids = await MediaServerConfigService.get_excluded_library_ids(db, config_id_filter)
            if excluded_ids:
                query = query.where(or_(
                    MediaServerWatchHistory.library_id == None,
                    MediaServerWatchHistory.library_id.not_in(excluded_ids)
                ))
        else:
            # “仪表盘”或”全部服务器”视图：应用该用户所有服务器配置各自的排除规则
            configs = await MediaServerConfigService.get_by_user_id(db, user_id)
            exclusion_clauses = []
            for config in configs:
                ex_ids = await MediaServerConfigService.get_excluded_library_ids(db, config.id)
                if ex_ids:
                    exclusion_clauses.append(
                        and_(
                            MediaServerWatchHistory.media_server_config_id == config.id,
                            MediaServerWatchHistory.library_id.in_(ex_ids)
                        )
                    )

            if exclusion_clauses:
                query = query.where(not_(or_(*exclusion_clauses)))

        # 获取总数
        from sqlalchemy import func

        count_query = select(func.count()).select_from(query.subquery())
        count_result = await db.execute(count_query)
        total = count_result.scalar()

        # 分页和排序
        query = query.order_by(desc(MediaServerWatchHistory.last_played_at)).limit(limit).offset(offset)

        result = await db.execute(query)
        items = list(result.scalars().all())

        # 获取配置以构建完整图片 URL
        config_map = {}
        
        # 获取关联信息并计算字段
        for item in items:
            # 获取服务器配置
            if item.media_server_config_id not in config_map:
                config = await MediaServerConfigService.get_by_id(db, item.media_server_config_id)
                if config:
                    config_map[item.media_server_config_id] = config
            
            config = config_map.get(item.media_server_config_id)
            if not config:
                continue

            # 设置服务器名称
            item.server_name = config.name

            # 计算进度和图片 URL (如果是 Jellyfin/Emby)
            if item.server_data:
                # 进度
                if item.is_completed:
                    item.playback_progress = 100.0
                elif item.runtime_seconds and item.play_duration_seconds:
                    item.playback_progress = round((item.play_duration_seconds / item.runtime_seconds) * 100, 1)
                
                # 构建服务器基础路径
                protocol = "https" if config.use_ssl else "http"
                base_url = f"{protocol}://{config.host}:{config.port}"

                # 图片 URL (Jellyfin/Emby 逻辑)
                image_tag = item.server_data.get("ImageTags", {}).get("Primary")
                if image_tag:
                    # 返回相对路径供前端代理使用
                    item.image_url = f"/Items/{item.server_item_id}/Images/Primary?tag={image_tag}"
                elif item.server_data.get("ParentThumbItemId") and item.server_data.get("ParentThumbImageTag"):
                    # 剧集可能使用季或剧的海报
                    parent_id = item.server_data.get("ParentThumbItemId")
                    parent_tag = item.server_data.get("ParentThumbImageTag")
                    item.image_url = f"/Items/{parent_id}/Images/Primary?tag={parent_tag}"

                # 构建 Web 播放/详情跳转链接
                if config.type in ["jellyfin", "emby"]:
                    item.playback_url = f"{base_url}/web/index.html#!/details?id={item.server_item_id}"
                elif config.type == "plex":
                    # Plex 的详情页面链接由 metadata 键值构成
                    # 这里的 server_item_id 应当是 metadataId
                    # 对于 Plex 图片，目前尚未完全实现获取逻辑，暂留空或后续完善
                    # item.image_url = ... (Plex handled differently)
                    item.playback_url = f"{base_url}/web/index.html#!/server/{config.server_config.get('machineIdentifier', '')}/details?key=%2Flibrary%2Fmetadata%2F{item.server_item_id}"

        return items, total

    @staticmethod
    async def get_watch_statistics(db: AsyncSession, user_id: int) -> Dict[str, Any]:
        """
        获取观看统计

        Args:
            db: 数据库会话
            user_id: 用户ID

        Returns:
            Dict: 统计信息
        """
        from sqlalchemy import func

        # 总观看次数
        total_query = select(func.count()).where(MediaServerWatchHistory.user_id == user_id)
        total_result = await db.execute(total_query)
        total_count = total_result.scalar()

        # 已完成数量
        completed_query = select(func.count()).where(
            and_(MediaServerWatchHistory.user_id == user_id, MediaServerWatchHistory.is_completed == True)
        )
        completed_result = await db.execute(completed_query)
        completed_count = completed_result.scalar()

        # 按媒体类型统计
        type_query = select(MediaServerWatchHistory.media_type, func.count()).where(
            MediaServerWatchHistory.user_id == user_id
        ).group_by(MediaServerWatchHistory.media_type)
        type_result = await db.execute(type_query)
        by_type = {row[0]: row[1] for row in type_result.all()}

        return {"total_count": total_count, "completed_count": completed_count, "by_type": by_type}

    @staticmethod
    def _extract_media_type(server_data: Dict[str, Any]) -> str:
        """
        从服务器数据提取媒体类型

        Args:
            server_data: 服务器原始数据

        Returns:
            str: 媒体类型（movie/tv/music）
        """
        item_type = server_data.get("Type", "").lower()

        if item_type == "movie":
            return "movie"
        elif item_type in ["episode", "series"]:
            return "tv"
        elif item_type in ["audio", "musicalbum"]:
            return "music"
        else:
            return "unknown"
