# -*- coding: utf-8 -*-
"""
时区工具函数
统一管理系统时区
"""
from datetime import datetime, timezone
from typing import Optional

import pytz

from app.core.config import settings


def get_system_timezone():
    """获取系统配置的时区对象"""
    return pytz.timezone(settings.TIMEZONE)


def now() -> datetime:
    """
    获取系统时区的当前时间（时区感知）

    替代 datetime.now() 和 datetime.utcnow()

    Returns:
        系统时区的当前时间

    Example:
        >>> from app.utils.timezone import now
        >>> current_time = now()
        >>> print(current_time)  # 2025-11-22 18:30:00+08:00
    """
    tz = get_system_timezone()
    return datetime.now(tz)


def to_system_tz(dt: datetime) -> datetime:
    """
    将任意时区的 datetime 转换为系统时区

    Args:
        dt: datetime 对象（可以是任意时区或 naive）

    Returns:
        系统时区的 datetime

    Example:
        >>> from datetime import datetime, timezone as dt_timezone
        >>> utc_time = datetime(2025, 11, 22, 10, 30, tzinfo=dt_timezone.utc)
        >>> beijing_time = to_system_tz(utc_time)
        >>> print(beijing_time)  # 2025-11-22 18:30:00+08:00
    """
    tz = get_system_timezone()

    if dt.tzinfo is None:
        # SQLAlchemy 对 DateTime(timezone=True) + SQLite：
        # 写入 aware datetime 时转为 UTC 字符串存储，读出来是 naive UTC。
        # 因此 naive datetime 应视为 UTC，再转换为系统时区。
        dt = dt.replace(tzinfo=timezone.utc).astimezone(tz)
    else:
        # 如果有时区信息，转换为系统时区
        dt = dt.astimezone(tz)

    return dt


def ensure_timezone(dt: datetime) -> datetime:
    """
    确保 datetime 对象带有时区信息（时区感知）

    如果 datetime 是 naive（不带时区），则假设为系统时区并添加时区信息。
    如果已经带有时区信息，则转换为系统时区。

    Args:
        dt: datetime 对象

    Returns:
        带有时区信息的 datetime 对象

    Example:
        >>> from datetime import datetime
        >>> naive_dt = datetime(2025, 11, 22, 18, 30)
        >>> aware_dt = ensure_timezone(naive_dt)
        >>> print(aware_dt)  # 2025-11-22 18:30:00+08:00
    """
    return to_system_tz(dt)


def parse_pt_site_time(time_str: str, format: str = "%Y-%m-%d %H:%M:%S") -> datetime:
    """
    解析 PT 站点返回的时间字符串（假定为系统时区）

    Args:
        time_str: 时间字符串（如 "2025-11-22 18:30:00"）
        format: 时间格式

    Returns:
        系统时区的 datetime 对象

    Example:
        >>> pt_time = parse_pt_site_time("2025-11-22 18:30:00")
        >>> print(pt_time)  # 2025-11-22 18:30:00+08:00
    """
    tz = get_system_timezone()
    naive_dt = datetime.strptime(time_str, format)
    return tz.localize(naive_dt)


def parse_datetime(time_str: str) -> datetime:
    """
    解析 ISO 8601 格式的时间字符串为系统时区时间

    Args:
        time_str: 时间字符串

    Returns:
        系统时区的 datetime
    """
    # Python 3.11+ supports Z for UTC
    dt = datetime.fromisoformat(time_str)
    return to_system_tz(dt)


def format_datetime(dt: Optional[datetime], format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    格式化时间为本地时间字符串

    Args:
        dt: datetime 对象
        format_str: 格式化字符串

    Returns:
        格式化后的时间字符串
    """
    if dt is None:
        return ""

    # 确保时间是本地时间
    local_dt = to_system_tz(dt)

    return local_dt.strftime(format_str)


def format_iso_datetime(dt: Optional[datetime]) -> str:
    """
    格式化时间为ISO格式的本地时间字符串

    Args:
        dt: datetime 对象

    Returns:
        ISO格式的时间字符串
    """
    if dt is None:
        return ""

    # 确保时间是本地时间
    local_dt = to_system_tz(dt)

    return local_dt.isoformat()


def utc_now() -> datetime:
    """
    获取当前UTC时间（仅用于特殊场景如JWT token）

    Returns:
        当前UTC时间
    """
    return datetime.now(timezone.utc)


class DateTimeMixin:
    """日期时间处理Mixin类，为模型添加时间格式化方法"""

    def format_created_at(self, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
        """格式化创建时间"""
        return format_datetime(self.created_at, format_str)

    def format_updated_at(self, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
        """格式化更新时间"""
        return format_datetime(self.updated_at, format_str)

    def created_at_iso(self) -> str:
        """获取ISO格式的创建时间"""
        return format_iso_datetime(self.created_at)

    def updated_at_iso(self) -> str:
        """获取ISO格式的更新时间"""
        return format_iso_datetime(self.updated_at)
