# 前端通知系统重构任务清单

> 本文档是后端架构重构完成后的前端配套任务
>
> **前置条件**：后端通知系统架构已完成重构（NotificationInternalService + NotificationExternalService）

---

## 📋 任务概览

### 已完成（后端）
- ✅ 通知全局配置初始化（16项配置到 system_settings）
- ✅ 站外消息历史 API（`GET /api/v1/notifications/external`）
- ✅ Service 层架构重构（Internal/External/Dispatch 分离）
- ✅ 前端 API 封装添加（`notification.ts` 新增站外消息 API）

### 待完成（前端）
- ⏳ 重构 `/notifications` 页面（简化为消息中心）
- ⏳ 重构 `/settings?tab=notifications` 页面（配置管理）
- ⏳ 添加跨页面导航优化

---

## 🎯 任务 1：重构 /notifications 页面

**目标**：将通知中心简化为"消息查看"功能，移除配置管理 Tab

### 当前状态
**文件**：`frontend/src/views/Notifications.vue`（1038 行）

**当前结构**：
- Tab1: 消息中心（站内消息列表）✅ 保留
- Tab2: 通知渠道（渠道配置）❌ 移至 Settings
- Tab3: 通知规则（规则管理）❌ 移至 Settings
- Tab4: 通知模板（模板管理）❌ 移至 Settings

### 目标结构
```
/notifications 页面
├── 页面标题：消息中心
├── 导航提示：[提示] 想要配置通知渠道、规则或模板？前往 设置 → 通知设置
├── Tab1: 站内消息（保留现有实现）
└── Tab2: 站外消息历史（新增）
```

### 实施步骤

#### 1.1 保留站内消息 Tab（Tab1）
**保持现有代码不变**：
- 消息列表（Line 16-120）
- 消息详情弹窗
- 标记已读/删除功能
- 分页和筛选

#### 1.2 移除配置类 Tab（Tab2/3/4）
**删除以下部分**：
- Tab2: 通知渠道（Line 121-185）
- Tab3: 通知规则（Line 186-235）
- Tab4: 通知模板（Line 236-410）
- 相关的 script 代码（渠道/规则/模板的数据和方法）

**保留的代码行范围**（仅供参考）：
- 模板部分：Line 1-120（页面头 + Tab1）
- Script 部分：Line 414-485（消息中心相关逻辑）

#### 1.3 新增站外消息历史 Tab（Tab2）

**模板代码**：
```vue
<!-- Tab 2: 站外消息历史 -->
<el-tab-pane label="站外消息历史" name="external">
  <el-card>
    <template #header>
      <div class="card-header">
        <span>站外通知发送记录</span>
        <div class="header-actions">
          <el-select
            v-model="externalFilter.status"
            placeholder="全部状态"
            clearable
            style="width: 120px; margin-right: 10px"
            @change="loadExternalMessages"
          >
            <el-option label="全部" value="" />
            <el-option label="已发送" value="sent" />
            <el-option label="发送失败" value="failed" />
            <el-option label="待发送" value="pending" />
          </el-select>
          <el-select
            v-model="externalFilter.channelType"
            placeholder="全部渠道"
            clearable
            style="width: 120px; margin-right: 10px"
            @change="loadExternalMessages"
          >
            <el-option label="全部" value="" />
            <el-option label="Telegram" value="telegram" />
            <el-option label="Email" value="email" />
            <el-option label="Webhook" value="webhook" />
          </el-select>
          <el-button :icon="Refresh" @click="loadExternalMessages">刷新</el-button>
        </div>
      </div>
    </template>

    <!-- 站外消息列表 -->
    <el-table
      v-loading="externalLoading"
      :data="externalMessages"
      style="width: 100%"
    >
      <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
      <el-table-column prop="channelType" label="渠道" width="120">
        <template #default="{ row }">
          <el-tag :type="getChannelTypeTag(row.channelType)" size="small">
            {{ getChannelTypeName(row.channelType) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="getExternalStatusTag(row.status)" size="small">
            {{ getExternalStatusName(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="sentAt" label="发送时间" width="180">
        <template #default="{ row }">
          {{ row.sentAt ? formatDateTime(row.sentAt) : '-' }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="100" fixed="right">
        <template #default="{ row }">
          <el-button
            type="primary"
            text
            :icon="View"
            @click="viewExternalMessage(row)"
          >
            查看
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <el-pagination
      v-model:current-page="externalPagination.page"
      v-model:page-size="externalPagination.pageSize"
      :total="externalPagination.total"
      :page-sizes="[10, 20, 50, 100]"
      layout="total, sizes, prev, pager, next, jumper"
      @size-change="loadExternalMessages"
      @current-change="loadExternalMessages"
      style="margin-top: 20px; justify-content: flex-end"
    />
  </el-card>
</el-tab-pane>
```

