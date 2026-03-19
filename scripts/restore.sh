#!/bin/bash
# ==============================================================================
# NasFusion 恢复脚本
# ==============================================================================

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "======================================"
echo "  NasFusion 数据恢复"
echo "======================================"
echo ""

# 检查参数
if [ -z "$1" ]; then
    echo -e "${RED}错误：请指定备份文件${NC}"
    echo "用法：bash scripts/restore.sh <backup-file>"
    echo ""
    echo "可用备份文件："
    ls -lh backups/*.tar.gz 2>/dev/null || echo "  无可用备份"
    exit 1
fi

BACKUP_FILE="$1"

# 检查备份文件是否存在
if [ ! -f "$BACKUP_FILE" ]; then
    echo -e "${RED}错误：备份文件不存在：$BACKUP_FILE${NC}"
    exit 1
fi

echo "备份文件：$BACKUP_FILE"
echo "文件大小：$(du -h "$BACKUP_FILE" | cut -f1)"
echo ""

# 确认恢复
echo -e "${YELLOW}警告：恢复操作将覆盖当前数据！${NC}"
read -p "是否继续？(y/N): " confirm
if [[ ! $confirm =~ ^[Yy]$ ]]; then
    echo "恢复已取消"
    exit 0
fi

# 临时目录
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

echo ""
echo "======================================"
echo "  步骤 1：解压备份文件"
echo "======================================"
echo ""

tar -xzf "$BACKUP_FILE" -C "$TEMP_DIR"
echo -e "${GREEN}✓${NC} 备份文件解压完成"

echo ""
echo "======================================"
echo "  步骤 2：停止服务"
echo "======================================"
echo ""

docker-compose down

echo ""
echo "======================================"
echo "  步骤 3：恢复配置文件"
echo "======================================"
echo ""

if [ -f "$TEMP_DIR/backend.env" ]; then
    cp "$TEMP_DIR/backend.env" backend/.env
    echo -e "${GREEN}✓${NC} 配置文件恢复完成"
else
    echo -e "${YELLOW}警告：备份中无配置文件${NC}"
fi

echo ""
echo "======================================"
echo "  步骤 4：启动数据库"
echo "======================================"
echo ""

docker-compose up -d postgres redis

echo "等待数据库就绪..."
sleep 10

echo ""
echo "======================================"
echo "  步骤 5：恢复数据库"
echo "======================================"
echo ""

if [ -f "$TEMP_DIR/database.sql" ]; then
    echo "正在恢复数据库..."
    docker exec -i nasfusion-postgres psql -U nasfusion nasfusion < "$TEMP_DIR/database.sql"
    echo -e "${GREEN}✓${NC} 数据库恢复完成"
else
    echo -e "${YELLOW}警告：备份中无数据库文件${NC}"
fi

echo ""
echo "======================================"
echo "  步骤 6：启动所有服务"
echo "======================================"
echo ""

docker-compose up -d

echo "等待服务就绪..."
sleep 10

docker-compose ps

echo ""
echo "======================================"
echo "  恢复完成！"
echo "======================================"
echo ""
echo -e "${GREEN}数据已成功恢复${NC}"
echo "访问地址：http://localhost"
echo ""
