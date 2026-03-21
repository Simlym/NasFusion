"""
ORM基础模型
定义所有model的基类和通用Mixin
"""
from typing import Any

from sqlalchemy import Column, Integer
from sqlalchemy.orm import DeclarativeBase, declared_attr

from app.core.json_types import TZDateTime
from app.utils.timezone import now


class Base(DeclarativeBase):
    """ORM基类"""

    pass


class TimestampMixin:
    """时间戳Mixin"""

    created_at = Column(
        TZDateTime(),
        default=now,
        nullable=False,
        comment="创建时间"
    )
    updated_at = Column(
        TZDateTime(),
        default=now,
        onupdate=now,
        nullable=False,
        comment="更新时间",
    )


class IDMixin:
    """主键ID Mixin"""

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, comment="主键ID")


class BaseModel(Base, IDMixin, TimestampMixin):
    """
    基础Model类
    包含id, created_at, updated_at字段
    所有model都应继承此类
    """

    __abstract__ = True

    @declared_attr
    def __tablename__(cls) -> str:
        """自动生成表名（类名转小写）"""
        return cls.__name__.lower()

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
