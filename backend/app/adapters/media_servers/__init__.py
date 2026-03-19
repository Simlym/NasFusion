# -*- coding: utf-8 -*-
"""
媒体服务器适配器模块（Jellyfin/Emby/Plex）
"""
from app.adapters.media_servers.base import BaseMediaServerAdapter
from app.adapters.media_servers.jellyfin import JellyfinAdapter

# 未来实现：
# from app.adapters.media_servers.emby import EmbyAdapter
# from app.adapters.media_servers.plex import PlexAdapter

from app.constants.media_server import (
    MEDIA_SERVER_TYPE_JELLYFIN,
    MEDIA_SERVER_TYPE_EMBY,
    MEDIA_SERVER_TYPE_PLEX,
)

# 适配器注册表（工厂模式）
ADAPTER_REGISTRY = {
    MEDIA_SERVER_TYPE_JELLYFIN: JellyfinAdapter,
    # MEDIA_SERVER_TYPE_EMBY: EmbyAdapter,  # 未来实现
    # MEDIA_SERVER_TYPE_PLEX: PlexAdapter,  # 未来实现
}


def get_media_server_adapter(server_type: str, config: dict) -> BaseMediaServerAdapter:
    """
    根据服务器类型获取适配器实例（工厂方法）

    Args:
        server_type: 服务器类型（jellyfin/emby/plex）
        config: 适配器配置字典
            - name: 服务器名称
            - host: 服务器地址
            - port: 端口号
            - use_ssl: 是否使用SSL
            - api_key: API Key（Jellyfin/Emby使用）
            - token: 访问令牌（Plex使用）

    Returns:
        BaseMediaServerAdapter: 对应的适配器实例

    Raises:
        ValueError: 不支持的服务器类型
    """
    adapter_class = ADAPTER_REGISTRY.get(server_type)
    if not adapter_class:
        raise ValueError(f"Unsupported media server type: {server_type}")
    return adapter_class(config)


__all__ = [
    "BaseMediaServerAdapter",
    "JellyfinAdapter",
    "get_media_server_adapter",
    "ADAPTER_REGISTRY",
]
