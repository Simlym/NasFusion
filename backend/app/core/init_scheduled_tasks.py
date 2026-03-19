# -*- coding: utf-8 -*-
"""
系统初始化
在应用启动时自动创建必要的系统任务
"""
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import (
    SCHEDULE_TYPE_CRON,
    SCHEDULE_TYPE_INTERVAL,
    SCHEDULE_TYPE_MANUAL,
    TASK_TYPE_TASK_EXECUTION_CLEANUP,
    TASK_TYPE_SUBSCRIPTION_CHECK,
    TASK_TYPE_DOWNLOAD_STATUS_SYNC,
    TASK_TYPE_PT_RESOURCE_IDENTIFY,
    TASK_TYPE_MEDIA_SERVER_WATCH_HISTORY_SYNC,
    TASK_TYPE_MEDIA_SERVER_LIBRARY_STATS_UPDATE,
    TASK_TYPE_MEDIA_SERVER_LIBRARY_SYNC,
    TASK_TYPE_TRENDING_SYNC,
    TASK_TYPE_TRENDING_DETAIL_SYNC,
    TASK_TYPE_PERSON_DETAIL_SYNC,
    TASK_TYPE_CREDITS_BACKFILL,
    TASK_TYPE_PERSON_MERGE,
)
from app.constants.trending import (
    DEFAULT_TRENDING_SYNC_COUNT,
    DEFAULT_TRENDING_SYNC_CRON,
)
from app.core.config import settings
from app.core.database import async_session_local
from app.models.scheduled_task import ScheduledTask
from app.services.task.scheduler_manager import scheduler_manager

logger = logging.getLogger(__name__)


async def init_subscription_check_task(db: AsyncSession):
    """
    初始化全局订阅检查任务

    创建一个定时任务，定期扫描所有需要检查的订阅（next_check_at <= now()）
    """
    # 检查是否已存在订阅检查任务（使用 task_name 检查，因为它有 UNIQUE 约束）
    task_name = "订阅自动检查（全局）"
    result = await db.execute(
        select(ScheduledTask).where(ScheduledTask.task_name == task_name)
    )
    existing_task = result.scalar_one_or_none()

    if existing_task:
        logger.debug(f"订阅检查任务已存在: {existing_task.task_name} (ID: {existing_task.id})")
        return existing_task

    # 创建全局订阅检查任务
    check_interval = 5

    task = ScheduledTask(
        task_type=TASK_TYPE_SUBSCRIPTION_CHECK,
        task_name=task_name,
        description=f"每{check_interval}分钟扫描一次，检查所有到期的订阅（next_check_at <= now()）",
        schedule_type=SCHEDULE_TYPE_INTERVAL,
        schedule_config={
            "interval": check_interval,
            "unit": "minutes"
        },
        handler=TASK_TYPE_SUBSCRIPTION_CHECK,  # 使用任务类型作为 handler
        handler_params={
            "check_all": True,           # 检查所有订阅
            "sync_resources": False,     # 是否先同步PT资源（用订阅标题搜索）
            "sync_max_pages": 1,         # 同步最大页数
            "auto_identify": False,      # 是否自动识别匹配关键字的未识别资源
        },
        enabled=True,
        priority=5,  # 中等优先级
        max_retries=3,
    )

    db.add(task)
    await db.commit()
    await db.refresh(task)

    logger.info(f"已创建订阅检查任务: {task.task_name} (ID: {task.id}), 间隔: {check_interval}分钟")

    return task


async def init_download_sync_task(db: AsyncSession):
    """
    初始化下载状态同步任务

    创建一个定时任务，每分钟检查所有进行中的下载任务
    """
    task_name = "监听下载完成"
    result = await db.execute(
        select(ScheduledTask).where(ScheduledTask.task_name == task_name)
    )
    existing_task = result.scalar_one_or_none()

    if existing_task:
        logger.debug(f"下载同步任务已存在: {existing_task.task_name} (ID: {existing_task.id})")
        return existing_task

    # 创建下载状态同步任务
    task = ScheduledTask(
        task_type=TASK_TYPE_DOWNLOAD_STATUS_SYNC,
        task_name=task_name,
        description="每分钟检查所有进行中的下载任务，自动创建 MediaFile 记录",
        schedule_type=SCHEDULE_TYPE_INTERVAL,
        schedule_config={"interval": 1, "unit": "minutes"},
        handler=TASK_TYPE_DOWNLOAD_STATUS_SYNC,  # 使用任务类型作为 handler
        handler_params={},
        enabled=True,
        priority=2,  # 较高优先级
        max_retries=1,
    )

    db.add(task)
    await db.commit()
    await db.refresh(task)

    logger.info(f"已创建下载同步任务: {task.task_name} (ID: {task.id})")

    return task