**Script 代码**：
```typescript
// 在 setup 中添加

// ==================== 站外消息历史 ====================
import { getExternalNotifications, type NotificationExternal } from '@/api/modules/notification'

const externalLoading = ref(false)
const externalMessages = ref<NotificationExternal[]>([])
const externalFilter = reactive({
  status: '',
  channelType: ''
})
const externalPagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

// 加载站外消息列表
const loadExternalMessages = async () => {
  externalLoading.value = true
  try {
    const res = await getExternalNotifications({
      page: externalPagination.page,
      page_size: externalPagination.pageSize,
      status: externalFilter.status || undefined,
      channel_type: externalFilter.channelType || undefined
    })
    if (res.data) {
      externalMessages.value = res.data.items || []
      externalPagination.total = res.data.total || 0
    }
  } catch (error) {
    console.error('加载站外消息失败:', error)
    ElMessage.error('加载站外消息失败')
  } finally {
    externalLoading.value = false
  }
}

// 查看站外消息详情
const viewExternalMessage = (message: NotificationExternal) => {
  // TODO: 实现详情弹窗
  ElMessage.info('查看站外消息: ' + message.title)
}

// 辅助方法
const getChannelTypeTag = (type: string) => {
  const tags: Record<string, string> = {
    telegram: 'primary',
    email: 'success',
    webhook: 'warning'
  }
  return tags[type] || 'info'
}

const getChannelTypeName = (type: string) => {
  const names: Record<string, string> = {
    telegram: 'Telegram',
    email: 'Email',
    webhook: 'Webhook'
  }
  return names[type] || type
}

const getExternalStatusTag = (status: string) => {
  const tags: Record<string, string> = {
    sent: 'success',
    failed: 'danger',
    pending: 'warning'
  }
  return tags[status] || 'info'
}

const getExternalStatusName = (status: string) => {
  const names: Record<string, string> = {
    sent: '已发送',
    failed: '发送失败',
    pending: '待发送'
  }
  return names[status] || status
}

// 监听 Tab 切换
watch(activeTab, (newTab) => {
  if (newTab === 'external') {
    loadExternalMessages()
  }
})
```

#### 1.4 添加导航提示

在页面顶部添加：
```vue
<!-- 在 el-tabs 之前添加 -->
<el-alert
  :closable="false"
  type="info"
  style="margin-bottom: 20px"
>
  <template #default>
    想要配置通知渠道、规则或模板？
    <el-link
      type="primary"
      :underline="false"
      @click="router.push('/settings?tab=notifications')"
      style="margin-left: 8px"
    >
      前往通知设置 →
    </el-link>
  </template>
</el-alert>
```

---

## 🎯 任务 2：重构 /settings?tab=notifications 页面

**目标**：实现完整的通知系统配置管理

### 当前状态
**文件**：`frontend/src/views/Settings.vue` 的 NotificationManager 组件

**当前实现**：TODO 占位页面（无实际功能）

### 目标结构
```
/settings?tab=notifications 页面
├── 导航提示：[提示] 想要查看收到的消息？前往消息中心 →
├── Section 1: 全局通知设置（使用 system_settings）
├── Section 2: 通知渠道管理（从 Notifications.vue 迁移）
├── Section 3: 通知规则管理（从 Notifications.vue 迁移）
└── Section 4: 通知模板管理（从 Notifications.vue 迁移）
```

### 实施步骤

#### 2.1 Section 1：全局通知设置（新增）

**读取配置**：
```typescript
import { getSettings, upsertSetting } from '@/api/modules/settings'

// 加载通知全局配置
const loadNotificationSettings = async () => {
  const res = await getSettings('notification')
  // 解析配置项
  const settings = res.data.items || []

  // 示例配置
  notificationSettings.value = {
    defaultLanguage: findSetting(settings, 'notification.default_language'),
    retentionDays: findSetting(settings, 'notification.retention_days'),
    enableSystemMessages: findSetting(settings, 'notification.enable_system_messages') === 'true',
    // ... 其他配置
  }
}

// 保存配置
const saveNotificationSettings = async () => {
  await upsertSetting('notification', 'notification.default_language', notificationSettings.value.defaultLanguage)
  await upsertSetting('notification', 'notification.retention_days', notificationSettings.value.retentionDays)
  // ... 保存其他配置
  ElMessage.success('全局设置已保存')
}
```

**表单 UI**：
```vue
<el-card header="全局通知设置">
  <el-form :model="notificationSettings" label-width="150px">
    <el-form-item label="默认语言">
      <el-select v-model="notificationSettings.defaultLanguage">
        <el-option label="简体中文" value="zh-CN" />
        <el-option label="English" value="en-US" />
      </el-select>
    </el-form-item>

    <el-form-item label="消息保留天数">
      <el-input-number v-model="notificationSettings.retentionDays" :min="1" :max="365" />
      <span style="margin-left: 10px; color: #909399">超过此天数的已读消息将自动清理</span>
    </el-form-item>

    <el-form-item label="启用系统内消息">
      <el-switch v-model="notificationSettings.enableSystemMessages" />
    </el-form-item>

    <!-- 更多配置项... -->

    <el-form-item>
      <el-button type="primary" @click="saveNotificationSettings">保存设置</el-button>
    </el-form-item>
  </el-form>
</el-card>
```

