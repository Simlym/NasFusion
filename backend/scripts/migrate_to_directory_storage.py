# -*- coding: utf-8 -*-
"""
从现有media_files表构建media_directories表的迁移脚本

使用方法:
    cd backend
    python scripts/migrate_to_directory_storage.py
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

from app.core.database import async_session_local
from app.services.mediafile.media_directory_service import MediaDirectoryService


async def migrate():
    """执行迁移"""
    print("=" * 60)
    print("开始执行媒体目录迁移")
    print("=" * 60)

    async with async_session_local() as db:
        # 扫描所有媒体库目录
        base_dirs = [
            "./data/media",  # 主媒体库
            # 可以添加更多基础目录
        ]

        total_created = 0
        total_updated = 0

        for base_dir in base_dirs:
            print(f"\n📂 开始同步目录: {base_dir}")
            print("-" * 60)

            try:
                result = await MediaDirectoryService.sync_from_files(db, base_dir)
                created = result['created']
                updated = result['updated']

                total_created += created
                total_updated += updated

                print(f"  ✅ 新建: {created} 个目录")
                print(f"  ✅ 更新: {updated} 个目录")

            except Exception as e:
                print(f"  ❌ 同步失败: {e}")
                continue

        print("\n" + "=" * 60)
        print(f"目录树同步完成!")
        print(f"  总计新建: {total_created} 个目录")
        print(f"  总计更新: {total_updated} 个目录")
        print("=" * 60)

        # 检测问题
        print("\n🔍 开始检测问题...")
        print("-" * 60)

        try:
            issues = await MediaDirectoryService.detect_issues(db)
            total_issues = sum(issues.values())

            print(f"  问题检测完成:")
            for issue_type, count in issues.items():
                if count > 0:
                    print(f"    - {issue_type}: {count} 个")

            print(f"  ⚠️  总计发现 {total_issues} 个问题")

        except Exception as e:
            print(f"  ❌ 问题检测失败: {e}")

        print("\n" + "=" * 60)
        print("✨ 迁移完成!")
        print("=" * 60)


if __name__ == "__main__":
    print("\n欢迎使用媒体目录迁移工具\n")
    asyncio.run(migrate())
