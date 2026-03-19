# 系统设置 API 优化总结

## 问题分析

### 原有问题
1. **频繁触发 API 请求**：每次路由变化都会检查是否需要加载配置
2. **缓存逻辑矛盾**：虽然有内存缓存，但注释说"每次路由变化时重新加载配置"
3. **架构不合理**：全局系统设置在页面级 composable 中管理
4. **无持久化**：页面刷新后缓存丢失，需要重新请求

### 影响
- 在多个页面间切换时，虽然缓存会阻止网络请求，但 watch 回调仍然频繁触发
- 系统设置分散管理，不便于维护和扩展
- 用户体验不佳（页面刷新后需要重新加载）

## 优化方案

### 方案 1：Settings Store（已实施）

**核心思路**：
- 创建全局 `useSettingsStore`，统一管理系统设置
- 在应用启动时加载一次（App.vue 的 onMounted）
- 使用 pinia-plugin-persistedstate 持久化到 localStorage
- 所有组件通过 store 访问配置

**优点**：
1. ✅ 应用启动时只请求一次 API
2. ✅ 持久化到 localStorage，页面刷新无需重新请求
3. ✅ 全局状态管理，任何组件都可访问
4. ✅ 修改配置自动同步到所有使用的地方
5. ✅ 便于扩展其他系统设置

**实施步骤**：

1. **安装依赖**
```bash
npm install pinia-plugin-persistedstate@^3.2.1
```

2. **创建 Settings Store** (`frontend/src/stores/settings.ts`)
```typescript
export const useSettingsStore = defineStore('settings', () => {
  const showAdultContent = ref<boolean>(false)
  const initialized = ref<boolean>(false)

  async function initSettings() {
    if (initialized.value) return
    await loadMediaLibrarySettings()
    initialized.value = true
  }

  async function updateShowAdultContent(value: boolean) {
    await api.settings.updateSetting(...)
    showAdultContent.value = value
  }

  return { showAdultContent, initSettings, updateShowAdultContent }
})
```

3. **配置 Pinia 插件** (`frontend/src/main.ts`)
```typescript
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate'
pinia.use(piniaPluginPersistedstate)
```

4. **应用启动时初始化** (`frontend/src/App.vue`)
```typescript
const settingsStore = useSettingsStore()
onMounted(async () => {
  if (!settingsStore.initialized) {
    await settingsStore.initSettings()
  }
})
```

5. **重构 usePageTabs.ts**
```typescript
// 移除：loadAdultContentConfig(), updateAdultContentCache()
// 改用：const settingsStore = useSettingsStore()
const tabs = computed(() => {
  if (route.name === 'MediaLibrary' && settingsStore.showAdultContent) {
    // 动态添加成人页签
  }
})
```

6. **重构设置页面** (`MediaLibrarySettings.vue`)
```typescript
// 移除：import { updateAdultContentCache }
// 改用：const settingsStore = useSettingsStore()
const handleShowAdultContentChange = async (value: boolean) => {
  await settingsStore.updateShowAdultContent(value)
}
```

## 性能对比

### 优化前
- 每次路由变化触发 watch 回调
- 页面刷新需重新请求 API
- 设置分散在多个文件中

### 优化后
- 应用启动时只请求一次
- 持久化到 localStorage，页面刷新无需请求
- 统一的全局状态管理

## 扩展性

**新增系统设置的步骤**：

1. 在 `stores/settings.ts` 中添加状态：
```typescript
const newSetting = ref<string>('')

async function loadNewSetting() {
  const { data } = await api.settings.getSetting('category', 'key')
  newSetting.value = data?.value
}

// 在 initSettings() 中调用 loadNewSetting()
```

2. 在组件中使用：
```typescript
const settingsStore = useSettingsStore()
console.log(settingsStore.newSetting)
```

## 文件变更清单

### 新增文件
- ✅ `frontend/src/stores/settings.ts` - Settings Store

### 修改文件
- ✅ `frontend/package.json` - 添加 pinia-plugin-persistedstate 依赖
- ✅ `frontend/src/main.ts` - 配置持久化插件
- ✅ `frontend/src/App.vue` - 应用启动时初始化
- ✅ `frontend/src/stores/index.ts` - 导出 useSettingsStore
- ✅ `frontend/src/composables/usePageTabs.ts` - 重构为使用 store
- ✅ `frontend/src/components/settings/MediaLibrarySettings.vue` - 重构为使用 store

## 测试建议

1. **功能测试**：
   - 启动应用，检查网络面板，确认只请求一次 `/system-settings/.../show_adult_content`
   - 在设置页面修改"显示成人内容"开关，刷新页面，确认设置保持
   - 在媒体库页面，确认成人页签显示逻辑正确

2. **性能测试**：
   - 在多个页面间快速切换，检查网络请求次数
   - 刷新页面，检查是否从 localStorage 加载配置

3. **边界测试**：
   - 清除 localStorage，刷新页面，确认重新加载配置
   - API 请求失败时，确认错误处理正确

## 未来改进

1. **错误重试机制**：如果初始加载失败，可以添加重试逻辑
2. **配置更新通知**：如果后端配置被其他用户修改，前端可以接收通知并重新加载
3. **更多设置项**：将其他全局配置（如下载设置、通知设置）也迁移到 Settings Store

---

**优化完成时间**：2025-12-29
**优化负责人**：Claude Code
