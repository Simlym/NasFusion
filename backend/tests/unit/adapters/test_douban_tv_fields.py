# -*- coding: utf-8 -*-
"""
测试豆瓣TV API返回的字段，查看是否包含季数和集数信息
"""
import asyncio
import json
from app.adapters.metadata.douban_api import DoubanApi


async def test_douban_tv_fields():
    """测试豆瓣电视剧API返回的所有字段"""
    api = DoubanApi()

    # 测试一个已知的电视剧ID（勿扰飞升）
    douban_id = "35896172"

    print(f"\n{'='*80}")
    print(f"测试豆瓣电视剧详情 API - ID: {douban_id}")
    print(f"{'='*80}\n")

    try:
        result = await api.tv_detail(douban_id)

        if result:
            print("成功获取电视剧详情\n")
            print(json.dumps(result, ensure_ascii=False, indent=2))

            print(f"\n{'='*80}")
            print("关键字段检查:")
            print(f"{'='*80}\n")

            # 检查可能的季数/集数字段
            fields_to_check = [
                "number_of_seasons",
                "number_of_episodes",
                "seasons",
                "episodes",
                "episodes_count",
                "total_episodes",
                "season_count",
                "episodes_info",
                "episodes_num",
                "season_num",
            ]

            for field in fields_to_check:
                value = result.get(field)
                status = "存在" if value is not None else "不存在"
                print(f"{status} - {field}: {value}")

            print(f"\n{'='*80}")
            print("所有字段列表:")
            print(f"{'='*80}\n")
            for key in sorted(result.keys()):
                print(f"  - {key}")

        else:
            print("未能获取电视剧详情")

    except Exception as e:
        print(f"错误: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_douban_tv_fields())
