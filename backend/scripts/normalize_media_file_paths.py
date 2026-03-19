# -*- coding: utf-8 -*-
"""
规范化 media_files 表中的路径格式

将现有记录的 directory 字段从反斜杠格式转换为正斜杠格式，并添加 ./ 前缀

使用方法:
    cd backend
    python scripts/normalize_media_file_paths.py
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
from sqlalchemy import select
from app.models.media_file import MediaFile


def normalize_path(path: str) -> str:
    """
    规范化路径为统一格式
    - 统一使用正斜杠
    - 添加 ./ 前缀（如果是相对路径）
    """
    # 转换为 Path 对象
    p = Path(path)

    # 转换为 POSIX 风格路径（正斜杠）
    normalized = p.as_posix()

    # 如果是相对路径且不以 ./ 开头，添加 ./
    if not p.is_absolute() and not normalized.startswith('./'):
        normalized = './' + normalized

    return normalized


async def migrate():
    """执行路径规范化"""
    print("=" * 60)
    print("开始规范化媒体文件路径")
    print("=" * 60)

    async with async_session_local() as db:
        # 获取所有媒体文件记录
        result = await db.execute(select(MediaFile))
        files = list(result.scalars().all())

        print(f"\n找到 {len(files)} 个媒体文件记录")

        updated_count = 0
        for file in files:
            old_directory = file.directory
            new_directory = normalize_path(old_directory)

            if old_directory != new_directory:
                print(f"  更新: {old_directory} → {new_directory}")
                file.directory = new_directory
                updated_count += 1

        if updated_count > 0:
            await db.commit()
            print(f"\n✅ 成功更新 {updated_count} 个文件记录的路径")
        else:
            print(f"\n✅ 所有路径已经是规范格式，无需更新")

    print("=" * 60)
    print("路径规范化完成！")
    print("=" * 60)


if __name__ == "__main__":
    print("\n欢迎使用媒体文件路径规范化工具\n")
    asyncio.run(migrate())