async def init_cleanup_task(db: AsyncSession):
    """
    初始化历史记录清理任务

    创建一个定时任务，每天凌晨清理旧的执行记录
    """
    task_name = "清理任务执行历史"
    result = await db.execute(
        select(ScheduledTask).where(ScheduledTask.task_name == task_name)
    )
    existing_task = result.scalar_one_or_none()

    if existing_task:
        logger.debug(f"清理任务已存在: {existing_task.task_name} (ID: {existing_task.id})")
        return existing_task

    # 创建清理任务（每天凌晨3点执行）
    task = ScheduledTask(
        task_type=TASK_TYPE_TASK_EXECUTION_CLEANUP,
        task_name=task_name,
        description="每天凌晨3点清理7天前的已完成任务执行记录（保留失败记录）",
        schedule_type=SCHEDULE_TYPE_CRON,
        schedule_config={
            "cron": "0 3 * * *",  # 每天凌晨3点
            "timezone": "Asia/Shanghai"
        },
        handler=TASK_TYPE_TASK_EXECUTION_CLEANUP,  # 使用任务类型作为 handler
        handler_params={
            "days": 7,  # 保留7天
            "keep_failed": True  # 保留失败记录
        },
        enabled=True,
        priority=1,  # 低优先级
        max_retries=1,
    )

    db.add(task)
    await db.commit()
    await db.refresh(task)

    logger.info(f"已创建清理任务: {task.task_name} (ID: {task.id})")

    return task


async def init_resource_identify_task(db: AsyncSession):
    """
    初始化批量识别任务

    创建一个手动触发的任务，允许用户批量识别PT资源
    """
    task_name = "批量识别PT资源"
    result = await db.execute(
        select(ScheduledTask).where(ScheduledTask.task_name == task_name)
    )
    existing_task = result.scalar_one_or_none()

    if existing_task:
        logger.debug(f"批量识别任务已存在: {existing_task.task_name} (ID: {existing_task.id})")
        return existing_task

    # 创建手动触发的批量识别任务
    task = ScheduledTask(
        task_type=TASK_TYPE_PT_RESOURCE_IDENTIFY,
        task_name=task_name,
        description="手动批量识别PT资源，支持指定识别数量和资源分类",
        schedule_type=SCHEDULE_TYPE_MANUAL,
        schedule_config={},
        handler=TASK_TYPE_PT_RESOURCE_IDENTIFY,
        handler_params={
            "limit": 100,  # 默认识别100个
            "category": None,  # 默认不限制分类
            "skip_errors": True
        },
        enabled=True,
        priority=3,  # 中等优先级
        max_retries=1,
    )

    db.add(task)
    await db.commit()
    await db.refresh(task)

    logger.info(f"已创建批量识别任务: {task.task_name} (ID: {task.id})")

    return task


async def init_media_server_tasks(db: AsyncSession):
    """
    初始化媒体服务器自动同步任务
    """
    # 1. 观看历史全局同步任务
    sync_task_name = "媒体服务器观看历史定时同步"
    sync_result = await db.execute(
        select(ScheduledTask).where(ScheduledTask.task_name == sync_task_name)
    )
    if not sync_result.scalar_one_or_none():
        sync_task = ScheduledTask(
            task_type=TASK_TYPE_MEDIA_SERVER_WATCH_HISTORY_SYNC,
            task_name=sync_task_name,
            description="定期检查所有已启用的媒体服务器，同步最新的观看历史数据",
            schedule_type=SCHEDULE_TYPE_INTERVAL,
            schedule_config={"interval": 30, "unit": "minutes"},  # 每30分钟检查一次分发
            handler=TASK_TYPE_MEDIA_SERVER_WATCH_HISTORY_SYNC,
            handler_params={},  # 空参数表示全局同步
            enabled=True,
            priority=3,
            max_retries=1,
        )
        db.add(sync_task)
        logger.info(f"已创建媒体服务器观看历史同步任务: {sync_task_name}")

    # 2. 库统计全局更新任务
    stats_task_name = "媒体服务器库统计定时更新"
    stats_result = await db.execute(
        select(ScheduledTask).where(ScheduledTask.task_name == stats_task_name)
    )
    if not stats_result.scalar_one_or_none():
        stats_task = ScheduledTask(
            task_type=TASK_TYPE_MEDIA_SERVER_LIBRARY_STATS_UPDATE,
            task_name=stats_task_name,
            description="定期更新所有媒体服务器的媒体库统计数据（电影/剧集数量等）",
            schedule_type=SCHEDULE_TYPE_INTERVAL,
            schedule_config={"interval": 6, "unit": "hours"},  # 每6小时更新一次
            handler=TASK_TYPE_MEDIA_SERVER_LIBRARY_STATS_UPDATE,
            handler_params={},  # 空参数表示全局更新
            enabled=True,
            priority=1,
            max_retries=1,
        )
        db.add(stats_task)
        logger.info(f"已创建媒体服务器库统计更新任务: {stats_task_name}")

    # 3. 媒体库同步全局任务
    library_sync_task_name = "媒体服务器媒体库定时同步"
    library_sync_result = await db.execute(
        select(ScheduledTask).where(ScheduledTask.task_name == library_sync_task_name)
    )
    if not library_sync_result.scalar_one_or_none():
        library_sync_task = ScheduledTask(
            task_type=TASK_TYPE_MEDIA_SERVER_LIBRARY_SYNC,
            task_name=library_sync_task_name,
            description="定期同步所有已启用的媒体服务器的媒体库数据",
            schedule_type=SCHEDULE_TYPE_INTERVAL,
            schedule_config={"interval": 6, "unit": "hours"},  # 每6小时同步一次
            handler=TASK_TYPE_MEDIA_SERVER_LIBRARY_SYNC,
            handler_params={},  # 空参数表示全局同步
            enabled=True,
            priority=2,
            max_retries=1,
        )
        db.add(library_sync_task)
        logger.info(f"已创建媒体服务器媒体库同步任务: {library_sync_task_name}")

    await db.commit()


