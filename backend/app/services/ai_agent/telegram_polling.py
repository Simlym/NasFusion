# -*- coding: utf-8 -*-
"""
Telegram 长轮询服务

通过 Telegram Bot 的 getUpdates 接口持续拉取用户消息，无需公网回调地址即可
接收对话消息，适合部署在内网 / NAS 环境。

与 Webhook 方案二选一：
- Webhook：需要公网 HTTPS 地址，Telegram 主动推送（见 telegram_webhook.py）
- 长轮询：本服务，应用主动拉取，内网即可工作（默认方式）

工作流程：
1. 应用启动时从已启用的 Telegram 通知渠道中读取 bot_token
2. 为每个不同的 bot_token 启动一个轮询协程
3. 收到消息后复用 TelegramAgentHandler 调用 AI Agent 并回复
"""
import asyncio
import logging
from typing import Any, Dict, List, Optional, Set

import httpx
from sqlalchemy import select

from app.constants.notification import NOTIFICATION_CHANNEL_TELEGRAM
from app.core.config import settings
from app.core.database import async_session_local
from app.models import NotificationChannel
from app.services.ai_agent.telegram_handler import process_telegram_update

logger = logging.getLogger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org"

# getUpdates 的长轮询超时（秒），Telegram 在此时间内无消息才返回空
LONG_POLL_TIMEOUT = 30
# 网络异常后的重试等待（秒）
RETRY_DELAY = 5


class TelegramPoller:
    """
    单个 Bot 的长轮询器

    维护自身的 update offset，循环调用 getUpdates 拉取消息并交给
    AI Agent 处理。一个 bot_token 对应一个实例。
    """

    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self._offset: Optional[int] = None
        self._running = False
        # 复用 OpenAI 代理配置，便于内网访问 Telegram 时走代理
        self._proxy = settings.openai.PROXY

    async def run(self) -> None:
        """启动轮询循环，直到 stop() 被调用"""
        self._running = True
        masked = self.bot_token.split(":")[0]
        logger.info(f"Telegram 长轮询启动: bot={masked}")

        # 启动前清理可能存在的 Webhook，否则 getUpdates 会返回 409 冲突
        await self._delete_webhook()

        while self._running:
            try:
                updates = await self._fetch_updates()
                for update in updates:
                    await self._handle_update(update)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.warning(f"Telegram 轮询异常，{RETRY_DELAY}s 后重试: {e}")
                await asyncio.sleep(RETRY_DELAY)

        logger.info(f"Telegram 长轮询停止: bot={masked}")

    def stop(self) -> None:
        """请求停止轮询"""
        self._running = False

    async def _delete_webhook(self) -> None:
        """删除已配置的 Webhook，避免与长轮询冲突"""
        try:
            url = f"{TELEGRAM_API_BASE}/bot{self.bot_token}/deleteWebhook"
            async with httpx.AsyncClient(timeout=10.0, proxy=self._proxy) as client:
                await client.post(url, json={"drop_pending_updates": False})
        except Exception as e:
            logger.debug(f"删除 Webhook 失败（可忽略）: {e}")

    async def _fetch_updates(self) -> List[Dict[str, Any]]:
        """调用 getUpdates 拉取一批消息"""
        url = f"{TELEGRAM_API_BASE}/bot{self.bot_token}/getUpdates"
        params: Dict[str, Any] = {
            "timeout": LONG_POLL_TIMEOUT,
            # 只关心消息和按钮回调，减少无关更新
            "allowed_updates": ["message", "callback_query"],
        }
        if self._offset is not None:
            params["offset"] = self._offset

        # 客户端超时需大于长轮询超时，留出网络余量
        timeout = httpx.Timeout(LONG_POLL_TIMEOUT + 15)
        async with httpx.AsyncClient(timeout=timeout, proxy=self._proxy) as client:
            response = await client.post(url, json=params)
            data = response.json()

        if not data.get("ok"):
            logger.warning(f"getUpdates 返回错误: {data.get('description')}")
            return []

        updates = data.get("result", [])
        if updates:
            # 下次从最后一条之后开始拉取，确认已消费
            self._offset = updates[-1]["update_id"] + 1
        return updates

    async def _handle_update(self, update: Dict[str, Any]) -> None:
        """处理单条 update：交给 AI Agent 并自动回复"""
        try:
            async with async_session_local() as db:
                await process_telegram_update(db, self.bot_token, update)
        except Exception:
            logger.exception("处理 Telegram 消息失败")


class TelegramPollingManager:
    """
    长轮询管理器（单例）

    负责在应用启动 / 通知渠道变更时，根据已启用的 Telegram 渠道维护一组
    TelegramPoller。每个唯一 bot_token 仅保留一个轮询任务。
    """

    def __init__(self):
        # bot_token -> (poller, task)
        self._pollers: Dict[str, "tuple[TelegramPoller, asyncio.Task]"] = {}
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        """应用启动时调用，按当前渠道配置拉起轮询任务"""
        if not settings.TELEGRAM_POLLING_ENABLED:
            logger.info("Telegram 长轮询已关闭（TELEGRAM_POLLING_ENABLED=False）")
            return
        await self.reload()

    async def reload(self) -> None:
        """
        重新加载渠道配置，启动新增的 bot、停止已移除的 bot

        通知渠道增删改后可调用此方法实现热更新。
        """
        if not settings.TELEGRAM_POLLING_ENABLED:
            return

        async with self._lock:
            tokens = await self._load_enabled_bot_tokens()

            # 停止已不再需要的轮询任务
            for token in list(self._pollers.keys()):
                if token not in tokens:
                    await self._stop_poller(token)

            # 启动新增的轮询任务
            for token in tokens:
                if token not in self._pollers:
                    self._start_poller(token)

    async def shutdown(self) -> None:
        """应用关闭时停止所有轮询任务"""
        async with self._lock:
            for token in list(self._pollers.keys()):
                await self._stop_poller(token)

    def _start_poller(self, bot_token: str) -> None:
        poller = TelegramPoller(bot_token)
        task = asyncio.create_task(poller.run())
        self._pollers[bot_token] = (poller, task)

    async def _stop_poller(self, bot_token: str) -> None:
        poller, task = self._pollers.pop(bot_token)
        poller.stop()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("停止 Telegram 轮询任务出错")

    @staticmethod
    async def _load_enabled_bot_tokens() -> Set[str]:
        """读取所有已启用 Telegram 渠道的 bot_token（去重）"""
        tokens: Set[str] = set()
        try:
            async with async_session_local() as db:
                result = await db.execute(
                    select(NotificationChannel).where(
                        NotificationChannel.channel_type == NOTIFICATION_CHANNEL_TELEGRAM,
                        NotificationChannel.enabled.is_(True),
                    )
                )
                channels = result.scalars().all()
                for channel in channels:
                    config = channel.config or {}
                    token = config.get("bot_token")
                    if token:
                        tokens.add(token)
        except Exception:
            logger.exception("加载 Telegram 渠道配置失败")
        return tokens


# 全局单例
telegram_polling_manager = TelegramPollingManager()
