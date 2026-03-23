# -*- coding: utf-8 -*-
from app.services.ai_agent.skills.nasfusion.scripts.subscribe_tv import SubscribeTVSkill
from app.services.ai_agent.skills.nasfusion.scripts.subscribe_movie import SubscribeMovieSkill
from app.services.ai_agent.skills.nasfusion.scripts.smart_download import SmartDownloadSkill
from app.services.ai_agent.skills.nasfusion.scripts.dashboard import DashboardSkill
from app.services.ai_agent.skills.nasfusion.scripts.trending_download import TrendingDownloadSkill

__all__ = [
    "SubscribeTVSkill",
    "SubscribeMovieSkill",
    "SmartDownloadSkill",
    "DashboardSkill",
    "TrendingDownloadSkill",
]
