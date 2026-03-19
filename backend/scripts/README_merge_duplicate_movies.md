# 合并重复电影记录脚本

## 问题背景

在资源识别过程中，同一部电影可能通过 TMDB 和豆瓣分别识别，导致在 `unified_movies` 表中创建了多条记录：

- **记录A**：只有 `tmdb_id`，缺少 `douban_id`
- **记录B**：只有 `douban_id`，缺少 `tmdb_id`

这违反了系统的"资源去重"设计原则。

## 脚本功能

`merge_duplicate_movies.py` 脚本会：

1. **查找重复记录**：按 `(title, year)` 分组，找到所有重复的电影
2. **合并元数据**：将重复记录的元数据合并到主记录
3. **更新映射关系**：将 `resource_mappings` 中的关联指向主记录
4. **删除重复记录**：删除多余的记录

### 合并策略

**优先级规则**：
1. **优先选择有 `tmdb_id` 的记录作为主记录**
2. 如果都没有 `tmdb_id`，选择有 `douban_id` 的记录
3. 如果都没有外部ID，选择 ID 最小的记录

**字段合并规则**：
- **外部ID**：补充主记录缺失的 `douban_id`、`imdb_id`
- **评分**：主记录为空时，使用其他记录的值
- **文本字段**：主记录为空时，使用其他记录的值（如 `overview`、`original_title`）
- **数组字段**：
  - 主记录为空：使用其他记录的值
  - 主记录非空：合并去重（如 `genres`、`actors`、`directors`）
  - **特殊处理**：`languages` 和 `countries` 会自动标准化并去重
    - 例如：`['English', '英语']` → `['英语']`
    - 例如：`['United States of America', '美国']` → `['美国']`
- **PT资源统计**：取最大值（如 `best_seeder_count`、`pt_resource_count`）
- **布尔标志**：任一为 `True` 则为 `True`（如 `has_free_resource`）

### 保留规则

**优先保留有 TMDB ID 的记录**（TMDB 作为主要元数据源），删除其他重复记录。

## 使用方法

### 1. 预览模式（推荐先运行）

```bash
cd backend
venv/Scripts/python.exe scripts/merge_duplicate_movies.py --dry-run --verbose
```

**参数说明**：
- `--dry-run`：只分析不执行，预览将要合并的记录
- `--verbose`：显示详细日志，包括每个字段的合并情况

**输出示例**：
```
[INFO] 发现 30 组重复记录

合并: 8号出口 (2025) - 2 条记录
[INFO]   主记录: UnifiedMovie(id=550, tmdb_id=1408208, douban_id=None, imdb_id=None)
[INFO]   重复记录: UnifiedMovie(id=349, tmdb_id=None, douban_id=37178027, imdb_id=None)
[INFO]   合并元数据: 2 个字段
[DEBUG]     douban_id: 37178027
[DEBUG]     rating_douban: 7.5
[INFO]   更新映射 ResourceMapping(id=205, pt_resource_id=14425) 从 unified_resource_id=349 → 550
[INFO]   删除重复记录 UnifiedMovie(id=349)

============================================================
【预览模式 - 未执行实际操作】
合并组数: 30
删除记录: 30
更新映射: 5
============================================================
```

### 2. 执行合并

确认预览结果无误后，去掉 `--dry-run` 参数执行实际合并：

```bash
cd backend
venv/Scripts/python.exe scripts/merge_duplicate_movies.py --verbose
```

**注意**：
- ✅ 执行前建议**备份数据库**
- ✅ 操作不可逆，请确认预览结果后再执行
- ✅ 脚本会自动处理 `resource_mappings` 表的更新

### 3. 静默执行（无详细日志）

```bash
cd backend
venv/Scripts/python.exe scripts/merge_duplicate_movies.py
```

只输出统计信息，不显示详细日志。

## 输出说明

执行完成后会显示统计信息：

