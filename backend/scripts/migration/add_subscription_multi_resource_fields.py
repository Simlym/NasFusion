# -*- coding: utf-8 -*-
"""
添加订阅多资源关联字段到 subscriptions 表

新增字段：
- related_tv_ids: 关联的TV资源ID列表（同一系列的不同年番/季度）
- absolute_episode_start: 绝对集数起始
- absolute_episode_end: 绝对集数结束
- override_title: 覆写标题（用于NFO）
- override_year: 覆写年份
- override_folder: 覆写存储目录名
"""
import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

# 添加项目根目录到 Python 路径
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

# 加载环境变量
load_dotenv(backend_dir / ".env")

from sqlalchemy import text
from app.core.database import async_session_local


from app.core.config import settings


# 需要添加的新列
NEW_COLUMNS = [
    ("related_tv_ids", "TEXT", "关联的TV资源ID列表"),
    ("absolute_episode_start", "INTEGER", "绝对集数起始"),
    ("absolute_episode_end", "INTEGER", "绝对集数结束"),
    ("override_title", "VARCHAR(500)", "覆写标题"),
    ("override_year", "INTEGER", "覆写年份"),
    ("override_folder", "VARCHAR(500)", "覆写存储目录名"),
]


async def get_existing_columns(db, table_name: str) -> list:
    """获取表的现有列名"""
    if settings.database.DB_TYPE == "sqlite":
        result = await db.execute(text(f"PRAGMA table_info({table_name})"))
        columns = result.fetchall()
        return [col[1] for col in columns]
    else:
        # PostgreSQL 使用 information_schema
        result = await db.execute(text(
            f"SELECT column_name FROM information_schema.columns "
            f"WHERE table_name = '{table_name}'"
        ))
        columns = result.fetchall()
        return [col[0] for col in columns]


async def add_subscription_multi_resource_fields():
    """添加订阅多资源关联字段"""
    async with async_session_local() as db:
        try:
            # 获取现有列
            existing_columns = await get_existing_columns(db, "subscriptions")
            print(f"现有列数: {len(existing_columns)}")

            added_count = 0
            skipped_count = 0

            for column_name, column_type, description in NEW_COLUMNS:
                if column_name in existing_columns:
                    print(f"  ⏭️  {column_name} 已存在，跳过")
                    skipped_count += 1
                    continue

                # 添加新列
                sql = f"ALTER TABLE subscriptions ADD COLUMN {column_name} {column_type}"
                await db.execute(text(sql))
                print(f"  ✅ 添加 {column_name} ({description})")
                added_count += 1

            await db.commit()

            print(f"\n迁移完成！")
            print(f"  - 新增列: {added_count}")
            print(f"  - 跳过列: {skipped_count}")

        except Exception as e:
            print(f"❌ 迁移失败: {e}")
            await db.rollback()
            raise


if __name__ == "__main__":
    print("=" * 60)
    print("添加订阅多资源关联字段到 subscriptions 表")
    print("=" * 60)
    asyncio.run(add_subscription_multi_resource_fields())
    print("=" * 60)