async def init_trending_sync_task(db: AsyncSession):
    """
    初始化榜单同步任务

    创建一个定时任务，每天定时同步豆瓣和TMDB的热门榜单
    """
    task_name = "榜单自动同步（全局）"
    result = await db.execute(
        select(ScheduledTask).where(ScheduledTask.task_name == task_name)
    )
    existing_task = result.scalar_one_or_none()

    if existing_task:
        logger.debug(f"榜单同步任务已存在: {existing_task.task_name} (ID: {existing_task.id})")
        return existing_task

    # 创建榜单同步任务（每天08:00和20:00执行）
    task = ScheduledTask(
        task_type=TASK_TYPE_TRENDING_SYNC,
        task_name=task_name,
        description=f"每天08:00和20:00同步豆瓣和TMDB热门榜单（每个榜单{DEFAULT_TRENDING_SYNC_COUNT}条）",
        schedule_type=SCHEDULE_TYPE_CRON,
        schedule_config={
            "cron": DEFAULT_TRENDING_SYNC_CRON,  # "0 8,20 * * *"
            "timezone": "Asia/Shanghai"
        },
        handler=TASK_TYPE_TRENDING_SYNC,  # 使用任务类型作为 handler
        handler_params={
            "collection_types": None,  # None = 同步所有榜单
            "count": DEFAULT_TRENDING_SYNC_COUNT  # 100
        },
        enabled=True,
        priority=3,  # 中等优先级
        max_retries=2,
    )

    db.add(task)
    await db.commit()
    await db.refresh(task)

    logger.info(f"已创建榜单同步任务: {task.task_name} (ID: {task.id}), cron: {DEFAULT_TRENDING_SYNC_CRON}")

    return task


async def init_trending_detail_sync_task(db: AsyncSession):
    """
    初始化榜单详情同步任务

    创建一个定时任务，异步处理榜单详情同步（阶段二）
    """
    task_name = "榜单详情同步（异步）"
    result = await db.execute(
        select(ScheduledTask).where(ScheduledTask.task_name == task_name)
    )
    existing_task = result.scalar_one_or_none()

    if existing_task:
        logger.debug(f"榜单详情同步任务已存在: {existing_task.task_name} (ID: {existing_task.id})")
        return existing_task

    # 创建榜单详情同步任务（每30分钟执行一次）
    task = ScheduledTask(
        task_type=TASK_TYPE_TRENDING_DETAIL_SYNC,
        task_name=task_name,
        description="定期处理榜单记录的详情同步，创建/更新 unified_movies/unified_tv_series 记录",
        schedule_type=SCHEDULE_TYPE_INTERVAL,
        schedule_config={
            "interval": 30,
            "unit": "minutes"
        },
        handler=TASK_TYPE_TRENDING_DETAIL_SYNC,
        handler_params={
            "batch_size": 20,  # 每批处理20条
            "max_batches": 50  # 最大处理50批
        },
        enabled=True,
        priority=2,  # 较高优先级
        max_retries=2,
    )

    db.add(task)
    await db.commit()
    await db.refresh(task)

    logger.info(f"已创建榜单详情同步任务: {task.task_name} (ID: {task.id})")

    return task


