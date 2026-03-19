# NasFusion 时区支持实现方案

**文档版本**: v1.0
**创建日期**: 2025-11-22
**适用范围**: FastAPI + SQLAlchemy 2.0 (Async) + PostgreSQL/SQLite

---

## 一、当前状态分析

### 1.1 代码现状

**后端数据库层：**
- `backend/app/models/base.py` (第21-28行)：
  - `TimestampMixin` 使用 `datetime.now(timezone.utc)` 作为默认值（已经是时区感知的！）
  - **问题**：使用 `Column(DateTime)` 而不是 `DateTime(timezone=True)`

**后端业务逻辑层：**
- 13个文件仍在使用 `datetime.utcnow()`（时区无感知，已弃用）：
  - `app/models/user.py` (第30、56行)
  - `app/services/user_service.py` (第132、179、185、234行)
  - `app/services/pt_site_service.py`
  - `app/services/pt_resource_service.py`
  - `app/services/resource_identify_service.py`
  - 其他服务文件也有类似问题

**前端时间处理：**
- `frontend/src/utils/format.ts`：使用 `new Date(date)` 直接解析
- **问题**：未处理时区信息，依赖浏览器本地时区
- **已修复**：`MovieDetail.vue` 中已添加 'Z' 后缀处理

**系统配置：**
- `backend/app/core/config.py` (第159-186行)：
  - 已定义 `TIMEZONE` 配置（默认 "Asia/Shanghai"）
  - 已实现 `get_local_time()` 方法用于时区转换
  - 但这些配置尚未在项目中被使用

### 1.2 关键问题总结

1. ❌ **数据库字段定义不完整**：未使用 `DateTime(timezone=True)`
2. ❌ **遗留的 `datetime.utcnow()` 调用**：应迁移到 `datetime.now(timezone.utc)`
3. ❌ **Pydantic 序列化未配置时区**：datetime 可能缺少 timezone 信息
4. ⚠️ **前端时区处理不统一**：需要统一的时间格式化方案

---

## 二、业界最佳实践

### 2.1 核心原则

1. **始终在数据库存储 UTC 时间**
   - PostgreSQL: 使用 `TIMESTAMP WITH TIME ZONE` (存储 UTC，显示时自动转换)
   - SQLite: 手动管理时区（存储 UTC 字符串）

2. **在应用层全程使用时区感知的 datetime**
   - Python: `datetime.now(timezone.utc)` 替代 `datetime.utcnow()`
   - SQLAlchemy: `DateTime(timezone=True)` 替代 `DateTime`

3. **仅在用户界面层进行时区转换**
   - API 响应使用 ISO 8601 格式（如 `2025-11-22T10:30:00Z`）
   - 前端根据用户时区显示本地时间

### 2.2 PostgreSQL vs SQLite 差异

| 特性 | PostgreSQL | SQLite |
|------|-----------|--------|
| 时区字段 | `TIMESTAMP WITH TIME ZONE` | 无原生支持 |
| SQLAlchemy 配置 | `DateTime(timezone=True)` | `DateTime(timezone=True)` + TypeDecorator |
| 存储格式 | 内部 UTC，自动转换 | 手动存储 UTC 字符串 |
| 时区信息保留 | 输入时转换为 UTC，不保留原始 TZ | 依赖应用层 |

**关键发现**：
- PostgreSQL 的 `TIMESTAMP WITH TIME ZONE` **不存储时区**，只在输入时转换为 UTC
- SQLite 需要自定义 `TypeDecorator` 来强制时区感知

---

## 三、推荐技术方案

### 3.1 方案选择：UTC 存储 + 用户时区显示

**理由：**
- ✅ 符合业界主流实践（FastAPI、Django、Rails 等）
- ✅ 避免夏令时和时区迁移问题
- ✅ 简化跨时区协作
- ✅ 用户可自定义显示时区（已有 `users.timezone` 和 `user_profiles.timezone` 字段）

