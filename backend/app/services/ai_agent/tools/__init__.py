# -*- coding: utf-8 -*-
"""
AI Agent 工具集

所有工具在此注册
"""
from app.services.ai_agent.tools.recommend import (
    MovieRecommendTool,
    TVRecommendTool,
)
from app.services.ai_agent.tools.resource import (
    ResourceSearchTool,
    ResourceIdentifyTool,
)
from app.services.ai_agent.tools.download import (
    DownloadCreateTool,
    DownloadStatusTool,
    DownloadManageTool,
)
from app.services.ai_agent.tools.subscription import (
    SubscriptionCreateTool,
    SubscriptionListTool,
    SubscriptionUpdateTool,
    SubscriptionDeleteTool,
)
from app.services.ai_agent.tools.query import (
    MediaQueryTool,
    TrendingQueryTool,
    SystemStatusTool,
)
from app.services.ai_agent.tools.sync import PTSyncTool
from app.services.ai_agent.tools.tasks_tool import TaskManageTool
from app.services.ai_agent.tools.settings import SettingsManageTool
from app.services.ai_agent.tools.site import SiteManageTool
from app.services.ai_agent.tools.organize import OrganizeMediaTool
from app.services.ai_agent.tools.watch import WatchHistoryTool
from app.services.ai_agent.tools.files import (
    ListDirectoryTool,
    ReadFileTool,
    WriteFileTool,
    EditFileTool,
)


__all__ = [
    "MovieRecommendTool",
    "TVRecommendTool",
    "ResourceSearchTool",
    "ResourceIdentifyTool",
    "DownloadCreateTool",
    "DownloadStatusTool",
    "DownloadManageTool",
    "SubscriptionCreateTool",
    "SubscriptionListTool",
    "SubscriptionUpdateTool",
    "SubscriptionDeleteTool",
    "MediaQueryTool",
    "TrendingQueryTool",
    "SystemStatusTool",
    "PTSyncTool",
    "TaskManageTool",
    "SettingsManageTool",
    "SiteManageTool",
    "OrganizeMediaTool",
    "WatchHistoryTool",
    "ListDirectoryTool",
    "ReadFileTool",
    "WriteFileTool",
    "EditFileTool",
]
