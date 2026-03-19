# NasFusion 简化时区方案

**文档版本**: v1.0
**创建日期**: 2025-11-22
**适用场景**: 单一时区用户群体（如仅中国用户）

---

## 一、方案概述

### 核心思路

**配置文件设定时区，全系统统一使用该时区时间**

- 📁 配置文件中设置 `TIMEZONE = "Asia/Shanghai"`
- 💾 数据库存储该时区的时间（不转换为 UTC）
- 🖥️ 前端直接显示，无需时区转换
- 🔄 PT站点时间直接存储（M-Team 等站点使用北京时间）

### 优势

- ✅ **实现简单**：无需复杂的时区转换逻辑
- ✅ **直观易懂**：数据库存储的就是用户看到的时间
- ✅ **无需转换**：PT站点时间可以直接存储
- ✅ **保留灵活性**：未来可通过修改配置文件切换时区

### 与完整方案的差异

| 特性 | 完整方案（UTC） | 简化方案（配置时区） |
|------|----------------|-------------------|
| 数据库存储 | UTC 时间 | 配置文件指定的时区时间 |
| 前端显示 | 需要转换 | 直接显示 |
| PT站点时间 | 需要转换（+8 → UTC） | 直接存储 |
| 代码复杂度 | 高 | 低 |
| 多时区支持 | ✅ | ❌ |
| 适用场景 | 全球用户 | 单一时区用户 |

---

## 二、实施步骤

### 步骤 1：确认配置文件已有时区设置

**文件：`backend/app/core/config.py`**

检查是否已存在 `TIMEZONE` 配置（当前项目已有）：

```python
class Settings(BaseSettings):
    # ... 其他配置

    # 时区配置
    TIMEZONE: str = Field(default="Asia/Shanghai", description="系统时区")

    def get_local_time(self, dt: Optional[datetime] = None) -> datetime:
        """
        获取指定时区的当前时间

        Args:
            dt: datetime对象（可选），默认为当前时间

        Returns:
            指定时区的datetime对象
        """
        import pytz

        tz = pytz.timezone(self.TIMEZONE)
        if dt is None:
            return datetime.now(tz)
        return dt.astimezone(tz)
```

✅ **已存在**，无需修改。

### 步骤 2：创建时区工具函数

**文件：`backend/app/utils/timezone.py`（新建）**

```python
# -*- coding: utf-8 -*-
"""
时区工具函数
统一管理系统时区
"""
from datetime import datetime
from typing import Optional

import pytz

from app.core.config import settings


def get_system_timezone():
    """获取系统配置的时区对象"""
    return pytz.timezone(settings.TIMEZONE)


def now() -> datetime:
    """
    获取系统时区的当前时间（时区感知）

    替代 datetime.now() 和 datetime.utcnow()

    Returns:
        系统时区的当前时间

    Example:
        >>> from app.utils.timezone import now
        >>> current_time = now()
        >>> print(current_time)  # 2025-11-22 18:30:00+08:00
    """
    tz = get_system_timezone()
    return datetime.now(tz)


def to_system_tz(dt: datetime) -> datetime:
    """
    将任意时区的 datetime 转换为系统时区

    Args:
        dt: datetime 对象（可以是任意时区或 naive）

    Returns:
        系统时区的 datetime

    Example:
        >>> from datetime import datetime, timezone as dt_timezone
        >>> utc_time = datetime(2025, 11, 22, 10, 30, tzinfo=dt_timezone.utc)
        >>> beijing_time = to_system_tz(utc_time)
        >>> print(beijing_time)  # 2025-11-22 18:30:00+08:00
    """
    tz = get_system_timezone()

    if dt.tzinfo is None:
        # 如果是 naive datetime，假设为 UTC
        dt = pytz.utc.localize(dt)

    return dt.astimezone(tz)


def parse_pt_site_time(time_str: str, format: str = "%Y-%m-%d %H:%M:%S") -> datetime:
    """
    解析 PT 站点返回的时间字符串（假定为系统时区）

    Args:
        time_str: 时间字符串（如 "2025-11-22 18:30:00"）
        format: 时间格式

    Returns:
        系统时区的 datetime 对象

    Example:
        >>> pt_time = parse_pt_site_time("2025-11-22 18:30:00")
        >>> print(pt_time)  # 2025-11-22 18:30:00+08:00
    """
    tz = get_system_timezone()
    naive_dt = datetime.strptime(time_str, format)
    return tz.localize(naive_dt)
```

