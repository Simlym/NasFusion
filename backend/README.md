# NasFusion 后端

PT站点媒体资源管理系统 - 后端服务

## 项目概述

NasFusion是一个以PT站点为核心的媒体资源管理系统，提供资源同步、下载管理、媒体整理、订阅追踪、AI推荐等功能。

### 核心特性

- 🎬 **PT资源同步** - 支持多个PT站点的资源同步和聚合
- 📥 **智能下载** - 集成qBittorrent、Transmission等下载器
- 📁 **自动整理** - 智能识别和整理媒体文件
- 🔔 **订阅系统** - 追踪媒体更新，自动下载
- 🤖 **AI推荐** - 基于OpenAI的智能推荐引擎
- 📱 **多渠道通知** - Telegram、Email、Webhook等通知方式
- 🗄️ **双数据库** - 支持SQLite（开发）和PostgreSQL（生产）

## 技术栈

- **框架**: FastAPI 0.109+
- **ORM**: SQLAlchemy 2.0 (异步)
- **数据库**: PostgreSQL / SQLite
- **任务队列**: Celery + Redis
- **定时任务**: APScheduler
- **数据验证**: Pydantic 2.5+
- **测试**: Pytest + pytest-asyncio

## 快速开始

### 环境要求

- Python 3.10+
- PostgreSQL 14+ (可选，可使用SQLite)
- Redis 6+ (可选，Celery需要)

### 安装步骤

1. **克隆项目**

```bash
git clone <repository-url>
cd NasFusion/backend
```

2. **创建虚拟环境**

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

3. **安装依赖**

```bash
pip install -r requirements.txt
```

4. **配置环境变量**

```bash
cp .env.example .env
# 编辑.env文件，配置数据库和其他设置
```

5. **初始化数据库**

```bash
# 使用Alembic迁移（推荐）
alembic upgrade head

# 或者开发环境自动创建（DEBUG=true时）
python -m app.main
```

6. **运行开发服务器**

```bash
# 方式1：直接运行
python -m app.main

# 方式2：使用uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

7. **访问API文档**

打开浏览器访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 项目结构

```
backend/
├── app/                    # 应用主目录
│   ├── core/              # 核心配置
│   │   ├── config.py      # 配置管理
│   │   ├── database.py    # 数据库会话
│   │   ├── dependencies.py # 依赖注入
│   │   └── logging.py     # 日志配置
│   ├── api/               # API路由
│   │   └── v1/            # API v1版本
│   ├── models/            # ORM模型
│   ├── schemas/           # Pydantic模型
│   ├── repositories/      # 数据访问层
│   ├── services/          # 业务逻辑层
│   ├── adapters/          # 外部系统适配器
│   │   ├── pt_sites/      # PT站点适配器
│   │   ├── downloaders/   # 下载器适配器
│   │   ├── notifications/ # 通知适配器
│   │   └── metadata/      # 元数据适配器
│   ├── tasks/             # 异步任务
│   ├── utils/             # 工具函数
│   └── constants/         # 常量定义
├── tests/                 # 测试目录
│   ├── unit/              # 单元测试
│   ├── integration/       # 集成测试
│   └── e2e/               # 端到端测试
├── alembic/               # 数据库迁移
├── scripts/               # 运维脚本
├── requirements.txt       # 依赖列表
├── .env.example           # 环境变量示例
└── README.md              # 本文档
```

## 配置说明

### 数据库配置

#### 使用SQLite（开发环境）

```env
DB_TYPE=sqlite
DB_SQLITE_PATH=./data/nasfusion.db
```

#### 使用PostgreSQL（生产环境）

```env
DB_TYPE=postgresql
DB_POSTGRES_SERVER=localhost
DB_POSTGRES_USER=nasfusion
DB_POSTGRES_PASSWORD=your-password
DB_POSTGRES_DB=nasfusion
DB_POSTGRES_PORT=5432
```

### Celery配置（可选）

```env
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### OpenAI配置（AI推荐功能）

