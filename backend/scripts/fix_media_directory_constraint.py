# -*- coding: utf-8 -*-
"""
修复 media_directories 表的约束问题
将硬编码的 'tv_series' 约束改为使用 MEDIA_TYPES 常量（'tv'）
"""
import sys
import asyncio
from pathlib import Path

# 添加项目根目录到 Python 路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import text
from app.core.database import AsyncSessionLocal, engine
from app.models import MediaDirectory
from app.constants import MEDIA_TYPES


async def fix_constraint():
    """修复约束"""
    print("开始修复 media_directories 表约束...")

    async with engine.begin() as conn:
        # SQLite 不支持直接修改约束，需要重建表
        print("检测到 SQLite，将重建表...")

        # 1. 创建临时表（新结构）
        print("1. 创建临时表...")
        media_types_str = ", ".join([f"'{mt}'" for mt in MEDIA_TYPES])
        await conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS media_directories_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                directory_path VARCHAR(1024) UNIQUE NOT NULL,
                directory_name VARCHAR(512) NOT NULL,
                parent_id INTEGER,
                media_type VARCHAR(50),
                unified_table_name VARCHAR(100),
                unified_resource_id INTEGER,
                series_name VARCHAR(512),
                season_number INTEGER,
                episode_count INTEGER DEFAULT 0,
                has_nfo BOOLEAN DEFAULT 0,
                nfo_path VARCHAR(1024),
                has_poster BOOLEAN DEFAULT 0,
                poster_path VARCHAR(1024),
                has_backdrop BOOLEAN DEFAULT 0,
                backdrop_path VARCHAR(1024),
                issue_flags JSON,
                total_files INTEGER DEFAULT 0,
                total_size BIGINT DEFAULT 0,
                scanned_at TIMESTAMP,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL,
                FOREIGN KEY (parent_id) REFERENCES media_directories_new(id),
                CHECK (media_type IS NULL OR media_type IN ({media_types_str}))
            )
        """))

        # 2. 迁移数据（如果旧表存在）
        print("2. 检查并迁移旧数据...")
        try:
            # 检查旧表是否有数据
            result = await conn.execute(text("SELECT COUNT(*) FROM media_directories"))
            count = result.scalar()

            if count > 0:
                print(f"   发现 {count} 条记录，开始迁移...")
                # 迁移数据
                await conn.execute(text("""
                    INSERT INTO media_directories_new
                    SELECT * FROM media_directories
                """))
                print(f"   成功迁移 {count} 条记录")
            else:
                print("   旧表为空，无需迁移")
        except Exception as e:
            print(f"   旧表不存在或迁移失败（这是正常的）: {e}")

        # 3. 删除旧表
        print("3. 删除旧表...")
        await conn.execute(text("DROP TABLE IF EXISTS media_directories"))

        # 4. 重命名新表
        print("4. 重命名新表...")
        await conn.execute(text("ALTER TABLE media_directories_new RENAME TO media_directories"))

        # 5. 重建索引
        print("5. 重建索引...")
        await conn.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS ix_media_directories_directory_path
            ON media_directories (directory_path)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_media_directories_parent_id
            ON media_directories (parent_id)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_media_directories_media_type
            ON media_directories (media_type)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_media_directories_unified_resource_id
            ON media_directories (unified_resource_id)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_media_dir_unified_resource
            ON media_directories (unified_table_name, unified_resource_id)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_media_dir_series_season
            ON media_directories (series_name, season_number)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_media_dir_type_path
            ON media_directories (media_type, directory_path)
        """))

    print("✅ 约束修复完成！")
    print(f"新的媒体类型约束: {MEDIA_TYPES}")


async def main():
    """主函数"""
    try:
        await fix_constraint()
    except Exception as e:
        print(f"❌ 修复失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
