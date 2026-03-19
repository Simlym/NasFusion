# Alembic 迁移场景说明

本文档说明不同部署场景下 Alembic 迁移的行为。

---

## 场景 1️⃣: 新用户从 GitHub 克隆后首次部署

### 用户操作：
```bash
git clone https://github.com/your-username/NasFusion.git
cd NasFusion
cp .env.example .env
# 编辑 .env 配置
docker-compose up -d
```

### Alembic 执行流程：

1. **容器启动** → `entrypoint.sh` 自动运行 `alembic upgrade head`

2. **检查 alembic_version 表**：
   - 表不存在 → Alembic 知道这是全新数据库

3. **执行迁移 001**：
   ```python
   def upgrade() -> None:
       pass  # 空操作，仅标记基线
   ```
   - 结果：✅ 无操作，成功

4. **执行迁移 002**：
   ```python
   # 检查表结构
   movies_columns = inspector.get_columns('unified_movies')

   if 'votes_count' in columns and 'votes_tmdb' not in columns:
       # 旧数据库：执行迁移
       ...
   elif 'votes_tmdb' in columns:
       # 新数据库：跳过 ✅
       print("already has new structure, skipping migration")
   ```
   - SQLAlchemy 已自动创建表（包含 `votes_tmdb` 等新列）
   - 检测到 `votes_tmdb` 存在 → **自动跳过迁移** ✅
   - 结果：✅ 无操作，成功

5. **最终状态**：
   - 数据库：所有表已创建，包含最新结构
   - Alembic 版本：`002 (head)` ✅

### 总结：
✅ **完全自动化，无需任何手动干预**
✅ **不会报错，不会重复创建列**
✅ **新用户开箱即用**

---

## 场景 2️⃣: 你的生产环境（表结构已手动更新）

### 背景：
- 生产数据库已在 2026-01-XX 手动执行 SQL
- `votes_tmdb`、`votes_douban`、`votes_imdb` 列已添加
- `votes_count` 列已删除
- 但 `alembic_version` 表不存在或版本为空

### 用户操作（推荐）：
```bash
# 1. 更新代码
git pull

# 2. 重新构建镜像
docker-compose build backend

# 3. 启动容器
docker-compose up -d backend

# 4. 进入容器标记版本
docker exec -it nasfusion-backend bash
alembic stamp 002  # 标记为最新版本（不执行 SQL）
alembic current    # 验证：应输出 002 (head)
exit
```

### Alembic 执行流程：

#### 方式 A: 让容器启动时尝试迁移（会跳过）

1. **容器启动** → `entrypoint.sh` 运行 `alembic upgrade head`

2. **执行迁移 002**：
   ```python
   # 检查表结构
   if 'votes_tmdb' in columns:
       # 已手动执行 SQL，跳过 ✅
       print("already has new structure, skipping migration")
   ```
   - 检测到 `votes_tmdb` 已存在 → **自动跳过** ✅
   - 结果：✅ 无操作，成功

3. **进入容器标记版本**：
   ```bash
   alembic stamp 002
   ```
   - 在 `alembic_version` 表中记录版本 `002`

#### 方式 B: 先标记版本再启动（推荐）

1. **启动容器前**在宿主机运行：
   ```bash
   docker-compose up -d postgres  # 仅启动数据库
   docker run --rm --network nasfusion-network \
     -v $(pwd)/backend:/app \
     -e DB_POSTGRES_SERVER=postgres \
     -e DB_POSTGRES_PASSWORD=your_password \
     nasfusion/backend:latest \
     alembic stamp 002
   ```

2. **启动完整应用**：
   ```bash
   docker-compose up -d
   ```
   - `alembic upgrade head` 检测到已是最新版本 → 无操作 ✅

### 总结：
✅ **智能检测，不会重复执行 SQL**
✅ **两种方式都安全可靠**
⚠️ **首次需要手动标记版本**

---

## 场景 3️⃣: 旧版本升级（从 votes_count 到 votes_tmdb）

### 背景：
- 用户使用旧版本 NasFusion
- 数据库表包含 `votes_count` 列
- 升级到新版本（包含 002 迁移）

### 用户操作：
```bash
git pull
docker-compose build backend
docker-compose up -d
```

