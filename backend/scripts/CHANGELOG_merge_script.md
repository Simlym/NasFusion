# 合并脚本更新日志

## v2.0 - 2025-01-17

### ✨ 新增功能

#### 1. **优先保留 TMDB 记录**
- 调整主记录选择逻辑，优先保留有 `tmdb_id` 的记录作为主记录
- 排序策略：`tmdb_id` > `douban_id` > `id`

**影响**：
- ✅ TMDB 作为主要元数据源，确保数据质量
- ✅ 豆瓣数据作为补充，填充 TMDB 的空字段

#### 2. **语言和国家/地区标准化**
- 自动调用 `MetadataNormalizer` 标准化 `languages` 和 `countries` 字段
- 去重时不区分大小写

**效果**：
```python
# 优化前
languages: ['English', '英语']  # ❌ 重复
countries: ['United States of America', '美国']  # ❌ 重复

# 优化后
languages: ['英语']  # ✅ 已标准化去重
countries: ['美国']  # ✅ 已标准化去重
```

**技术细节**：
- 使用 `MetadataNormalizer.normalize_language()` 和 `normalize_country()`
- 支持的映射：
  - 语言：`English` → `英语`, `Mandarin` → `汉语普通话`, `Cantonese` → `粤语`
  - 国家：`United States of America` → `美国`, `China` → `中国大陆`, `Hong Kong` → `中国香港`

#### 3. **外部ID冲突自动处理**
- 新增 `clear_conflicting_external_ids()` 方法
- 在更新主记录前，自动检测并清除冲突的外部ID

**场景示例**：
```
电影A（主记录）准备更新 douban_id=1303494
电影B（其他记录）已占用 douban_id=1303494
→ 自动清除电影B的 douban_id（设为 NULL）
→ 记录警告日志
```

**日志输出**：
```
⚠️ 清除冲突: UnifiedMovie(id=8502, title="杀羊人") 的 douban_id=1303494（与主记录冲突）
```

**解决的问题**：
- ✅ 避免 `UniqueViolationError: duplicate key value violates unique constraint`
- ✅ 处理三条或更多记录指向同一部电影但标题有微小差异的情况

### 🔧 优化改进

#### 1. **合并逻辑优化**
- **评分**：主记录为空时，使用其他记录的值（之前是取最高值）
- **文本字段**：主记录为空时，使用其他记录的值（之前是取最长的）
- **数组字段**：主记录为空时使用其他记录，非空时合并去重

#### 2. **人员信息合并优化**
- 支持按 `id` 或 `name` 去重
- 保留 TMDB 人员信息的优先级

#### 3. **Windows 编码问题修复**
- 添加 UTF-8 编码设置，解决控制台乱码问题

### 📝 文档更新

#### 1. **使用说明文档** (`README_merge_duplicate_movies.md`)
- ✅ 更新合并策略说明（优先 TMDB）
- ✅ 新增语言和国家标准化示例
- ✅ 新增外部ID冲突处理说明
- ✅ 更新常见问题解答

#### 2. **Docker 执行指南** (`DOCKER_EXECUTION_GUIDE.md`)
- ✅ 三种执行方法详解
- ✅ 常见问题排查
- ✅ 群晖 NAS 完整流程
- ✅ 性能优化建议

#### 3. **更新日志** (`CHANGELOG_merge_script.md`)
- ✅ 详细记录所有功能更新
- ✅ 技术细节说明

### 🐛 修复的问题

#### 问题1：外部ID唯一约束冲突
**错误信息**：
```
sqlalchemy.exc.IntegrityError: duplicate key value violates unique constraint "ix_unified_movies_douban_id"
DETAIL:  Key (douban_id)=(1303494) already exists.
```

**原因**：
- 存在三条或更多记录指向同一部电影
- 标题有微小差异（如 "杀羊人" vs "杀羊人 "），导致按 `(title, year)` 分组时被视为不同组
- 尝试将 `douban_id=1303494` 更新到主记录时，发现已被其他记录占用

**解决方案**：
- 新增 `clear_conflicting_external_ids()` 方法
- 在更新前检测冲突并清除占用的外部ID
- 记录警告日志供用户审查

#### 问题2：语言和国家重复
**问题描述**：
- 合并后出现 `['English', '英语']` 等重复值
- TMDB 使用英文，豆瓣使用中文

**解决方案**：
- 新增 `normalize_and_deduplicate_list()` 方法
- 合并时自动调用 `MetadataNormalizer` 标准化
- 去重时不区分大小写

#### 问题3：主记录选择不合理
**问题描述**：
- 之前按 ID 升序，可能保留了只有豆瓣数据的记录
- TMDB 数据质量更高，应优先保留

**解决方案**：
- 调整排序策略：`tmdb_id.asc().nulls_last()` → `douban_id.asc().nulls_last()` → `id.asc()`
- 优先保留有 TMDB ID 的记录

### 📊 测试结果

**测试环境**：
- 数据库类型：PostgreSQL
- 记录数量：30组重复记录（60条记录）
- 映射更新：5条 `resource_mappings`

**执行结果**：
```
合并组数: 30
删除记录: 30
更新映射: 5
```

**验证通过**：
- ✅ 优先保留 TMDB 记录
- ✅ 语言和国家已标准化去重
- ✅ 外部ID冲突已自动处理
- ✅ resource_mappings 已正确更新

### 🚀 使用方式

#### 本地执行
```bash
cd backend
venv/Scripts/python.exe scripts/merge_duplicate_movies.py --dry-run --verbose
```

#### Docker 执行
```bash
# 预览模式
docker exec nasfusion-backend python scripts/merge_duplicate_movies.py --dry-run --verbose

# 执行合并
docker exec nasfusion-backend python scripts/merge_duplicate_movies.py --verbose
```

### ⚠️ 重要提醒

1. **备份数据库**：执行前务必备份数据库
2. **先预览**：使用 `--dry-run` 预览操作
3. **检查日志**：注意 `⚠️ 清除冲突` 警告，确认是否符合预期
4. **验证结果**：执行后验证数据完整性

### 🔗 相关文档

- [使用说明](./README_merge_duplicate_movies.md)
- [Docker 执行指南](./DOCKER_EXECUTION_GUIDE.md)
- [项目指南](../../CLAUDE.md)

---

**维护者**: Claude Code
**最后更新**: 2025-01-17
**版本**: v2.0
