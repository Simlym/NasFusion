"""
系统初始化模块
负责数据库初始化、管理员账户创建等
"""
import json
import logging
import subprocess
from pathlib import Path

from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Base
from app.schemas.user import UserCreate
from app.services.user.user_service import UserService
from app.core.config import settings

logger = logging.getLogger(__name__)


async def _is_fresh_database(backend_path: Path) -> bool:
    """检测是否为全新数据库（alembic_version 表不存在）"""
    try:
        from app.core.config import settings
        from sqlalchemy import create_engine, inspect

        db_url = settings.database.DATABASE_URL
        # 将异步驱动替换为同步驱动
        sync_url = db_url.replace("sqlite+aiosqlite", "sqlite").replace("postgresql+asyncpg", "postgresql+psycopg2")
        sync_engine = create_engine(sync_url)
        with sync_engine.connect():
            inspector = inspect(sync_engine)
            tables = inspector.get_table_names()
            return "alembic_version" not in tables
    except Exception:
        return False


async def run_alembic_migrations():
    """
    执行 Alembic 数据库迁移

    使用 subprocess 调用 alembic 命令，确保迁移在独立的进程中执行。
    新项目（全新数据库）直接 stamp head，跳过历史迁移，由 create_all 建表。
    老项目（已有 alembic_version）正常执行 upgrade head。
    """
    try:
        import asyncio

        logger.info("正在检查并执行数据库迁移...")

        # 获取 backend 目录路径
        backend_path = Path(__file__).parent.parent.parent
        alembic_ini_path = backend_path / "alembic.ini"

        if not alembic_ini_path.exists():
            logger.warning(f"alembic.ini 不存在于 {alembic_ini_path}，跳过迁移")
            return

        # 检测是否为全新数据库
        is_fresh = await _is_fresh_database(backend_path)

        if is_fresh:
            # 新项目：直接 stamp head，跳过所有历史迁移，由后续 create_all 建表
            logger.info("检测到全新数据库，跳过历史迁移，直接标记为最新版本...")

            def stamp_head():
                return subprocess.run(
                    ["alembic", "stamp", "head"],
                    cwd=str(backend_path),
                    capture_output=True,
                    text=True,
                )

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, stamp_head)

            if result.returncode != 0:
                logger.warning(f"alembic stamp head 失败: {result.stderr}")
            else:
                logger.info("新数据库已标记为最新迁移版本，将由 create_all 创建所有表")
        else:
            # 老项目：正常执行迁移链
            def run_migration():
                return subprocess.run(
                    ["alembic", "upgrade", "head"],
                    cwd=str(backend_path),
                    capture_output=True,
                    text=True,
                )

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, run_migration)

            if result.returncode != 0:
                logger.warning(f"数据库迁移执行失败: {result.stderr}")
            else:
                logger.info("数据库迁移完成")
                if result.stdout:
                    logger.debug(f"Alembic 输出: {result.stdout}")

    except FileNotFoundError:
        logger.warning("Alembic 命令未找到，跳过数据库迁移")
    except Exception as e:
        logger.warning(f"执行数据库迁移时出错: {e}")


async def init_database(engine):
    """
    初始化数据库表结构，自动处理表结构更新

    Args:
        engine: 数据库引擎
    """
    logger.info("数据库表结构初始化开始...")

    # 先执行 Alembic 迁移（会等待完成）
    await run_alembic_migrations()

    # 等待一小段时间确保数据库连接完全释放
    import asyncio
    await asyncio.sleep(0.5)

    # 作为后备方案，创建所有表结构（处理没有迁移的新表）
    async with engine.begin() as conn:
        # 创建所有表结构
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)

    logger.info("数据库表结构初始化完成")


async def init_admin_user(db: AsyncSession):
    """
    初始化管理员账户

    如果系统中没有用户，则创建默认管理员账户：
    - username: admin
    - password: admin 或 随机生成的密码

    Args:
        db: 数据库会话
    """
    # 检查是否是第一个用户
    is_first = await UserService.is_first_user(db)

    if not is_first:
        logger.debug("系统中已存在用户，跳过管理员初始化")
        return

    logger.info("检测到系统首次启动，正在创建默认管理员账户...")

    # 默认管理员用户名
    admin_username = "admin"

    admin_password = "admin123"

    try:
        # 创建管理员用户
        admin_user = await UserService.create_user(
            db,
            UserCreate(
                username=admin_username,
                password=admin_password,
                role="admin",
                email=None,
                display_name="系统管理员",
                language="zh-CN",
                timezone="UTC",
            ),
        )

        logger.warning("=" * 80)
        logger.warning("管理员账户创建成功！")
        logger.warning(f"用户名: {admin_username}")
        logger.warning(f"密码: {admin_password}")
        logger.warning("请妥善保管此密码，并在首次登录后立即修改！")
        logger.warning("=" * 80)

        # 同时打印到控制台
        print("\n" + "=" * 80)
        print("🎉 管理员账户创建成功！")
        print(f"用户名: {admin_username}")
        print(f"密码: {admin_password}")
        print("请妥善保管此密码，并在首次登录后立即修改！")
        print("=" * 80 + "\n")

    except Exception as e:
        logger.error(f"创建管理员账户失败: {e}")
        raise


