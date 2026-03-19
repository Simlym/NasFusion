# -*- coding: utf-8 -*-
"""
调度任务管理API
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_admin_user
from app.models.user import User
from app.schemas.scheduled_task import (
    PTSyncTaskCreate,
    ScheduledTaskCreate,
    ScheduledTaskListResponse,
    ScheduledTaskResponse,
    ScheduledTaskRunRequest,
    ScheduledTaskUpdate,
)
from app.schemas.task_execution import TaskExecutionListResponse
from app.services.task.scheduled_task_service import ScheduledTaskService
from app.services.task.task_execution_service import TaskExecutionService
from app.services.task.scheduler_manager import scheduler_manager

router = APIRouter(prefix="/scheduled-tasks", tags=["调度任务管理"])


@router.get("", response_model=ScheduledTaskListResponse, summary="获取调度任务列表")
async def get_scheduled_tasks(
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量"),
    enabled_only: bool = Query(False, description="仅返回启用的任务"),
    task_type: str = Query(None, description="任务类型过滤"),
    keyword: str = Query(None, description="任务名称关键字"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """获取调度任务列表"""
    tasks, total = await ScheduledTaskService.get_all(
        db, skip=skip, limit=limit, enabled_only=enabled_only, task_type=task_type, keyword=keyword
    )

    return ScheduledTaskListResponse(total=total, items=tasks)


@router.post(
    "",
    response_model=ScheduledTaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建调度任务",
)
async def create_scheduled_task(
    task_data: ScheduledTaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """创建新的调度任务"""
    try:
        task = await ScheduledTaskService.create(db, task_data)
        # 将任务添加到调度器
        await scheduler_manager.add_job(task)
        return task
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/pt-sync",
    response_model=ScheduledTaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建PT站点同步任务",
)
async def create_pt_sync_task(
    task_data: PTSyncTaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """创建PT站点同步任务（快捷方式）"""
    try:
        task = await ScheduledTaskService.create_pt_sync_task(db, task_data)
        # 将任务添加到调度器
        await scheduler_manager.add_job(task)
        return task
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{task_id}", response_model=ScheduledTaskResponse, summary="获取调度任务详情")
async def get_scheduled_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """获取调度任务详情"""
    task = await ScheduledTaskService.get_by_id(db, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"任务不存在: {task_id}"
        )
    return task


@router.put("/{task_id}", response_model=ScheduledTaskResponse, summary="更新调度任务")
async def update_scheduled_task(
    task_id: int,
    task_data: ScheduledTaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """更新调度任务"""
    try:
        task = await ScheduledTaskService.update(db, task_id, task_data)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"任务不存在: {task_id}"
            )

        # 更新调度器中的任务
        if task.enabled:
            await scheduler_manager.add_job(task)
        else:
            await scheduler_manager.remove_job(task.id)

        return task
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除调度任务")
async def delete_scheduled_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """删除调度任务"""
    # 先从调度器移除
    await scheduler_manager.remove_job(task_id)

    success = await ScheduledTaskService.delete(db, task_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"任务不存在: {task_id}"
        )


@router.post("/{task_id}/toggle", response_model=ScheduledTaskResponse, summary="切换任务启用状态")
async def toggle_scheduled_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """切换任务启用状态"""
    task = await ScheduledTaskService.toggle_enabled(db, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"任务不存在: {task_id}"
        )

    # 更新调度器
    if task.enabled:
        await scheduler_manager.add_job(task)
    else:
        await scheduler_manager.remove_job(task.id)

    return task


@router.post("/{task_id}/run", summary="立即执行任务")
async def run_scheduled_task_now(
    task_id: int,
    request_data: ScheduledTaskRunRequest = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """立即执行调度任务"""
    try:
        execution_id = await scheduler_manager.run_task_now(task_id)
        return {"message": "任务已提交执行", "execution_id": execution_id}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/{task_id}/executions",
    response_model=TaskExecutionListResponse,
    summary="获取任务执行历史",
)
async def get_task_executions(
    task_id: int,
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    status: str = Query(None, description="状态过滤"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """获取任务的执行历史"""
    executions, total = await TaskExecutionService.get_all(
        db, skip=skip, limit=limit, status=status, scheduled_task_id=task_id
    )

    return TaskExecutionListResponse(total=total, items=executions)
