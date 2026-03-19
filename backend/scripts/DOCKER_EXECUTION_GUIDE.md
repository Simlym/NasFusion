# Docker 环境执行脚本指南

## 方法概览

在 Docker 环境中执行合并脚本有三种方法：

| 方法 | 适用场景 | 优点 | 缺点 |
|------|---------|------|------|
| **方法1：docker exec** | 容器已运行 | 简单直接，无需进入容器 | 需要容器在运行 |
| **方法2：docker-compose exec** | 使用 docker-compose | 支持服务名，便于管理 | 需要 docker-compose |
| **方法3：进入容器交互式执行** | 需要调试或多次执行 | 可以反复执行，便于调试 | 需要手动进入容器 |

---

## 前置准备

### 1. 确认容器状态

```bash
# 查看所有容器状态
docker ps -a

# 或使用 docker-compose
docker-compose ps
```

确认 `nasfusion-backend` 容器处于 **Running** 状态。

### 2. 备份数据库（重要！）

#### 如果使用 PostgreSQL：

```bash
# 进入 postgres 容器备份
docker exec nasfusion-postgres pg_dump -U nasfusion nasfusion > backup_$(date +%Y%m%d_%H%M%S).sql

# 或使用 docker-compose
docker-compose exec postgres pg_dump -U nasfusion nasfusion > backup_$(date +%Y%m%d_%H%M%S).sql
```

#### 如果使用 SQLite：

```bash
# 复制数据库文件
docker cp nasfusion-backend:/app/data/nasfusion.db ./backup_nasfusion_$(date +%Y%m%d_%H%M%S).db
```

---

## 方法1：使用 docker exec（推荐）

### 步骤1：预览模式（必须先执行）

```bash
docker exec nasfusion-backend python scripts/merge_duplicate_movies.py --dry-run --verbose
```

### 步骤2：执行实际合并

确认预览结果无误后：

```bash
docker exec nasfusion-backend python scripts/merge_duplicate_movies.py --verbose
```

### 步骤3：验证结果

```bash
# 进入 PostgreSQL 容器验证
docker exec -it nasfusion-postgres psql -U nasfusion -d nasfusion -c "
SELECT title, year, COUNT(1) as count
FROM unified_movies
GROUP BY title, year
HAVING COUNT(1) > 1;
"
```

如果返回空结果（0 rows），说明合并成功。

---

## 方法2：使用 docker-compose exec

### 步骤1：预览模式

```bash
docker-compose exec backend python scripts/merge_duplicate_movies.py --dry-run --verbose
```

### 步骤2：执行实际合并

```bash
docker-compose exec backend python scripts/merge_duplicate_movies.py --verbose
```

### 步骤3：验证结果

```bash
docker-compose exec postgres psql -U nasfusion -d nasfusion -c "
SELECT title, year, COUNT(1) as count
FROM unified_movies
GROUP BY title, year
HAVING COUNT(1) > 1;
"
```

---

## 方法3：进入容器交互式执行

### 步骤1：进入容器

```bash
# 使用 docker exec
docker exec -it nasfusion-backend bash

# 或使用 docker-compose
docker-compose exec backend bash
```

### 步骤2：在容器内执行脚本

```bash
# 预览模式
python scripts/merge_duplicate_movies.py --dry-run --verbose

# 执行合并
python scripts/merge_duplicate_movies.py --verbose

# 退出容器
exit
```

---

## 常见问题

### Q1: 提示 "python: command not found"

**原因**：容器中 Python 可能使用 `python3` 命令。

**解决方案**：

```bash
# 尝试使用 python3
docker exec nasfusion-backend python3 scripts/merge_duplicate_movies.py --dry-run
```

### Q2: 提示 "No such file or directory: scripts/merge_duplicate_movies.py"

**原因**：脚本文件未复制到容器中。

**解决方案1：重新构建镜像**

```bash
# 停止容器
docker-compose down

# 重新构建镜像（包含最新代码）
docker-compose build backend

# 启动容器
docker-compose up -d
```

**解决方案2：临时复制脚本到容器**

```bash
# 从宿主机复制脚本到容器
docker cp backend/scripts/merge_duplicate_movies.py nasfusion-backend:/app/scripts/

# 确保脚本可执行
docker exec nasfusion-backend chmod +x /app/scripts/merge_duplicate_movies.py
```

### Q3: 提示 "ImportError: cannot import name 'async_session_local'"

**原因**：容器中的代码版本过旧。

**解决方案**：重新构建镜像（参考 Q2 解决方案1）。

### Q4: 提示 "ModuleNotFoundError: No module named 'dotenv'"

**原因**：缺少 `python-dotenv` 依赖。

**解决方案**：

```bash
# 进入容器安装依赖
docker exec nasfusion-backend pip install python-dotenv

# 或在 requirements.txt 中添加后重新构建
```

### Q5: 如何查看脚本输出日志？

**方法1：直接查看**

```bash
docker exec nasfusion-backend python scripts/merge_duplicate_movies.py --dry-run --verbose 2>&1 | less
```

**方法2：保存到文件**

```bash
# 保存到宿主机
docker exec nasfusion-backend python scripts/merge_duplicate_movies.py --dry-run --verbose > merge_preview.log 2>&1

# 或保存到容器内
docker exec nasfusion-backend sh -c "python scripts/merge_duplicate_movies.py --dry-run --verbose > /app/data/logs/merge_preview.log 2>&1"

# 从容器复制日志到宿主机
docker cp nasfusion-backend:/app/data/logs/merge_preview.log ./
```

