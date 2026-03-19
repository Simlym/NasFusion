# PT资源Detail接口使用策略

## 问题分析

PT站点提供三种API接口：

### 1. Search API（搜索接口）
- **一次请求返回多个资源**（通常50-100个）
- 包含基础信息：标题、大小、做种数、促销信息等
- **适合列表展示和初始同步**

### 2. Detail API（详情接口）
- **一次请求只能获取一个资源的详情**
- 包含种子相关信息：评分、完整描述、MediaInfo、图片等
- **请求量大，容易触发限流**

### 3. Douban API（豆瓣信息接口）⭐ NEW
- **一次请求只能获取一个资源的豆瓣信息**
- 包含影视内容信息：导演、演员、类型、剧情简介
- 提供格式化的BB代码描述（可用于NFO）
- **需要豆瓣ID，与Detail API互补**

## 请求量对比

| 场景 | Search API | Detail API | 总请求数 |
|------|------------|------------|----------|
| 同步1000个资源（仅搜索） | 20次 | 0次 | **20次** ✅ |
| 同步1000个资源（含详情） | 20次 | 1000次 | **1020次** ❌ |
| 按2秒间隔计算耗时 | 40秒 | 33分钟 | **34分钟** |

**结论**：全量同步时调用detail接口**不可行**。

---

## 推荐方案：分层获取策略

### 📊 数据分层

```
┌─────────────────────────────────────┐
│ Level 1: 基础信息 (Search API)      │  ← 全量同步
│ - 标题、大小、做种数                │
│ - 促销信息、分类                    │
│ - IMDB/豆瓣ID（无评分）             │
├─────────────────────────────────────┤
│ Level 2: 详细信息 (Detail API)      │  ← 按需获取
│ - IMDB/豆瓣评分                     │
│ - 完整描述（BB代码）                │
│ - MediaInfo                         │
│ - 原始文件名、图片列表              │
└─────────────────────────────────────┘
```

### 🎯 获取策略

#### 1. 同步阶段（自动）
```bash
POST /api/v1/pt-resources/sites/1/sync
{
  "sync_type": "manual",
  "max_pages": 10
}
```
- ✅ 只调用 **Search API**
- ✅ 快速同步大量资源
- ✅ 满足列表展示需求

#### 2. 查看详情阶段（按需）
```bash
POST /api/v1/pt-resources/{resource_id}/fetch-detail
```
- ✅ 用户点击查看详情时才调用
- ✅ 调用一次 **Detail API**
- ✅ 结果缓存到数据库（`detail_fetched=true`）
- ✅ 再次查看直接返回缓存

---

## 数据库设计

### PTResource 模型字段

```python
class PTResource(BaseModel):
    # Search API 提供的基础字段
    title = Column(String(1000))
    size_bytes = Column(BigInteger)
    seeders = Column(Integer)
    is_free = Column(Boolean)
    imdb_id = Column(String(20))      # 有ID
    douban_id = Column(String(20))     # 有ID

    # Detail API 额外提供的字段
    imdb_rating = Column(DECIMAL(3, 1))      # 评分 ⭐
    douban_rating = Column(DECIMAL(3, 1))    # 评分 ⭐
    description = Column(Text)                # 完整描述
    mediainfo = Column(Text)                  # MediaInfo
    origin_file_name = Column(String(500))    # 原始文件名
    image_list = Column(JSON)                 # 图片列表

    # 状态标记
    detail_fetched = Column(Boolean, default=False)  # 是否已获取详情
    detail_fetched_at = Column(DateTime)             # 获取时间
    raw_detail_json = Column(JSON)                   # 原始数据
```

---

## API使用示例

### 示例 1：全量同步（不获取detail）

```bash
# 同步前10页资源
POST /api/v1/pt-resources/sites/1/sync
{
  "sync_type": "manual",
  "max_pages": 10
}

# 响应
{
  "sync_log_id": 123,
  "message": "同步完成",
  "status": "success"
}

# 结果：500个资源，只调用10次search API
```

### 示例 2：按需获取详情

```bash
# 用户在前端点击查看资源详情
POST /api/v1/pt-resources/1001/fetch-detail

# 首次调用：
# - 调用 Detail API
# - 更新数据库
# - 返回完整信息

# 再次调用：
# - 直接返回缓存（detail_fetched=true）
# - 不调用 Detail API
```

### 示例 3：前端实现

```javascript
// 资源列表页 - 只显示基础信息
async function fetchResourceList() {
  const response = await fetch('/api/v1/pt-resources?page=1&page_size=50');
  const data = await response.json();

  // 显示：标题、大小、做种数、是否免费
  // 不显示：评分、完整描述、MediaInfo
}

// 资源详情页 - 按需加载详情
async function showResourceDetail(resourceId) {
  // 先获取基础信息（已缓存）
  const basic = await fetch(`/api/v1/pt-resources/${resourceId}`);

  // 显示基础信息（立即展示）
  renderBasicInfo(basic);

  // 检查是否需要获取详情
  if (!basic.detail_fetched) {
    // 显示"加载中..."
    showLoading();

    // 异步获取详情
    const detail = await fetch(`/api/v1/pt-resources/${resourceId}/fetch-detail`, {
      method: 'POST'
    });

    // 显示详细信息（评分、描述、MediaInfo）
    renderDetailInfo(detail);
  } else {
    // 直接显示已缓存的详情
    renderDetailInfo(basic);
  }
}
```

