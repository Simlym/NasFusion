"""
登录历史服务层
"""
import logging
from typing import Optional

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.login_history import LoginHistory
from app.utils.ip_location import get_ip_location
from app.utils.timezone import now

logger = logging.getLogger(__name__)

# 登录状态常量
LOGIN_STATUS_SUCCESS = "success"
LOGIN_STATUS_FAILED = "failed"
LOGIN_STATUS_LOCKED = "locked"


class LoginHistoryService:
    """登录历史服务"""

    @staticmethod
    async def record_login(
        db: AsyncSession,
        user_id: int,
        ip_address: Optional[str],
        user_agent: Optional[str],
        login_status: str,
        failure_reason: Optional[str] = None,
    ) -> LoginHistory:
        """
        记录登录历史

        Args:
            db: 数据库会话
            user_id: 用户ID
            ip_address: 登录IP
            user_agent: 浏览器User-Agent
            login_status: 登录状态 (success/failed/locked)
            failure_reason: 失败原因

        Returns:
            LoginHistory: 创建的登录记录
        """
        # 异步获取 IP 地理位置
        location = None
        try:
            location = await get_ip_location(ip_address)
        except Exception as e:
            logger.debug(f"获取IP地理位置失败: {e}")

        record = LoginHistory(
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            location=location,
            login_status=login_status,
            failure_reason=failure_reason,
            login_at=now(),
        )
        db.add(record)
        await db.flush()
        return record

    @staticmethod
    async def get_user_login_history(
        db: AsyncSession,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
        status_filter: Optional[str] = None,
    ) -> tuple[list[LoginHistory], int]:
        """
        获取用户的登录历史

        Args:
            db: 数据库会话
            user_id: 用户ID
            page: 页码
            page_size: 每页数量
            status_filter: 按状态过滤

        Returns:
            tuple: (登录记录列表, 总数)
        """
        query = select(LoginHistory).where(LoginHistory.user_id == user_id)
        count_query = select(func.count(LoginHistory.id)).where(LoginHistory.user_id == user_id)

        if status_filter:
            query = query.where(LoginHistory.login_status == status_filter)
            count_query = count_query.where(LoginHistory.login_status == status_filter)

        # 获取总数
        result = await db.execute(count_query)
        total = result.scalar_one()

        # 分页查询（按时间倒序）
        query = query.order_by(LoginHistory.login_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        records = result.scalars().all()

        return list(records), total

    @staticmethod
    async def get_all_login_history(
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        user_id: Optional[int] = None,
        status_filter: Optional[str] = None,
    ) -> tuple[list[LoginHistory], int]:
        """
        获取所有用户的登录历史（管理员）

        Args:
            db: 数据库会话
            page: 页码
            page_size: 每页数量
            user_id: 按用户ID过滤
            status_filter: 按状态过滤

        Returns:
            tuple: (登录记录列表, 总数)
        """
        from app.models.user import User

        query = select(LoginHistory)
        count_query = select(func.count(LoginHistory.id))

        if user_id:
            query = query.where(LoginHistory.user_id == user_id)
            count_query = count_query.where(LoginHistory.user_id == user_id)

        if status_filter:
            query = query.where(LoginHistory.login_status == status_filter)
            count_query = count_query.where(LoginHistory.login_status == status_filter)

        # 获取总数
        result = await db.execute(count_query)
        total = result.scalar_one()

        # 分页查询（按时间倒序）
        query = query.order_by(LoginHistory.login_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        records = result.scalars().all()

        return list(records), total

    @staticmethod
    async def cleanup_old_records(db: AsyncSession, keep_days: int = 90) -> int:
        """
        清理超过指定天数的旧登录记录

        Args:
            db: 数据库会话
            keep_days: 保留天数（默认90天）

        Returns:
            int: 删除的记录数
        """
        from datetime import timedelta

        cutoff_time = now() - timedelta(days=keep_days)

        result = await db.execute(
            delete(LoginHistory).where(LoginHistory.login_at < cutoff_time)
        )
        await db.commit()
        return result.rowcount
