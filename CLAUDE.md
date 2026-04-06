# CLAUDE.md

为 Claude Code (claude.ai/code) 提供项目指导文档。

---

## 项目概述

**NasFusion** 是一个基于 PT（Private Tracker）站点的媒体资源管理系统。

### 核心理念
- **PT优先方式**：以 PT 站点资源为起点，而非 TMDB/豆瓣
- **本地缓存**：定期同步 PT 站点资源到本地数据库以实现快速访问
- **全生命周期管理**：从资源发现、下载管理到媒体库集成
- **智能推荐**：基于观看历史的 AI 推荐

### 技术栈
- **后端**：FastAPI + SQLAlchemy 2.0 (Async) + PostgreSQL/SQLite
- **前端**：Vue3 + TypeScript + Element Plus
- **任务调度**：APScheduler + asyncio
- **AI 集成**：OpenAI API

---

## 项目结构

```
backend/
├── app/
│   ├── adapters/          # 外部系统适配器（PT 站点、下载器、媒体服务器等）
│   ├── api/v1/            # API 路由
│   ├── constants/         # 常量定义（避免魔法字符串）
│   ├── core/              # 核心配置（config、database、dependencies）
│   ├── events/            # 事件系统（Event System）
│   ├── models/            # SQLAlchemy 模型
│   ├── schemas/           # Pydantic 模型（数据验证）
│   ├── services/          # 业务逻辑层
│   │   └── ai_agent/      # AI Agent 服务
│   │       ├── agent_service.py    # AI Agent 核心服务
│   │       ├── tool_registry.py    # 工具注册表（BaseTool）
│   │       ├── context.py          # 用户上下文（共享基础设施）
│   │       ├── telegram_handler.py # Telegram 集成
│   │       ├── tools/              # 内置工具（单步操作）
│   │       ├── skills/             # 高级技能/工作流（预留）
│   │       ├── mcp_server/         # 对外暴露 MCP 服务
│   │       └── mcp_client/         # 调用外部 MCP 服务
│   ├── tasks/             # 任务处理器（Task Handlers）
│   ├── utils/             # 工具函数
│   └── main.py            # FastAPI 应用入口
├── docs/                  # 项目文档
├── alembic/               # 数据库迁移脚本
└── data/                  # 数据目录（数据库、日志、媒体）

frontend/
├── src/
│   ├── api/               # API 调用封装
│   ├── components/        # Vue 组件
│   ├── views/             # 页面视图
│   ├── stores/            # Pinia 状态管理
│   ├── router/            # Vue Router 配置
│   └── utils/             # 工具函数
└── package.json
```

---

## 核心功能

### ✅ 已实现
1. **用户系统**：注册、登录（JWT）、用户管理、敏感数据加密
2. **PT 站点管理**：站点配置、连接测试、健康检查、代理支持
3. **PT 分类管理**：同步站点分类、自动映射到标准分类
4. **PT 资源同步**：MTeam 适配器、资源搜索、自动去重、促销识别、季集识别
5. **资源识别系统**：自动识别（电影/电视剧）、TMDB/豆瓣元数据关联、批量识别
6. **任务调度系统**：APScheduler、后台任务、进度跟踪、任务历史
7. **订阅系统**：电视剧季度订阅、资源自动匹配、质量优先级、自动下载
8. **媒体文件管理**：文件扫描、整理规则、目录管理、元数据刮削
9. **下载管理**：qBittorrent 集成、任务监控、自动下载
10. **通知系统**：事件驱动、多渠道通知、Telegram/Email 集成
11. **媒体服务器集成**：Jellyfin/Emby/Plex 连接、媒体库同步、观看历史跟踪



---

## 开发指南

### 快速开始

#### 后端开发
```bash
cd backend
python -m venv venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
python -m app.main      # 启动开发服务器
```

**API 文档**：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

#### 前端开发
```bash
cd frontend
npm install
npm run dev  # 访问 http://localhost:5173
```

### 数据库迁移

```bash
cd backend

# 生成迁移脚本
alembic revision --autogenerate -m "描述变更内容"

# 应用迁移
alembic upgrade head

# 查看当前版本
alembic current

# 回滚到上一个版本
alembic downgrade -1
```

