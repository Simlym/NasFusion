"""
API响应辅助工具（简化版）
统一处理API响应格式，数据库存储本地时间
"""
from datetime import datetime
from typing import Any, Dict, Optional

from app.utils.timezone import format_datetime, format_iso_datetime


def serialize_datetime(dt: Optional[datetime], format_type: str = "iso") -> Optional[str]:
    """
    序列化日期时间对象为字符串

    Args:
        dt: 日期时间对象（数据库中的本地时间）
        format_type: 格式类型，"iso"（ISO格式）或 "readable"（可读格式）

    Returns:
        格式化后的时间字符串
    """
    if dt is None:
        return None

    if format_type == "iso":
        return format_iso_datetime(dt)
    elif format_type == "readable":
        return format_datetime(dt)
    else:
        return format_iso_datetime(dt)


# 兼容函数，供旧的API使用
def success_response(
    data: Any = None,
    message: str = "操作成功",
    datetime_format: str = "iso",
    meta: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    成功响应（兼容函数）

    Args:
        data: 响应数据
        message: 响应消息
        datetime_format: 日期时间格式
        meta: 元数据（如分页信息）

    Returns:
        标准化的成功响应
    """
    response = {
        "success": True,
        "message": message,
        "data": prepare_response_data(data, datetime_format) if data else None,
    }

    if meta:
        response["meta"] = meta

    return response


def error_response(
    message: str = "操作失败",
    code: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    错误响应（兼容函数）

    Args:
        message: 错误消息
        code: 错误代码
        details: 错误详情

    Returns:
        标准化的错误响应
    """
    response = {
        "success": False,
        "message": message,
    }

    if code:
        response["code"] = code

    if details:
        response["details"] = details

    return response


def prepare_response_data(data: Dict[str, Any], datetime_format: str = "iso") -> Dict[str, Any]:
    """
    准备API响应数据，自动处理日期时间字段

    Args:
        data: 原始数据字典
        datetime_format: 日期时间格式类型

    Returns:
        处理后的响应数据
    """
    if not isinstance(data, dict):
        return data

    result = {}

    for key, value in data.items():
        # 处理日期时间字段
        if isinstance(value, datetime):
            result[key] = serialize_datetime(value, datetime_format)
        elif key.endswith("_at") and value is not None:
            # 对于以_at结尾的字段，如果不是datetime类型，尝试转换为datetime
            try:
                if isinstance(value, str):
                    from dateutil.parser import parse
                    dt_value = parse(value)
                    result[key] = serialize_datetime(dt_value, datetime_format)
                else:
                    result[key] = value
            except (ValueError, ImportError):
                result[key] = value
        elif isinstance(value, dict):
            # 递归处理嵌套字典
            result[key] = prepare_response_data(value, datetime_format)
        elif isinstance(value, list):
            # 处理列表中的字典项
            result[key] = [
                prepare_response_data(item, datetime_format) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            result[key] = value

    return result


class DateTimeAwareResponse:
    """支持时区的API响应包装器"""

    @staticmethod
    def success(
        data: Any = None,
        message: str = "操作成功",
        datetime_format: str = "iso",
        meta: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        成功响应

        Args:
            data: 响应数据
            message: 响应消息
            datetime_format: 日期时间格式
            meta: 元数据（如分页信息）

        Returns:
            标准化的成功响应
        """
        response = {
            "success": True,
            "message": message,
            "data": prepare_response_data(data, datetime_format) if data else None,
        }

        if meta:
            response["meta"] = meta

        return response

    @staticmethod
    def error(
        message: str = "操作失败",
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        错误响应

        Args:
            message: 错误消息
            code: 错误代码
            details: 错误详情

        Returns:
            标准化的错误响应
        """
        response = {
            "success": False,
            "message": message,
        }

        if code:
            response["code"] = code

        if details:
            response["details"] = details

        return response


# 常用的响应格式
def paginated_response(
    items: list,
    total: int,
    page: int,
    page_size: int,
    message: str = "获取成功",
    datetime_format: str = "iso"
) -> Dict[str, Any]:
    """
    分页响应格式

    Args:
        items: 数据列表
        total: 总数
        page: 当前页码
        page_size: 每页数量
        message: 响应消息
        datetime_format: 日期时间格式

    Returns:
        分页响应数据
    """
    return DateTimeAwareResponse.success(
        data=items,
        message=message,
        datetime_format=datetime_format,
        meta={
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
    )