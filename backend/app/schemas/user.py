"""
用户相关Schemas
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


# ========== 用户基础Schema ==========
class UserBase(BaseModel):
    """用户基础信息"""

    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: Optional[EmailStr] = Field(None, description="邮箱")
    display_name: Optional[str] = Field(None, max_length=100, description="显示名称")
    avatar_url: Optional[str] = Field(None, description="头像URL")
    timezone: str = Field(default="UTC", description="时区")
    language: str = Field(default="zh-CN", description="语言")


class UserCreate(UserBase):
    """创建用户"""

    password: str = Field(..., min_length=6, max_length=128, description="密码")
    role: Optional[str] = Field(default="user", description="角色: admin/user")

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """验证密码强度"""
        if len(v) < 6:
            raise ValueError("密码长度至少6个字符")
        if len(v) > 128:
            raise ValueError("密码长度不能超过128个字符")
        return v

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        """验证角色"""
        if v not in ["admin", "user"]:
            raise ValueError("角色只能是admin或user")
        return v


class UserUpdate(BaseModel):
    """更新用户信息"""

    email: Optional[EmailStr] = None
    display_name: Optional[str] = Field(None, max_length=100)
    avatar_url: Optional[str] = None
    timezone: Optional[str] = None
    language: Optional[str] = None
    is_active: Optional[bool] = None


class UserChangePassword(BaseModel):
    """修改密码"""

    old_password: str = Field(..., description="旧密码")
    new_password: str = Field(..., min_length=6, max_length=128, description="新密码")

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """验证密码强度"""
        if len(v) < 6:
            raise ValueError("密码长度至少6个字符")
        return v


class UserResponse(UserBase):
    """用户响应"""

    id: int
    role: str
    is_active: bool
    is_verified: bool
    last_login_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """用户列表响应"""

    items: list[UserResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ========== 用户配置Schema ==========
class UserProfileBase(BaseModel):
    """用户配置基础信息"""

    ui_theme: str = Field(default="auto", description="界面主题")
    language: str = Field(default="zh-CN", description="语言")
    timezone: str = Field(default="UTC", description="时区")
    items_per_page: int = Field(default=50, ge=10, le=200, description="每页显示数量")


class UserProfileUpdate(BaseModel):
    """更新用户配置"""

    ui_theme: Optional[str] = Field(None, description="界面主题: light/dark/auto")
    language: Optional[str] = None
    timezone: Optional[str] = None
    items_per_page: Optional[int] = Field(None, ge=10, le=200)
    min_seeders: Optional[int] = Field(None, ge=0)
    max_auto_download_size_gb: Optional[int] = Field(None, ge=0)
    default_downloader: Optional[str] = None
    auto_start_download: Optional[bool] = None
    download_path_template: Optional[str] = None
    notification_enabled: Optional[bool] = None
    email_notifications: Optional[bool] = None
    push_notifications: Optional[bool] = None
    ai_recommendations_enabled: Optional[bool] = None
    recommendation_frequency: Optional[str] = None
    share_anonymous_stats: Optional[bool] = None
    public_watchlist: Optional[bool] = None


class UserProfileResponse(UserProfileBase):
    """用户配置响应"""

    id: int
    user_id: int
    min_seeders: int
    max_auto_download_size_gb: Optional[int]
    default_downloader: Optional[str]
    auto_start_download: bool
    download_path_template: Optional[str]
    notification_enabled: bool
    email_notifications: bool
    push_notifications: bool
    ai_recommendations_enabled: bool
    recommendation_frequency: str
    share_anonymous_stats: bool
    public_watchlist: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ========== 用户及配置Schema ==========
class UserWithProfile(UserResponse):
    """用户及其配置信息"""

    profile: Optional[UserProfileResponse] = None

    class Config:
        from_attributes = True


# ========== 认证Schema ==========
class UserLogin(BaseModel):
    """用户登录"""

    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class Token(BaseModel):
    """JWT Token"""

    access_token: str
    token_type: str = "bearer"
    expires_in: int  # 秒
    refresh_token: Optional[str] = None  # 刷新令牌


class RefreshTokenRequest(BaseModel):
    """刷新令牌请求"""

    refresh_token: str = Field(..., description="刷新令牌")


class TokenData(BaseModel):
    """Token数据"""

    user_id: Optional[int] = None
    username: Optional[str] = None
    role: Optional[str] = None
