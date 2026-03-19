"""
PT站点适配器

管理不同PT站点的适配器实现
"""
from typing import Dict, Any, Type
from app.adapters.base import BasePTSiteAdapter
from app.adapters.pt_sites.mteam import MTeamAdapter
from app.adapters.pt_sites.nexusphp import (
    NexusPHPAdapter,
    HDSkyAdapter,
    CHDBitsAdapter,
    PTHomeAdapter,
    OurBitsAdapter,
)


# 适配器注册表
# key为站点类型标识，value为适配器类
ADAPTER_REGISTRY: Dict[str, Type[BasePTSiteAdapter]] = {
    # API站点
    "mteam": MTeamAdapter,

    # NexusPHP站点（网页解析）
    "nexusphp": NexusPHPAdapter,  # 通用NexusPHP适配器
    "hdsky": HDSkyAdapter,        # 天空
    "chdbits": CHDBitsAdapter,    # 彩虹岛
    "pthome": PTHomeAdapter,      # 铂金家
    "ourbits": OurBitsAdapter,    # 我堡
}


def get_adapter(site_type: str, config: Dict[str, Any], metadata_mappings: Dict = None) -> BasePTSiteAdapter:
    """
    根据站点类型获取适配器实例

    Args:
        site_type: 站点类型，如"mteam", "hdsky"
        config: 站点配置信息
        metadata_mappings: 元数据映射字典（可选）

    Returns:
        适配器实例

    Raises:
        ValueError: 不支持的站点类型
    """
    adapter_class = ADAPTER_REGISTRY.get(site_type.lower())
    if not adapter_class:
        raise ValueError(
            f"Unsupported site type: {site_type}. "
            f"Supported types: {list(ADAPTER_REGISTRY.keys())}"
        )

    return adapter_class(config, metadata_mappings=metadata_mappings)


def get_supported_site_types() -> list[str]:
    """
    获取支持的站点类型列表

    Returns:
        站点类型列表
    """
    return list(ADAPTER_REGISTRY.keys())


__all__ = [
    "MTeamAdapter",
    "NexusPHPAdapter",
    "HDSkyAdapter",
    "CHDBitsAdapter",
    "PTHomeAdapter",
    "OurBitsAdapter",
    "ADAPTER_REGISTRY",
    "get_adapter",
    "get_supported_site_types",
]