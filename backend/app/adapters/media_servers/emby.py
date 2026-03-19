# -*- coding: utf-8 -*-
"""
Emby 适配器
"""
from typing import Dict, Any
from app.adapters.media_servers.jellyfin import JellyfinAdapter

class EmbyAdapter(JellyfinAdapter):
    """
    Emby 适配器
    由于 Emby 和 Jellyfin API 高度兼容，直接继承 JellyfinAdapter。
    如果有特定于 Emby 的差异，可以在此覆盖。
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # Emby 可能需要不同的默认端口或其他微调，但通常 8096 是通用的
        self.port = config.get("port", 8096)
