#!/bin/bash
# ==============================================================================
# NasFusion 备份脚本
# ==============================================================================

set -e

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "======================================"
echo "  NasFusion 数据备份"
echo "======================================"
echo ""

# 生成备份时间戳
BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="./backups"
BACKUP_FILE="nasfusion_backup_$BACKUP_DATE.tar.gz"

# 创建备份目录
mkdir -p "$BACKUP_DIR"

echo "备份文件：$BACKUP_FILE"
echo ""

# 临时目录
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

echo "======================================"
echo "  步骤 1：导出数据库"
echo "======================================"
echo ""

# 导出 PostgreSQL 数据库
if docker ps | grep -q nasfusion-postgres; then
    echo "正在导出 PostgreSQL 数据库..."
    docker exec nasfusion-postgres pg_dump -U nasfusion nasfusion > "$TEMP_DIR/database.sql"
    echo -e "${GREEN}✓${NC} 数据库导出完成"
else
    echo -e "${YELLOW}警告：PostgreSQL 容器未运行，跳过数据库备份${NC}"
fi

echo ""
echo "======================================"
echo "  步骤 2：备份配置文件"
echo "======================================"
echo ""

# 复制配置文件
echo "正在备份配置文件..."
cp backend/.env "$TEMP_DIR/backend.env" 2>/dev/null || echo -e "${YELLOW}警告：backend/.env 不存在${NC}"
cp docker-compose.yml "$TEMP_DIR/" 2>/dev/null || true

echo -e "${GREEN}✓${NC} 配置文件备份完成"

echo ""
echo "======================================"
echo "  步骤 3：打包备份文件"
echo "======================================"
echo ""

# 打包备份
cd "$TEMP_DIR"
tar -czf "$BACKUP_FILE" *
cd - > /dev/null

# 移动到备份目录
mv "$TEMP_DIR/$BACKUP_FILE" "$BACKUP_DIR/"

echo -e "${GREEN}✓${NC} 备份文件已保存"

echo ""
echo "======================================"
echo "  备份完成！"
echo "======================================"
echo ""
echo "备份文件：$BACKUP_DIR/$BACKUP_FILE"
echo "文件大小：$(du -h "$BACKUP_DIR/$BACKUP_FILE" | cut -f1)"
echo ""
echo "恢复命令："
echo "  bash scripts/restore.sh $BACKUP_DIR/$BACKUP_FILE"
echo ""
echo -e "${YELLOW}提示：此备份不包含媒体文件（体积较大）${NC}"
echo "如需备份媒体文件，请手动复制 ./data/media 目录"
echo ""
