# -*- coding: utf-8 -*-
"""
数据库自定义类型定义
"""
import json
from datetime import date, datetime
from sqlalchemy import TypeDecorator, Text
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