```
============================================================
【合并完成】
合并组数: 30      # 处理了多少组重复记录
删除记录: 30      # 删除了多少条重复记录
更新映射: 5       # 更新了多少条 resource_mappings 关联
============================================================
```

## 合并示例

### 示例1：合并外部ID（优先保留 TMDB 记录）

**合并前**：
| id  | title | year | tmdb_id | douban_id | imdb_id |
|-----|-------|------|---------|-----------|---------|
| 349 | 8号出口 | 2025 | NULL    | 37178027  | NULL    |
| 550 | 8号出口 | 2025 | 1408208 | NULL      | NULL    |

**合并后**：
| id  | title | year | tmdb_id | douban_id | imdb_id |
|-----|-------|------|---------|-----------|---------|
| 550 | 8号出口 | 2025 | 1408208 | 37178027  | NULL    |

💡 **说明**：保留了 ID=550（有 tmdb_id）作为主记录，将 ID=349 的 douban_id 补充到主记录，然后删除 ID=349。

### 示例2：合并元数据（主记录空字段使用 douban 数据覆盖）

**合并前**：
- **记录A（TMDB）**：
  - `id=550`
  - `tmdb_id=1408208`
  - `rating_tmdb=6.1`
  - `overview="本片的背景是2023年发售..."`
  - `backdrop_url="https://..."`
  - `rating_douban=NULL`
  - `genres=["悬疑", "惊悚"]`

- **记录B（豆瓣）**：
  - `id=349`
  - `douban_id=37178027`
  - `rating_douban=7.5`
  - `overview=NULL`
  - `genres=["悬疑", "惊悚", "恐怖"]`

**合并后**：
- **记录A（保留）**：
  - `id=550`
  - `tmdb_id=1408208`
  - `douban_id=37178027` ✅ 补充了豆瓣ID
  - `rating_tmdb=6.1`
  - `rating_douban=7.5` ✅ 补充了豆瓣评分
  - `overview="本片的背景是2023年发售..."` （保留TMDB的描述）
  - `backdrop_url="https://..."`
  - `genres=["悬疑", "惊悚", "恐怖"]` ✅ 合并了genres

### 示例3：语言和国家/地区标准化去重

**合并前**：
- **记录A（TMDB）**：
  - `languages=["English"]`
  - `countries=["United States of America"]`

- **记录B（豆瓣）**：
  - `languages=["英语"]`
  - `countries=["美国"]`

**合并后**：
```
languages: ['英语']  # ✅ 自动标准化并去重
countries: ['美国']  # ✅ 自动标准化并去重
```

💡 **说明**：使用 `MetadataNormalizer` 自动将英文转换为中文并去重，避免出现 `['English', '英语']` 这样的重复数据。

### 示例4：更新映射关系

**合并前**：
```
resource_mappings:
  - id=205, pt_resource_id=14425, unified_resource_id=349  # 指向豆瓣记录

unified_movies:
  - id=550 (TMDB记录，主记录)
  - id=349 (豆瓣记录，重复记录)
```

**合并后**：
```
resource_mappings:
  - id=205, pt_resource_id=14425, unified_resource_id=550  # ✅ 已更新，指向TMDB主记录

unified_movies:
  - id=550 (主记录，已合并349的豆瓣元数据)
  # id=349 已删除
```

## 常见问题

### Q: 如何判断哪条记录是主记录？
A: **优先保留有 `tmdb_id` 的记录**作为主记录。如果都没有 `tmdb_id`，则保留有 `douban_id` 的记录。如果都没有外部ID，则保留 ID 最小的记录。

### Q: 脚本会删除哪些数据？
A: 只删除 `unified_movies` 表中的重复记录，不会删除 `pt_resources` 或 `resource_mappings` 数据。映射关系会自动更新指向主记录。

### Q: 如果外部ID冲突怎么办？
A: 脚本会自动检测并处理外部ID冲突：
- **场景**：电影A准备更新 `douban_id=123`，但数据库中电影B已占用此ID
- **处理**：自动清除电影B的 `douban_id`（设为 `NULL`）
- **日志**：显示警告 `⚠️ 清除冲突: UnifiedMovie(id=..., title="...") 的 douban_id=123（与主记录冲突）`
- **原因**：通常是因为存在三条或更多记录指向同一部电影，但标题有微小差异

