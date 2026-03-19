# -*- coding: utf-8 -*-
"""
MTeam API 认证调试脚本

用途：
1. 检查数据库中存储的 MTeam 站点配置
2. 测试 API key 解密
3. 测试 API 请求
4. 输出详细的调试信息

使用方法：
    python scripts/debug_mteam_auth.py
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_local
from app.models.pt_site import PTSite
from app.utils.encryption import encryption_util


async def debug_mteam_auth():
    """调试 MTeam 认证"""
    async with async_session_local() as db:
        try:
            # 获取 MTeam 站点
            result = await db.execute(
                select(PTSite).where(PTSite.type == "mteam")
            )
            site = result.scalar_one_or_none()

            if not site:
                print("❌ 没有找到 MTeam 站点配置")
                return

            print("\n" + "=" * 60)
            print("🔍 MTeam 站点配置信息")
            print("=" * 60)
            print(f"站点名称: {site.name}")
            print(f"站点类型: {site.type}")
            print(f"域名: {site.domain}")
            print(f"基础URL: {site.base_url}")
            print(f"认证类型: {site.auth_type}")
            print(f"状态: {site.status}")
            print(f"代理配置: {site.proxy_config}")
            print(f"请求间隔: {site.request_interval}")

            print("\n" + "=" * 60)
            print("🔐 认证信息检查")
            print("=" * 60)

            # 检查加密字段
            if site.auth_passkey:
                print(f"✅ auth_passkey 已设置（加密后长度: {len(site.auth_passkey)} 字符）")
                print(f"   加密后前20字符: {site.auth_passkey[:20]}...")

                # 尝试解密
                try:
                    decrypted_key = encryption_util.decrypt(site.auth_passkey)
                    if decrypted_key:
                        print(f"✅ 解密成功！")
                        print(f"   解密后长度: {len(decrypted_key)} 字符")
                        print(f"   API Key 前10字符: {decrypted_key[:10]}...")
                        print(f"   API Key 后10字符: ...{decrypted_key[-10:]}")

                        # 验证 API Key 格式（MTeam 的 API key 通常是32位）
                        if len(decrypted_key) == 32:
                            print("   ✅ API Key 长度正确（32字符）")
                        else:
                            print(f"   ⚠️  API Key 长度异常：{len(decrypted_key)} 字符（预期32字符）")
                    else:
                        print("❌ 解密结果为空！")
                except Exception as e:
                    print(f"❌ 解密失败: {str(e)}")
            else:
                print("❌ auth_passkey 未设置")

            # 测试 API 请求
            print("\n" + "=" * 60)
            print("🌐 测试 API 请求")
            print("=" * 60)

            if site.auth_passkey:
                try:
                    from app.adapters.pt_sites import get_adapter

                    # 准备配置
                    config = {
                        "name": site.name,
                        "base_url": site.base_url,
                        "domain": site.domain,
                        "proxy_config": site.proxy_config,
                        "request_interval": site.request_interval or 2,
                        "auth_passkey": encryption_util.decrypt(site.auth_passkey),
                    }

                    print(f"API 基础 URL: {config['base_url']}")
                    print(f"域名: {config['domain']}")
                    print(f"API Key (前10字符): {config['auth_passkey'][:10] if config['auth_passkey'] else 'None'}...")

                    adapter = get_adapter(site.type, config)

                    # 测试分类列表 API
                    print("\n📝 测试分类列表 API...")
                    try:
                        categories = await adapter.fetch_categories()
                        print(f"✅ 成功！获取到 {len(categories)} 个分类")
                        if categories:
                            print(f"   示例分类: {categories[0]}")
                    except Exception as e:
                        print(f"❌ 失败: {str(e)}")

                        # 提供更多调试信息
                        import traceback
                        print("\n详细错误信息：")
                        traceback.print_exc()

                    # 测试健康检查
                    print("\n💚 测试健康检查...")
                    try:
                        health = await adapter.health_check()
                        if health:
                            print("✅ 健康检查通过")
                        else:
                            print("❌ 健康检查失败")
                    except Exception as e:
                        print(f"❌ 失败: {str(e)}")

                except Exception as e:
                    print(f"❌ 创建适配器失败: {str(e)}")
                    import traceback
                    traceback.print_exc()

            print("\n" + "=" * 60)
            print("💡 诊断建议")
            print("=" * 60)
            print("如果看到 403 Forbidden 错误，请检查：")
            print("1. 你的 MTeam API Key 是否正确")
            print("   - 登录 MTeam 网站")
            print("   - 进入个人设置 -> API")
            print("   - 复制完整的 32 位 API Key")
            print()
            print("2. 基础 URL 是否正确")
            print("   - 应该是：https://api.m-team.io")
            print("   - 或者其他 MTeam 提供的 API 地址")
            print()
            print("3. 是否需要代理")
            print("   - 如果你的网络环境需要代理才能访问 MTeam API")
            print("   - 请在站点配置中设置正确的代理")
            print()
            print("4. API Key 是否过期")
            print("   - 某些 PT 站点的 API Key 有过期时间")
            print("   - 尝试重新生成 API Key")
            print()
            print("5. IP 是否被限制")
            print("   - 检查你的 IP 是否在站点的允许列表中")

        except Exception as e:
            print(f"\n❌ 调试过程出错: {str(e)}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    try:
        asyncio.run(debug_mteam_auth())
    except KeyboardInterrupt:
        print("\n\n⚠️  操作已取消")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 执行失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
