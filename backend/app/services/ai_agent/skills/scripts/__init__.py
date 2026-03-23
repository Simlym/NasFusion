# -*- coding: utf-8 -*-
from app.services.ai_agent.skills.scripts.subscribe_tv import SubscribeTVSkill
from app.services.ai_agent.skills.scripts.subscribe_movie import SubscribeMovieSkill
from app.services.ai_agent.skills.scripts.smart_download import SmartDownloadSkill
from app.services.ai_agent.skills.scripts.dashboard import DashboardSkill
from app.services.ai_agent.skills.scripts.trending_download import TrendingDownloadSkill

__all__ = [
    "SubscribeTVSkill",
    "SubscribeMovieSkill",
    "SmartDownloadSkill",
    "DashboardSkill",
    "TrendingDownloadSkill",
]