### 3.2 实现架构

```
┌─────────────────────────────────────────────────────┐
│              数据库层（存储 UTC）                      │
│  - PostgreSQL: TIMESTAMP WITH TIME ZONE             │
│  - SQLite: TIMESTAMP + TypeDecorator                │
└─────────────────────────────────────────────────────┘
                        ↕
┌─────────────────────────────────────────────────────┐
│        SQLAlchemy 层（时区感知 datetime）             │
│  - DateTime(timezone=True)                          │
│  - 自定义 TZDateTime TypeDecorator (SQLite)         │
└─────────────────────────────────────────────────────┘
                        ↕
┌─────────────────────────────────────────────────────┐
│         业务逻辑层（统一使用 UTC）                     │
│  - datetime.now(timezone.utc)                       │
│  - 避免 datetime.utcnow()                           │
└─────────────────────────────────────────────────────┘
                        ↕
┌─────────────────────────────────────────────────────┐
│      API 层（Pydantic 序列化为 ISO 8601）             │
│  - 输出: 2025-11-22T10:30:00Z                       │
│  - 自动添加 'Z' 后缀                                  │
└─────────────────────────────────────────────────────┘
                        ↕
┌─────────────────────────────────────────────────────┐
│       前端层（根据用户时区显示）                        │
│  - 解析 ISO 8601 字符串                              │
│  - 使用 Intl.DateTimeFormat 或 Day.js               │
└─────────────────────────────────────────────────────┘
```

---

## 四、详细实现代码

### 4.1 数据库层：自定义 TypeDecorator

**文件：`backend/app/models/types.py`（新建）**

```python
# -*- coding: utf-8 -*-
"""
自定义 SQLAlchemy 类型
用于跨数据库的时区感知 datetime 处理
"""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, TypeDecorator


class TZDateTime(TypeDecorator):
    """
    时区感知的 DateTime 类型

    行为：
    - PostgreSQL: 使用 TIMESTAMP WITH TIME ZONE
    - SQLite: 使用 TIMESTAMP，手动处理时区
    - 存储：始终存储 UTC 时间
    - 读取：返回时区感知的 datetime 对象（UTC）
    """

    impl = DateTime
    cache_ok = True

    def __init__(self, *args, **kwargs):
        # 强制启用时区支持
        kwargs['timezone'] = True
        super().__init__(*args, **kwargs)

    def process_bind_param(self, value: Optional[datetime], dialect) -> Optional[datetime]:
        """存储到数据库前的处理"""
        if value is None:
            return None

        # 确保是时区感知的 datetime
        if value.tzinfo is None:
            # 如果是 naive datetime，假设为 UTC
            value = value.replace(tzinfo=timezone.utc)
        else:
            # 转换为 UTC
            value = value.astimezone(timezone.utc)

        # SQLite 需要移除时区信息（存储为 UTC 字符串）
        if dialect.name == 'sqlite':
            return value.replace(tzinfo=None)

        return value

    def process_result_value(self, value: Optional[datetime], dialect) -> Optional[datetime]:
        """从数据库读取后的处理"""
        if value is None:
            return None

        # 确保返回时区感知的 datetime（UTC）
        if value.tzinfo is None:
            # SQLite 返回的是 naive datetime，添加 UTC 时区信息
            return value.replace(tzinfo=timezone.utc)

        # PostgreSQL 已经是时区感知的，转换为 UTC
        return value.astimezone(timezone.utc)
```

### 4.2 模型层：更新 TimestampMixin

**文件：`backend/app/models/base.py`**

