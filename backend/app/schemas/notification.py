# -*- coding: utf-8 -*-
"""
通知系统 Pydantic Schemas
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer
from pydantic.alias_generators import to_camel

from app.schemas.base import BaseResponseSchema


# ============================================================================
# 站内消息通知 (Notification Internal)
# ============================================================================


class NotificationInternalBase(BaseModel):
    """站内通知基础 Schema"""

    notification_type: str = Field(..., description="通知类型")
    title: str = Field(..., max_length=200, description="通知标题")
    content: str = Field(..., description="通知内容")
    priority: str = Field(default="normal", description="优先级: low/normal/high/urgent")
    related_type: Optional[str] = Field(None, max_length=50, description="关联资源类型")
    related_id: Optional[int] = Field(None, description="关联资源ID")
    extra_data: Optional[Dict[str, Any]] = Field(None, description="扩展数据")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,  # 允许同时使用字段名和别名
        alias_generator=to_camel  # 自动将 snake_case 转换为 camelCase
    )


class NotificationInternalCreate(NotificationInternalBase):
    """创建站内通知"""

    user_id: Optional[int] = Field(None, description="用户ID，NULL表示系统广播")
    expires_at: Optional[datetime] = Field(None, description="过期时间")


class NotificationInternalUpdate(BaseModel):
    """更新站内通知"""

    status: Optional[str] = Field(None, description="状态: unread/read/archived")
    read_at: Optional[datetime] = Field(None, description="阅读时间")


class NotificationInternalResponse(BaseResponseSchema, NotificationInternalBase):
    """站内通知响应"""

    id: int
    user_id: Optional[int]
    status: str
    read_at: Optional[datetime]
    expires_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    @field_serializer('read_at', 'expires_at', when_used='json', check_fields=False)
    def serialize_datetime(self, dt: Optional[datetime], _info) -> Optional[str]:
        """序列化 datetime 为 ISO 8601 格式"""
        if dt is None:
            return None
        return dt.isoformat()

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,  # 允许同时使用字段名和别名
        alias_generator=to_camel  # 自动将 snake_case 转换为 camelCase
    )


class NotificationInternalListResponse(BaseModel):
    """站内通知列表响应"""

    total: int = Field(..., description="总数")
    items: List[NotificationInternalResponse] = Field(..., description="通知列表")
    unread_count: int = Field(default=0, description="未读数量")


# ============================================================================
# 通知渠道 (Notification Channel)
# ============================================================================


class NotificationChannelBase(BaseModel):
    """通知渠道基础 Schema"""

    name: str = Field(..., max_length=100, description="渠道名称")
    channel_type: str = Field(..., max_length=30, description="渠道类型: telegram/email/webhook")
    config: Dict[str, Any] = Field(..., description="渠道配置")
    enabled: bool = Field(default=True, description="是否启用")
    priority: int = Field(default=5, ge=1, le=10, description="渠道优先级")
    description: Optional[str] = Field(None, description="渠道描述")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,  # 允许同时使用字段名和别名
        alias_generator=to_camel  # 自动将 snake_case 转换为 camelCase
    )


class NotificationChannelCreate(NotificationChannelBase):
    """创建通知渠道"""

    user_id: Optional[int] = Field(None, description="用户ID，NULL表示系统级")


class NotificationChannelUpdate(BaseModel):
    """更新通知渠道"""

    name: Optional[str] = Field(None, max_length=100)
    config: Optional[Dict[str, Any]] = None
    enabled: Optional[bool] = None
    priority: Optional[int] = Field(None, ge=1, le=10)
    description: Optional[str] = None


class NotificationChannelResponse(BaseResponseSchema, NotificationChannelBase):
    """通知渠道响应"""

    id: int
    user_id: Optional[int]
    status: str
    last_test_at: Optional[datetime]
    last_test_result: Optional[str]
    last_success_at: Optional[datetime]
    consecutive_failures: int
    created_at: datetime
    updated_at: datetime

    @field_serializer('last_test_at', 'last_success_at', when_used='json', check_fields=False)
    def serialize_datetime(self, dt: Optional[datetime], _info) -> Optional[str]:
        """序列化 datetime 为 ISO 8601 格式"""
        if dt is None:
            return None
        return dt.isoformat()

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,  # 允许同时使用字段名和别名
        alias_generator=to_camel  # 自动将 snake_case 转换为 camelCase
    )


class NotificationChannelListResponse(BaseModel):
    """通知渠道列表响应"""

    total: int
    items: List[NotificationChannelResponse]


# ============================================================================
# 通知规则 (Notification Rule)
# ============================================================================


class NotificationRuleBase(BaseModel):
    """通知规则基础 Schema"""

    name: str = Field(..., max_length=100, description="规则名称")
    enabled: bool = Field(default=True, description="是否启用")
    event_type: str = Field(..., max_length=50, description="事件类型")
    conditions: Optional[Dict[str, Any]] = Field(None, description="触发条件")
    channel_ids: List[int] = Field(..., description="通知渠道ID列表")
    send_in_app: bool = Field(default=True, description="发送系统内通知")
    template_id: Optional[int] = Field(None, description="使用的模板ID")
    silent_hours: Optional[Dict[str, Any]] = Field(None, description="静默时段配置")
    deduplication_window: Optional[int] = Field(None, description="去重时间窗口(秒)")
    priority: int = Field(default=5, ge=1, le=10, description="规则优先级(1-10)")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,  # 允许同时使用字段名和别名
        alias_generator=to_camel  # 自动将 snake_case 转换为 camelCase
    )


class NotificationRuleCreate(NotificationRuleBase):
    """创建通知规则"""

    user_id: int = Field(..., description="用户ID")


class NotificationRuleUpdate(BaseModel):
    """更新通知规则"""

    name: Optional[str] = Field(None, max_length=100)
    enabled: Optional[bool] = None
    event_type: Optional[str] = Field(None, max_length=50)
    conditions: Optional[Dict[str, Any]] = None
    channel_ids: Optional[List[int]] = Field(None, alias="channelIds")
    send_in_app: Optional[bool] = None
    template_id: Optional[int] = None
    silent_hours: Optional[Dict[str, Any]] = None
    deduplication_window: Optional[int] = None
    priority: Optional[int] = Field(None, ge=1, le=10)

    model_config = ConfigDict(
        populate_by_name=True,  # 允许同时使用字段名和别名
    )


class NotificationRuleResponse(BaseResponseSchema, NotificationRuleBase):
    """通知规则响应"""

    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,  # 允许同时使用字段名和别名
        alias_generator=to_camel  # 自动将 snake_case 转换为 camelCase
    )


class NotificationRuleListResponse(BaseModel):
    """通知规则列表响应"""

    total: int
    items: List[NotificationRuleResponse]


# ============================================================================
# 通知模板 (Notification Template)
# ============================================================================


class NotificationTemplateBase(BaseModel):
    """通知模板基础 Schema"""

    event_type: str = Field(..., max_length=50, description="事件类型")
    name: str = Field(..., max_length=100, description="模板名称")
    language: str = Field(default="zh-CN", max_length=10, description="语言")
    format: str = Field(default="markdown", description="格式: markdown/html/text")
    title_template: str = Field(..., max_length=200, description="标题模板")
    content_template: str = Field(..., description="内容模板")
    variables: Optional[Dict[str, Any]] = Field(None, description="可用变量说明")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,  # 允许同时使用字段名和别名
        alias_generator=to_camel  # 自动将 snake_case 转换为 camelCase
    )


class NotificationTemplateCreate(NotificationTemplateBase):
    """创建通知模板"""

    user_id: Optional[int] = Field(None, description="用户ID，NULL表示系统模板")
    is_system: bool = Field(default=False, description="是否系统模板")


class NotificationTemplateUpdate(BaseModel):
    """更新通知模板"""

    name: Optional[str] = Field(None, max_length=100)
    language: Optional[str] = Field(None, max_length=10)
    format: Optional[str] = None
    title_template: Optional[str] = Field(None, max_length=200)
    content_template: Optional[str] = None
    variables: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,  # 允许同时使用字段名和别名
        alias_generator=to_camel  # 自动将 snake_case 转换为 camelCase
    )


class NotificationTemplateResponse(BaseResponseSchema, NotificationTemplateBase):
    """通知模板响应"""

    id: int
    user_id: Optional[int]
    is_system: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,  # 允许同时使用字段名和别名
        alias_generator=to_camel  # 自动将 snake_case 转换为 camelCase
    )


class NotificationTemplateListResponse(BaseModel):
    """通知模板列表响应"""

    total: int
    items: List[NotificationTemplateResponse]


# ============================================================================
# 站外通知日志 (Notification External)
# ============================================================================


class NotificationExternalBase(BaseModel):
    """站外通知基础 Schema"""

    notification_type: str = Field(..., max_length=50, description="通知类型")
    channel_id: Optional[int] = Field(None, description="通知渠道ID")
    channel_type: Optional[str] = Field(None, max_length=30, description="渠道类型")
    title: str = Field(..., max_length=200, description="通知标题")
    content: str = Field(..., description="通知内容")
    status: str = Field(..., description="状态: pending/sent/failed")
    retry_count: int = Field(default=0, description="重试次数")
    error_message: Optional[str] = Field(None, description="错误信息")
    sent_at: Optional[datetime] = Field(None, description="发送时间")
    response_data: Optional[Dict[str, Any]] = Field(None, description="渠道返回数据")
    extra_data: Optional[Dict[str, Any]] = Field(None, description="扩展数据")


class NotificationExternalCreate(NotificationExternalBase):
    """创建站外通知"""

    user_id: Optional[int] = Field(None, description="用户ID")


class NotificationExternalUpdate(BaseModel):
    """更新站外通知"""

    status: Optional[str] = None
    retry_count: Optional[int] = None
    error_message: Optional[str] = None
    sent_at: Optional[datetime] = None
    response_data: Optional[Dict[str, Any]] = None


class NotificationExternalResponse(BaseResponseSchema, NotificationExternalBase):
    """站外通知响应"""

    id: int
    user_id: Optional[int]
    created_at: datetime
    updated_at: datetime

    @field_serializer('sent_at', when_used='json', check_fields=False)
    def serialize_datetime(self, dt: Optional[datetime], _info) -> Optional[str]:
        """序列化 datetime 为 ISO 8601 格式"""
        if dt is None:
            return None
        return dt.isoformat()


class NotificationExternalListResponse(BaseModel):
    """站外通知列表响应"""

    total: int
    items: List[NotificationExternalResponse]


# ============================================================================
# 通知渠道 (扩展现有 NotificationChannel schemas)
# ============================================================================


class NotificationChannelTest(BaseModel):
    """测试通知渠道"""

    test_message: str = Field(default="测试消息", description="测试消息内容")


class NotificationChannelTestResponse(BaseModel):
    """测试通知渠道响应"""

    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="测试结果消息")
    response_data: Optional[Dict[str, Any]] = Field(None, description="渠道返回数据")


# ============================================================================
# 通用请求参数
# ============================================================================


class NotificationQuery(BaseModel):
    """通知查询参数"""

    skip: int = Field(default=0, ge=0, description="跳过数量")
    limit: int = Field(default=20, ge=1, le=100, description="返回数量")
    status: Optional[str] = Field(None, description="状态筛选")
    notification_type: Optional[str] = Field(None, description="通知类型筛选")
    priority: Optional[str] = Field(None, description="优先级筛选")
    start_date: Optional[datetime] = Field(None, description="开始日期")
    end_date: Optional[datetime] = Field(None, description="结束日期")


class NotificationMarkAsReadRequest(BaseModel):
    """标记已读请求"""

    notification_ids: List[int] = Field(..., description="通知ID列表")


class NotificationSendRequest(BaseModel):
    """发送通知请求（用于测试/手动发送）"""

    event_type: str = Field(..., description="事件类型")
    user_id: Optional[int] = Field(None, description="用户ID")
    data: Dict[str, Any] = Field(..., description="通知数据")
    related_type: Optional[str] = Field(None, description="关联资源类型")
    related_id: Optional[int] = Field(None, description="关联资源ID")


class UnreadCountResponse(BaseModel):
    """未读数量响应"""

    count: int = Field(..., description="未读消息数量")