**重要提示**:
- ✅ 每次修改模型后运行 `alembic revision --autogenerate`
- ✅ 生成后**必须手动检查并裁剪**迁移脚本，只保留本次真正变更的部分
- ⚠️ autogenerate 会检测所有历史 schema 差异，生成大量无关的 `alter_column`/`drop_table`，**必须全部删除**
- ⚠️ autogenerate 生成的脚本可能引用 `app.core.json_types.JSON()` 等自定义类型但不导入，直接执行会报 `NameError`，裁剪掉这些行即可
- ⚠️ 生产环境部署前先在测试环境验证
- ⚠️ 禁止手动修改已提交（已 upgrade）的迁移脚本

**标准裁剪流程**：autogenerate 后，迁移文件只应包含：
```python
def upgrade() -> None:
    # 只写本次新增/修改的内容，例如：
    op.add_column('table_name', sa.Column('new_col', sa.DateTime(timezone=True), nullable=True))
    op.create_index('ix_table_name_new_col', 'table_name', ['new_col'], unique=False)

def downgrade() -> None:
    op.drop_index('ix_table_name_new_col', table_name='table_name')
    op.drop_column('table_name', 'new_col')
```

详见：[数据库迁移指南](backend/docs/database/09-deployment.md)

---

## 核心开发规范

### 1. 命名规范
- **类名**：大驼峰（PascalCase）- `PTSiteService`
- **函数/方法名**：小写下划线（snake_case）- `fetch_resources`
- **常量**：大写下划线（UPPER_CASE）- `MEDIA_TYPE_MOVIE`
- **变量**：小写下划线（snake_case）- `user_id`

### 2. 使用常量避免魔法字符串

```python
# ❌ 错误：硬编码字符串
if resource.category == "movie":
    ...

# ✅ 正确：使用常量
from app.constants import MEDIA_TYPE_MOVIE
if resource.category == MEDIA_TYPE_MOVIE:
    ...
```

### 3. 架构分层
- **不使用 Repository 层**，Service 层直接访问数据库
- 架构：`API 路由 → Service 层 → Database`

```python
class PTSiteService:
    @staticmethod
    async def get_by_id(db: AsyncSession, site_id: int):
        result = await db.execute(select(PTSite).where(PTSite.id == site_id))
        return result.scalar_one_or_none()
```

### 4. 时区处理

**核心原则**：数据库统一存储 UTC 时间，应用层使用 `Asia/Shanghai` 时区。

- **存储层**：`TZDateTime` 自定义类型自动将时间转为 UTC 写入数据库，读取时转回 `Asia/Shanghai`
- **应用层**：始终使用 `now()` 获取带时区的当前时间，禁止使用 `datetime.now()` / `datetime.utcnow()`
- **前端传递**：时间字段带时区信息（如 `2025-11-22T18:30:00+08:00`）

```python
# ✅ 正确：使用时区工具函数
from app.utils.timezone import now, parse_pt_site_time

current_time = now()  # 返回 Asia/Shanghai 带时区: 2025-11-22 18:30:00+08:00
# 写入数据库时 TZDateTime 自动转为 UTC: 2025-11-22 10:30:00+00:00
# 读取时自动转回 Asia/Shanghai

published_at = parse_pt_site_time("2025-11-22 18:30:00")

# ❌ 错误：禁止使用
# current_time = datetime.now()      # 无时区信息，与数据库 aware datetime 运算会报 TypeError
# current_time = datetime.utcnow()   # 已废弃
```

**模型层**：
```python
from app.utils.timezone import now
from app.core.db_types import TZDateTime

created_at = Column(
    TZDateTime(),  # 自动处理 UTC 存储和时区转换
    default=now,
    nullable=False
)
```

### 5. 异步编程
- 使用 `async/await` 进行数据库操作和 HTTP 请求
- `AsyncSession` 用于数据库会话
- `httpx.AsyncClient` 用于异步 HTTP 请求
- 使用 `asyncio.sleep()` 而非 `time.sleep()`

### 6. 任务处理器架构

使用**注册表模式**管理后台任务处理器。

**核心概念**：
- 每种任务类型有独立的处理器类（继承 `BaseTaskHandler`）
- 统一的 `execute(db, params, execution_id)` 接口
- `TaskHandlerRegistry` 动态管理任务类型映射

