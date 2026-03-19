# -*- coding: utf-8 -*-
"""
一次性脚本：修复已有映射但识别状态为null的PT资源

问题说明：
早期版本的批量识别任务在跳过已有映射的资源时，没有更新识别状态，
导致部分资源虽然有映射关系，但 identification_status 仍为 null。

此脚本会：
1. 查询所有有映射但状态不是 'identified' 的PT资源
2. 批量更新它们的状态为 'identified'
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session_local
from app.models.pt_resource import PTResource
from app.models.resource_mapping import ResourceMapping
from app.constants.resource_identification import IDENTIFICATION_STATUS_IDENTIFIED


async def fix_identification_status():
    """修复已映射但状态为null的PT资源"""
    async_session_local = get_async_session_local()
    async with async_session_local() as db:
        try:
            # 1. 查询所有有映射的PT资源ID
            mapping_query = select(ResourceMapping.pt_resource_id).distinct()
            mapping_result = await db.execute(mapping_query)
            mapped_pt_resource_ids = [row[0] for row in mapping_result.all()]

            print(f"📊 找到 {len(mapped_pt_resource_ids)} 个已有映射的PT资源")

            if not mapped_pt_resource_ids:
                print("✅ 没有需要修复的数据")
                return

            # 2. 查询这些资源中状态不是 'identified' 的资源
            query = select(PTResource).where(
                PTResource.id.in_(mapped_pt_resource_ids),
                PTResource.identification_status != IDENTIFICATION_STATUS_IDENTIFIED
            )
            result = await db.execute(query)
            resources_to_fix = result.scalars().all()

            print(f"⚠️  发现 {len(resources_to_fix)} 个资源需要修复状态")

            if not resources_to_fix:
                print("✅ 所有已映射资源的状态都已正确")
                return

            # 3. 显示部分待修复资源示例
            print("\n📋 待修复资源示例（前5个）：")
            for resource in resources_to_fix[:5]:
                print(f"  - ID: {resource.id}, 标题: {resource.title}, "
                      f"当前状态: {resource.identification_status}")

            # 4. 批量更新状态
            resource_ids_to_fix = [r.id for r in resources_to_fix]
            update_stmt = (
                update(PTResource)
                .where(PTResource.id.in_(resource_ids_to_fix))
                .values(identification_status=IDENTIFICATION_STATUS_IDENTIFIED)
            )

            await db.execute(update_stmt)
            await db.commit()

            print(f"\n✅ 成功修复 {len(resources_to_fix)} 个PT资源的识别状态")
            print(f"   状态已更新为: {IDENTIFICATION_STATUS_IDENTIFIED}")

        except Exception as e:
            print(f"\n❌ 修复失败: {str(e)}")
            await db.rollback()
            raise


async def main():
    """主函数"""
    print("=" * 60)
    print("修复PT资源识别状态")
    print("=" * 60)
    print()

    await fix_identification_status()

    print()
    print("=" * 60)
    print("修复完成！")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
