"""
用户管理API
"""
import math
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_active_user, get_current_admin_user
from app.models.user import User
from app.schemas.user import (
    UserChangePassword,
    UserCreate,
    UserListResponse,
    UserProfileResponse,
    UserProfileUpdate,
    UserResponse,
    UserUpdate,
    UserWithProfile,
)
from app.services.user.user_service import UserService

router = APIRouter(prefix="/users", tags=["用户管理"])

# 配置上传目录
UPLOAD_DIR = Path("uploads/avatars")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


@router.get("", response_model=UserListResponse, summary="获取用户列表")
async def get_users(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    role: str = Query(None, description="角色过滤: admin/user"),
    is_active: bool = Query(None, description="是否激活"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    获取用户列表（仅管理员）

    - **page**: 页码（从1开始）
    - **page_size**: 每页数量（1-100）
    - **role**: 角色过滤（可选）
    - **is_active**: 激活状态过滤（可选）
    """
    users, total = await UserService.get_list(
        db, page=page, page_size=page_size, role=role, is_active=is_active
    )

    return UserListResponse(
        items=users,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0,
    )


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="创建用户")
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    创建新用户（仅管理员）

    - **username**: 用户名（3-50字符）
    - **password**: 密码（至少6字符）
    - **email**: 邮箱（可选）
    - **role**: 角色（admin/user，默认user）
    """
    try:
        user = await UserService.create_user(db, user_data)
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/me", response_model=UserWithProfile, summary="获取个人信息")
async def get_my_info(
    current_user: User = Depends(get_current_active_user),
):
    """
    获取当前登录用户的详细信息
    """
    return current_user


@router.put("/me", response_model=UserResponse, summary="更新个人信息")
async def update_my_info(
    user_data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    更新当前用户信息

    - **email**: 邮箱
    - **display_name**: 显示名称
    - **avatar_url**: 头像URL
    - **timezone**: 时区
    - **language**: 语言
    """
    user = await UserService.update_user(db, current_user.id, user_data)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )
    return user


@router.post("/me/change-password", summary="修改密码")
async def change_password(
    password_data: UserChangePassword,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    修改当前用户密码

    - **old_password**: 旧密码
    - **new_password**: 新密码（至少6字符）
    """
    success = await UserService.change_password(
        db, current_user.id, password_data.old_password, password_data.new_password
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="旧密码错误",
        )

    return {"message": "密码修改成功"}


@router.get("/me/profile", response_model=UserProfileResponse, summary="获取用户配置")
async def get_my_profile(
    current_user: User = Depends(get_current_active_user),
):
    """
    获取当前用户的配置信息
    """
    if not current_user.profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户配置不存在",
        )
    return current_user.profile


@router.put("/me/profile", response_model=UserProfileResponse, summary="更新用户配置")
async def update_my_profile(
    profile_data: UserProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    更新当前用户的配置信息

    - **ui_theme**: 界面主题（light/dark/auto）
    - **language**: 语言
    - **timezone**: 时区
    - **items_per_page**: 每页显示数量
    - 等等...
    """
    profile = await UserService.update_profile(db, current_user.id, profile_data)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户配置不存在",
        )
    return profile


@router.get("/{user_id}", response_model=UserResponse, summary="获取用户信息")
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    获取指定用户信息（仅管理员）
    """
    user = await UserService.get_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )
    return user


@router.put("/{user_id}", response_model=UserResponse, summary="更新用户信息")
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    更新指定用户信息（仅管理员）
    """
    user = await UserService.update_user(db, user_id, user_data)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除用户")
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    删除用户（仅管理员）

    注意：不能删除自己
    """
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能删除自己",
        )

    success = await UserService.delete_user(db, user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )
    return None


@router.post("/me/avatar", summary="上传头像")
async def upload_avatar(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    上传用户头像

    - 支持的格式：jpg, jpeg, png, gif, webp
    - 最大大小：5MB
    """
    # 检查文件扩展名
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的文件格式。支持的格式：{', '.join(ALLOWED_EXTENSIONS)}",
        )

    # 检查文件大小
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"文件大小超过限制（最大 {MAX_FILE_SIZE // 1024 // 1024}MB）",
        )

    # 生成唯一文件名
    filename = f"{current_user.id}_{uuid.uuid4().hex}{file_ext}"
    file_path = UPLOAD_DIR / filename

    # 保存文件
    try:
        with open(file_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"文件保存失败: {str(e)}",
        )

    # 更新用户头像URL
    avatar_url = f"/uploads/avatars/{filename}"
    user = await UserService.update_user(db, current_user.id, UserUpdate(avatar_url=avatar_url))

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    return {"avatar_url": avatar_url, "message": "头像上传成功"}
