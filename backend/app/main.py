"""
FastAPI应用入口
"""
from contextlib import asynccontextmanager
from pathlib import Path

# 确保环境变量在导入配置前加载
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import async_session_local, close_db, engine
from app.core.init import initialize_system
from app.core.logging import setup_logging
from app.services.task.scheduler_manager import scheduler_manager
from app.events.manager import event_bus_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理

    启动时:
    - 初始化日志
    - 初始化数据库（开发环境）
    - 初始化管理员账户
    - 启动事件总线
    - 启动任务调度器

    关闭时:
    - 关闭任务调度器
    - 关闭事件总线
    - 关闭数据库连接
    """
    # 启动
    setup_logging()

    # 初始化系统
    async with async_session_local() as db:
        await initialize_system(engine, db)

    # 启动事件总线（在任务调度器之前）
    await event_bus_manager.start()

    # 启动任务调度器
    await scheduler_manager.start()

    yield

    # 关闭任务调度器
    await scheduler_manager.shutdown()

    # 关闭事件总线
    await event_bus_manager.stop()

    # 关闭数据库连接
    await close_db()


# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="PT站点媒体资源管理系统",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# 配置CORS
# 注意：当 allow_origins=["*"] 时，浏览器不允许携带凭证（Cookies/Authorization）
# 因此只有配置了具体域名时才启用 allow_credentials
_cors_allow_credentials = "*" not in settings.ALLOWED_HOSTS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=_cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件目录
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# 挂载媒体文件目录（用于访问海报、背景图等）
MEDIA_DATA_DIR = Path("./data/media")
MEDIA_DATA_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(MEDIA_DATA_DIR)), name="media")

# 创建图片缓存目录
IMAGE_CACHE_DIR = Path(settings.IMAGE_CACHE_PATH)
IMAGE_CACHE_DIR.mkdir(parents=True, exist_ok=True)


# 健康检查端点
@app.get("/health", tags=["健康检查"])
async def health_check():
    """健康检查"""
    return JSONResponse(
        content={
            "status": "healthy",
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
        }
    )


# 根路径
@app.get("/", tags=["根路径"])
async def root():
    """根路径"""
    return JSONResponse(
        content={
            "message": f"Welcome to {settings.APP_NAME}",
            "version": settings.APP_VERSION,
            "docs": "/docs" if settings.DEBUG else "Disabled in production",
        }
    )


# 注册API路由
from app.api.v1.router import api_router

app.include_router(api_router, prefix=settings.API_V1_PREFIX)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
