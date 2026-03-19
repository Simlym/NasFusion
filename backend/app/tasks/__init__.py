# -*- coding: utf-8 -*-
"""任务处理器模块"""
from app.tasks.base import BaseTaskHandler
from app.tasks.registry import TaskHandlerRegistry, register_all_handlers

__all__ = ["BaseTaskHandler", "TaskHandlerRegistry", "register_all_handlers"]
