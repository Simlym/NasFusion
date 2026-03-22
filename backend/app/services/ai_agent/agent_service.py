# -*- coding: utf-8 -*-
"""
AI Agent 核心服务

对话管理和Agent执行
"""
import json
import logging
import time
from typing import Any, AsyncGenerator, Dict, List, Optional

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.llm import get_llm_adapter, ChatMessage
from app.constants.ai_agent import (
    DEFAULT_SYSTEM_PROMPT,
    MESSAGE_ROLE_ASSISTANT,
    MESSAGE_ROLE_SYSTEM,
    MESSAGE_ROLE_TOOL,
    MESSAGE_ROLE_USER,
    CONVERSATION_STATUS_ACTIVE,
    DEFAULT_CONVERSATION_MAX_TURNS,
)
from app.models import AIAgentConfig, AIConversation, AIMessage, AIToolExecution
from app.services.ai_agent.mcp_client.client import mcp_client
from app.utils.timezone import now


logger = logging.getLogger(__name__)


class AIAgentService:
    """
    AI Agent 服务

    提供对话管理、消息处理、工具调用等功能
    """

    # ==================== 配置管理 ====================

    @staticmethod
    async def get_config(db: AsyncSession, user_id: int) -> Optional[AIAgentConfig]:
        """获取用户的AI配置"""
        result = await db.execute(
            select(AIAgentConfig).where(AIAgentConfig.user_id == user_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_or_update_config(
        db: AsyncSession,
        user_id: int,
        config_data: Dict[str, Any],
    ) -> AIAgentConfig:
        """创建或更新AI配置"""
        config = await AIAgentService.get_config(db, user_id)

        if config:
            # 更新
            for key, value in config_data.items():
                if hasattr(config, key) and value is not None:
                    setattr(config, key, value)
        else:
            # 创建
            config = AIAgentConfig(user_id=user_id, **config_data)
            db.add(config)

        await db.commit()
        await db.refresh(config)
        return config

    # ==================== 对话管理 ====================

    @staticmethod
    async def create_conversation(
        db: AsyncSession,
        user_id: int,
        source: str = "web",
        telegram_chat_id: Optional[str] = None,
        title: Optional[str] = None,
    ) -> AIConversation:
        """创建新对话"""
        conversation = AIConversation(
            user_id=user_id,
            source=source,
            telegram_chat_id=telegram_chat_id,
            title=title or "新对话",
            status=CONVERSATION_STATUS_ACTIVE,
            message_count=0,
        )
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
        return conversation

    @staticmethod
    async def get_conversation(
        db: AsyncSession,
        conversation_id: int,
        user_id: int,
    ) -> Optional[AIConversation]:
        """获取对话"""
        result = await db.execute(
            select(AIConversation).where(
                AIConversation.id == conversation_id,
                AIConversation.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_or_create_telegram_conversation(
        db: AsyncSession,
        user_id: int,
        telegram_chat_id: str,
    ) -> AIConversation:
        """获取或创建Telegram对话"""
        result = await db.execute(
            select(AIConversation).where(
                AIConversation.user_id == user_id,
                AIConversation.telegram_chat_id == telegram_chat_id,
                AIConversation.status == CONVERSATION_STATUS_ACTIVE,
            )
        )
        conversation = result.scalar_one_or_none()

        if not conversation:
            conversation = await AIAgentService.create_conversation(
                db,
                user_id,
                source="telegram",
                telegram_chat_id=telegram_chat_id,
                title="Telegram对话",
            )

        return conversation

    @staticmethod
    async def list_conversations(
        db: AsyncSession,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
    ) -> tuple[List[AIConversation], int]:
        """获取对话列表"""
        query = select(AIConversation).where(AIConversation.user_id == user_id)

        if status:
            query = query.where(AIConversation.status == status)

        # 计数
        count_result = await db.execute(
            select(AIConversation.id).where(AIConversation.user_id == user_id)
        )
        total = len(count_result.all())

        # 分页
        query = query.order_by(desc(AIConversation.updated_at))
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        conversations = result.scalars().all()

        return list(conversations), total

    @staticmethod
    async def get_conversation_messages(
        db: AsyncSession,
        conversation_id: int,
        limit: int = 50,
    ) -> List[AIMessage]:
        """获取对话消息"""
        result = await db.execute(
            select(AIMessage)
            .where(AIMessage.conversation_id == conversation_id)
            .order_by(AIMessage.created_at)
            .limit(limit)
        )
        return list(result.scalars().all())

    # ==================== 消息处理 ====================

    @staticmethod
    async def add_message(
        db: AsyncSession,
        conversation_id: int,
        role: str,
        content: Optional[str],
        tool_calls: Optional[List[Dict]] = None,
        tool_call_id: Optional[str] = None,
        tool_name: Optional[str] = None,
        model: Optional[str] = None,
        finish_reason: Optional[str] = None,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
    ) -> AIMessage:
        """添加消息"""
        message = AIMessage(
            conversation_id=conversation_id,
            role=role,
            content=content,
            tool_calls=tool_calls,
            tool_call_id=tool_call_id,
            tool_name=tool_name,
            model=model,
            finish_reason=finish_reason,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
        db.add(message)

        # 更新对话统计
        conversation_result = await db.execute(
            select(AIConversation).where(AIConversation.id == conversation_id)
        )
        conversation = conversation_result.scalar_one_or_none()
        if conversation:
            conversation.message_count += 1
            conversation.last_message_at = now()
            # 自动生成标题（取用户第一条消息的前20字）
            if conversation.message_count == 1 and role == MESSAGE_ROLE_USER and content:
                conversation.title = content[:20] + ("..." if len(content) > 20 else "")

        await db.commit()
        await db.refresh(message)
        return message

    # ==================== Agent 执行 ====================

    @staticmethod
    async def chat(
        db: AsyncSession,
        user_id: int,
        message: str,
        conversation_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        处理聊天消息

        Args:
            db: 数据库会话
            user_id: 用户ID
            message: 用户消息
            conversation_id: 对话ID（可选）

        Returns:
            聊天响应
        """
        # 获取配置
        config = await AIAgentService.get_config(db, user_id)
        if not config or not config.is_enabled:
            return {
                "success": False,
                "error": "AI Agent 未启用，请先在设置中配置",
            }

        # 获取或创建对话
        if conversation_id:
            conversation = await AIAgentService.get_conversation(
                db, conversation_id, user_id
            )
            if not conversation:
                return {
                    "success": False,
                    "error": "对话不存在",
                }
        else:
            conversation = await AIAgentService.create_conversation(db, user_id)

        # 添加用户消息
        user_message = await AIAgentService.add_message(
            db,
            conversation.id,
            MESSAGE_ROLE_USER,
            message,
        )

        # 获取历史消息
        history_messages = await AIAgentService.get_conversation_messages(
            db,
            conversation.id,
            limit=DEFAULT_CONVERSATION_MAX_TURNS * 2,
        )

        # 构建消息列表
        messages = []

        # 系统提示词
        system_prompt = config.system_prompt or DEFAULT_SYSTEM_PROMPT
        messages.append(ChatMessage(role=MESSAGE_ROLE_SYSTEM, content=system_prompt))

        # 历史消息
        for msg in history_messages:
            if msg.role == MESSAGE_ROLE_TOOL:
                messages.append(ChatMessage(
                    role=MESSAGE_ROLE_TOOL,
                    content=msg.content or "",  # content 可能为 None
                    tool_call_id=msg.tool_call_id,
                    name=msg.tool_name,
                ))
            else:
                messages.append(ChatMessage(role=msg.role, content=msg.content or ""))

        # 获取LLM适配器
        try:
            adapter = get_llm_adapter(
                config.provider,
                {
                    "api_key": config.api_key,
                    "api_base": config.api_base,
                    "proxy": config.proxy,
                    "model": config.model,
                    "temperature": float(config.temperature),
                    "max_tokens": config.max_tokens,
                    "top_p": float(config.top_p),
                }
            )
        except Exception as e:
            logger.exception("创建LLM适配器失败")
            return {
                "success": False,
                "error": f"AI配置错误: {str(e)}",
            }

        # 获取工具定义（内部 + 外部 MCP Server）
        tools = None
        if config.enable_tools:
            tools = await mcp_client.list_tools(db, user_id)

        # 调用LLM
        try:
            response = await adapter.chat(messages=messages, tools=tools)
        except Exception as e:
            logger.exception("LLM调用失败")
            return {
                "success": False,
                "error": f"AI调用失败: {str(e)}",
            }

        # 处理响应
        tool_results = []

        # 如果有工具调用
        if response.tool_calls:
            # 保存助手消息（带工具调用）
            assistant_message = await AIAgentService.add_message(
                db,
                conversation.id,
                MESSAGE_ROLE_ASSISTANT,
                response.content,
                tool_calls=[tc.model_dump() for tc in response.tool_calls],
                model=config.model,
                finish_reason=response.finish_reason,
                prompt_tokens=response.usage.get("prompt_tokens") if response.usage else None,
                completion_tokens=response.usage.get("completion_tokens") if response.usage else None,
            )

            # 执行工具
            for tool_call in response.tool_calls:
                start_time = time.time()

                result = await mcp_client.call_tool(
                    tool_call.name,
                    tool_call.arguments,
                    db,
                    user_id,
                )

                execution_time = int((time.time() - start_time) * 1000)

                # 记录工具执行
                tool_execution = AIToolExecution(
                    message_id=assistant_message.id,
                    conversation_id=conversation.id,
                    user_id=user_id,
                    tool_name=tool_call.name,
                    tool_call_id=tool_call.id,
                    arguments=tool_call.arguments,
                    result=result,
                    status="completed" if result.get("success") else "failed",
                    error_message=result.get("error"),
                    execution_time_ms=execution_time,
                )
                db.add(tool_execution)

                # 添加工具结果消息
                await AIAgentService.add_message(
                    db,
                    conversation.id,
                    MESSAGE_ROLE_TOOL,
                    json.dumps(result, ensure_ascii=False),
                    tool_call_id=tool_call.id,
                    tool_name=tool_call.name,
                )

                tool_results.append({
                    "tool": tool_call.name,
                    "result": result,
                })

                # 更新消息列表
                messages.append(ChatMessage(
                    role=MESSAGE_ROLE_ASSISTANT,
                    content=response.content or "",  # 工具调用时 content 可能为 None
                ))
                messages.append(ChatMessage(
                    role=MESSAGE_ROLE_TOOL,
                    content=json.dumps(result, ensure_ascii=False),
                    tool_call_id=tool_call.id,
                    name=tool_call.name,
                ))

            # 再次调用LLM获取最终回复
            try:
                final_response = await adapter.chat(messages=messages, tools=tools)
                final_content = final_response.content or "工具执行完成"
            except Exception as e:
                logger.exception("LLM最终调用失败")
                final_content = "工具已执行，但生成回复时出错"

            # 保存最终回复
            final_message = await AIAgentService.add_message(
                db,
                conversation.id,
                MESSAGE_ROLE_ASSISTANT,
                final_content,
                model=config.model,
                finish_reason="stop",
            )

            await db.commit()

            return {
                "success": True,
                "conversation_id": conversation.id,
                "message_id": final_message.id,
                "content": final_content,
                "tool_calls": [tc.model_dump() for tc in response.tool_calls],
                "tool_results": tool_results,
                "finish_reason": "stop",
                "usage": response.usage,
            }

        else:
            # 无工具调用，直接保存回复
            assistant_message = await AIAgentService.add_message(
                db,
                conversation.id,
                MESSAGE_ROLE_ASSISTANT,
                response.content,
                model=config.model,
                finish_reason=response.finish_reason,
                prompt_tokens=response.usage.get("prompt_tokens") if response.usage else None,
                completion_tokens=response.usage.get("completion_tokens") if response.usage else None,
            )

            await db.commit()

            return {
                "success": True,
                "conversation_id": conversation.id,
                "message_id": assistant_message.id,
                "content": response.content,
                "tool_calls": None,
                "tool_results": None,
                "finish_reason": response.finish_reason,
                "usage": response.usage,
            }

    @staticmethod
    async def chat_stream(
        db: AsyncSession,
        user_id: int,
        message: str,
        conversation_id: Optional[int] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式处理聊天消息

        Args:
            db: 数据库会话
            user_id: 用户ID
            message: 用户消息
            conversation_id: 对话ID（可选）

        Yields:
            流式响应块
        """
        # 获取配置
        config = await AIAgentService.get_config(db, user_id)
        if not config or not config.is_enabled:
            yield {
                "type": "error",
                "error": "AI Agent 未启用",
            }
            return

        # 获取或创建对话
        if conversation_id:
            conversation = await AIAgentService.get_conversation(
                db, conversation_id, user_id
            )
            if not conversation:
                yield {
                    "type": "error",
                    "error": "对话不存在",
                }
                return
        else:
            conversation = await AIAgentService.create_conversation(db, user_id)

        # 发送对话ID
        yield {
            "type": "conversation",
            "conversation_id": conversation.id,
        }

        # 添加用户消息
        await AIAgentService.add_message(
            db,
            conversation.id,
            MESSAGE_ROLE_USER,
            message,
        )

        # 获取历史消息
        history_messages = await AIAgentService.get_conversation_messages(
            db,
            conversation.id,
            limit=DEFAULT_CONVERSATION_MAX_TURNS * 2,
        )

        # 构建消息列表
        messages = []
        system_prompt = config.system_prompt or DEFAULT_SYSTEM_PROMPT
        messages.append(ChatMessage(role=MESSAGE_ROLE_SYSTEM, content=system_prompt))

        for msg in history_messages:
            if msg.role == MESSAGE_ROLE_TOOL:
                messages.append(ChatMessage(
                    role=MESSAGE_ROLE_TOOL,
                    content=msg.content or "",  # content 可能为 None
                    tool_call_id=msg.tool_call_id,
                    name=msg.tool_name,
                ))
            else:
                messages.append(ChatMessage(role=msg.role, content=msg.content or ""))

        # 获取LLM适配器
        try:
            adapter = get_llm_adapter(
                config.provider,
                {
                    "api_key": config.api_key,
                    "api_base": config.api_base,
                    "proxy": config.proxy,
                    "model": config.model,
                    "temperature": float(config.temperature),
                    "max_tokens": config.max_tokens,
                    "top_p": float(config.top_p),
                }
            )
        except Exception as e:
            yield {
                "type": "error",
                "error": f"AI配置错误: {str(e)}",
            }
            return

        # 获取工具定义
        tools = None
        if config.enable_tools:
            tools = await mcp_client.list_tools(db, user_id)

        # 流式调用（支持工具调用循环）
        max_tool_rounds = 5  # 防止无限循环
        try:
            for round_idx in range(max_tool_rounds + 1):
                full_content = ""
                tool_calls_result = None

                async for event in adapter.chat_stream(messages=messages, tools=tools):
                    if event.type == "content" and event.content:
                        full_content += event.content
                        yield {
                            "type": "content",
                            "content": event.content,
                        }
                    elif event.type == "tool_calls" and event.tool_calls:
                        tool_calls_result = event.tool_calls
                    # type == "done" 不需要特殊处理

                # 如果没有工具调用，保存回复并结束
                if not tool_calls_result:
                    assistant_message = await AIAgentService.add_message(
                        db,
                        conversation.id,
                        MESSAGE_ROLE_ASSISTANT,
                        full_content,
                        model=config.model,
                        finish_reason="stop",
                    )
                    await db.commit()

                    yield {
                        "type": "done",
                        "message_id": assistant_message.id,
                        "content": full_content,
                    }
                    return

                # 有工具调用：保存助手消息，执行工具，继续循环
                assistant_message = await AIAgentService.add_message(
                    db,
                    conversation.id,
                    MESSAGE_ROLE_ASSISTANT,
                    full_content or None,
                    tool_calls=[tc.model_dump() for tc in tool_calls_result],
                    model=config.model,
                    finish_reason="tool_calls",
                )

                # 通知前端开始工具调用
                yield {
                    "type": "tool_calls",
                    "tool_calls": [{"id": tc.id, "name": tc.name, "arguments": tc.arguments} for tc in tool_calls_result],
                }

                # 更新消息列表：添加助手消息（带 tool_calls 信息）
                messages.append(ChatMessage(
                    role=MESSAGE_ROLE_ASSISTANT,
                    content=full_content or "",
                ))

                # 逐个执行工具
                for tool_call in tool_calls_result:
                    start_time = time.time()

                    result = await mcp_client.call_tool(
                        tool_call.name,
                        tool_call.arguments,
                        db,
                        user_id,
                    )

                    execution_time = int((time.time() - start_time) * 1000)

                    # 记录工具执行
                    tool_execution = AIToolExecution(
                        message_id=assistant_message.id,
                        conversation_id=conversation.id,
                        user_id=user_id,
                        tool_name=tool_call.name,
                        tool_call_id=tool_call.id,
                        arguments=tool_call.arguments,
                        result=result,
                        status="completed" if result.get("success") else "failed",
                        error_message=result.get("error"),
                        execution_time_ms=execution_time,
                    )
                    db.add(tool_execution)

                    # 添加工具结果消息
                    await AIAgentService.add_message(
                        db,
                        conversation.id,
                        MESSAGE_ROLE_TOOL,
                        json.dumps(result, ensure_ascii=False),
                        tool_call_id=tool_call.id,
                        tool_name=tool_call.name,
                    )

                    # 通知前端工具执行结果
                    yield {
                        "type": "tool_result",
                        "tool_call_id": tool_call.id,
                        "tool_name": tool_call.name,
                        "result": result,
                        "execution_time_ms": execution_time,
                    }

                    # 更新消息列表
                    messages.append(ChatMessage(
                        role=MESSAGE_ROLE_TOOL,
                        content=json.dumps(result, ensure_ascii=False),
                        tool_call_id=tool_call.id,
                        name=tool_call.name,
                    ))

                # 循环继续，再次流式调用 LLM 让其根据工具结果生成回复

            # 超过最大轮次
            yield {
                "type": "error",
                "error": "工具调用轮次超过上限，已终止",
            }

        except Exception as e:
            logger.exception("流式调用失败")
            yield {
                "type": "error",
                "error": f"AI调用失败: {str(e)}",
            }