### Q6: 执行后如何恢复数据？

**PostgreSQL 恢复**：

```bash
# 停止应用
docker-compose stop backend

# 恢复数据库
docker exec -i nasfusion-postgres psql -U nasfusion -d nasfusion < backup_20250117_143000.sql

# 启动应用
docker-compose start backend
```

**SQLite 恢复**：

```bash
# 停止应用
docker-compose stop backend

# 恢复数据库文件
docker cp backup_nasfusion_20250117_143000.db nasfusion-backend:/app/data/nasfusion.db

# 启动应用
docker-compose start backend
```

---

## 完整执行示例

### 群晖 NAS 用户

```bash
# 1. SSH 登录群晖
ssh admin@192.168.1.100

# 2. 进入项目目录
cd /volume1/docker/nasfusion

# 3. 备份数据库
docker-compose exec postgres pg_dump -U nasfusion nasfusion > backup_$(date +%Y%m%d_%H%M%S).sql

# 4. 预览合并
docker-compose exec backend python scripts/merge_duplicate_movies.py --dry-run --verbose | tee merge_preview.log

# 5. 检查预览结果
less merge_preview.log

# 6. 执行合并
docker-compose exec backend python scripts/merge_duplicate_movies.py --verbose

# 7. 验证结果
docker-compose exec postgres psql -U nasfusion -d nasfusion -c "
SELECT title, year, COUNT(1) as count
FROM unified_movies
GROUP BY title, year
HAVING COUNT(1) > 1;
"
```

### 普通 Linux 服务器

```bash
# 1. 进入项目目录
cd /path/to/nasfusion

# 2. 备份数据库
docker exec nasfusion-postgres pg_dump -U nasfusion nasfusion > backup_$(date +%Y%m%d_%H%M%S).sql

# 3. 预览合并
docker exec nasfusion-backend python scripts/merge_duplicate_movies.py --dry-run --verbose

# 4. 执行合并
docker exec nasfusion-backend python scripts/merge_duplicate_movies.py --verbose

# 5. 验证结果
docker exec nasfusion-postgres psql -U nasfusion -d nasfusion -c "
SELECT title, year, COUNT(1) as count
FROM unified_movies
GROUP BY title, year
HAVING COUNT(1) > 1;
"
```

---

## 高级技巧

### 1. 后台执行（避免 SSH 断开导致中断）

```bash
# 使用 nohup 在后台执行
nohup docker exec nasfusion-backend python scripts/merge_duplicate_movies.py --verbose > merge.log 2>&1 &

# 查看进度
tail -f merge.log

# 查看进程状态
ps aux | grep merge_duplicate
```

### 2. 设置执行超时

```bash
# 使用 timeout 命令（10分钟超时）
timeout 600 docker exec nasfusion-backend python scripts/merge_duplicate_movies.py --verbose
```

### 3. 定期自动合并（可选）

在宿主机创建 cron 任务：

```bash
# 编辑 crontab
crontab -e

# 添加以下行（每周日凌晨2点执行）
0 2 * * 0 docker exec nasfusion-backend python scripts/merge_duplicate_movies.py --verbose >> /var/log/nasfusion_merge.log 2>&1
```

---

## 性能优化

### 1. 调整容器资源限制

编辑 `docker-compose.yml`（群晖用户跳过此步骤）：

```yaml
backend:
  # ... 其他配置 ...
  deploy:
    resources:
      limits:
        cpus: '2.0'
        memory: 4G
```

### 2. 临时提高数据库性能

```bash
# PostgreSQL：临时禁用同步模式（提高写入速度）
docker exec nasfusion-postgres psql -U nasfusion -d nasfusion -c "ALTER SYSTEM SET synchronous_commit = off;"
docker exec nasfusion-postgres psql -U nasfusion -d nasfusion -c "SELECT pg_reload_conf();"

# 执行合并
docker exec nasfusion-backend python scripts/merge_duplicate_movies.py --verbose

# 恢复同步模式
docker exec nasfusion-postgres psql -U nasfusion -d nasfusion -c "ALTER SYSTEM RESET synchronous_commit;"
docker exec nasfusion-postgres psql -U nasfusion -d nasfusion -c "SELECT pg_reload_conf();"
```

---

## 故障排查

### 检查容器日志

```bash
# 查看后端日志
docker logs nasfusion-backend --tail 100 -f

# 查看数据库日志
docker logs nasfusion-postgres --tail 100 -f
```

### 检查网络连接

```bash
# 测试后端到数据库的连接
docker exec nasfusion-backend nc -zv postgres 5432
```

### 检查磁盘空间

```bash
# 检查容器内磁盘空间
docker exec nasfusion-backend df -h

# 检查宿主机磁盘空间
df -h
```

---

## 安全建议

1. ✅ **始终先执行 `--dry-run` 预览**
2. ✅ **在执行前备份数据库**
3. ✅ **在低峰期执行（如凌晨）**
4. ✅ **保留备份至少7天**
5. ✅ **执行后验证数据完整性**

---

## 维护者

- 文档位置：`backend/scripts/DOCKER_EXECUTION_GUIDE.md`
- 最后更新：2025-01-17
- 维护者：Claude Code

## 相关文档

- [合并脚本使用说明](./README_merge_duplicate_movies.md)
- [项目指南 CLAUDE.md](../../CLAUDE.md)
- [Docker Compose 配置](../../docker-compose.yml)