async def init_media_library_directories(db: AsyncSession):
    """
    初始化媒体库目录结构（新挂载点系统）

    - 创建默认整理配置
    """
    logger.info("正在初始化媒体库目录结构...")

    from app.services.mediafile.organize_config_service import OrganizeConfigService

    # 注意：存储挂载点已改为手工添加，不再自动扫描
    logger.debug("存储挂载点采用手工添加模式，跳过自动扫描")

    # 创建默认整理配置
    logger.debug("正在创建默认整理配置...")
    try:
        # create_default_configs 函数内部会检查每种媒体类型是否已存在配置
        created = await OrganizeConfigService.create_default_configs(db)
        if created:
            logger.info(f"创建默认整理配置，新增 {len(created)} 个配置")
        else:
            logger.debug("默认整理配置检查完成，所有配置已存在")
    except Exception as e:
        logger.error(f"创建默认整理配置失败: {e}")

    # 初始化系统设置默认值
    await init_system_settings(db)

    logger.info("媒体库目录结构初始化完成")


async def init_system_settings(db: AsyncSession):
    """
    初始化系统设置默认值

    确保所有已知的系统设置在数据库中都有记录，
    已存在的设置不会被覆盖。
    """
    from app.services.common.system_setting_service import SystemSettingService

    # 需要初始化的默认设置列表: (category, key, default_value, description)
    default_settings = [
        ("media_library", "show_adult_content", "false", "是否在媒体库显示成人内容页签"),
        ("media_library", "movie_show_anime", "false", "电影列表是否显示动画内容"),
        ("media_library", "tv_show_anime", "false", "剧集列表是否显示动画内容"),
        ("homepage", "backdrop_count", "10", "首页Hero轮播背景图显示数量（1-50）"),
    ]

    for category, key, value, description in default_settings:
        existing = await SystemSettingService.get_by_key(db, category, key)
        if existing:
            continue

        await SystemSettingService.upsert(
            db,
            category=category,
            key=key,
            value=value,
            description=description,
        )
        logger.info(f"系统设置已初始化: {category}/{key} = {value}")


async def init_identification_priority(db: AsyncSession):
    """
    初始化资源识别优先级配置

    创建 metadata_scraping/identification_priority 系统设置，
    使用默认的识别源优先级顺序
    """
    from app.services.common.system_setting_service import SystemSettingService
    from app.schemas.system_setting import SystemSettingCreate
    from app.constants.resource_identification import DEFAULT_IDENTIFICATION_PRIORITY

    # 检查是否已存在配置
    existing = await SystemSettingService.get_by_key(
        db, "metadata_scraping", "identification_priority"
    )

    if existing:
        logger.debug("资源识别优先级配置已存在，跳过初始化")
        return

    logger.debug("正在初始化资源识别优先级配置...")

    # 创建默认配置
    setting_data = SystemSettingCreate(
        category="metadata_scraping",
        key="identification_priority",
        value=json.dumps({"enabled_sources": DEFAULT_IDENTIFICATION_PRIORITY}),
        description="资源识别优先级配置（启用的识别源及其顺序）",
        is_active=True
    )

    await SystemSettingService.create(db, setting_data)
    logger.info("资源识别优先级配置已初始化")


async def cleanup_stuck_tasks(db: AsyncSession):
    """
    清理卡住的任务（系统启动时）

    将所有处于 pending 或 running 状态的任务标记为失败，
    这些任务可能是因为程序异常退出而没有正常完成。
    """
    logger.debug("正在清理卡住的任务...")

    from app.services.task.task_execution_service import TaskExecutionService
    from app.constants import (
        EXECUTION_STATUS_PENDING,
        EXECUTION_STATUS_RUNNING,
        EXECUTION_STATUS_FAILED
    )
    from sqlalchemy import update
    from app.models.task_execution import TaskExecution

    try:
        # 查询所有 pending 或 running 状态的任务
        stmt = (
            update(TaskExecution)
            .where(
                or_(
                    TaskExecution.status == EXECUTION_STATUS_PENDING,
                    TaskExecution.status == EXECUTION_STATUS_RUNNING
                )
            )
            .values(
                status=EXECUTION_STATUS_FAILED,
                error_message="系统重启，任务被中断",
                completed_at=None
            )
        )

        result = await db.execute(stmt)
        await db.commit()

        stuck_count = result.rowcount
        if stuck_count > 0:
            logger.info(f"已清理 {stuck_count} 个卡住的任务")
        else:
            logger.debug("没有发现卡住的任务")

    except Exception as e:
        logger.error(f"清理卡住的任务失败: {e}")


async def initialize_system(engine, db: AsyncSession):
    """
    初始化整个系统

    Args:
        engine: 数据库引擎
        db: 数据库会话
    """
    logger.info("开始初始化系统...")

    # 1. 初始化数据库表
    await init_database(engine)

    # 2. 清理卡住的任务（在系统启动时）
    await cleanup_stuck_tasks(db)

    # 3. 初始化管理员账户
    await init_admin_user(db)

    # 4. 初始化媒体库目录结构
    await init_media_library_directories(db)

    # 5. 初始化资源识别优先级配置
    await init_identification_priority(db)

    # 6. 初始化系统任务
    from app.core.init_scheduled_tasks import init_system_tasks
    await init_system_tasks()

    logger.info("系统初始化完成")
