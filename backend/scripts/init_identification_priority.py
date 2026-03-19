# -*- coding: utf-8 -*-
"""
初始化资源识别优先级配置

运行方式：
    python scripts/init_identification_priority.py
"""
import asyncio
import json
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.core.database import async_session_local
from app.models.system_setting import SystemSetting
from app.constants.resource_identification import DEFAULT_IDENTIFICATION_PRIORITY


async def init_identification_priority():
    """初始化资源识别优先级配置"""
    async with async_session_local() as db:
        # 检查配置是否已存在
        result = await db.execute(
            select(SystemSetting).where(
                SystemSetting.category == "metadata_scraping",
                SystemSetting.key == "identification_priority",
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            print(f"识别优先级配置已存在，当前值：{existing.value}")
            print("如需重置，请手动删除后重新运行此脚本")
            return

        # 创建默认配置
        config_value = json.dumps(
            {"enabled_sources": DEFAULT_IDENTIFICATION_PRIORITY},
            ensure_ascii=False
        )

        setting = SystemSetting(
            category="metadata_scraping",
            key="identification_priority",
            value=config_value,
            description="资源识别优先级配置（启用的识别源及其顺序）",
            is_active=True,
            is_encrypted=False,
        )

        db.add(setting)
        await db.commit()
        await db.refresh(setting)

        print("Success: Created identification priority configuration")
        print(f"  ID: {setting.id}")
        print(f"  Category: {setting.category}")
        print(f"  Key: {setting.key}")
        print(f"  Value: {setting.value}")
        print(f"\nDefault priority order:")
        for i, source in enumerate(DEFAULT_IDENTIFICATION_PRIORITY, 1):
            print(f"  {i}. {source}")


if __name__ == "__main__":
    asyncio.run(init_identification_priority())