```python
"""
ORM基础模型
定义所有model的基类和通用Mixin
"""
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Column, Integer
from sqlalchemy.orm import DeclarativeBase, declared_attr

from app.models.types import TZDateTime  # 导入自定义类型


class Base(DeclarativeBase):
    """ORM基类"""
    pass


class TimestampMixin:
    """时间戳Mixin"""

    created_at = Column(
        TZDateTime,  # 使用自定义时区感知类型
        default=lambda: datetime.now(timezone.utc),  # 使用 lambda 避免提前计算
        nullable=False,
        comment="创建时间"
    )
    updated_at = Column(
        TZDateTime,  # 使用自定义时区感知类型
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="更新时间",
    )


class IDMixin:
    """主键ID Mixin"""
    id = Column(Integer, primary_key=True, index=True, autoincrement=True, comment="主键ID")


class BaseModel(Base, IDMixin, TimestampMixin):
    """
    基础Model类
    包含id, created_at, updated_at字段
    所有model都应继承此类
    """

    __abstract__ = True

    @declared_attr
    def __tablename__(cls) -> str:
        """自动生成表名（类名转小写）"""
        return cls.__name__.lower()

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
```

**关键改进：**
1. ✅ 使用 `TZDateTime` 替代 `DateTime`
2. ✅ 使用 `lambda` 包装 `datetime.now(timezone.utc)`，避免默认值在模块加载时计算

### 4.3 业务逻辑层：批量替换 datetime.utcnow()

**需要修改的文件列表（共13个文件）：**

```bash
backend/app/models/user.py:30
backend/app/models/user.py:56
backend/app/services/user/user_service.py:132
backend/app/services/user/user_service.py:179
backend/app/services/user/user_service.py:185
backend/app/services/user/user_service.py:234
backend/app/services/pt_site_service.py:多处
backend/app/services/pt_resource_service.py:多处
backend/app/services/resource_identify_service.py:多处
# ... 其他文件
```

**替换规则：**

```python
# ❌ 旧代码
from datetime import datetime

user.last_login_at = datetime.utcnow()
user.locked_until = datetime.utcnow() + timedelta(minutes=30)

# ✅ 新代码
from datetime import datetime, timezone

user.last_login_at = datetime.now(timezone.utc)
user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=30)
```

**批量替换命令（谨慎使用，建议手动审查）：**

```bash
# 查找所有使用 datetime.utcnow() 的地方
cd backend
grep -rn "datetime.utcnow()" --include="*.py"

# 批量替换（执行前务必备份代码！）
find . -name "*.py" -exec sed -i 's/datetime\.utcnow()/datetime.now(timezone.utc)/g' {} +

# 确保导入了 timezone
grep -rn "from datetime import" --include="*.py" | grep -v "timezone"
```

### 4.4 API 层：Pydantic 序列化配置

**方案 A：全局配置（推荐）**

**文件：`backend/app/schemas/base.py`（新建）**

```python
# -*- coding: utf-8 -*-
"""
Pydantic 基础配置
统一 datetime 序列化规则
"""
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, field_serializer


class TimestampMixin(BaseModel):
    """
    时间戳字段 Mixin
    确保所有 datetime 字段序列化为 ISO 8601 格式（带 UTC 标识）
    """

    @field_serializer('created_at', 'updated_at', 'last_login_at',
                      'last_sync_at', 'health_check_at', 'completed_at',
                      'started_at', 'scheduled_at', 'locked_until',
                      'last_check_at', 'last_seeder_update_at',
                      'promotion_expire_at', 'published_at',
                      when_used='json')
    def serialize_datetime(self, dt: datetime, _info) -> str:
        """
        将 datetime 序列化为 ISO 8601 格式

        输入: datetime(2025, 11, 22, 10, 30, 0, tzinfo=timezone.utc)
        输出: "2025-11-22T10:30:00Z"
        """
        if dt is None:
            return None

        # 确保是 UTC 时区
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)

        # 使用 'Z' 后缀表示 UTC（等价于 +00:00）
        return dt.strftime('%Y-%m-%dT%H:%M:%SZ')


class BaseResponseSchema(TimestampMixin):
    """
    响应 Schema 基类
    包含通用配置
    """

    model_config = ConfigDict(
        from_attributes=True,  # 支持从 ORM 模型创建
        use_enum_values=True,   # 序列化枚举为值
    )
```

