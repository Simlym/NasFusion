# -*- coding: utf-8 -*-
"""
媒体服务器媒体库同步任务处理器（通用）
同步媒体服务器中的所有媒体项到本地数据库
"""
import logging
from typing import Dict, Any, List

from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from app.tasks.base import BaseTaskHandler
from app.services.media_server.media_server_item_service import MediaServerItemService
from app.services.media_server.media_server_config_service import MediaServerConfigService
from app.services.task.task_execution_service import TaskExecutionService
# get_media_server_adapter 通过 MediaServerConfigService.get_adapter 调用
from app.constants.media import MEDIA_TYPE_MOVIE, MEDIA_TYPE_TV
from app.utils.timezone import parse_datetime

logger = logging.getLogger(__name__)


class MediaServerLibrarySyncHandler(BaseTaskHandler):
    """媒体服务器媒体库同步任务（通用）"""

    @staticmethod
    async def execute(
        db: AsyncSession,
        params: Dict[str, Any],
        execution_id: int,
    ) -> Dict[str, Any]:
        """
        执行媒体库同步

        Args:
            db: 数据库会话
            params: 处理器参数
                - media_server_config_id: 媒体服务器配置ID (可选，不传则同步所有已启用的服务器)
                - library_ids: 要同步的媒体库ID列表 (可选，不传则同步所有)
                - match_files: 是否匹配本地文件 (可选，默认 True)
                - sync_mode: 同步模式 (可选，full/incremental，默认 full)
                - incremental_hours: 增量同步时间范围（小时）(可选，默认 24)
            execution_id: 任务执行ID

        Returns:
            同步结果
        """
        media_server_config_id = params.get("media_server_config_id")
        library_ids = params.get("library_ids")
        match_files = params.get("match_files", True)
        sync_mode = params.get("sync_mode", "full")  # full 或 incremental
        incremental_hours = params.get("incremental_hours", 24)

        if media_server_config_id:
            # 同步单个服务器
            return await MediaServerLibrarySyncHandler._sync_single_server(
                db, execution_id, media_server_config_id, library_ids, match_files, sync_mode, incremental_hours
            )
        else:
            # 全局同步：同步所有已启用自动刷新的服务器
            return await MediaServerLibrarySyncHandler._sync_all_servers(
                db, execution_id, match_files, sync_mode, incremental_hours
            )

    @staticmethod
    async def _sync_all_servers(
        db: AsyncSession,
        execution_id: int,
        match_files: bool = True,
        sync_mode: str = "full",
        incremental_hours: int = 24
    ) -> Dict[str, Any]:
        """
        全局同步：同步所有已启用自动刷新的媒体服务器

        Args:
            db: 数据库会话
            execution_id: 任务执行ID
            match_files: 是否匹配本地文件
            sync_mode: 同步模式
            incremental_hours: 增量同步时间范围

        Returns:
            同步结果
        """
        # 获取所有启用自动刷新的媒体服务器
        configs = await MediaServerConfigService.get_all_with_auto_refresh_enabled(db)
        if not configs:
            await TaskExecutionService.append_log(db, execution_id, "没有启用媒体库自动刷新的媒体服务器")
            return {"synced_count": 0, "server_count": 0}

        await TaskExecutionService.append_log(
            db, execution_id, f"发现 {len(configs)} 个已启用自动刷新的媒体服务器，开始同步..."
        )

        total_synced = 0
        total_new = 0
        total_updated = 0
        total_matched = 0
        total_deactivated = 0
        success_count = 0

        for i, config in enumerate(configs):
            await TaskExecutionService.append_log(
                db, execution_id, f"[{i+1}/{len(configs)}] 正在同步: {config.name} ({config.type})..."
            )

            try:
                res = await MediaServerLibrarySyncHandler._sync_single_server(
                    db, execution_id, config.id, None, match_files, sync_mode, incremental_hours, sub_task=True
                )
                total_synced += res.get("synced_count", 0)
                total_new += res.get("new_count", 0)
                total_updated += res.get("updated_count", 0)
                total_matched += res.get("matched_file_count", 0)
                total_deactivated += res.get("deactivated_count", 0)
                success_count += 1

                await TaskExecutionService.append_log(
                    db, execution_id,
                    f"  - 完成: 新增 {res.get('new_count', 0)}, 更新 {res.get('updated_count', 0)}, 匹配 {res.get('matched_file_count', 0)}"
                )
            except Exception as e:
                await TaskExecutionService.append_log(
                    db, execution_id, f"  - 失败: {str(e)}"
                )
                logger.error(f"Failed to sync library for {config.name}: {str(e)}")

            # 更新整体进度
            progress = int((i + 1) / len(configs) * 100)
            await TaskExecutionService.update_progress(db, execution_id, progress)

        summary = {
            "synced_count": total_synced,
            "new_count": total_new,
            "updated_count": total_updated,
            "deactivated_count": total_deactivated,
            "matched_file_count": total_matched,
            "server_count": len(configs),
            "success_count": success_count
        }

        await TaskExecutionService.append_log(
            db, execution_id,
            f"全局同步完成: 共同步 {total_synced} 项 ({success_count}/{len(configs)} 个服务器成功)"
        )

        return summary

    @staticmethod
    async def _sync_single_server(
        db: AsyncSession,
        execution_id: int,
        media_server_config_id: int,
        library_ids: List[str] = None,
        match_files: bool = True,
        sync_mode: str = "full",
        incremental_hours: int = 24,
        sub_task: bool = False
    ) -> Dict[str, Any]:
        """
        同步单个媒体服务器的媒体库

        Args:
            db: 数据库会话
            execution_id: 任务执行ID
            media_server_config_id: 媒体服务器配置ID
            library_ids: 要同步的媒体库ID列表
            match_files: 是否匹配本地文件
            sync_mode: 同步模式
            incremental_hours: 增量同步时间范围
            sub_task: 是否作为子任务执行（影响日志输出格式）

        Returns:
            同步结果
        """
        # 获取配置
        config = await MediaServerConfigService.get_by_id(db, media_server_config_id)
        if not config:
            raise ValueError(f"Media server config not found: {media_server_config_id}")

        sync_mode_text = "增量同步" if sync_mode == "incremental" else "全量同步"
        if not sub_task:
            if sync_mode == "incremental":
                await TaskExecutionService.append_log(
                    db, execution_id, f"开始{sync_mode_text}媒体库: {config.name} ({config.type}) - 最近{incremental_hours}小时"
                )
            else:
                await TaskExecutionService.append_log(
                    db, execution_id, f"开始{sync_mode_text}媒体库: {config.name} ({config.type})"
                )

        # 获取适配器
        adapter = MediaServerConfigService.get_adapter(config)

        # 测试连接
        if not await adapter.test_connection():
            raise ConnectionError(f"无法连接到媒体服务器: {config.name}")

        # 获取媒体库列表
        libraries = await adapter.get_libraries()
        if not sub_task:
            await TaskExecutionService.append_log(db, execution_id, f"发现 {len(libraries)} 个媒体库")

        # 过滤要同步的媒体库
        if library_ids:
            libraries = [lib for lib in libraries if lib["id"] in library_ids]
            if not sub_task:
                await TaskExecutionService.append_log(db, execution_id, f"筛选后需要同步 {len(libraries)} 个媒体库")

        if not libraries:
            return {
                "synced_count": 0,
                "new_count": 0,
                "updated_count": 0,
                "deactivated_count": 0,
                "matched_file_count": 0,
            }

        # 同步所有媒体项
        total_synced = 0
        total_new = 0
        total_updated = 0
        total_matched = 0
        all_active_item_ids = []

        for i, library in enumerate(libraries):
            library_id = library["id"]
            library_name = library["name"]
            # collectionType 可能为 movies, tvsub, music, books, trailers, homevideos, boxsets, mixed
            library_type = library.get("collectionType", "").lower()

            # 跳过不支持的媒体库类型（避免查询视频字段导致 500 错误）
            if library_type in ["books", "music", "photos"]:
                if not sub_task:
                    await TaskExecutionService.append_log(
                        db, execution_id, f"[{i+1}/{len(libraries)}] 跳过媒体库: {library_name} (类型: {library_type} 不支持)"
                    )
                continue

            if not sub_task:
                await TaskExecutionService.append_log(
                    db, execution_id, f"[{i+1}/{len(libraries)}] 正在同步媒体库: {library_name} ({library_type})..."
                )

            try:
                # 获取该媒体库中的所有媒体项
                items = await MediaServerLibrarySyncHandler._fetch_library_items(
                    adapter, library_id, config, sync_mode, incremental_hours
                )

                if not sub_task:
                    if sync_mode == "incremental":
                        await TaskExecutionService.append_log(
                            db, execution_id, f"  - 获取到 {len(items)} 个媒体项 (增量: 最近{incremental_hours}小时内修改)"
                        )
                    else:
                        await TaskExecutionService.append_log(
                            db, execution_id, f"  - 获取到 {len(items)} 个媒体项 (全量)"
                        )

                # 批量同步到数据库
                for item_data in items:
                    try:
                        item, is_new = await MediaServerItemService.create_or_update(
                            db, media_server_config_id, item_data["server_item_id"], item_data
                        )
                        all_active_item_ids.append(item_data["server_item_id"])

                        if is_new:
                            total_new += 1
                        else:
                            total_updated += 1

                        total_synced += 1

                        # 匹配本地文件
                        if match_files and item.file_path:
                            path_mappings = config.library_path_mappings if config.library_path_mappings else []
                            media_file = await MediaServerItemService.match_media_file_by_path(
                                db, item, path_mappings
                            )
                            if media_file:
                                await MediaServerItemService.update_associations(db, item, media_file)
                                total_matched += 1

                    except Exception as e:
                        logger.error(f"Failed to sync item {item_data.get('server_item_id')}: {str(e)}")

                if not sub_task:
                    await TaskExecutionService.append_log(
                        db, execution_id, f"  - 完成: 新增 {total_new}, 更新 {total_updated}"
                    )

            except Exception as e:
                if not sub_task:
                    await TaskExecutionService.append_log(
                        db, execution_id, f"  - 失败: {str(e)}"
                    )
                logger.error(f"Failed to sync library {library_name}: {str(e)}")

            # 更新进度（仅在非子任务模式下）
            if not sub_task:
                progress = int((i + 1) / len(libraries) * 90)  # 90% 用于同步，10% 用于清理
                await TaskExecutionService.update_progress(db, execution_id, progress)

        # 标记已删除的媒体项为非活跃
        # 注意：增量同步时不执行停用逻辑，因为增量同步只返回最近修改的项，不是完整列表
        deactivated_count = 0
        if sync_mode == "full":
            if not sub_task:
                await TaskExecutionService.append_log(db, execution_id, "正在清理已删除的媒体项...")
            deactivated_count = await MediaServerItemService.deactivate_stale_items(
                db, media_server_config_id, all_active_item_ids
            )
        else:
            if not sub_task:
                await TaskExecutionService.append_log(db, execution_id, "增量同步模式，跳过清理步骤")

        if not sub_task:
            await TaskExecutionService.update_progress(db, execution_id, 100)

        result = {
            "synced_count": total_synced,
            "new_count": total_new,
            "updated_count": total_updated,
            "deactivated_count": deactivated_count,
            "matched_file_count": total_matched,
        }

        if not sub_task:
            await TaskExecutionService.append_log(
                db,
                execution_id,
                f"同步完成: 总计 {total_synced} 项 (新增 {total_new}, 更新 {total_updated}, 停用 {deactivated_count}, 匹配 {total_matched})",
            )

        return result

    @staticmethod
    async def _fetch_library_items(
        adapter, library_id: str, config, sync_mode: str = "full", incremental_hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        从媒体服务器获取指定媒体库的所有媒体项

        Args:
            adapter: 媒体服务器适配器
            library_id: 媒体库ID
            config: 媒体服务器配置
            sync_mode: 同步模式（full/incremental）
            incremental_hours: 增量同步时间范围（小时）

        Returns:
            List[Dict]: 标准化的媒体项列表
        """
        items = []

        # 计算增量同步的截止时间（用于客户端过滤）
        # 注意：Jellyfin API 不可靠地支持 MinDateLastSaved 参数，所以改用客户端过滤
        cutoff_datetime = None
        if sync_mode == "incremental":
            from datetime import timedelta
            from app.utils.timezone import now
            cutoff_datetime = now() - timedelta(hours=incremental_hours)
            logger.info(
                f"Incremental sync for library {library_id}: "
                f"will filter items created/modified after {cutoff_datetime.isoformat()}"
            )

        # 获取用户ID
        users = await adapter.get_users()
        if not users:
            raise ValueError("No users found in media server")
        user_id = users[0]["id"]

        # 构建 API 请求（Jellyfin/Emby 通用）
        protocol = "https" if config.use_ssl else "http"
        base_url = f"{protocol}://{config.host}:{config.port}"

        # 分批获取所有项（避免一次性加载过多）
        start_index = 0
        batch_size = 500

        # 定义字段集（从完整到最小，用于降级重试）
        # 添加 DateCreated 字段用于增量同步的客户端过滤
        field_sets = [
            # 完整字段集
            "Path,ProviderIds,ProductionYear,PremiereDate,CommunityRating,CriticRating,OfficialRating,Overview,Genres,Studios,Tags,People,MediaStreams,RunTimeTicks,ParentId,SeriesId,SeriesName,SeasonId,ParentIndexNumber,IndexNumber,UserData,DateCreated",
            # 中等字段集（移除 People 和 MediaStreams，这些字段最容易导致服务器端错误）
            "Path,ProviderIds,ProductionYear,PremiereDate,CommunityRating,OfficialRating,Overview,Genres,Studios,Tags,RunTimeTicks,ParentId,SeriesId,SeriesName,SeasonId,ParentIndexNumber,IndexNumber,UserData,DateCreated",
            # 最小字段集（仅保留核心字段）
            "Path,ProviderIds,ProductionYear,PremiereDate,Overview,RunTimeTicks,ParentId,SeriesId,SeriesName,SeasonId,ParentIndexNumber,IndexNumber,UserData,DateCreated",
        ]

        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
            while True:
                base_params = {
                    "ParentId": library_id,
                    "Recursive": "true",
                    "StartIndex": start_index,
                    "Limit": batch_size,
                    "IncludeItemTypes": "Movie,Episode,Series,Season",
                }

                # 增量同步时按 DateCreated 降序排序，这样可以尽早遇到旧项并停止
                if sync_mode == "incremental":
                    base_params["SortBy"] = "DateCreated"
                    base_params["SortOrder"] = "Descending"

                # 尝试不同的字段集，从完整到最小
                data = None
                last_error = None
                fallback_to_full_sync = False

                for field_set_index, fields in enumerate(field_sets):
                    try:
                        params = base_params.copy()
                        params["Fields"] = fields

                        response = await client.get(
                            f"{base_url}/Users/{user_id}/Items",
                            headers={"X-Emby-Token": adapter.api_key},
                            params=params,
                        )
                        response.raise_for_status()
                        data = response.json()

                        # 第一批次时记录请求参数和返回的总数量
                        if start_index == 0 and field_set_index == 0:
                            total_record_count = data.get("TotalRecordCount", 0)
                            logger.info(
                                f"Library {library_id} first batch: "
                                f"TotalRecordCount={total_record_count}, "
                                f"sync_mode={sync_mode}"
                            )

                        # 如果使用了降级字段集，记录警告
                        if field_set_index > 0:
                            logger.warning(
                                f"Library {library_id}: Used fallback field set #{field_set_index + 1} "
                                f"(removed fields from previous attempt)"
                            )
                        break

                    except httpx.HTTPStatusError as e:
                        last_error = e
                        # 只有500错误才尝试降级，其他错误直接抛出
                        if e.response.status_code == 500:
                            logger.warning(
                                f"Library {library_id} batch {start_index}: "
                                f"Server error with field set #{field_set_index + 1}, "
                                f"trying with fewer fields..."
                            )
                            continue
                        else:
                            raise
                    except Exception as e:
                        # 网络错误等其他异常直接抛出
                        logger.error(f"Library {library_id} batch {start_index}: {str(e)}")
                        raise

                # 如果所有字段集都失败，抛出错误
                if data is None:
                    logger.error(
                        f"Library {library_id} batch {start_index}: "
                        f"Failed with all field sets, last error: {last_error}"
                    )
                    raise last_error

                batch_items = data.get("Items", [])
                if not batch_items:
                    break

                # 增量同步：客户端过滤，只保留最近创建/修改的项
                # 由于按 DateCreated 降序排序，遇到旧项时可以提前退出
                should_stop_early = False
                
                for raw_item in batch_items:
                    try:
                        # 增量同步时检查 DateCreated
                        if cutoff_datetime:
                            date_created_str = raw_item.get("DateCreated")
                            if date_created_str:
                                item_date = parse_datetime(date_created_str)
                                if item_date and item_date < cutoff_datetime:
                                    # 由于按日期降序排序，后续都是更旧的项，可以提前停止
                                    should_stop_early = True
                                    break
                        
                        item_data = MediaServerLibrarySyncHandler._normalize_item(raw_item, config, library_id)
                        items.append(item_data)
                    except Exception as e:
                        item_id = raw_item.get("Id", "unknown")
                        logger.error(f"Failed to normalize item {item_id}: {str(e)}")
                        # 继续处理其他项，不因单个项失败而中断

                # 如果增量同步遇到旧项，提前停止获取
                if should_stop_early:
                    logger.info(
                        f"Library {library_id}: Incremental sync stopped early, "
                        f"found {len(items)} items created after {cutoff_datetime.isoformat()}"
                    )
                    break

                # 检查是否还有更多数据
                total_count = data.get("TotalRecordCount", 0)
                start_index += batch_size
                if start_index >= total_count:
                    break

                logger.debug(f"Fetched {len(items)}/{total_count} items from library {library_id}")

        return items

    @staticmethod
    def _normalize_item(raw_item: Dict[str, Any], config, library_id: str) -> Dict[str, Any]:
        """
        将媒体服务器原始数据转换为标准格式

        Args:
            raw_item: 媒体服务器原始媒体项
            config: 媒体服务器配置
            library_id: 媒体库ID

        Returns:
            Dict: 标准化的媒体项数据
        """
        item_type = raw_item.get("Type", "")

        # 映射媒体类型
        media_type = "other"
        if item_type == "Movie":
            media_type = MEDIA_TYPE_MOVIE
        elif item_type in ["Episode", "Series", "Season"]:
            media_type = MEDIA_TYPE_TV

        # 提取文件路径（仅对具体媒体文件）
        file_path = None
        file_size = None
        if item_type in ["Movie", "Episode"]:
            file_path = raw_item.get("Path")
            media_sources = raw_item.get("MediaSources", [])
            if media_sources:
                file_size = media_sources[0].get("Size")

        # 提取播放统计
        user_data = raw_item.get("UserData", {})
        play_count = user_data.get("PlayCount", 0)
        last_played_at = user_data.get("LastPlayedDate")
        is_favorite = user_data.get("IsFavorite", False)

        # 解析播放时间
        if last_played_at:
            try:
                last_played_at = parse_datetime(last_played_at)
            except:
                last_played_at = None

        # 提取技术信息
        runtime_ticks = raw_item.get("RunTimeTicks")
        runtime_seconds = int(runtime_ticks / 10000000) if runtime_ticks else None

        # 提取视频信息（MediaStreams 字段可能因降级而缺失）
        resolution = None
        video_codec = None
        audio_codec = None
        media_streams = raw_item.get("MediaStreams")
        if media_streams:
            try:
                for stream in media_streams:
                    if stream.get("Type") == "Video":
                        height = stream.get("Height")
                        if height:
                            if height >= 2160:
                                resolution = "2160p"
                            elif height >= 1080:
                                resolution = "1080p"
                            elif height >= 720:
                                resolution = "720p"
                        video_codec = stream.get("Codec")
                    elif stream.get("Type") == "Audio":
                        audio_codec = stream.get("Codec")
            except Exception as e:
                logger.debug(f"Failed to parse media streams: {e}")

        # 提取外部ID
        provider_ids = raw_item.get("ProviderIds", {})
        tmdb_id = provider_ids.get("Tmdb")
        imdb_id = provider_ids.get("Imdb")
        tvdb_id = provider_ids.get("Tvdb")

        # 转换为整数
        if tmdb_id:
            try:
                tmdb_id = int(tmdb_id)
            except:
                tmdb_id = None
        if tvdb_id:
            try:
                tvdb_id = int(tvdb_id)
            except:
                tvdb_id = None

        # 提取图片路径
        image_tags = raw_item.get("ImageTags", {})
        images = {}
        for img_type, tag in image_tags.items():
            images[img_type] = f"/Items/{raw_item.get('Id')}/Images/{img_type}"

        # 提取人员信息（可能因字段降级而缺失）
        people = raw_item.get("People", []) if "People" in raw_item else None

        # 提取流派（转换为字符串数组，可能因字段降级而缺失）
        genres = None
        genres_raw = raw_item.get("Genres")
        if genres_raw:
            try:
                if isinstance(genres_raw, list):
                    genres = [g if isinstance(g, str) else (g.get("Name", "") if isinstance(g, dict) else str(g)) for g in genres_raw]
            except Exception as e:
                logger.debug(f"Failed to parse genres: {e}")

        # 提取工作室（转换为字符串数组，可能因字段降级而缺失）
        studios = None
        studios_raw = raw_item.get("Studios")
        if studios_raw:
            try:
                if isinstance(studios_raw, list):
                    studios = [s.get("Name", "") if isinstance(s, dict) else str(s) for s in studios_raw]
            except Exception as e:
                logger.debug(f"Failed to parse studios: {e}")

        # 提取标签（转换为字符串数组，可能因字段降级而缺失）
        tags = None
        tags_raw = raw_item.get("Tags")
        if tags_raw:
            try:
                if isinstance(tags_raw, list):
                    tags = [t if isinstance(t, str) else str(t) for t in tags_raw]
            except Exception as e:
                logger.debug(f"Failed to parse tags: {e}")

        # 解析首映日期
        premiere_date = raw_item.get("PremiereDate")
        if premiere_date:
            try:
                premiere_date = parse_datetime(premiere_date)
            except:
                premiere_date = None

        # 解析加入媒体库时间
        date_created = raw_item.get("DateCreated")
        if date_created:
            try:
                date_created = parse_datetime(date_created)
            except:
                date_created = None

        return {
            "server_type": config.type,
            "server_item_id": raw_item.get("Id"),
            "library_id": raw_item.get("ParentId") if item_type != "Movie" else library_id,
            "item_type": item_type,
            "media_type": media_type,
            "name": raw_item.get("Name", ""),
            "sort_name": raw_item.get("SortName"),
            "original_name": raw_item.get("OriginalTitle"),
            "year": raw_item.get("ProductionYear"),
            "premiere_date": premiere_date,
            "date_created": date_created,
            # 电视剧特定字段
            "series_id": raw_item.get("SeriesId"),
            "series_name": raw_item.get("SeriesName"),
            "season_id": raw_item.get("SeasonId"),
            "season_number": raw_item.get("ParentIndexNumber"),
            "episode_number": raw_item.get("IndexNumber"),
            # 文件信息
            "file_path": file_path,
            "file_size": file_size,
            # 外部ID
            "tmdb_id": tmdb_id,
            "imdb_id": imdb_id,
            "tvdb_id": tvdb_id,
            # 播放统计
            "play_count": play_count,
            "last_played_at": last_played_at,
            "is_favorite": is_favorite,
            # 技术信息
            "runtime_ticks": runtime_ticks,
            "runtime_seconds": runtime_seconds,
            "resolution": resolution,
            "video_codec": video_codec,
            "audio_codec": audio_codec,
            # 元数据
            "overview": raw_item.get("Overview"),
            "community_rating": str(raw_item.get("CommunityRating")) if raw_item.get("CommunityRating") else None,
            "critic_rating": str(raw_item.get("CriticRating")) if raw_item.get("CriticRating") else None,
            "official_rating": raw_item.get("OfficialRating"),
            "images": images if images else None,
            "people": people if people else None,
            "genres": genres if genres else None,
            "studios": studios if studios else None,
            "tags": tags if tags else None,
            # 原始数据
            "server_data": raw_item,
        }
