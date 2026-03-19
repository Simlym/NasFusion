# 存储挂载点系统 - 前端修改总结

## 修改时间
2026-01-03

## 修改的页面

### 1. ✅ MediaLibrarySettings.vue（媒体库设置页面）
**访问路径**：`/settings?tab=media`

#### 修改前
- 功能：配置各媒体分类的下载临时目录
- 数据来源：`system_settings.category_paths`（JSON）
- 存储格式：
  ```json
  {
    "movie": {
      "paths": [
        {"path": "./data/downloads/Movies", "is_default": true}
      ]
    }
  }
  ```

#### 修改后
- **功能**：存储挂载点配置管理
- **数据来源**：`storage_mounts` 表（通过 `/storage-mounts` API）
- **主要功能**：
  1. 下载挂载点管理（添加、编辑、删除、启用/禁用）
  2. 媒体库挂载点管理（同上）
  3. 显示挂载点信息：
     - 挂载点名称
     - 容器路径
     - 宿主机路径
     - 媒体类型
     - 优先级
     - 剩余空间
     - 状态

#### 新增 UI 组件
- **两个卡片**：
  - 下载挂载点列表
  - 媒体库挂载点列表
- **添加/编辑对话框**：
  - 挂载点名称
  - 容器路径
  - 宿主机路径（可选）
  - 挂载点类型（download/library）
  - 媒体类型（仅媒体库挂载点）
  - 优先级（仅媒体库挂载点）
  - 是否默认（仅媒体库挂载点）
  - 备注

#### API 调用
```typescript
// 加载挂载点列表
GET /storage-mounts

// 添加挂载点
POST /storage-mounts
{
  "mount_name": "mount_1",
  "container_path": "/app/data/downloads/mount_1",
  "host_path": "/volume2/Downloads",
  "mount_type": "download",
  "is_enabled": true
}

// 更新挂载点
PATCH /storage-mounts/{id}

// 删除挂载点
DELETE /storage-mounts/{id}
```

---

### 2. ✅ OrganizeSettings.vue（整理规则设置页面）
**访问路径**：`/settings?tab=organize`

#### 修改前
- **媒体库根目录**字段：
  - 可编辑输入框
  - 必填验证
  - 用于指定整理目标路径

#### 修改后
- **媒体库根目录**字段：
  - 改为只读（`disabled`）
  - 占位符：`"由挂载点系统动态选择"`
  - 移除必填验证
  - 添加提示信息：
    > 实际整理时由存储挂载点系统根据媒体类型自动选择目标路径，优先使用同盘挂载点。
  - 添加"配置挂载点"按钮，点击跳转到 `/settings?tab=media`

#### 代码变更
```vue
<!-- 旧代码 -->
<el-form-item label="媒体库根目录" prop="library_root">
  <el-input v-model="form.library_root" placeholder="例如: /media/Movies" />
</el-form-item>

<!-- 新代码 -->
<el-form-item label="媒体库根目录">
  <el-input
    v-model="form.library_root"
    disabled
    placeholder="由挂载点系统动态选择"
  >
    <template #append>
      <el-button @click="$router.push('/settings?tab=media')">配置挂载点</el-button>
    </template>
  </el-input>
  <div class="form-item-tip">
    实际整理时由存储挂载点系统根据媒体类型自动选择目标路径，优先使用同盘挂载点。
    <el-link type="primary" @click="$router.push('/settings?tab=media')">前往配置 →</el-link>
  </div>
</el-form-item>
```

#### 表单验证变更
```typescript
// 移除 library_root 必填验证
const rules = {
  media_type: [{ required: true, message: '请选择媒体类型', trigger: 'change' }],
  // library_root: [{ required: true, message: '请输入媒体库根目录', trigger: 'blur' }], // 已删除
  dir_template: [{ required: true, message: '请输入目录模板', trigger: 'blur' }],
  // ...
}
```

---

## 用户体验优化

### 工作流程引导
1. **新用户初始化**：
   - 访问 `/settings?tab=media`
   - 点击"添加下载挂载点"，配置下载存储
   - 点击"添加媒体库挂载点"，配置媒体库存储
   - 设置媒体类型、优先级

2. **配置整理规则**：
   - 访问 `/settings?tab=organize`
   - 看到"媒体库根目录"为灰色禁用状态
   - 点击"配置挂载点"按钮跳转到挂载点管理
   - 返回后继续配置目录模板和文件名模板

3. **下载和整理**：
   - 下载任务自动选择下载挂载点（优先同盘）
   - 整理任务自动选择媒体库挂载点（优先同盘）
   - 用户无需手动指定路径

