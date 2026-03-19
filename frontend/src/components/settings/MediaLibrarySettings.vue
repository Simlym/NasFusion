<template>
  <div class="settings-section">
    <h3>存储挂载点配置</h3>
    <p class="section-description">配置下载和媒体库存储挂载点，支持多盘聚合和同盘硬链接优化</p>

    <!-- 工具栏 -->
    <div class="toolbar">
      <el-button :icon="Refresh" :loading="loading" @click="loadMounts">刷新</el-button>
      <el-button :icon="Plus" type="primary" @click="showAddDialog('download')">添加下载挂载点</el-button>
      <el-button :icon="Plus" type="success" @click="showAddDialog('library')">添加媒体库挂载点</el-button>
    </div>

    <!-- 帮助说明 -->
    <el-alert type="info" :closable="false" style="margin-bottom: 20px">
      <div>
        <p><strong>工作原理</strong>：下载挂载点（临时） → 媒体库挂载点（最终存储）</p>
        <p style="margin-top: 8px; color: var(--el-text-color-secondary); font-size: 13px">
          系统会自动检测同盘挂载点，优先使用硬链接整理以节省空间
        </p>
      </div>
    </el-alert>

    <!-- 下载挂载点列表 -->
    <el-card shadow="never" style="margin-bottom: 20px">
      <template #header>
        <span><el-icon style="margin-right: 8px"><FolderOpened /></el-icon>下载挂载点</span>
      </template>
      <el-table v-loading="loading" :data="downloadMounts" stripe>
        <el-table-column prop="mount_name" label="挂载点名称" min-width="150" />
        <el-table-column prop="container_path" label="容器路径" min-width="200" show-overflow-tooltip />
        <el-table-column prop="host_path" label="宿主机路径" min-width="200" show-overflow-tooltip />
        <el-table-column prop="media_category" label="媒体类型" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.media_category" size="small">{{ getMediaTypeName(row.media_category) }}</el-tag>
            <span v-else style="color: var(--el-text-color-placeholder)">未设置</span>
          </template>
        </el-table-column>
        <el-table-column prop="free_space" label="剩余空间" width="120">
          <template #default="{ row }">
            <span v-if="row.free_space">{{ formatFileSize(row.free_space) }}</span>
            <span v-else style="color: var(--el-text-color-placeholder)">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="is_enabled" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_enabled ? 'success' : 'info'" size="small">
              {{ row.is_enabled ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="editMount(row)">编辑</el-button>
            <el-button link type="warning" size="small" @click="toggleMountStatus(row)">
              {{ row.is_enabled ? '禁用' : '启用' }}
            </el-button>
            <el-button link type="danger" size="small" @click="deleteMount(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!downloadMounts.length && !loading" description="未配置下载挂载点" :image-size="80" />
    </el-card>

    <!-- 媒体库挂载点列表 -->
    <el-card shadow="never">
      <template #header>
        <span><el-icon style="margin-right: 8px"><Film /></el-icon>媒体库挂载点</span>
      </template>
      <el-table v-loading="loading" :data="libraryMounts" stripe>
        <el-table-column prop="mount_name" label="挂载点名称" min-width="150" />
        <el-table-column prop="container_path" label="容器路径" min-width="200" show-overflow-tooltip />
        <el-table-column prop="host_path" label="宿主机路径" min-width="200" show-overflow-tooltip />
        <el-table-column prop="media_category" label="媒体类型" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.media_category" size="small" type="success">
              {{ getMediaTypeName(row.media_category) }}
            </el-tag>
            <span v-else style="color: var(--el-text-color-placeholder)">未设置</span>
          </template>
        </el-table-column>
        <el-table-column prop="priority" label="优先级" width="100" />
        <el-table-column prop="is_default" label="默认" width="80">
          <template #default="{ row }">
            <el-tag v-if="row.is_default" type="primary" size="small">默认</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="free_space" label="剩余空间" width="120">
          <template #default="{ row }">
            <span v-if="row.free_space">{{ formatFileSize(row.free_space) }}</span>
            <span v-else style="color: var(--el-text-color-placeholder)">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="is_enabled" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_enabled ? 'success' : 'info'" size="small">
              {{ row.is_enabled ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="editMount(row)">编辑</el-button>
            <el-button link type="warning" size="small" @click="toggleMountStatus(row)">
              {{ row.is_enabled ? '禁用' : '启用' }}
            </el-button>
            <el-button link type="danger" size="small" @click="deleteMount(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!libraryMounts.length && !loading" description="未配置媒体库挂载点" :image-size="80" />
    </el-card>

    <!-- 添加/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEditing ? '编辑挂载点' : '添加挂载点'"
      width="600px"
    >
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="120px">
        <el-form-item label="挂载点名称" prop="mount_name">
          <el-input v-model="form.mount_name" placeholder="如：mount_1, volume2_tv" />
        </el-form-item>
        <el-form-item label="容器路径" prop="container_path">
          <el-input v-model="form.container_path" placeholder="如：/app/data/downloads/mount_1" />
          <div class="form-item-tip">容器内的实际路径</div>
        </el-form-item>
        <el-form-item label="宿主机路径" prop="host_path">
          <el-input v-model="form.host_path" placeholder="如：/volume2/Downloads（可选）" />
          <div class="form-item-tip">仅用于显示和跨系统分析，可留空</div>
        </el-form-item>
        <el-form-item label="挂载点类型" prop="mount_type">
          <el-radio-group v-model="form.mount_type" :disabled="isEditing">
            <el-radio value="download">下载挂载点</el-radio>
            <el-radio value="library">媒体库挂载点</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="form.mount_type === 'library'" label="媒体类型" prop="media_category">
          <el-select v-model="form.media_category" placeholder="选择媒体类型">
            <el-option
              v-for="cat in mediaCategories"
              :key="cat.value"
              :label="cat.label"
              :value="cat.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item v-if="form.mount_type === 'library'" label="优先级" prop="priority">
          <el-input-number v-model="form.priority" :min="0" :max="100" />
          <div class="form-item-tip">数字越大优先级越高，同类型多个挂载点时按优先级选择</div>
        </el-form-item>
        <el-form-item v-if="form.mount_type === 'library'" label="设为默认">
          <el-switch v-model="form.is_default" />
          <div class="form-item-tip">该媒体类型的默认挂载点</div>
        </el-form-item>
        <el-form-item label="是否启用">
          <el-switch v-model="form.is_enabled" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="2"
            placeholder="如：国产、4K电影库"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Plus, FolderOpened, Film } from '@element-plus/icons-vue'
import type { FormInstance, FormRules } from 'element-plus'
import api from '@/api'

// 媒体类型列表
const mediaCategories = [
  { label: '电影', value: 'movie' },
  { label: '剧集', value: 'tv' },
  { label: '动画', value: 'anime' },
  { label: '电子书', value: 'book' },
  { label: '音乐', value: 'music' },
  { label: '成人', value: 'adult' },
  { label: '游戏', value: 'game' },
  { label: '其他', value: 'other' }
]

interface StorageMount {
  id: number
  mount_name: string
  container_path: string
  host_path?: string
  mount_type: 'download' | 'library'
  media_category?: string
  priority: number
  is_default: boolean
  is_enabled: boolean
  free_space?: number
  description?: string
}

const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const isEditing = ref(false)
const mounts = ref<StorageMount[]>([])
const formRef = ref<FormInstance>()

const defaultForm = {
  mount_name: '',
  container_path: '',
  host_path: '',
  mount_type: 'download' as 'download' | 'library',
  media_category: '',
  priority: 50,
  is_default: false,
  is_enabled: true,
  description: ''
}

const form = ref({ ...defaultForm })

const formRules: FormRules = {
  mount_name: [{ required: true, message: '请输入挂载点名称', trigger: 'blur' }],
  container_path: [{ required: true, message: '请输入容器路径', trigger: 'blur' }],
  mount_type: [{ required: true, message: '请选择挂载点类型', trigger: 'change' }]
}

// 计算属性：分离下载和媒体库挂载点
const downloadMounts = computed(() =>
  mounts.value.filter(m => m.mount_type === 'download')
)

const libraryMounts = computed(() =>
  mounts.value.filter(m => m.mount_type === 'library').sort((a, b) => {
    // 按媒体类型分组，同类型按优先级排序
    if (a.media_category !== b.media_category) {
      return (a.media_category || '').localeCompare(b.media_category || '')
    }
    return (b.priority || 0) - (a.priority || 0)
  })
)

// 获取媒体类型名称
function getMediaTypeName(value: string) {
  return mediaCategories.find(c => c.value === value)?.label || value
}

// 格式化文件大小
function formatFileSize(bytes: number) {
  if (!bytes) return '-'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let size = bytes
  let unitIndex = 0
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024
    unitIndex++
  }
  return `${size.toFixed(2)} ${units[unitIndex]}`
}

// 加载挂载点列表
async function loadMounts() {
  loading.value = true
  try {
    const res = await api.get('/storage-mounts')
    mounts.value = res.data.items || []
  } catch (error: any) {
    console.error('加载挂载点失败:', error)
    ElMessage.error(error.response?.data?.detail || '加载失败')
  } finally {
    loading.value = false
  }
}

// 显示添加对话框
function showAddDialog(mountType: 'download' | 'library') {
  isEditing.value = false
  form.value = {
    ...defaultForm,
    mount_type: mountType
  }
  dialogVisible.value = true
}

// 编辑挂载点
function editMount(mount: StorageMount) {
  isEditing.value = true
  form.value = {
    mount_name: mount.mount_name,
    container_path: mount.container_path,
    host_path: mount.host_path || '',
    mount_type: mount.mount_type,
    media_category: mount.media_category || '',
    priority: mount.priority || 50,
    is_default: mount.is_default || false,
    is_enabled: mount.is_enabled,
    description: mount.description || ''
  }
  form.value.id = mount.id
  dialogVisible.value = true
}

// 切换挂载点状态
async function toggleMountStatus(mount: StorageMount) {
  try {
    await api.patch(`/storage-mounts/${mount.id}`, {
      is_enabled: !mount.is_enabled
    })
    ElMessage.success(mount.is_enabled ? '已禁用' : '已启用')
    await loadMounts()
  } catch (error: any) {
    console.error('切换状态失败:', error)
    ElMessage.error(error.response?.data?.detail || '操作失败')
  }
}

// 删除挂载点
async function deleteMount(mount: StorageMount) {
  try {
    await ElMessageBox.confirm(
      `确定要删除挂载点"${mount.mount_name}"吗？`,
      '删除确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    await api.delete(`/storage-mounts/${mount.id}`)
    ElMessage.success('删除成功')
    await loadMounts()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
      ElMessage.error(error.response?.data?.detail || '删除失败')
    }
  }
}

// 提交表单
async function submitForm() {
  if (!formRef.value) return

  try {
    await formRef.value.validate()
    saving.value = true

    const data = { ...form.value }
    if (data.mount_type === 'download') {
      delete data.media_category
      delete data.priority
      delete data.is_default
    }

    if (isEditing.value) {
      await api.patch(`/storage-mounts/${data.id}`, data)
      ElMessage.success('更新成功')
    } else {
      await api.post('/storage-mounts', data)
      ElMessage.success('添加成功')
    }

    dialogVisible.value = false
    await loadMounts()
  } catch (error: any) {
    if (error !== false) { // 排除表单验证失败
      console.error('提交失败:', error)
      ElMessage.error(error.response?.data?.detail || '提交失败')
    }
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  loadMounts()
})
</script>

<style scoped>
.settings-section {
  padding: 20px;
}

.settings-section h3 {
  margin: 0 0 8px 0;
  font-size: 20px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.section-description {
  margin: 0 0 20px 0;
  color: var(--el-text-color-secondary);
  font-size: 14px;
}

.toolbar {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
}

.form-item-tip {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 4px;
}
</style>
