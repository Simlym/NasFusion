# -*- coding: utf-8 -*-
"""
下载任务创建处理器
"""
import logging
import hashlib
from typing import Dict, Any
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import bencodepy

from app.tasks.base import BaseTaskHandler
from app.models.pt_resource import PTResource
from app.models.pt_site import PTSite
from app.models.download_task import DownloadTask
from app.services.pt.pt_site_service import PTSiteService
from app.services.download.downloader_config_service import DownloaderConfigService
from app.services.task.task_execution_service import TaskExecutionService
from app.adapters.pt_sites import get_adapter
from app.constants import (
    AUTH_TYPE_COOKIE,
    AUTH_TYPE_PASSKEY,
    AUTH_TYPE_USER_PASS,
    HR_STRATEGY_AUTO_LIMIT,
    TASK_STATUS_PENDING,
)
from app.constants.event import EVENT_DOWNLOAD_STARTED
from app.events.bus import event_bus
from app.core.config import settings
from app.utils.timezone import now

logger = logging.getLogger(__name__)


class DownloadCreateHandler(BaseTaskHandler):
    """创建下载任务（带步骤进度）"""

    @staticmethod
    async def execute(
        db: AsyncSession,
        params: Dict[str, Any],
        execution_id: int,
    ) -> Dict[str, Any]:
        """
        执行创建下载任务

        Args:
            db: 数据库会话
            params: 处理器参数
                - pt_resource_id: PT资源ID (必需)
                - downloader_config_id: 下载器配置ID (必需)
                - save_path: 保存路径 (必需)
                - auto_organize: 自动整理 (默认 True)
                - organize_config_id: 整理配置ID (可选)
                - storage_mount_id: 存储挂载点ID (可选)
                - keep_seeding: 保持做种 (默认 True)
                - seeding_time_limit: 做种时间限制 (可选)
                - seeding_ratio_limit: 分享率限制 (可选)
                - unified_table_name: 统一资源表名 (可选)
                - unified_resource_id: 统一资源ID (可选)
                - user_id: 用户ID (可选)
            execution_id: 任务执行ID

        Returns:
            下载任务创建结果
        """
        # 获取参数
        pt_resource_id = params.get("pt_resource_id")
        downloader_config_id = params.get("downloader_config_id")
        save_path = params.get("save_path")
        auto_organize = params.get("auto_organize", True)
        organize_config_id = params.get("organize_config_id")
        storage_mount_id = params.get("storage_mount_id")
        keep_seeding = params.get("keep_seeding", True)
        seeding_time_limit = params.get("seeding_time_limit")
        seeding_ratio_limit = params.get("seeding_ratio_limit")
        unified_table_name = params.get("unified_table_name")
        unified_resource_id = params.get("unified_resource_id")
        user_id = params.get("user_id")

        if not pt_resource_id or not downloader_config_id or not save_path:
            raise ValueError("创建下载任务缺少必要参数")

        # 定义步骤
        steps = [
            {"name": "验证资源信息", "status": "pending", "progress": 0, "message": "等待中"},
            {"name": "验证下载器连接", "status": "pending", "progress": 0, "message": "等待中"},
            {"name": "下载种子文件", "status": "pending", "progress": 0, "message": "等待中"},
            {"name": "保存种子到本地", "status": "pending", "progress": 0, "message": "等待中"},
            {"name": "推送到下载器", "status": "pending", "progress": 0, "message": "等待中"},
            {"name": "创建任务记录", "status": "pending", "progress": 0, "message": "等待中"},
        ]

        # 初始化进度详情
        await TaskExecutionService.update_progress(
            db, execution_id, 0,
            progress_detail={"steps": steps, "current_step": 0, "total_steps": len(steps)}
        )

        try:
            # 步骤 1: 验证资源信息
            steps[0]["status"] = "running"
            steps[0]["message"] = "正在验证资源..."
            await TaskExecutionService.update_progress(
                db, execution_id, 5,
                progress_detail={"steps": steps, "current_step": 0, "total_steps": len(steps)}
            )
            await TaskExecutionService.append_log(db, execution_id, "开始验证资源信息")

            result = await db.execute(select(PTResource).where(PTResource.id == pt_resource_id))
            pt_resource = result.scalar_one_or_none()
            if not pt_resource:
                raise ValueError(f"PT资源不存在 (ID: {pt_resource_id})")

            downloader_config = await DownloaderConfigService.get_by_id(db, downloader_config_id)
            if not downloader_config:
                raise ValueError(f"下载器配置不存在 (ID: {downloader_config_id})")

            if not downloader_config.is_enabled:
                raise ValueError(f"下载器未启用: {downloader_config.name}")

            result = await db.execute(select(PTSite).where(PTSite.id == pt_resource.site_id))
            pt_site = result.scalar_one_or_none()
            if not pt_site:
                raise ValueError(f"PT站点不存在 (ID: {pt_resource.site_id})")

            steps[0]["status"] = "completed"
            steps[0]["progress"] = 100
            steps[0]["message"] = "资源验证成功"
            await TaskExecutionService.update_progress(
                db, execution_id, 10,
                progress_detail={"steps": steps, "current_step": 1, "total_steps": len(steps)}
            )
            await TaskExecutionService.append_log(db, execution_id, f"资源验证成功: {pt_resource.title}")

            # 步骤 2: 验证下载器连接
            steps[1]["status"] = "running"
            steps[1]["message"] = f"正在连接 {downloader_config.name}..."
            await TaskExecutionService.update_progress(
                db, execution_id, 15,
                progress_detail={"steps": steps, "current_step": 1, "total_steps": len(steps)}
            )
            await TaskExecutionService.append_log(db, execution_id, f"开始验证下载器连接: {downloader_config.name}")

            # 准备下载器适配器
            downloader_adapter = DownloaderConfigService._get_downloader_adapter(downloader_config)

            try:
                # 检查连接
                is_connected = await downloader_adapter.test_connection()
                if not is_connected:
                    raise ConnectionError(f"无法连接到下载器: {downloader_config.name}")
            except Exception as e:
                # 如果是 NotImplementedError，我们假设连接是可以的（某些旧适配器可能没实现）
                # 但 BaseDownloaderAdapter 已经是 abstractmethod，所以应该实现了。
                # 除非是其他的...
                # 暂时严格处理
                raise ConnectionError(f"下载器连接失败: {str(e)}")

            steps[1]["status"] = "completed"
            steps[1]["progress"] = 100
            steps[1]["message"] = f"下载器连接成功"
            await TaskExecutionService.update_progress(
                db, execution_id, 20,
                progress_detail={"steps": steps, "current_step": 2, "total_steps": len(steps)}
            )
            await TaskExecutionService.append_log(db, execution_id, "下载器连接验证通过")

            # 步骤 3: 下载种子文件
            steps[2]["status"] = "running"
            steps[2]["message"] = f"正在从 {pt_site.name} 下载种子..."
            await TaskExecutionService.update_progress(
                db, execution_id, 30,
                progress_detail={"steps": steps, "current_step": 2, "total_steps": len(steps)}
            )
            await TaskExecutionService.append_log(db, execution_id, f"开始从 {pt_site.name} 下载种子文件")

            # 准备适配器配置
            config = {
                "name": pt_site.name,
                "base_url": pt_site.base_url,
                "domain": pt_site.domain,
                "proxy_config": pt_site.proxy_config,
                "request_interval": pt_site.request_interval or 2,
            }

            # 添加认证信息
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
            # 传递资源的 download_url（可能已包含认证信息）
            torrent_data = await site_adapter.download_torrent(
                pt_resource.torrent_id,
                download_url=pt_resource.download_url
            )

            steps[2]["status"] = "completed"
            steps[2]["progress"] = 100
            steps[2]["message"] = f"种子下载成功 ({len(torrent_data)} 字节)"
            await TaskExecutionService.update_progress(
                db, execution_id, 50,
                progress_detail={"steps": steps, "current_step": 3, "total_steps": len(steps)}
            )
            await TaskExecutionService.append_log(db, execution_id, f"种子文件下载成功，大小: {len(torrent_data)} 字节")

            # 步骤 4: 保存种子文件到本地
            steps[3]["status"] = "running"
            steps[3]["message"] = "正在保存种子文件..."
            await TaskExecutionService.update_progress(
                db, execution_id, 60,
                progress_detail={"steps": steps, "current_step": 3, "total_steps": len(steps)}
            )
            await TaskExecutionService.append_log(db, execution_id, "开始保存种子文件到本地")

            # 确保种子目录存在
            torrent_dir = Path(settings.DATA_DIR) / "torrents"
            torrent_dir.mkdir(parents=True, exist_ok=True)
            site_dir = torrent_dir / pt_site.name
            site_dir.mkdir(exist_ok=True)
            torrent_file_path = site_dir / f"{pt_resource.torrent_id}.torrent"

            with open(torrent_file_path, "wb") as f:
                f.write(torrent_data)

            # 计算种子 hash 并提取真实名字
            torrent_dict = bencodepy.decode(torrent_data)
            info_dict = torrent_dict[b"info"]
            info_encoded = bencodepy.encode(info_dict)
            task_hash = hashlib.sha1(info_encoded).hexdigest().lower()

            # 从种子文件提取真实名字（优先使用种子内部名字，而非PT站点标题）
            torrent_real_name = info_dict.get(b"name", b"").decode("utf-8", errors="ignore") or pt_resource.title
            logger.info(f"种子真实名字: {torrent_real_name} (PT站点标题: {pt_resource.title})")

            steps[3]["status"] = "completed"
            steps[3]["progress"] = 100
            steps[3]["message"] = f"种子已保存: {torrent_file_path.name}"
            await TaskExecutionService.update_progress(
                db, execution_id, 70,
                progress_detail={"steps": steps, "current_step": 4, "total_steps": len(steps)}
            )
            await TaskExecutionService.append_log(db, execution_id, f"种子文件已保存: {torrent_file_path}")
            await TaskExecutionService.append_log(db, execution_id, f"种子名字: {torrent_real_name}")

            # 检查任务是否已存在
            result = await db.execute(select(DownloadTask).where(DownloadTask.task_hash == task_hash))
            existing_task = result.scalar_one_or_none()
            if existing_task:
                await TaskExecutionService.append_log(db, execution_id, f"下载任务已存在: {task_hash}")
                steps[4]["status"] = "completed"
                steps[4]["progress"] = 100
                steps[4]["message"] = "任务已存在，跳过"
                steps[5]["status"] = "completed"
                steps[5]["progress"] = 100
                steps[5]["message"] = "使用已有任务"
                await TaskExecutionService.update_progress(
                    db, execution_id, 100,
                    progress_detail={"steps": steps, "current_step": 6, "total_steps": len(steps)}
                )
                
                # 关闭适配器
                if 'downloader_adapter' in locals():
                    await downloader_adapter.close()

                return {"download_task_id": existing_task.id, "task_hash": task_hash, "existed": True}

            # 步骤 5: 推送到下载器
            steps[4]["status"] = "running"
            steps[4]["message"] = f"正在推送到 {downloader_config.name}..."
            await TaskExecutionService.update_progress(
                db, execution_id, 80,
                progress_detail={"steps": steps, "current_step": 4, "total_steps": len(steps)}
            )
            await TaskExecutionService.append_log(db, execution_id, f"开始推送到下载器: {downloader_config.name}")

            # 准备下载选项
            download_options = {}
            if pt_resource.category:
                download_options["category"] = pt_resource.category

            # 设置标签
            tags = [pt_site.name]
            if pt_resource.is_free:
                tags.append("FREE")
            if pt_resource.has_hr:
                tags.append("HR")
            download_options["tags"] = ",".join(tags)

            # HR 处理
            if pt_resource.has_hr and downloader_config.hr_strategy == HR_STRATEGY_AUTO_LIMIT:
                if pt_resource.hr_ratio:
                    download_options["ratio_limit"] = float(pt_resource.hr_ratio)
                if pt_resource.hr_seed_time:
                    download_options["seeding_time_limit"] = pt_resource.hr_seed_time * 60

            # 用户指定的限制
            if seeding_ratio_limit:
                download_options["ratio_limit"] = seeding_ratio_limit
            if seeding_time_limit:
                download_options["seeding_time_limit"] = seeding_time_limit * 60

            # 推送到下载器
            try:
                result = await downloader_adapter.add_torrent_file(
                    torrent_data=torrent_data,
                    save_path=save_path,
                    **download_options,
                )
            finally:
                await downloader_adapter.close()

            steps[4]["status"] = "completed"
            steps[4]["progress"] = 100
            steps[4]["message"] = "推送成功"
            await TaskExecutionService.update_progress(
                db, execution_id, 90,
                progress_detail={"steps": steps, "current_step": 5, "total_steps": len(steps)}
            )
            await TaskExecutionService.append_log(db, execution_id, "种子已成功推送到下载器")

            # 步骤 6: 创建数据库记录
            steps[5]["status"] = "running"
            steps[5]["message"] = "正在创建任务记录..."
            await TaskExecutionService.update_progress(
                db, execution_id, 95,
                progress_detail={"steps": steps, "current_step": 5, "total_steps": len(steps)}
            )
            await TaskExecutionService.append_log(db, execution_id, "开始创建下载任务记录")

            download_task = DownloadTask(
                task_hash=task_hash,
                pt_resource_id=pt_resource.id,
                downloader_config_id=downloader_config.id,
                user_id=user_id,
                media_type=pt_resource.category,
                unified_table_name=unified_table_name,
                unified_resource_id=unified_resource_id,
                client_type=downloader_config.type,
                client_task_id=task_hash,
                torrent_file_path=str(torrent_file_path),
                torrent_name=torrent_real_name,  # 使用种子真实名字
                save_path=save_path,
                status=TASK_STATUS_PENDING,
                progress=0,
                total_size=pt_resource.size_bytes,
                downloaded_size=0,
                uploaded_size=0,
                ratio=0.0,
                auto_organize=auto_organize,
                organize_config_id=organize_config_id,
                storage_mount_id=storage_mount_id,
                keep_seeding=keep_seeding,
                seeding_time_limit=seeding_time_limit,
                seeding_ratio_limit=seeding_ratio_limit,
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

            steps[5]["status"] = "completed"
            steps[5]["progress"] = 100
            steps[5]["message"] = "任务记录创建成功"
            await TaskExecutionService.update_progress(
                db, execution_id, 100,
                progress_detail={"steps": steps, "current_step": 6, "total_steps": len(steps)}
            )
            await TaskExecutionService.append_log(db, execution_id, f"下载任务创建成功 (ID: {download_task.id})")

            # 发布下载已开始事件
            await event_bus.publish(
                EVENT_DOWNLOAD_STARTED,
                {
                    "user_id": download_task.user_id,  # 下载任务的创建者
                    "download_task_id": download_task.id,
                    "task_hash": task_hash,
                    "torrent_name": torrent_real_name,  # 使用种子真实名字
                    "pt_resource_id": pt_resource.id,
                    "site_id": pt_site.id,
                    "site_name": pt_site.name,
                    "media_type": pt_resource.category,
                    "total_size": pt_resource.size_bytes,
                    "size_gb": round(pt_resource.size_bytes / (1024**3), 2),
                    "is_free": pt_resource.is_free,
                    "has_hr": pt_resource.has_hr,
                    "downloader_name": downloader_config.name,
                    "save_path": save_path,
                    "related_type": "download_task",
                    "related_id": download_task.id,
                }
            )
            logger.info(f"已发布下载开始事件: {pt_resource.title}, 用户ID: {download_task.user_id}")

            # 延迟 3 秒后进行第一次状态同步，给下载器足够的时间处理种子
            import asyncio
            await TaskExecutionService.append_log(db, execution_id, "等待下载器处理种子文件...")
            await asyncio.sleep(3)

            try:
                await TaskExecutionService.append_log(db, execution_id, "开始同步下载任务状态...")
                from app.services.download.download_task_service import DownloadTaskService
                synced_task = await DownloadTaskService.sync_task_status(db, download_task.id)
                if synced_task:
                    await TaskExecutionService.append_log(
                        db, execution_id,
                        f"状态同步成功: {synced_task.status}, 进度: {synced_task.progress}%"
                    )
                    # 刷新 download_task 以获取最新状态
                    await db.refresh(download_task)
            except Exception as e:
                # 同步失败不影响任务创建，只记录日志
                await TaskExecutionService.append_log(
                    db, execution_id,
                    f"首次状态同步失败（不影响下载）: {str(e)}"
                )
                logger.warning(f"首次状态同步失败: {str(e)}")

            return {
                "download_task_id": download_task.id,
                "task_hash": task_hash,
                "torrent_name": torrent_real_name,  # 使用种子真实名字
                "existed": False
            }

        except Exception as e:
            # 如果适配器已经创建，确保关闭
            if 'downloader_adapter' in locals() and downloader_adapter:
                await downloader_adapter.close()

            # 更新失败步骤的状态
            current_progress = 0
            for step in steps:
                if step["status"] == "running":
                    step["status"] = "failed"
                    step["message"] = str(e)
                    break
                elif step["status"] == "completed":
                    current_progress += 15  # 每步约15-16%

            await TaskExecutionService.update_progress(
                db, execution_id, current_progress,
                progress_detail={"steps": steps, "current_step": len([s for s in steps if s["status"] == "completed"]), "total_steps": len(steps)}
            )
            await TaskExecutionService.append_log(db, execution_id, f"下载任务创建失败: {str(e)}")
            raise