### 视觉提示
- **帮助说明**：在 MediaLibrarySettings.vue 顶部显示工作原理
- **状态标签**：显示挂载点启用/禁用状态
- **剩余空间**：实时显示挂载点剩余空间
- **同盘标识**：（后续可添加）下载对话框中标识同盘挂载点

---

## 待完成的工作

### 前端
1. ⏳ **DownloadDialog.vue** - 下载对话框路径选择器
   - 替换旧的 `category_paths` API 调用
   - 改为调用 `/storage-mounts/download-paths?media_category={type}`
   - 显示同盘标识

2. ⏳ **首次使用向导** - 引导用户配置挂载点
   - 检测是否已配置挂载点
   - 如果未配置，显示配置向导

3. ⏳ **挂载点健康检查** - 显示挂载点可访问性
   - 在列表中显示"可访问"/"不可访问"状态
   - 定期检查挂载点健康状态

### 后端
4. ⏳ **存储挂载点 API** - 实现完整的 CRUD 接口
   - `GET /storage-mounts` - 列表
   - `POST /storage-mounts` - 创建
   - `PATCH /storage-mounts/{id}` - 更新
   - `DELETE /storage-mounts/{id}` - 删除
   - `POST /storage-mounts/scan` - 扫描挂载点
   - `GET /storage-mounts/download-paths` - 获取下载路径列表

---

## 用户迁移指南

### 对于现有用户

#### 步骤 1：访问新的设置页面


#### 步骤 2：创建下载挂载点
1. 点击"添加下载挂载点"
2. 填写信息：
   - 挂载点名称：`mount_1`
   - 容器路径：`/app/data/downloads/mount_1`
   - 宿主机路径：`/volume2/Downloads`（可选）
3. 点击"确定"

#### 步骤 3：创建媒体库挂载点
1. 点击"添加媒体库挂载点"
2. 填写信息：
   - 挂载点名称：`mount_1`
   - 容器路径：`/app/data/library/mount_1`
   - 宿主机路径：`/volume2/Media`（可选）
   - 媒体类型：`movie`
   - 优先级：`100`
   - 设为默认：`是`
3. 重复此步骤为每种媒体类型创建挂载点

#### 步骤 4：检查整理规则
1. 查看"媒体库根目录"字段为灰色禁用状态
2. 确认提示信息显示正确

#### 步骤 5：测试下载和整理
1. 创建新的下载任务，验证自动选择挂载点
2. 整理文件，验证自动选择同盘挂载点

---

## 常见问题

### Q1：为什么"媒体库根目录"字段是灰色的？
**A**：新的挂载点系统会根据媒体类型自动选择目标路径，无需手动配置。这样可以支持多盘聚合和同盘硬链接优化。

### Q2：如何修改媒体库路径？
**A**：点击"配置挂载点"按钮跳转到挂载点管理页面，在那里可以添加、编辑、删除挂载点。

### Q3：旧的下载临时目录配置会丢失吗？
**A**：旧配置保留在数据库中（`system_settings.category_paths`），但不再使用。建议按照上述步骤迁移到新的挂载点系统。

### Q4：如何实现多盘聚合？
**A**：为同一媒体类型创建多个挂载点，系统会按优先级和同盘策略自动选择。例如：
- `mount_1` - movie - 优先级 100（默认）
- `mount_2` - movie - 优先级 50（备用）

### Q5：同盘硬链接如何工作？
**A**：系统会检测下载文件所在的挂载点设备，优先选择同一设备的媒体库挂载点进行整理，从而使用硬链接而非复制。

---

## 截图对比

### 修改前（MediaLibrarySettings）
```
媒体库设定
配置各媒体分类的下载临时目录

┌─ 电影 ──────────────────┐
│ 目录 1: ./data/downloads/movie [默认] │
│ [添加目录]                              │
└─────────────────────────────────────┘
```

### 修改后（MediaLibrarySettings）
```
存储挂载点配置
配置下载和媒体库存储挂载点，支持多盘聚合和同盘硬链接优化

[添加下载挂载点] [添加媒体库挂载点]

┌─ 下载挂载点 ────────────────────┐
│ mount_1 | /app/data/downloads/mount_1 | /volume2/Downloads | movie | 1.5TB | 启用 │
└──────────────────────────────────────────────────────────────────────────┘

┌─ 媒体库挂载点 ──────────────────┐
│ mount_1 | /app/data/library/mount_1 | /volume2/Media | movie | 优先级:100 | 默认 | 2.3TB | 启用 │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

---

**文档维护者**: Claude Code
**最后更新**: 2026-01-03
**版本**: v1.0
