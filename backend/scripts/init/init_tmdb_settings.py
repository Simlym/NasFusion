#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
初始化TMDB配置到系统设置

使用方法：
    python scripts/init_tmdb_settings.py --api-key YOUR_TMDB_API_KEY

获取TMDB API Key:
    1. 访问 https://www.themoviedb.org/
    2. 注册账号并登录
    3. 访问 https://www.themoviedb.org/settings/api
    4. 申请API密钥（免费）
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select
from app.core.database import async_session_local
from app.models.system_setting import SystemSetting


async def init_tmdb_settings(api_key: str, proxy_url: str = None):
    """
    初始化TMDB配置

    Args:
        api_key: TMDB API Key
        proxy_url: 代理地址（可选），如 "http://127.0.0.1:7890"
    """
    async with async_session_local() as db:
        print("🔧 初始化TMDB配置...")

        # 1. 添加TMDB API Key
        query = select(SystemSetting).where(
            SystemSetting.category == "metadata",
            SystemSetting.key == "tmdb_api_key",
        )
        result = await db.execute(query)
        existing = result.scalar_one_or_none()

        if existing:
            existing.value = api_key
            print(f"✓ 更新TMDB API Key: {api_key[:10]}...{api_key[-4:]}")
        else:
            setting = SystemSetting(
                category="metadata",
                key="tmdb_api_key",
                value=api_key,
                description="TMDB API密钥，用于电影元数据识别",
            )
            db.add(setting)
            print(f"✓ 添加TMDB API Key: {api_key[:10]}...{api_key[-4:]}")

        # 2. 添加代理配置（如果提供）
        if proxy_url:
            proxy_query = select(SystemSetting).where(
                SystemSetting.category == "metadata",
                SystemSetting.key == "tmdb_proxy",
            )
            proxy_result = await db.execute(proxy_query)
            proxy_existing = proxy_result.scalar_one_or_none()

            if proxy_existing:
                proxy_existing.value = proxy_url
                print(f"✓ 更新TMDB代理: {proxy_url}")
            else:
                proxy_setting = SystemSetting(
                    category="metadata",
                    key="tmdb_proxy",
                    value=proxy_url,
                    description="TMDB API代理地址（可选）",
                )
                db.add(proxy_setting)
                print(f"✓ 添加TMDB代理: {proxy_url}")

        await db.commit()
        print("\n✅ TMDB配置初始化完成！")
        print("\n现在您可以：")
        print("  1. 使用IMDB ID识别资源（无需豆瓣ID）")
        print("  2. 使用标题+年份搜索识别（备选方案）")
        print("  3. 提高识别成功率\n")


async def show_current_settings():
    """显示当前TMDB配置"""
    async with async_session_local() as db:
        print("\n📋 当前TMDB配置：")
        print("-" * 50)

        # 查询API Key
        query = select(SystemSetting).where(
            SystemSetting.category == "metadata",
            SystemSetting.key == "tmdb_api_key",
        )
        result = await db.execute(query)
        api_key_setting = result.scalar_one_or_none()

        if api_key_setting:
            api_key = api_key_setting.value
            print(f"TMDB API Key: {api_key[:10]}...{api_key[-4:]}")
        else:
            print("TMDB API Key: ❌ 未配置")

        # 查询代理
        proxy_query = select(SystemSetting).where(
            SystemSetting.category == "metadata",
            SystemSetting.key == "tmdb_proxy",
        )
        proxy_result = await db.execute(proxy_query)
        proxy_setting = proxy_result.scalar_one_or_none()

        if proxy_setting:
            print(f"TMDB代理: {proxy_setting.value}")
        else:
            print("TMDB代理: 未配置（直连）")

        print("-" * 50 + "\n")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="初始化TMDB配置")
    parser.add_argument("--api-key", type=str, help="TMDB API Key")
    parser.add_argument("--proxy", type=str, help="代理地址，如 http://127.0.0.1:7890")
    parser.add_argument("--show", action="store_true", help="显示当前配置")

    args = parser.parse_args()

    if args.show:
        asyncio.run(show_current_settings())
        return

    if not args.api_key:
        print("❌ 错误：请提供 --api-key 参数")
        print("\n使用示例：")
        print("  python scripts/init_tmdb_settings.py --api-key YOUR_API_KEY")
        print("  python scripts/init_tmdb_settings.py --api-key YOUR_API_KEY --proxy http://127.0.0.1:7890")
        print("\n获取TMDB API Key:")
        print("  1. 访问 https://www.themoviedb.org/")
        print("  2. 注册账号并登录")
        print("  3. 访问 https://www.themoviedb.org/settings/api")
        print("  4. 申请API密钥（免费）\n")
        sys.exit(1)

    asyncio.run(init_tmdb_settings(args.api_key, args.proxy))


if __name__ == "__main__":
    main()
