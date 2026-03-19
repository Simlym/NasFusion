# 投票数字段迁移脚本使用说明

## 背景

原设计中 `votes_count` 字段无法对应三个不同的评分来源（TMDB、豆瓣、IMDB），导致投票数数据混乱。

**修改内容：**
- 将 `votes_count` 拆分为 `votes_tmdb`、`votes_douban`、`votes_imdb` 三个独立字段
- 根据 `metadata_source` 字段自动迁移现有数据到对应的新字段

**影响的表：**
- `unified_movies` - 统一电影资源表
- `unified_tv_series` - 统一电视剧资源表

---

## 使用方法

### 1. 完整迁移（推荐）

执行完整的迁移流程：添加新字段 → 迁移数据 → 验证

```bash
cd backend
python scripts/migration/migrate_votes_fields.py
```

**执行步骤：**
1. 为两个表添加 `votes_tmdb`、`votes_douban`、`votes_imdb` 字段
2. 根据 `metadata_source` 迁移现有 `votes_count` 数据：
   - `metadata_source = 'tmdb'` → 数据复制到 `votes_tmdb`
   - `metadata_source = 'douban'` → 数据复制到 `votes_douban`
   - 无 `metadata_source` 的记录默认迁移到 `votes_tmdb`
3. 验证迁移结果

### 2. 删除旧字段

⚠️ **警告：此操作不可逆！请先备份数据库！**

在完成迁移并验证数据正确后，删除旧的 `votes_count` 字段：

```bash
python scripts/migration/migrate_votes_fields.py --drop-old-fields
```

**注意事项：**
- **PostgreSQL**: 可以直接删除列
- **SQLite**: 不支持直接删除列，需要手动重建表或等待下次完整迁移

### 3. 仅验证结果

不执行迁移，仅查看当前字段状态和数据统计：

```bash
python scripts/migration/migrate_votes_fields.py --verify-only
```

---

## 迁移流程示例

### 完整迁移流程

```bash
# 步骤1: 备份数据库
cp data/nasfusion.db data/nasfusion.db.backup

# 步骤2: 执行迁移
python scripts/migration/migrate_votes_fields.py

# 输出示例：
# ============================================================
# 投票数字段迁移脚本
# ============================================================
#
# 变更:
#   votes_count → votes_tmdb / votes_douban / votes_imdb
#
# 影响表:
#   - unified_movies
#   - unified_tv_series
# ============================================================
#
# 步骤 1/3: 添加新字段
# ------------------------------------------------------------
# 检测到数据库类型: SQLITE
#
# [unified_movies] 检查字段...
#   [+] 添加字段: votes_tmdb
#   [+] 添加字段: votes_douban
#   [+] 添加字段: votes_imdb
#   [OK] unified_movies 字段添加完成
# [unified_tv_series] 检查字段...
#   [+] 添加字段: votes_tmdb
#   [+] 添加字段: votes_douban
#   [+] 添加字段: votes_imdb
#   [OK] unified_tv_series 字段添加完成
#
# ✅ 所有新字段添加完成！
#
# 步骤 2/3: 迁移现有数据
# ------------------------------------------------------------
#
# [unified_movies] 开始迁移数据...
#   找到 150 条记录需要迁移
#   [OK] 迁移 TMDB 数据: 120 条
#   [OK] 迁移豆瓣数据: 30 条
#   [✓] unified_movies 数据迁移完成！
#
# [unified_tv_series] 开始迁移数据...
#   找到 80 条记录需要迁移
#   [OK] 迁移 TMDB 数据: 70 条
#   [OK] 迁移豆瓣数据: 10 条
#   [✓] unified_tv_series 数据迁移完成！
#
# 步骤 3/3: 验证迁移结果
# ------------------------------------------------------------
#
# ============================================================
# 验证迁移结果
# ============================================================
#
# [unified_movies]
#   总记录数: 200
#   包含 TMDB 投票数: 120
#   包含豆瓣投票数: 30
#   包含 IMDB 投票数: 0
#   [!] 仍存在 votes_count 字段
#
# [unified_tv_series]
#   总记录数: 100
#   包含 TMDB 投票数: 70
#   包含豆瓣投票数: 10
#   包含 IMDB 投票数: 0
#   [!] 仍存在 votes_count 字段
#
# ✅ 验证完成！
#
# ============================================================
# ✅ 迁移完成！
# ============================================================
#
# 下一步:
#   1. 验证数据正确性
#   2. 运行: python scripts/migration/migrate_votes_fields.py --drop-old-fields
#      （删除旧的 votes_count 字段）
# ============================================================

# 步骤3: 手动验证数据（可选）
sqlite3 data/nasfusion.db "SELECT title, metadata_source, votes_tmdb, votes_douban FROM unified_movies LIMIT 5;"

# 步骤4: 确认无误后，删除旧字段
python scripts/migration/migrate_votes_fields.py --drop-old-fields
```