```env
OPENAI_API_KEY=sk-your-api-key
OPENAI_API_BASE=https://api.openai.com/v1
OPENAI_PROXY=http://proxy.example.com:7890  # 可选
```

## 开发指南

### 代码规范

```bash
# 格式化代码
black app tests

# 排序导入
isort app tests

# 类型检查
mypy app

# 代码检查
flake8 app
```

### 运行测试

```bash
# 运行所有测试
pytest

# 运行单元测试
pytest tests/unit -v

# 运行集成测试
pytest tests/integration -v

# 生成覆盖率报告
pytest --cov=app --cov-report=html
```

### 数据库迁移

```bash
# 创建迁移
alembic revision --autogenerate -m "描述"

# 应用迁移
alembic upgrade head

# 回退迁移
alembic downgrade -1
```

### 启动Celery Worker

```bash
celery -A app.tasks.celery_app worker -l info
```

### 启动Celery Beat（定时任务）

```bash
celery -A app.tasks.celery_app beat -l info
```

## API接口

详细的API文档请访问：http://localhost:8000/docs

### 主要端点

- `GET /health` - 健康检查
- `GET /api/v1/pt-sites` - PT站点列表
- `POST /api/v1/pt-sites` - 添加PT站点
- `GET /api/v1/resources` - 资源列表
- `POST /api/v1/downloads` - 创建下载任务
- `GET /api/v1/subscriptions` - 订阅列表

## 架构设计

### 分层架构

```
┌─────────────────────────────────────┐
│         API层 (FastAPI)             │  ← HTTP请求/响应
├─────────────────────────────────────┤
│       Service层 (业务逻辑)           │  ← 业务编排
├─────────────────────────────────────┤
│    Repository层 (数据访问)           │  ← 数据库操作
├─────────────────────────────────────┤
│       Model层 (ORM模型)              │  ← 数据模型
└─────────────────────────────────────┘

     ┌──────────────────────┐
     │  Adapter层 (外部集成)  │  ← PT站点、下载器、通知
     └──────────────────────┘
```

### 适配器模式

通过适配器模式集成多种外部系统：

- **PT站点适配器**: MTeam, CHDBits, HDSky等
- **下载器适配器**: qBittorrent, Transmission, Synology DSM
- **通知适配器**: Telegram, Email, Webhook, Discord
- **元数据适配器**: TMDB, Douban

## 部署

### Docker部署（推荐）

```bash
# 构建镜像
docker build -t nasfusion-backend .

# 运行容器
docker run -d \
  --name nasfusion-backend \
  -p 8000:8000 \
  -v ./data:/app/data \
  --env-file .env \
  nasfusion-backend
```

### 生产环境部署

```bash
# 使用Gunicorn + Uvicorn workers
gunicorn app.main:app \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile -
```

## 常见问题

### Q: 如何添加新的PT站点适配器？

A: 1. 在 `app/adapters/pt_sites/` 创建新文件
   2. 继承 `BasePTSiteAdapter`
   3. 实现所有抽象方法
   4. 在 `factory.py` 中注册

### Q: 数据库迁移失败怎么办？

A: 检查数据库连接配置，确保数据库服务正常运行，查看迁移脚本是否有错误。

### Q: Celery任务不执行？

A: 确保Redis服务运行正常，检查Celery worker和beat进程是否启动。

## 贡献指南

欢迎贡献代码！请遵循以下步骤：

1. Fork本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

## 许可证

MIT License

## 联系方式

项目主页: https://github.com/yourusername/nasfusion

## 更新日志

### v0.1.0 (当前版本)

- ✅ 项目初始化
- ✅ 基础架构搭建
- ✅ 配置管理系统
- ✅ 数据库连接
- ✅ 基础ORM模型
- ✅ Repository模式
- ✅ 适配器框架

### 待实现

- ⏳ PT站点管理API
- ⏳ 资源同步功能
- ⏳ 下载管理功能
- ⏳ 订阅系统
- ⏳ AI推荐引擎
- ⏳ 通知系统
