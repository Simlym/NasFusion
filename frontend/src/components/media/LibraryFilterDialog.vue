<template>
  <el-dialog
    v-model="visible"
    title="媒体库显示设置"
    width="500px"
    @closed="handleClosed"
  >
    <div class="filter-tip">
      <el-alert
        title="默认全部显示，取消勾选的媒体库将不在最近观看中显示"
        type="info"
        show-icon
        :closable="false"
      />
    </div>

    <div v-loading="loading" class="library-list">
      <template v-if="libraries.length > 0">
        <el-checkbox-group v-model="localVisibleIds">
          <div v-for="lib in libraries" :key="lib.id" class="library-item">
            <el-checkbox :value="lib.id">
              <div class="lib-info">
                <span class="lib-name">{{ lib.name }}</span>
                <span class="lib-type">{{ formatLibType(lib.type) }}</span>
              </div>
            </el-checkbox>
          </div>
        </el-checkbox-group>
      </template>
      <el-empty v-else-if="!loading" description="未找到媒体库" />
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存设置</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/api'
import type { MediaServerConfig } from '@/types/mediaServer'

const props = defineProps<{
  configId?: number
  config?: MediaServerConfig
}>()

const emit = defineEmits(['updated'])

const visible = ref(false)
const loading = ref(false)
const saving = ref(false)
const libraries = ref<any[]>([])
const localVisibleIds = ref<string[]>([])

const open = async () => {
  if (!props.configId) {
    ElMessage.warning('请先选择媒体服务器')
    return
  }
  visible.value = true
  await loadLibraries()
}

const loadLibraries = async () => {
  if (!props.configId) return
  loading.value = true
  try {
    const res = await api.mediaServer.getMediaServerLibraries(props.configId, true)
    libraries.value = res.data
    const excluded = new Set(props.config?.server_config?.excluded_library_ids || [])
    localVisibleIds.value = libraries.value
      .map((lib: any) => lib.id)
      .filter((id: string) => !excluded.has(id))
  } catch (err) {
    ElMessage.error('获取媒体库失败')
  } finally {
    loading.value = false
  }
}

const handleSave = async () => {
  if (!props.configId) return
  saving.value = true
  try {
    const updatedConfig = { ...props.config }
    if (!updatedConfig.server_config) {
      updatedConfig.server_config = {}
    }
    const visibleSet = new Set(localVisibleIds.value)
    updatedConfig.server_config.excluded_library_ids = libraries.value
      .map((lib: any) => lib.id)
      .filter((id: string) => !visibleSet.has(id))

    await api.mediaServer.updateMediaServerConfig(props.configId, {
      server_config: updatedConfig.server_config
    })

    ElMessage.success('设置已保存')
    visible.value = false
    emit('updated')
  } catch (err) {
    ElMessage.error('保存设置失败')
  } finally {
    saving.value = false
  }
}

const handleClosed = () => {
  libraries.value = []
}

const formatLibType = (type: string) => {
  const map: Record<string, string> = {
    movies: '电影',
    tvshows: '剧集',
    music: '音乐',
    books: '书籍',
    other: '其他'
  }
  return map[type] || type
}

defineExpose({ open })
</script>

<style scoped>
.filter-tip {
  margin-bottom: 20px;
}

.library-list {
  max-height: 400px;
  overflow-y: auto;
  padding: 10px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 4px;
}

.library-item {
  padding: 8px 0;
  border-bottom: 1px dashed var(--el-border-color-lighter);
}

.library-item:last-child {
  border-bottom: none;
}

:deep(.el-checkbox) {
  width: 100%;
  height: auto;
}

.lib-info {
  display: flex;
  flex-direction: column;
  margin-left: 8px;
}

.lib-name {
  font-weight: 500;
  color: var(--el-text-color-primary);
}

.lib-type {
  font-size: 11px;
  color: var(--el-text-color-secondary);
  line-height: 1.2;
}
</style>
