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

    def __init__(self, bot_token: str, proxy: Optional[str] = None):
        self.bot_token = bot_token
        # 代理 URL，发送回复时走代理（用于内网访问 Telegram API）
        self.proxy = proxy

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

            # 获取或创建该 chat 的持续对话，保证多轮上下文连贯
            conversation = await AIAgentService.get_or_create_telegram_conversation(
                db,
                user_id,
                chat_id,
            )

            # 调用 AI Agent
            result = await AIAgentService.chat(
                db,
                user_id,
                text,
                conversation_id=conversation.id,
            )

            if not result.get("success"):
                return {
                    "success": False,
                    "error": result.get("error"),
                    "reply": f"处理失败: {result.get('error', '未知错误')}",
                }

            # 回复内容
            # 说明：工具调用后 AIAgentService 已让 LLM 二次生成完整回复，
            # 这里不再手动拼接工具结果摘要，避免与 AI 回复重复。
            reply = result.get("content", "")

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

    # Telegram 单条消息最大长度
    MAX_MESSAGE_LENGTH = 4096

    async def send_reply(
        self,
        chat_id: str,
        text: str,
    ) -> bool:
        """
        发送回复消息

        将 AI 输出的 Markdown 转换为 Telegram MarkdownV2 后发送
        （表格转等宽代码块、加粗/斜体/标题/列表等正确渲染）。
        若 MarkdownV2 解析失败，自动降级为纯文本重发，确保消息可达。

        Args:
            chat_id: Telegram Chat ID
            text: 回复文本（Markdown）

        Returns:
            是否发送成功
        """
        # 先按原始文本截断，避免超长（转义后长度会增加，发送前再兜底截断）
        if len(text) > self.MAX_MESSAGE_LENGTH:
            text = text[: self.MAX_MESSAGE_LENGTH - 6] + "\n..."

        # 转换为 Telegram MarkdownV2
        markdown_v2 = self._to_markdown_v2(text)
        if len(markdown_v2) > self.MAX_MESSAGE_LENGTH:
            markdown_v2 = markdown_v2[: self.MAX_MESSAGE_LENGTH]

        # 优先用 MarkdownV2 发送，解析失败则降级为纯文本
        if await self._send_message(chat_id, markdown_v2, parse_mode="MarkdownV2"):
            return True

        logger.warning("MarkdownV2 发送失败，降级为纯文本重发")
        return await self._send_message(chat_id, text, parse_mode=None)

    @staticmethod
    def _to_markdown_v2(text: str) -> str:
        """将通用 Markdown 转换为 Telegram MarkdownV2，失败则原样返回"""
        try:
            import telegramify_markdown

            return telegramify_markdown.standardize(text)
        except Exception:
            logger.exception("Markdown 转换失败，使用原文")
            return text

    async def _send_message(
        self,
        chat_id: str,
        text: str,
        parse_mode: Optional[str] = None,
    ) -> bool:
        """调用 sendMessage 发送一条消息"""
        try:
            url = f"{self.TELEGRAM_API_BASE}/bot{self.bot_token}/sendMessage"
            data: Dict[str, Any] = {
                "chat_id": chat_id,
                "text": text,
            }
            if parse_mode:
                data["parse_mode"] = parse_mode

            async with httpx.AsyncClient(timeout=30.0, proxy=self.proxy) as client:
                response = await client.post(url, json=data)
                response_data = response.json()

            if not response_data.get("ok"):
                logger.warning(
                    f"Telegram 发送返回错误 (parse_mode={parse_mode}): "
                    f"{response_data.get('description')}"
                )
                return False
            return True

        except Exception:
            logger.exception("发送 Telegram 消息失败")
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

        # 读取代理配置（发送回复时使用）
        from app.services.ai_agent.telegram_proxy import get_telegram_proxy
        proxy = await get_telegram_proxy(db)

        # 忽略命令（以 / 开头）
        if text.startswith("/"):
            handler = TelegramAgentHandler(bot_token, proxy=proxy)
            # 可以在这里处理特定命令
            if text.startswith("/start"):
                reply = (
                    "👋 欢迎使用 AI 助手！\n\n"
                    f"您当前的 Chat ID 是：`{chat_id}`\n"
                    "请在系统「通知渠道」中用此 Chat ID 配置 Telegram，完成账户绑定后即可对话。\n\n"
                    "绑定后可直接发送消息与我对话，例如：\n"
                    "- 推荐几部科幻电影\n"
                    "- 搜索复仇者联盟\n"
                    "- 查看下载状态"
                )
                await handler.send_reply(chat_id, reply)
                return reply
            elif text == "/help":
                reply = """🤖 **AI 助手**

我可以帮您：
📽 推荐电影/剧集
🔍 搜索 PT 资源
⬇️ 创建下载任务
📋 管理订阅
📊 查看系统状态

直接发送消息即可开始对话！"""
                await handler.send_reply(chat_id, reply)
                return reply
            return None

        # 处理普通消息
        handler = TelegramAgentHandler(bot_token, proxy=proxy)
        result = await handler.handle_message(db, chat_id, text)

        reply = result.get("reply")
        if reply:
            await handler.send_reply(chat_id, reply)

        return reply

    except Exception as e:
        logger.exception("处理 Telegram Update 失败")
        return None