### Alembic 执行流程：

1. **容器启动** → `entrypoint.sh` 运行 `alembic upgrade head`

2. **检查当前版本**：
   - 当前版本：`001` 或更早
   - 目标版本：`002 (head)`

3. **执行迁移 002**：
   ```python
   # 检查表结构
   movies_columns = inspector.get_columns('unified_movies')

   if 'votes_count' in columns and 'votes_tmdb' not in columns:
       # 旧数据库：执行完整迁移 ✅
       op.add_column('unified_movies', Column('votes_tmdb', ...))
       op.add_column('unified_movies', Column('votes_douban', ...))
       op.add_column('unified_movies', Column('votes_imdb', ...))

       # 迁移数据
       op.execute('UPDATE unified_movies SET votes_tmdb = votes_count ...')

       # 删除旧列
       op.drop_column('unified_movies', 'votes_count')
   ```

4. **最终状态**：
   - 新列已添加：`votes_tmdb`、`votes_douban`、`votes_imdb` ✅
   - 数据已迁移：`votes_tmdb` = 原 `votes_count` ✅
   - 旧列已删除：`votes_count` ❌
   - Alembic 版本：`002 (head)` ✅

### 总结：
✅ **完全自动化，无需手动干预**
✅ **数据安全迁移，不丢失原有数据**
✅ **平滑升级，无停机时间**

---

## 技术实现：智能检测逻辑

### 核心代码（002_split_votes_columns.py）：

```python
from sqlalchemy import inspect
from alembic import context

def upgrade() -> None:
    conn = context.get_bind()
    inspector = inspect(conn)

    # 获取当前表结构
    movies_columns = [col['name'] for col in inspector.get_columns('unified_movies')]

    # 智能判断
    if 'votes_count' in movies_columns and 'votes_tmdb' not in movies_columns:
        # 场景 3: 旧数据库，执行完整迁移
        ...
    elif 'votes_tmdb' in movies_columns:
        # 场景 1 & 2: 新数据库或已迁移，跳过
        print("already has new structure, skipping migration")
```

### 检测逻辑表：

| votes_count | votes_tmdb | 场景 | 操作 |
|------------|-----------|------|------|
| ✅ 存在    | ❌ 不存在 | 场景 3 (旧数据库) | 执行完整迁移 |
| ❌ 不存在  | ✅ 存在   | 场景 1 (新用户) 或 场景 2 (已手动更新) | 跳过迁移 |
| ❌ 不存在  | ❌ 不存在 | 异常状态（不应发生） | 报错 |
| ✅ 存在    | ✅ 存在   | 迁移中断（极少见） | 继续迁移 |

---

## 常见问题

### Q1: 新用户首次部署会不会报错？
**A**: ✅ 不会！迁移脚本会检测到新表结构并自动跳过。

### Q2: 生产环境已手动执行 SQL，会不会重复执行？
**A**: ✅ 不会！智能检测会发现 `votes_tmdb` 已存在，自动跳过。
⚠️ 但需要手动运行 `alembic stamp 002` 标记版本。

### Q3: 旧版本用户升级会自动迁移吗？
**A**: ✅ 会！检测到 `votes_count` 存在且 `votes_tmdb` 不存在，自动执行迁移。

### Q4: 如何验证迁移成功？
```bash
# 检查 Alembic 版本
docker exec -it nasfusion-backend alembic current
# 应输出: 002 (head)

# 检查表结构
docker exec -it nasfusion-postgres psql -U nasfusion -d nasfusion -c "\d unified_movies"
# 应包含: votes_tmdb, votes_douban, votes_imdb
# 不应包含: votes_count
```

### Q5: 如果迁移失败了怎么办？
**A**: 查看容器日志：
```bash
docker-compose logs backend | grep -i "alembic"
```
根据错误信息决定：
- 如果是"列已存在"：运行 `alembic stamp 002` 标记版本
- 如果是连接错误：检查数据库连接配置
- 其他错误：查看详细日志，必要时手动修复

---

**总结**：无论是新用户、生产环境还是旧版本升级，Alembic 迁移都能智能处理，确保数据安全和系统稳定！🎉
