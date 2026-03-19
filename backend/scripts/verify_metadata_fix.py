# -*- coding: utf-8 -*-
"""
验证元数据修复效果

使用方法:
    python scripts/verify_metadata_fix.py
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import select
from app.core.database import async_session_local
from app.models.unified_movie import UnifiedMovie
from app.models.unified_tv_series import UnifiedTVSeries


async def verify_movies():
    """验证电影数据"""
    print("检查电影数据...")
    print("-" * 60)

    async with async_session_local() as db:
        # 查询前10条记录
        query = select(UnifiedMovie).limit(10)
        result = await db.execute(query)
        movies = result.scalars().all()

        for movie in movies:
            print(f"\nID: {movie.id} - {movie.title}")
            print(f"  类型: {movie.genres}")
            print(f"  语言: {movie.languages}")
            print(f"  国家: {movie.countries}")

        # 统计有问题的记录
        query_all = select(UnifiedMovie)
        result_all = await db.execute(query_all)
        all_movies = result_all.scalars().all()

        problematic = []
        for movie in all_movies:
            has_issue = False
            issues = []

            # 检查 genres 是否为列表
            if movie.genres and not isinstance(movie.genres, list):
                has_issue = True
                issues.append("genres 不是列表")

            # 检查 languages 是否为列表
            if movie.languages and not isinstance(movie.languages, list):
                has_issue = True
                issues.append("languages 不是列表")

            # 检查 countries 是否为列表
            if movie.countries and not isinstance(movie.countries, list):
                has_issue = True
                issues.append("countries 不是列表")

            if has_issue:
                problematic.append({
                    "id": movie.id,
                    "title": movie.title,
                    "issues": issues
                })

        print(f"\n电影统计:")
        print(f"  总数: {len(all_movies)}")
        print(f"  有问题: {len(problematic)}")

        if problematic:
            print("\n有问题的记录:")
            for item in problematic[:5]:  # 只显示前5条
                print(f"  - ID {item['id']}: {item['title']} - {', '.join(item['issues'])}")


async def verify_tv_series():
    """验证电视剧数据"""
    print("\n" + "=" * 60)
    print("检查电视剧数据...")
    print("-" * 60)

    async with async_session_local() as db:
        # 查询前10条记录
        query = select(UnifiedTVSeries).limit(10)
        result = await db.execute(query)
        tv_series_list = result.scalars().all()

        for tv in tv_series_list:
            print(f"\nID: {tv.id} - {tv.title}")
            print(f"  类型: {tv.genres}")
            print(f"  语言: {tv.languages}")
            print(f"  国家: {tv.countries}")

        # 统计有问题的记录
        query_all = select(UnifiedTVSeries)
        result_all = await db.execute(query_all)
        all_tv = result_all.scalars().all()

        problematic = []
        for tv in all_tv:
            has_issue = False
            issues = []

            # 检查 genres 是否为列表
            if tv.genres and not isinstance(tv.genres, list):
                has_issue = True
                issues.append("genres 不是列表")

            # 检查 languages 是否为列表
            if tv.languages and not isinstance(tv.languages, list):
                has_issue = True
                issues.append("languages 不是列表")

            # 检查 countries 是否为列表
            if tv.countries and not isinstance(tv.countries, list):
                has_issue = True
                issues.append("countries 不是列表")

            if has_issue:
                problematic.append({
                    "id": tv.id,
                    "title": tv.title,
                    "issues": issues
                })

        print(f"\n电视剧统计:")
        print(f"  总数: {len(all_tv)}")
        print(f"  有问题: {len(problematic)}")

        if problematic:
            print("\n有问题的记录:")
            for item in problematic[:5]:  # 只显示前5条
                print(f"  - ID {item['id']}: {item['title']} - {', '.join(item['issues'])}")


async def main():
    """主函数"""
    print("=" * 60)
    print("元数据修复验证工具")
    print("=" * 60)

    await verify_movies()
    await verify_tv_series()

    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
