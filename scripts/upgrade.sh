#!/bin/bash
# ==============================================================================
# NasFusion 一键升级脚本
# ==============================================================================

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "======================================"
echo "  NasFusion 版本升级"
echo "======================================"
echo ""

# 检查是否在项目根目录
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}错误：请在项目根目录执行此脚本${NC}"
    exit 1
fi

# 检查配置文件
if [ ! -f "backend/.env" ]; then
    echo -e "${RED}错误：未找到配置文件 backend/.env${NC}"
    echo "请先运行安装脚本：bash scripts/install.sh"
    exit 1
fi

# 获取当前版本
CURRENT_VERSION=$(docker-compose ps backend | grep nasfusion-backend | awk '{print $2}' || echo "unknown")

echo "当前版本：$CURRENT_VERSION"
echo ""

# 确认升级
read -p "是否继续升级到最新版本？(y/N): " confirm
if [[ ! $confirm =~ ^[Yy]$ ]]; then
    echo "升级已取消"
    exit 0
fi

echo ""
echo "======================================"
echo "  步骤 1：备份数据"
echo "======================================"
echo ""

# 调用备份脚本
if [ -f "scripts/backup.sh" ]; then
    bash scripts/backup.sh
else
    echo -e "${YELLOW}警告：未找到备份脚本，跳过自动备份${NC}"
    echo "建议手动备份数据库和配置文件"
    read -p "继续升级？(y/N): " continue_upgrade
    if [[ ! $continue_upgrade =~ ^[Yy]$ ]]; then
        echo "升级已取消"
        exit 0
    fi
fi

echo ""
echo "======================================"
echo "  步骤 2：拉取最新镜像"
echo "======================================"
echo ""

docker-compose pull

echo ""
echo "======================================"
echo "  步骤 3：停止旧容器"
echo "======================================"
echo ""

docker-compose down

echo ""
echo "======================================"
echo "  步骤 4：启动新容器"
echo "======================================"
echo ""

docker-compose up -d

echo ""
echo "等待服务就绪..."
sleep 15

echo ""
echo "======================================"
echo "  步骤 5：健康检查"
echo "======================================"
echo ""

# 检查后端健康状态
echo "检查后端服务..."
for i in {1..10}; do
    if docker exec nasfusion-backend curl -f http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} 后端服务健康"
        break
    fi
    if [ $i -eq 10 ]; then
        echo -e "${RED}✗${NC} 后端服务启动失败"
        echo "查看日志：docker-compose logs backend"
        echo ""
        echo "尝试回滚到备份..."
        read -p "是否回滚？(y/N): " rollback
        if [[ $rollback =~ ^[Yy]$ ]]; then
            docker-compose down
            # 这里可以调用 restore.sh 进行回滚
            echo "请手动运行 bash scripts/restore.sh 进行恢复"
        fi
        exit 1
    fi
    echo "等待后端服务启动... ($i/10)"
    sleep 3
done

# 显示服务状态
echo ""
docker-compose ps

echo ""
echo "======================================"
echo "  升级完成！"
echo "======================================"
echo ""

# 获取新版本
NEW_VERSION=$(docker-compose ps backend | grep nasfusion-backend | awk '{print $2}' || echo "unknown")

echo -e "${GREEN}升级成功！${NC}"
echo "  旧版本：$CURRENT_VERSION"
echo "  新版本：$NEW_VERSION"
echo ""
echo "访问地址：http://localhost"
echo ""
echo "其他命令："
echo "  查看日志：docker-compose logs -f"
echo "  重启服务：docker-compose restart"
echo "  回滚版本：bash scripts/restore.sh <backup-file>"
echo ""
