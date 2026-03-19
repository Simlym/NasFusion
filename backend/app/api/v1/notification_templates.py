# -*- coding: utf-8 -*-
"""
通知模板 API
"""
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_admin_user, get_current_user
from app.models.user import User
from app.schemas.notification import (
    NotificationTemplateCreate,
    NotificationTemplateListResponse,
    NotificationTemplateResponse,
    NotificationTemplateUpdate,
)
from app.services.notification.notification_template_service import NotificationTemplateService

router = APIRouter(prefix="/notification-templates", tags=["notification-templates"])
logger = logging.getLogger(__name__)


@router.post("", response_model=NotificationTemplateResponse, status_code=201)
async def create_notification_template(
    template_data: NotificationTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    创建通知模板

    创建新的通知模板，用于自定义通知消息格式。

    - **event_type**: 事件类型
    - **name**: 模板名称
    - **language**: 语言代码（如: zh-CN, en-US）
    - **format**: 消息格式（text, markdown, html）
    - **title_template**: 标题模板（支持变量替换）
    - **content_template**: 内容模板（支持变量替换）
    - **variables**: 可用变量列表（可选）
    - **is_system**: 是否为系统模板（仅管理员可创建）

    变量替换语法:
    - 基本语法: `{variable_name}`
    - 默认值语法: `{variable_name|default_value}`

    示例:
    ```
    标题: "{media_name} 下载完成"
    内容: "文件大小: {size_gb|未知} GB\\n质量: {quality|未知}"
    ```
    """
    try:
        # 验证模板语法
        title_validation = NotificationTemplateService.validate_template(
            template_data.title_template
        )
        content_validation = NotificationTemplateService.validate_template(
            template_data.content_template
        )

        if not title_validation["valid"]:
            raise ValueError(f"标题模板语法错误: {', '.join(title_validation['errors'])}")

        if not content_validation["valid"]:
            raise ValueError(f"内容模板语法错误: {', '.join(content_validation['errors'])}")

        # 系统模板只能由管理员创建
        if template_data.is_system and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="仅管理员可创建系统模板")

        # 非系统模板设置用户 ID
        if not template_data.is_system:
            template_data.user_id = current_user.id
        else:
            template_data.user_id = None

        template = await NotificationTemplateService.create_template(db, template_data)

        logger.info(
            f"用户 {current_user.username} 创建通知模板: {template.name}, 模板ID: {template.id}"
        )

        return template

    except ValueError as e:
        logger.warning(f"创建通知模板失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"创建通知模板时发生异常: {str(e)}")
        raise HTTPException(status_code=500, detail="创建通知模板失败")


@router.get("", response_model=NotificationTemplateListResponse)
async def get_notification_templates(
    event_type: Optional[str] = Query(None, description="事件类型筛选"),
    language: Optional[str] = Query(None, description="语言筛选"),
    is_system: Optional[bool] = Query(None, description="是否系统模板筛选"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取通知模板列表

    获取当前用户的自定义模板和系统模板。

    - **event_type**: 按事件类型筛选（可选）
    - **language**: 按语言筛选（可选）
    - **is_system**: 按是否系统模板筛选（可选）
    """
    try:
        user_templates = []
        system_templates = []

        # 获取用户自定义模板
        if is_system is None or is_system is False:
            user_templates = await NotificationTemplateService.get_user_templates(
                db,
                user_id=current_user.id,
                event_type=event_type,
                language=language,
            )

        # 获取系统模板
        if is_system is None or is_system is True:
            system_templates = await NotificationTemplateService.get_system_templates(
                db, event_type=event_type, language=language
            )

        # 合并结果
        all_templates = user_templates + system_templates

        return NotificationTemplateListResponse(
            total=len(all_templates), items=all_templates
        )

    except Exception as e:
        logger.exception(f"获取通知模板列表时发生异常: {str(e)}")
        raise HTTPException(status_code=500, detail="获取通知模板列表失败")


@router.get("/{template_id}", response_model=NotificationTemplateResponse)
async def get_notification_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取通知模板详情

    根据模板 ID 获取详细信息。
    """
    try:
        template = await NotificationTemplateService.get_by_id(db, template_id)

        if not template:
            raise HTTPException(status_code=404, detail="通知模板不存在")

        # 检查权限：系统模板所有人可见，自定义模板仅创建者可见
        if not template.is_system and template.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="无权访问此通知模板")

        return template

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"获取通知模板详情时发生异常: {str(e)}")
        raise HTTPException(status_code=500, detail="获取通知模板详情失败")


@router.put("/{template_id}", response_model=NotificationTemplateResponse)
async def update_notification_template(
    template_id: int,
    update_data: NotificationTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    更新通知模板

    更新现有通知模板的配置信息。

    - **name**: 模板名称
    - **language**: 语言代码
    - **format**: 消息格式
    - **title_template**: 标题模板
    - **content_template**: 内容模板
    - **variables**: 可用变量列表

    注意: 系统模板只能由管理员修改。
    """
    try:
        # 检查模板是否存在
        existing_template = await NotificationTemplateService.get_by_id(db, template_id)

        if not existing_template:
            raise HTTPException(status_code=404, detail="通知模板不存在")

        # 检查权限
        if existing_template.is_system and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="仅管理员可修改系统模板")

        if (
            not existing_template.is_system
            and existing_template.user_id != current_user.id
        ):
            raise HTTPException(status_code=403, detail="无权修改此通知模板")

        # 验证新模板语法（如果提供）
        if update_data.title_template:
            validation = NotificationTemplateService.validate_template(
                update_data.title_template
            )
            if not validation["valid"]:
                raise ValueError(
                    f"标题模板语法错误: {', '.join(validation['errors'])}"
                )

        if update_data.content_template:
            validation = NotificationTemplateService.validate_template(
                update_data.content_template
            )
            if not validation["valid"]:
                raise ValueError(
                    f"内容模板语法错误: {', '.join(validation['errors'])}"
                )

        # 更新模板
        updated_template = await NotificationTemplateService.update_template(
            db, template_id, update_data
        )

        if not updated_template:
            raise HTTPException(status_code=404, detail="通知模板不存在")

        logger.info(f"用户 {current_user.username} 更新通知模板: {template_id}")

        return updated_template

    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"更新通知模板失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"更新通知模板时发生异常: {str(e)}")
        raise HTTPException(status_code=500, detail="更新通知模板失败")


