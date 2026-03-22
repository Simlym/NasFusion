# -*- coding: utf-8 -*-
"""
智谱 AI (ZhipuAI) 适配器
支持 GLM-4 系列模型
"""
import json
import time
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx

from app.adapters.llm.base import (
    BaseLLMAdapter,
    ChatCompletionResponse,
    ChatMessage,
    StreamEvent,
    ToolCall,
    ToolDefinition,
)
from app.constants.ai_agent import (
    LLM_PROVIDER_ZHIPU,
    ZHIPU_API_BASE,
    ZHIPU_API_TIMEOUT,
    ZHIPU_MODELS,
)


class ZhipuAdapter(BaseLLMAdapter):
    """
    智谱 AI 适配器

    配置示例:
    {
        "api_key": "your-api-key",
        "model": "glm-4-flash",
        "temperature": 0.7,
        "max_tokens": 2048,
        "top_p": 0.9,
        "proxy": null
    }
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.validate_config(["api_key"])

        self.api_base = config.get("api_base", ZHIPU_API_BASE)
        self.timeout = config.get("timeout", ZHIPU_API_TIMEOUT)

        # 设置默认模型（如果未指定）
        if not self.model:
            self.model = "glm-4-flash"

    @property
    def provider_name(self) -> str:
        return LLM_PROVIDER_ZHIPU

    @property
    def supported_models(self) -> List[str]:
        return ZHIPU_MODELS

    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _build_messages(self, messages: List[ChatMessage]) -> List[Dict[str, Any]]:
        """构建消息列表"""
        result = []
        for msg in messages:
            message_dict = {
                "role": msg.role,
                "content": msg.content,
            }
            if msg.name:
                message_dict["name"] = msg.name
            if msg.tool_call_id:
                message_dict["tool_call_id"] = msg.tool_call_id
            result.append(message_dict)
        return result

    def _build_tools(self, tools: List[ToolDefinition]) -> List[Dict[str, Any]]:
        """构建工具列表"""
        result = []
        for tool in tools:
            result.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                }
            })
        return result

    def _parse_tool_calls(self, tool_calls_data: List[Dict]) -> List[ToolCall]:
        """解析工具调用"""
        result = []
        for tc in tool_calls_data:
            func = tc.get("function", {})
            arguments = func.get("arguments", "{}")

            # 解析 arguments（可能是字符串或字典）
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    arguments = {}

            result.append(ToolCall(
                id=tc.get("id", ""),
                name=func.get("name", ""),
                arguments=arguments,
            ))
        return result

    async def chat(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[ToolDefinition]] = None,
        tool_choice: Optional[str] = None,
        **kwargs
    ) -> ChatCompletionResponse:
        """
        发送聊天请求

        Args:
            messages: 消息列表
            tools: 可用工具列表
            tool_choice: 工具选择策略 (auto/none/required)
            **kwargs: 其他参数

        Returns:
            ChatCompletionResponse
        """
        try:
            # 构建请求体
            payload = {
                "model": kwargs.get("model", self.model),
                "messages": self._build_messages(messages),
                "temperature": kwargs.get("temperature", self.temperature),
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                "top_p": kwargs.get("top_p", self.top_p),
                "stream": False,
            }

            # 添加工具
            if tools:
                payload["tools"] = self._build_tools(tools)
                if tool_choice:
                    payload["tool_choice"] = tool_choice

            # 发送请求
            url = f"{self.api_base}/chat/completions"

            transport = None
            if self.proxy:
                transport = httpx.AsyncHTTPTransport(proxy=self.proxy)

            async with httpx.AsyncClient(
                timeout=self.timeout,
                transport=transport,
            ) as client:
                response = await client.post(
                    url,
                    headers=self._get_headers(),
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()

            # 解析响应
            choice = data.get("choices", [{}])[0]
            message = choice.get("message", {})
            usage = data.get("usage", {})

            # 检查是否有工具调用
            tool_calls = None
            tool_calls_data = message.get("tool_calls")
            if tool_calls_data:
                tool_calls = self._parse_tool_calls(tool_calls_data)

            return ChatCompletionResponse(
                content=message.get("content"),
                tool_calls=tool_calls,
                finish_reason=choice.get("finish_reason", "stop"),
                usage={
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                }
            )

        except httpx.HTTPStatusError as e:
            self.logger.error(f"智谱API请求失败: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            self.logger.exception(f"智谱API请求异常: {str(e)}")
            raise

    async def chat_stream(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[ToolDefinition]] = None,
        tool_choice: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        发送流式聊天请求

        Args:
            messages: 消息列表
            tools: 可用工具列表
            tool_choice: 工具选择策略
            **kwargs: 其他参数

        Yields:
            StreamEvent 事件
        """
        try:
            # 构建请求体
            payload = {
                "model": kwargs.get("model", self.model),
                "messages": self._build_messages(messages),
                "temperature": kwargs.get("temperature", self.temperature),
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                "top_p": kwargs.get("top_p", self.top_p),
                "stream": True,
            }

            # 添加工具
            if tools:
                payload["tools"] = self._build_tools(tools)
                if tool_choice:
                    payload["tool_choice"] = tool_choice

            # 发送请求
            url = f"{self.api_base}/chat/completions"

            transport = None
            if self.proxy:
                transport = httpx.AsyncHTTPTransport(proxy=self.proxy)

            # 累积工具调用的 delta 片段
            # key: index, value: {"id": str, "name": str, "arguments": str}
            tool_calls_acc: Dict[int, Dict[str, str]] = {}
            finish_reason = None

            async with httpx.AsyncClient(
                timeout=self.timeout,
                transport=transport,
            ) as client:
                async with client.stream(
                    "POST",
                    url,
                    headers=self._get_headers(),
                    json=payload,
                ) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        if not line:
                            continue

                        # 处理 SSE 格式
                        if line.startswith("data: "):
                            data_str = line[6:]

                            if data_str == "[DONE]":
                                break

                            try:
                                data = json.loads(data_str)
                                choice = data.get("choices", [{}])[0]
                                delta = choice.get("delta", {})
                                chunk_finish = choice.get("finish_reason")

                                if chunk_finish:
                                    finish_reason = chunk_finish

                                # 处理文本内容
                                content = delta.get("content")
                                if content:
                                    yield StreamEvent(type="content", content=content)

                                # 处理工具调用 delta
                                delta_tool_calls = delta.get("tool_calls")
                                if delta_tool_calls:
                                    for tc_delta in delta_tool_calls:
                                        idx = tc_delta.get("index", 0)
                                        if idx not in tool_calls_acc:
                                            tool_calls_acc[idx] = {
                                                "id": "",
                                                "name": "",
                                                "arguments": "",
                                            }
                                        acc = tool_calls_acc[idx]
                                        if tc_delta.get("id"):
                                            acc["id"] = tc_delta["id"]
                                        func = tc_delta.get("function", {})
                                        if func.get("name"):
                                            acc["name"] = func["name"]
                                        if func.get("arguments"):
                                            acc["arguments"] += func["arguments"]

                            except json.JSONDecodeError:
                                continue

            # 流结束后，如果有累积的工具调用，发出 tool_calls 事件
            if tool_calls_acc:
                parsed_tool_calls = []
                for idx in sorted(tool_calls_acc.keys()):
                    acc = tool_calls_acc[idx]
                    arguments = acc["arguments"]
                    if isinstance(arguments, str):
                        try:
                            arguments = json.loads(arguments)
                        except json.JSONDecodeError:
                            arguments = {}
                    parsed_tool_calls.append(ToolCall(
                        id=acc["id"],
                        name=acc["name"],
                        arguments=arguments,
                    ))
                yield StreamEvent(
                    type="tool_calls",
                    tool_calls=parsed_tool_calls,
                    finish_reason=finish_reason or "tool_calls",
                )
            else:
                yield StreamEvent(
                    type="done",
                    finish_reason=finish_reason or "stop",
                )

        except httpx.HTTPStatusError as e:
            self.logger.error(f"智谱API流式请求失败: {e.response.status_code}")
            raise
        except Exception as e:
            self.logger.exception(f"智谱API流式请求异常: {str(e)}")
            raise

    async def test_connection(self) -> Dict[str, Any]:
        """
        测试连接

        通过发送简单请求验证 API Key 是否有效
        """
        try:
            start_time = time.time()

            # 发送简单测试请求
            messages = [
                ChatMessage(role="user", content="你好")
            ]

            response = await self.chat(
                messages=messages,
                max_tokens=10,
            )

            latency_ms = int((time.time() - start_time) * 1000)

            self.logger.info(
                f"智谱AI连接测试成功: model={self.model}, latency={latency_ms}ms"
            )

            return {
                "success": True,
                "message": f"连接成功! 模型: {self.model}",
                "latency_ms": latency_ms,
                "model": self.model,
                "usage": response.usage,
            }

        except httpx.HTTPStatusError as e:
            error_msg = f"API请求失败: {e.response.status_code}"
            try:
                error_data = e.response.json()
                error_msg = error_data.get("error", {}).get("message", error_msg)
            except Exception:
                pass

            self.logger.error(f"智谱AI连接测试失败: {error_msg}")
            return {
                "success": False,
                "message": error_msg,
                "latency_ms": 0,
            }
        except httpx.TimeoutException:
            return {
                "success": False,
                "message": "连接超时",
                "latency_ms": self.timeout * 1000,
            }
        except Exception as e:
            self.logger.exception(f"智谱AI连接测试异常: {str(e)}")
            return {
                "success": False,
                "message": f"测试异常: {str(e)}",
                "latency_ms": 0,
            }