### 步骤 3：更新模型定义

**文件：`backend/app/models/base.py`**

```python
"""
ORM基础模型
定义所有model的基类和通用Mixin
"""
from typing import Any

from sqlalchemy import Column, Integer, DateTime
from sqlalchemy.orm import DeclarativeBase, declared_attr

from app.utils.timezone import now  # 导入时区工具函数


class Base(DeclarativeBase):
    """ORM基类"""
    pass


class TimestampMixin:
    """时间戳Mixin"""

    created_at = Column(
        DateTime(timezone=True),  # 启用时区支持
        default=now,  # 使用系统时区的当前时间
        nullable=False,
        comment="创建时间"
    )
    updated_at = Column(
        DateTime(timezone=True),  # 启用时区支持
        default=now,
        onupdate=now,
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
- ✅ 使用 `DateTime(timezone=True)` 启用时区支持
- ✅ 使用 `app.utils.timezone.now` 替代 `datetime.now(timezone.utc)`
- ✅ 数据库将存储系统配置的时区时间

### 步骤 4：批量替换业务逻辑中的时间调用

**需要修改的文件（13个）：**

```python
# ❌ 旧代码
from datetime import datetime

user.last_login_at = datetime.utcnow()
user.locked_until = datetime.utcnow() + timedelta(minutes=30)

# ✅ 新代码
from app.utils.timezone import now

user.last_login_at = now()
user.locked_until = now() + timedelta(minutes=30)
```

**批量替换步骤：**

```bash
# 1. 查找所有使用 datetime.utcnow() 的地方
cd backend
grep -rn "datetime.utcnow()" --include="*.py"

# 2. 批量替换（执行前务必备份！）
find . -name "*.py" -exec sed -i 's/datetime\.utcnow()/now()/g' {} +

# 3. 批量添加导入（需手动检查每个文件）
# 在每个修改的文件顶部添加：
# from app.utils.timezone import now
```

**需要修改的文件列表：**
- `app/models/user.py`
- `app/services/user/user_service.py`
- `app/services/pt_site_service.py`
- `app/services/pt_resource_service.py`
- `app/services/resource_identify_service.py`
- `app/services/scheduler_manager.py`
- 其他使用 `datetime.utcnow()` 的文件

### 步骤 5：PT 站点适配器修改

**文件：`backend/app/adapters/pt_sites/mteam.py`**

修改时间解析逻辑，使用系统时区：

```python
from app.utils.timezone import parse_pt_site_time

class MTeamAdapter(BasePTSiteAdapter):

    async def parse_torrent(self, item: dict, site_id: int) -> dict:
        """解析种子信息"""

        # ❌ 旧代码：假设为 UTC
        # published_at = datetime.strptime(item["createdDate"], "%Y-%m-%d %H:%M:%S")

        # ✅ 新代码：解析为系统时区（Asia/Shanghai）
        published_at = parse_pt_site_time(item["createdDate"])

        # 促销过期时间
        promotion_expire_at = None
        if item.get("discount", {}).get("until"):
            promotion_expire_at = parse_pt_site_time(item["discount"]["until"])

        return {
            # ... 其他字段
            "published_at": published_at,
            "promotion_expire_at": promotion_expire_at,
        }
