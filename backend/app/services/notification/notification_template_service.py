# -*- coding: utf-8 -*-
"""
通知模板服务层
"""
import logging
import re
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import NotificationTemplate
from app.schemas.notification import (
    NotificationTemplateCreate,
    NotificationTemplateUpdate,
)

logger = logging.getLogger(__name__)


class NotificationTemplateService:
    """通知模板服务"""

    @staticmethod
    async def create_template(
        db: AsyncSession, template_data: NotificationTemplateCreate
    ) -> NotificationTemplate:
        """
        创建通知模板

        Args:
            db: 数据库会话
            template_data: 模板数据

        Returns:
            创建的模板记录
        """
        template = NotificationTemplate(
            user_id=template_data.user_id,
            event_type=template_data.event_type,
            name=template_data.name,
            language=template_data.language,
            format=template_data.format,
            title_template=template_data.title_template,
            content_template=template_data.content_template,
            variables=template_data.variables,
            is_system=template_data.is_system,
        )

        db.add(template)
        await db.commit()
        await db.refresh(template)

        logger.info(
            f"创建通知模板: {template.name} (事件: {template.event_type}, 语言: {template.language})"
        )
        return template

    @staticmethod
    async def get_by_id(
        db: AsyncSession, template_id: int
    ) -> Optional[NotificationTemplate]:
        """根据ID获取模板"""
        result = await db.execute(
            select(NotificationTemplate).where(NotificationTemplate.id == template_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_template_for_event(
        db: AsyncSession,
        event_type: str,
        user_id: Optional[int] = None,
        language: str = "zh-CN",
    ) -> Optional[NotificationTemplate]:
        """
        获取事件对应的模板

        优先级: 用户自定义模板 > 系统模板

        Args:
            db: 数据库会话
            event_type: 事件类型
            user_id: 用户ID（可选）
            language: 语言

        Returns:
            模板记录
        """
        # 先尝试获取用户自定义模板
        if user_id:
            query = select(NotificationTemplate).where(
                and_(
                    NotificationTemplate.user_id == user_id,
                    NotificationTemplate.event_type == event_type,
                    NotificationTemplate.language == language,
                )
            )

            result = await db.execute(query)
            user_template = result.scalar_one_or_none()

            if user_template:
                logger.debug(
                    f"使用用户自定义模板: {user_template.name} (ID: {user_template.id})"
                )
                return user_template

        # 获取系统模板
        query = select(NotificationTemplate).where(
            and_(
                NotificationTemplate.is_system == True,
                NotificationTemplate.event_type == event_type,
                NotificationTemplate.language == language,
            )
        )

        result = await db.execute(query)
        system_template = result.scalar_one_or_none()

        if system_template:
            logger.debug(
                f"使用系统模板: {system_template.name} (ID: {system_template.id})"
            )
            return system_template

        # 如果指定语言没有模板，尝试获取默认语言（zh-CN）
        if language != "zh-CN":
            return await NotificationTemplateService.get_template_for_event(
                db, event_type, user_id, "zh-CN"
            )

        logger.warning(f"未找到模板: event_type={event_type}, language={language}")
        return None

    @staticmethod
    async def get_user_templates(
        db: AsyncSession,
        user_id: int,
        event_type: Optional[str] = None,
        language: Optional[str] = None,
    ) -> List[NotificationTemplate]:
        """
        获取用户的模板列表

        Args:
            db: 数据库会话
            user_id: 用户ID
            event_type: 事件类型筛选
            language: 语言筛选

        Returns:
            模板列表
        """
        query = select(NotificationTemplate).where(
            NotificationTemplate.user_id == user_id
        )

        if event_type:
            query = query.where(NotificationTemplate.event_type == event_type)

        if language:
            query = query.where(NotificationTemplate.language == language)

        query = query.order_by(NotificationTemplate.event_type, NotificationTemplate.language)

        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_system_templates(
        db: AsyncSession,
        event_type: Optional[str] = None,
        language: Optional[str] = None,
    ) -> List[NotificationTemplate]:
        """
        获取系统模板列表

        Args:
            db: 数据库会话
            event_type: 事件类型筛选
            language: 语言筛选

        Returns:
            系统模板列表
        """
        query = select(NotificationTemplate).where(
            NotificationTemplate.is_system == True
        )

        if event_type:
            query = query.where(NotificationTemplate.event_type == event_type)

        if language:
            query = query.where(NotificationTemplate.language == language)

        query = query.order_by(NotificationTemplate.event_type, NotificationTemplate.language)

        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def update_template(
        db: AsyncSession, template_id: int, update_data: NotificationTemplateUpdate
    ) -> Optional[NotificationTemplate]:
        """
        更新通知模板

        Args:
            db: 数据库会话
            template_id: 模板ID
            update_data: 更新数据

        Returns:
            更新后的模板记录
        """
        template = await NotificationTemplateService.get_by_id(db, template_id)

        if not template:
            return None

        # 更新字段
        update_dict = update_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(template, key, value)

        await db.commit()
        await db.refresh(template)

        logger.info(f"更新通知模板: {template.name} (ID: {template.id})")
        return template

    @staticmethod
    async def delete_template(db: AsyncSession, template_id: int) -> bool:
        """
        删除通知模板

        Args:
            db: 数据库会话
            template_id: 模板ID

        Returns:
            是否删除成功
        """
        template = await NotificationTemplateService.get_by_id(db, template_id)

        if not template:
            return False

        # 不允许删除系统模板
        if template.is_system:
            logger.warning(f"尝试删除系统模板: {template.name} (ID: {template.id})")
            return False

        await db.delete(template)
        await db.commit()

        logger.info(f"删除通知模板: {template.name} (ID: {template.id})")
        return True

    @staticmethod
    def render_template(
        template: NotificationTemplate, variables: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        渲染模板

        Args:
            template: 通知模板
            variables: 变量字典

        Returns:
            {"title": str, "content": str}
        """
        # 渲染标题
        title = NotificationTemplateService._replace_variables(
            template.title_template, variables
        )

        # 渲染内容
        content = NotificationTemplateService._replace_variables(
            template.content_template, variables
        )

        logger.debug(
            f"模板渲染完成: {template.name}, 变量数: {len(variables)}"
        )

        return {"title": title, "content": content}

    @staticmethod
    def _replace_variables(template_str: str, variables: Dict[str, Any]) -> str:
        """
        替换模板中的变量

        支持格式: {variable_name}

        Args:
            template_str: 模板字符串
            variables: 变量字典

        Returns:
            替换后的字符串
        """
        # 使用正则表达式找到所有 {variable} 格式的占位符
        pattern = r"\{([^}]+)\}"

        def replace_func(match):
            var_name = match.group(1).strip()

            # 支持默认值语法: {variable|default_value}
            if "|" in var_name:
                var_name, default_value = var_name.split("|", 1)
                var_name = var_name.strip()
                default_value = default_value.strip()
            else:
                default_value = f"{{{var_name}}}"  # 保留原始占位符

            # 获取变量值
            value = variables.get(var_name, default_value)

            # 转换为字符串
            if value is None:
                return ""
            elif isinstance(value, (int, float)):
                return str(value)
            elif isinstance(value, bool):
                return "是" if value else "否"
            else:
                return str(value)

        return re.sub(pattern, replace_func, template_str)

    @staticmethod
    def validate_template(template_str: str) -> Dict[str, Any]:
        """
        验证模板语法

        Args:
            template_str: 模板字符串

        Returns:
            {"valid": bool, "errors": List[str], "variables": List[str]}
        """
        errors = []
        variables = []

        # 查找所有变量
        pattern = r"\{([^}]+)\}"
        matches = re.findall(pattern, template_str)

        for match in matches:
            var_name = match.strip()

            # 支持默认值语法
            if "|" in var_name:
                var_name = var_name.split("|")[0].strip()

            # 检查变量名是否合法（只允许字母、数字、下划线）
            if not re.match(r"^[a-zA-Z0-9_]+$", var_name):
                errors.append(f"非法变量名: {var_name}")
            else:
                if var_name not in variables:
                    variables.append(var_name)

        # 检查括号是否匹配
        if template_str.count("{") != template_str.count("}"):
            errors.append("括号不匹配")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "variables": variables,
        }
