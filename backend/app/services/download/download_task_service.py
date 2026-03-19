# -*- coding: utf-8 -*-
"""
下载任务服务
"""
import hashlib
import logging
import os
from datetime import datetime
from app.utils.timezone import now
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.pt_sites import get_adapter
from app.constants import (
    AUTH_TYPE_COOKIE,
    AUTH_TYPE_PASSKEY,
    AUTH_TYPE_USER_PASS,
    HR_STRATEGY_AUTO_LIMIT,
    TASK_STATUS_DOWNLOADING,
    TASK_STATUS_ERROR,
    TASK_STATUS_PENDING,
)
from app.core.config import settings
from app.models.download_task import DownloadTask
from app.models.downloader_config import DownloaderConfig
from app.models.pt_resource import PTResource
from app.models.pt_site import PTSite
from app.schemas.downloader import DownloadTaskCreate
from app.services.download.downloader_config_service import DownloaderConfigService
from app.services.pt.pt_site_service import PTSiteService

logger = logging.getLogger(__name__)


class DownloadTaskService:
    """下载任务服务"""

    @staticmethod
    def _ensure_torrent_dir():
        """确保种子文件目录存在"""
        torrent_dir = Path(settings.DATA_DIR) / "torrents"
        torrent_dir.mkdir(parents=True, exist_ok=True)
        return torrent_dir

    @staticmethod
    def _get_torrent_file_path(site_name: str, torrent_id: str) -> Path:
        """
        获取种子文件保存路径

        Args:
            site_name: 站点名称
            torrent_id: 种子ID

        Returns:
            种子文件路径
        """
        torrent_dir = DownloadTaskService._ensure_torrent_dir()
        site_dir = torrent_dir / site_name
        site_dir.mkdir(exist_ok=True)
        return site_dir / f"{torrent_id}.torrent"

    @staticmethod
    def _calculate_torrent_hash(torrent_data: bytes) -> str:
        """
        计算种子文件的 InfoHash

        Args:
            torrent_data: 种子文件字节流

        Returns:
            InfoHash (SHA1)
        """
        try:
            import bencodepy

            # 解析种子文件
            torrent_dict = bencodepy.decode(torrent_data)
            # 获取 info 字典
            info_dict = torrent_dict[b"info"]
            # 计算 info 字典的 SHA1 hash
            info_encoded = bencodepy.encode(info_dict)
            info_hash = hashlib.sha1(info_encoded).hexdigest()
            return info_hash.lower()
        except Exception as e:
            logger.error(f"Error calculating torrent hash: {str(e)}")
            # 如果解析失败，使用整个文件的 SHA1
            return hashlib.sha1(torrent_data).hexdigest()

    @staticmethod
    def _extract_torrent_name(torrent_data: bytes, fallback_name: str = "") -> str:
        """
        从种子文件提取真实名字

        Args:
            torrent_data: 种子文件字节流
            fallback_name: 提取失败时的备用名字

        Returns:
            种子真实名字
        """
        try:
            import bencodepy

            # 解析种子文件
            torrent_dict = bencodepy.decode(torrent_data)
            # 获取 info 字典
            info_dict = torrent_dict[b"info"]
            # 提取名字字段
            torrent_name = info_dict.get(b"name", b"").decode("utf-8", errors="ignore")
            return torrent_name or fallback_name
        except Exception as e:
            logger.error(f"Error extracting torrent name: {str(e)}")
            return fallback_name

    @staticmethod
    async def create(db: AsyncSession, data: DownloadTaskCreate) -> DownloadTask:
        """
        创建下载任务

        工作流程：
        1. 验证 PT 资源和下载器配置
        2. 从 PT 站点下载种子文件
        3. 保存种子文件到本地
        4. 计算种子 hash
        5. 推送到下载器
        6. 创建数据库记录

        Args:
            db: 数据库会话
            data: 下载任务数据

        Returns:
            创建的下载任务
        """
        try:
            # 1. 获取 PT 资源
            result = await db.execute(
                select(PTResource).where(PTResource.id == data.pt_resource_id)
            )
            pt_resource = result.scalar_one_or_none()
            if not pt_resource:
                raise ValueError(f"PT资源不存在 (ID: {data.pt_resource_id})")

            # 2. 获取下载器配置
            downloader_config = await DownloaderConfigService.get_by_id(
                db, data.downloader_config_id
            )
            if not downloader_config:
                raise ValueError(f"下载器配置不存在 (ID: {data.downloader_config_id})")

            if not downloader_config.is_enabled:
                raise ValueError(f"下载器未启用: {downloader_config.name}")

            # 3. 获取 PT 站点
            result = await db.execute(
                select(PTSite).where(PTSite.id == pt_resource.site_id)
            )
            pt_site = result.scalar_one_or_none()
            if not pt_site:
                raise ValueError(f"PT站点不存在 (ID: {pt_resource.site_id})")

            # 4. 从 PT 站点下载种子文件
            logger.info(f"Downloading torrent from {pt_site.name}: {pt_resource.title}")

            # 准备适配器配置
            config = {
                "name": pt_site.name,
                "base_url": pt_site.base_url,
                "domain": pt_site.domain,
                "proxy_config": pt_site.proxy_config,
                "request_interval": pt_site.request_interval or 2,
            }

            # 添加认证信息（需要解密）
            # NexusPHP 站点通常需要同时使用 Cookie（网页认证）和 Passkey（下载认证）
            auth_info = PTSiteService.decrypt_auth_info(pt_site)
            if pt_site.auth_type == AUTH_TYPE_PASSKEY:
                config["auth_passkey"] = auth_info.get("auth_passkey")
            elif pt_site.auth_type == AUTH_TYPE_COOKIE:
                config["auth_cookie"] = auth_info.get("auth_cookie")
                # 对于 Cookie 认证的站点，也尝试获取 passkey（用于下载）
                if auth_info.get("auth_passkey"):
                    config["auth_passkey"] = auth_info.get("auth_passkey")
            elif pt_site.auth_type == AUTH_TYPE_USER_PASS:
                config["auth_username"] = auth_info.get("auth_username")
                config["auth_password"] = auth_info.get("auth_password")

            site_adapter = get_adapter(pt_site.type, config)

            # 打印调试信息
            logger.info(f"PT Resource torrent_id: {pt_resource.torrent_id} (type: {type(pt_resource.torrent_id)})")

            # 传递资源的 download_url（可能已包含认证信息）
            torrent_data = await site_adapter.download_torrent(
                pt_resource.torrent_id,
                download_url=pt_resource.download_url
            )

            # 5. 保存种子文件到本地
            torrent_file_path = DownloadTaskService._get_torrent_file_path(
                pt_site.name, pt_resource.torrent_id
            )
            with open(torrent_file_path, "wb") as f:
                f.write(torrent_data)
            logger.info(f"Saved torrent file to: {torrent_file_path}")

            # 6. 计算种子 hash 并提取真实名字
            task_hash = DownloadTaskService._calculate_torrent_hash(torrent_data)
            torrent_real_name = DownloadTaskService._extract_torrent_name(torrent_data, pt_resource.title)
            logger.info(f"Calculated torrent hash: {task_hash}")
            logger.info(f"种子真实名字: {torrent_real_name} (PT站点标题: {pt_resource.title})")

            # 7. 检查任务是否已存在
            result = await db.execute(
                select(DownloadTask).where(DownloadTask.task_hash == task_hash)
            )
            existing_task = result.scalar_one_or_none()
            if existing_task:
                logger.warning(f"Download task already exists with hash: {task_hash}")
                return existing_task

            # 8. 准备下载器适配器
            downloader_adapter = DownloaderConfigService._get_downloader_adapter(
                downloader_config
            )

            # 9. 准备下载选项
            download_options = {}

            # 设置分类
            if pt_resource.category:
                download_options["category"] = pt_resource.category

            # 设置标签
            tags = [pt_site.name]
            if pt_resource.is_free:
                tags.append("FREE")
            if pt_resource.has_hr:
                tags.append("HR")
            download_options["tags"] = ",".join(tags)

            # HR 处理：自动设置做种限制
            if pt_resource.has_hr and downloader_config.hr_strategy == HR_STRATEGY_AUTO_LIMIT:
                # 设置分享率限制
                if pt_resource.hr_ratio:
                    download_options["ratio_limit"] = float(pt_resource.hr_ratio)

                # 设置做种时长限制（转换为分钟）
                if pt_resource.hr_seed_time:
                    download_options["seeding_time_limit"] = pt_resource.hr_seed_time * 60

            # 如果用户指定了限制，使用用户指定的值
            if data.seeding_ratio_limit:
                download_options["ratio_limit"] = data.seeding_ratio_limit
            if data.seeding_time_limit:
                download_options["seeding_time_limit"] = data.seeding_time_limit * 60

            # 9.5. 如果未指定 save_path，使用挂载点系统自动选择
            if not data.save_path:
                logger.info("未指定保存路径，使用挂载点系统自动选择...")
                from app.services.storage.storage_mount_service import StorageMountService

                download_mounts = await StorageMountService.get_download_mounts_for_media(
                    db,
                    media_category=pt_resource.category
                )

                if not download_mounts:
                    raise ValueError(f"未找到媒体类型 {pt_resource.category} 的可用下载挂载点，请在存储配置中添加")

                # 使用推荐的第一个挂载点（同盘优先）
                data.save_path = download_mounts[0].container_path
                logger.info(f"自动选择下载挂载点: {download_mounts[0].name} ({data.save_path})")

            # 10. 推送到下载器
            logger.info(f"Adding torrent to downloader: {downloader_config.name}")
            try:
                result = await downloader_adapter.add_torrent_file(
                    torrent_data=torrent_data,
                    save_path=data.save_path,
                    **download_options,
                )
                logger.info(f"Torrent added to downloader: {result}")
            except Exception as e:
                logger.error(f"Failed to add torrent to downloader: {str(e)}")
                raise
            finally:
                await downloader_adapter.close()

            # 11. 自动推导 unified_table_name 和 unified_resource_id
            # 如果前端未传入，尝试从 resource_mappings 获取
            unified_table_name = data.unified_table_name
            unified_resource_id = data.unified_resource_id

            if not unified_table_name or not unified_resource_id:
                from app.models.resource_mapping import ResourceMapping
                mapping_query = select(ResourceMapping).where(
                    ResourceMapping.pt_resource_id == pt_resource.id
                )
                mapping_result = await db.execute(mapping_query)
                mapping = mapping_result.scalar_one_or_none()

                if mapping:
                    unified_table_name = mapping.unified_table_name
                    unified_resource_id = mapping.unified_resource_id
                    logger.info(
                        f"自动推导 unified 字段: {unified_table_name} ID={unified_resource_id}"
                    )

            # 12. 创建下载任务记录
            download_task = DownloadTask(
                task_hash=task_hash,
                pt_resource_id=pt_resource.id,
                downloader_config_id=downloader_config.id,
                media_type=pt_resource.category,
                unified_table_name=unified_table_name,
                unified_resource_id=unified_resource_id,
                client_type=downloader_config.type,
                client_task_id=task_hash,  # qBittorrent 使用 hash 作为任务ID
                torrent_file_path=str(torrent_file_path),
                torrent_name=torrent_real_name,  # 使用种子真实名字
                save_path=data.save_path,
                status=TASK_STATUS_PENDING,
                progress=0,
                total_size=pt_resource.size_bytes,
                downloaded_size=0,
                uploaded_size=0,
                ratio=0.0,
                auto_organize=data.auto_organize,
                organize_config_id=data.organize_config_id,
                storage_mount_id=data.storage_mount_id,
                keep_seeding=data.keep_seeding,
                seeding_time_limit=data.seeding_time_limit,
                seeding_ratio_limit=data.seeding_ratio_limit,
                has_hr=pt_resource.has_hr,
                hr_days=pt_resource.hr_days,
                hr_seed_time=pt_resource.hr_seed_time,
                hr_ratio=pt_resource.hr_ratio,
                added_at=now(),
                metadata_snapshot={
                    "site_name": pt_site.name,
                    "torrent_title": pt_resource.title,
                    "size": pt_resource.size_bytes,
                    "category": pt_resource.category,
                    "is_free": pt_resource.is_free,
                    "has_hr": pt_resource.has_hr,
                },
                client_config_snapshot={
                    "downloader_name": downloader_config.name,
                    "downloader_type": downloader_config.type,
                },
            )

            db.add(download_task)
            await db.commit()
            await db.refresh(download_task)

            logger.info(f"Created download task: {download_task.torrent_name} (ID: {download_task.id})")
            return download_task

        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating download task: {str(e)}")
            raise

    @staticmethod
    async def get_by_id(db: AsyncSession, task_id: int) -> Optional[DownloadTask]:
        """
        根据ID获取下载任务

        Args:
            db: 数据库会话
            task_id: 任务ID

        Returns:
            下载任务
        """
        result = await db.execute(
            select(DownloadTask).where(DownloadTask.id == task_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_pt_resource_id(db: AsyncSession, pt_resource_id: int) -> Optional[DownloadTask]:
        """
        根据PT资源ID获取下载任务

        Args:
            db: 数据库会话
            pt_resource_id: PT资源ID

        Returns:
            下载任务（若存在）
        """
        result = await db.execute(
            select(DownloadTask).where(DownloadTask.pt_resource_id == pt_resource_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_hash(db: AsyncSession, task_hash: str) -> Optional[DownloadTask]:
        """
        根据hash获取下载任务

        Args:
            db: 数据库会话
            task_hash: 任务hash

        Returns:
            下载任务
        """
        result = await db.execute(
            select(DownloadTask).where(DownloadTask.task_hash == task_hash)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
        media_type: Optional[str] = None,
        downloader_config_id: Optional[int] = None,
    ) -> Dict[str, any]:
        """
        获取下载任务列表

        Args:
            db: 数据库会话
            skip: 跳过数量
            limit: 限制数量
            status: 状态过滤
            media_type: 媒体类型过滤
            downloader_config_id: 下载器配置ID过滤

        Returns:
            包含总数和列表的字典
        """
        # 联查 PT 资源表以获取 subtitle
        query = (
            select(DownloadTask, PTResource.subtitle)
            .outerjoin(PTResource, DownloadTask.pt_resource_id == PTResource.id)
        )

        if status:
            query = query.where(DownloadTask.status == status)
        if media_type:
            query = query.where(DownloadTask.media_type == media_type)
        if downloader_config_id:
            query = query.where(DownloadTask.downloader_config_id == downloader_config_id)

        # 获取总数
        count_query = select(func.count()).select_from(
            query.subquery()
        )
        total = await db.scalar(count_query)

        # 获取列表
        query = query.offset(skip).limit(limit).order_by(DownloadTask.created_at.desc())
        result = await db.execute(query)
        rows = result.all()

        # 将结果转换为字典格式，包含 subtitle
        items = []
        for task, subtitle in rows:
            task_dict = {
                "id": task.id,
                "task_hash": task.task_hash,
                "pt_resource_id": task.pt_resource_id,
                "downloader_config_id": task.downloader_config_id,
                "media_type": task.media_type,
                "unified_table_name": task.unified_table_name,
                "unified_resource_id": task.unified_resource_id,
                "client_type": task.client_type,
                "client_task_id": task.client_task_id,
                "torrent_name": task.torrent_name,
                "subtitle": subtitle,  # 添加 subtitle 字段
                "save_path": task.save_path,
                "status": task.status,
                "progress": task.progress,
                "download_speed": task.download_speed,
                "upload_speed": task.upload_speed,
                "eta": task.eta,
                "total_size": task.total_size,
                "downloaded_size": task.downloaded_size,
                "uploaded_size": task.uploaded_size,
                "ratio": task.ratio,
                "auto_organize": task.auto_organize,
                "keep_seeding": task.keep_seeding,
                "seeding_time_limit": task.seeding_time_limit,
                "seeding_ratio_limit": task.seeding_ratio_limit,
                "has_hr": task.has_hr,
                "hr_days": task.hr_days,
                "hr_seed_time": task.hr_seed_time,
                "hr_ratio": task.hr_ratio,
                "added_at": task.added_at,
                "started_at": task.started_at,
                "completed_at": task.completed_at,
                "error_message": task.error_message,
                "error_at": task.error_at,
                "retry_count": task.retry_count,
                "created_at": task.created_at,
                "updated_at": task.updated_at,
            }
            items.append(task_dict)

        return {"total": total or 0, "items": items}

    @staticmethod
    async def sync_task_status(db: AsyncSession, task_id: int) -> Optional[DownloadTask]:
        """
        同步下载任务状态（从下载器获取最新状态）

        Args:
            db: 数据库会话
            task_id: 任务ID

        Returns:
            更新后的下载任务
        """
        try:
            task = await DownloadTaskService.get_by_id(db, task_id)
            if not task:
                return None

            # 获取下载器配置
            downloader_config = await DownloaderConfigService.get_by_id(
                db, task.downloader_config_id
            )
            if not downloader_config:
                logger.error(f"Downloader config not found for task {task_id}")
                return task

            # 获取下载器适配器
            adapter = DownloaderConfigService._get_downloader_adapter(downloader_config)

            try:
                # 从下载器获取任务信息
                torrent_info = await adapter.get_torrent_info(task.task_hash)

                # 更新任务状态
                await DownloadTaskService._update_task_record(db, task, torrent_info)
                await db.commit()
                await db.refresh(task)

                return task

            except Exception as e:
                logger.error(f"Error syncing task status from downloader: {str(e)}")
                await DownloadTaskService._handle_sync_error(db, task, e)
                await db.commit()
                await db.refresh(task)
                return task
            finally:
                await adapter.close()

        except Exception as e:
            logger.error(f"Error syncing task status: {str(e)}")
            raise

    @staticmethod
    async def sync_batch_status(db: AsyncSession, task_ids: List[int]) -> List[DownloadTask]:
        """
        批量同步下载任务状态

        Args:
            db: 数据库会话
            task_ids: 任务ID列表

        Returns:
            更新后的下载任务列表
        """
        if not task_ids:
            return []

        try:
            # 1. 获取任务信息并按下载器分组
            query = select(DownloadTask).where(DownloadTask.id.in_(task_ids))
            result = await db.execute(query)
            tasks = result.scalars().all()

            tasks_by_downloader = {}
            for task in tasks:
                if task.downloader_config_id not in tasks_by_downloader:
                    tasks_by_downloader[task.downloader_config_id] = []
                tasks_by_downloader[task.downloader_config_id].append(task)

            updated_tasks = []

            # 2. 对每个下载器并行获取信息
            for downloader_id, group_tasks in tasks_by_downloader.items():
                downloader_config = await DownloaderConfigService.get_by_id(db, downloader_id)
                if not downloader_config:
                    logger.error(f"Downloader config {downloader_id} not found")
                    updated_tasks.extend(group_tasks)
                    continue

                adapter = DownloaderConfigService._get_downloader_adapter(downloader_config)
                try:
                    hashes = [task.task_hash for task in group_tasks]
                    torrents_info = await adapter.get_torrents_info(hashes)

                    # 将 info 映射到 task (使用小写hash以避免大小写不一致问题)
                    info_map = {
                        (info["hash"].lower() if info.get("hash") else ""): info 
                        for info in torrents_info
                    }

                    for task in group_tasks:
                        # 同样使用小写hash进行查找
                        task_hash_lower = task.task_hash.lower() if task.task_hash else ""
                        info = info_map.get(task_hash_lower)
                        if info:
                            await DownloadTaskService._update_task_record(db, task, info)
                        else:
                            # 任务可能在下载器中被删除了
                            logger.warning(f"Task {task.task_hash} not found in downloader {downloader_id}")
                        updated_tasks.append(task)

                except Exception as e:
                    logger.error(f"Error batch syncing tasks for downloader {downloader_id}: {e}")
                    for task in group_tasks:
                        await DownloadTaskService._handle_sync_error(db, task, e)
                        updated_tasks.append(task)
                finally:
                    await adapter.close()

            # 3. 统一提交
            await db.commit()
            for task in updated_tasks:
                await db.refresh(task)

            return updated_tasks

        except Exception as e:
            await db.rollback()
            logger.error(f"Error in sync_batch_status: {e}")
            raise

    @staticmethod
    async def _update_task_record(db: AsyncSession, task: DownloadTask, info: Dict[str, Any]) -> None:
        """更新任务记录（不提交）"""
        task.status = info["state"]
        task.progress = int(info["progress"] * 100)
        task.download_speed = info["download_speed"]
        task.upload_speed = info["upload_speed"]
        task.downloaded_size = info["downloaded"]
        task.uploaded_size = info["uploaded"]
        task.ratio = info["ratio"]
        task.eta = info["eta"]

        # 如果下载器返回的名字与数据库中的不一致，更新为真实名字
        # 这可以修正创建时使用PT站点标题而非种子真实名字的问题
        if info.get("name") and info["name"] != task.torrent_name:
            logger.info(f"更新种子名字: '{task.torrent_name}' -> '{info['name']}'")
            task.torrent_name = info["name"]

        # 如果是第一次开始下载，记录开始时间
        if not task.started_at and task.status == TASK_STATUS_DOWNLOADING:
            task.started_at = now()

        # 如果已完成，记录完成时间
        newly_completed = False
        if task.progress == 100 and not task.completed_at:
            task.completed_at = now()
            newly_completed = True

        if newly_completed:
            # 自动发现并关联媒体文件
            try:
                # 延迟导入以避免循环依赖
                from app.services.mediafile.media_file_service import MediaFileService
                media_files = await MediaFileService.create_from_download_task(db, task)
                logger.info(f"自动发现 {len(media_files)} 个媒体文件，关联到下载任务 {task.id}")
            except Exception as e:
                logger.error(f"自动发现媒体文件失败，下载任务 {task.id}: {e}")

            # 发送下载完成通知
            await DownloadTaskService._send_completion_notification(db, task)

    @staticmethod
    async def _handle_sync_error(db: AsyncSession, task: DownloadTask, e: Exception) -> None:
        """
        处理同步错误（不提交）

        策略：
        1. 如果任务是 pending 状态，保持 pending（可能是下载器还在处理）
        2. 如果任务是其他状态，增加重试计数
        3. 只有重试次数超过 3 次才标记为 error
        """
        error_msg = str(e)

        # 如果是 pending 状态，保持 pending，不标记为错误
        if task.status == TASK_STATUS_PENDING:
            logger.info(f"任务 {task.id} 仍在 pending 状态，同步失败：{error_msg}")
            task.error_message = f"等待下载器处理中: {error_msg}"
            return

        # 增加重试计数
        task.retry_count = (task.retry_count or 0) + 1
        task.error_message = error_msg
        task.error_at = now()

        # 只有重试超过 3 次才标记为 error
        if task.retry_count >= 3:
            newly_failed = task.status != TASK_STATUS_ERROR
            task.status = TASK_STATUS_ERROR
            logger.error(f"任务 {task.id} 同步失败次数过多（{task.retry_count}次），标记为错误")

            # 发送下载失败通知
            if newly_failed:
                await DownloadTaskService._send_failure_notification(db, task)
        else:
            logger.warning(f"任务 {task.id} 同步失败（第{task.retry_count}次）：{error_msg}")

    @staticmethod
    async def pause_task(db: AsyncSession, task_id: int) -> bool:
        """
        暂停下载任务

        Args:
            db: 数据库会话
            task_id: 任务ID

        Returns:
            是否成功
        """
        try:
            task = await DownloadTaskService.get_by_id(db, task_id)
            if not task:
                return False

            # 获取下载器适配器
            downloader_config = await DownloaderConfigService.get_by_id(
                db, task.downloader_config_id
            )
            adapter = DownloaderConfigService._get_downloader_adapter(downloader_config)

            try:
                # 暂停任务
                success = await adapter.pause_torrent(task.task_hash)
                if success:
                    # 同步状态
                    await DownloadTaskService.sync_task_status(db, task_id)
                return success
            finally:
                await adapter.close()

        except Exception as e:
            logger.error(f"Error pausing task: {str(e)}")
            return False

    @staticmethod
    async def resume_task(db: AsyncSession, task_id: int) -> bool:
        """
        恢复下载任务

        Args:
            db: 数据库会话
            task_id: 任务ID

        Returns:
            是否成功
        """
        try:
            task = await DownloadTaskService.get_by_id(db, task_id)
            if not task:
                return False

            # 获取下载器适配器
            downloader_config = await DownloaderConfigService.get_by_id(
                db, task.downloader_config_id
            )
            adapter = DownloaderConfigService._get_downloader_adapter(downloader_config)

            try:
                # 恢复任务
                success = await adapter.resume_torrent(task.task_hash)
                if success:
                    # 同步状态
                    await DownloadTaskService.sync_task_status(db, task_id)
                return success
            finally:
                await adapter.close()

        except Exception as e:
            logger.error(f"Error resuming task: {str(e)}")
            return False

    @staticmethod
    async def delete_task(db: AsyncSession, task_id: int, delete_files: bool = False) -> bool:
        """
        删除下载任务

        Args:
            db: 数据库会话
            task_id: 任务ID
            delete_files: 是否同时删除文件

        Returns:
            是否成功
        """
        try:
            task = await DownloadTaskService.get_by_id(db, task_id)
            if not task:
                return False

            # 获取下载器适配器
            downloader_config = await DownloaderConfigService.get_by_id(
                db, task.downloader_config_id
            )
            adapter = DownloaderConfigService._get_downloader_adapter(downloader_config)

            try:
                # 从下载器删除任务
                success = await adapter.delete_torrent(task.task_hash, delete_files)

                if success:
                    # 从数据库删除记录
                    await db.delete(task)
                    await db.commit()
                    logger.info(f"Deleted download task: {task.torrent_name} (ID: {task_id})")

                return success
            finally:
                await adapter.close()

        except Exception as e:
            await db.rollback()
            logger.error(f"Error deleting task: {str(e)}")
            return False

    @staticmethod
    async def _send_completion_notification(
        db: AsyncSession, task: DownloadTask
    ) -> None:
        """
        发送下载完成通知

        Args:
            db: 数据库会话
            task: 下载任务
        """
        try:
            from app.constants.event import EVENT_DOWNLOAD_COMPLETED
            from app.events.bus import event_bus
            from sqlalchemy import select

            # 计算下载用时
            duration = None
            if task.started_at and task.completed_at:
                try:
                    # 处理时区不一致的情况
                    from app.utils.timezone import ensure_timezone
                    started_at = ensure_timezone(task.started_at)
                    completed_at = ensure_timezone(task.completed_at)

                    duration_seconds = int((completed_at - started_at).total_seconds())
                    hours = duration_seconds // 3600
                    minutes = (duration_seconds % 3600) // 60
                    if hours > 0:
                        duration = f"{hours}小时{minutes}分钟"
                    else:
                        duration = f"{minutes}分钟"
                except Exception as e:
                    logger.warning(f"计算下载用时失败: {e}")
                    duration = "未知"

            # 获取PT资源信息以获取站点名称和哈希值
            site_name = "未知站点"
            torrent_hash = task.task_hash or "未知"

            if task.pt_resource_id:
                result = await db.execute(
                    select(PTResource).where(PTResource.id == task.pt_resource_id)
                )
                pt_resource = result.scalar_one_or_none()
                if pt_resource:
                    site_result = await db.execute(
                        select(PTSite).where(PTSite.id == pt_resource.site_id)
                    )
                    pt_site = site_result.scalar_one_or_none()
                    if pt_site:
                        site_name = pt_site.name

            # 准备事件数据
            event_data = {
                "download_task_id": task.id,  # 工作流处理器需要
                "torrent_name": task.torrent_name,  # 工作流处理器需要
                "user_id": task.user_id,
                "media_name": task.torrent_name,
                "size_gb": round(task.total_size / (1024**3), 2) if task.total_size else 0,
                "size_bytes": task.total_size or 0,
                "save_path": task.save_path or "未知",
                "duration": duration or "未知",
                "ratio": round(task.ratio, 2) if task.ratio else 0,
                "site_name": site_name,
                "torrent_hash": torrent_hash,
                "related_type": "download_task",
                "related_id": task.id,
            }

            # 发布事件（异步触发，不阻塞）
            await event_bus.publish(
                EVENT_DOWNLOAD_COMPLETED,
                event_data
            )

            logger.debug(f"下载完成事件已发布: 任务{task.id}, {task.torrent_name}")

        except Exception as e:
            logger.exception(f"发布下载完成事件失败: 任务{task.id}, 错误: {e}")

    @staticmethod
    async def _send_failure_notification(
        db: AsyncSession, task: DownloadTask
    ) -> None:
        """
        发送下载失败通知

        Args:
            db: 数据库会话
            task: 下载任务
        """
        try:
            from app.constants.event import EVENT_DOWNLOAD_FAILED
            from app.events.bus import event_bus

            # 准备事件数据
            event_data = {
                "user_id": task.user_id,
                "media_name": task.torrent_name,
                "error_message": task.error_message or "未知错误",
                "retry_count": task.retry_count or 0,
                "related_type": "download_task",
                "related_id": task.id,
            }

            # 发布事件（异步触发，不阻塞）
            await event_bus.publish(
                EVENT_DOWNLOAD_FAILED,
                event_data
            )

            logger.debug(f"下载失败事件已发布: 任务{task.id}, {task.torrent_name}")

        except Exception as e:
            logger.exception(f"发布下载失败事件失败: 任务{task.id}, 错误: {e}")
