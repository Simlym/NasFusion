"""事务内写入的工作流事件；投递记录永久保留，用作业务去重凭据。"""
from sqlalchemy import Column, ForeignKey, Integer, String, Text

from app.constants.durable_event import EVENT_PENDING
from app.core.db_types import JSON, TZDateTime
from app.models.base import BaseModel


class WorkflowEvent(BaseModel):
    __tablename__ = "workflow_events"

    business_key = Column(String(160), nullable=False, unique=True)
    event_type = Column(String(80), nullable=False)
    payload = Column(JSON, nullable=False)
    status = Column(String(20), nullable=False, default=EVENT_PENDING, index=True)
    execution_id = Column(
        Integer, ForeignKey("task_executions.id", ondelete="SET NULL"), nullable=True,
    )
    delivered_at = Column(TZDateTime(), nullable=True)
    attempts = Column(Integer, nullable=False, default=0)
    next_attempt_at = Column(TZDateTime(), nullable=True)
    last_error = Column(Text, nullable=True)
