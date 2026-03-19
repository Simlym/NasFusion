# -*- coding: utf-8 -*-
"""
工作流处理器

监听系统事件并触发自动化任务，实现业务流程的自动化编排。

工作流规则：
    - PT资源同步完成 → 自动识别新资源 + 检查订阅
    - 下载创建 → 启动下载状态同步
    - 下载完成 → 触发资源整理（预留）
"""
import asyncio
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_local
from app.constants.event import (
    EVENT_SITE_SYNC_COMPLETED,
    EVENT_DOWNLOAD_STARTED,
    EVENT_DOWNLOAD_COMPLETED,
)
from app.constants.task import (
    TASK_TYPE_PT_RESOURCE_IDENTIFY,
    TASK_TYPE_SUBSCRIPTION_CHECK,
    TASK_TYPE_DOWNLOAD_STATUS_SYNC,
    TASK_TYPE_MEDIA_FILE_AUTO_ORGANIZE,
)

logger = logging.getLogger(__name__)


# ============================================================================
# 工作流配置
# ============================================================================

WORKFLOW_CONFIG = {
    "site_sync_auto_identify": {
        "enabled": False,  # 暂时禁用自动批量识别
        "max_resources": 100,  # 单次识别资源上限
        "priority": 3,  # 中等优先级
        "skip_errors": True,
    },
    "site_sync_auto_check_subscription": {
        "enabled": True,
        "priority": 2,  # 高优先级
    },
    "download_started_auto_sync": {
        "enabled": True,
        "priority": 5,  # 普通优先级
    },
    "download_completed_auto_organize": {
        "enabled": True,  # 启用自动整理
        "priority": 4,
    },
}


# ============================================================================
# 事件处理入口
# ============================================================================

async def handle_workflow_event(event_type: str, event_data: Dict[str, Any]) -> None:
    """
    工作流事件处理入口

    根据事件类型路由到对应的处理函数，触发自动化任务。

    Args:
        event_type: 事件类型
        event_data: 事件数据
    """
    logger.debug(f"收到工作流事件: {event_type}")

    async with async_session_local() as db:
        try:
            if event_type == EVENT_SITE_SYNC_COMPLETED:
                await _handle_site_sync_completed(db, event_data)
            elif event_type == EVENT_DOWNLOAD_STARTED:
                await _handle_download_started(db, event_data)
            elif event_type == EVENT_DOWNLOAD_COMPLETED:
                await _handle_download_completed(db, event_data)
            else:
                logger.debug(f"工作流处理器暂不处理事件: {event_type}")

        except Exception as e:
            logger.exception(f"工作流事件处理失败: {event_type}, 错误: {str(e)}")


# ============================================================================
# 场景处理函数
# ============================================================================

async def _handle_site_sync_completed(
    db: AsyncSession,
    event_data: Dict[str, Any]
) -> None:
    """
    处理站点同步完成事件

    工作流：
        1. 查询该站点新增的未识别资源
        2. 如果有未识别资源，创建批量识别任务
        3. 创建订阅检查任务

    Args:
        db: 数据库会话
        event_data: 事件数据
            - site_id: 站点ID
            - site_name: 站点名称
            - resources_new: 新增资源数量
    """
    site_id = event_data.get("site_id")
    site_name = event_data.get("site_name", f"站点{site_id}")
    resources_new = event_data.get("resources_new", 0)

    if not site_id:
        logger.warning("站点同步完成事件缺少 site_id，跳过工作流")
        return

    # 场景1：自动识别新资源
    if WORKFLOW_CONFIG["site_sync_auto_identify"]["enabled"]:
        if resources_new > 0:
            # 查询未识别资源
            from app.services.pt.pt_resource_service import PTResourceService

            max_resources = WORKFLOW_CONFIG["site_sync_auto_identify"]["max_resources"]
            unidentified_resources = await PTResourceService.get_unidentified_resources(
                db, site_id=site_id, limit=max_resources
            )

            if unidentified_resources:
                # 检查是否已有运行中的识别任务（防止重复创建）
                has_running_task = await _has_running_identify_task(db)

                if has_running_task:
                    logger.debug(
                        f"站点 {site_name} 同步完成，但已有运行中的识别任务，跳过创建"
                    )
                else:
                    # 创建批量识别任务
                    execution_id = await _create_identify_task(
                        db,
                        pt_resource_ids=[r.id for r in unidentified_resources],
                        triggered_by=f"站点同步完成: {site_name}",
                    )
                    logger.info(
                        f"✓ 工作流触发: 站点 {site_name} 同步完成，"
                        f"已创建识别任务 (执行ID: {execution_id}, 资源数: {len(unidentified_resources)})"
                    )
            else:
                logger.debug(f"站点 {site_name} 无未识别资源，跳过识别任务")
        else:
            logger.debug(f"站点 {site_name} 无新增资源，跳过识别任务")

    # 场景2：自动检查订阅
    if WORKFLOW_CONFIG["site_sync_auto_check_subscription"]["enabled"]:
        # 检查是否已有运行中的订阅检查任务（防止重复创建）
        has_running_task = await _has_running_subscription_check_task(db)

        if has_running_task:
            logger.debug(
                f"站点 {site_name} 同步完成，但已有运行中的订阅检查任务，跳过创建"
            )
        else:
            execution_id = await _create_subscription_check_task(
                db,
                check_all=True,
                triggered_by=f"站点同步完成: {site_name}",
            )
            logger.info(
                f"✓ 工作流触发: 站点 {site_name} 同步完成，"
                f"已创建订阅检查任务 (执行ID: {execution_id})"
            )


