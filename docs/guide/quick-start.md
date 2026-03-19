# 快速开始

推荐使用 Docker Compose 一键部署，也可以手动安装。

## Docker 部署（推荐）

### 前置要求

- Docker 20.10+
- Docker Compose 2.0+

### 1. 克隆仓库

```bash
git clone https://github.com/YOUR_USERNAME/NasFusion.git
cd NasFusion
```

### 2. 复制配置文件

```bash
cp backend/.env.example backend/.env
```

编辑 `backend/.env`，填写必要配置：

```ini
# 数据库（默认使用 SQLite，无需额外配置）
DATABASE_URL=sqlite+aiosqlite:///./data/nasfusion.db

# JWT 密钥（请修改为随机字符串）
SECRET_KEY=your-secret-key-here

# TMDB API Key（用于元数据刮削）
TMDB_API_KEY=your-tmdb-api-key
```

### 3. 启动服务

```bash
docker compose up -d
```

### 4. 访问系统

| 服务 | 地址 |
|------|------|
| 前端界面 | http://localhost:3000 |
| API 文档 | http://localhost:8000/docs |

### 5. 初始账户

首次启动后，使用以下信息登录：

- **用户名**：`admin`
- **密码**：`admin123`

::: warning
请在登录后立即修改默认密码。
:::

## 手动部署

参见 [手动部署指南](../deploy/manual)。

## 下一步

服务启动后，建议按以下顺序配置：

1. [添加 PT 站点](../features/pt-sites)
2. [触发资源同步](../features/resource-sync)
3. [创建订阅](../features/subscription)
4. [连接媒体服务器](../features/media-library)
