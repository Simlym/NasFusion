# -*- coding: utf-8 -*-
"""
Pydantic 基础配置
统一 datetime 序列化规则
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_serializer

from app.utils.timezone import to_system_tz


class TimestampMixin(BaseModel):
    """
    时间戳字段 Mixin
    确保所有 datetime 字段序列化为 ISO 8601 格式（带时区信息）
    """

    @field_serializer('created_at', 'updated_at', 'last_login_at',
                      'last_sync_at', 'health_check_at', 'completed_at',
                      'started_at', 'scheduled_at', 'locked_until',
                      'last_check_at', 'last_seeder_update_at',
                      'promotion_expire_at', 'published_at',
                      'password_changed_at', 'douban_fetched_at',
                      'detail_fetched_at', 'added_at', 'error_at',
                      'next_retry_at', 'last_run_at', 'next_run_at',
                      when_used='json',
                      check_fields=False)
    def serialize_datetime(self, dt: Optional[datetime], _info) -> Optional[str]:
        """
        将 datetime 序列化为 ISO 8601 格式（带时区）

        输入: datetime(2025, 11, 22, 18, 30, 0, tzinfo=Asia/Shanghai)
        输出: "2025-11-22T18:30:00+08:00"
        """
        if dt is None:
            return None

        # 确保是系统时区
        dt = to_system_tz(dt)

        # 使用 isoformat() 输出标准 ISO 8601 格式（带时区偏移）
        return dt.isoformat()


class BaseResponseSchema(TimestampMixin):
    """
    响应 Schema 基类
    包含通用配置
    """

    model_config = ConfigDict(
        from_attributes=True,  # 支持从 ORM 模型创建
        use_enum_values=True,   # 序列化枚举为值
    )
