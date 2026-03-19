# 前端任务类型修复报告

## 问题描述

前端 `Tasks.vue` 页面中使用了旧的任务类型标识符,导致创建和编辑调度任务时 `handler` 字段值不正确。

**症状**:
- 在 `http://localhost:3000/tasks?tab=scheduled` 页面
- 新增或更新调度任务时,`handler` 字段被设置为旧格式(如 `tasks.pt_sync.sync_site`)
- 导致任务执行时找不到对应的处理器

## 根本原因

前端代码中硬编码了旧的任务类型值:
- 使用 `'pt_sync'` 而不是 `'pt_resource_sync'`
- 使用 `'batch_identify'` 而不是 `'pt_resource_identify'`
- 使用 `'scan_media'` 而不是 `'media_file_scan'`

## 修复内容

### 修改文件
- ✅ `frontend/src/views/Tasks.vue` - 任务管理页面

### 具体修改

#### 1. 表单类型定义 (第 930 行)
```typescript
// ❌ 旧代码
task_type: 'pt_sync' as 'pt_sync' | 'subscription_check'

// ✅ 新代码
task_type: 'pt_resource_sync' as 'pt_resource_sync' | 'subscription_check'
```

#### 2. 表单验证规则 (第 954 行)
```typescript
// ❌ 旧代码
if (form.task_type === 'pt_sync') {

// ✅ 新代码
if (form.task_type === 'pt_resource_sync') {
```

#### 3. 对话框标题 (第 1044 行)
```typescript
// ❌ 旧代码
const taskTypeName = form.task_type === 'pt_sync' ? 'PT同步' : '订阅检查'

// ✅ 新代码
const taskTypeName = form.task_type === 'pt_resource_sync' ? 'PT同步' : '订阅检查'
```

#### 4. 任务类型颜色映射 (第 1074 行)
```typescript
// ❌ 旧代码
const colorMap = {
  'pt_sync': 'primary',
  'batch_identify': 'success',
  'scan_media': 'info'
}

// ✅ 新代码
const colorMap = {
  'pt_resource_sync': 'primary',
  'pt_resource_identify': 'success',
  'media_file_scan': 'info',
  // 旧格式兼容
  'pt_sync': 'primary',
  'batch_identify': 'success',
  'scan_media': 'info'
}
```

#### 5. 任务类型切换处理 (第 1180 行)
```typescript
// ❌ 旧代码
const handleTaskTypeChange = (taskType: 'pt_sync' | 'subscription_check') => {
  if (taskType === 'pt_sync') {

// ✅ 新代码
const handleTaskTypeChange = (taskType: 'pt_resource_sync' | 'subscription_check') => {
  if (taskType === 'pt_resource_sync') {
```

#### 6. 编辑任务表单填充 (第 1259 行)
```typescript
// ❌ 旧代码
if (task.task_type === 'pt_sync') {

// ✅ 新代码(支持新旧格式兼容)
if (task.task_type === 'pt_resource_sync' || task.task_type === 'pt_sync') {
  form.task_type = 'pt_resource_sync'  // 统一为新格式
```

#### 7. 提交表单创建任务 (第 1412 行)
```typescript
// ❌ 旧代码
if (form.task_type === 'pt_sync') {

// ✅ 新代码
if (form.task_type === 'pt_resource_sync') {
```

#### 8. 提交表单更新任务 (第 1455 行)
```typescript
// ❌ 旧代码
if (form.task_type === 'pt_sync') {

// ✅ 新代码
if (form.task_type === 'pt_resource_sync') {
```

#### 9. 表单重置 (第 1494 行)
```typescript
// ❌ 旧代码
form.task_type = 'pt_sync'

// ✅ 新代码
form.task_type = 'pt_resource_sync'
```

#### 10. 模板 - 任务类型选择器 (第 551 行)
```vue
<!-- ❌ 旧代码 -->
<el-option label="PT站点同步" value="pt_sync" />

<!-- ✅ 新代码 -->
<el-option label="PT站点同步" value="pt_resource_sync" />
```

#### 11. 模板 - 条件渲染 (第 561 行)
```vue
<!-- ❌ 旧代码 -->
<template v-if="form.task_type === 'pt_sync'">

<!-- ✅ 新代码 -->
<template v-if="form.task_type === 'pt_resource_sync'">
```

#### 12. 模板 - 历史记录过滤器 (第 314-318 行)
```vue
<!-- ❌ 旧代码 -->
<el-option label="PT同步" value="pt_sync" />
<el-option label="批量识别" value="batch_identify" />
<el-option label="订阅检查" value="subscription_check" />

<!-- ✅ 新代码 -->
<el-option label="PT同步" value="pt_resource_sync" />
<el-option label="批量识别" value="pt_resource_identify" />
<el-option label="订阅检查" value="subscription_check" />
<el-option label="媒体扫描" value="media_file_scan" />
<el-option label="创建下载" value="download_create" />
```

## 兼容性处理

### 向后兼容
为了兼容数据库中可能存在的旧格式任务,在以下地方添加了兼容逻辑:

1. **颜色映射**: 同时支持新旧两种格式
2. **编辑表单**: 自动将旧格式转换为新格式

```typescript
// 编辑时自动转换
if (task.task_type === 'pt_resource_sync' || task.task_type === 'pt_sync') {
  form.task_type = 'pt_resource_sync'  // 统一为新格式
  // ...
}
```

## 测试验证

### 测试场景
1. ✅ 创建新的 PT 同步任务
2. ✅ 创建新的订阅检查任务
3. ✅ 编辑现有任务(包括旧格式任务)
4. ✅ 任务类型过滤器正常工作
5. ✅ 任务颜色标签正确显示

### 预期行为
- 新建任务时,`task_type` 和 `handler` 字段都使用新格式
- 编辑旧任务时,自动转换为新格式
- 历史记录筛选支持新的任务类型

## 任务类型对照表

| 旧格式 | 新格式 | 说明 |
|--------|--------|------|
| `pt_sync` | `pt_resource_sync` | PT资源同步 |
| `batch_identify` | `pt_resource_identify` | PT资源识别 |
| `subscription_check` | `subscription_check` | 订阅检查(未变) |
| `scan_media` | `media_file_scan` | 媒体文件扫描 |
| `create_download` | `download_create` | 创建下载任务 |
| `sync_download_status` | `download_status_sync` | 同步下载状态 |
| `cleanup` | `task_execution_cleanup` | 任务执行记录清理 |

## 后续建议

1. ✅ **已修复**: 所有硬编码的旧任务类型已更新
2. ⚠️ **建议**: 在后端响应中统一任务类型格式
3. ⚠️ **建议**: 考虑添加前端类型守卫,避免将来再次使用错误的类型值

## 修复完成时间

- **开始**: 2025-12-07
- **完成**: 2025-12-07
- **状态**: ✅ 已完成
- **影响**: 前端所有任务创建和编辑功能

---

**维护者**: Claude Code
**更新日期**: 2025-12-07
