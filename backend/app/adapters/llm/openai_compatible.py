# -*- coding: utf-8 -*-
"""
OpenAI Compatible 适配器

支持所有 OpenAI API 兼容的服务
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
from app.constants.ai_agent import LLM_PROVIDER_OPENAI


class OpenAICompatibleAdapter(BaseLLMAdapter):
    """通用 OpenAI 兼容适配器"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.validate_config(["api_key"])
        self.api_base = config.get("api_base", "https://api.openai.com/v1").rstrip("/")
        self.timeout = config.get("timeout", 120)
        if not self.model:
            self.model = "gpt-4o-mini"
        self.provider_hint = self._detect_provider()

    def _detect_provider(self) -> str:
        base_lower = self.api_base.lower()
        if "deepseek" in base_lower:
            return "deepseek"
        elif "ollama" in base_lower or "11434" in base_lower:
            return "ollama"
        elif "groq" in base_lower:
            return "groq"
        elif "azure" in base_lower:
            return "azure"
        elif "openai" in base_lower:
            return "openai"
        return "unknown"

    @property
    def provider_name(self) -> str:
        return self.config.get("provider_override", self.provider_hint)

    @property
    def supported_models(self) -> List[str]:
        return [
            "gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo",
            "deepseek-chat", "deepseek-reasoner",
            "kimi-k2.5", "kimi-k2", "kimi-k2-thinking",
            "moonshot-v1-auto", "moonshot-v1-128k", "moonshot-v1-32k", "moonshot-v1-8k",
            "llama-3.3-70b-versatile", "llama-3.1-8b-instant",
            "mixtral-8x7b-32768", "gemma2-9b-it",
            "llama3.2", "llama3.1", "qwen2.5", "phi4", "mistral",
        ]

    def _get_headers(self) -> Dict[str, str]:
        if self.provider_hint == "azure":
            return {
                "api-key": self.api_key,
                "Content-Type": "application/json",
            }
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _build_messages(self, messages: List[ChatMessage]) -> List[Dict[str, Any]]:
        """构建消息列表（支持多模态）"""
        result = []
        for msg in messages:
            # 处理多模态消息（有图片）
            if msg.images and self._is_multimodal_model():
                content_parts = []
                
                # 添加文本
                if msg.content:
                    content_parts.append({
                        "type": "text",
                        "text": msg.content,
                    })
                
                # 添加图片
                for img_base64 in msg.images:
                    content_parts.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{img_base64}",
                            "detail": "auto",
                        },
                    })
                
                message_dict = {
                    "role": msg.role,
                    "content": content_parts,
                }
            else:
                # 普通文本消息
                message_dict = {
                    "role": msg.role,
                    "content": msg.content,
                }
            
            if msg.name:
                message_dict["name"] = msg.name
            if msg.tool_call_id:
                message_dict["tool_call_id"] = msg.tool_call_id
            # 助手消息需要序列化 tool_calls（通过 extra="allow" 传入）
            if msg.role == "assistant" and hasattr(msg, "tool_calls") and msg.tool_calls:
                message_dict["tool_calls"] = [
                    {
                        "id": tc.get("id", ""),
                        "type": "function",
                        "function": {
                            "name": tc.get("name", ""),
                            "arguments": json.dumps(tc.get("arguments", {}), ensure_ascii=False),
                        },
                    }
                    for tc in msg.tool_calls
                ]
            result.append(message_dict)
        return result

    def _is_multimodal_model(self) -> bool:
        """检查当前模型是否支持多模态"""
        model_lower = self.model.lower()
        multimodal_keywords = ["gpt-4o", "gpt-4-turbo", "vision", "glm-4v", "llava"]
        return any(kw in model_lower for kw in multimodal_keywords)

    def _build_tools(self, tools) -> List[Dict[str, Any]]:
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

    def _parse_tool_calls(self, tool_calls_data) -> List[ToolCall]:
        result = []
        for tc in tool_calls_data:
            func = tc.get("function", {})
            arguments = func.get("arguments", "{}")
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

    def _get_chat_endpoint(self) -> str:
        if self.provider_hint == "azure":
            deployment = self.config.get("azure_deployment", self.model)
            api_version = self.config.get("azure_api_version", "2024-02-01")
            return f"{self.api_base}/openai/deployments/{deployment}/chat/completions?api-version={api_version}"
        return f"{self.api_base}/chat/completions"

    def _build_payload(
        self,
        messages,
        tools,
        tool_choice,
        stream,
        **kwargs
    ) -> Dict[str, Any]:
        payload = {
            "model": kwargs.get("model", self.model),
            "messages": self._build_messages(messages),
            "temperature": kwargs.get("temperature", self.temperature),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "top_p": kwargs.get("top_p", self.top_p),
            "stream": stream,
        }
        if self.provider_hint != "ollama":
            if kwargs.get("frequency_penalty") is not None:
                payload["frequency_penalty"] = kwargs["frequency_penalty"]
            if kwargs.get("presence_penalty") is not None:
                payload["presence_penalty"] = kwargs["presence_penalty"]
        if tools:
            payload["tools"] = self._build_tools(tools)
            if tool_choice:
                payload["tool_choice"] = tool_choice
        return payload

    async def chat(
        self,
        messages,
        tools=None,
        tool_choice=None,
        **kwargs
    ) -> ChatCompletionResponse:
        try:
            payload = self._build_payload(messages, tools, tool_choice, stream=False, **kwargs)
            url = self._get_chat_endpoint()
            client_kwargs = {"timeout": self.timeout}
            if self.proxy:
                client_kwargs["proxy"] = self.proxy
            async with httpx.AsyncClient(**client_kwargs) as client:
                response = await client.post(url, headers=self._get_headers(), json=payload)
                response.raise_for_status()
                data = response.json()
            choice = data.get("choices", [{}])[0]
            message = choice.get("message", {})
            usage = data.get("usage", {})
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
            error_text = e.response.text
            self.logger.error(f"OpenAI API 请求失败: {e.response.status_code} - {error_text[:500]}")
            try:
                error_data = e.response.json()
                error_msg = error_data.get("error", {}).get("message", error_text)
            except Exception:
                error_msg = error_text
            raise RuntimeError(f"API 错误 ({e.response.status_code}): {error_msg}")
        except Exception as e:
            self.logger.exception(f"OpenAI API 请求异常: {str(e)}")
            raise

    async def chat_stream(
        self,
        messages,
        tools=None,
        tool_choice=None,
        **kwargs
    ) -> AsyncGenerator[StreamEvent, None]:
        try:
            payload = self._build_payload(messages, tools, tool_choice, stream=True, **kwargs)
            url = self._get_chat_endpoint()
            client_kwargs = {"timeout": self.timeout}
            if self.proxy:
                client_kwargs["proxy"] = self.proxy
            tool_calls_acc = {}
            finish_reason = None
            async with httpx.AsyncClient(**client_kwargs) as client:
                async with client.stream("POST", url, headers=self._get_headers(), json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                break
                            try:
                                data = json.loads(data_str)
                                if "error" in data:
                                    error_msg = data["error"].get("message", "Unknown error")
                                    yield StreamEvent(type="error", content=error_msg)
                                    return
                                choice = data.get("choices", [{}])[0]
                                delta = choice.get("delta", {})
                                chunk_finish = choice.get("finish_reason")
                                if chunk_finish:
                                    finish_reason = chunk_finish
                                content = delta.get("content")
                                if content:
                                    yield StreamEvent(type="content", content=content)
                                delta_tool_calls = delta.get("tool_calls")
                                if delta_tool_calls:
                                    for tc_delta in delta_tool_calls:
                                        idx = tc_delta.get("index", 0)
                                        if idx not in tool_calls_acc:
                                            tool_calls_acc[idx] = {"id": "", "name": "", "arguments": ""}
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
            # 流结束后处理工具调用
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
            self.logger.error(f"OpenAI API 流式请求失败: {e.response.status_code}")
            raise
        except Exception as e:
            self.logger.exception(f"OpenAI API 流式请求异常: {str(e)}")
            raise

    async def test_connection(self) -> Dict[str, Any]:
        """测试连接"""
        try:
            start_time = time.time()
            messages = [ChatMessage(role="user", content="你好")]
            response = await self.chat(messages=messages, max_tokens=10)
            latency_ms = int((time.time() - start_time) * 1000)
            self.logger.info(f"OpenAI 连接测试成功: model={self.model}, latency={latency_ms}ms")
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
            self.logger.error(f"OpenAI 连接测试失败: {error_msg}")
            return {"success": False, "message": error_msg, "latency_ms": 0}
        except httpx.TimeoutException:
            return {"success": False, "message": "连接超时", "latency_ms": self.timeout * 1000}
        except Exception as e:
            self.logger.exception(f"OpenAI 连接测试异常: {str(e)}")
            return {"success": False, "message": f"测试异常: {str(e)}", "latency_ms": 0}