**添加新任务类型**（5 步）：
1. 在 `constants/task.py` 定义常量：`TASK_TYPE_MY_TASK = "my_task"`
2. 创建 `tasks/handlers/my_task_handler.py`，继承 `BaseTaskHandler`
3. 在 `tasks/handlers/__init__.py` 导出处理器类
4. 在 `tasks/registry.py` 的 `register_all_handlers()` 中注册
5. 创建任务时使用 `handler=TASK_TYPE_MY_TASK`

详见：[任务处理器架构文档](backend/docs/task_handler_architecture.md)

### 7. 事件系统

使用**发布-订阅模式**解耦业务逻辑和事件处理。

```python
# 发布事件
from app.events.bus import event_bus

await event_bus.publish("download_completed", {
    "user_id": 1,
    "media_name": "复仇者联盟",
    "size_gb": 15.5
})
```

**扩展方式**：
- 在 `app/events/handlers/` 下创建新处理器
- 在 `manager.py` 的 `_register_listeners()` 中注册

详见：[事件总线指南](backend/docs/event_bus_guide.md)

---

## 文档索引

### 核心文档
- **数据库设计**：[backend/docs/database/README.md](backend/docs/database/README.md)
- **PT 站点集成**：
  - [mteam_quick_start.md](backend/docs/mteam_quick_start.md) - MTeam 快速接入
  - [category_management.md](backend/docs/category_management.md) - 分类管理指南
- **系统架构**：
  - [task_handler_architecture.md](backend/docs/task_handler_architecture.md) - 任务处理器架构
  - [event_bus_guide.md](backend/docs/event_bus_guide.md) - 事件总线指南
  - [notification_system_design.md](backend/docs/notification_system_design.md) - 通知系统设计
- **部署相关**：
  - [alembic_migration.md](backend/docs/alembic_migration.md) - 数据库迁移指南
  - [production_deploy.md](backend/docs/production_deploy.md) - 生产环境部署

### 实现指南
- **时区处理**：[simplified_timezone_guide.md](backend/docs/simplified_timezone_guide.md)
- **媒体整理**：[media_organization_guide.md](backend/docs/media_organization_guide.md)
- **元数据管理**：[metadata_management.md](backend/docs/metadata_management.md)
- **刮削逻辑**：[scraping_logic.md](backend/docs/scraping_logic.md)

---

## 开发流程

### 添加新功能
1. **定义常量**：在 `app/constants/` 中定义相关常量
2. **创建模型**：在 `app/models/` 中定义数据模型
3. **编写 Service**：在 `app/services/` 中实现业务逻辑
4. **定义 Schema**：在 `app/schemas/` 中定义 Pydantic 模型
5. **创建 API**：在 `app/api/v1/` 中创建路由
6. **前端集成**：在 `frontend/src/api/` 中封装 API 调用
7. **编写文档**：在 `backend/docs/` 中添加相关文档

### 代码提交
- 遵循常量规范，避免魔法字符串
- 使用时区工具函数，禁止 `datetime.utcnow()`
- Service 层直接访问数据库，无需 Repository
- 前端 API 使用相对路径（不含 `/api/v1`）

---

## 常见问题

### Q: 如何添加新的 PT 站点适配器？
A: 参考 `app/adapters/pt_sites/mteam.py`，继承 `BasePTSiteAdapter`，实现必要方法。

### Q: 如何修改系统时区？
A: 修改 `backend/app/core/config.py` 中 `TIMEZONE` 配置，重启应用。

### Q: 如何创建后台任务？
A: 参考任务调度系统架构，定义任务类型常量，注册处理器，创建 API 接口。详见[任务处理器架构文档](backend/docs/task_handler_architecture.md)。

### Q: 前端 API 请求 404？
A: 检查环境变量 `VITE_API_BASE_URL` 是否包含 `/api/v1`，API 模块是否使用相对路径。

### Q: 数据库迁移失败？
A: 查看详细指南：[backend/docs/alembic_migration.md](backend/docs/alembic_migration.md)

---

**文档维护者**: Claude Code
**最后更新**: 2026-01-24
**版本**: v3.0