---

## 高级策略（可选实现）

### 策略 1：智能预加载

仅对**热门资源**预加载详情：

```python
# 定时任务：每天预加载热门资源的详情
async def preload_popular_resources():
    # 条件：做种数 > 100 且 is_free = true
    popular = await db.execute(
        select(PTResource)
        .where(
            PTResource.seeders > 100,
            PTResource.is_free == True,
            PTResource.detail_fetched == False
        )
        .limit(50)  # 每天最多50个
    )

    for resource in popular:
        await PTResourceService.fetch_resource_detail(db, resource.id)
        await asyncio.sleep(5)  # 间隔5秒
```

### 策略 2：批量获取优化

对用户收藏的资源批量获取详情：

```python
@router.post("/batch-fetch-details")
async def batch_fetch_details(
    resource_ids: List[int],
    db: AsyncSession = Depends(get_db),
):
    """
    批量获取资源详情

    限制：
    - 一次最多20个
    - 自动限流（每次间隔3秒）
    """
    if len(resource_ids) > 20:
        raise HTTPException(400, "一次最多获取20个资源详情")

    results = []
    for resource_id in resource_ids:
        try:
            resource = await PTResourceService.fetch_resource_detail(db, resource_id)
            results.append(resource)
            await asyncio.sleep(3)  # 避免触发限流
        except Exception as e:
            logger.error(f"Failed to fetch detail for {resource_id}: {e}")

    return results
```

### 策略 3：优先级队列

使用Redis队列管理detail获取：

```python
# 高优先级：用户主动请求
# 中优先级：热门资源预加载
# 低优先级：全量补齐（慢慢爬）

class DetailFetchPriority:
    HIGH = 1    # 用户点击，立即获取
    MEDIUM = 2  # 热门资源，定时获取
    LOW = 3     # 后台补齐，慢慢获取
```

---

## 最佳实践总结

### ✅ 推荐做法

1. **同步时只用Search API** - 快速建立资源库
2. **按需获取Detail** - 用户真正需要时才调用
3. **缓存机制** - 获取一次，永久缓存
4. **尊重限流** - 间隔合理，避免封禁
5. **智能预加载**（可选）- 只预加载热门资源

### ❌ 避免做法

1. ❌ 全量同步时调用detail
2. ❌ 定时全量刷新detail
3. ❌ 无缓存重复获取
4. ❌ 高频批量调用
5. ❌ 不遵守速率限制

---

## 性能对比

| 方案 | 请求数（1000资源） | 耗时 | 可行性 |
|------|-------------------|------|--------|
| ❌ 全量同步+Detail | 1020次 | 34分钟 | 不可行 |
| ✅ 同步+按需Detail | 20次 + N次 | 40秒 + 按需 | **推荐** |
| ⭐ 同步+智能预加载 | 20次 + 50次/天 | 40秒 + 2.5分钟/天 | 最佳 |

---

## 故障排查

### 问题 1：获取详情时报错429（Too Many Requests）

**原因**：请求过于频繁，触发站点限流

**解决方案**：
```python
# 增加请求间隔
site.request_interval = 5  # 改为5秒

# 或使用指数退避
for retry in range(3):
    try:
        return await adapter.get_resource_detail(resource_id)
    except HTTPError as e:
        if e.status == 429:
            await asyncio.sleep(2 ** retry * 5)  # 5秒, 10秒, 20秒
        else:
            raise
```

### 问题 2：Detail数据未更新

**原因**：`detail_fetched=true` 导致不再获取

**解决方案**：
```python
# 方案1：重置标志
UPDATE pt_resources SET detail_fetched = false WHERE id = 1001;

# 方案2：添加强制刷新参数
@router.post("/{resource_id}/fetch-detail")
async def fetch_resource_detail(
    resource_id: int,
    force_refresh: bool = False,  # 强制刷新
    db: AsyncSession = Depends(get_db),
):
    if force_refresh:
        resource.detail_fetched = False
        await db.commit()

    return await PTResourceService.fetch_resource_detail(db, resource_id)
```

---

## 总结

✅ **核心原则**：**按需获取 + 缓存优先**

1. 同步阶段：只用Search API（快速）
2. 详情阶段：用户查看时才调用Detail API
3. 缓存机制：获取一次，永久使用
4. 智能预加载（可选）：只预加载热门资源

这样既能保证用户体验，又不会触发站点限流。🎯
