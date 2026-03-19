# -*- coding: utf-8 -*-
"""
资源识别API接口
"""
import asyncio
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import EXECUTION_STATUS_PENDING, TASK_TYPE_PT_RESOURCE_IDENTIFY
from app.core.dependencies import get_db
from app.schemas.resource_mapping import ResourceMappingResponse, ResourceMappingWithDetails
from app.schemas.task_execution import TaskExecutionCreate
from app.services.identification.resource_identify_service import ResourceIdentificationService
from app.services.identification.resource_mapping_service import ResourceMappingService
from app.services.task.scheduler_manager import scheduler_manager
from app.services.task.task_execution_service import TaskExecutionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/resource-identification", tags=["资源识别"])


@router.post("/{pt_resource_id}/identify", response_model=ResourceMappingResponse)
async def identify_resource(
    pt_resource_id: int,
    media_type: str = Query("auto", description="媒体类型: auto | movie | tv | music | book | adult"),
    force: bool = Query(False, description="是否强制重新识别（删除旧映射）"),
    db: AsyncSession = Depends(get_db),
):
    """
    识别PT资源并建立映射（统一入口）

    - **pt_resource_id**: PT资源ID
    - **media_type**: 媒体类型（auto自动判断, movie电影, tv电视剧等）
    - **force**: 是否强制重新识别（删除旧映射）

    返回映射关系
    """
    try:
        mapping = await ResourceIdentificationService.identify_resource(
            db=db,
            pt_resource_id=pt_resource_id,
            media_type=media_type,
            force=force,
        )
        return mapping
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to identify resource: {str(e)}")
        raise HTTPException(status_code=500, detail=f"识别失败: {str(e)}")


@router.post("/batch-identify")
async def batch_identify_resources(
    pt_resource_ids: List[int],
    media_type: str = Query("auto", description="媒体类型: auto | movie | tv | music | book | adult"),
    skip_errors: bool = Query(True, description="是否跳过错误继续处理"),
    db: AsyncSession = Depends(get_db),
):
    """
    批量识别PT资源（异步任务模式）

    - **pt_resource_ids**: PT资源ID列表
    - **media_type**: 媒体类型（auto自动判断, movie电影, tv电视剧等）
    - **skip_errors**: 是否跳过错误继续处理

    返回任务执行信息：
    - task_execution_id: 任务执行ID
    - status: 任务状态（pending）
    - message: 提示信息
    """
    try:
        if not pt_resource_ids:
            raise HTTPException(status_code=400, detail="pt_resource_ids不能为空")

        # 创建任务执行记录
        task_data = TaskExecutionCreate(
            task_type=TASK_TYPE_PT_RESOURCE_IDENTIFY,
            task_name=f"批量识别 {len(pt_resource_ids)} 个资源",
            handler=TASK_TYPE_PT_RESOURCE_IDENTIFY,  # 使用任务类型作为 handler
            handler_params={
                "pt_resource_ids": pt_resource_ids,
                "media_type": media_type,
                "skip_errors": skip_errors
            },
            priority=5,
            status=EXECUTION_STATUS_PENDING
        )

        execution = await TaskExecutionService.create(db, task_data)

        # 在后台执行任务（需要创建一个临时的ScheduledTask来执行）
        asyncio.create_task(scheduler_manager._execute_task_by_execution(execution.id))

        return {
            "task_execution_id": execution.id,
            "status": "pending",
            "message": f"批量识别任务已创建，共 {len(pt_resource_ids)} 个资源"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create batch identify task: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建批量识别任务失败: {str(e)}")


# 保留旧接口作为别名（向后兼容）
@router.post("/movies/{pt_resource_id}/identify", response_model=ResourceMappingResponse, deprecated=True)
async def identify_movie_legacy(
    pt_resource_id: int,
    force: bool = Query(False, description="是否强制重新识别（删除旧映射）"),
    db: AsyncSession = Depends(get_db),
):
    """
    [已废弃] 识别PT资源为电影

    请使用新接口: POST /{pt_resource_id}/identify?media_type=movie
    """
    return await identify_resource(pt_resource_id, "movie", force, db)


@router.post("/movies/batch-identify", deprecated=True)
async def batch_identify_movies_legacy(
    pt_resource_ids: List[int],
    skip_errors: bool = Query(True, description="是否跳过错误继续处理"),
    db: AsyncSession = Depends(get_db),
):
    """
    [已废弃] 批量识别PT资源为电影

    请使用新接口: POST /batch-identify?media_type=movie
    """
    return await batch_identify_resources(pt_resource_ids, "movie", skip_errors, db)


@router.get("/pt-resources/{pt_resource_id}/mapping")
async def get_resource_mapping(
    pt_resource_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    查询PT资源的映射关系

    - **pt_resource_id**: PT资源ID

    返回映射关系（含详细信息），如果不存在则返回 null
    """
    mapping = await ResourceMappingService.get_by_pt_resource(db, pt_resource_id)
    if not mapping:
        return None

    # 构建详细信息
    from app.schemas.unified_movie import UnifiedMovieResponse
    from app.schemas.pt_resource import PTResourceResponse

    response_data = ResourceMappingResponse.model_validate(mapping).model_dump()

    # 添加关联数据
    if mapping.pt_resource:
        response_data["pt_resource"] = PTResourceResponse.model_validate(mapping.pt_resource).model_dump()

    if mapping.unified_movie:
        response_data["unified_movie"] = UnifiedMovieResponse.model_validate(mapping.unified_movie).model_dump()

    return response_data


@router.delete("/mappings/{mapping_id}")
async def delete_mapping(
    mapping_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    删除映射关系（支持重新识别）

    - **mapping_id**: 映射ID

    返回删除结果
    """
    success = await ResourceMappingService.delete_mapping(db, mapping_id)
    if not success:
        raise HTTPException(status_code=404, detail="映射关系不存在")

    return {"success": True, "message": "映射关系已删除"}


@router.delete("/pt-resources/{pt_resource_id}/mapping")
async def delete_resource_mapping(
    pt_resource_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    删除PT资源的映射关系

    - **pt_resource_id**: PT资源ID

    返回删除结果
    """
    success = await ResourceMappingService.delete_by_pt_resource(db, pt_resource_id)
    if not success:
        raise HTTPException(status_code=404, detail="映射关系不存在")

    return {"success": True, "message": "映射关系已删除"}
