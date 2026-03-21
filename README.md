# NasFusion

**媒体资源全生命周期管理系统**

> **关于本项目**：这是一个 Vibe Coding 学习项目。作者并非技术出身，借助 AI 辅助编程完成，主要用于个人学习和探索全栈开发。代码质量和架构设计仍在持续改进中，欢迎交流。

NasFusion 是一个面向 NAS 用户的媒体资源管理系统，提供从资源发现、自动下载到媒体库集成的全流程管理。

## 核心特性

- **资源管理** - 支持多种主流资源站点接入（含通用 NexusPHP 适配）
- **自动下载** - 智能订阅、质量过滤、促销识别、季集自动匹配
- **资源识别** - 自动识别电影/电视剧、TMDB/豆瓣元数据关联、批量识别
- **媒体库管理** - 智能整理、NFO 生成、海报下载、硬链接支持
- **下载器集成** - 支持 qBittorrent、Transmission、群晖 Download Station
- **媒体服务器集成** - 支持 Jellyfin、Plex，观看历史同步
- **通知系统** - Telegram、Email、Webhook 多渠道通知
- **AI 助手** - 内置 AI 对话界面

## 技术栈

| 组件 | 技术 |
|------|------|
| 后端 | FastAPI + SQLAlchemy 2.0 (Async) + PostgreSQL/SQLite |
| 前端 | Vue3 + TypeScript + Element Plus |
| 任务调度 | APScheduler + asyncio |
| 部署 | Docker + Docker Compose |

## 快速开始

### Docker 部署（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/Simlym/NasFusion.git
cd NasFusion

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，设置 SECRET_KEY、JWT_SECRET_KEY、DB_POSTGRES_PASSWORD 等

# 3. 启动服务
docker-compose up -d

# 4. 访问应用
# http://localhost:8080
```

详细部署说明参见 [Docker 部署指南](README.docker.md)。

### 本地开发

```bash
# 后端
cd backend
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或 venv\Scripts\activate  # Windows
pip install -r requirements.txt

# ⚠️ 必须先配置环境变量，否则启动会报错
cp .env.example .env
# 编辑 .env，设置 SECRET_KEY 和 JWT_SECRET_KEY（至少 32 字符）
# 快速生成密钥：python -c "import secrets; print(secrets.token_hex(32))"

python -m app.main

# 前端
cd frontend
npm install
npm run dev
```

## 配置说明

### 必需配置

| 变量名 | 说明 | 示例 |
|--------|------|------|
| `SECRET_KEY` | 应用加密密钥（至少 32 字符） | `openssl rand -hex 32` |
| `JWT_SECRET_KEY` | JWT 签名密钥（至少 32 字符） | `openssl rand -hex 32` |
| `DB_POSTGRES_PASSWORD` | 数据库密码 | 自定义强密码 |

### 可选配置

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `HTTP_PORT` | Web 访问端口 | `8080` |
| `PUID` / `PGID` | 容器用户权限（NAS 用户需配置） | `1024` / `100` |
| `VOLUME_1_PATH` | NAS 存储卷路径（支持硬链接） | `/volume1` |
| `TMDB_API_KEY` | TMDB API Key（元数据刮削） | - |
| `OPENAI_API_KEY` | OpenAI API Key（AI 助手） | - |
| `TZ` | 时区 | `Asia/Shanghai` |
| `DEBUG` | 调试模式 | `false` |

详细配置参见 [`.env.example`](.env.example)

## 支持的架构

- `linux/amd64` - x86_64 架构（Intel/AMD）
- `linux/arm64` - ARM64 架构（Apple Silicon、树莓派 4+、群晖 ARM NAS）

## 文档

- [在线文档](https://simlym.github.io/NasFusion/)
- [Docker 部署指南](README.docker.md)
- [快速入门](QUICKSTART.md)
- [项目开发指南](CLAUDE.md)
- [后端文档](backend/docs/)

## 项目结构

```
NasFusion/
├── backend/           # FastAPI 后端
│   ├── app/
│   │   ├── adapters/  # 外部系统适配器（资源站点、下载器、媒体服务器）
│   │   ├── api/v1/    # API 路由
│   │   ├── core/      # 核心配置
│   │   ├── models/    # 数据库模型
│   │   ├── schemas/   # Pydantic 模型
│   │   ├── services/  # 业务逻辑
│   │   └── tasks/     # 后台任务
│   └── docs/          # 后端文档
├── frontend/          # Vue3 前端
│   └── src/
├── nginx/             # Nginx 反向代理配置
├── scripts/           # 安装、备份、升级脚本
├── .env.example       # 环境变量模板
└── docker-compose.yml # Docker 编排
```

## 社区

欢迎加入 Telegram 群组交流讨论：[t.me/NasFusion](https://t.me/NasFusion)

## 贡献

欢迎提交 Issue 和 Pull Request！请参阅 [CONTRIBUTING.md](CONTRIBUTING.md) 了解贡献指南。

## 安全

如果您发现安全漏洞，请参阅 [SECURITY.md](SECURITY.md) 了解如何负责任地披露。

## 免责声明

- 本项目仅供个人学习和研究使用，严禁用于任何商业目的。
- 使用本项目下载的任何内容，均由用户自行承担法律责任，项目作者不对因使用本项目而产生的任何直接或间接损失负责。
- 本项目不存储、传播任何受版权保护的内容，仅提供自动化管理工具，内容来源完全取决于用户自身的配置和使用行为。
- 若您所在地区不允许使用此类工具，请勿下载或使用本项目。

## 许可证

本项目采用 [MIT 许可证](LICENSE) 开源。
