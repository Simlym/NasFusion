# -*- coding: utf-8 -*-
"""
对话归档服务

自动归档长时间未活动的对话，释放资源并保持数据库性能。

归档策略：
1. 基于时间的归档：超过 X 天未活动的对话自动归档
2. 基于消息数量的归档：超过 X 条消息的对话自动归档
3. 手动归档：用户可以手动归档对话

归档后的对话：
- 状态变为 archived
- 可以被查看但不再参与上下文
- 可以恢复为 active
"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.ai_agent import (
    CONVERSATION_STATUS_ACTIVE,
    CONVERSATION_STATUS_ARCHIVED,
)
from app.models import AIConversation, AIMessage
from app.utils.timezone import now

logger = logging.getLogger(__name__)


class ConversationArchiveConfig:
    """归档配置"""
    
    # 默认配置
    DEFAULT_INACTIVE_DAYS = 7  # 7 天未活动自动归档
    DEFAULT_MAX_MESSAGES = 200  # 超过 200 条消息自动归档
    DEFAULT_MAX_ACTIVE_CONVERSATIONS = 50  # 最大活跃对话数


class ConversationArchiveService:
    """
    对话归档服务
    
    提供自动归档和手动归档功能。
    """

    @staticmethod
    async def archive_conversation(
        db: AsyncSession,
        conversation: AIConversation,
        reason: str = "manual",
    ) -> AIConversation:
        """
        归档单个对话
        
        Args:
            db: 数据库会话
            conversation: 要归档的对话
            reason: 归档原因（manual/auto_inactive/auto_max_messages）
            
        Returns:
            更新后的对话对象
        """
        if conversation.status == CONVERSATION_STATUS_ARCHIVED:
            logger.debug(f"对话 {conversation.id} 已经归档")
            return conversation

        conversation.status = CONVERSATION_STATUS_ARCHIVED
        await db.commit()
        
        logger.info(
            f"对话 {conversation.id} 已归档 (用户: {conversation.user_id}, "
            f"原因: {reason}, 消息数: {conversation.message_count})"
        )
        
        return conversation

    @staticmethod
    async def unarchive_conversation(
        db: AsyncSession,
        conversation: AIConversation,
    ) -> AIConversation:
        """
        恢复归档的对话
        
        Args:
            db: 数据库会话
            conversation: 要恢复的对话
            
        Returns:
            更新后的对话对象
        """
        if conversation.status == CONVERSATION_STATUS_ACTIVE:
            return conversation

        conversation.status = CONVERSATION_STATUS_ACTIVE
        await db.commit()
        
        logger.info(f"对话 {conversation.id} 已恢复为活跃状态")
        
        return conversation

    @staticmethod
    async def auto_archive_inactive(
        db: AsyncSession,
        inactive_days: int = None,
        user_id: Optional[int] = None,
    ) -> List[AIConversation]:
        """
        自动归档长时间未活动的对话
        
        Args:
            db: 数据库会话
            inactive_days: 未活动天数阈值（默认使用配置）
            user_id: 特定用户（None 表示所有用户）
            
        Returns:
            被归档的对话列表
        """
        if inactive_days is None:
            inactive_days = ConversationArchiveConfig.DEFAULT_INACTIVE_DAYS

        cutoff_date = now() - timedelta(days=inactive_days)
        
        # 查询符合条件的对话
        query = select(AIConversation).where(
            AIConversation.status == CONVERSATION_STATUS_ACTIVE,
            AIConversation.last_message_at < cutoff_date,
        )
        
        if user_id:
            query = query.where(AIConversation.user_id == user_id)
        
        result = await db.execute(query)
        conversations = result.scalars().all()
        
        archived = []
        for conv in conversations:
            await ConversationArchiveService.archive_conversation(
                db, conv, reason="auto_inactive"
            )
            archived.append(conv)
        
        if archived:
            logger.info(f"自动归档了 {len(archived)} 个不活跃对话（超过 {inactive_days} 天）")
        
        return archived

    @staticmethod
    async def auto_archive_by_message_count(
        db: AsyncSession,
        max_messages: int = None,
        user_id: Optional[int] = None,
    ) -> List[AIConversation]:
        """
        自动归档消息数过多的对话
        
        Args:
            db: 数据库会话
            max_messages: 最大消息数阈值（默认使用配置）
            user_id: 特定用户（None 表示所有用户）
            
        Returns:
            被归档的对话列表
        """
        if max_messages is None:
            max_messages = ConversationArchiveConfig.DEFAULT_MAX_MESSAGES

        # 查询符合条件的对话
        query = select(AIConversation).where(
            AIConversation.status == CONVERSATION_STATUS_ACTIVE,
            AIConversation.message_count > max_messages,
        )
        
        if user_id:
            query = query.where(AIConversation.user_id == user_id)
        
        result = await db.execute(query)
        conversations = result.scalars().all()
        
        archived = []
        for conv in conversations:
            await ConversationArchiveService.archive_conversation(
                db, conv, reason="auto_max_messages"
            )
            archived.append(conv)
        
        if archived:
            logger.info(f"自动归档了 {len(archived)} 个大容量对话（超过 {max_messages} 条消息）")
        
        return archived

    @staticmethod
    async def auto_archive_by_count_limit(
        db: AsyncSession,
        max_active: int = None,
        user_id: Optional[int] = None,
    ) -> List[AIConversation]:
        """
        当活跃对话数超过限制时，归档最老的对话
        
        Args:
            db: 数据库会话
            max_active: 最大活跃对话数（默认使用配置）
            user_id: 特定用户（None 表示所有用户）
            
        Returns:
            被归档的对话列表
        """
        if max_active is None:
            max_active = ConversationArchiveConfig.DEFAULT_MAX_ACTIVE_CONVERSATIONS

        # 统计活跃对话数
        count_query = select(func.count(AIConversation.id)).where(
            AIConversation.status == CONVERSATION_STATUS_ACTIVE
        )
        if user_id:
            count_query = count_query.where(AIConversation.user_id == user_id)
        
        active_count = await db.scalar(count_query) or 0
        
        if active_count <= max_active:
            return []

        # 需要归档的对话数
        to_archive_count = active_count - max_active
        
        # 查询最老的活跃对话
        query = select(AIConversation).where(
            AIConversation.status == CONVERSATION_STATUS_ACTIVE
        ).order_by(
            AIConversation.last_message_at.asc()  # 最久未更新的优先归档
        ).limit(to_archive_count)
        
        if user_id:
            query = query.where(AIConversation.user_id == user_id)
        
        result = await db.execute(query)
        conversations = result.scalars().all()
        
        archived = []
        for conv in conversations:
            await ConversationArchiveService.archive_conversation(
                db, conv, reason="auto_count_limit"
            )
            archived.append(conv)
        
        if archived:
            logger.info(f"自动归档了 {len(archived)} 个对话（超过最大活跃数 {max_active}）")
        
        return archived

    @staticmethod
    async def run_auto_archive(
        db: AsyncSession,
        user_id: Optional[int] = None,
    ) -> Dict:
        """
        运行完整的自动归档流程
        
        按优先级执行：
        1. 归档消息数过多的对话
        2. 归档长时间未活动的对话
        3. 如果仍超过数量限制，归档最老的对话
        
        Args:
            db: 数据库会话
            user_id: 特定用户（None 表示所有用户）
            
        Returns:
            归档统计信息
        """
        stats = {
            "archived_by_messages": [],
            "archived_by_inactive": [],
            "archived_by_count": [],
            "total_archived": 0,
        }

        # 1. 按消息数归档
        archived = await ConversationArchiveService.auto_archive_by_message_count(
            db, user_id=user_id
        )
        stats["archived_by_messages"] = [c.id for c in archived]
        stats["total_archived"] += len(archived)

        # 2. 按不活动时间归档
        archived = await ConversationArchiveService.auto_archive_inactive(
            db, user_id=user_id
        )
        stats["archived_by_inactive"] = [c.id for c in archived]
        stats["total_archived"] += len(archived)

        # 3. 按数量限制归档
        archived = await ConversationArchiveService.auto_archive_by_count_limit(
            db, user_id=user_id
        )
        stats["archived_by_count"] = [c.id for c in archived]
        stats["total_archived"] += len(archived)

        logger.info(f"自动归档完成: {stats['total_archived']} 个对话")
        return stats

    @staticmethod
    async def list_archived_conversations(
        db: AsyncSession,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[AIConversation], int]:
        """
        获取归档对话列表
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            page: 页码
            page_size: 每页数量
            
        Returns:
            (对话列表, 总数)
        """
        # 计数
        count_result = await db.execute(
            select(func.count(AIConversation.id)).where(
                AIConversation.user_id == user_id,
                AIConversation.status == CONVERSATION_STATUS_ARCHIVED,
            )
        )
        total = count_result.scalar() or 0

        # 查询
        query = select(AIConversation).where(
            AIConversation.user_id == user_id,
            AIConversation.status == CONVERSATION_STATUS_ARCHIVED,
        ).order_by(
            desc(AIConversation.last_message_at)
        ).offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        conversations = result.scalars().all()

        return list(conversations), total

    @staticmethod
    async def cleanup_deleted_conversations(
        db: AsyncSession,
        days_since_delete: int = 30,
    ) -> int:
        """
        清理已删除的对话（软删除后真正删除）
        
        Args:
            db: 数据库会话
            days_since_delete: 删除后保留的天数
            
        Returns:
            清理的对话数
        """
        from app.constants.ai_agent import CONVERSATION_STATUS_DELETED
        
        cutoff_date = now() - timedelta(days=days_since_delete)
        
        # 这里可以实现真正的物理删除
        # 由于有外键约束（消息关联对话），需要先删除消息
        # 暂时只记录日志
        
        query = select(AIConversation).where(
            AIConversation.status == CONVERSATION_STATUS_DELETED,
            AIConversation.updated_at < cutoff_date,
        )
        
        result = await db.execute(query)
        conversations = result.scalars().all()
        
        # TODO: 实现物理删除（先删消息，再删对话）
        
        count = len(conversations)
        if count > 0:
            logger.info(f"发现 {count} 个可清理的已删除对话（超过 {days_since_delete} 天）")
        
        return count


# 用于定时任务
async def auto_archive_task():
    """
    定时任务：自动归档对话
    
    可以在 APScheduler 中配置，例如每天凌晨运行。
    """
    from app.core.database import async_session_local
    
    async with async_session_local() as db:
        try:
            stats = await ConversationArchiveService.run_auto_archive(db)
            logger.info(f"自动归档任务完成: {stats}")
        except Exception as e:
            logger.exception("自动归档任务失败")
            raise