async def _handle_download_started(
    db: AsyncSession,
    event_data: Dict[str, Any]
) -> None:
    """
    处理下载创建事件

    工作流：
        创建下载状态同步任务，立即同步下载器状态

    Args:
        db: 数据库会话
        event_data: 事件数据
            - download_task_id: 下载任务ID
            - torrent_name: 种子名称
    """
    if not WORKFLOW_CONFIG["download_started_auto_sync"]["enabled"]:
        logger.debug("下载创建自动同步已禁用，跳过工作流")
        return

    torrent_name = event_data.get("torrent_name", "未知")

    # 创建下载状态同步任务
    execution_id = await _create_download_status_sync_task(
        db,
        triggered_by=f"下载创建: {torrent_name}",
    )
    logger.info(
        f"✓ 工作流触发: 下载创建 ({torrent_name})，"
        f"已创建下载状态同步任务 (执行ID: {execution_id})"
    )


async def _handle_download_completed(
    db: AsyncSession,
    event_data: Dict[str, Any]
) -> None:
    """
    处理下载完成事件

    工作流：
        创建媒体文件自动整理任务

    Args:
        db: 数据库会话
        event_data: 事件数据
            - download_task_id: 下载任务ID
            - torrent_name: 种子名称
            - save_path: 保存路径
    """
    if not WORKFLOW_CONFIG["download_completed_auto_organize"]["enabled"]:
        logger.debug("下载完成自动整理已禁用，跳过工作流")
        return

    download_task_id = event_data.get("download_task_id")
    torrent_name = event_data.get("torrent_name", "未知")
    save_path = event_data.get("save_path")

    if not download_task_id or not save_path:
        logger.warning(f"下载完成事件缺少必需参数: download_task_id={download_task_id}, save_path={save_path}")
        return

    # 创建自动整理任务
    execution_id = await _create_auto_organize_task(
        db,
        download_task_id=download_task_id,
        save_path=save_path,
        triggered_by=f"下载完成: {torrent_name}",
    )
    logger.info(
        f"✓ 工作流触发: 下载完成 ({torrent_name})，"
        f"已创建自动整理任务 (执行ID: {execution_id})"
    )


# ============================================================================
# 任务去重检查函数
# ============================================================================

async def _has_running_identify_task(db: AsyncSession) -> bool:
    """
    检查是否已有运行中的识别任务

    Args:
        db: 数据库会话

    Returns:
        bool: 是否已有运行中的识别任务
    """
    from app.services.task.task_execution_service import TaskExecutionService
    from app.constants.task import EXECUTION_STATUS_PENDING, EXECUTION_STATUS_RUNNING

    # 查询是否有 pending 或 running 状态的识别任务
    running_tasks = await TaskExecutionService.get_running_tasks_by_type(
        db, TASK_TYPE_PT_RESOURCE_IDENTIFY
    )

    return len(running_tasks) > 0


async def _has_running_subscription_check_task(db: AsyncSession) -> bool:
    """
    检查是否已有运行中的订阅检查任务

    Args:
        db: 数据库会话

    Returns:
        bool: 是否已有运行中的订阅检查任务
    """
    from app.services.task.task_execution_service import TaskExecutionService

    # 查询是否有 pending 或 running 状态的订阅检查任务
    running_tasks = await TaskExecutionService.get_running_tasks_by_type(
        db, TASK_TYPE_SUBSCRIPTION_CHECK
    )

    return len(running_tasks) > 0


# ============================================================================
# 任务创建辅助函数
# ============================================================================

