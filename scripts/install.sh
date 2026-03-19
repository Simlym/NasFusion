#!/bin/bash
# ==============================================================================
# NasFusion 一键安装脚本
# ==============================================================================

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "======================================"
echo "  NasFusion 安装向导"
echo "======================================"
echo ""

# 检测 Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}错误：未检测到 Docker，请先安装 Docker${NC}"
    echo "安装指南：https://docs.docker.com/get-docker/"
    exit 1
fi

# 检测 Docker Compose
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}错误：未检测到 Docker Compose，请先安装${NC}"
    echo "安装指南：https://docs.docker.com/compose/install/"
    exit 1
fi

echo -e "${GREEN}✓${NC} Docker 和 Docker Compose 检测通过"
echo ""

# 检查是否已存在配置文件
if [ -f "backend/.env" ]; then
    echo -e "${YELLOW}警告：检测到现有配置文件 backend/.env${NC}"
    read -p "是否覆盖现有配置？(y/N): " overwrite
    if [[ ! $overwrite =~ ^[Yy]$ ]]; then
        echo "安装已取消"
        exit 0
    fi
fi

echo "======================================"
echo "  配置向导"
echo "======================================"
echo ""

# 生成随机密钥
generate_secret() {
    openssl rand -hex 32 2>/dev/null || cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 64 | head -n 1
}

SECRET_KEY=$(generate_secret)
JWT_SECRET_KEY=$(generate_secret)

# 数据库配置
read -p "PostgreSQL 数据库密码 [自动生成]: " DB_PASSWORD
if [ -z "$DB_PASSWORD" ]; then
    DB_PASSWORD=$(generate_secret | head -c 20)
fi

# TMDB API Key
echo ""
echo "TMDB API Key 是必需的（用于获取电影/电视剧元数据）"
echo "获取地址：https://www.themoviedb.org/settings/api"
read -p "请输入 TMDB API Key: " TMDB_API_KEY
while [ -z "$TMDB_API_KEY" ]; do
    echo -e "${RED}TMDB API Key 不能为空${NC}"
    read -p "请输入 TMDB API Key: " TMDB_API_KEY
done

# OpenAI API Key（可选）
echo ""
read -p "OpenAI API Key（用于 AI 推荐，可选，回车跳过）: " OPENAI_API_KEY

# NAS 用户权限配置
echo ""
echo "NAS 用户权限配置（解决文件权限问题）"
echo "执行 'id' 命令查看你的 UID 和 GID"
read -p "PUID [1000]: " PUID
PUID=${PUID:-1000}
read -p "PGID [1000]: " PGID
PGID=${PGID:-1000}

# 数据目录配置
echo ""
echo "数据目录配置"
echo "群晖示例：/volume1/docker/nasfusion"
echo "威联通示例：/share/Container/nasfusion"
read -p "数据根目录 [./data]: " DATA_ROOT
DATA_ROOT=${DATA_ROOT:-./data}

# 创建配置文件
echo ""
echo "正在生成配置文件..."

cp backend/.env.production backend/.env

# 替换配置项
sed -i "s/SECRET_KEY=.*/SECRET_KEY=$SECRET_KEY/" backend/.env
sed -i "s/JWT_SECRET_KEY=.*/JWT_SECRET_KEY=$JWT_SECRET_KEY/" backend/.env
sed -i "s/DB_POSTGRES_PASSWORD=.*/DB_POSTGRES_PASSWORD=$DB_PASSWORD/" backend/.env
sed -i "s/TMDB_API_KEY=.*/TMDB_API_KEY=$TMDB_API_KEY/" backend/.env
sed -i "s/PUID=.*/PUID=$PUID/" backend/.env
sed -i "s/PGID=.*/PGID=$PGID/" backend/.env

if [ -n "$OPENAI_API_KEY" ]; then
    sed -i "s/OPENAI_API_KEY=.*/OPENAI_API_KEY=$OPENAI_API_KEY/" backend/.env
fi

# 创建数据目录
echo "正在创建数据目录..."
mkdir -p "$DATA_ROOT"/{media,downloads,torrents,logs,cache/nginx}

echo -e "${GREEN}✓${NC} 配置文件生成完成"
echo ""

# 拉取镜像
echo "======================================"
echo "  拉取 Docker 镜像"
echo "======================================"
echo ""

docker-compose pull

echo ""
echo "======================================"
echo "  启动服务"
echo "======================================"
echo ""

docker-compose up -d

echo ""
echo "等待服务就绪..."
sleep 10

# 检查服务状态
docker-compose ps

echo ""
echo "======================================"
echo "  安装完成！"
echo "======================================"
echo ""
echo -e "${GREEN}访问地址：http://localhost${NC}"
echo ""
echo "默认管理员账号："
echo "  用户名：admin"
echo "  密码：admin123（首次登录后请立即修改）"
echo ""
echo "其他命令："
echo "  查看日志：docker-compose logs -f"
echo "  停止服务：docker-compose down"
echo "  重启服务：docker-compose restart"
echo "  升级版本：bash scripts/upgrade.sh"
echo ""
echo -e "${YELLOW}提示：请妥善保管 backend/.env 文件中的密钥${NC}"
echo ""
