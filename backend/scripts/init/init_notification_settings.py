#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
初始化通知系统默认配置到 system_settings 表

使用方法：
    python scripts/init_notification_settings.py
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
from app.constants.notification import (
    DEFAULT_NOTIFICATION_EXPIRE_DAYS,
    DEFAULT_DEDUPLICATION_WINDOW,
    DEFAULT_MAX_RETRY_COUNT,
    DEFAULT_MAX_MESSAGE_LENGTH,
)


async def init_notification_settings():
    """初始化通知系统默认配置"""
    async with async_session_local() as db:
        print("初始化通知系统配置...")
        print("-" * 60)

        # 定义默认配置项
        default_settings = {
            # 基础配置
            "notification.default_language": (
                "zh-CN",
                "默认通知语言"
            ),
            "notification.retention_days": (
                str(DEFAULT_NOTIFICATION_EXPIRE_DAYS),
                "消息保留天数（超过此天数的已读消息将被自动清理）"
            ),
            "notification.max_message_length": (
                str(DEFAULT_MAX_MESSAGE_LENGTH),
                "单条通知最大字符长度"
            ),
            "notification.deduplication_window": (
                str(DEFAULT_DEDUPLICATION_WINDOW),
                "消息去重时间窗口（秒），相同内容在此时间内不重复发送"
            ),
            "notification.max_retry_count": (
                str(DEFAULT_MAX_RETRY_COUNT),
                "通知发送失败最大重试次数"
            ),
            "notification.enable_system_messages": (
                "true",
                "启用系统内消息（站内信）"
            ),

            # Telegram 渠道配置
            "notification.telegram.default_parse_mode": (
                "Markdown",
                "Telegram 默认消息格式（Markdown/HTML/text）"
            ),
            "notification.telegram.disable_notification": (
                "false",
                "Telegram 静音推送（不发送声音提示）"
            ),

            # Email 渠道配置
            "notification.email.smtp_timeout": (
                "30",
                "Email SMTP 连接超时时间（秒）"
            ),
            "notification.email.use_tls": (
                "true",
                "Email 是否使用 TLS 加密"
            ),

            # Webhook 渠道配置
            "notification.webhook.default_method": (
                "POST",
                "Webhook 默认请求方法（POST/PUT）"
            ),
            "notification.webhook.timeout": (
                "30",
                "Webhook 请求超时时间（秒）"
            ),
            "notification.webhook.follow_redirects": (
                "true",
                "Webhook 是否跟随重定向"
            ),

            # 渠道通用配置
            "notification.channel_timeout": (
                "30",
                "通知渠道发送超时时间（秒）"
            ),
            "notification.batch_send_enabled": (
                "false",
                "启用批量发送通知（合并多条消息）"
            ),
            "notification.consecutive_failures_threshold": (
                "5",
                "渠道连续失败次数阈值（达到后自动禁用渠道）"
            ),
        }

        # 逐个配置项进行 upsert
        created_count = 0
        updated_count = 0

        for key, (value, description) in default_settings.items():
            # 查询是否已存在
            query = select(SystemSetting).where(
                SystemSetting.category == "notification",
                SystemSetting.key == key,
            )
            result = await db.execute(query)
            existing = result.scalar_one_or_none()

            if existing:
                # 更新描述（保留用户修改的值）
                if existing.description != description:
                    existing.description = description
                    updated_count += 1
                    print(f"  [更新] {key} (保留现有值)")
            else:
                # 创建新配置
                setting = SystemSetting(
                    category="notification",
                    key=key,
                    value=value,
                    description=description,
                    is_active=True,
                )
                db.add(setting)
                created_count += 1
                print(f"  [创建] {key} = {value}")

        await db.commit()

        print("-" * 60)
        print(f"通知配置初始化完成！")
        print(f"   - 新增配置: {created_count} 项")
        print(f"   - 更新配置: {updated_count} 项")
        print("\n现在您可以：")
        print("  1. 在前端 /settings?tab=notifications 页面修改配置")
        print("  2. 通过 API /api/v1/system-settings 查询和更新配置")
        print("  3. 配置将自动应用到通知系统的各个模块\n")


async def show_current_settings():
    """显示当前通知配置"""
    async with async_session_local() as db:
        print("\n当前通知系统配置：")
        print("=" * 60)

        # 查询所有 notification category 的配置
        query = select(SystemSetting).where(
            SystemSetting.category == "notification"
        ).order_by(SystemSetting.key)

        result = await db.execute(query)
        settings = result.scalars().all()

        if settings:
            for setting in settings:
                status = "[活动]" if setting.is_active else "[禁用]"
                print(f"{status} {setting.key}")
                print(f"  值: {setting.value}")
                print(f"  说明: {setting.description}")
                print()
        else:
            print("未找到任何通知配置，请先运行初始化脚本")
            print("\n运行命令:")
            print("  python scripts/init_notification_settings.py")

        print("=" * 60 + "\n")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="初始化通知系统配置")
    parser.add_argument("--show", action="store_true", help="显示当前配置")

    args = parser.parse_args()

    if args.show:
        asyncio.run(show_current_settings())
    else:
        asyncio.run(init_notification_settings())


if __name__ == "__main__":
    main()
