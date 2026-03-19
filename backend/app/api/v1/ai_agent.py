# -*- coding: utf-8 -*-
"""
AI Agent API 接口
"""
import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

logger = logging.getLogger(__name__)
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models import User
from app.schemas.ai_agent import (
    AIAgentConfigCreate,
    AIAgentConfigResponse,
    AIAgentConfigUpdate,
    AIChatRequest,
    AIChatResponse,
    AIConnectionTestRequest,
    AIConnectionTestResponse,
    AIConversationCreate,
    AIConversationDetailResponse,
    AIConversationListResponse,
    AIConversationResponse,
    AIConversationUpdate,
    AIMessageResponse,
    LLMProviderInfo,
    LLMProvidersResponse,
)
from app.services.ai_agent import AIAgentService
from app.adapters.llm import get_llm_adapter, get_supported_providers
from app.constants.ai_agent import (
    LLM_PROVIDER_DISPLAY_NAMES,
    ZHIPU_MODELS,
    ZHIPU_MODEL_DISPLAY_NAMES,
    LLM_PROVIDER_ZHIPU,
)

router = APIRouter(prefix="/ai-agent", tags=["AI Agent"])


# ==================== 供应商信息 ====================

@router.get("/providers", response_model=LLMProvidersResponse)
async def get_providers():
    """获取支持的LLM供应商列表"""
    providers = []

    # 智谱
    providers.append(LLMProviderInfo(
        provider=LLM_PROVIDER_ZHIPU,
        display_name=LLM_PROVIDER_DISPLAY_NAMES.get(LLM_PROVIDER_ZHIPU, "智谱AI"),
        models=[
            {"id": model, "name": ZHIPU_MODEL_DISPLAY_NAMES.get(model, model)}
            for model in ZHIPU_MODELS
        ],
        supports_tools=True,
        supports_streaming=True,
    ))

    # 未来扩展其他供应商...

    return LLMProvidersResponse(providers=providers)


# ==================== 配置管理 ====================

