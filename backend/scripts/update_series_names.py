# -*- coding: utf-8 -*-
"""
更新剧集季度目录的 series_name 字段
从目录路径中提取剧集名称
"""
import sys
import asyncio
from pathlib import Path

# 添加项目根目录到 Python 路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import select, update
from app.core.database import AsyncSessionLocal
from app.models import MediaDirectory
from app.constants import MEDIA_TYPE_TV


async def update_series_names():
    """更新剧集季度目录的 series_name"""
    print("开始更新剧集季度目录的 series_name...")

    async with AsyncSessionLocal() as db:
        # 查询所有剧集季度目录（有 season_number 但 series_name 为空）
        result = await db.execute(
            select(MediaDirectory).where(
                MediaDirectory.media_type == MEDIA_TYPE_TV,
                MediaDirectory.season_number.isnot(None),
                MediaDirectory.series_name.is_(None)
            )
        )
        directories = list(result.scalars().all())

        print(f"找到 {len(directories)} 个需要更新的目录")

        updated_count = 0
        for directory in directories:
            # 从目录路径提取剧集名
            # 例如: ./data/media/TV Shows/我们这一天 (2016)/Season 1
            # 提取: 我们这一天 (2016)
            path_parts = Path(directory.directory_path).parts
            if len(path_parts) >= 2:
                series_name = path_parts[-2]  # 父目录名
                directory.series_name = series_name
                updated_count += 1
                print(f"✅ ID={directory.id}: {directory.directory_name} -> {series_name}")
            else:
                print(f"⚠️  ID={directory.id}: 路径格式不符合预期: {directory.directory_path}")

        # 提交更改
        if updated_count > 0:
            await db.commit()
            print(f"\n✅ 成功更新 {updated_count} 个目录的 series_name")
        else:
            print("\n⚠️  没有需要更新的目录")


async def main():
    """主函数"""
    try:
        await update_series_names()
    except Exception as e:
        print(f"❌ 更新失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
