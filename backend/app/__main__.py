"""
模块入口：支持 `python -m app` / `uv run python -m app` 启动开发服务器。

等价于 `app/main.py` 中 `if __name__ == "__main__"` 的逻辑，
统一收敛到此处，便于使用 uv 运行。
"""
import uvicorn

from app.core.config import settings


def main() -> None:
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )


if __name__ == "__main__":
    main()
