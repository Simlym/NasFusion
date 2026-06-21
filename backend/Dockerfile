# ==============================================================================
# NasFusion Backend Dockerfile
# 多阶段构建优化镜像大小
# ==============================================================================

FROM python:3.11-slim AS base

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 设置工作目录
WORKDIR /app

# ==============================================================================
# 构建阶段：用 uv 安装依赖到独立 venv
# ==============================================================================
FROM base AS builder

# 引入 uv 二进制（官方静态镜像，无需 pip 安装）
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /uvx /bin/

# ----------------------------------------------------------------------------
# 镜像源参数（默认官方源，对 GitHub CI 最快）。
# 国内本地构建可临时切清华，例如：
#   docker build \
#     --build-arg APT_MIRROR=mirrors.tuna.tsinghua.edu.cn \
#     --build-arg PIP_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple .
#   APT_MIRROR 为空（默认）时不替换 apt 源。
# ----------------------------------------------------------------------------
ARG APT_MIRROR=""
ARG PIP_INDEX="https://pypi.org/simple"

# 仅当显式传入 APT_MIRROR 时才替换 Debian 源
RUN if [ -n "$APT_MIRROR" ]; then \
        sed -i "s/deb.debian.org/${APT_MIRROR}/g" /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
        sed -i "s/deb.debian.org/${APT_MIRROR}/g" /etc/apt/sources.list; \
    fi

# 安装构建依赖（个别包无预编译 wheel 时需要编译）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libffi-dev \
    libxml2-dev \
    libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

# uv 配置：
#  - 用系统 Python（镜像自带 3.11），不让 uv 再下载
#  - 字节码预编译，加快容器启动
#  - PyPI 源由 PIP_INDEX 决定（默认官方）
ENV UV_PYTHON_DOWNLOADS=never \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_DEFAULT_INDEX=${PIP_INDEX}

# 先只复制依赖清单，最大化利用构建缓存（源码变更不会触发重装依赖）
COPY pyproject.toml uv.lock ./

# 按 lock 安装运行时依赖到项目内 .venv（--no-dev 排除测试/格式化工具，--no-install-project 不装自身）
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# ==============================================================================
# 运行阶段：最小化镜像
# ==============================================================================
FROM base AS runtime

# 镜像源参数（默认官方源；与 builder 阶段一致，国内本地构建可传 APT_MIRROR 切换）
ARG APT_MIRROR=""

# 仅当显式传入 APT_MIRROR 时才替换 Debian 源
RUN if [ -n "$APT_MIRROR" ]; then \
        sed -i "s/deb.debian.org/${APT_MIRROR}/g" /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
        sed -i "s/deb.debian.org/${APT_MIRROR}/g" /etc/apt/sources.list; \
    fi

# 安装运行时依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    # PostgreSQL 客户端库
    libpq5 \
    # 媒体信息工具
    mediainfo \
    # 网络工具（健康检查）
    curl \
    netcat-traditional \
    # 清理
    && rm -rf /var/lib/apt/lists/*

# 从构建阶段复制已装好依赖的虚拟环境
COPY --from=builder /app/.venv /app/.venv

# 让 venv 的可执行文件（uvicorn、alembic 等）直接可用
ENV PATH="/app/.venv/bin:$PATH"

# 创建非 root 用户（支持 PUID/PGID）
ARG PUID=1024
ARG PGID=100

RUN set -ex && \
    echo "Creating user with PUID=${PUID}, PGID=${PGID}" && \
    if getent group ${PGID} > /dev/null 2>&1; then \
        GROUP_NAME=$(getent group ${PGID} | cut -d: -f1); \
        echo "Using existing group: ${GROUP_NAME} (GID ${PGID})"; \
    else \
        groupadd -g ${PGID} nasfusion; \
        echo "Created new group: nasfusion (GID ${PGID})"; \
    fi && \
    useradd -u ${PUID} -g ${PGID} -m -s /bin/bash nasfusion && \
    echo "Created user: nasfusion (UID ${PUID}, GID ${PGID})"

# 复制应用代码（使用 --chown 直接设置所有者，避免权限继承问题）
COPY --chown=${PUID}:${PGID} . /app/

# 复制并设置 entrypoint.sh 权限
COPY --chown=${PUID}:${PGID} entrypoint.sh /usr/local/bin/entrypoint.sh

# 一次性设置所有权限（确保没有权限问题）
RUN chmod 755 /usr/local/bin/entrypoint.sh && \
    chmod -R 755 /app && \
    mkdir -p /app/data/torrents /app/data/logs /app/data/cache && \
    chown -R ${PUID}:${PGID} /app

# 应用版本号（由 CI 构建时通过 --build-arg APP_VERSION=<git-tag> 注入）
ARG APP_VERSION=dev
ENV APP_VERSION=${APP_VERSION}

# 设置 Python 路径
ENV PYTHONPATH=/app

# 切换到非 root 用户
USER ${PUID}:${PGID}

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动命令
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
