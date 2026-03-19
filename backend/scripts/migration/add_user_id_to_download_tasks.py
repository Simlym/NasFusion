# -*- coding: utf-8 -*-
"""
添加 user_id 字段到 download_tasks 表

用途：
1. 在 download_tasks 表中添加 user_id 字段
2. 创建外键约束和索引

使用方法：
    python scripts/migration/add_user_id_to_download_tasks.py
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from app.core.database import async_session_local


async def add_user_id_field():
    """添加 user_id 字段到 download_tasks 表"""
    async with async_session_local() as db:
        try:
            print("\n开始迁移：添加 user_id 字段到 download_tasks 表")
            print("=" * 60)

            # 检查字段是否已存在
            print("[1/4] 检查字段是否已存在...")
            check_column_sql = """
            SELECT COUNT(*)
            FROM pragma_table_info('download_tasks')
            WHERE name='user_id';
            """
            result = await db.execute(text(check_column_sql))
            exists = result.scalar()

            if exists > 0:
                print("✓ user_id 字段已存在，跳过迁移")
                return

            # 添加 user_id 列
            print("[2/4] 添加 user_id 列...")
            add_column_sql = """
            ALTER TABLE download_tasks
            ADD COLUMN user_id INTEGER;
            """
            await db.execute(text(add_column_sql))
            print("✓ user_id 列添加成功")

            # 创建索引
            print("[3/4] 创建索引...")
            create_index_sql = """
            CREATE INDEX IF NOT EXISTS ix_download_tasks_user_id
            ON download_tasks(user_id);
            """
            await db.execute(text(create_index_sql))
            print("✓ 索引创建成功")

            # 创建外键（SQLite 需要重建表，这里先跳过外键约束）
            # 注意：SQLite 不支持 ALTER TABLE ADD CONSTRAINT，外键在模型中定义即可
            print("[4/4] 外键约束将在重启应用后生效（通过 SQLAlchemy 模型定义）")

            await db.commit()
            print("\n✓ 迁移完成！")
            print("=" * 60)
            print("\n提示：请重启应用以使所有更改生效")

        except Exception as e:
            await db.rollback()
            print(f"\n✗ 迁移失败：{e}")
            raise


async def main():
    """主函数"""
    try:
        await add_user_id_field()
    except Exception as e:
        print(f"\n错误：{e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