@router.delete("/{template_id}")
async def delete_notification_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    删除通知模板

    删除指定的通知模板。

    注意: 系统模板不允许删除。
    """
    try:
        # 检查模板是否存在
        existing_template = await NotificationTemplateService.get_by_id(db, template_id)

        if not existing_template:
            raise HTTPException(status_code=404, detail="通知模板不存在")

        # 检查权限
        if existing_template.is_system:
            raise HTTPException(status_code=403, detail="系统模板不允许删除")

        if existing_template.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="无权删除此通知模板")

        # 删除模板
        success = await NotificationTemplateService.delete_template(db, template_id)

        if not success:
            raise HTTPException(status_code=404, detail="通知模板不存在")

        logger.info(f"用户 {current_user.username} 删除通知模板: {template_id}")

        return {"message": "通知模板已删除"}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"删除通知模板时发生异常: {str(e)}")
        raise HTTPException(status_code=500, detail="删除通知模板失败")


@router.post("/validate")
async def validate_notification_template(
    template_str: str = Query(..., description="模板字符串"),
):
    """
    验证通知模板语法

    验证模板字符串的语法是否正确，并返回可用变量列表。

    请求示例:
    ```
    GET /api/v1/notification-templates/validate?template_str={media_name} 下载完成，大小: {size_gb|未知} GB
    ```

    响应示例:
    ```json
    {
        "valid": true,
        "errors": [],
        "variables": ["media_name", "size_gb"]
    }
    ```
    """
    try:
        result = NotificationTemplateService.validate_template(template_str)
        return result

    except Exception as e:
        logger.exception(f"验证通知模板时发生异常: {str(e)}")
        raise HTTPException(status_code=500, detail="验证通知模板失败")


@router.post("/{template_id}/render")
async def render_notification_template(
    template_id: int,
    variables: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    渲染通知模板

    使用提供的变量渲染模板，用于预览效果。

    请求体示例:
    ```json
    {
        "media_name": "复仇者联盟4",
        "size_gb": 15.5,
        "quality": "1080p",
        "site_name": "MTeam"
    }
    ```

    响应示例:
    ```json
    {
        "title": "复仇者联盟4 下载完成",
        "content": "文件大小: 15.5 GB\\n质量: 1080p\\n来源站点: MTeam"
    }
    ```
    """
    try:
        # 获取模板
        template = await NotificationTemplateService.get_by_id(db, template_id)

        if not template:
            raise HTTPException(status_code=404, detail="通知模板不存在")

        # 检查权限
        if not template.is_system and template.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="无权访问此通知模板")

        # 渲染模板
        result = NotificationTemplateService.render_template(template, variables)

        logger.info(
            f"用户 {current_user.username} 渲染通知模板 {template_id}, 变量数: {len(variables)}"
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"渲染通知模板时发生异常: {str(e)}")
        raise HTTPException(status_code=500, detail="渲染通知模板失败")