```

### 步骤 6：Pydantic 序列化配置

**文件：`backend/app/schemas/base.py`（新建）**

```python
# -*- coding: utf-8 -*-
"""
Pydantic 基础配置
统一 datetime 序列化规则
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_serializer

from app.utils.timezone import to_system_tz


class TimestampMixin(BaseModel):
    """
    时间戳字段 Mixin
    确保所有 datetime 字段序列化为 ISO 8601 格式（带时区信息）
    """

    @field_serializer('created_at', 'updated_at', 'last_login_at',
                      'last_sync_at', 'health_check_at', 'completed_at',
                      'started_at', 'scheduled_at', 'locked_until',
                      'last_check_at', 'last_seeder_update_at',
                      'promotion_expire_at', 'published_at',
                      when_used='json')
    def serialize_datetime(self, dt: Optional[datetime], _info) -> Optional[str]:
        """
        将 datetime 序列化为 ISO 8601 格式（带时区）

        输入: datetime(2025, 11, 22, 18, 30, 0, tzinfo=Asia/Shanghai)
        输出: "2025-11-22T18:30:00+08:00"
        """
        if dt is None:
            return None

        # 确保是系统时区
        dt = to_system_tz(dt)

        # 使用 isoformat() 输出标准 ISO 8601 格式
        return dt.isoformat()


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

**关键点：**
- ✅ 输出格式：`2025-11-22T18:30:00+08:00`（带时区偏移）
- ✅ 前端可以直接解析，无需手动添加 'Z' 后缀

### 步骤 7：前端时间处理（最简化）

**文件：`frontend/src/utils/format.ts`**

```typescript
/**
 * 格式化日期时间
 *
 * 后端返回格式：2025-11-22T18:30:00+08:00
 * 前端直接显示，无需时区转换
 */
export function formatDateTime(date: string | Date, format = 'YYYY-MM-DD HH:mm:ss'): string {
  if (!date) return '-'

  const d = typeof date === 'string' ? new Date(date) : date

  // 使用原生 Intl API 格式化（自动使用本地时区）
  const formatted = new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  }).format(d)

  // 格式化输出：2025/11/22 18:30:00 → 2025-11-22 18:30:00
  return formatted.replace(/\//g, '-').replace(/\s/g, ' ')
}

/**
 * 格式化相对时间（如 "3小时前"）
 */
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
  return formatDateTime(date, 'YYYY-MM-DD')
}
```

**关键点：**
- ✅ 无需安装 Day.js
- ✅ 使用原生 Intl API
- ✅ 前端直接显示后端返回的时间，无需转换

### 步骤 8：移除 MovieDetail.vue 中的临时修复

**文件：`frontend/src/views/MovieDetail.vue`**

移除之前添加的 'Z' 后缀处理逻辑：

```typescript
// ❌ 删除这段代码（不再需要）
const checkAndAutoRefresh = async () => {
  // ...

  // 关键修复：确保后端返回的UTC字符串被正确解析为UTC时间
  // 如果字符串不含 'Z' 后缀，手动添加以确保按UTC解析
  let lastCheckAtStr = resource.lastCheckAt
  if (!lastCheckAtStr.endsWith('Z') && !lastCheckAtStr.includes('+')) {
    lastCheckAtStr = lastCheckAtStr + 'Z'  // ❌ 删除这行
  }

  // ...
}

// ✅ 简化为：
const checkAndAutoRefresh = async () => {
  // ...

  // 直接解析后端返回的时间（已包含时区信息）
  const lastCheckDate = new Date(resource.lastCheckAt)
  const lastCheckTime = lastCheckDate.getTime()

  // ...
}
```

---

## 三、数据库迁移

### PostgreSQL 迁移

```sql
-- 修改列类型为 TIMESTAMP WITH TIME ZONE
ALTER TABLE users
  ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE,
  ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE,
  ALTER COLUMN last_login_at TYPE TIMESTAMP WITH TIME ZONE;

ALTER TABLE pt_sites
  ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE,
  ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE,
  ALTER COLUMN health_check_at TYPE TIMESTAMP WITH TIME ZONE;

ALTER TABLE pt_resources
  ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE,
  ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE,
  ALTER COLUMN last_check_at TYPE TIMESTAMP WITH TIME ZONE,
  ALTER COLUMN published_at TYPE TIMESTAMP WITH TIME ZONE;

-- 其他表类似...
```

**注意**：已有数据会被假定为 UTC，迁移后会自动转换。如果当前数据已经是北京时间，需要先转换：

```sql
-- 如果已有数据是北京时间（naive），需要先添加时区信息
UPDATE pt_resources
SET published_at = published_at AT TIME ZONE 'Asia/Shanghai';
```

### SQLite 迁移

SQLite 无需迁移，只需确保新代码使用 `DateTime(timezone=True)`。

---

## 四、实施清单

### 后端任务

- [ ] **步骤 1**：确认 `config.py` 中 `TIMEZONE` 配置
- [ ] **步骤 2**：创建 `backend/app/utils/timezone.py`
- [ ] **步骤 3**：更新 `backend/app/models/base.py`
- [ ] **步骤 4**：批量替换 `datetime.utcnow()` → `now()`（13个文件）
  - [ ] `app/models/user.py`
  - [ ] `app/services/user/user_service.py`
  - [ ] `app/services/pt_site_service.py`
  - [ ] `app/services/pt_resource_service.py`
  - [ ] `app/services/resource_identify_service.py`
  - [ ] `app/services/scheduler_manager.py`
  - [ ] 其他文件...
- [ ] **步骤 5**：更新 `backend/app/adapters/pt_sites/mteam.py`
- [ ] **步骤 6**：创建 `backend/app/schemas/base.py`
- [ ] **步骤 6.1**：所有 Response Schema 继承 `BaseResponseSchema`
- [ ] **数据库迁移**：执行 PostgreSQL/SQLite 迁移（可选）

### 前端任务

- [ ] **步骤 7**：更新 `frontend/src/utils/format.ts`
- [ ] **步骤 8**：移除 `MovieDetail.vue` 中的临时 'Z' 后缀处理

### 测试任务

- [ ] 后端单元测试：验证 `timezone.now()` 返回正确时区
- [ ] API 测试：验证响应包含时区信息（`+08:00`）
- [ ] 前端测试：验证时间显示正确
- [ ] 端到端测试：PT资源同步 → 时间正确显示

---

## 五、测试验证

### 后端测试

```python
# 在 Python console 中测试
from app.utils.timezone import now, parse_pt_site_time, to_system_tz
from datetime import datetime, timezone as dt_timezone

# 测试 1：now() 返回系统时区时间
current_time = now()
print(current_time)  # 应输出：2025-11-22 18:30:00+08:00
print(current_time.tzinfo)  # 应输出：<DstTzInfo 'Asia/Shanghai' CST+8:00:00 STD>

# 测试 2：解析 PT 站点时间
pt_time = parse_pt_site_time("2025-11-22 18:30:00")
print(pt_time)  # 应输出：2025-11-22 18:30:00+08:00

# 测试 3：UTC 转系统时区
utc_time = datetime(2025, 11, 22, 10, 30, tzinfo=dt_timezone.utc)
beijing_time = to_system_tz(utc_time)
print(beijing_time)  # 应输出：2025-11-22 18:30:00+08:00
```

### API 测试

```bash
# 测试电影详情 API
curl http://localhost:8000/api/v1/unified/movies/19 | jq '.createdAt'
# 应输出："2025-11-22T18:30:00+08:00"

# 测试 PT 资源列表 API
curl http://localhost:8000/api/v1/pt-resources?page=1 | jq '.items[0].publishedAt'
# 应输出："2025-11-22T18:30:00+08:00"
```

### 前端测试

```javascript
// 在浏览器 console 中测试
const dateStr = "2025-11-22T18:30:00+08:00"
const date = new Date(dateStr)
console.log(date.toISOString())  // 应输出：2025-11-22T10:30:00.000Z（UTC时间）
console.log(formatDateTime(dateStr))  // 应输出：2025-11-22 18:30:00
```

---

## 六、常见问题

### Q1：如果需要切换到其他时区（如 Asia/Tokyo），如何操作？

**A**：只需修改配置文件：

```python
# backend/app/core/config.py
TIMEZONE: str = Field(default="Asia/Tokyo", description="系统时区")
```

重启应用后，所有新数据将使用新时区。

### Q2：已有数据如何处理？

**A**：
- **PostgreSQL**：执行迁移脚本，将 naive datetime 转换为时区感知
- **SQLite**：无需迁移，新代码会自动处理

### Q3：前端用户在不同时区（如美国）访问，时间会显示错误吗？

**A**：
- 当前方案下，所有用户看到的都是 **系统配置的时区时间**（如北京时间）
- 如果需要根据用户浏览器时区显示，需要改用完整的 UTC 方案

### Q4：与完整 UTC 方案相比，有哪些限制？

**A**：
- ❌ 不支持多时区用户（所有用户看到相同时区）
- ❌ 迁移到 UTC 需要数据库迁移
- ✅ 但对于单一时区用户群体，这些限制可接受

---

## 七、总结

### 核心改动

1. ✅ **统一时间函数**：`app.utils.timezone.now()` 替代 `datetime.utcnow()`
2. ✅ **PT 站点时间解析**：`parse_pt_site_time()` 直接解析为系统时区
3. ✅ **Pydantic 序列化**：输出 ISO 8601 格式（带时区偏移）
4. ✅ **前端无需转换**：直接显示后端返回的时间

### 优势

- 🚀 **实现简单**：约 2-3 天完成（vs 完整方案 5-9 天）
- 📦 **无额外依赖**：前端无需 Day.js
- 🎯 **符合业务**：适合单一时区用户群体

### 风险

- ⚠️ **扩展性受限**：未来支持多时区需要重构
- ⚠️ **非标准方案**：违反业界最佳实践（UTC 存储）

### 建议

对于 **仅中国用户 + PT 站点使用北京时间** 的场景，这个简化方案是最优选择。

---

**文档维护者**: Claude Code
**最后更新**: 2025-11-22
**版本**: v1.0
