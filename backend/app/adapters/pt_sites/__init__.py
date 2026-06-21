"""
PT站点适配器

管理不同PT站点的适配器实现。

路由策略（get_adapter）：
1. 优先按站点预设（preset）的 schema 字段路由到对应"框架"适配器（SCHEMA_REGISTRY）。
   新增同框架站点只需在 site_presets.py 增加配置，无需改这里。
2. 回退：按 site_type 直查旧的站点级注册表（ADAPTER_REGISTRY），兼容无预设/存量站点。
"""
import logging
from typing import Dict, Any, Optional, Type

from app.adapters.base import BasePTSiteAdapter
from app.adapters.pt_sites.mteam import MTeamAdapter
from app.adapters.pt_sites.nexusphp import NexusPHPAdapter
from app.adapters.pt_sites.unit3d import Unit3dAdapter
from app.adapters.pt_sites.generic_json_api import GenericJSONAPIAdapter
from app.constants.site_presets import (
    get_site_preset,
    SITE_SCHEMA_MTEAM,
    SITE_SCHEMA_NEXUSPHP,
    SITE_SCHEMA_UNIT3D,
    SITE_SCHEMA_GENERIC_JSON_API,
)

logger = logging.getLogger(__name__)


# 框架（schema）→ 适配器
# 这是主路由表。站点预设的 schema 字段决定使用哪个适配器，
# 各站点的差异通过预设配置（selectors / category_details / *_config）表达。
SCHEMA_REGISTRY: Dict[str, Type[BasePTSiteAdapter]] = {
    SITE_SCHEMA_MTEAM: MTeamAdapter,
    SITE_SCHEMA_NEXUSPHP: NexusPHPAdapter,
    SITE_SCHEMA_UNIT3D: Unit3dAdapter,
    SITE_SCHEMA_GENERIC_JSON_API: GenericJSONAPIAdapter,
}


# 站点类型 → 适配器（兼容路由）
# 仅用于无预设或存量数据的回退。新站点应走 SCHEMA_REGISTRY。
ADAPTER_REGISTRY: Dict[str, Type[BasePTSiteAdapter]] = {
    "mteam": MTeamAdapter,
    "nexusphp": NexusPHPAdapter,
    # 注：hdsky/chdbits/pthome/ourbits 等站点级映射已移除，
    # 由 schema=nexusphp + preset_id 还原其行为。
}


def _resolve_adapter_class(
    site_type: str, config: Dict[str, Any]
) -> Type[BasePTSiteAdapter]:
    """
    解析应使用的适配器类。

    Args:
        site_type: 站点类型（当前等同于 preset_id）
        config: 站点配置（应包含 preset_id）

    Returns:
        适配器类

    Raises:
        ValueError: 无法解析适配器
    """
    # 1) 优先按 preset 的 schema 路由
    preset_id = config.get("preset_id") or site_type
    preset = get_site_preset(preset_id) if preset_id else None
    if preset:
        schema = preset.get("schema")
        adapter_class = SCHEMA_REGISTRY.get(schema)
        if adapter_class:
            return adapter_class
        logger.warning(
            f"预设 {preset_id} 的 schema='{schema}' 暂无对应适配器，回退到站点级路由"
        )

    # 2) 回退：按 site_type 直查站点级注册表
    adapter_class = ADAPTER_REGISTRY.get(site_type.lower())
    if adapter_class:
        return adapter_class

    raise ValueError(
        f"Unsupported site: type={site_type}, "
        f"schema={preset.get('schema') if preset else None}. "
        f"Supported schemas: {list(SCHEMA_REGISTRY.keys())}; "
        f"supported types: {list(ADAPTER_REGISTRY.keys())}"
    )


def get_adapter(
    site_type: str,
    config: Dict[str, Any],
    metadata_mappings: Optional[Dict] = None,
) -> BasePTSiteAdapter:
    """
    根据站点类型获取适配器实例

    Args:
        site_type: 站点类型，如 "mteam", "hdsky"（当前等同于 preset_id）
        config: 站点配置信息
        metadata_mappings: 元数据映射字典（可选）

    Returns:
        适配器实例

    Raises:
        ValueError: 不支持的站点类型
    """
    # 确保 config 带上 preset_id，使适配器内部能加载预设。
    # 现状 site.type 即 preset_id；若调用方未显式传入则用 site_type 兜底。
    if not config.get("preset_id"):
        config["preset_id"] = site_type

    adapter_class = _resolve_adapter_class(site_type, config)
    return adapter_class(config, metadata_mappings=metadata_mappings)


def get_supported_site_types() -> list[str]:
    """
    获取支持的站点类型列表（框架 schema + 兼容站点类型）

    Returns:
        站点类型列表
    """
    return list(dict.fromkeys([*SCHEMA_REGISTRY.keys(), *ADAPTER_REGISTRY.keys()]))


__all__ = [
    "MTeamAdapter",
    "NexusPHPAdapter",
    "Unit3dAdapter",
    "GenericJSONAPIAdapter",
    "SCHEMA_REGISTRY",
    "ADAPTER_REGISTRY",
    "get_adapter",
    "get_supported_site_types",
]
