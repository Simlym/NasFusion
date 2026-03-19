# -*- coding: utf-8 -*-
"""
添加 organize_mode 字段到 media_files 表
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import text
from app.core.database import async_session_maker


async def add_organize_mode_column():
    """添加 organize_mode 列到 media_files 表"""
    async with async_session_maker() as db:
        try:
            # 检查列是否已存在
            result = await db.execute(text("PRAGMA table_info(media_files)"))
            columns = result.fetchall()
            column_names = [col[1] for col in columns]

            if 'organize_mode' in column_names:
                print("✅ organize_mode 列已存在，无需添加")
                return

            # 添加新列
            await db.execute(
                text("ALTER TABLE media_files ADD COLUMN organize_mode VARCHAR(20)")
            )
            await db.commit()
            print("✅ 成功添加 organize_mode 列到 media_files 表")

        except Exception as e:
            print(f"❌ 添加列失败: {e}")
            await db.rollback()
            raise


if __name__ == "__main__":
    print("开始添加 organize_mode 列...")
    asyncio.run(add_organize_mode_column())
    print("完成！")