### Q: 执行失败怎么办？
A: 脚本具有**自动错误恢复机制**：
- **遇到错误时自动跳过**：某个合并组失败时，自动回滚该组的操作并继续处理后续记录
- **错误日志**：显示 `❌ 合并失败: ...` 和详细错误信息
- **统计信息**：最后显示 `失败记录: N ⚠️`
- **手动处理**：失败的记录可以手动检查和处理

如果需要调试：
1. 使用 `--verbose` 参数查看详细日志
2. 检查数据库中失败记录的具体情况
3. 必要时恢复数据库备份

### Q: 如何验证合并结果？
A: 执行以下SQL查询，检查是否还有重复记录：

```sql
SELECT title, year, COUNT(1) as count
FROM unified_movies
GROUP BY title, year
HAVING COUNT(1) > 1;
```

如果返回空结果，说明已无重复记录。

### Q: 为什么有些记录有 resource_mappings 关联，有些没有？
A:
- **有关联**：说明该电影有对应的PT资源
- **无关联**：可能是从榜单同步的电影，或者PT资源已被删除

### Q: 脚本会影响前端显示吗？
A:
- ✅ 合并后，原本分散的PT资源会统一显示在同一个电影下
- ✅ 元数据更完整（同时包含TMDB和豆瓣的信息）
- ✅ 统计数据更准确（`pt_resource_count`、`has_free_resource` 等）

## 技术细节

### 数据库事务

脚本使用数据库事务确保数据一致性：

1. 更新主记录元数据 → `commit()`
2. 更新 `resource_mappings` → `commit()`
3. 删除重复记录 → `commit()`

如果任一步骤失败，会自动回滚。

### 并发安全

脚本**不支持并发运行**，请确保：
- ✅ 只运行一个脚本实例
- ✅ 执行期间不要进行PT资源同步或识别操作

### 性能

- 处理速度：约 **100组/秒**（取决于数据量和硬件）
- 内存占用：约 **50MB**（处理1000组重复记录）

## 后续优化建议

### 1. 防止新的重复记录产生

修改 `UnifiedMovieService.find_or_create()` 方法：

```python
async def find_or_create(...):
    # 1. 先通过外部ID查找
    existing = await find_by_external_ids(db, tmdb_id, douban_id, imdb_id)
    if existing:
        return existing, False

    # 2. 如果只有 tmdb_id，尝试获取 douban_id
    if tmdb_id and not douban_id:
        douban_id = await fetch_douban_id_from_tmdb(tmdb_id)

    # 3. 如果只有 douban_id，尝试获取 tmdb_id
    if douban_id and not tmdb_id:
        tmdb_id = await fetch_tmdb_id_from_douban(douban_id)

    # 4. 再次查找（使用完整的ID）
    existing = await find_by_external_ids(db, tmdb_id, douban_id, imdb_id)
    if existing:
        return existing, False

    # 5. 创建新记录
    return await create_movie(db, metadata)
```

### 2. 定期运行脚本

添加定时任务，每周自动运行一次去重脚本：

```python
# app/tasks/handlers/movie_dedup_handler.py
class MovieDedupHandler(BaseTaskHandler):
    @staticmethod
    async def execute(db: AsyncSession, params: dict, execution_id: int):
        merger = MovieMerger(dry_run=False, verbose=False)
        await merger.run()
        return {"merged_count": merger.merged_count}
```

## 维护者

- 脚本位置：`backend/scripts/merge_duplicate_movies.py`
- 最后更新：2025-01-17
- 维护者：Claude Code

## 相关文档

- [数据库设计](../docs/database/README.md)
- [任务处理器架构](../docs/task_handler_architecture.md)
- [CLAUDE.md 项目指南](../../CLAUDE.md)
