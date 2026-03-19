# -*- coding: utf-8 -*-
"""
Alembic 环境配置 - 支持异步 SQLAlchemy 2.0
"""
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# 导入应用配置
import sys
from pathlib import Path
import os
from dotenv import load_dotenv

# 将项目根目录添加到 Python 路径
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# 加载环境变量
env_file = Path(__file__).resolve().parents[1] / ".env"
if env_file.exists():
    load_dotenv(env_file)

from app.core.config import settings
from app.models.base import Base

# 导入所有模型以确保它们被注册到 Base.metadata
from app.models import *  # noqa: F401, F403

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# 从应用配置中设置数据库URL
config.set_main_option("sqlalchemy.url", settings.database.DATABASE_URL)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,  # 检测列类型变化
        compare_server_default=True,  # 检测默认值变化
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """执行迁移的核心函数"""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,  # 检测列类型变化
        compare_server_default=True,  # 检测默认值变化
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """在异步模式下运行迁移"""
    # 获取数据库配置
    db_config = config.get_section(config.config_ini_section, {})

    # 为 SQLite 添加更长的超时时间（60秒）
    database_url = db_config.get("sqlalchemy.url", "")
    if "sqlite" in database_url:
        db_config["sqlalchemy.connect_args"] = {"timeout": 60}

    connectable = async_engine_from_config(
        db_config,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
