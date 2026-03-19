# -*- coding: utf-8 -*-
"""
批量更新电视剧集数信息

从豆瓣API重新获取电视剧元数据，更新 number_of_episodes 字段
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_local
from app.models.unified_tv_series import UnifiedTVSeries
from app.adapters.metadata.douban_adapter import DoubanAdapter


async def update_tv_episodes():
    """批量更新电视剧集数"""
    print("="*80)
    print("批量更新电视剧集数信息")
    print("="*80)

    adapter = DoubanAdapter()
    updated_count = 0
    failed_count = 0
    skipped_count = 0

    async with async_session_local() as session:
        # 查询所有有豆瓣ID但缺少集数信息的电视剧
        stmt = select(UnifiedTVSeries).where(
            UnifiedTVSeries.douban_id.isnot(None),
            UnifiedTVSeries.number_of_episodes.is_(None)
        )
        result = await session.execute(stmt)
        tv_series_list = result.scalars().all()

        total = len(tv_series_list)
        print(f"\n找到 {total} 条需要更新的电视剧记录\n")

        for idx, tv in enumerate(tv_series_list, 1):
            print(f"[{idx}/{total}] 处理: {tv.title} (豆瓣ID: {tv.douban_id})")

            try:
                # 从豆瓣获取最新详情
                detail = await adapter.get_tv_detail(tv.douban_id, fetch_celebrities=False)

                if detail and detail.get("number_of_episodes"):
                    # 更新集数
                    tv.number_of_episodes = detail["number_of_episodes"]

                    # 如果有其他可更新的字段也一并更新
                    if detail.get("rating_douban") and not tv.rating_douban:
                        tv.rating_douban = detail["rating_douban"]
                    if detail.get("votes_count") and not tv.votes_count:
                        tv.votes_count = detail["votes_count"]

                    print(f"  [OK] 更新成功: 集数={tv.number_of_episodes}")
                    updated_count += 1
                else:
                    print(f"  [SKIP] 跳过: 豆瓣API未返回集数信息")
                    skipped_count += 1

                # 避免请求过快
                await asyncio.sleep(1)

            except Exception as e:
                print(f"  [FAIL] 失败: {str(e)}")
                failed_count += 1
                continue

        # 提交更改
        if updated_count > 0:
            await session.commit()
            print(f"\n[OK] 已提交 {updated_count} 条更新到数据库")

    print(f"\n{'='*80}")
    print(f"更新完成!")
    print(f"{'='*80}")
    print(f"成功更新: {updated_count}")
    print(f"跳过: {skipped_count}")
    print(f"失败: {failed_count}")
    print(f"总计: {total}")


if __name__ == "__main__":
    asyncio.run(update_tv_episodes())
