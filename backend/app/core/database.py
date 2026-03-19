"""
数据库会话管理模块
支持SQLite和PostgreSQL双数据库
"""
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool, StaticPool

from app.core.config import settings

# 创建异步数据库引擎
# 根据数据库类型选择不同的配置
if settings.database.DB_TYPE == "sqlite":
    # SQLite特殊配置
    engine = create_async_engine(
        settings.database.DATABASE_URL,
        echo=False,  # 关闭SQL日志输出
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # SQLite使用静态连接池
    )
else:
    # PostgreSQL配置
    engine = create_async_engine(
        settings.database.DATABASE_URL,
        echo=False,  # 关闭SQL日志输出
        pool_pre_ping=True,  # 连接前检查连接有效性
        pool_size=10,  # 连接池大小
        max_overflow=20,  # 最大溢出连接数
    )

# 创建异步会话工厂
async_session_local = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    依赖注入：获取数据库会话

    使用示例:
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            # 使用db进行数据库操作
            pass

    注意：
        - 在 finally 中调用 rollback 确保连接归还前事务状态干净
        - 对于已提交的事务，rollback 是无操作
        - 对于失败/aborted 的事务，rollback 会清理状态
        - 这可以防止 PostgreSQL 的 "current transaction is aborted" 错误
    """
    async with async_session_local() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.rollback()
            await session.close()


async def init_db() -> None:
    """
    初始化数据库
    创建所有表（仅用于开发环境，生产环境应使用Alembic）
    """
    from app.models.base import Base

    async with engine.begin() as conn:
        # 开发环境：创建所有表
        # 生产环境：应该使用 alembic upgrade head
        if settings.DEBUG:
            await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """
    关闭数据库连接
    应用关闭时调用
    """
    await engine.dispose()
