# 生产环境部署指南 - Alembic 迁移

## 背景

生产环境数据库表结构已通过手动 SQL 更新完成（votes_tmdb/votes_douban/votes_imdb 列已添加）。
现在需要将 Alembic 迁移系统同步到生产环境，但**不能重复执行迁移 SQL**。

## ✅ 好消息：迁移脚本已优化！

`002_split_votes_columns.py` 已包含**智能检测逻辑**：
- 自动检测表结构（检查是否有 `votes_count` 或 `votes_tmdb` 列）
- 旧数据库：执行完整迁移
- 新数据库或已迁移：自动跳过

**这意味着**：
- 新用户从 GitHub 克隆后首次部署 → 自动跳过迁移（SQLAlchemy 已创建新表结构）✅
- 你的生产环境（已手动执行 SQL）→ 只需标记版本即可 ✅

---

## 部署方案（二选一）

### 方案 A：推荐 - 在容器内标记版本 ✅

**优点**：保留自动迁移机制，适合长期维护

#### 步骤：

1. **正常启动容器（会尝试运行迁移，可能失败但会继续启动）**
   ```bash
   docker-compose up -d backend
   ```

2. **进入后端容器**
   ```bash
   docker exec -it nasfusion-backend bash
   ```

3. **检查当前迁移状态**
   ```bash
   alembic current
   # 如果输出为空或错误，说明 alembic_version 表还没初始化
   ```

4. **标记数据库为最新版本（不执行 SQL）**
   ```bash
   alembic stamp 002
   ```

5. **验证版本**
   ```bash
   alembic current
   # 应该输出: 002 (head)

   alembic history
   # 应该输出迁移历史
   ```

6. **重启容器（确保一切正常）**
   ```bash
   docker-compose restart backend
   ```

---

### 方案 B：临时禁用自动迁移

**优点**：最安全，适合首次部署

#### 步骤：

1. **修改 docker-compose.yml，添加环境变量禁用自动迁移**
   ```yaml
   environment:
     # ... 其他环境变量 ...
     SKIP_ALEMBIC_MIGRATION: "true"  # 添加这一行
   ```

2. **修改 backend/entrypoint.sh**
   ```bash
   # 将第97-105行修改为：
   if [ "$SKIP_ALEMBIC_MIGRATION" != "true" ] && [ -f "alembic.ini" ]; then
       echo "Running database migrations..."
       alembic upgrade head || {
           echo "WARNING: Database migration failed (continuing anyway)"
       }
   else
       echo "Skipping database migrations (SKIP_ALEMBIC_MIGRATION=$SKIP_ALEMBIC_MIGRATION)"
   fi
   ```

3. **启动容器**
   ```bash
   docker-compose up -d backend
   ```

4. **进入容器标记版本**
   ```bash
   docker exec -it nasfusion-backend bash
   alembic stamp 002
   alembic current  # 验证
   ```

5. **移除 SKIP_ALEMBIC_MIGRATION 环境变量**
   - 从 docker-compose.yml 中删除该变量
   - 重启容器

6. **验证自动迁移恢复正常**
   ```bash
   docker-compose logs -f backend
   # 应该看到 "Running database migrations..." 日志
   ```

---

## 验证迁移成功

### 1. 检查 Alembic 版本表
```sql
-- 进入 PostgreSQL
docker exec -it nasfusion-postgres psql -U nasfusion -d nasfusion

-- 查看版本
SELECT * FROM alembic_version;
-- 应该输出: version_num = '002'
```

### 2. 检查表结构
```sql
-- 检查 unified_tv_series 表
\d unified_tv_series
-- 应该包含: votes_tmdb, votes_douban, votes_imdb

-- 检查 unified_movies 表
\d unified_movies
-- 应该包含: votes_tmdb, votes_douban, votes_imdb

-- 不应该包含: votes_count
```

### 3. 检查应用启动
```bash
# 查看后端日志
docker-compose logs -f backend

# 应该看到正常启动日志，没有数据库错误
```

---

## 常见问题

### Q1: 容器启动时看到 "Database migration failed"
**A**: 正常！因为迁移已手动执行。只要后续标记版本成功，应用能正常运行即可。

### Q2: alembic current 输出为空
**A**: 说明 alembic_version 表还没初始化。运行 `alembic stamp 002` 即可。

### Q3: 应用启动报错 "no such column: votes_tmdb"
**A**: 说明手动 SQL 没有执行成功。请检查数据库表结构，重新执行迁移脚本。

### Q4: 后续如何处理新的迁移？
**A**: 标记版本后，未来的迁移会自动通过 entrypoint.sh 执行，无需手动操作。

---

## 迁移 SQL 参考（已执行）

如果需要在其他环境重新执行，参考以下 SQL：

```sql
-- unified_movies 表
ALTER TABLE unified_movies ADD COLUMN votes_tmdb INTEGER;
ALTER TABLE unified_movies ADD COLUMN votes_douban INTEGER;
ALTER TABLE unified_movies ADD COLUMN votes_imdb INTEGER;

-- 迁移数据（可选）
UPDATE unified_movies SET votes_tmdb = votes_count WHERE votes_count IS NOT NULL;

-- 删除旧列
ALTER TABLE unified_movies DROP COLUMN votes_count;

-- unified_tv_series 表
ALTER TABLE unified_tv_series ADD COLUMN votes_tmdb INTEGER;
ALTER TABLE unified_tv_series ADD COLUMN votes_douban INTEGER;
ALTER TABLE unified_tv_series ADD COLUMN votes_imdb INTEGER;

-- 迁移数据（可选）
UPDATE unified_tv_series SET votes_tmdb = votes_count WHERE votes_count IS NOT NULL;

-- 删除旧列
ALTER TABLE unified_tv_series DROP COLUMN votes_count;
```

---

## 推荐操作流程

**最简单安全的方式（方案 A）**：

```bash
# 1. 正常启动
docker-compose up -d backend

# 2. 进入容器
docker exec -it nasfusion-backend bash

# 3. 标记版本
alembic stamp 002

# 4. 验证
alembic current

# 5. 退出并查看日志
exit
docker-compose logs -f backend
```

完成！🎉
