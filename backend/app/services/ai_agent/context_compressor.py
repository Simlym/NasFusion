# -*- coding: utf-8 -*-
"""
上下文压缩服务

用于处理长对话的上下文管理：
1. Token 计算和估算
2. 对话摘要生成
3. 智能上下文截断
4. 历史消息压缩
"""
import json
import logging
from typing import Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.llm import ChatMessage, get_llm_adapter
from app.constants.ai_agent import (
    MESSAGE_ROLE_ASSISTANT,
    MESSAGE_ROLE_SYSTEM,
    MESSAGE_ROLE_TOOL,
    MESSAGE_ROLE_USER,
)
from app.models import AIAgentConfig, AIConversation, AIMessage

logger = logging.getLogger(__name__)


class ContextCompressor:
    """
    上下文压缩器
    
    管理对话历史，防止 Token 超限：
    - 保留最近 N 条完整消息
    - 对老消息生成摘要
    - 支持完全摘要模式（适用于超长对话）
    """

    # Token 估算：中文字符约 1.5 tokens，英文单词约 1.3 tokens
    AVG_TOKEN_PER_CHAR = 1.5
    
    # 默认保留的最近消息数
    DEFAULT_KEEP_RECENT = 6
    
    # 触发摘要的 Token 阈值
    SUMMARIZE_THRESHOLD = 6000
    
    # 最大上下文 Token 数（超过则强制截断）
    MAX_CONTEXT_TOKENS = 8000

    def __init__(self, config: AIAgentConfig):
        self.config = config
        self.keep_recent = self.DEFAULT_KEEP_RECENT

    def estimate_tokens(self, messages: List[ChatMessage]) -> int:
        """
        估算消息列表的 Token 数
        
        简单估算：按字符数计算
        更精确的实现可以使用 tiktoken
        """
        total_chars = 0
        for msg in messages:
            if msg.content:
                total_chars += len(msg.content)
        return int(total_chars * self.AVG_TOKEN_PER_CHAR)

    def estimate_tokens_for_message(self, message: AIMessage) -> int:
        """估算单条消息的 Token 数"""
        content_len = len(message.content) if message.content else 0
        # 工具调用结果通常较长，额外计算
        if message.role == MESSAGE_ROLE_TOOL and message.content:
            try:
                # 尝试解析 JSON，获取实际内容长度
                data = json.loads(message.content)
                content_len = len(str(data))
            except Exception:
                pass
        return int(content_len * self.AVG_TOKEN_PER_CHAR)

    async def compress_context(
        self,
        db: AsyncSession,
        conversation: AIConversation,
        history_messages: List[AIMessage],
        system_prompt: str,
    ) -> Tuple[List[ChatMessage], Optional[str]]:
        """
        压缩上下文
        
        Args:
            db: 数据库会话
            conversation: 对话对象
            history_messages: 历史消息列表（已按时间排序）
            system_prompt: 系统提示词
            
        Returns:
            (压缩后的消息列表, 新生成的摘要或None)
        """
        if not history_messages:
            return [ChatMessage(role=MESSAGE_ROLE_SYSTEM, content=system_prompt)], None

        # 计算当前 Token 数
        current_tokens = self._estimate_total_tokens(history_messages, system_prompt)
        
        logger.debug(f"当前对话 Token 估算: {current_tokens}, 阈值: {self.SUMMARIZE_THRESHOLD}")

        # 如果 Token 数在阈值内，直接返回完整历史
        if current_tokens < self.SUMMARIZE_THRESHOLD:
            messages = [ChatMessage(role=MESSAGE_ROLE_SYSTEM, content=system_prompt)]
            messages.extend(self._convert_to_chat_messages(history_messages))
            return messages, None

        # 需要压缩：保留最近的消息，老消息用摘要替代
        return await self._compress_with_summary(
            db, conversation, history_messages, system_prompt
        )

    def _estimate_total_tokens(
        self, 
        messages: List[AIMessage], 
        system_prompt: str
    ) -> int:
        """估算总 Token 数"""
        total = int(len(system_prompt) * self.AVG_TOKEN_PER_CHAR)
        for msg in messages:
            total += self.estimate_tokens_for_message(msg)
        return total

    def _convert_to_chat_messages(self, messages: List[AIMessage]) -> List[ChatMessage]:
        """将 AIMessage 转换为 ChatMessage"""
        result = []
        for msg in messages:
            if msg.role == MESSAGE_ROLE_TOOL:
                result.append(ChatMessage(
                    role=MESSAGE_ROLE_TOOL,
                    content=msg.content or "",
                    tool_call_id=msg.tool_call_id,
                    name=msg.tool_name,
                ))
            else:
                result.append(ChatMessage(
                    role=msg.role,
                    content=msg.content or ""
                ))
        return result

    async def _compress_with_summary(
        self,
        db: AsyncSession,
        conversation: AIConversation,
        history_messages: List[AIMessage],
        system_prompt: str,
    ) -> Tuple[List[ChatMessage], Optional[str]]:
        """
        使用摘要压缩上下文
        
        策略：
        1. 保留最近 keep_recent 条完整消息
        2. 将更早的消息生成摘要
        3. 如果已有摘要，合并到系统提示词
        """
        # 分割消息：保留的 + 需要摘要的
        if len(history_messages) <= self.keep_recent:
            # 消息太少，直接返回
            messages = [ChatMessage(role=MESSAGE_ROLE_SYSTEM, content=system_prompt)]
            messages.extend(self._convert_to_chat_messages(history_messages))
            return messages, conversation.context_summary

        messages_to_summarize = history_messages[:-self.keep_recent]
        recent_messages = history_messages[-self.keep_recent:]

        # 生成摘要
        new_summary = await self._generate_summary(db, messages_to_summarize, conversation.context_summary)

        # 构建压缩后的消息列表
        compressed_messages = []
        
        # 系统提示词 + 摘要
        enhanced_system = system_prompt
        if new_summary:
            enhanced_system += f"\n\n[对话历史摘要]\n{new_summary}"
        
        compressed_messages.append(ChatMessage(
            role=MESSAGE_ROLE_SYSTEM,
            content=enhanced_system
        ))

        # 添加保留的最近消息
        compressed_messages.extend(self._convert_to_chat_messages(recent_messages))

        # 估算压缩后的 Token 数
        compressed_tokens = self.estimate_tokens(compressed_messages)
        logger.info(
            f"上下文已压缩: {len(history_messages)} 条 -> {len(compressed_messages)} 条, "
            f"Token: ~{compressed_tokens}"
        )

        return compressed_messages, new_summary

    async def _generate_summary(
        self,
        db: AsyncSession,
        messages: List[AIMessage],
        existing_summary: Optional[str],
    ) -> str:
        """
        生成对话摘要
        
        使用 LLM 生成摘要，保留关键信息：
        - 用户的主要意图和需求
        - 已执行的工具调用和结果
        - 重要的上下文信息
        """
        try:
            # 构建摘要请求的 prompt
            summary_prompt = self._build_summary_prompt(messages, existing_summary)
            
            # 获取 LLM 适配器（使用轻量级配置）
            adapter = get_llm_adapter(
                self.config.provider,
                {
                    "api_key": self.config.api_key,
                    "api_base": self.config.api_base,
                    "proxy": self.config.proxy,
                    "model": self.config.model,
                    "temperature": 0.3,  # 低温度，更稳定的摘要
                    "max_tokens": 500,   # 摘要长度限制
                    "top_p": 0.9,
                }
            )

            chat_messages = [ChatMessage(role=MESSAGE_ROLE_USER, content=summary_prompt)]
            response = await adapter.chat(messages=chat_messages)
            
            summary = response.content or ""
            summary = summary.strip()
            
            # 如果已有摘要，合并（限制总长度）
            if existing_summary:
                combined = f"{existing_summary}\n{summary}"
                # 限制摘要总长度，避免无限增长
                max_summary_chars = 2000
                if len(combined) > max_summary_chars:
                    combined = combined[-max_summary_chars:]
                summary = combined
            
            return summary

        except Exception as e:
            logger.exception("生成摘要失败")
            # 失败时返回简单的时间线摘要
            return self._fallback_summary(messages, existing_summary)

    def _build_summary_prompt(
        self, 
        messages: List[AIMessage],
        existing_summary: Optional[str],
    ) -> str:
        """构建摘要生成的 prompt"""
        # 将消息转换为文本格式
        message_text = []
        for msg in messages:
            role_display = {
                MESSAGE_ROLE_USER: "用户",
                MESSAGE_ROLE_ASSISTANT: "助手",
                MESSAGE_ROLE_TOOL: "工具",
            }.get(msg.role, msg.role)
            
            content = msg.content or ""
            # 截断过长的内容
            if len(content) > 500:
                content = content[:500] + "..."
            
            if msg.role == MESSAGE_ROLE_TOOL:
                message_text.append(f"[{role_display}:{msg.tool_name}] {content}")
            else:
                message_text.append(f"[{role_display}] {content}")

        full_text = "\n".join(message_text)
        
        prompt = f"""请对以下对话历史生成简洁的摘要（不超过200字），保留关键信息：

对话内容：
{full_text}
"""
        if existing_summary:
            prompt += f"\n已有摘要（请在此基础上补充）：\n{existing_summary}\n"

        prompt += """
请生成摘要，包含：
1. 用户的主要请求和意图
2. 已执行的关键操作和结果
3. 当前进展和待办事项（如有）

摘要："""
        return prompt

    def _fallback_summary(
        self, 
        messages: List[AIMessage],
        existing_summary: Optional[str],
    ) -> str:
        """降级方案：简单的时间线摘要"""
        user_msgs = [m for m in messages if m.role == MESSAGE_ROLE_USER]
        tool_msgs = [m for m in messages if m.role == MESSAGE_ROLE_TOOL]
        
        summary_parts = []
        if existing_summary:
            summary_parts.append(existing_summary)
        
        if user_msgs:
            topics = [m.content[:50] + "..." for m in user_msgs[-3:] if m.content]
            summary_parts.append(f"近期话题: {', '.join(topics)}")
        
        if tool_msgs:
            tool_names = set(m.tool_name for m in tool_msgs if m.tool_name)
            summary_parts.append(f"已使用工具: {', '.join(tool_names)}")
        
        return "\n".join(summary_parts) if summary_parts else "对话历史"


