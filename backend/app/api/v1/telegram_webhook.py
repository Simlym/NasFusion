# -*- coding: utf-8 -*-
"""
Telegram Webhook API 端点

接收 Telegram Bot 的 Webhook 请求
"""
import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.services.ai_agent.telegram_handler import process_telegram_update

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telegram", tags=["Telegram Webhook"])


@router.post("/webhook/{bot_token}")
async def telegram_webhook(
    bot_token: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Telegram Webhook 端点

    接收来自 Telegram 的更新消息

    设置 Webhook:
    https://api.telegram.org/bot<token>/setWebhook?url=https://your-domain.com/api/v1/telegram/webhook/<token>
    """
    try:
        # 获取请求体
        update = await request.json()

        logger.debug(f"收到 Telegram Update: {update}")

        # 处理更新
        await process_telegram_update(db, bot_token, update)

        # Telegram 要求返回 200
        return {"ok": True}

    except Exception as e:
        logger.exception(f"处理 Telegram Webhook 失败: {str(e)}")
        # 即使出错也返回 200，避免 Telegram 重试
        return {"ok": True}


@router.get("/webhook/info")
async def get_webhook_info():
    """
    获取 Webhook 设置说明
    """
    return {
        "message": "Telegram Webhook 配置说明",
        "steps": [
            "1. 获取您的 Bot Token（从 @BotFather）",
            "2. 配置系统的外网访问地址（需要 HTTPS）",
            "3. 调用以下 URL 设置 Webhook：",
            "   https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook?url=<YOUR_DOMAIN>/api/v1/telegram/webhook/<YOUR_BOT_TOKEN>",
            "4. 在 NasFusion 中配置 Telegram 通知渠道",
            "5. 发送消息给 Bot 即可开始对话",
        ],
        "example": {
            "set_webhook": "https://api.telegram.org/bot123456:ABC-DEF/setWebhook?url=https://example.com/api/v1/telegram/webhook/123456:ABC-DEF",
            "delete_webhook": "https://api.telegram.org/bot123456:ABC-DEF/deleteWebhook",
            "get_webhook_info": "https://api.telegram.org/bot123456:ABC-DEF/getWebhookInfo",
        },
    }
