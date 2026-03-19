"""
认证相关API
"""
import logging
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.schemas.user import RefreshTokenRequest, Token, UserLogin, UserResponse, UserWithProfile
from app.services.user.login_history_service import (
    LOGIN_STATUS_FAILED,
    LOGIN_STATUS_LOCKED,
    LOGIN_STATUS_SUCCESS,
    LoginHistoryService,
)
from app.services.user.user_service import UserService
from app.utils.security import create_access_token, create_refresh_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["认证"])


def _get_client_ip(request: Request) -> str:
    """从请求中获取客户端真实 IP（支持反向代理）"""
    # 优先从 X-Forwarded-For 获取
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    # 其次 X-Real-IP
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    # 最后使用直连 IP
    if request.client:
        return request.client.host
    return ""


@router.post("/login", response_model=Token, summary="用户登录")
async def login(
    login_data: UserLogin,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    用户登录

    - **username**: 用户名
    - **password**: 密码

    返回JWT访问令牌

    错误响应 detail 格式:
    - 密码错误: {"message": "...", "code": "wrong_password", "remaining_attempts": N}
    - 账户锁定: {"message": "...", "code": "account_locked", "remaining_seconds": N}
    - 账户禁用: {"message": "...", "code": "account_disabled"}
    """
    client_ip = _get_client_ip(request)
    user_agent = request.headers.get("User-Agent", "")

    # 验证用户
    user, error_code, error_detail = await UserService.authenticate(
        db, login_data.username, login_data.password
    )

    if error_code:
        # 构建错误响应
        error_messages = {
            "user_not_found": "用户名或密码错误",
            "wrong_password": "用户名或密码错误",
            "account_locked": "账户已被锁定，请稍后再试",
            "account_disabled": "用户已被禁用",
        }
        detail = {
            "message": error_messages.get(error_code, "登录失败"),
            "code": error_code,
        }
        if error_detail:
            detail.update(error_detail)

        # 对于 user_not_found 不暴露用户是否存在（统一为 wrong_password）
        if error_code == "user_not_found":
            detail["code"] = "wrong_password"

        # 记录登录失败历史
        # 对于 user_not_found, 需要通过 username 查找 user_id
        record_user_id = None
        if error_code == "user_not_found":
            # 用户不存在时不记录（避免注入垃圾数据）
            pass
        else:
            # 用户存在但登录失败，需要重新获取用户 ID
            existing_user = await UserService.get_by_username(db, login_data.username)
            if existing_user:
                record_user_id = existing_user.id
                login_status = LOGIN_STATUS_LOCKED if error_code == "account_locked" else LOGIN_STATUS_FAILED
                await LoginHistoryService.record_login(
                    db=db,
                    user_id=record_user_id,
                    ip_address=client_ip,
                    user_agent=user_agent,
                    login_status=login_status,
                    failure_reason=error_messages.get(error_code, "登录失败"),
                )
                await db.commit()

        status_code = (
            status.HTTP_403_FORBIDDEN
            if error_code in ("account_locked", "account_disabled")
            else status.HTTP_401_UNAUTHORIZED
        )
        raise HTTPException(
            status_code=status_code,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"} if status_code == 401 else None,
        )

    # 登录成功，记录历史
    await LoginHistoryService.record_login(
        db=db,
        user_id=user.id,
        ip_address=client_ip,
        user_agent=user_agent,
        login_status=LOGIN_STATUS_SUCCESS,
    )
    await db.commit()

    # 生成JWT token
    access_token_expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id), "username": user.username, "role": user.role},
        expires_delta=access_token_expires,
    )

    # 生成刷新令牌
    refresh_token_expires = timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    refresh_token = create_refresh_token(
        data={"sub": str(user.id)},
        expires_delta=refresh_token_expires,
    )

    token_data = Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        refresh_token=refresh_token,
    )
    return token_data


@router.get("/me", response_model=UserWithProfile, summary="获取当前用户信息")
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user),
):
    """
    获取当前登录用户的详细信息
    """
    return current_user


@router.post("/refresh", response_model=Token, summary="刷新令牌")
async def refresh_token(
    request_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    刷新访问令牌

    使用刷新令牌获取新的访问令牌和刷新令牌
    """
    from app.utils.security import decode_access_token

    # 解码刷新令牌
    payload = decode_access_token(request_data.refresh_token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的刷新令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 验证令牌类型
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌类型错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 获取用户ID
    user_id_str = payload.get("sub")
    if user_id_str is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的刷新令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的刷新令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 从数据库获取用户
    user = await UserService.get_by_id(db, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在或已被禁用",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 生成新的访问令牌
    access_token_expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id), "username": user.username, "role": user.role},
        expires_delta=access_token_expires,
    )

    # 生成新的刷新令牌
    refresh_token_expires = timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    new_refresh_token = create_refresh_token(
        data={"sub": str(user.id)},
        expires_delta=refresh_token_expires,
    )

    token_data = Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        refresh_token=new_refresh_token,
    )
    return token_data


