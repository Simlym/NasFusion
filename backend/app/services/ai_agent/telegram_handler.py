# -*- coding: utf-8 -*-
"""
Telegram AI Agent 处理器

处理来自 Telegram 的消息，与 AI Agent 交互
"""
import logging
from typing import Any, Dict, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, NotificationChannel
from app.constants.notification import NOTIFICATION_CHANNEL_TELEGRAM
from app.services.ai_agent import AIAgentService

logger = logging.getLogger(__name__)


class TelegramAgentHandler:
    """
    Telegram Agent 处理器

    接收 Telegram 消息，调用 AI Agent 处理，返回回复
    """

    TELEGRAM_API_BASE = "https://api.telegram.org"

    def __init__(self, bot_token: str):
        self.bot_token = bot_token

    async def handle_message(
        self,
        db: AsyncSession,
        chat_id: str,
        text: str,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        处理 Telegram 消息

        Args:
            db: 数据库会话
            chat_id: Telegram Chat ID
            text: 消息文本
            user_id: NasFusion 用户ID（可选，如果已绑定）

        Returns:
            处理结果
        """
        try:
            # 如果没有用户ID，尝试通过 chat_id 查找绑定的用户
            if not user_id:
                user_id = await self._find_user_by_chat_id(db, chat_id)

            if not user_id:
                return {
                    "success": False,
                    "error": "未绑定 NasFusion 账户",
                    "reply": "您还未绑定 NasFusion 账户，请先在系统设置中绑定 Telegram。",
                }

            # 调用 AI Agent
            result = await AIAgentService.chat(
                db,
                user_id,
                text,
                conversation_id=None,  # 使用 Telegram 对话
            )

            if not result.get("success"):
                return {
                    "success": False,
                    "error": result.get("error"),
                    "reply": f"处理失败: {result.get('error', '未知错误')}",
                }

            # 格式化回复
            reply = result.get("content", "")

            # 如果有工具调用结果，添加摘要
            tool_results = result.get("tool_results")
            if tool_results:
                for tr in tool_results:
                    tool_name = tr.get("tool", "")
                    tool_result = tr.get("result", {})

                    # 根据工具类型格式化
                    if tool_name == "movie_recommend" and tool_result.get("movies"):
                        movies = tool_result["movies"]
                        reply += "\n\n🎬 **推荐电影:**"
                        for i, m in enumerate(movies[:5], 1):
                            rating = m.get("douban_rating") or m.get("tmdb_rating") or "N/A"
                            reply += f"\n{i}. {m['title']} ({m.get('year', 'N/A')}) ⭐{rating}"

                    elif tool_name == "tv_recommend" and tool_result.get("tv_series"):
                        tv_list = tool_result["tv_series"]
                        reply += "\n\n📺 **推荐剧集:**"
                        for i, tv in enumerate(tv_list[:5], 1):
                            rating = tv.get("douban_rating") or tv.get("tmdb_rating") or "N/A"
                            reply += f"\n{i}. {tv['title']} ({tv.get('first_air_year', 'N/A')}) ⭐{rating}"

                    elif tool_name == "resource_search" and tool_result.get("resources"):
                        resources = tool_result["resources"]
                        reply += "\n\n🔍 **搜索结果:**"
                        for i, r in enumerate(resources[:5], 1):
                            promo = "🆓" if r.get("is_free") else ""
                            reply += f"\n{i}. {r['title'][:30]} {promo}"

                    elif tool_name == "download_status" and tool_result.get("tasks"):
                        tasks = tool_result["tasks"]
                        reply += "\n\n⬇️ **下载状态:**"
                        for t in tasks[:5]:
                            status_emoji = {
                                "downloading": "⏬",
                                "seeding": "🌱",
                                "completed": "✅",
                                "error": "❌",
                            }.get(t["status"], "⏳")
                            reply += f"\n{status_emoji} {t['title'][:25]}"

                    elif tool_name == "subscription_list" and tool_result.get("subscriptions"):
                        subs = tool_result["subscriptions"]
                        reply += "\n\n📋 **订阅列表:**"
                        for s in subs[:5]:
                            status_emoji = "✅" if s["status"] == "active" else "⏸"
                            reply += f"\n{status_emoji} {s['title']}"

            return {
                "success": True,
                "reply": reply,
                "conversation_id": result.get("conversation_id"),
            }

        except Exception as e:
            logger.exception("处理 Telegram 消息失败")
            return {
                "success": False,
                "error": str(e),
                "reply": f"处理出错: {str(e)}",
            }

    async def send_reply(
        self,
        chat_id: str,
        text: str,
        parse_mode: str = "Markdown",
    ) -> bool:
        """
        发送回复消息

        Args:
            chat_id: Telegram Chat ID
            text: 回复文本
            parse_mode: 解析模式

        Returns:
            是否发送成功
        """
        try:
            url = f"{self.TELEGRAM_API_BASE}/bot{self.bot_token}/sendMessage"

            # 截断过长消息
            if len(text) > 4096:
                text = text[:4090] + "\n..."

            data = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": parse_mode,
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=data)
                response_data = response.json()

            return response_data.get("ok", False)

        except Exception as e:
            logger.exception(f"发送 Telegram 回复失败: {str(e)}")
            return False

    async def _find_user_by_chat_id(
        self,
        db: AsyncSession,
        chat_id: str,
    ) -> Optional[int]:
        """
        通过 Telegram Chat ID 查找绑定的用户

        查找通知渠道配置中绑定了该 chat_id 的用户
        """
        try:
            # 查找配置了该 chat_id 的 Telegram 渠道
            result = await db.execute(
                select(NotificationChannel).where(
                    NotificationChannel.channel_type == NOTIFICATION_CHANNEL_TELEGRAM,
                )
            )
            channels = result.scalars().all()

            for channel in channels:
                config = channel.config or {}
                if config.get("chat_id") == chat_id:
                    return channel.user_id

            return None

        except Exception as e:
            logger.exception(f"查找用户失败: {str(e)}")
            return None


# Telegram Webhook 处理（可选，用于实时接收消息）

async def process_telegram_update(
    db: AsyncSession,
    bot_token: str,
    update: Dict[str, Any],
) -> Optional[str]:
    """
    处理 Telegram Webhook Update

    Args:
        db: 数据库会话
        bot_token: Bot Token
        update: Telegram Update 对象

    Returns:
        回复消息（如果有）
    """
    try:
        # 提取消息
        message = update.get("message")
        if not message:
            return None

        chat_id = str(message.get("chat", {}).get("id"))
        text = message.get("text", "")

        if not chat_id or not text:
            return None

        # 忽略命令（以 / 开头）
        if text.startswith("/"):
            # 可以在这里处理特定命令
            if text == "/start":
                return "👋 欢迎使用 NasFusion AI 助手！\n\n您可以直接发送消息与我对话，例如：\n- 推荐几部科幻电影\n- 搜索复仇者联盟\n- 查看下载状态"
            elif text == "/help":
                return """🤖 **NasFusion AI 助手**

我可以帮您：
📽 推荐电影/剧集
🔍 搜索 PT 资源
⬇️ 创建下载任务
📋 管理订阅
📊 查看系统状态

直接发送消息即可开始对话！"""
            return None

        # 处理普通消息
        handler = TelegramAgentHandler(bot_token)
        result = await handler.handle_message(db, chat_id, text)

        reply = result.get("reply")
        if reply:
            await handler.send_reply(chat_id, reply)

        return reply

    except Exception as e:
        logger.exception("处理 Telegram Update 失败")
        return None