class ContextManager:
    """
    上下文管理器
    
    高层封装，便于在 AgentService 中使用
    """

    @staticmethod
    async def build_messages(
        db: AsyncSession,
        conversation: AIConversation,
        history_messages: List[AIMessage],
        config: AIAgentConfig,
        system_prompt: str,
        enable_compression: bool = True,
    ) -> Tuple[List[ChatMessage], Optional[str]]:
        """
        构建消息列表（带上下文压缩）
        
        Returns:
            (消息列表, 新摘要或None)
        """
        if not enable_compression:
            # 不压缩，直接转换
            messages = [ChatMessage(role=MESSAGE_ROLE_SYSTEM, content=system_prompt)]
            for msg in history_messages:
                if msg.role == MESSAGE_ROLE_TOOL:
                    messages.append(ChatMessage(
                        role=MESSAGE_ROLE_TOOL,
                        content=msg.content or "",
                        tool_call_id=msg.tool_call_id,
                        name=msg.tool_name,
                    ))
                else:
                    messages.append(ChatMessage(
                        role=msg.role,
                        content=msg.content or ""
                    ))
            return messages, None

        # 使用压缩器
        compressor = ContextCompressor(config)
        return await compressor.compress_context(
            db, conversation, history_messages, system_prompt
        )

    @staticmethod
    async def update_conversation_summary(
        db: AsyncSession,
        conversation: AIConversation,
        new_summary: Optional[str],
    ):
        """更新对话的上下文摘要"""
        if new_summary and new_summary != conversation.context_summary:
            conversation.context_summary = new_summary
            await db.commit()
            logger.debug(f"已更新对话 {conversation.id} 的上下文摘要")
