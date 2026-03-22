"""
API v1 路由聚合
"""
from fastapi import APIRouter

from app.api.v1 import (
    ai_agent,
    auth,
    mcp,
    telegram_webhook,
    download_tasks,
    downloaders,
    file_system,
    image_cache,
    login_history,
    media_files,
    media_directories,
    media_servers,
    notification_channels,
    notification_debug,
    notification_dispatch,
    notification_rules,
    notification_templates,
    notifications,
    organize_configs,
    pt_resource_details,
    pt_resources,
    pt_sites,
    resource_identification,
    scheduled_tasks,
    subscriptions,
    system_logs,
    system_settings,
    task_executions,
    trending,
    unified_movies,
    unified_tv,
    storage_mounts,
    users,
    dashboard,
    persons,
)

# 创建v1路由器
api_router = APIRouter()

# 注册子路由
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(pt_sites.router)
api_router.include_router(pt_resources.router)
api_router.include_router(resource_identification.router)
api_router.include_router(unified_movies.router)
api_router.include_router(unified_tv.router)
api_router.include_router(persons.router, prefix="/persons", tags=["persons"])
api_router.include_router(subscriptions.router)
api_router.include_router(notifications.router)
api_router.include_router(notification_channels.router)
api_router.include_router(notification_rules.router)
api_router.include_router(notification_templates.router)
api_router.include_router(notification_dispatch.router)
api_router.include_router(notification_debug.router)
api_router.include_router(system_settings.router)
api_router.include_router(system_logs.router)
api_router.include_router(downloaders.router)
api_router.include_router(download_tasks.router)
api_router.include_router(media_files.router)
api_router.include_router(media_directories.router)
api_router.include_router(media_servers.router)
api_router.include_router(organize_configs.router)
api_router.include_router(scheduled_tasks.router)
api_router.include_router(task_executions.router)
api_router.include_router(trending.router)
api_router.include_router(image_cache.router)
api_router.include_router(file_system.router)
api_router.include_router(pt_resource_details.router)
api_router.include_router(storage_mounts.router)
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(login_history.router)
api_router.include_router(ai_agent.router)
api_router.include_router(mcp.router)
api_router.include_router(telegram_webhook.router)