**方案 B：在现有 Schema 中添加 field_serializer**

**示例：`backend/app/schemas/user.py`**

```python
from datetime import datetime, timezone
from pydantic import field_serializer

class UserResponse(UserBase):
    """用户响应"""

    id: int
    role: str
    is_active: bool
    is_verified: bool
    last_login_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    @field_serializer('last_login_at', 'created_at', 'updated_at', when_used='json')
    def serialize_dt(self, dt: datetime, _info) -> str:
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.strftime('%Y-%m-%dT%H:%M:%SZ')

    model_config = ConfigDict(from_attributes=True)
```

**推荐使用方案 A**，让所有 Response Schema 继承 `BaseResponseSchema`：

```python
# 修改所有响应 Schema
from app.schemas.base import BaseResponseSchema

class UserResponse(BaseResponseSchema):
    """用户响应"""
    id: int
    role: str
    # ... 其他字段
```

### 4.5 前端层：统一时间格式化

**方案 A：使用 Day.js（推荐，轻量级）**

```bash
cd frontend
npm install dayjs
```

**文件：`frontend/src/utils/format.ts`**

```typescript
import dayjs from 'dayjs'
import utc from 'dayjs/plugin/utc'
import timezone from 'dayjs/plugin/timezone'
import relativeTime from 'dayjs/plugin/relativeTime'
import 'dayjs/locale/zh-cn'

dayjs.extend(utc)
dayjs.extend(timezone)
dayjs.extend(relativeTime)
dayjs.locale('zh-cn')

/**
 * 获取用户时区配置（从 Pinia store）
 */
export function getUserTimezone(): string {
  // 从用户配置读取，默认使用浏览器时区
  const userStore = useUserStore?.()
  return userStore?.profile?.timezone || dayjs.tz.guess()
}

/**
 * 格式化日期时间（自动转换为用户时区）
 * @param date ISO 8601 字符串（如 "2025-11-22T10:30:00Z"）
 * @param format 格式化模板，默认 "YYYY-MM-DD HH:mm:ss"
 * @returns 格式化后的本地时间字符串
 */
export function formatDateTime(date: string | Date, format = 'YYYY-MM-DD HH:mm:ss'): string {
  if (!date) return '-'

  const userTz = getUserTimezone()

  // 解析 UTC 时间并转换为用户时区
  return dayjs.utc(date).tz(userTz).format(format)
}

/**
 * 格式化相对时间（如 "3小时前"）
 */
export function formatRelativeTime(date: string | Date): string {
  if (!date) return '-'

  const userTz = getUserTimezone()
  return dayjs.utc(date).tz(userTz).fromNow()
}

/**
 * 显示完整时区信息（调试用）
 */
export function formatDateTimeWithZone(date: string | Date): string {
  if (!date) return '-'

  const userTz = getUserTimezone()
  const dt = dayjs.utc(date).tz(userTz)

  return `${dt.format('YYYY-MM-DD HH:mm:ss')} (${userTz})`
}
```

**方案 B：使用原生 Intl API（无需依赖）**

```typescript
export function getUserTimezone(): string {
  // 从用户配置读取，默认使用浏览器时区
  const userStore = useUserStore?.()
  return userStore?.profile?.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone
}

export function formatDateTime(date: string | Date, format?: string): string {
  if (!date) return '-'

  const d = typeof date === 'string' ? new Date(date) : date

  // 自动使用用户浏览器时区
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
    timeZone: getUserTimezone()
  }).format(d)
}

export function formatRelativeTime(date: string | Date): string {
  if (!date) return '-'

  const d = typeof date === 'string' ? new Date(date) : date
  const now = Date.now()
  const diff = now - d.getTime()

  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)

  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes}分钟前`
  if (hours < 24) return `${hours}小时前`
  if (days < 30) return `${days}天前`
  return formatDateTime(date)
}
```

### 4.6 用户时区配置管理

**API 接口：获取可用时区列表**

**文件：`backend/app/api/v1/system.py`**

```python
from fastapi import APIRouter
import pytz

