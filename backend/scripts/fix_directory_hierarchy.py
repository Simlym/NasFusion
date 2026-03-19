# -*- coding: utf-8 -*-
"""
修复媒体目录的父子关系
为剧集季度目录创建父目录，建立正确的层级结构
"""
import sys
import asyncio
from pathlib import Path
from collections import defaultdict

# 添加项目根目录到 Python 路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models import MediaDirectory
from app.constants import MEDIA_TYPE_TV
from app.utils.timezone import now


async def fix_directory_hierarchy():
    """修复目录层级结构"""
    print("开始修复媒体目录层级结构...")

    async with AsyncSessionLocal() as db:
        # 1. 查找所有剧集季度目录（parent_id=NULL 且有 season_number）
        result = await db.execute(
            select(MediaDirectory).where(
                MediaDirectory.media_type == MEDIA_TYPE_TV,
                MediaDirectory.season_number.isnot(None),
                MediaDirectory.parent_id.is_(None)
            )
        )
        season_dirs = list(result.scalars().all())

        print(f"找到 {len(season_dirs)} 个需要修复的季度目录")

        # 2. 按父目录路径分组
        parent_groups = defaultdict(list)
        for season_dir in season_dirs:
            parent_path = str(Path(season_dir.directory_path).parent)
            parent_groups[parent_path].append(season_dir)

        print(f"需要创建 {len(parent_groups)} 个父目录")

        # 3. 为每个剧集创建父目录记录
        created_parents = {}
        for parent_path, children in parent_groups.items():
            # 检查父目录是否已存在
            existing_result = await db.execute(
                select(MediaDirectory).where(
                    MediaDirectory.directory_path == parent_path
                )
            )
            parent_dir = existing_result.scalar_one_or_none()

            if not parent_dir:
                # 创建父目录记录
                parent_name = Path(parent_path).name

                # 计算统计信息
                total_files = sum(child.total_files for child in children)
                total_size = sum(child.total_size for child in children)

                # 检查父目录的元数据文件
                from app.services.mediafile.media_directory_service import MediaDirectoryService
                has_nfo, nfo_path = await MediaDirectoryService._check_metadata_file(
                    parent_path, ".nfo",
                    check_parent=False,
                    is_season_dir=False
                )
                has_poster, poster_path = await MediaDirectoryService._check_metadata_file(
                    parent_path,
                    ["-poster.jpg", "-poster.png", "poster.jpg", "poster.png"],
                    check_parent=False,
                    is_season_dir=False
                )
                has_backdrop, backdrop_path = await MediaDirectoryService._check_metadata_file(
                    parent_path,
                    ["-fanart.jpg", "-fanart.png", "fanart.jpg", "fanart.png", "backdrop.jpg"],
                    check_parent=False,
                    is_season_dir=False
                )

                parent_dir = MediaDirectory(
                    directory_path=parent_path,
                    directory_name=parent_name,
                    parent_id=None,
                    media_type=MEDIA_TYPE_TV,
                    series_name=parent_name,
                    season_number=None,
                    episode_count=0,
                    total_files=total_files,
                    total_size=total_size,
                    has_nfo=has_nfo,
                    nfo_path=nfo_path,
                    has_poster=has_poster,
                    poster_path=poster_path,
                    has_backdrop=has_backdrop,
                    backdrop_path=backdrop_path,
                    scanned_at=now()
                )
                db.add(parent_dir)
                await db.flush()  # 获取 parent_dir.id

                print(f"✅ 创建父目录: {parent_name} (ID={parent_dir.id})")
                created_parents[parent_path] = parent_dir
            else:
                print(f"⚠️  父目录已存在: {parent_dir.directory_name} (ID={parent_dir.id})")
                created_parents[parent_path] = parent_dir

        # 4. 更新季度目录的 parent_id
        updated_count = 0
        for parent_path, children in parent_groups.items():
            parent_dir = created_parents[parent_path]
            for child in children:
                child.parent_id = parent_dir.id
                updated_count += 1
                print(f"   └─ 关联季度目录: {child.directory_name} → 父目录ID={parent_dir.id}")

        # 5. 提交更改
        await db.commit()

        print(f"\n✅ 修复完成！")
        print(f"   创建父目录: {len(created_parents)} 个")
        print(f"   更新季度目录: {updated_count} 个")


async def verify_hierarchy():
    """验证修复结果"""
    print("\n验证目录层级结构...")

    async with AsyncSessionLocal() as db:
        # 查询所有剧集目录
        result = await db.execute(
            select(MediaDirectory)
            .where(MediaDirectory.media_type == MEDIA_TYPE_TV)
            .order_by(MediaDirectory.directory_path)
        )
        directories = list(result.scalars().all())

        # 按层级分组
        parents = [d for d in directories if d.parent_id is None]
        children = [d for d in directories if d.parent_id is not None]

        print(f"\n层级结构统计:")
        print(f"  父目录（剧集根目录）: {len(parents)} 个")
        print(f"  子目录（季度目录）: {len(children)} 个")

        print(f"\n示例层级结构（前3个剧集）:")
        for parent in parents[:3]:
            print(f"  📁 {parent.directory_name} (ID={parent.id}, parent_id={parent.parent_id})")
            parent_children = [c for c in children if c.parent_id == parent.id]
            for child in parent_children:
                print(f"     └─ {child.directory_name} (ID={child.id}, season={child.season_number})")


async def main():
    """主函数"""
    try:
        await fix_directory_hierarchy()
        await verify_hierarchy()
    except Exception as e:
        print(f"\n❌ 修复失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
