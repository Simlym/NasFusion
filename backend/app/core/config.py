"""
应用配置管理模块
使用Pydantic Settings进行配置管理，支持环境变量
"""
from functools import lru_cache
from typing import List, Optional
import pytz

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """数据库配置"""

    DB_TYPE: str = Field(default="sqlite", validation_alias="DB_TYPE", description="数据库类型: sqlite 或 postgresql")

    # SQLite配置
    SQLITE_PATH: str = Field(default="./data/nasfusion.db", description="SQLite数据库路径")

    # PostgreSQL配置
    POSTGRES_SERVER: Optional[str] = Field(default=None, description="PostgreSQL服务器地址")
    POSTGRES_USER: Optional[str] = Field(default=None, description="PostgreSQL用户名")
    POSTGRES_PASSWORD: Optional[str] = Field(default=None, description="PostgreSQL密码")
    POSTGRES_DB: Optional[str] = Field(default=None, description="PostgreSQL数据库名")
    POSTGRES_PORT: int = Field(default=5432, description="PostgreSQL端口")

    @property
    def DATABASE_URL(self) -> str:
        """生成数据库连接URL"""
        if self.DB_TYPE.lower() == "sqlite":
            return f"sqlite+aiosqlite:///{self.SQLITE_PATH}"
        elif self.DB_TYPE.lower() == "postgresql":
            if not all([self.POSTGRES_SERVER, self.POSTGRES_USER, self.POSTGRES_PASSWORD, self.POSTGRES_DB]):
                raise ValueError("PostgreSQL配置不完整")
            return (
                f"postgresql+asyncpg://{self.POSTGRES_USER}:"
                f"{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:"
                f"{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )
        else:
            raise ValueError(f"不支持的数据库类型: {self.DB_TYPE}")

    model_config = SettingsConfigDict(
        env_prefix="DB_",
        env_file=None,  # 不强制要求 .env 文件，优先使用环境变量
        case_sensitive=True,
        extra="ignore"
    )


class CelerySettings(BaseSettings):
    """Celery配置"""

    BROKER_URL: str = Field(default="redis://localhost:6379/0", description="Celery broker URL")
    RESULT_BACKEND: str = Field(default="redis://localhost:6379/0", description="Celery result backend")

    model_config = SettingsConfigDict(
        env_prefix="CELERY_",
        env_file=None,
        extra="ignore"
    )


class RedisSettings(BaseSettings):
    """Redis配置"""

    HOST: str = Field(default="localhost", description="Redis主机")
    PORT: int = Field(default=6379, description="Redis端口")
    DB: int = Field(default=0, description="Redis数据库编号")
    PASSWORD: Optional[str] = Field(default=None, description="Redis密码")

    @property
    def REDIS_URL(self) -> str:
        """生成Redis连接URL"""
        if self.PASSWORD:
            return f"redis://:{self.PASSWORD}@{self.HOST}:{self.PORT}/{self.DB}"
        return f"redis://{self.HOST}:{self.PORT}/{self.DB}"

    model_config = SettingsConfigDict(
        env_prefix="REDIS_",
        env_file=None,
        extra="ignore"
    )


class OpenAISettings(BaseSettings):
    """OpenAI配置"""

    API_KEY: Optional[str] = Field(default=None, description="OpenAI API密钥")
    API_BASE: str = Field(default="https://api.openai.com/v1", description="OpenAI API基础URL")
    PROXY: Optional[str] = Field(default=None, description="代理服务器URL")
    MODEL: str = Field(default="gpt-3.5-turbo", description="默认使用的模型")

    model_config = SettingsConfigDict(
        env_prefix="OPENAI_",
        env_file=None,
        extra="ignore"
    )


class Settings(BaseSettings):
    """主配置类"""

    # 应用基础配置
    APP_NAME: str = Field(default="NasFusion", description="应用名称")
    APP_VERSION: str = Field(default="0.1.0", description="应用版本")
    DEBUG: bool = Field(default=False, description="是否开启调试模式")
    SECRET_KEY: str = Field(..., description="应用密钥，用于加密")

    # API配置
    API_V1_PREFIX: str = Field(default="/api/v1", description="API v1路径前缀")
    ALLOWED_HOSTS: List[str] = Field(default=["*"], description="允许的主机列表")

    # 子配置
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    celery: CelerySettings = Field(default_factory=CelerySettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    openai: OpenAISettings = Field(default_factory=OpenAISettings)

    # 外部API配置
    TMDB_API_KEY: Optional[str] = Field(default=None, description="TMDB API密钥")
    TMDB_LANGUAGE: str = Field(default="zh-CN", description="TMDB语言设置")

    # 豆瓣API配置（Frodo移动端API，来自开源社区公开密钥）
    DOUBAN_API_KEY: str = Field(
        default="0dad551ec0f84ed02907ff5c42e8ec70",
        description="豆瓣API Key（GET请求）"
    )
    DOUBAN_API_KEY2: str = Field(
        default="0ab215a8b1977939201640fa14c66bab",
        description="豆瓣API Key（POST请求）"
    )
    DOUBAN_API_SECRET: str = Field(
        default="bf7dddc7c9cfe6f7",
        description="豆瓣API签名密钥"
    )

    # 文件路径配置
    DATA_DIR: str = Field(default="./data", description="数据根目录")

    # ===== 存储卷配置 =====
    VOLUME_MOUNTS_BASE: str = Field(default="/mnt", description="卷挂载基础目录（Docker模式）")

    # ===== 其他路径配置 =====
    TORRENT_PATH: str = Field(default="./data/torrents", description="种子文件目录")
    LOG_PATH: str = Field(default="./data/logs", description="日志目录")
    IMAGE_CACHE_PATH: str = Field(default="./data/cache/images", description="图片缓存目录")

    # 任务配置
    SYNC_INTERVAL_MINUTES: int = Field(default=30, description="PT站点同步间隔（分钟）")
    SUBSCRIPTION_CHECK_INTERVAL_MINUTES: int = Field(default=60, description="订阅检查间隔（分钟）")
    AI_RECOMMENDATION_CRON: str = Field(default="0 3 * * *", description="AI推荐cron表达式")



    # 日志配置
    LOG_LEVEL: str = Field(default="INFO", description="日志级别")
    LOG_FORMAT: str = Field(default="json", description="日志格式: json 或 text")

    # JWT配置
    JWT_SECRET_KEY: Optional[str] = Field(default=None, description="JWT密钥")
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT算法")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, description="JWT访问令牌过期时间（分钟）")
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, description="JWT刷新令牌过期时间（天）")

    # 时区配置
    TIMEZONE: str = Field(default="Asia/Shanghai", description="系统默认时区")
    TIMEZONE_OFFSET: str = Field(default="+08:00", description="时区偏移量")

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """验证SECRET_KEY不能为空且长度足够"""
        if not v or v == "your-secret-key-here-change-in-production":
            raise ValueError("请设置安全的SECRET_KEY")
        if len(v) < 32:
            raise ValueError("SECRET_KEY长度至少32个字符")
        return v

    def get_timezone(self):
        """获取时区对象"""
        return pytz.timezone(self.TIMEZONE)

    def get_local_time(self, utc_datetime=None):
        """将UTC时间转换为本地时间"""
        if utc_datetime is None:
            from datetime import datetime, timezone
            utc_datetime = datetime.now(timezone.utc)

        if utc_datetime.tzinfo is None:
            # 如果没有时区信息，假设是UTC时间
            utc_datetime = utc_datetime.replace(tzinfo=timezone.utc)

        return utc_datetime.astimezone(self.get_timezone())

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    获取设置实例（使用缓存）
    """
    return Settings()

# 直接初始化 - Pydantic 会自动读取环境变量
try:
    settings = Settings()
except Exception as e:
    import sys
    print("\n" + "=" * 60)
    print("❌ 配置初始化失败，请检查环境变量或 .env 文件")
    print("=" * 60)
    print(f"\n错误详情：{e}")
    print("\n解决方案：")
    print("  1. 复制 .env.example 为 .env：")
    print("       cp .env.example .env")
    print("  2. 编辑 .env，至少设置以下必填项：")
    print("       SECRET_KEY=<32位以上的随机字符串>")
    print("\n  快速生成 SECRET_KEY：")
    print("       python -c \"import secrets; print(secrets.token_hex(32))\"")
    print("=" * 60 + "\n")
    sys.exit(1)