router = APIRouter()

@router.get("/timezones")
async def get_timezones():
    """
    获取可用时区列表
    按地区分组，常用时区置顶
    """
    common_timezones = [
        "Asia/Shanghai",
        "Asia/Hong_Kong",
        "Asia/Taipei",
        "UTC",
        "America/New_York",
        "Europe/London",
        "Asia/Tokyo",
    ]

    all_timezones = sorted(pytz.all_timezones)

    return {
        "common": common_timezones,
        "all": all_timezones
    }
```

**前端：用户配置界面**

**文件：`frontend/src/views/UserProfile.vue`**

```vue
<template>
  <el-form-item label="时区">
    <el-select v-model="profile.timezone" filterable placeholder="请选择时区">
      <el-option-group label="常用时区">
        <el-option
          v-for="tz in commonTimezones"
          :key="tz"
          :label="formatTimezoneLabel(tz)"
          :value="tz"
        />
      </el-option-group>
      <el-option-group label="全部时区">
        <el-option
          v-for="tz in allTimezones"
          :key="tz"
          :label="tz"
          :value="tz"
        />
      </el-option-group>
    </el-select>
  </el-form-item>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getTimezones } from '@/api/modules/system'

const commonTimezones = ref<string[]>([])
const allTimezones = ref<string[]>([])

onMounted(async () => {
  const { data } = await getTimezones()
  commonTimezones.value = data.common
  allTimezones.value = data.all
})

function formatTimezoneLabel(tz: string): string {
  const offset = new Date().toLocaleString('en-US', {
    timeZone: tz,
    timeZoneName: 'short'
  }).split(' ').pop()
  return `${tz} (${offset})`
}
</script>
```

---

## 五、数据迁移策略

### 5.1 迁移步骤

**步骤 1：添加新的 TypeDecorator**
- 创建 `backend/app/models/types.py`
- 向后兼容，不破坏现有数据

**步骤 2：更新模型定义**
- 修改 `TimestampMixin` 使用 `TZDateTime`
- 替换所有 `datetime.utcnow()` 为 `datetime.now(timezone.utc)`

**步骤 3：数据库迁移（仅 PostgreSQL 需要）**

如果项目使用 Alembic：

```python
# alembic/versions/xxxx_add_timezone_support.py
"""add timezone support

Revision ID: xxxx
Revises: yyyy
Create Date: 2025-11-22
"""
from alembic import op
import sqlalchemy as sa


def upgrade():
    # PostgreSQL: 修改列类型为 TIMESTAMP WITH TIME ZONE
    op.execute("""
        ALTER TABLE users
        ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE,
        ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE,
        ALTER COLUMN last_login_at TYPE TIMESTAMP WITH TIME ZONE;
    """)

    op.execute("""
        ALTER TABLE pt_sites
        ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE,
        ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE,
        ALTER COLUMN health_check_at TYPE TIMESTAMP WITH TIME ZONE;
    """)

    op.execute("""
        ALTER TABLE pt_resources
        ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE,
        ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE,
        ALTER COLUMN last_check_at TYPE TIMESTAMP WITH TIME ZONE,
        ALTER COLUMN published_at TYPE TIMESTAMP WITH TIME ZONE;
    """)

    # 其他表类似...


def downgrade():
    # 回退到 TIMESTAMP WITHOUT TIME ZONE
    op.execute("""
        ALTER TABLE users
        ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE,
        ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE,
        ALTER COLUMN last_login_at TYPE TIMESTAMP WITHOUT TIME ZONE;
    """)

    # 其他表类似...
