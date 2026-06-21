# -*- coding: utf-8 -*-
"""
AI Agent 工具注册表

管理所有可用的 Agent 工具
"""
import copy
import hashlib
import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Type

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.llm.base import ToolDefinition
from app.constants.ai_agent import AGENT_CONFIRM_FIELD


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

    # 是否为危险工具：True 时参与「二次确认协议」，schema 自动注入 __confirm__ 字段。
    # 是否每次都需要确认由 requires_confirmation(arguments) 决定（默认始终需要）。
    dangerous: bool = False

    @classmethod
    def requires_confirmation(cls, arguments: Dict[str, Any]) -> bool:
        """
        判断本次调用是否需要用户二次确认。

        默认：危险工具的所有调用都需确认。可被子类重写以实现条件危险
        （例如仅当 action=delete 时才需确认）。
        """
        return cls.dangerous

    @classmethod
    def get_confirmation_prompt(cls, arguments: Dict[str, Any]) -> str:
        """返回给用户的确认提示文案。子类应重写以描述具体的不可逆影响。"""
        return f"⚠️ 工具「{cls.name}」将执行一项不可逆操作，确认执行吗？"

    @classmethod
    def get_definition(cls) -> ToolDefinition:
        """获取工具定义（给 LLM）"""
        parameters = cls.parameters
        # 危险工具：在 schema 中显式声明 __confirm__，否则 LLM 无法回传确认令牌
        if cls.dangerous:
            parameters = copy.deepcopy(cls.parameters) if cls.parameters else {}
            parameters.setdefault("type", "object")
            parameters.setdefault("properties", {})
            parameters["properties"][AGENT_CONFIRM_FIELD] = {
                "type": "string",
                "description": (
                    "危险操作确认令牌。首次调用请勿填写；当工具返回 requires_confirmation 时，"
                    "在获得用户明确同意后，将返回的 confirmation_token 原样填入以执行。"
                ),
            }
        return ToolDefinition(
            name=cls.name,
            description=cls.description,
            parameters=parameters,
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

    @staticmethod
    def _confirmation_token(tool_name: str, arguments: Dict[str, Any]) -> str:
        """
        基于工具名 + 参数（排除确认字段本身）派生确认令牌。

        令牌与具体参数绑定：一旦 LLM 改动参数，旧令牌即失效，从而保证
        「用户看到的待确认操作」与「实际执行的操作」一致。
        """
        payload = {k: v for k, v in arguments.items() if k != AGENT_CONFIRM_FIELD}
        raw = tool_name + ":" + json.dumps(
            payload, sort_keys=True, ensure_ascii=False, default=str
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:8]

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

        # 危险操作二次确认：未携带有效确认令牌时，先返回确认请求而不执行
        try:
            needs_confirm = tool_class.requires_confirmation(arguments)
        except Exception:
            needs_confirm = getattr(tool_class, "dangerous", False)
        if needs_confirm:
            expected = cls._confirmation_token(resolved_name, arguments)
            if arguments.get(AGENT_CONFIRM_FIELD) != expected:
                logger.info(f"危险操作待用户确认: {resolved_name}")
                return {
                    "success": False,
                    "requires_confirmation": True,
                    "confirmation_token": expected,
                    "confirmation_prompt": tool_class.get_confirmation_prompt(arguments),
                    "message": "此操作涉及不可逆变更，需用户明确确认后才能执行。",
                }
            # 已确认：剥离确认字段，避免传入工具 execute 干扰业务逻辑
            arguments = {k: v for k, v in arguments.items() if k != AGENT_CONFIRM_FIELD}

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
