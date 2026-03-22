# -*- coding: utf-8 -*-
"""
系统设置管理工具

查询和更新系统设置，查看各模块配置状态
"""
import logging
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.ai_agent import AGENT_TOOL_SETTINGS_MANAGE
from app.models.system_setting import SystemSetting
from app.models.downloader_config import DownloaderConfig
from app.models.media_server_config import MediaServerConfig
from app.models.pt_site import PTSite
from app.models.notification import NotificationChannel
from app.models.storage_mount import StorageMount
from app.models.organize_config import OrganizeConfig
from app.models.login_history import LoginHistory
from app.services.ai_agent.tool_registry import BaseTool, register_tool


logger = logging.getLogger(__name__)


@register_tool
class SettingsManageTool(BaseTool):
    """系统设置管理工具"""

    name = AGENT_TOOL_SETTINGS_MANAGE
    description = """查询和管理系统设置。可以：
1. 查看所有系统设置或按分类查看
2. 获取某个具体设置的值
3. 更新或创建系统设置
4. 查看各模块配置概览
5. 查看/修改运行时日志级别（临时生效，重启恢复）

系统设置页面有以下模块（与前端一致）：
- system: 系统配置（媒体库设置、首页设置、日志级别）
- storage: 存储管理（存储挂载点）
- sites: PT站点
- downloaders: 下载器
- media_servers: 媒体服务器
- organize: 整理规则（文件整理配置）
- media_scraping: 媒体刮削（TMDB/TVDB API配置、识别优先级）
- notifications: 通知设置
- login_security: 登录安全（登录历史记录）

常用设置分类(category)和键(key)：
- homepage: backdrop_count(背景图数量，1-50，默认10)
- media_library: movie_show_anime(电影显示动画，默认false)、tv_show_anime(剧集显示动画，默认false)、show_adult_content(限制级内容，默认false)
- metadata_scraping: tmdb_api_key、tmdb_language、tmdb_proxy、tvdb_api_key、tvdb_pin、tvdb_proxy、identification_priority(识别优先级JSON)
- notification: notification.enable_internal_messages、notification.enable_external_messages、notification.default_language、notification.retention_days、notification.max_retries
- image_cache: expire_days(缓存过期天数)、max_size_mb(缓存最大MB)
- log_level: 特殊设置，使用 action=get_log_level 查看，action=set_log_level 修改

值均为字符串格式，布尔值用 "true"/"false"，数字用对应字符串。"""

    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "操作类型",
                "enum": ["list", "get", "update", "overview", "get_log_level", "set_log_level"],
            },
            "category": {
                "type": "string",
                "description": "设置分类（action=list/get/update 时使用）",
            },
            "key": {
                "type": "string",
                "description": "设置键名（action=get/update 时必填）",
            },
            "value": {
                "type": "string",
                "description": "设置值（action=update 时必填）",
            },
            "description": {
                "type": "string",
                "description": "设置描述（action=update 时可选）",
            },
            "overview_modules": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": [
                        "system",
                        "storage",
                        "sites",
                        "downloaders",
                        "media_servers",
                        "organize",
                        "media_scraping",
                        "notifications",
                        "login_security",
                        "all",
                    ],
                },
                "description": "要查看的模块（action=overview 时使用，默认 all）",
            },
            "log_level": {
                "type": "string",
                "description": "日志级别（action=set_log_level 时必填）",
                "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            },
        },
        "required": ["action"],
    }

    @classmethod
    async def execute(
        cls,
        db: AsyncSession,
        user_id: int,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        """执行设置管理操作"""
        action = arguments.get("action")

        if action == "list":
            return await cls._list_settings(db, arguments.get("category"))
        elif action == "get":
            return await cls._get_setting(
                db, arguments.get("category"), arguments.get("key")
            )
        elif action == "update":
            return await cls._update_setting(
                db,
                arguments.get("category"),
                arguments.get("key"),
                arguments.get("value"),
                arguments.get("description"),
            )
        elif action == "overview":
            return await cls._overview(
                db, arguments.get("overview_modules", ["all"])
            )
        elif action == "get_log_level":
            return cls._get_log_level()
        elif action == "set_log_level":
            return cls._set_log_level(arguments.get("log_level"))

        return {"success": False, "error": f"未知操作: {action}"}

    @classmethod
    async def _list_settings(
        cls, db: AsyncSession, category: str | None
    ) -> Dict[str, Any]:
        """列出系统设置"""
        query = select(SystemSetting)
        if category:
            query = query.where(SystemSetting.category == category)
        query = query.order_by(SystemSetting.category, SystemSetting.key)

        result = await db.execute(query)
        settings = result.scalars().all()

        if not settings:
            msg = f"分类「{category}」下没有设置" if category else "没有系统设置"
            return {"success": True, "message": msg, "settings": []}

        settings_list = []
        for s in settings:
            settings_list.append({
                "category": s.category,
                "key": s.key,
                "value": s.value if not s.is_encrypted else "******",
                "description": s.description,
                "is_active": s.is_active,
            })

        # 按分类分组统计
        categories = {}
        for s in settings_list:
            cat = s["category"]
            if cat not in categories:
                categories[cat] = 0
            categories[cat] += 1

        cat_summary = "、".join(
            f"{cat}({count}项)" for cat, count in categories.items()
        )

        return {
            "success": True,
            "message": f"共{len(settings_list)}项设置，分类：{cat_summary}",
            "settings": settings_list,
        }

    @classmethod
    async def _get_setting(
        cls, db: AsyncSession, category: str | None, key: str | None
    ) -> Dict[str, Any]:
        """获取单个设置"""
        if not category or not key:
            return {"success": False, "error": "获取设置需要提供 category 和 key"}

        result = await db.execute(
            select(SystemSetting).where(
                SystemSetting.category == category,
                SystemSetting.key == key,
            )
        )
        setting = result.scalar_one_or_none()

        if not setting:
            return {
                "success": False,
                "error": f"设置不存在: {category}/{key}",
            }

        return {
            "success": True,
            "message": f"设置 {category}/{key}",
            "setting": {
                "category": setting.category,
                "key": setting.key,
                "value": setting.value if not setting.is_encrypted else "******",
                "description": setting.description,
                "is_active": setting.is_active,
                "updated_at": setting.updated_at.isoformat() if setting.updated_at else None,
            },
        }

    @classmethod
    async def _update_setting(
        cls,
        db: AsyncSession,
        category: str | None,
        key: str | None,
        value: str | None,
        description: str | None,
    ) -> Dict[str, Any]:
        """更新或创建设置"""
        if not category or not key:
            return {"success": False, "error": "更新设置需要提供 category 和 key"}
        if value is None:
            return {"success": False, "error": "更新设置需要提供 value"}

        from app.services.common.system_setting_service import SystemSettingService

        setting = await SystemSettingService.upsert(
            db, category, key, value, description
        )

        # 如果更新的是识别优先级配置，清除缓存
        if category == "metadata_scraping" and key == "identification_priority":
            from app.services.identification.identify_priority_service import (
                IdentificationPriorityService,
            )
            IdentificationPriorityService.clear_cache()

        return {
            "success": True,
            "message": f"已更新设置 {category}/{key} = {value}",
            "setting": {
                "category": setting.category,
                "key": setting.key,
                "value": setting.value,
                "description": setting.description,
            },
        }

    @classmethod
    def _get_log_level(cls) -> Dict[str, Any]:
        """获取当前日志级别"""
        import logging as _logging

        from app.core.config import settings as app_settings

        root_logger = _logging.getLogger()
        runtime_level = _logging.getLevelName(root_logger.level)
        config_level = app_settings.LOG_LEVEL

        return {
            "success": True,
            "message": f"日志级别：配置文件默认 {config_level}，当前运行时 {runtime_level}",
            "log_level": {
                "config_level": config_level,
                "runtime_level": runtime_level,
                "available_levels": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                "note": "运行时修改为临时生效，应用重启后恢复为配置文件默认值",
            },
        }

    @classmethod
    def _set_log_level(cls, level: Optional[str]) -> Dict[str, Any]:
        """设置运行时日志级别"""
        if not level:
            return {"success": False, "error": "设置日志级别需要提供 log_level 参数"}

        import logging as _logging

        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        level_upper = level.upper()
        if level_upper not in valid_levels:
            return {
                "success": False,
                "error": f"无效的日志级别: {level}，有效值为: {', '.join(valid_levels)}",
            }

        log_level = getattr(_logging, level_upper)
        root_logger = _logging.getLogger()
        root_logger.setLevel(log_level)
        for handler in root_logger.handlers:
            handler.setLevel(log_level)

        from app.core.config import settings as app_settings

        return {
            "success": True,
            "message": f"日志级别已设置为 {level_upper}（临时生效，重启后恢复为 {app_settings.LOG_LEVEL}）",
            "log_level": {
                "config_level": app_settings.LOG_LEVEL,
                "runtime_level": level_upper,
            },
        }

    @classmethod
    async def _overview(
        cls, db: AsyncSession, modules: list[str]
    ) -> Dict[str, Any]:
        """查看各模块配置概览"""
        include_all = "all" in modules
        overview = {}

        # 模块顺序与前端设置页面 tab 保持一致
        MOD_NAMES = {
            "system": "系统配置",
            "storage": "存储管理",
            "sites": "PT站点",
            "downloaders": "下载器",
            "media_servers": "媒体服务器",
            "organize": "整理规则",
            "media_scraping": "媒体刮削",
            "notifications": "通知设置",
            "login_security": "登录安全",
        }

        # 1. 系统配置（媒体库设置 + 首页设置 + 日志级别）
        if include_all or "system" in modules:
            sys_result = await db.execute(
                select(SystemSetting).where(
                    SystemSetting.category.in_(["media_library", "homepage"])
                )
            )
            sys_settings = sys_result.scalars().all()
            settings_list = [
                {
                    "category": s.category,
                    "key": s.key,
                    "value": s.value if not s.is_encrypted else "******",
                    "description": s.description,
                }
                for s in sys_settings
            ]
            # 附加日志级别信息
            log_info = cls._get_log_level()
            overview["system"] = {
                "total": len(settings_list),
                "settings": settings_list,
                "log_level": log_info.get("log_level"),
            }

        # 2. 存储管理
        if include_all or "storage" in modules:
            sm_result = await db.execute(select(StorageMount))
            mounts = sm_result.scalars().all()
            overview["storage"] = {
                "total": len(mounts),
                "list": [
                    {
                        "name": m.name,
                        "mount_type": m.mount_type,
                        "container_path": m.container_path,
                        "host_path": m.host_path,
                        "is_enabled": m.is_enabled,
                        "media_category": m.media_category,
                    }
                    for m in mounts
                ],
            }

        # 3. PT 站点
        if include_all or "sites" in modules:
            sites_result = await db.execute(select(PTSite))
            sites = sites_result.scalars().all()
            overview["sites"] = {
                "total": len(sites),
                "list": [
                    {
                        "name": s.name,
                        "type": s.type,
                        "domain": s.domain,
                        "status": s.status,
                        "health_status": s.health_status,
                        "sync_enabled": s.sync_enabled,
                    }
                    for s in sites
                ],
            }

        # 4. 下载器
        if include_all or "downloaders" in modules:
            dl_result = await db.execute(select(DownloaderConfig))
            downloaders = dl_result.scalars().all()
            overview["downloaders"] = {
                "total": len(downloaders),
                "list": [
                    {
                        "name": d.name,
                        "type": d.type,
                        "host": d.host,
                        "port": d.port,
                        "status": d.status,
                        "is_default": d.is_default,
                        "is_enabled": d.is_enabled,
                    }
                    for d in downloaders
                ],
            }

        # 5. 媒体服务器
        if include_all or "media_servers" in modules:
            ms_result = await db.execute(select(MediaServerConfig))
            servers = ms_result.scalars().all()
            overview["media_servers"] = {
                "total": len(servers),
                "list": [
                    {
                        "name": s.name,
                        "type": s.type,
                        "host": s.host,
                        "port": s.port,
                        "status": s.status,
                        "is_default": s.is_default,
                    }
                    for s in servers
                ],
            }

        # 6. 整理规则
        if include_all or "organize" in modules:
            oc_result = await db.execute(select(OrganizeConfig))
            configs = oc_result.scalars().all()
            overview["organize"] = {
                "total": len(configs),
                "list": [
                    {
                        "name": c.name,
                        "media_type": c.media_type,
                        "organize_mode": c.organize_mode,
                        "is_enabled": c.is_enabled,
                        "is_default": c.is_default,
                        "library_root": c.library_root,
                    }
                    for c in configs
                ],
            }

        # 7. 媒体刮削（TMDB/TVDB 配置 + 识别优先级）
        if include_all or "media_scraping" in modules:
            scraping_result = await db.execute(
                select(SystemSetting).where(
                    SystemSetting.category == "metadata_scraping"
                )
            )
            scraping_settings = scraping_result.scalars().all()
            overview["media_scraping"] = {
                "total": len(scraping_settings),
                "settings": [
                    {
                        "key": s.key,
                        "value": s.value if not s.is_encrypted else "******",
                        "description": s.description,
                    }
                    for s in scraping_settings
                ],
            }

        # 8. 通知设置
        if include_all or "notifications" in modules:
            nc_result = await db.execute(select(NotificationChannel))
            channels = nc_result.scalars().all()
            # 也获取通知相关系统设置
            notify_settings_result = await db.execute(
                select(SystemSetting).where(
                    SystemSetting.category == "notification"
                )
            )
            notify_settings = notify_settings_result.scalars().all()
            overview["notifications"] = {
                "total": len(channels),
                "channels": [
                    {
                        "name": c.name,
                        "channel_type": c.channel_type,
                        "enabled": c.enabled,
                    }
                    for c in channels
                ],
                "settings": [
                    {
                        "key": s.key,
                        "value": s.value if not s.is_encrypted else "******",
                        "description": s.description,
                    }
                    for s in notify_settings
                ],
            }

        # 9. 登录安全（最近登录统计）
        if include_all or "login_security" in modules:
            from sqlalchemy import func, case

            stats_result = await db.execute(
                select(
                    func.count(LoginHistory.id).label("total"),
                    func.count(
                        case(
                            (LoginHistory.login_status == "success", 1),
                        )
                    ).label("success"),
                    func.count(
                        case(
                            (LoginHistory.login_status == "failed", 1),
                        )
                    ).label("failed"),
                    func.count(
                        case(
                            (LoginHistory.login_status == "locked", 1),
                        )
                    ).label("locked"),
                )
            )
            stats = stats_result.one()
            overview["login_security"] = {
                "total_records": stats.total,
                "success_count": stats.success,
                "failed_count": stats.failed,
                "locked_count": stats.locked,
            }

        # 总结
        parts = []
        for mod, data in overview.items():
            label = MOD_NAMES.get(mod, mod)
            total = data.get("total", data.get("total_records", 0))
            if mod == "system":
                parts.append(f"{label}({total}项设置)")
            elif mod == "login_security":
                parts.append(f"{label}({total}条记录)")
            else:
                parts.append(f"{label}({total}个)")

        return {
            "success": True,
            "message": "配置概览：" + "，".join(parts),
            "overview": overview,
        }