async def _create_identify_task(
    db: AsyncSession,
    pt_resource_ids: List[int],
    triggered_by: str = "工作流自动触发",
) -> int:
    """
    创建资源识别任务

    Args:
        db: 数据库会话
        pt_resource_ids: PT资源ID列表
        triggered_by: 触发来源描述

    Returns:
        任务执行ID
    """
    from app.services.task.task_execution_service import TaskExecutionService
    from app.schemas.task_execution import TaskExecutionCreate
    from app.services.task.scheduler_manager import scheduler_manager

    config = WORKFLOW_CONFIG["site_sync_auto_identify"]

    execution_data = TaskExecutionCreate(
        task_type=TASK_TYPE_PT_RESOURCE_IDENTIFY,
        task_name=f"[自动] 批量识别 {len(pt_resource_ids)} 个资源",
        handler=TASK_TYPE_PT_RESOURCE_IDENTIFY,
        handler_params={
            "pt_resource_ids": pt_resource_ids,
            "media_type": "auto",
            "skip_errors": config["skip_errors"],
            "triggered_by": triggered_by,
        },
        priority=config["priority"],
    )

    execution = await TaskExecutionService.create(db, execution_data)

    # 后台异步执行
    asyncio.create_task(scheduler_manager._execute_task_by_execution(execution.id))

    return execution.id


async def _create_subscription_check_task(
    db: AsyncSession,
    check_all: bool = True,
    subscription_ids: Optional[List[int]] = None,
    triggered_by: str = "工作流自动触发",
) -> int:
    """
    创建订阅检查任务

    Args:
        db: 数据库会话
        check_all: 是否检查所有订阅
        subscription_ids: 指定订阅ID列表（当 check_all=False 时使用）
        triggered_by: 触发来源描述

    Returns:
        任务执行ID
    """
    from app.services.task.task_execution_service import TaskExecutionService
    from app.schemas.task_execution import TaskExecutionCreate
    from app.services.task.scheduler_manager import scheduler_manager

    config = WORKFLOW_CONFIG["site_sync_auto_check_subscription"]

    handler_params = {
        "check_all": check_all,
        "triggered_by": triggered_by,
    }

    if not check_all and subscription_ids:
        handler_params["subscription_ids"] = subscription_ids

    execution_data = TaskExecutionCreate(
        task_type=TASK_TYPE_SUBSCRIPTION_CHECK,
        task_name=f"[自动] 检查订阅",
        handler=TASK_TYPE_SUBSCRIPTION_CHECK,
        handler_params=handler_params,
        priority=config["priority"],
    )

    execution = await TaskExecutionService.create(db, execution_data)

    # 后台异步执行
    asyncio.create_task(scheduler_manager._execute_task_by_execution(execution.id))

    return execution.id


async def _create_download_status_sync_task(
    db: AsyncSession,
    triggered_by: str = "工作流自动触发",
) -> int:
    """
    创建下载状态同步任务

    Args:
        db: 数据库会话
        triggered_by: 触发来源描述

    Returns:
        任务执行ID
    """
    from app.services.task.task_execution_service import TaskExecutionService
    from app.schemas.task_execution import TaskExecutionCreate
    from app.services.task.scheduler_manager import scheduler_manager

    config = WORKFLOW_CONFIG["download_started_auto_sync"]

    execution_data = TaskExecutionCreate(
        task_type=TASK_TYPE_DOWNLOAD_STATUS_SYNC,
        task_name=f"[自动] 同步下载状态",
        handler=TASK_TYPE_DOWNLOAD_STATUS_SYNC,
        handler_params={
            "triggered_by": triggered_by,
        },
        priority=config["priority"],
    )

    execution = await TaskExecutionService.create(db, execution_data)

    # 后台异步执行
    asyncio.create_task(scheduler_manager._execute_task_by_execution(execution.id))

    return execution.id


async def _create_auto_organize_task(
    db: AsyncSession,
    download_task_id: int,
    save_path: str,
    triggered_by: str = "工作流自动触发",
) -> int:
    """
    创建媒体文件自动整理任务

    Args:
        db: 数据库会话
        download_task_id: 下载任务ID
        save_path: 下载保存路径
        triggered_by: 触发来源描述

    Returns:
        任务执行ID
    """
    from app.services.task.task_execution_service import TaskExecutionService
    from app.schemas.task_execution import TaskExecutionCreate
    from app.services.task.scheduler_manager import scheduler_manager

    config = WORKFLOW_CONFIG["download_completed_auto_organize"]

    execution_data = TaskExecutionCreate(
        task_type=TASK_TYPE_MEDIA_FILE_AUTO_ORGANIZE,
        task_name=f"[自动] 整理下载文件",
        handler=TASK_TYPE_MEDIA_FILE_AUTO_ORGANIZE,
        handler_params={
            "download_task_id": download_task_id,
            "save_path": save_path,
            "triggered_by": triggered_by,
        },
        priority=config["priority"],
    )

    execution = await TaskExecutionService.create(db, execution_data)

    # 后台异步执行
    asyncio.create_task(scheduler_manager._execute_task_by_execution(execution.id))

    return execution.id
