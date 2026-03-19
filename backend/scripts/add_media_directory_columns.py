# -*- coding: utf-8 -*-
"""
添加媒体目录相关字段的数据库迁移脚本

使用方法:
    cd backend
    python scripts/add_media_directory_columns.py
"""
import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 加载环境变量
env_file = project_root / ".env"
load_dotenv(env_file)

from sqlalchemy import text
from app.core.database import async_session_local, engine


async def migrate():
    """执行迁移"""
    print("=" * 60)
    print("开始执行数据库迁移：添加媒体目录支持")
    print("=" * 60)

    async with engine.begin() as conn:
        # 1. 创建 media_directories 表
        print("\n📦 步骤 1/2: 创建 media_directories 表...")

        create_table_sql = """
        CREATE TABLE IF NOT EXISTS media_directories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            directory_path TEXT NOT NULL UNIQUE,
            parent_id INTEGER,
            depth INTEGER NOT NULL DEFAULT 0,
            media_type VARCHAR(20),
            file_count INTEGER NOT NULL DEFAULT 0,
            total_size BIGINT NOT NULL DEFAULT 0,
            video_count INTEGER NOT NULL DEFAULT 0,
            audio_count INTEGER NOT NULL DEFAULT 0,
            subtitle_count INTEGER NOT NULL DEFAULT 0,
            other_count INTEGER NOT NULL DEFAULT 0,
            has_mixed_types BOOLEAN NOT NULL DEFAULT 0,
            has_nfo BOOLEAN NOT NULL DEFAULT 0,
            has_poster BOOLEAN NOT NULL DEFAULT 0,
            has_backdrop BOOLEAN NOT NULL DEFAULT 0,
            nfo_path TEXT,
            poster_path TEXT,
            backdrop_path TEXT,
            organized BOOLEAN NOT NULL DEFAULT 0,
            organized_path TEXT,
            organized_at TIMESTAMP WITH TIME ZONE,
            title VARCHAR(500),
            year INTEGER,
            season_number INTEGER,
            unified_table_name VARCHAR(50),
            unified_resource_id INTEGER,
            match_method VARCHAR(30) DEFAULT 'none',
            match_confidence INTEGER,
            discovered_at TIMESTAMP WITH TIME ZONE NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (parent_id) REFERENCES media_directories(id) ON DELETE CASCADE
        )
        """

        try:
            await conn.execute(text(create_table_sql))
            print("  ✅ media_directories 表创建成功")
        except Exception as e:
            print(f"  ⚠️  表可能已存在: {e}")

        # 2. 检查并添加 media_directory_id 列到 media_files 表
        print("\n📝 步骤 2/2: 添加 media_directory_id 列到 media_files 表...")

        # 检查列是否已存在
        check_column_sql = """
        SELECT COUNT(*) as count
        FROM pragma_table_info('media_files')
        WHERE name = 'media_directory_id'
        """

        result = await conn.execute(text(check_column_sql))
        row = result.fetchone()
        column_exists = row[0] > 0

        if column_exists:
            print("  ⚠️  media_directory_id 列已存在，跳过添加")
        else:
            # 添加新列
            add_column_sql = """
            ALTER TABLE media_files
            ADD COLUMN media_directory_id INTEGER REFERENCES media_directories(id)
            """

            try:
                await conn.execute(text(add_column_sql))
                print("  ✅ media_directory_id 列添加成功")
            except Exception as e:
                print(f"  ❌ 添加列失败: {e}")
                return

        # 3. 创建索引
        print("\n🔧 步骤 3/3: 创建索引...")

        indexes = [
            "CREATE INDEX IF NOT EXISTS ix_media_directories_parent_id ON media_directories(parent_id)",
            "CREATE INDEX IF NOT EXISTS ix_media_directories_media_type ON media_directories(media_type)",
            "CREATE INDEX IF NOT EXISTS ix_media_directories_organized ON media_directories(organized)",
            "CREATE INDEX IF NOT EXISTS ix_media_files_media_directory_id ON media_files(media_directory_id)",
        ]

        for idx_sql in indexes:
            try:
                await conn.execute(text(idx_sql))
                print(f"  ✅ 索引创建成功")
            except Exception as e:
                print(f"  ⚠️  索引可能已存在: {e}")

    print("\n" + "=" * 60)
    print("✨ 数据库迁移完成!")
    print("=" * 60)
    print("\n💡 下一步: 运行 python scripts/migrate_to_directory_storage.py 来填充目录数据")


if __name__ == "__main__":
    print("\n欢迎使用数据库迁移工具\n")
    asyncio.run(migrate())