@router.get("/config", response_model=Optional[AIAgentConfigResponse])
async def get_config(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取AI Agent配置"""
    config = await AIAgentService.get_config(db, current_user.id)
    if not config:
        return None
    return AIAgentConfigResponse.model_validate(config)


@router.post("/config", response_model=AIAgentConfigResponse)
async def create_config(
    config_data: AIAgentConfigCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建AI Agent配置"""
    config = await AIAgentService.create_or_update_config(
        db,
        current_user.id,
        config_data.model_dump(exclude_unset=True),
    )
    return AIAgentConfigResponse.model_validate(config)


@router.put("/config", response_model=AIAgentConfigResponse)
async def update_config(
    config_data: AIAgentConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新AI Agent配置"""
    config = await AIAgentService.create_or_update_config(
        db,
        current_user.id,
        config_data.model_dump(exclude_unset=True),
    )
    return AIAgentConfigResponse.model_validate(config)


@router.post("/config/test", response_model=AIConnectionTestResponse)
async def test_connection(
    test_data: AIConnectionTestRequest,
    current_user: User = Depends(get_current_user),
):
    """测试LLM连接"""
    try:
        adapter = get_llm_adapter(
            test_data.provider,
            {
                "api_key": test_data.api_key,
                "api_base": test_data.api_base,
                "proxy": test_data.proxy,
                "model": test_data.model,
            }
        )
        result = await adapter.test_connection()
        return AIConnectionTestResponse(**result)
    except Exception as e:
        return AIConnectionTestResponse(
            success=False,
            message=f"连接失败: {str(e)}",
            latency_ms=0,
        )


# ==================== 对话管理 ====================

@router.get("/conversations", response_model=AIConversationListResponse)
async def list_conversations(
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取对话列表"""
    conversations, total = await AIAgentService.list_conversations(
        db,
        current_user.id,
        page=page,
        page_size=page_size,
        status=status,
    )
    return AIConversationListResponse(
        items=[AIConversationResponse.model_validate(c) for c in conversations],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/conversations", response_model=AIConversationResponse)
async def create_conversation(
    data: AIConversationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建新对话"""
    conversation = await AIAgentService.create_conversation(
        db,
        current_user.id,
        source=data.source,
        telegram_chat_id=data.telegram_chat_id,
        title=data.title,
    )
    return AIConversationResponse.model_validate(conversation)


@router.get("/conversations/{conversation_id}", response_model=AIConversationDetailResponse)
async def get_conversation(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取对话详情（包含消息）"""
    conversation = await AIAgentService.get_conversation(
        db,
        conversation_id,
        current_user.id,
    )
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="对话不存在",
        )

    messages = await AIAgentService.get_conversation_messages(
        db,
        conversation_id,
    )

    # 手动构造响应对象，避免触发 SQLAlchemy 关系加载
    return AIConversationDetailResponse(
        id=conversation.id,
        user_id=conversation.user_id,
        title=conversation.title,
        source=conversation.source,
        telegram_chat_id=conversation.telegram_chat_id,
        status=conversation.status,
        message_count=conversation.message_count,
        last_message_at=conversation.last_message_at,
        context_summary=conversation.context_summary,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=[AIMessageResponse.model_validate(m) for m in messages],
    )


@router.put("/conversations/{conversation_id}", response_model=AIConversationResponse)
async def update_conversation(
    conversation_id: int,
    data: AIConversationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新对话"""
    conversation = await AIAgentService.get_conversation(
        db,
        conversation_id,
        current_user.id,
    )
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="对话不存在",
        )

    if data.title is not None:
        conversation.title = data.title
    if data.status is not None:
        conversation.status = data.status

    await db.commit()
    await db.refresh(conversation)

    return AIConversationResponse.model_validate(conversation)


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除对话"""
    conversation = await AIAgentService.get_conversation(
        db,
        conversation_id,
        current_user.id,
    )
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="对话不存在",
        )

    conversation.status = "deleted"
    await db.commit()

    return {"message": "对话已删除"}


# ==================== 聊天 ====================

@router.post("/chat", response_model=AIChatResponse)
async def chat(
    request: AIChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """发送聊天消息"""
    if request.stream:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="流式输出请使用 /chat/stream 接口",
        )

    try:
        logger.info(f"用户 {current_user.id} 发送聊天消息: {request.message[:50]}...")

        result = await AIAgentService.chat(
            db,
            current_user.id,
            request.message,
            request.conversation_id,
        )

        if not result.get("success"):
            error_msg = result.get("error", "聊天失败")
            logger.error(f"AI聊天失败 - 用户: {current_user.id}, 错误: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_msg,
            )

        logger.info(f"AI聊天成功 - 用户: {current_user.id}, 对话: {result['conversation_id']}")

        return AIChatResponse(
            conversation_id=result["conversation_id"],
            message_id=result["message_id"],
            content=result["content"],
            tool_calls=result.get("tool_calls"),
            tool_results=result.get("tool_results"),
            finish_reason=result.get("finish_reason", "stop"),
            usage=result.get("usage"),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"AI聊天异常 - 用户: {current_user.id}, 消息: {request.message[:50]}, 错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"聊天服务异常: {str(e)}",
        )


@router.post("/chat/stream")
async def chat_stream(
    request: AIChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """流式聊天"""
    # 提前提取基本类型值，避免生成器内访问已分离的 SQLAlchemy 对象
    user_id = current_user.id

    async def generate():
        try:
            async for chunk in AIAgentService.chat_stream(
                db,
                user_id,
                request.message,
                request.conversation_id,
            ):
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.exception(f"流式聊天异常 - 用户: {user_id}, 错误: {str(e)}")
            error_chunk = {"type": "error", "error": f"聊天服务异常: {str(e)}"}
            yield f"data: {json.dumps(error_chunk, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
        },
    )


# ==================== 工具信息 ====================

@router.get("/tools")
async def get_tools(
    current_user: User = Depends(get_current_user),
):
    """获取可用工具列表"""
    from app.services.ai_agent.tool_registry import ToolRegistry

    tools = ToolRegistry.get_all_tools()
    return {
        "tools": [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            }
            for tool in tools.values()
        ]
    }
