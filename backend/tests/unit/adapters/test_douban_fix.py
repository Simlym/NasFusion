# -*- coding: utf-8 -*-
"""
测试豆瓣适配器修复后的集数提取
"""
import asyncio
import json
from app.adapters.metadata.douban_adapter import DoubanAdapter


async def test_douban_tv_episodes():
    """测试豆瓣电视剧集数提取"""
    adapter = DoubanAdapter()

    # 测试一个已知的电视剧ID（勿扰飞升）
    douban_id = "35896172"

    print(f"\n{'='*80}")
    print(f"测试豆瓣电视剧集数提取 - ID: {douban_id}")
    print(f"{'='*80}\n")

    try:
        result = await adapter.get_tv_detail(douban_id, fetch_celebrities=False)

        if result:
            print("成功获取电视剧详情\n")
            print(json.dumps(result, ensure_ascii=False, indent=2))

            print(f"\n{'='*80}")
            print("关键字段验证:")
            print(f"{'='*80}\n")

            print(f"标题: {result.get('title')}")
            print(f"年份: {result.get('year')}")
            print(f"总集数 (number_of_episodes): {result.get('number_of_episodes')}")
            print(f"总季数 (number_of_seasons): {result.get('number_of_seasons')}")
            print(f"豆瓣评分: {result.get('rating_douban')}")

            if result.get('number_of_episodes'):
                print(f"\n成功! 豆瓣集数已提取: {result.get('number_of_episodes')} 集")
            else:
                print(f"\n警告: 集数字段仍为空")

        else:
            print("未能获取电视剧详情")

    except Exception as e:
        print(f"错误: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_douban_tv_episodes())
