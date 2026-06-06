# ==============================================================================
# NasFusion 网关镜像（前端静态文件 + 反向代理合二为一）
# ==============================================================================
# 说明：
#   - 原先 frontend 容器 + nginx 容器是两层 nginx 套娃，这里合并为一个网关容器
#   - 阶段一用 Node 编译 Vue 前端，阶段二用 nginx 直接托管 dist 并反代后端
#   - build context 为「项目根目录」（见 docker-compose / CI），以便同时访问
#     frontend/ 与 nginx/ 两个目录
# ==============================================================================

# ------------------------------------------------------------------------------
# 阶段一：编译前端
# ------------------------------------------------------------------------------
FROM node:18-alpine AS frontend-builder

WORKDIR /app

# 使用 npm 国内镜像源加速（构建在 CI / NAS 上都更稳）
RUN npm config set registry https://registry.npmmirror.com

# 先装依赖（利用 Docker 层缓存）
COPY frontend/package*.json ./
RUN npm ci

# 再拷源码并构建生产产物
COPY frontend/ ./
RUN npm run build:prod

# ------------------------------------------------------------------------------
# 阶段二：nginx 网关
# ------------------------------------------------------------------------------
FROM nginx:alpine

# 网关反向代理 + 前端静态托管配置（统一入口）
COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf

# 前端构建产物
COPY --from=frontend-builder /app/dist /usr/share/nginx/html

RUN chmod -R a+r /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost/health || exit 1

CMD ["nginx", "-g", "daemon off;"]
