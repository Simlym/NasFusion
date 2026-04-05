# -*- coding: utf-8 -*-
"""
LLM 配置数据库模型
"""
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text

from app.core.db_types import TZDateTime
from app.models.base import BaseModel


class LLMConfig(BaseModel):
    """
    LLM 配置表

    管理员在系统设置中维护的全局 LLM 供应商配置
    """

    __tablename__ = "llm_configs"

    name = Column(
        String(100),
        nullable=False,
        comment="配置名称，如'我的OpenAI'",
    )
    provider = Column(
        String(50),
        nullable=False,
        comment="LLM供应商: zhipu, openai, deepseek等",
    )
    api_key = Column(
        Text,
        nullable=False,
        comment="API密钥（加密存储）",
    )
    api_base = Column(
        String(500),
        nullable=True,
        comment="API基础URL（可选）",
    )
    proxy = Column(
        String(255),
        nullable=True,
        comment="代理服务器URL",
    )
    model = Column(
        String(100),
        nullable=False,
        comment="默认模型",
    )
    default_temperature = Column(
        String(10),
        nullable=False,
        default="0.7",
        comment="默认温度参数",
    )
    default_max_tokens = Column(
        Integer,
        nullable=False,
        default=2048,
        comment="默认最大Token数",
    )
    default_top_p = Column(
        String(10),
        nullable=False,
        default="0.9",
        comment="默认Top-P参数",
    )
    is_enabled = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="是否启用",
    )
    sort_order = Column(
        Integer,
        nullable=False,
        default=0,
        comment="排序顺序",
    )
    last_test_at = Column(
        TZDateTime(),
        nullable=True,
        comment="最后测试时间",
    )
    last_test_result = Column(
        Text,
        nullable=True,
        comment="最后测试结果",
    )
