# -*- coding: utf-8 -*-
"""
PT 资源标准结构

统一各站点适配器 fetch_resources 的返回结构，确保字段对齐 PTResource 模型，
并由消费方 pt_resource_service 正确处理。

消费契约见 pt_resource_service._perform_sync：
    result = await adapter.fetch_resources(...)
    result["resources"] -> List[resource_dict]
    result["total_pages"] -> int
"""
from typing import Any, Dict, List, Optional

# 单条资源的默认字段值（缺失即补默认，避免下游 KeyError）
# 必填字段 torrent_id / title / category 不在此处，由调用方保证提供。
RESOURCE_DEFAULTS: Dict[str, Any] = {
    "subtitle": "",
    "original_category_id": None,
    "subcategory": None,
    "size_bytes": 0,
    "seeders": 0,
    "leechers": 0,
    "completions": 0,
    "published_at": None,
    "is_free": False,
    "is_double_upload": False,
    "is_discount": False,
    "promotion_type": "none",
    "promotion_expire_at": None,
    "download_url": "",
    "detail_url": "",
    "tv_info": None,
    "detail_fetched": False,
    "douban_id": None,
    "douban_rating": None,
    "imdb_id": None,
    "imdb_rating": None,
}


def normalize_resource(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    补全单条资源的默认字段。

    Args:
        raw: 至少包含 torrent_id / title / category 的原始字典

    Returns:
        补全默认值后的资源字典
    """
    return {**RESOURCE_DEFAULTS, **raw}


def make_page_result(
    resources: List[Dict[str, Any]],
    page: int,
    total_pages: int = 1,
    total: Optional[int] = None,
) -> Dict[str, Any]:
    """
    构建标准分页返回结构。

    Args:
        resources: 资源列表
        page: 当前页码
        total_pages: 总页数
        total: 资源总数（缺省时取本页数量）

    Returns:
        标准分页结果字典
    """
    return {
        "resources": resources,
        "total_pages": total_pages,
        "total": total if total is not None else len(resources),
        "page_number": page,
        "page_size": len(resources),
    }


__all__ = ["RESOURCE_DEFAULTS", "normalize_resource", "make_page_result"]
