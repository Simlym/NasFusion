# -*- coding: utf-8 -*-
"""
下载器适配器模块
"""
from app.adapters.downloaders.base import BaseDownloaderAdapter
from app.adapters.downloaders.qbittorrent import QBittorrentAdapter
from app.adapters.downloaders.synology_ds import SynologyDownloadStationAdapter
from app.adapters.downloaders.transmission import TransmissionAdapter

__all__ = [
    "BaseDownloaderAdapter",
    "QBittorrentAdapter",
    "TransmissionAdapter",
    "SynologyDownloadStationAdapter",
]
