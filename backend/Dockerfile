# ==============================================================================
# NasFusion Backend Dockerfile
# 多阶段构建优化镜像大小
# ==============================================================================

FROM python:3.11-slim as base

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 设置工作目录
WORKDIR /app

# ==============================================================================
# 构建阶段：安装依赖
# ==============================================================================
FROM base as builder

# 配置 apt 使用清华镜像源加速下载
RUN sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
    sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list

# 安装构建依赖（优化：移除 g++，添加必要的库）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libffi-dev \
    libxml2-dev \
    libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 配置 pip 使用国内镜像源并安装 Python 依赖
# 使用清华镜像提高下载速度和成功率
# 使用预编译包加速构建
RUN pip install --upgrade pip setuptools wheel -i https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip install --no-warn-script-location \
    --prefer-binary \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    --trusted-host pypi.tuna.tsinghua.edu.cn \
    -r requirements.txt

# ==============================================================================
# 运行阶段：最小化镜像
# ==============================================================================
FROM base as runtime

# 配置 apt 使用清华镜像源加速下载
RUN sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
    sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list

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

# 从构建阶段复制 Python 依赖（系统安装的包）
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

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