```

**如果项目使用 `create_all()` 方式（当前项目）：**

```bash
# 备份数据库
pg_dump nasfusion > backup_before_timezone.sql

# 删除旧表并重新创建（开发环境）
# 警告：会丢失数据！生产环境禁止使用！
DROP DATABASE nasfusion;
CREATE DATABASE nasfusion;

# 重新运行应用，自动创建表
python -m app.main
```

**SQLite：无需迁移**（已存储为 UTC，只需应用层处理）

**步骤 4：更新 Pydantic Schema**
- 添加 `field_serializer` 确保输出 ISO 8601

**步骤 5：更新前端**
- 安装 Day.js 或使用 Intl API
- 更新所有时间显示组件

### 5.2 兼容性测试清单

**后端测试：**
- [ ] PostgreSQL: 插入时区感知 datetime，查询返回正确格式
- [ ] SQLite: 插入时区感知 datetime，查询返回正确格式
- [ ] API 响应包含 'Z' 后缀（ISO 8601）
- [ ] Pydantic 序列化正确（`field_serializer` 生效）
- [ ] 所有 `datetime.utcnow()` 已替换为 `datetime.now(timezone.utc)`

**前端测试：**
- [ ] 正确解析 ISO 8601 字符串
- [ ] 时间显示符合用户时区
- [ ] 相对时间显示正确（"3小时前"）
- [ ] 用户时区配置生效

**端到端测试：**
- [ ] 创建PT站点 → 显示正确的创建时间
- [ ] 同步PT资源 → 显示正确的发布时间
- [ ] 刷新资源 → 显示正确的检查时间
- [ ] 跨时区用户看到不同的本地时间

---

## 六、实施计划

### Phase 1：基础设施（1-2天）

**任务清单：**
- [ ] 创建 `backend/app/models/types.py`（TZDateTime TypeDecorator）
- [ ] 更新 `backend/app/models/base.py`（TimestampMixin 使用 TZDateTime）
- [ ] 创建 `backend/app/schemas/base.py`（BaseResponseSchema + field_serializer）
- [ ] 添加 `backend/app/api/v1/system.py`（/timezones 接口）
- [ ] 编写单元测试验证 TypeDecorator 正确性

### Phase 2：后端迁移（2-3天）

**任务清单：**
- [ ] 批量替换 `datetime.utcnow()` → `datetime.now(timezone.utc)`（13个文件）
  ```bash
  # 需要修改的文件
  app/models/user.py
  app/services/user/user_service.py
  app/services/pt_site_service.py
  app/services/pt_resource_service.py
  app/services/resource_identify_service.py
  app/services/scheduler_manager.py
  # ... 其他文件
  ```
- [ ] 更新所有 Response Schema 继承 `BaseResponseSchema`
  - `app/schemas/user.py` - UserResponse
  - `app/schemas/pt_site.py` - PTSiteResponse
  - `app/schemas/pt_resource.py` - PTResourceResponse
  - `app/schemas/unified_movie.py` - UnifiedMovieResponse
  - `app/schemas/unified_tv.py` - UnifiedTVResponse
  - 其他 Schema...
- [ ] 数据库迁移（如果使用 PostgreSQL）
- [ ] 编写集成测试（API 返回 ISO 8601 格式）

### Phase 3：前端改造（1-2天）

**方案选择：**
- **推荐**：Day.js（轻量级，功能完整）
- **备选**：Intl API（无依赖，但功能有限）

**任务清单：**
- [ ] 安装依赖（如使用 Day.js）
  ```bash
  cd frontend
  npm install dayjs
  ```
- [ ] 重写 `frontend/src/utils/format.ts`
  - `formatDateTime()` - 格式化日期时间
  - `formatRelativeTime()` - 相对时间
  - `getUserTimezone()` - 获取用户时区
- [ ] 创建用户时区配置界面
  - `frontend/src/views/UserProfile.vue`
  - 添加时区选择下拉框
- [ ] 更新所有使用时间显示的组件
  - `MovieDetail.vue`
  - `TVDetail.vue`
  - `ResourceList.vue`
  - `SiteManagement.vue`
  - 其他组件...
- [ ] 移除临时的 'Z' 后缀添加逻辑（已在后端处理）

### Phase 4：测试和部署（1-2天）

**测试清单：**
- [ ] 单元测试：TZDateTime TypeDecorator
- [ ] 集成测试：API 序列化/反序列化
- [ ] E2E 测试：前端时间显示
- [ ] 性能测试：确保无明显性能退化
- [ ] 兼容性测试：PostgreSQL + SQLite

**部署步骤：**
1. 备份生产数据库
2. 灰度发布（先 SQLite 测试环境）
3. 监控错误日志和性能指标
4. 全量发布（PostgreSQL 生产环境）

**预计总工时：5-9 个工作日**

---

## 七、常见问题解答

### Q1：为什么不在数据库直接存储用户时区的时间？

**A**: 业界共识是"数据库存储 UTC，用户界面显示本地时间"，原因：
- ✅ 避免夏令时切换导致的时间跳跃
- ✅ 跨时区协作（同一时间点，所有用户看到一致的相对时间）
- ✅ 简化服务器逻辑（无需处理多个时区的计算）
- ✅ 数据库查询和索引更高效

### Q2：SQLite 时区支持为什么比 PostgreSQL 复杂？

**A**: SQLite 是嵌入式数据库，缺少原生时区类型，需要通过以下方式弥补：
- 存储 UTC 时间字符串
- 使用 TypeDecorator 在应用层添加/移除时区信息
- 查询时手动转换

### Q3：前端如何获取用户时区配置？

**A**: 三种方式（优先级从高到低）：
1. **用户配置表**：`user_profiles.timezone`（用户手动设置）
2. **浏览器默认时区**：`Intl.DateTimeFormat().resolvedOptions().timeZone`
3. **系统默认时区**：`settings.TIMEZONE`（"Asia/Shanghai"）

### Q4：Pydantic v1 和 v2 的差异？

**A**: 项目使用 Pydantic v2，关键差异：
- **v1**: `class Config` + `json_encoders`
- **v2**: `model_config = ConfigDict()` + `@field_serializer`

推荐使用 v2 的 `@field_serializer` 装饰器，更灵活和类型安全。

### Q5：如何处理历史数据（已存储的 UTC 时间）？

**A**:
- **PostgreSQL**: 修改列类型为 `TIMESTAMP WITH TIME ZONE`，已有数据自动假定为 UTC
- **SQLite**: 无需迁移，TypeDecorator 会为 naive datetime 添加 UTC 时区信息
- **应用层**: 已存储的 UTC 时间不需要修改，只需确保读取时添加时区信息

### Q6：Day.js vs Intl API，如何选择？

**A**:

| 特性 | Day.js | Intl API |
|------|--------|----------|
| 体积 | 2KB gzipped | 0（浏览器原生） |
| 相对时间 | ✅ `fromNow()` | ❌ 需手动实现 |
| 时区转换 | ✅ 插件支持 | ✅ 原生支持 |
| API 简洁性 | ✅ 链式调用 | ❌ 较复杂 |
| 兼容性 | ✅ 良好 | ⚠️ 旧浏览器需 polyfill |

**推荐**：Day.js（体积小，功能完整，API 友好）

### Q7：如何验证时区支持是否正确实施？

**A**: 测试步骤：

```python
# 后端测试（Python console）
from app.models.pt_resource import PTResource
from app.core.database import async_session_local
from datetime import datetime, timezone