#### 2.2 Section 2-4：迁移渠道/规则/模板管理

**方法 A：完整迁移代码**
1. 从 `Notifications.vue` 复制 Tab2/3/4 的完整代码
2. 粘贴到 Settings.vue 的 notifications tab 中
3. 保留所有功能：CRUD、测试、筛选等

**方法 B：快捷跳转**
1. 仅显示简要列表和跳转按钮
2. 点击"管理渠道"跳转到 `/notifications/channels`
3. 点击"管理规则"跳转到 `/notifications/rules`
4. 点击"管理模板"跳转到 `/notifications/templates`

**推荐**：方法 A（完整迁移），保持功能一致性

#### 2.3 添加导航提示

```vue
<el-alert
  :closable="false"
  type="info"
  style="margin-bottom: 20px"
>
  <template #default>
    想要查看收到的消息？
    <el-link
      type="primary"
      :underline="false"
      @click="router.push('/notifications')"
      style="margin-left: 8px"
    >
      前往消息中心 →
    </el-link>
  </template>
</el-alert>
```

---

## 🎯 任务 3：UI 优化和测试

### 3.1 页面标题调整
- `/notifications`：消息中心（原"通知中心"）
- `/settings?tab=notifications`：通知设置

### 3.2 功能测试清单

#### Notifications 页面测试
- [ ] Tab1 站内消息列表正常显示
- [ ] 标记已读/删除功能正常
- [ ] Tab2 站外消息历史正常显示
- [ ] 筛选（状态、渠道类型）正常
- [ ] 分页功能正常
- [ ] 导航提示可点击跳转到 Settings

#### Settings 页面测试
- [ ] Section 1 全局设置表单正常显示
- [ ] 配置读取和保存正常
- [ ] Section 2-4 渠道/规则/模板管理功能正常
- [ ] 导航提示可点击跳转到 Notifications

---

## 📦 文件清单

### 需要修改的文件
1. ✅ `frontend/src/api/modules/notification.ts`（已完成 - 添加站外消息 API）
2. ⏳ `frontend/src/views/Notifications.vue`（重构：简化为消息中心）
3. ⏳ `frontend/src/views/Settings.vue`（重构：实现通知设置）
4. ⏳ `frontend/src/api/modules/settings.ts`（可能需要 - 确认 system_settings API）

### 需要测试的后端 API
- `GET /api/v1/notifications`（站内消息列表）
- `GET /api/v1/notifications/external`（站外消息历史）
- `GET /api/v1/system-settings?category=notification`（通知全局配置）
- `POST /api/v1/system-settings/{category}/{key}/upsert`（保存配置）

---

## 🔧 可选优化

### 优化 1：站外消息详情弹窗
显示更详细的发送信息：
- 渠道名称
- 发送状态和时间
- 错误信息（如果失败）
- 重试次数
- 响应数据

### 优化 2：站外消息统计图表
添加统计展示：
- 成功率
- 渠道分布
- 事件类型分布
- 每日发送量趋势

### 优化 3：批量操作
- 批量删除站内消息
- 批量标记已读
- 批量重试失败的站外消息

---

## 📚 参考资料

### 后端 API 文档
访问：`http://localhost:8000/docs`

关键接口：
- 通知系统：`/api/v1/notifications`
- 站外消息：`/api/v1/notifications/external`
- 系统设置：`/api/v1/system-settings`
- 通知渠道：`/api/v1/notification-channels`
- 通知规则：`/api/v1/notification-rules`
- 通知模板：`/api/v1/notification-templates`

### 前端组件参考
- Element Plus 组件库：https://element-plus.org/
- 现有实现：`Notifications.vue`（1038行，包含完整的 Tab 实现）

---

## ✅ 验收标准

### 功能完整性
- [x] 后端架构重构完成（Internal/External Service 分离）
- [x] 后端 API 全部可用
- [x] 前端 API 封装完成
- [ ] Notifications 页面简化完成
- [ ] Settings 页面配置管理完成
- [ ] 跨页面导航正常

### 用户体验
- [ ] 页面职责清晰（消息查看 vs 系统配置）
- [ ] 导航提示友好
- [ ] 无功能缺失
- [ ] 响应速度正常

### 代码质量
- [ ] 无 TypeScript 错误
- [ ] 无 ESLint 警告
- [ ] 组件结构清晰
- [ ] 代码可维护

---

## 📝 预计工作量

| 任务 | 预计时间 | 难度 |
|------|---------|------|
| 任务 1：重构 Notifications 页面 | 1-1.5 小时 | 中 |
| 任务 2：重构 Settings 页面 | 1.5-2 小时 | 中高 |
| 任务 3：测试和优化 | 0.5-1 小时 | 低 |
| **总计** | **3-4.5 小时** | **中** |

---

**创建时间**：2025-11-30
**依赖**：后端通知系统架构重构已完成
**状态**：待开始
