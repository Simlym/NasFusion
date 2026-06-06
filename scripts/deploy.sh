#!/bin/bash
# ==============================================================================
# NasFusion 群晖 NAS 部署脚本
# 用于群晖任务计划，以 root 用户执行
# 执行方式：bash /volume4/dockers/NasFusion/scripts/deploy.sh
# ==============================================================================

PROJECT_DIR="/volume4/dockers/NasFusion"
LOG_FILE="$PROJECT_DIR/scripts/deploy.log"

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

echo "========================================" >> "$LOG_FILE"
log "开始部署"

# 切换到项目目录
cd "$PROJECT_DIR" || { log "错误：目录不存在 $PROJECT_DIR"; exit 1; }

# 拉取最新 compose / 配置（镜像由 CI 预构建，无需本地编译）
# git pull 以 admin 身份执行（SSH 密钥在 admin 的 ~/.ssh/）
log "拉取最新代码..."
su -s /bin/bash admin -c "cd $PROJECT_DIR && git pull origin main" >> "$LOG_FILE" 2>&1
if [ $? -ne 0 ]; then
    log "错误：git pull 失败，请检查 SSH 密钥和网络"
    exit 1
fi

log "拉取最新镜像..."
docker-compose pull >> "$LOG_FILE" 2>&1
if [ $? -ne 0 ]; then
    log "错误：docker-compose pull 失败，请检查网络或镜像源（IMAGE_REGISTRY）"
    exit 1
fi

log "镜像更新成功，开始启动容器..."

# 启动/更新容器（仅重建有变化的服务）
docker-compose up -d >> "$LOG_FILE" 2>&1
if [ $? -ne 0 ]; then
    log "错误：docker-compose 启动失败"
    log "查看详细日志：docker-compose logs"
    exit 1
fi

log "部署完成"
echo "========================================" >> "$LOG_FILE"