@router.post("/send-verification-email", summary="发送邮箱验证邮件")
async def send_verification_email(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    向用户邮箱发送验证邮件

    注意：需要配置SMTP邮件服务才能使用此功能
    """
    if not current_user.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户未设置邮箱",
        )

    if current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已验证",
        )

    # TODO: 实现邮件发送逻辑
    # 1. 生成验证令牌
    # 2. 保存到数据库或缓存
    # 3. 发送包含验证链接的邮件
    # 示例：verification_token = create_verification_token(current_user.id)
    # 发送邮件：await send_email(to=current_user.email, subject="邮箱验证", body=f"验证链接: {verification_url}")

    return {
        "message": "验证邮件已发送（功能待实现：需要配置SMTP邮件服务）",
    }


@router.post("/verify-email", summary="验证邮箱")
async def verify_email(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """
    通过验证令牌验证用户邮箱

    - **token**: 邮件中的验证令牌
    """
    # TODO: 实现邮箱验证逻辑
    # 1. 验证令牌有效性
    # 2. 获取用户ID
    # 3. 更新用户验证状态
    # user_id = verify_token(token)
    # user = await UserService.get_by_id(db, user_id)
    # user.is_verified = True
    # await db.commit()

    return {
        "message": "邮箱验证成功（功能待实现）",
    }


@router.post("/request-password-reset", summary="请求密码重置")
async def request_password_reset(
    email: str,
    db: AsyncSession = Depends(get_db),
):
    """
    请求密码重置

    发送密码重置邮件到用户邮箱

    - **email**: 用户邮箱
    """
    # 查找用户
    user = await UserService.get_by_email(db, email)
    if not user:
        # 为了安全，即使用户不存在也返回成功信息
        return {
            "message": "如果该邮箱已注册，密码重置邮件将发送到该邮箱",
        }

    # TODO: 实现密码重置邮件发送逻辑
    # 1. 生成重置令牌
    # 2. 保存到数据库或缓存（设置过期时间，例如1小时）
    # 3. 发送包含重置链接的邮件
    # reset_token = create_password_reset_token(user.id)
    # await send_email(to=email, subject="密码重置", body=f"重置链接: {reset_url}")

    return {
        "message": "如果该邮箱已注册，密码重置邮件将发送到该邮箱（功能待实现：需要配置SMTP邮件服务）",
    }


@router.post("/reset-password", summary="重置密码")
async def reset_password(
    token: str,
    new_password: str,
    db: AsyncSession = Depends(get_db),
):
    """
    使用重置令牌重置密码

    - **token**: 密码重置令牌
    - **new_password**: 新密码
    """
    # TODO: 实现密码重置逻辑
    # 1. 验证令牌有效性和是否过期
    # 2. 获取用户ID
    # 3. 更新用户密码
    # user_id = verify_password_reset_token(token)
    # if not user_id:
    #     raise HTTPException(status_code=400, detail="令牌无效或已过期")
    # user = await UserService.get_by_id(db, user_id)
    # user.password_hash = get_password_hash(new_password)
    # user.password_changed_at = datetime.utcnow()
    # await db.commit()

    return {
        "message": "密码重置成功（功能待实现）",
    }
