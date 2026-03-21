# -*- coding: utf-8 -*-
"""
数据库自定义类型定义
"""
import json
from datetime import date, datetime, timezone

from sqlalchemy import DateTime, TypeDecorator, Text
from sqlalchemy.dialects.postgresql import JSONB


def _default_serializer(obj):
    """处理 json.dumps 无法序列化的类型"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

class JSON(TypeDecorator):
    """
    自定义 JSON 类型，支持 Unicode 字符不转义

    特性：
    - SQLite: 序列化时使用 ensure_ascii=False，保持 Unicode 字符可读
    - PostgreSQL: 使用原生 JSONB 类型
    - 适用于所有 Unicode 内容（中文、日文、韩文、emoji 等）

    使用场景：
    - 存储包含多语言文本的 JSON 数据
    - 需要在数据库中直接查看 JSON 内容时提高可读性
    """
    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        """根据数据库方言选择实现"""
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(JSONB())
        else:
            return dialect.type_descriptor(Text())

    def process_bind_param(self, value, dialect):
        """将 Python 对象转换为数据库存储格式"""
        if value is None:
            return None

        if dialect.name == 'postgresql':
            # PostgreSQL 的 JSONB 需要先序列化再反序列化，以确保 datetime 等类型被转换
            return json.loads(json.dumps(value, default=_default_serializer))
        else:
            # SQLite 等数据库：序列化为 JSON 字符串（保持 Unicode）
            return json.dumps(value, ensure_ascii=False, separators=(',', ':'), default=_default_serializer)

    def process_result_value(self, value, dialect):
        """将数据库存储格式转换为 Python 对象"""
        if value is None:
            return None

        if dialect.name == 'postgresql':
            # PostgreSQL 返回的已经是 Python 对象
            return value
        else:
            # SQLite 返回的是字符串，需要反序列化
            if isinstance(value, str):
                return json.loads(value)
            return value


class TZDateTime(TypeDecorator):
    """
    时区感知的 DateTime 类型

    解决 SQLAlchemy + SQLite 的时区问题：
    - SQLite 没有原生时区支持，存储 aware datetime 时只保留数值部分，丢失时区信息
    - 本类型在写入 SQLite 前将 aware datetime 统一转为 UTC，读取时标记为 UTC
    - PostgreSQL 原生支持时区，直接透传

    这样 to_system_tz() 中 "naive datetime 视为 UTC" 的假设就始终成立。
    """
    impl = DateTime
    cache_ok = True

    def __init__(self):
        super().__init__(timezone=True)

    def process_bind_param(self, value, dialect):
        """写入前：SQLite 统一转为 UTC"""
        if value is None:
            return value
        if dialect.name == 'sqlite':
            if value.tzinfo is not None:
                # 有时区信息：转为 UTC
                value = value.astimezone(timezone.utc)
            # naive datetime 假定已经是 UTC，不处理
        return value

    def process_result_value(self, value, dialect):
        """读取后：SQLite 返回的 naive datetime 标记为 UTC"""
        if value is None:
            return value
        if dialect.name == 'sqlite':
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
        return value
