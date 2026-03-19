# NasFusion - PT 媒体资源管理系统

[![GitHub Release](https://img.shields.io/github/v/release/Simlym/NasFusion)](https://github.com/Simlym/NasFusion/releases)
[![GitHub Stars](https://img.shields.io/github/stars/Simlym/NasFusion)](https://github.com/Simlym/NasFusion)

NasFusion 是一个基于 PT（Private Tracker）站点的媒体资源管理系统，提供从资源发现、自动下载到媒体库集成的全生命周期管理。

## 快速开始

### 方式 1：一键部署（推荐）

```bash
# 1. 下载项目
git clone https://github.com/Simlym/NasFusion.git
cd NasFusion

# 2. 配置环境变量
cp .env.example .env
nano .env  # 修改数据库密码、Secret Key 等

# 3. 启动服务
docker-compose up -d

# 4. 访问应用
# http://localhost:8080
```

### 方式 2：使用安装脚本

```bash
git clone https://github.com/Simlym/NasFusion.git
cd NasFusion
bash scripts/install.sh
```

## 核心功能

- **PT 资源管理** - 支持 MTeam、CHDBits、HDChina 等主流站点
- **自动下载** - 智能订阅、质量过滤、促销识别
- **资源识别** - 自动识别电影/电视剧、TMDB/豆瓣元数据关联
- **媒体库管理** - 智能整理、NFO 生成、海报下载
- **下载管理** - qBittorrent 集成、任务监控
- **媒体服务器集成** - Jellyfin / Emby / Plex 连接与观看历史同步
- **通知系统** - Telegram、Email、Webhook 通知
- **AI 助手** - 内置 AI 对话界面

## 架构说明

NasFusion 采用微服务架构，由以下组件组成：

```
┌─────────────────────────────────────────┐
│          Nginx (反向代理)                │
│              :8080                      │
└──────────┬──────────────────┬───────────┘
           │                  │
  ┌────────▼────────┐  ┌──────▼──────────┐
  │    Frontend     │  │     Backend     │
  │  Vue3 + Nginx   │  │ FastAPI + Uvicorn│
  └─────────────────┘  └────────┬─────────┘
                                │
                   ┌────────────┴────────────┐
                   │                         │
           ┌───────▼────────┐     ┌─────────▼────────┐
           │   PostgreSQL   │     │      Redis       │
           │   (数据存储)    │     │   (缓存/队列)    │
           └────────────────┘     └──────────────────┘
```

## 环境变量

配置文件位于项目根目录 `.env`，从 `.env.example` 复制后修改。

### 必需配置

| 变量名 | 说明 | 生成方法 |
|--------|------|---------|
| `SECRET_KEY` | 应用加密密钥（至少 32 字符） | `openssl rand -hex 32` |
| `JWT_SECRET_KEY` | JWT 签名密钥（至少 32 字符） | `openssl rand -hex 32` |
| `DB_POSTGRES_PASSWORD` | 数据库密码 | 自定义强密码 |

### 可选配置

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `HTTP_PORT` | Web 访问端口 | `8080` |
| `DB_EXTERNAL_PORT` | PostgreSQL 外部端口 | `5432` |
| `PUID` | 容器运行用户 ID | `1024` |
| `PGID` | 容器运行用户组 ID | `100` |
| `TZ` | 时区 | `Asia/Shanghai` |
| `LOG_LEVEL` | 日志级别 | `INFO` |
| `DEBUG` | 调试模式 | `false` |

## 数据目录

应用数据默认存储在项目 `data/` 目录下：

| 环境变量 | 默认路径 | 说明 |
|---------|---------|------|
| `LOG_PATH` | `./data/logs` | 应用日志 |
| `TORRENT_PATH` | `./data/torrents` | 种子文件 |
| `CACHE_PATH` | `./data/cache` | 图片缓存 |

## 存储卷挂载（硬链接支持）

NasFusion 支持将 NAS 物理卷整体挂载到容器，以确保同一卷内的下载目录和媒体库之间可以创建**硬链接**（节省磁盘空间，避免重复占用）。

```
# .env 中配置需要挂载的卷路径
VOLUME_1_PATH=/volume1       # 主存储卷（必须）
# VOLUME_2_PATH=/volume2     # 扩展卷（可选）
# VOLUME_3_PATH=/volume3
# VOLUME_4_PATH=/volume4
```

容器内访问路径为 `/mnt/volume1`、`/mnt/volume2` 等。具体的下载目录和媒体库路径在 Web 界面的**存储设置**中配置。

> **原理**：硬链接只能在同一文件系统内创建。将整个卷挂载可确保 `/volume1/Downloads` 和 `/volume1/Media` 共享同一设备 ID，从而支持硬链接。

## 支持的架构

- `linux/amd64` - x86_64 架构（Intel/AMD）
- `linux/arm64` - ARM64 架构（Apple Silicon、树莓派 4+、群晖 ARM NAS）

## NAS 部署

### 群晖 Synology

1. **查看用户 ID**：
```bash
ssh admin@your-nas-ip
id admin
# 输出：uid=1024(admin) gid=100(users)
```

2. **配置环境变量**（`.env`）：
```bash
PUID=1024
PGID=100
HTTP_PORT=8080        # 群晖 80 端口通常被系统占用
VOLUME_1_PATH=/volume1
```

3. **启动服务**：
```bash
docker-compose up -d
```

4. **访问应用**：`http://your-nas-ip:8080`

### 威联通 QNAP

```bash
PUID=1000
PGID=1000
HTTP_PORT=8080
VOLUME_1_PATH=/share/Multimedia
```

## 常用命令

```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose down

# 查看日志
docker-compose logs -f

# 重启服务
docker-compose restart

# 查看状态
docker-compose ps

# 升级版本
docker-compose pull
docker-compose up -d
```

## 版本升级

### 自动升级（推荐）

```bash
bash scripts/upgrade.sh
```

### 手动升级

```bash
# 1. 备份数据
bash scripts/backup.sh

# 2. 拉取新镜像
docker-compose pull

# 3. 重启服务
docker-compose down
docker-compose up -d
```

## 备份与恢复

### 备份

```bash
bash scripts/backup.sh
# 备份文件保存在 ./backups/ 目录
```

### 恢复

```bash
bash scripts/restore.sh backups/nasfusion_backup_YYYYMMDD_HHMMSS.tar.gz
```

## 故障排查

### 1. 健康检查失败

```bash
# 查看后端日志
docker-compose logs backend

# 检查健康端点
docker exec nasfusion-backend curl http://localhost:8000/health
```

### 2. 数据库连接失败

```bash
# 检查数据库容器状态
docker-compose ps postgres

# 查看数据库日志
docker-compose logs postgres
```

### 3. 端口冲突

修改 `.env` 中的端口配置：

```bash
HTTP_PORT=8888
DB_EXTERNAL_PORT=5433
```

### 4. 硬链接失败

确认下载目录和媒体库目录在同一个卷内，且该卷已正确配置 `VOLUME_N_PATH`。

## 默认账号

- **用户名**: `admin`
- **密码**: `admin123`

⚠️ **重要**：首次登录后请立即修改密码！

## 安全建议

1. 修改默认管理员密码
2. 使用强随机密钥（`SECRET_KEY`、`JWT_SECRET_KEY`）
3. 生产环境建议不暴露数据库端口（`DB_EXTERNAL_PORT`）
4. 生产环境启用 HTTPS（Nginx 反向代理）
5. 定期备份数据

## 文档

- **完整文档**: https://github.com/Simlym/NasFusion/tree/main/docs
- **升级指南**: https://github.com/Simlym/NasFusion/blob/main/docs/upgrade-guide.md
- **API 文档**: http://localhost:8080/docs（运行后访问）

## 支持

- **问题反馈**: https://github.com/Simlym/NasFusion/issues
- **功能建议**: https://github.com/Simlym/NasFusion/discussions
- **更新日志**: https://github.com/Simlym/NasFusion/releases

## 许可证

[MIT License](https://github.com/Simlym/NasFusion/blob/main/LICENSE)

---

**构建时间**: 自动构建于每次 push 到 main 分支
**维护者**: NasFusion Team
