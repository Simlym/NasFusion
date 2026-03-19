# ==============================================================================
# NasFusion Frontend Dockerfile
# 多阶段构建：Node.js 构建 → Nginx 静态托管
# ==============================================================================

# ==============================================================================
# 构建阶段：编译 Vue3 应用
# ==============================================================================
FROM node:18-alpine as builder

WORKDIR /app

# 复制包管理文件
COPY package*.json ./

# 安装依赖（包含 devDependencies，构建需要 vue-tsc 等工具）
RUN npm ci

# 复制源代码和配置文件
COPY . .

# 构建生产版本（跳过类型检查以加快构建速度）
RUN npm run build:prod

# ==============================================================================
# 运行阶段：Nginx 静态文件服务
# ==============================================================================
FROM nginx:alpine

# 复制自定义 Nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 从构建阶段复制构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

# 确保静态文件权限正确
RUN chmod -R a+r /usr/share/nginx/html

# 暴露端口
EXPOSE 80

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost/ || exit 1

# Nginx 前台运行
CMD ["nginx", "-g", "daemon off;"]