@router.get("/event/{event_type}", response_model=NotificationTemplateResponse)
async def get_template_for_event(
    event_type: str,
    language: str = Query("zh-CN", description="语言代码"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取事件对应的模板

    获取指定事件类型的通知模板，优先返回用户自定义模板，否则返回系统模板。

    - **event_type**: 事件类型
    - **language**: 语言代码（默认: zh-CN）

    优先级: 用户自定义模板 > 系统模板 > 默认语言(zh-CN)系统模板
    """
    try:
        template = await NotificationTemplateService.get_template_for_event(
            db, event_type=event_type, user_id=current_user.id, language=language
        )

        if not template:
            raise HTTPException(
                status_code=404,
                detail=f"未找到事件类型 {event_type} (语言: {language}) 的通知模板",
            )

        return template

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"获取事件模板时发生异常: {str(e)}")
        raise HTTPException(status_code=500, detail="获取事件模板失败")


@router.post("/system/init", dependencies=[Depends(get_current_admin_user)])
async def initialize_system_templates(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    初始化系统模板

    创建默认的系统通知模板（仅管理员可用）。

    这将为所有事件类型创建中文和英文的默认模板。
    """
    try:
        from app.constants.event import (
            # 订阅相关
            EVENT_SUBSCRIPTION_MATCHED,
            EVENT_SUBSCRIPTION_DOWNLOADED,
            EVENT_SUBSCRIPTION_COMPLETED,
            EVENT_SUBSCRIPTION_NO_RESOURCE,
            # 下载相关
            EVENT_DOWNLOAD_STARTED,
            EVENT_DOWNLOAD_COMPLETED,
            EVENT_DOWNLOAD_FAILED,
            EVENT_DOWNLOAD_PAUSED,
            # 资源相关
            EVENT_RESOURCE_FREE_PROMOTION,
            EVENT_RESOURCE_2X_PROMOTION,
            EVENT_RESOURCE_HIGH_QUALITY,
            # PT站点相关
            EVENT_SITE_CONNECTION_FAILED,
            EVENT_SITE_AUTH_EXPIRED,
            EVENT_SITE_SYNC_COMPLETED,
            # 媒体文件相关
            EVENT_MEDIA_SCAN_COMPLETED,
            EVENT_MEDIA_ORGANIZED,
            EVENT_MEDIA_METADATA_SCRAPED,
            # 任务相关
            EVENT_TASK_FAILED,
            EVENT_TASK_COMPLETED,
            # 系统相关
            EVENT_SYSTEM_ERROR,
            EVENT_DISK_SPACE_LOW,
            EVENT_USER_LOGIN_ANOMALY,
            EVENT_SYSTEM_UPDATE_AVAILABLE,
        )
        from app.constants.notification import NOTIFICATION_FORMAT_TEXT

        created_templates = []

        # 定义默认系统模板（中文）
        default_templates = [
            # ==================== 订阅相关 ====================
            {
                "event_type": EVENT_SUBSCRIPTION_MATCHED,
                "name": "订阅匹配通知",
                "language": "zh-CN",
                "format": NOTIFICATION_FORMAT_TEXT,
                "title_template": "📺 订阅匹配: {media_name}",
                "content_template": (
                    "媒体名称: {media_name}\n"
                    "质量: {quality|未知}\n"
                    "文件大小: {size_gb|未知} GB\n"
                    "促销类型: {promotion_type|无}\n"
                    "来源站点: {site_name}\n"
                    "做种数: {seeders|0} | 下载数: {leechers|0}"
                ),
                "is_system": True,
            },
            {
                "event_type": EVENT_SUBSCRIPTION_DOWNLOADED,
                "name": "订阅下载通知",
                "language": "zh-CN",
                "format": NOTIFICATION_FORMAT_TEXT,
                "title_template": "📥 订阅下载: {media_name}",
                "content_template": (
                    "媒体名称: {media_name}\n"
                    "文件大小: {size_gb|未知} GB\n"
                    "来源站点: {site_name}\n"
                    "保存路径: {save_path|未知}"
                ),
                "is_system": True,
            },
            {
                "event_type": EVENT_SUBSCRIPTION_COMPLETED,
                "name": "订阅完成通知",
                "language": "zh-CN",
                "format": NOTIFICATION_FORMAT_TEXT,
                "title_template": "✅ 订阅完成: {media_name}",
                "content_template": (
                    "媒体名称: {media_name}\n"
                    "总集数: {total_episodes|未知}\n"
                    "已下载: {downloaded_episodes|未知}\n"
                    "耗时: {duration|未知}"
                ),
                "is_system": True,
            },
            {
                "event_type": EVENT_SUBSCRIPTION_NO_RESOURCE,
                "name": "订阅无资源通知",
                "language": "zh-CN",
                "format": NOTIFICATION_FORMAT_TEXT,
                "title_template": "⚠️ 订阅无资源: {media_name}",
                "content_template": (
                    "媒体名称: {media_name}\n"
                    "订阅ID: {subscription_id}\n"
                    "最后检查: {last_check_at|未知}"
                ),
                "is_system": True,
            },

            # ==================== 下载相关 ====================
            {
                "event_type": EVENT_DOWNLOAD_STARTED,
                "name": "下载开始通知",
                "language": "zh-CN",
                "format": NOTIFICATION_FORMAT_TEXT,
                "title_template": "🚀 开始下载: {media_name}",
                "content_template": (
                    "媒体名称: {media_name}\n"
                    "文件大小: {size_gb|未知} GB\n"
                    "来源站点: {site_name}\n"
                    "种子哈希: {torrent_hash|未知}"
                ),
                "is_system": True,
            },
            {
                "event_type": EVENT_DOWNLOAD_COMPLETED,
                "name": "下载完成通知",
                "language": "zh-CN",
                "format": NOTIFICATION_FORMAT_TEXT,
                "title_template": "✅ 下载完成: {media_name}",
                "content_template": (
                    "媒体名称: {media_name}\n"
                    "文件大小: {size_gb|未知} GB\n"
                    "保存路径: {save_path|未知}\n"
                    "下载用时: {duration|未知}\n"
                    "分享率: {ratio|0.00}"
                ),
                "is_system": True,
            },
            {
                "event_type": EVENT_DOWNLOAD_FAILED,
                "name": "下载失败通知",
                "language": "zh-CN",
                "format": NOTIFICATION_FORMAT_TEXT,
                "title_template": "❌ 下载失败: {media_name}",
                "content_template": (
                    "媒体名称: {media_name}\n"
                    "失败原因: {error_message}\n"
                    "种子哈希: {torrent_hash|未知}\n"
                    "重试次数: {retry_count|0}"
                ),
                "is_system": True,
            },
            {
                "event_type": EVENT_DOWNLOAD_PAUSED,
                "name": "下载暂停通知",
                "language": "zh-CN",
                "format": NOTIFICATION_FORMAT_TEXT,
                "title_template": "⏸️ 下载暂停: {media_name}",
                "content_template": (
                    "媒体名称: {media_name}\n"
                    "当前进度: {progress|0}%\n"
                    "暂停原因: {reason|手动暂停}"
                ),
                "is_system": True,
            },

            # ==================== 资源相关 ====================
            {
                "event_type": EVENT_RESOURCE_FREE_PROMOTION,
                "name": "免费促销通知",
                "language": "zh-CN",
                "format": NOTIFICATION_FORMAT_TEXT,
                "title_template": "🎁 发现免费资源: {media_name}",
                "content_template": (
                    "媒体名称: {media_name}\n"
                    "来源站点: {site_name}\n"
                    "文件大小: {size_gb|未知} GB\n"
                    "促销截止: {promotion_end_at|未知}"
                ),
                "is_system": True,
            },
            {
                "event_type": EVENT_RESOURCE_2X_PROMOTION,
                "name": "2倍促销通知",
                "language": "zh-CN",
                "format": NOTIFICATION_FORMAT_TEXT,
                "title_template": "⚡ 发现2倍资源: {media_name}",
                "content_template": (
                    "媒体名称: {media_name}\n"
                    "来源站点: {site_name}\n"
                    "文件大小: {size_gb|未知} GB\n"
                    "促销截止: {promotion_end_at|未知}"
                ),
                "is_system": True,
            },
            {
                "event_type": EVENT_RESOURCE_HIGH_QUALITY,
                "name": "高质量资源通知",
                "language": "zh-CN",
                "format": NOTIFICATION_FORMAT_TEXT,
                "title_template": "🌟 发现高质量资源: {media_name}",
                "content_template": (
                    "媒体名称: {media_name}\n"
                    "来源站点: {site_name}\n"
                    "质量: {quality}\n"
                    "文件大小: {size_gb|未知} GB\n"
                    "做种数: {seeders|0}"
                ),
                "is_system": True,
            },

            # ==================== PT站点相关 ====================
            {
                "event_type": EVENT_SITE_CONNECTION_FAILED,
                "name": "站点连接失败通知",
                "language": "zh-CN",
                "format": NOTIFICATION_FORMAT_TEXT,
                "title_template": "🔌 站点连接失败: {site_name}",
                "content_template": (
                    "站点名称: {site_name}\n"
                    "错误信息: {error_message}\n"
                    "上次成功: {last_success_at|从未成功}"
                ),
                "is_system": True,
            },
            {
                "event_type": EVENT_SITE_AUTH_EXPIRED,
                "name": "站点认证过期通知",
                "language": "zh-CN",
                "format": NOTIFICATION_FORMAT_TEXT,
                "title_template": "🔑 站点认证过期: {site_name}",
                "content_template": (
                    "站点名称: {site_name}\n"
                    "过期时间: {expired_at}"
                ),
                "is_system": True,
            },
            {
                "event_type": EVENT_SITE_SYNC_COMPLETED,
                "name": "站点同步完成通知",
                "language": "zh-CN",
                "format": NOTIFICATION_FORMAT_TEXT,
                "title_template": "🔄 站点同步完成: {site_name}",
                "content_template": (
                    "站点名称: {site_name}\n"
                    "资源数量: {resources_count}\n"
                    "同步耗时: {duration|未知}"
                ),
                "is_system": True,
            },

            # ==================== 媒体文件相关 ====================
            {
                "event_type": EVENT_MEDIA_SCAN_COMPLETED,
                "name": "媒体扫描完成通知",
                "language": "zh-CN",
                "format": NOTIFICATION_FORMAT_TEXT,
                "title_template": "📂 媒体扫描完成",
                "content_template": (
                    "扫描目录: {directory}\n"
                    "发现文件: {files_found} 个\n"
                    "扫描耗时: {duration|未知}"
                ),
                "is_system": True,
            },
            {
                "event_type": EVENT_MEDIA_ORGANIZED,
                "name": "媒体整理完成通知",
                "language": "zh-CN",
                "format": NOTIFICATION_FORMAT_TEXT,
                "title_template": "📦 媒体整理完成: {media_name}",
                "content_template": (
                    "媒体名称: {media_name}\n"
                    "媒体类型: {media_type}\n"
                    "源路径: {source_path}\n"
                    "目标路径: {target_path}"
                ),
                "is_system": True,
            },
            {
                "event_type": EVENT_MEDIA_METADATA_SCRAPED,
                "name": "元数据刮削完成通知",
                "language": "zh-CN",
                "format": NOTIFICATION_FORMAT_TEXT,
                "title_template": "📝 元数据刮削完成: {media_name}",
                "content_template": (
                    "媒体名称: {media_name}\n"
                    "TMDB ID: {tmdb_id}\n"
                    "数据来源: {source}"
                ),
                "is_system": True,
            },

            # ==================== 任务相关 ====================
            {
                "event_type": EVENT_TASK_FAILED,
                "name": "任务失败通知",
                "language": "zh-CN",
                "format": NOTIFICATION_FORMAT_TEXT,
                "title_template": "❌ 任务失败: {task_name}",
                "content_template": (
                    "任务名称: {task_name}\n"
                    "任务类型: {task_type}\n"
                    "错误信息: {error_message}"
                ),
                "is_system": True,
            },
            {
                "event_type": EVENT_TASK_COMPLETED,
                "name": "任务完成通知",
                "language": "zh-CN",
                "format": NOTIFICATION_FORMAT_TEXT,
                "title_template": "✅ 任务完成: {task_name}",
                "content_template": (
                    "任务名称: {task_name}\n"
                    "执行耗时: {duration|未知}\n"
                    "执行结果: {result|成功}"
                ),
                "is_system": True,
            },

            # ==================== 系统相关 ====================
            {
                "event_type": EVENT_SYSTEM_ERROR,
                "name": "系统错误通知",
                "language": "zh-CN",
                "format": NOTIFICATION_FORMAT_TEXT,
                "title_template": "🚨 系统错误: {error_type}",
                "content_template": (
                    "错误类型: {error_type}\n"
                    "错误信息: {error_message}\n"
                    "发生时间: {timestamp}\n"
                    "所在模块: {module|未知}"
                ),
                "is_system": True,
            },
            {
                "event_type": EVENT_DISK_SPACE_LOW,
                "name": "磁盘空间不足通知",
                "language": "zh-CN",
                "format": NOTIFICATION_FORMAT_TEXT,
                "title_template": "💾 磁盘空间不足警告",
                "content_template": (
                    "磁盘路径: {disk_path}\n"
                    "可用空间: {available_gb} GB\n"
                    "总容量: {total_gb} GB\n"
                    "使用率: {usage_percent}%"
                ),
                "is_system": True,
            },
            {
                "event_type": EVENT_USER_LOGIN_ANOMALY,
                "name": "用户登录异常通知",
                "language": "zh-CN",
                "format": NOTIFICATION_FORMAT_TEXT,
                "title_template": "🔐 检测到异常登录",
                "content_template": (
                    "用户名: {username}\n"
                    "IP地址: {ip_address}\n"
                    "登录时间: {login_at}\n"
                    "异常原因: {reason}"
                ),
                "is_system": True,
            },
            {
                "event_type": EVENT_SYSTEM_UPDATE_AVAILABLE,
                "name": "系统更新可用通知",
                "language": "zh-CN",
                "format": NOTIFICATION_FORMAT_TEXT,
                "title_template": "🎉 系统更新可用",
                "content_template": (
                    "当前版本: {current_version}\n"
                    "最新版本: {new_version}\n"
                    "更新说明: {release_notes|查看GitHub Release}"
                ),
                "is_system": True,
            },
        ]

        # 创建模板（跳过已存在的）
        for template_data in default_templates:
            # 检查是否已存在相同的系统模板
            existing = await NotificationTemplateService.get_template_for_event(
                db,
                event_type=template_data["event_type"],
                user_id=None,  # 系统模板
                language=template_data["language"]
            )

            if existing and existing.is_system:
                logger.info(
                    f"系统模板已存在，跳过创建: {template_data['name']} "
                    f"(event={template_data['event_type']}, lang={template_data['language']})"
                )
                continue

            template_create = NotificationTemplateCreate(**template_data)
            template = await NotificationTemplateService.create_template(
                db, template_create
            )
            created_templates.append(template)
            logger.info(f"创建系统模板: {template.name} (ID: {template.id})")

        logger.info(f"管理员 {current_user.username} 初始化系统模板，共创建 {len(created_templates)} 个新模板")

        return {
            "message": f"成功创建 {len(created_templates)} 个系统模板",
            "templates": created_templates,
        }

    except Exception as e:
        logger.exception(f"初始化系统模板时发生异常: {str(e)}")
        raise HTTPException(status_code=500, detail="初始化系统模板失败")