async def init_person_detail_sync_task(db: AsyncSession):
    """
    初始化人员详情同步任务

    创建一个定时任务，定期批量从 TMDB 获取人员的 biography/birthday 等详情
    """
    task_name = "人员详情同步"
    result = await db.execute(
        select(ScheduledTask).where(ScheduledTask.task_name == task_name)
    )
    existing_task = result.scalar_one_or_none()

    if existing_task:
        logger.debug(f"人员详情同步任务已存在: {existing_task.task_name} (ID: {existing_task.id})")
        return existing_task

    task = ScheduledTask(
        task_type=TASK_TYPE_PERSON_DETAIL_SYNC,
        task_name=task_name,
        description="定期批量从 TMDB 获取人员详情（biography/birthday 等），每次处理50条未同步记录",
        schedule_type=SCHEDULE_TYPE_INTERVAL,
        schedule_config={
            "interval": 30,
            "unit": "minutes"
        },
        handler=TASK_TYPE_PERSON_DETAIL_SYNC,
        handler_params={
            "limit": 50,
        },
        enabled=True,
        priority=2,
        max_retries=2,
    )

    db.add(task)
    await db.commit()
    await db.refresh(task)

    logger.info(f"已创建人员详情同步任务: {task.task_name} (ID: {task.id})")

    return task


async def init_credits_backfill_task(db: AsyncSession):
    """
    初始化演职员关系回填任务

    一次性手动任务，将已识别资源的 JSON 演员数据回填到 credits 关联表
    """
    task_name = "演职员关系回填"
    result = await db.execute(
        select(ScheduledTask).where(ScheduledTask.task_name == task_name)
    )
    existing_task = result.scalar_one_or_none()

    if existing_task:
        logger.debug(f"演职员关系回填任务已存在: {existing_task.task_name} (ID: {existing_task.id})")
        return existing_task

    task = ScheduledTask(
        task_type=TASK_TYPE_CREDITS_BACKFILL,
        task_name=task_name,
        description="将已识别资源的演员/导演 JSON 数据回填到 movie_credits/tv_series_credits 关联表。支持参数: limit(数量), source(tmdb/douban)",
        schedule_type=SCHEDULE_TYPE_MANUAL,
        schedule_config={},
        handler=TASK_TYPE_CREDITS_BACKFILL,
        handler_params={
            "limit": 100,
            "source": "tmdb",
        },
        enabled=True,
        priority=3,
        max_retries=1,
    )

    db.add(task)
    await db.commit()
    await db.refresh(task)

    logger.info(f"已创建演职员关系回填任务: {task.task_name} (ID: {task.id})")

    return task


async def init_person_merge_task(db: AsyncSession):
    """
    初始化重复人物合并任务

    手动触发任务，将 name+birthday 相同且 detail_loaded=True 的重复人物记录合并
    """
    task_name = "重复人物合并"
    result = await db.execute(
        select(ScheduledTask).where(ScheduledTask.task_name == task_name)
    )
    existing_task = result.scalar_one_or_none()

    if existing_task:
        logger.debug(f"重复人物合并任务已存在: {existing_task.task_name} (ID: {existing_task.id})")
        return existing_task

    task = ScheduledTask(
        task_type=TASK_TYPE_PERSON_MERGE,
        task_name=task_name,
        description="将 name+birthday 相同且详情已加载的重复人物记录合并，"
                    "优先保留豆瓣来源记录，同时迁移演职表关系。"
                    "支持参数: dry_run(预览模式), limit(分组数量)",
        schedule_type=SCHEDULE_TYPE_MANUAL,
        schedule_config={},
        handler=TASK_TYPE_PERSON_MERGE,
        handler_params={
            "dry_run": False,
            "limit": 100,
        },
        enabled=True,
        priority=3,
        max_retries=1,
    )

    db.add(task)
    await db.commit()
    await db.refresh(task)

    logger.info(f"已创建重复人物合并任务: {task.task_name} (ID: {task.id})")

    return task


async def init_system_tasks():
    """
    初始化所有系统任务
    在应用启动时调用
    """
    logger.debug("开始初始化系统任务...")

    async with async_session_local() as db:
        try:
            # 初始化订阅检查任务
            await init_subscription_check_task(db)

            # 初始化下载状态同步任务
            await init_download_sync_task(db)

            # 初始化清理任务
            await init_cleanup_task(db)

            # 初始化批量识别任务
            await init_resource_identify_task(db)

            # 初始化媒体服务器任务
            await init_media_server_tasks(db)

            # 初始化榜单同步任务
            await init_trending_sync_task(db)

            # 初始化榜单详情同步任务
            await init_trending_detail_sync_task(db)

            # 初始化人员详情同步任务
            await init_person_detail_sync_task(db)

            # 初始化演职员关系回填任务
            await init_credits_backfill_task(db)

            # 初始化重复人物合并任务
            await init_person_merge_task(db)

            logger.info("系统任务初始化完成")

        except Exception as e:
            logger.error(f"系统任务初始化失败: {e}", exc_info=True)
            raise
