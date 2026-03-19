# -*- coding: utf-8 -*-
"""
清理 media_directories 表中的 Synology @eaDir 系统目录

这些目录是 Synology NAS 自动创建的系统目录，用于存储缩略图和索引：
- @eaDir: Extended Attributes Directory (缩略图、索引元数据)
- @tmp: 临时目录
- SYNO@*: Synology 系统文件

运行方式:
    cd backend && python -m scripts.cleanup_eadir
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.core.database import async_session_local


async def cleanup_eadir():
    """清理 @eaDir 等 NAS 系统目录"""
    print("=" * 60)
    print("🧹 清理 Synology @eaDir 系统目录")
    print("=" * 60)
    
    # 需要清理的模式
    patterns = [
        '%@eaDir%',      # Synology Extended Attributes
        '%@tmp%',        # Synology 临时目录
        '%#recycle%',    # 回收站
        '%SYNO@%',       # Synology 系统文件
    ]
    
    async with async_session_local() as session:
        async with session.begin():
            total_deleted_dirs = 0
            total_deleted_files = 0
            
            for pattern in patterns:
                # 1. 统计匹配目录数量
                count_dirs_result = await session.execute(
                    text("SELECT COUNT(*) FROM media_directories WHERE directory_path LIKE :pattern"),
                    {"pattern": pattern}
                )
                count_dirs = count_dirs_result.scalar()
                
                # 2. 统计匹配文件数量
                count_files_result = await session.execute(
                    text("SELECT COUNT(*) FROM media_files WHERE file_path LIKE :pattern"),
                    {"pattern": pattern}
                )
                count_files = count_files_result.scalar()
                
                if count_dirs > 0 or count_files > 0:
                    print(f"\n📁 模式: {pattern}")
                    print(f"   - 匹配目录: {count_dirs} 条")
                    print(f"   - 匹配文件: {count_files} 条")
                    
                    # 3. 删除匹配的文件记录
                    if count_files > 0:
                        await session.execute(
                            text("DELETE FROM media_files WHERE file_path LIKE :pattern"),
                            {"pattern": pattern}
                        )
                        print(f"   ✅ 已删除 {count_files} 条文件记录")
                        total_deleted_files += count_files
                    
                    # 4. 删除匹配的目录记录
                    if count_dirs > 0:
                        await session.execute(
                            text("DELETE FROM media_directories WHERE directory_path LIKE :pattern"),
                            {"pattern": pattern}
                        )
                        print(f"   ✅ 已删除 {count_dirs} 条目录记录")
                        total_deleted_dirs += count_dirs
            
            print("\n" + "=" * 60)
            print(f"📊 清理完成！")
            print(f"   - 删除目录记录: {total_deleted_dirs} 条")
            print(f"   - 删除文件记录: {total_deleted_files} 条")
            print("=" * 60)


if __name__ == "__main__":
    asyncio.run(cleanup_eadir())
