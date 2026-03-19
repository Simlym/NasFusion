"""
日志配置模块
支持JSON和文本两种格式
"""
import logging
import sys
from pathlib import Path
from typing import Any, Dict

from pythonjsonlogger import jsonlogger

from app.core.config import settings


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """自定义JSON日志格式化器"""

    def __init__(self, *args, **kwargs):
        """初始化时设置 ensure_ascii=False 以正确显示中文"""
        # 设置 json_ensure_ascii=False 避免中文被转义
        kwargs.setdefault('json_ensure_ascii', False)
        super().__init__(*args, **kwargs)

    def add_fields(
        self,
        log_record: Dict[str, Any],
        record: logging.LogRecord,
        message_dict: Dict[str, Any],
    ) -> None:
        # 先调用父类方法添加基础字段
        super().add_fields(log_record, record, message_dict)

        # 添加自定义字段
        log_record["app"] = settings.APP_NAME
        log_record["env"] = "debug" if settings.DEBUG else "production"

    def _perform_rename_log_fields(self, log_record: Dict[str, Any]) -> None:
        """
        重写字段重命名方法，添加字段存在性检查
        避免SQLAlchemy等第三方库日志记录缺少字段时的KeyError
        """
        if not hasattr(self, 'rename_fields') or not self.rename_fields:
            return

        for old_field_name, new_field_name in self.rename_fields.items():
            if old_field_name in log_record:
                log_record[new_field_name] = log_record.pop(old_field_name)


def setup_logging() -> None:
    """
    配置应用日志
    根据配置选择JSON或文本格式
    """
    # 创建日志目录
    log_path = Path(settings.LOG_PATH)
    log_path.mkdir(parents=True, exist_ok=True)

    # 获取root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, settings.LOG_LEVEL))

    # 清除默认handler
    logger.handlers.clear()

    # 控制台handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, settings.LOG_LEVEL))

    # 文件handler
    file_handler = logging.FileHandler(
        log_path / f"{settings.APP_NAME.lower()}.log",
        encoding="utf-8",
    )
    file_handler.setLevel(getattr(logging, settings.LOG_LEVEL))

    # 根据配置选择格式化器
    if settings.LOG_FORMAT == "json":
        # JSON格式 - 使用标准字段名，通过重命名得到想要的字段名
        formatter = CustomJsonFormatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s",
            rename_fields={
                "levelname": "level",
                "asctime": "timestamp",
            },
        )
    else:
        # 文本格式
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    # 设置第三方库日志级别
    # SQLAlchemy的engine日志可能导致格式化问题，单独设置
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.dialects").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.orm").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    # APScheduler 日志级别 - 只显示重要信息
    logging.getLogger("apscheduler.scheduler").setLevel(logging.WARNING)
    logging.getLogger("apscheduler.executors").setLevel(logging.WARNING)
    logging.getLogger("apscheduler.job").setLevel(logging.WARNING)
    # 忽略passlib的bcrypt版本检查警告
    logging.getLogger("passlib.handlers.bcrypt").setLevel(logging.ERROR)


def get_logger(name: str) -> logging.Logger:
    """
    获取logger实例

    Args:
        name: logger名称，通常使用 __name__

    Returns:
        logging.Logger: logger实例
    """
    return logging.getLogger(name)
