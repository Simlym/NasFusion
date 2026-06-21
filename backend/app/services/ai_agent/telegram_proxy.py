# -*- coding: utf-8 -*-
"""
Telegram 代理配置

代理地址存储在系统设置（system_setting）中，与 TMDB/TVDB 代理保持一致的管理方式：
Web 端可配、热生效、各服务代理互不影响。

设置位置：category='notification', key='telegram_proxy'，值为代理 URL
（如 http://127.0.0.1:7890 或 socks5://127.0.0.1:1080），留空表示直连。
"""
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.common.system_setting_service import SystemSettingService

logger = logging.getLogger(__name__)

# 设置分类与键名，集中定义避免散落的魔法字符串
TELEGRAM_PROXY_CATEGORY = "notification"
TELEGRAM_PROXY_KEY = "telegram_proxy"


async def get_telegram_proxy(db: AsyncSession) -> Optional[str]:
    """
    读取 Telegram 代理 URL

    Args:
        db: 数据库会话

    Returns:
        代理 URL，未配置则返回 None（直连）
    """
    try:
        setting = await SystemSettingService.get_by_key(
            db, TELEGRAM_PROXY_CATEGORY, TELEGRAM_PROXY_KEY
        )
        if setting and setting.value:
            return setting.value.strip() or None
    except Exception:
        logger.exception("读取 Telegram 代理配置失败")
    return None
