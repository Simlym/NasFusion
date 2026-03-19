# -*- coding: utf-8 -*-
"""
历史数据修复脚本：标准化 unified_persons.known_for_department 字段

问题：不同数据来源（TMDB/豆瓣）写入的值格式不一致：
  - TMDB 来源：Acting / Directing / Writing / Production / Camera / Crew ...
  - 豆瓣来源：演员 / 导演 / 主持人 / 作者 / 制片人 / 制片管理 ...

修复目标：统一为中文标准值，例如：
  Acting → 演员
  Directing → 导演
  作者 → 编剧
  Crew → 其他
  ...

用法:
    cd backend
    python scripts/migration/fix_known_for_department.py
"""

import asyncio
import sys
import os

# 确保能导入 app 模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from sqlalchemy import select, update
from app.core.database import async_session_local
from app.models.unified_person import UnifiedPerson
from app.utils.metadata_normalization import MetadataNormalizer


async def fix_known_for_department():
    """修复 known_for_department 字段的历史数据"""
    async with async_session_local() as db:
        # 查询所有 known_for_department 不为空的人员
        stmt = select(UnifiedPerson).where(
            UnifiedPerson.known_for_department.isnot(None)
        )
        result = await db.execute(stmt)
        persons = result.scalars().all()

        total = len(persons)
        print(f"共找到 {total} 条有 known_for_department 的记录")

        # 统计各值的分布（修复前）
        before_dist = {}
        for p in persons:
            val = p.known_for_department
            before_dist[val] = before_dist.get(val, 0) + 1

        print("\n修复前分布：")
        for val, cnt in sorted(before_dist.items(), key=lambda x: -x[1]):
            print(f"  {val!r}: {cnt}")

        # 执行标准化
        changed = 0
        for person in persons:
            old_val = person.known_for_department
            new_val = MetadataNormalizer.normalize_department(old_val)
            if old_val != new_val:
                person.known_for_department = new_val
                changed += 1

        if changed > 0:
            await db.commit()
            print(f"\n已更新 {changed} 条记录")
        else:
            print("\n所有记录已是标准值，无需更新")

        # 统计各值的分布（修复后）
        stmt2 = select(UnifiedPerson).where(
            UnifiedPerson.known_for_department.isnot(None)
        )
        result2 = await db.execute(stmt2)
        persons2 = result2.scalars().all()
        after_dist = {}
        for p in persons2:
            val = p.known_for_department
            after_dist[val] = after_dist.get(val, 0) + 1

        print("\n修复后分布：")
        for val, cnt in sorted(after_dist.items(), key=lambda x: -x[1]):
            print(f"  {val!r}: {cnt}")


if __name__ == "__main__":
    asyncio.run(fix_known_for_department())
