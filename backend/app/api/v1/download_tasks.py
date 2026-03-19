# -*- coding: utf-8 -*-
"""
下载任务API路由
"""
import asyncio
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.downloader import (
    DownloadTaskActionRequest,
    DownloadTaskCreate,
    DownloadTaskListResponse,
    DownloadTaskResponse,
    DownloadTaskBatchSyncRequest,
)
from app.schemas.task_execution import TaskExecutionCreate
from app.services.download.download_task_service import DownloadTaskService
from app.services.task.task_execution_service import TaskExecutionService
from app.constants import TASK_TYPE_DOWNLOAD_CREATE, RELATED_TYPE_PT_RESOURCE

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/download-tasks", tags=["下载任务"])


@router.post("", status_code=202)
async def create_download_task(
    data: DownloadTaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建下载任务（异步）"""
    try:
        # 创建任务执行记录
        execution_data = TaskExecutionCreate(
            task_type=TASK_TYPE_DOWNLOAD_CREATE,
            task_name=f"创建下载: {data.torrent_name or 'Unknown'}",
            handler=TASK_TYPE_DOWNLOAD_CREATE,  # 使用任务类型作为 handler
            handler_params={
                "pt_resource_id": data.pt_resource_id,
                "downloader_config_id": data.downloader_config_id,
                "save_path": data.save_path,
                "auto_organize": data.auto_organize,
                "organize_config_id": data.organize_config_id,  # 传递整理配置ID
                "storage_mount_id": data.storage_mount_id,  # 传递存储挂载点ID
                "keep_seeding": data.keep_seeding,
                "seeding_time_limit": data.seeding_time_limit,
                "seeding_ratio_limit": data.seeding_ratio_limit,
                "unified_table_name": data.unified_table_name,  # 传递统一资源表名
                "unified_resource_id": data.unified_resource_id,  # 传递统一资源ID
                "user_id": current_user.id,  # 传递当前用户ID
            },
            related_type=RELATED_TYPE_PT_RESOURCE,
            related_id=data.pt_resource_id,
        )

        execution = await TaskExecutionService.create(db, execution_data)

        # 在后台执行任务
        from app.services.task.scheduler_manager import scheduler_manager
        asyncio.create_task(scheduler_manager._execute_task_by_execution(execution.id))

        # 立即返回任务执行ID
        return {
            "execution_id": execution.id,
            "message": "下载任务已提交，正在后台处理"
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating download task: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建下载任务失败: {str(e)}")


@router.get("", response_model=DownloadTaskListResponse)
async def list_download_tasks(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    media_type: Optional[str] = None,
    downloader_config_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    """获取下载任务列表"""
    result = await DownloadTaskService.list(
        db,
        skip=skip,
        limit=limit,
        status=status,
        media_type=media_type,
        downloader_config_id=downloader_config_id,
    )
    return result


@router.get("/{task_id}", response_model=DownloadTaskResponse)
async def get_download_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取下载任务详情"""
    task = await DownloadTaskService.get_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="下载任务不存在")
    return task


@router.post("/{task_id}/sync", response_model=DownloadTaskResponse)
async def sync_download_task_status(
    task_id: int,
    db: AsyncSession = Depends(get_db),
):
    """同步下载任务状态"""
    task = await DownloadTaskService.sync_task_status(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="下载任务不存在")
    return task


@router.post("/batch-sync", response_model=List[DownloadTaskResponse])
async def batch_sync_download_tasks(
    data: DownloadTaskBatchSyncRequest,
    db: AsyncSession = Depends(get_db),
):
    """批量同步下载任务状态"""
    tasks = await DownloadTaskService.sync_batch_status(db, data.task_ids)
    return tasks


@router.post("/{task_id}/action")
async def control_download_task(
    task_id: int,
    data: DownloadTaskActionRequest,
    db: AsyncSession = Depends(get_db),
):
    """控制下载任务（暂停/恢复/删除）"""
    try:
        if data.action == "pause":
            success = await DownloadTaskService.pause_task(db, task_id)
            message = "任务已暂停" if success else "暂停任务失败"
        elif data.action == "resume":
            success = await DownloadTaskService.resume_task(db, task_id)
            message = "任务已恢复" if success else "恢复任务失败"
        elif data.action == "delete":
            success = await DownloadTaskService.delete_task(db, task_id, data.delete_files)
            message = "任务已删除" if success else "删除任务失败"
        else:
            raise HTTPException(status_code=400, detail="无效的操作")

        if not success:
            raise HTTPException(status_code=500, detail=message)

        return {"success": True, "message": message}

    except Exception as e:
        logger.error(f"Error controlling download task: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
