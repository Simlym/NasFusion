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
        tool_class = cls.get_tool(tool_name)
        if not tool_class:
            return {
                "success": False,
                "error": f"未知工具: {tool_name}",
            }

        try:
            # 使用嵌套事务（Savepoint）
            # 这样如果工具执行失败，不会回滚整个事务，只会回滚工具执行的部分
            async with db.begin_nested():
                result = await tool_class.execute(db, user_id, arguments)
            return result
        except Exception as e:
            logger.exception(f"工具执行失败: {tool_name}")
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