---

## 常见问题

### Q1: 迁移后发现数据不对怎么办？

**A**: 恢复备份并重新执行迁移

```bash
# 恢复备份
cp data/nasfusion.db.backup data/nasfusion.db

# 重新执行迁移
python scripts/migration/migrate_votes_fields.py
```

### Q2: SQLite 如何删除旧字段？

**A**: SQLite 不支持直接删除列，有两种方案：

**方案1（推荐）**: 等待下次完整数据库迁移时自动处理

**方案2（手动）**: 使用 SQLite 工具重建表

```sql
-- 1. 创建新表（不含 votes_count）
CREATE TABLE unified_movies_new (
    id INTEGER PRIMARY KEY,
    tmdb_id INTEGER,
    -- ... 其他字段
    votes_tmdb INTEGER,
    votes_douban INTEGER,
    votes_imdb INTEGER,
    -- ... 其他字段
);

-- 2. 复制数据
INSERT INTO unified_movies_new
SELECT id, tmdb_id, ..., votes_tmdb, votes_douban, votes_imdb, ...
FROM unified_movies;

-- 3. 删除旧表
DROP TABLE unified_movies;

-- 4. 重命名新表
ALTER TABLE unified_movies_new RENAME TO unified_movies;

-- 对 unified_tv_series 重复上述步骤
```

### Q3: 迁移时报错 "column already exists"

**A**: 表示新字段已存在，可以安全跳过。脚本会自动检测并跳过已存在的字段。

### Q4: 部分数据没有 metadata_source 字段，会如何处理？

**A**: 脚本会将没有 `metadata_source` 的记录默认迁移到 `votes_tmdb`，因为 TMDB 是项目的主要元数据来源。

---

## 迁移前后对比

### 迁移前

**unified_movies 表结构：**
```
- rating_tmdb (DECIMAL)
- rating_douban (DECIMAL)
- rating_imdb (DECIMAL)
- votes_count (INTEGER)  ❌ 单一字段，无法区分来源
```

**数据示例：**
```
title: "复仇者联盟"
metadata_source: "tmdb"
rating_tmdb: 8.5
votes_count: 25000  ← 实际是 TMDB 的投票数，但字段名不明确
```

### 迁移后

**unified_movies 表结构：**
```
- rating_tmdb (DECIMAL)
- votes_tmdb (INTEGER)    ✅ TMDB 投票数
- rating_douban (DECIMAL)
- votes_douban (INTEGER)  ✅ 豆瓣投票数
- rating_imdb (DECIMAL)
- votes_imdb (INTEGER)    ✅ IMDB 投票数
```

**数据示例：**
```
title: "复仇者联盟"
metadata_source: "tmdb"
rating_tmdb: 8.5
votes_tmdb: 25000   ✅ 明确是 TMDB 投票数
votes_douban: NULL
votes_imdb: NULL
```

---

## 相关文件

- **迁移脚本**: `scripts/migration/migrate_votes_fields.py`
- **模型文件**:
  - `app/models/unified_movie.py`
  - `app/models/unified_tv_series.py`
- **Schema 文件**:
  - `app/schemas/unified_movie.py`
  - `app/schemas/unified_tv.py`
- **适配器文件**:
  - `app/adapters/metadata/tmdb_adapter.py`
  - `app/adapters/metadata/douban_adapter.py`

---

## 更新日志

### 2026-01-19
- 创建迁移脚本
- 修改所有相关代码以使用新的字段结构
- 添加完整的数据迁移和验证逻辑
