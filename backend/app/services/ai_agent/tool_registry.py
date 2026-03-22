# -*- coding: utf-8 -*-
"""
AI Agent 工具注册表

管理所有可用的 Agent 工具
"""
import logging
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Type

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.llm.base import ToolDefinition


logger = logging.getLogger(__name__)


class BaseTool(ABC):
    """
    Agent 工具基类

    所有工具都应继承此类
    """

    # 工具名称（唯一标识）
    name: str = ""

    # 工具描述（给 LLM 看的）
    description: str = ""

    # 参数 JSON Schema
    parameters: Dict[str, Any] = {}

    @classmethod
    def get_definition(cls) -> ToolDefinition:
        """获取工具定义（给 LLM）"""
        return ToolDefinition(
            name=cls.name,
            description=cls.description,
            parameters=cls.parameters,
        )

    @classmethod
    @abstractmethod
    async def execute(
        cls,
        db: AsyncSession,
        user_id: int,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        执行工具

        Args:
            db: 数据库会话
            user_id: 用户ID
            arguments: 调用参数

        Returns:
            执行结果
        """
        pass


class ToolRegistry:
    """
    工具注册表

    管理所有已注册的工具
    """

    _tools: Dict[str, Type[BaseTool]] = {}

    @classmethod
    def register(cls, tool_class: Type[BaseTool]) -> None:
        """
        注册工具

        Args:
            tool_class: 工具类
        """
        if not tool_class.name:
            raise ValueError(f"工具类 {tool_class.__name__} 必须定义 name 属性")

        cls._tools[tool_class.name] = tool_class
        logger.debug(f"注册工具: {tool_class.name}")

    @classmethod
    def unregister(cls, tool_name: str) -> None:
        """
        注销工具

        Args:
            tool_name: 工具名称
        """
        if tool_name in cls._tools:
            del cls._tools[tool_name]
            logger.debug(f"注销工具: {tool_name}")

    @classmethod
    def get_tool(cls, tool_name: str) -> Optional[Type[BaseTool]]:
        """
        获取工具类

        Args:
            tool_name: 工具名称

        Returns:
            工具类或 None
        """
        return cls._tools.get(tool_name)

    @classmethod
    def get_all_tools(cls) -> Dict[str, Type[BaseTool]]:
        """获取所有工具"""
        return cls._tools.copy()

    @classmethod
    def get_tool_definitions(cls) -> List[ToolDefinition]:
        """获取所有工具的定义（给 LLM）"""
        return [tool.get_definition() for tool in cls._tools.values()]

    @classmethod
    def get_tool_names(cls) -> List[str]:
        """获取所有工具名称"""
        return list(cls._tools.keys())

    @classmethod
    def resolve_tool_name(cls, tool_name: str) -> Optional[str]:
        """
        解析工具名称，支持模糊匹配

        当 LLM 返回的工具名不在注册表中时，尝试通过关键词匹配
        找到最可能的已注册工具。

        Args:
            tool_name: LLM 返回的工具名称

        Returns:
            匹配到的已注册工具名，或 None
        """
        # 精确匹配
        if tool_name in cls._tools:
            return tool_name

        # 关键词 → 工具名映射表
        # 将常见的 LLM 幻觉工具名映射到正确的已注册工具
        KEYWORD_MAP = {
            "settings": "settings_manage",
            "setting": "settings_manage",
            "config": "settings_manage",
            "system_config": "settings_manage",
            "system_setting": "settings_manage",
            "download": "download_manage",
            "task": "task_manage",
            "subscription": "subscription_list",
            "subscribe": "subscription_create",
            "movie": "movie_recommend",
            "tv": "tv_recommend",
            "search": "resource_search",
            "resource": "resource_search",
            "identify": "resource_identify",
            "media": "media_query",
            "status": "system_status",
            "trending": "trending_query",
            "sync": "pt_sync",
        }

        name_lower = tool_name.lower()

        # 尝试关键词匹配
        for keyword, mapped_tool in KEYWORD_MAP.items():
            if keyword in name_lower and mapped_tool in cls._tools:
                logger.warning(
                    f"工具名纠正: '{tool_name}' -> '{mapped_tool}'"
                )
                return mapped_tool

        return None

    @classmethod
    def _adapt_arguments(
        cls,
        original_name: str,
        resolved_name: str,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        适配参数：当工具名被纠正后，尝试将幻觉参数映射到正确的参数格式

        Args:
            original_name: LLM 返回的原始工具名
            resolved_name: 纠正后的工具名
            arguments: LLM 提供的原始参数

        Returns:
            适配后的参数
        """
        name_lower = original_name.lower()

        if resolved_name == "settings_manage":
            # 推断 action
            if "get" in name_lower or "query" in name_lower or "list" in name_lower or "view" in name_lower:
                # 检查是否有模块信息，映射到 overview
                module_value = (
                    arguments.get("module_name")
                    or arguments.get("module")
                    or arguments.get("category")
                    or arguments.get("name")
                    or ""
                )
                if module_value:
                    # 将模块名映射到 overview_modules
                    module_map = {
                        "system_config": "system",
                        "system": "system",
                        "storage": "storage",
                        "pt_sites": "sites",
                        "sites": "sites",
                        "downloaders": "downloaders",
                        "downloader": "downloaders",
                        "media_servers": "media_servers",
                        "media_server": "media_servers",
                        "organize": "organize",
                        "media_scraping": "media_scraping",
                        "scraping": "media_scraping",
                        "notifications": "notifications",
                        "notification": "notifications",
                        "login_security": "login_security",
                    }
                    mapped = module_map.get(module_value.lower(), module_value.lower())
                    return {"action": "overview", "overview_modules": [mapped]}
                return {"action": "overview", "overview_modules": ["all"]}

            elif "set" in name_lower or "update" in name_lower:
                return {
                    "action": "update",
                    **{k: v for k, v in arguments.items() if k in ("category", "key", "value", "description")},
                }

        logger.debug(
            f"参数适配: 无特殊映射规则，原样传递参数 ({original_name} -> {resolved_name})"
        )
        return arguments

    @classmethod
    async def execute_tool(
        cls,
        tool_name: str,
        db: AsyncSession,
        user_id: int,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        执行工具

        Args:
            tool_name: 工具名称
            db: 数据库会话
            user_id: 用户ID
            arguments: 调用参数

        Returns:
            执行结果
        """
        # 解析工具名称（支持模糊匹配纠正）
        resolved_name = cls.resolve_tool_name(tool_name)
        if not resolved_name:
            available = ", ".join(cls._tools.keys())
            return {
                "success": False,
                "error": f"未知工具: {tool_name}。可用工具: {available}",
            }

        # 如果工具名被纠正了，尝试适配参数
        if resolved_name != tool_name:
            arguments = cls._adapt_arguments(tool_name, resolved_name, arguments)

        tool_class = cls._tools[resolved_name]

        try:
            result = await tool_class.execute(db, user_id, arguments)
            return result
        except Exception as e:
            logger.exception(f"工具执行失败: {resolved_name}")
            return {
                "success": False,
                "error": str(e),
            }


def register_tool(cls: Type[BaseTool]) -> Type[BaseTool]:
    """
    工具注册装饰器

    用法:
    @register_tool
    class MyTool(BaseTool):
        name = "my_tool"
        ...
    """
    ToolRegistry.register(cls)
    return cls
