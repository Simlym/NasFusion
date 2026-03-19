# NasFusion Docker 部署文档

## 目录

- [快速开始](#快速开始)
- [系统要求](#系统要求)
- [安装部署](#安装部署)
- [配置说明](#配置说明)
- [NAS 部署](#nas-部署)
- [升级指南](#升级指南)
- [故障排查](#故障排查)

---

## 快速开始

### 一键安装（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/your-repo/NasFusion.git
cd NasFusion

# 2. 运行安装脚本
bash scripts/install.sh

# 3. 访问应用
# http://localhost
```

### 手动安装

```bash
# 1. 复制配置文件
cp backend/.env.production backend/.env

# 2. 编辑配置（修改数据库密码、API Key 等）
nano backend/.env

# 3. 启动服务
docker-compose up -d

# 4. 查看日志
docker-compose logs -f
```

---

## 系统要求

### 硬件要求

- **CPU**: 2 核心及以上
- **内存**: 4GB 及以上
- **存储**: 20GB 系统空间 + 媒体库空间

### 软件要求

- **Docker**: 20.10.0 或更高版本
- **Docker Compose**: 2.0.0 或更高版本
- **操作系统**: Linux / macOS / Windows (WSL2)

### 端口要求

- **80**: Nginx 反向代理（HTTP）
- **443**: Nginx 反向代理（HTTPS，可选）

---

## 安装部署

### 环境准备

#### 1. 安装 Docker

**Ubuntu/Debian**:
```bash
curl -fsSL https://get.docker.com | bash
sudo usermod -aG docker $USER
```

**CentOS/RHEL**:
```bash
sudo yum install -y docker
sudo systemctl start docker
sudo systemctl enable docker
```

#### 2. 安装 Docker Compose

```bash
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 部署步骤

#### 方式 1：一键安装脚本

```bash
bash scripts/install.sh
```

安装脚本会自动：
1. 检测 Docker 环境
2. 引导配置（数据库密码、API Key 等）
3. 生成随机密钥
4. 创建数据目录
5. 拉取镜像并启动服务

#### 方式 2：手动部署

```bash
# 1. 复制并编辑配置文件
cp backend/.env.production backend/.env
nano backend/.env

# 必须修改的配置项：
# - SECRET_KEY: 使用 openssl rand -hex 32 生成
# - JWT_SECRET_KEY: 使用 openssl rand -hex 32 生成
# - DB_POSTGRES_PASSWORD: 数据库密码
# - TMDB_API_KEY: TMDB API Key（https://www.themoviedb.org/settings/api）

# 2. 创建数据目录
mkdir -p data/{media,downloads,torrents,logs,cache}

# 3. 启动服务
docker-compose up -d

# 4. 查看启动状态
docker-compose ps
```

---

## 配置说明

### 核心环境变量

| 变量名 | 说明 | 必需 | 默认值 |
|--------|------|------|--------|
| `SECRET_KEY` | 应用密钥 | ✅ | - |
| `JWT_SECRET_KEY` | JWT 密钥 | ✅ | - |
| `DB_POSTGRES_PASSWORD` | 数据库密码 | ✅ | - |
| `TMDB_API_KEY` | TMDB API Key | ✅ | - |
| `OPENAI_API_KEY` | OpenAI API Key | ❌ | - |
| `PUID` | 容器运行用户 ID | ❌ | 1000 |
| `PGID` | 容器运行用户组 ID | ❌ | 1000 |

### 数据目录映射

| 容器内路径 | 宿主机路径 | 说明 |
|-----------|-----------|------|
| `/app/data/media` | `./data/media` | 媒体库文件 |
| `/app/data/downloads` | `./data/downloads` | 下载目录 |
| `/app/data/torrents` | `./data/torrents` | 种子文件 |
| `/app/data/logs` | `./data/logs` | 应用日志 |

### 端口配置

修改 `docker-compose.yml` 中的端口映射：

```yaml
nginx:
  ports:
    - "8080:80"  # 改为 8080 端口
```

---

## NAS 部署

### 群晖 Synology

#### 方式 1：Container Manager（推荐）

1. 打开 **Container Manager**（旧称 Docker）
2. 上传项目文件到 `/volume1/docker/nasfusion/`
3. 使用 NAS 优化配置：

```bash
cd /volume1/docker/nasfusion
docker-compose -f docker-compose.nas.yml up -d
```

#### 方式 2：命令行部署

1. SSH 登录 NAS：
```bash
ssh admin@your-nas-ip
```

2. 查看用户 ID：
```bash
id admin
# 输出示例：uid=1026(admin) gid=100(users)
```

3. 编辑配置文件，设置正确的 PUID/PGID：
```bash
cd /volume1/docker/nasfusion
nano backend/.env

# 设置：
PUID=1026
PGID=100
```

4. 修改数据目录路径：
```bash
# 在 backend/.env 或 docker-compose.nas.yml 中设置
MEDIA_PATH=/volume1/media/NasFusion
DOWNLOAD_PATH=/volume1/downloads/NasFusion
```

5. 启动服务：
```bash
docker-compose -f docker-compose.nas.yml up -d
```

#### 方式 3：任务计划自动部署（推荐）

通过群晖**任务计划**，在 DSM 网页界面一键触发部署，无需每次 SSH 登录。

**前提条件**：
- 项目路径：`/volume4/dockers/NasFusion`（根据实际路径调整）
- Git 使用 SSH 密钥认证，密钥归属 `admin` 用户
- 已拉取最新代码，`scripts/deploy.sh` 文件存在

**部署脚本说明**（`scripts/deploy.sh`）：

脚本以 `root` 运行，内部用 `su -s /bin/bash admin` 切换到 admin 执行 `git pull`（复用 admin 的 SSH 密钥），再以 root 执行 `docker-compose up -d --build`。日志写入 `scripts/deploy.log`。

**配置步骤**：

1. 用 **admin** 账号拉取代码（含脚本文件）：

```bash
cd /volume4/dockers/NasFusion
git pull origin main
```

> 无需 `chmod +x`，脚本通过 `bash deploy.sh` 方式调用，不需要可执行权限。

2. 在 DSM 中创建任务：

   `控制面板` → `任务计划` → `新增` → `计划的任务` → `用户定义的脚本`

   | 选项卡 | 配置项 | 值 |
   |--------|--------|-----|
   | 常规 | 任务名称 | `NasFusion 部署` |
   | 常规 | 用户 | `root` |
   | 计划 | 日期 | 选择一个日期，**取消勾选"重复运行"** |
   | 任务设置 | 运行命令 | `bash /volume4/dockers/NasFusion/scripts/deploy.sh` |

3. 手动验证：选中任务点 **"运行"**，查看日志确认成功：

```bash
cat /volume4/dockers/NasFusion/scripts/deploy.log
```

**日常使用流程**：

```
本地开发 → git push → DSM 任务计划点"运行" → 自动完成 pull + 构建 + 启动
```

**注意事项**：

- `git pull` 必须以 `admin` 身份执行，否则 SSH 密钥不匹配会失败
- `docker-compose up -d --build` 需要 `root` 权限
- 每次部署日志追加写入 `scripts/deploy.log`，可定期清理

---

### 威联通 QNAP

#### 数据目录配置

```bash
# 威联通路径示例
MEDIA_PATH=/share/Multimedia/NasFusion
DOWNLOAD_PATH=/share/Download/NasFusion
```

#### 资源限制（避免 NAS 卡顿）

在 `docker-compose.nas.yml` 中已配置资源限制：

```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 2G
```

---

## 升级指南

### 一键升级（推荐）

```bash
bash scripts/upgrade.sh
```

升级脚本会自动：
1. 备份当前数据
2. 拉取最新镜像
3. 重启容器
4. 执行数据库迁移
5. 健康检查
6. 失败时自动回滚

### 手动升级

```bash
# 1. 备份数据
bash scripts/backup.sh

# 2. 拉取新镜像
docker-compose pull

# 3. 重启服务
docker-compose down
docker-compose up -d

# 4. 查看日志
docker-compose logs -f backend
```

### 回滚版本

```bash
# 从备份恢复
bash scripts/restore.sh backups/nasfusion_backup_YYYYMMDD_HHMMSS.tar.gz
```

---

## 故障排查

### 1. 数据库连接失败

**症状**:
```
FATAL: password authentication failed for user "nasfusion"
```

**解决方案**:
```bash
# 检查配置文件中的数据库密码
cat backend/.env | grep DB_POSTGRES_PASSWORD

# 重启数据库容器
docker-compose restart postgres
```

### 2. 端口已被占用

**症状**:
```
Error starting userland proxy: listen tcp 0.0.0.0:80: bind: address already in use
```

**解决方案**:
```bash
# 方式 1：修改端口映射
nano docker-compose.yml
# 将 ports: "80:80" 改为 "8080:80"

# 方式 2：停止占用端口的服务
sudo lsof -i :80
sudo kill <PID>
```

### 3. 文件权限问题（NAS）

**症状**:
```
Permission denied: '/app/data/media'
```

**解决方案**:
```bash
# 1. 查看 NAS 用户 ID
id admin

# 2. 设置正确的 PUID/PGID
nano backend/.env
PUID=1026  # 你的用户 ID
PGID=100   # 你的用户组 ID

# 3. 重启服务
docker-compose down
docker-compose up -d
```

### 4. 健康检查失败

**症状**:
```
nasfusion-backend | unhealthy
```

**解决方案**:
```bash
# 查看后端日志
docker-compose logs backend

# 手动检查健康端点
docker exec nasfusion-backend curl http://localhost:8000/health

# 重启后端
docker-compose restart backend
```

### 5. 镜像拉取失败

**症状**:
```
Error response from daemon: Get https://registry-1.docker.io/v2/: net/http: TLS handshake timeout
```

**解决方案**:
```bash
# 配置 Docker 镜像加速器（中国大陆用户）
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json <<-'EOF'
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com"
  ]
}
EOF

sudo systemctl daemon-reload
sudo systemctl restart docker
```

---

## 常见命令

### 查看服务状态
```bash
docker-compose ps
```

### 查看日志
```bash
# 所有服务
docker-compose logs -f

# 单个服务
docker-compose logs -f backend
docker-compose logs -f postgres
```

### 重启服务
```bash
# 重启所有服务
docker-compose restart

# 重启单个服务
docker-compose restart backend
```

### 停止/启动服务
```bash
# 停止
docker-compose down

# 启动
docker-compose up -d
```

### 进入容器
```bash
# 进入后端容器
docker exec -it nasfusion-backend bash

# 进入数据库容器
docker exec -it nasfusion-postgres psql -U nasfusion
```

### 清理资源
```bash
# 清理未使用的镜像
docker image prune -a

# 清理未使用的卷
docker volume prune

# 完全清理（谨慎使用）
docker system prune -a --volumes
```

---

## 性能优化

### 数据库优化

编辑 `docker-compose.yml`，添加 PostgreSQL 配置：

```yaml
postgres:
  command:
    - "postgres"
    - "-c"
    - "max_connections=200"
    - "-c"
    - "shared_buffers=256MB"
    - "-c"
    - "effective_cache_size=1GB"
```

### Redis 优化

```yaml
redis:
  command: redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru
```

---

## 安全建议

1. **修改默认管理员密码**：首次登录后立即修改
2. **使用强密钥**：SECRET_KEY 和 JWT_SECRET_KEY 至少 32 字符
3. **启用 HTTPS**：生产环境建议配置 SSL 证书
4. **定期备份**：每周执行一次备份
5. **限制访问**：使用防火墙限制 80/443 端口访问

---

## 支持与反馈

- **文档**: https://github.com/your-repo/NasFusion/tree/main/docs
- **问题反馈**: https://github.com/your-repo/NasFusion/issues
- **讨论区**: https://github.com/your-repo/NasFusion/discussions

---

**文档版本**: v1.1
**最后更新**: 2026-03-02
