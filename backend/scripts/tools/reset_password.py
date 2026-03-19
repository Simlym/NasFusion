#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重置管理员密码脚本
使用方法：python reset_password.py
"""
import asyncio
import sys
import os
from pathlib import Path

# 设置Windows控制台编码为UTF-8
if sys.platform == "win32":
    os.system("chcp 65001 >nul 2>&1")

# 添加项目根目录到路径（backend/）
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import select
from app.core.database import async_session_local, engine
from app.models.user import User
from app.utils.security import get_password_hash


async def reset_admin_password():
    """重置管理员密码"""
    print("\n" + "=" * 60)
    print("NasFusion - 管理员密码重置工具")
    print("=" * 60 + "\n")

    # 获取用户名（默认admin）
    username = input("请输入要重置密码的用户名 [admin]: ").strip() or "admin"

    # 获取新密码
    new_password = input("请输入新密码 (留空则设为 'admin'): ").strip() or "admin"

    async with async_session_local() as db:
        # 查找用户
        result = await db.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()

        if not user:
            print(f"\n[ERROR] 错误：用户 '{username}' 不存在！")
            print("\n可用的用户列表：")
            result = await db.execute(select(User.username, User.role))
            users = result.all()
            for u in users:
                print(f"  - {u.username} ({u.role})")
            return

        # 更新密码
        user.password_hash = get_password_hash(new_password)
        await db.commit()

        print("\n" + "=" * 60)
        print("[SUCCESS] 密码重置成功！")
        print("=" * 60)
        print(f"用户名: {username}")
        print(f"新密码: {new_password}")
        print("=" * 60 + "\n")


async def main():
    """主函数"""
    try:
        await reset_admin_password()
    except KeyboardInterrupt:
        print("\n\n操作已取消")
    except Exception as e:
        print(f"\n[ERROR] 错误：{e}")
        import traceback
        traceback.print_exc()
    finally:
        # 关闭数据库连接
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
