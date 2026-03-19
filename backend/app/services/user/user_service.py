"""
用户服务层
"""
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User, UserProfile
from app.schemas.user import UserCreate, UserProfileUpdate, UserUpdate
from app.utils.security import get_password_hash, verify_password
from app.utils.timezone import now


class UserService:
    """用户服务"""

    @staticmethod
    async def get_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
        """通过ID获取用户"""
        result = await db.execute(
            select(User).where(User.id == user_id).options(selectinload(User.profile))
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_username(db: AsyncSession, username: str) -> Optional[User]:
        """通过用户名获取用户"""
        result = await db.execute(
            select(User).where(User.username == username).options(selectinload(User.profile))
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_email(db: AsyncSession, email: str) -> Optional[User]:
        """通过邮箱获取用户"""
        result = await db.execute(
            select(User).where(User.email == email).options(selectinload(User.profile))
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_list(
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        role: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> tuple[list[User], int]:
        """
        获取用户列表

        Args:
            db: 数据库会话
            page: 页码
            page_size: 每页数量
            role: 角色过滤
            is_active: 激活状态过滤

        Returns:
            tuple: (用户列表, 总数)
        """
        from sqlalchemy import func

        # 构建查询
        query = select(User).options(selectinload(User.profile))

        # 应用过滤器
        if role:
            query = query.where(User.role == role)
        if is_active is not None:
            query = query.where(User.is_active == is_active)

        # 获取总数
        count_query = select(func.count(User.id))
        if role:
            count_query = count_query.where(User.role == role)
        if is_active is not None:
            count_query = count_query.where(User.is_active == is_active)

        result = await db.execute(count_query)
        total = result.scalar_one()

        # 分页
        query = query.order_by(User.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        users = result.scalars().all()

        return list(users), total

    @staticmethod
    async def create_user(db: AsyncSession, user_data: UserCreate) -> User:
        """
        创建用户

        Args:
            db: 数据库会话
            user_data: 用户创建数据

        Returns:
            User: 创建的用户

        Raises:
            ValueError: 用户名或邮箱已存在
        """
        # 检查用户名是否存在
        existing_user = await UserService.get_by_username(db, user_data.username)
        if existing_user:
            raise ValueError(f"用户名 '{user_data.username}' 已存在")

        # 检查邮箱是否存在
        if user_data.email:
            existing_email = await UserService.get_by_email(db, user_data.email)
            if existing_email:
                raise ValueError(f"邮箱 '{user_data.email}' 已被使用")

        # 创建用户
        user = User(
            username=user_data.username,
            email=user_data.email,
            password_hash=get_password_hash(user_data.password),
            role=user_data.role or "user",
            display_name=user_data.display_name or user_data.username,
            avatar_url=user_data.avatar_url,
            timezone=user_data.timezone,
            language=user_data.language,
            is_active=True,
            is_verified=False,
            password_changed_at=now(),
        )

        db.add(user)
        await db.flush()  # 刷新以获取user.id

        # 创建用户配置
        profile = UserProfile(
            user_id=user.id,
            ui_theme="auto",
            language=user_data.language,
            timezone=user_data.timezone,
        )
        db.add(profile)

        await db.commit()
        await db.refresh(user)

        return user

    # 登录安全默认配置
    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_DURATION_MINUTES = 30

    @staticmethod
    async def authenticate(
        db: AsyncSession, username: str, password: str
    ) -> tuple[Optional[User], Optional[str], Optional[dict]]:
        """
        验证用户登录

        Args:
            db: 数据库会话
            username: 用户名
            password: 密码

        Returns:
            tuple: (用户对象, 错误码, 额外信息)
                - 成功: (user, None, None)
                - 失败: (None, error_code, detail_info)
                  error_code:
                    - "user_not_found": 用户不存在
                    - "account_locked": 账户已锁定
                    - "wrong_password": 密码错误
                    - "account_disabled": 账户已禁用
        """
        user = await UserService.get_by_username(db, username)
        if not user:
            return None, "user_not_found", None

        # 检查账户是否激活
        if not user.is_active:
            return None, "account_disabled", None

        # 检查是否被锁定
        if user.is_locked:
            remaining_seconds = int((user.locked_until - now()).total_seconds())
            return None, "account_locked", {
                "locked_until": user.locked_until.isoformat(),
                "remaining_seconds": max(remaining_seconds, 0),
            }

        # 验证密码
        if not verify_password(password, user.password_hash):
            # 增加登录尝试次数
            user.login_attempts += 1
            remaining_attempts = max(UserService.MAX_LOGIN_ATTEMPTS - user.login_attempts, 0)

            if user.login_attempts >= UserService.MAX_LOGIN_ATTEMPTS:
                # 锁定账户
                user.locked_until = now() + timedelta(minutes=UserService.LOCKOUT_DURATION_MINUTES)
                await db.commit()
                return None, "account_locked", {
                    "locked_until": user.locked_until.isoformat(),
                    "remaining_seconds": UserService.LOCKOUT_DURATION_MINUTES * 60,
                }

            await db.commit()
            return None, "wrong_password", {
                "remaining_attempts": remaining_attempts,
            }

        # 登录成功，重置登录尝试次数
        user.login_attempts = 0
        user.last_login_at = now()
        user.locked_until = None
        await db.commit()

        return user, None, None

    @staticmethod
    async def update_user(db: AsyncSession, user_id: int, user_data: UserUpdate) -> Optional[User]:
        """更新用户信息"""
        user = await UserService.get_by_id(db, user_id)
        if not user:
            return None

        # 更新字段
        update_data = user_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)

        await db.commit()
        await db.refresh(user)

        return user

    @staticmethod
    async def change_password(
        db: AsyncSession, user_id: int, old_password: str, new_password: str
    ) -> bool:
        """
        修改密码

        Args:
            db: 数据库会话
            user_id: 用户ID
            old_password: 旧密码
            new_password: 新密码

        Returns:
            bool: 是否成功
        """
        user = await UserService.get_by_id(db, user_id)
        if not user:
            return False

        # 验证旧密码
        if not verify_password(old_password, user.password_hash):
            return False

        # 更新密码
        user.password_hash = get_password_hash(new_password)
        user.password_changed_at = now()

        await db.commit()
        return True

    @staticmethod
    async def update_profile(
        db: AsyncSession, user_id: int, profile_data: UserProfileUpdate
    ) -> Optional[UserProfile]:
        """更新用户配置"""
        # 获取用户配置
        result = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
        profile = result.scalar_one_or_none()

        if not profile:
            return None

        # 更新字段
        update_data = profile_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(profile, field, value)

        await db.commit()
        await db.refresh(profile)

        return profile

    @staticmethod
    async def get_user_count(db: AsyncSession) -> int:
        """获取用户总数"""
        from sqlalchemy import func

        result = await db.execute(select(func.count(User.id)))
        return result.scalar_one()

    @staticmethod
    async def is_first_user(db: AsyncSession) -> bool:
        """判断是否是第一个用户（用于初始化管理员）"""
        count = await UserService.get_user_count(db)
        return count == 0

    @staticmethod
    async def delete_user(db: AsyncSession, user_id: int) -> bool:
        """
        删除用户

        Args:
            db: 数据库会话
            user_id: 用户ID

        Returns:
            bool: 是否成功
        """
        user = await UserService.get_by_id(db, user_id)
        if not user:
            return False

        # 删除用户配置
        if user.profile:
            await db.delete(user.profile)

        # 删除用户
        await db.delete(user)
        await db.commit()

        return True