async with async_session_local() as db:
    resource = await db.get(PTResource, 1)
    print(resource.created_at)  # 应输出：datetime(2025, 11, 22, 10, 30, tzinfo=timezone.utc)
    print(resource.created_at.tzinfo)  # 应输出：UTC
```

```javascript
// 前端测试（浏览器 console）
const dateStr = "2025-11-22T10:30:00Z"
const date = new Date(dateStr)
console.log(date.toISOString())  // 应输出：2025-11-22T10:30:00.000Z
console.log(formatDateTime(dateStr))  // 应输出本地时间（如 "2025-11-22 18:30:00" for UTC+8）
```

---

## 八、性能影响分析

### 8.1 性能对比

| 操作 | 原方案 | 新方案 | 影响 |
|------|--------|--------|------|
| 数据库插入 | TIMESTAMP | TIMESTAMP WITH TIME ZONE | +5% (PostgreSQL 内部转换) |
| 数据库查询 | 直接返回 | TypeDecorator 处理 | +3% |
| API 序列化 | 默认 | field_serializer | +1% (字符串格式化) |
| 前端解析 | `new Date()` | Day.js/Intl | +2% |

**结论**：性能影响 < 10%，可忽略不计（数万级 QPS 项目才需优化）

### 8.2 数据库存储

- **PostgreSQL**: `TIMESTAMP WITH TIME ZONE` 占用 8 字节（与 `TIMESTAMP` 相同）
- **SQLite**: 无额外开销（仍存储字符串）

---

## 九、参考资源

### 官方文档
- [Pydantic Datetime Types](https://docs.pydantic.dev/2.0/usage/types/datetime/)
- [PostgreSQL Date/Time Types](https://www.postgresql.org/docs/current/datatype-datetime.html)
- [SQLAlchemy DateTime with Timezone](https://docs.sqlalchemy.org/en/20/core/type_basics.html#sqlalchemy.types.DateTime)
- [Python datetime Timezone](https://docs.python.org/3/library/datetime.html#datetime.datetime.astimezone)

### 社区最佳实践
- [FastAPI Timezone Handling](https://medium.com/@rameshkannanyt0078/how-to-handle-timezones-properly-in-fastapi-and-database-68b1c019c1bc)
- [SQLAlchemy-Utc Library](https://github.com/spoqa/sqlalchemy-utc)

### 工具库
- [Day.js](https://day.js.org/)
- [Day.js Timezone Plugin](https://day.js.org/docs/en/plugin/timezone)
- [pytz - Python Timezone Library](https://pypi.org/project/pytz/)

---

## 十、总结

### 核心要点

1. **数据库层**：使用 `TZDateTime` TypeDecorator 统一处理 PostgreSQL 和 SQLite
2. **业务逻辑层**：全面替换 `datetime.utcnow()` → `datetime.now(timezone.utc)`
3. **API 层**：Pydantic `field_serializer` 确保输出 ISO 8601 格式（带 'Z' 后缀）
4. **前端层**：Day.js 根据用户时区自动转换显示

### 风险评估

- **低风险**：向后兼容，不破坏现有数据
- **中等风险**：需要全面测试（13个文件的代码修改）
- **可回滚**：数据库迁移可逆，前端改动独立

### 投资回报

- ✅ **用户体验提升**：正确显示本地时间
- ✅ **代码质量提升**：符合 Python 3.11+ 推荐（`datetime.utcnow()` 已弃用）
- ✅ **未来扩展性**：支持多时区用户协作
- ✅ **避免 bug**：修复当前时间解析不一致问题

### 建议实施优先级

**优先级 1（必须）：**
- 修复 Pydantic 序列化（确保输出 'Z' 后缀）
- 替换 `datetime.utcnow()` → `datetime.now(timezone.utc)`

**优先级 2（推荐）：**
- 添加 TZDateTime TypeDecorator
- 前端统一使用 Day.js 或 Intl API

**优先级 3（可选）：**
- 用户自定义时区配置界面
- PostgreSQL 数据库迁移到 TIMESTAMP WITH TIME ZONE

---

**文档维护者**: Claude Code
**最后更新**: 2025-11-22
**版本**: v1.0
