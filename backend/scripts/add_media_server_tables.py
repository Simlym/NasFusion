# -*- coding: utf-8 -*-
"""
添加媒体服务器集成相关表的数据库迁移脚本

支持Jellyfin/Emby/Plex集成：
- media_server_configs: 媒体服务器配置（通用）
- viewing_history: 观看历史同步
- media_server_library_stats: 媒体库统计缓存

使用方法:
    cd backend
    python scripts/add_media_server_tables.py
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
    print("开始执行数据库迁移：添加媒体服务器集成支持")
    print("=" * 60)

    async with engine.begin() as conn:
        # 1. 创建 media_server_configs 表
        print("\n📦 步骤 1/4: 创建 media_server_configs 表...")

        create_configs_table_sql = """
        CREATE TABLE IF NOT EXISTS media_server_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type VARCHAR(50) NOT NULL,
            name VARCHAR(100) NOT NULL,
            is_default BOOLEAN NOT NULL DEFAULT 0,
            host VARCHAR(255) NOT NULL,
            port INTEGER NOT NULL,
            use_ssl BOOLEAN NOT NULL DEFAULT 0,
            api_key TEXT,
            token TEXT,
            username VARCHAR(255),
            password TEXT,
            server_config TEXT,
            auto_refresh_library BOOLEAN NOT NULL DEFAULT 1,
            sync_watch_history BOOLEAN NOT NULL DEFAULT 1,
            watch_history_sync_interval INTEGER NOT NULL DEFAULT 60,
            library_path_mappings TEXT,
            status VARCHAR(50) NOT NULL DEFAULT 'offline',
            last_check_at TIMESTAMP WITH TIME ZONE,
            last_sync_at TIMESTAMP WITH TIME ZONE,
            last_error TEXT,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            CHECK (type IN ('jellyfin', 'emby', 'plex')),
            CHECK (status IN ('online', 'offline', 'error'))
        )
        """

        try:
            await conn.execute(text(create_configs_table_sql))
            print("  ✅ media_server_configs 表创建成功")
        except Exception as e:
            print(f"  ⚠️  表可能已存在: {e}")

        # 2. 创建 media_watch_histories 表
        print("\n📦 步骤 2/4: 创建 media_watch_histories 表...")

        create_history_table_sql = """
        CREATE TABLE IF NOT EXISTS media_server_watch_histories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            media_server_config_id INTEGER NOT NULL,
            server_type VARCHAR(50) NOT NULL,
            server_item_id VARCHAR(100) NOT NULL,
            server_user_id VARCHAR(100) NOT NULL,
            media_type VARCHAR(20) NOT NULL,
            title VARCHAR(500) NOT NULL,
            year INTEGER,
            season_number INTEGER,
            episode_number INTEGER,
            episode_title VARCHAR(500),
            play_count INTEGER NOT NULL DEFAULT 1,
            last_played_at TIMESTAMP WITH TIME ZONE NOT NULL,
            play_duration_seconds INTEGER,
            runtime_seconds INTEGER,
            is_completed BOOLEAN NOT NULL DEFAULT 0,
            media_file_id INTEGER,
            unified_table_name VARCHAR(50),
            unified_resource_id INTEGER,
            server_data TEXT,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (media_server_config_id) REFERENCES media_server_configs(id) ON DELETE CASCADE,
            FOREIGN KEY (media_file_id) REFERENCES media_files(id) ON DELETE SET NULL
        )
        """

        try:
            await conn.execute(text(create_history_table_sql))
            print("  ✅ media_server_watch_histories 表创建成功")
        except Exception as e:
            print(f"  ⚠️  表可能已存在: {e}")

        # 3. 创建 media_server_library_stats 表
        print("\n📦 步骤 3/4: 创建 media_server_library_stats 表...")

        create_stats_table_sql = """
        CREATE TABLE IF NOT EXISTS media_server_library_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            media_server_config_id INTEGER NOT NULL,
            stats_data TEXT NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (media_server_config_id) REFERENCES media_server_configs(id) ON DELETE CASCADE
        )
        """

        try:
            await conn.execute(text(create_stats_table_sql))
            print("  ✅ media_server_library_stats 表创建成功")
        except Exception as e:
            print(f"  ⚠️  表可能已存在: {e}")

        # 4. 创建索引
        print("\n🔧 步骤 4/4: 创建索引...")

        indexes = [
            # media_server_configs 索引
            "CREATE INDEX IF NOT EXISTS idx_media_server_configs_user_id ON media_server_configs(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_media_server_configs_type ON media_server_configs(type)",
            "CREATE INDEX IF NOT EXISTS idx_media_server_configs_user_type ON media_server_configs(user_id, type)",
            "CREATE INDEX IF NOT EXISTS idx_media_server_configs_status ON media_server_configs(status)",

            # media_server_watch_histories 索引
            "CREATE INDEX IF NOT EXISTS idx_media_server_watch_histories_user_id ON media_server_watch_histories(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_media_server_watch_histories_media_server_config_id ON media_server_watch_histories(media_server_config_id)",
            "CREATE INDEX IF NOT EXISTS idx_media_server_watch_histories_server_item ON media_server_watch_histories(server_item_id, user_id, media_server_config_id)",
            "CREATE INDEX IF NOT EXISTS idx_media_server_watch_histories_media_type ON media_server_watch_histories(media_type)",
            "CREATE INDEX IF NOT EXISTS idx_media_server_watch_histories_unified ON media_server_watch_histories(unified_table_name, unified_resource_id)",
            "CREATE INDEX IF NOT EXISTS idx_media_server_watch_histories_server_type ON media_server_watch_histories(server_type)",
            "CREATE INDEX IF NOT EXISTS idx_media_server_watch_histories_media_file_id ON media_server_watch_histories(media_file_id)",

            # media_server_library_stats 索引
            "CREATE INDEX IF NOT EXISTS idx_media_server_library_stats_config_id ON media_server_library_stats(media_server_config_id)",
        ]

        success_count = 0
        for idx_sql in indexes:
            try:
                await conn.execute(text(idx_sql))
                success_count += 1
            except Exception as e:
                print(f"  ⚠️  索引可能已存在: {e}")

        print(f"  ✅ 成功创建 {success_count}/{len(indexes)} 个索引")

    print("\n" + "=" * 60)
    print("✨ 数据库迁移完成!")
    print("=" * 60)
    print("\n💡 下一步:")
    print("  1. 在前端添加媒体服务器配置页面")
    print("  2. 配置你的 Jellyfin/Emby/Plex 服务器")
    print("  3. 开始同步观看历史和媒体库信息")
    print("\n📚 支持的服务器类型:")
    print("  - Jellyfin (已实现)")
    print("  - Emby (预留)")
    print("  - Plex (预留)")


if __name__ == "__main__":
    print("\n欢迎使用媒体服务器集成数据库迁移工具\n")
    asyncio.run(migrate())
