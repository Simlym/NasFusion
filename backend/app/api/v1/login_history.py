"""
登录历史 API
"""
import math
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_active_user, get_current_admin_user
from app.models.user import User
from app.schemas.login_history import LoginHistoryListResponse, LoginHistoryResponse
from app.services.user.login_history_service import LoginHistoryService
from app.services.user.user_service import UserService

router = APIRouter(prefix="/login-history", tags=["登录历史"])


@router.get("/me", response_model=LoginHistoryListResponse, summary="获取当前用户的登录历史")
async def get_my_login_history(
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
    status: Optional[str] = Query(default=None, description="按状态过滤: success/failed/locked"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取当前登录用户的登录历史记录"""
    records, total = await LoginHistoryService.get_user_login_history(
        db=db,
        user_id=current_user.id,
        page=page,
        page_size=page_size,
        status_filter=status,
    )

    items = [
        LoginHistoryResponse(
            id=r.id,
            user_id=r.user_id,
            username=current_user.username,
            ip_address=r.ip_address,
            user_agent=r.user_agent,
            location=r.location,
            login_status=r.login_status,
            failure_reason=r.failure_reason,
            login_at=r.login_at,
            created_at=r.created_at,
        )
        for r in records
    ]

    return LoginHistoryListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0,
    )


@router.get("", response_model=LoginHistoryListResponse, summary="获取所有用户的登录历史（管理员）")
async def get_all_login_history(
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
    user_id: Optional[int] = Query(default=None, description="按用户ID过滤"),
    status: Optional[str] = Query(default=None, description="按状态过滤: success/failed/locked"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """获取所有用户的登录历史记录（仅管理员）"""
    records, total = await LoginHistoryService.get_all_login_history(
        db=db,
        page=page,
        page_size=page_size,
        user_id=user_id,
        status_filter=status,
    )

    # 批量获取用户名映射
    user_ids = {r.user_id for r in records}
    username_map = {}
    for uid in user_ids:
        u = await UserService.get_by_id(db, uid)
        if u:
            username_map[uid] = u.username

    items = [
        LoginHistoryResponse(
            id=r.id,
            user_id=r.user_id,
            username=username_map.get(r.user_id),
            ip_address=r.ip_address,
            user_agent=r.user_agent,
            location=r.location,
            login_status=r.login_status,
            failure_reason=r.failure_reason,
            login_at=r.login_at,
            created_at=r.created_at,
        )
        for r in records
    ]

    return LoginHistoryListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0,
    )


@router.delete("/cleanup", summary="清理旧登录记录（管理员）")
async def cleanup_login_history(
    keep_days: int = Query(default=90, ge=1, le=365, description="保留天数"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """清理超过指定天数的旧登录记录（仅管理员）"""
    deleted_count = await LoginHistoryService.cleanup_old_records(db, keep_days)
    return {"message": f"已清理 {deleted_count} 条旧登录记录", "deleted_count": deleted_count}
