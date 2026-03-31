# -*- coding: utf-8 -*-
"""
任务执行API
"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_admin_user
from app.models.user import User
from app.schemas.task_execution import (
    TaskExecutionResponse,
    TaskExecutionSummary,
    TaskQueueResponse,
)
from app.services.task.task_execution_service import TaskExecutionService

router = APIRouter(prefix="/task-executions", tags=["任务执行"])


@router.get("/queue/status", response_model=TaskQueueResponse, summary="获取任务队列状态")
async def get_task_queue_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """获取当前任务队列状态（运行中、等待中、最近完成的任务）"""
    queue_data = await TaskExecutionService.get_queue_status(db)

    return TaskQueueResponse(
        running=[TaskExecutionSummary.model_validate(e) for e in queue_data["running"]],
        pending=[TaskExecutionSummary.model_validate(e) for e in queue_data["pending"]],
        recent_completed=[
            TaskExecutionSummary.model_validate(e) for e in queue_data["recent_completed"]
        ],
    )


@router.get(
    "",
    summary="获取任务执行历史列表",
)
async def get_task_executions_list(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    task_type: Optional[str] = Query(None, description="任务类型"),
    task_types: Optional[List[str]] = Query(None, description="任务类型列表（多选）"),
    scheduled_task_id: Optional[int] = Query(None, description="调度任务ID"),
    keyword: Optional[str] = Query(None, description="搜索关键字"),
    status: Optional[str] = Query(None, description="执行状态"),
    start_date: Optional[datetime] = Query(None, description="开始日期"),
    end_date: Optional[datetime] = Query(None, description="结束日期"),
    sort_by: str = Query("created_at", description="排序字段"),
    sort_order: str = Query("desc", description="排序方向(asc/desc)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """获取任务执行历史列表，支持分页、过滤和排序"""
    skip = (page - 1) * page_size

    executions, total = await TaskExecutionService.get_all(
        db=db,
        skip=skip,
        limit=page_size,
        status=status,
        task_type=task_type,
        task_types=task_types,
        scheduled_task_id=scheduled_task_id,
        keyword=keyword,
        start_date=start_date,
        end_date=end_date,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    # 转换为Pydantic模型
    items = [TaskExecutionResponse.model_validate(exec) for exec in executions]

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.get(
    "/{execution_id}",
    response_model=TaskExecutionResponse,
    summary="获取任务执行详情",
)
async def get_task_execution(
    execution_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """获取单个任务执行的详细信息"""
    execution = await TaskExecutionService.get_by_id(db, execution_id)

    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"任务执行记录 {execution_id} 不存在"
        )

    return execution


@router.post(
    "/{execution_id}/cancel",
    response_model=TaskExecutionResponse,
    summary="取消任务执行",
)
async def cancel_task_execution(
    execution_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """取消正在执行或等待中的任务"""
    try:
        execution = await TaskExecutionService.cancel_execution(db, execution_id)
        if not execution:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"任务执行记录 {execution_id} 不存在"
            )
        return execution
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
