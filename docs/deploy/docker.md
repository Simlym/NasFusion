# Docker 部署

## 前置要求

- Docker 20.10+
- Docker Compose 2.0+
- 2GB+ 可用内存

## 部署步骤

### 1. 获取代码

```bash
git clone https://github.com/YOUR_USERNAME/NasFusion.git
cd NasFusion
```

### 2. 配置环境变量

```bash
cp backend/.env.example backend/.env
```

编辑 `backend/.env`：

```ini
# 必填
SECRET_KEY=请替换为随机字符串
TMDB_API_KEY=你的TMDB_API_Key

# 数据库（默认 SQLite）
DATABASE_URL=sqlite+aiosqlite:///./data/nasfusion.db

# 可选：使用 PostgreSQL
# DATABASE_URL=postgresql+asyncpg://nasfusion:password@db:5432/nasfusion
```

### 3. 启动服务

```bash
docker compose up -d
```

### 4. 查看日志

```bash
# 所有服务
docker compose logs -f

# 仅后端
docker compose logs -f backend
```

### 5. 访问系统

- 前端：http://localhost:3000
- API 文档：http://localhost:8000/docs

## 目录挂载

`docker-compose.yml` 中默认挂载：

| 容器路径 | 宿主机路径 | 说明 |
|----------|------------|------|
| `/app/data` | `./backend/data` | 数据库、日志 |
| `/media` | `/your/media/path` | 媒体文件目录 |
| `/downloads` | `/your/downloads/path` | qBittorrent 下载目录 |

::: warning
媒体目录和下载目录需要修改为你的实际路径。
:::

## 更新

```bash
git pull
docker compose pull
docker compose up -d
```

## 数据备份

```bash
# 备份数据库
cp backend/data/nasfusion.db backup/nasfusion_$(date +%Y%m%d).db
```
