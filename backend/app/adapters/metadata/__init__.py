# -*- coding: utf-8 -*-
"""
元数据适配器
"""
from app.adapters.metadata.douban_adapter import DoubanAdapter
from app.adapters.metadata.tmdb_adapter import TMDBAdapter
from app.adapters.metadata.tvdb_adapter import TVDBAdapter

__all__ = ["DoubanAdapter", "TMDBAdapter", "TVDBAdapter"]
