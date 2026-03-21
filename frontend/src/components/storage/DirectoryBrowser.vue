<template>
  <div class="directory-browser">
    <el-input
      v-model="currentPath"
      placeholder="输入路径或点击浏览按钮"
      :readonly="readonly"
      @change="handlePathChange"
    >
      <template #append>
        <el-button :icon="FolderOpened" @click="dialogVisible = true">
          浏览
        </el-button>
      </template>
    </el-input>

    <el-dialog
      v-model="dialogVisible"
      title="选择目录"
      width="600px"
      :close-on-click-modal="false"
    >
      <!-- 路径导航 -->
      <div class="path-navigator">
        <el-button
          :icon="Back"
          :disabled="!history.length"
          @click="navigateBack"
        >
          返回
        </el-button>
        <el-breadcrumb separator="/">
          <el-breadcrumb-item @click="navigateToRoot">
            根目录
          </el-breadcrumb-item>
          <el-breadcrumb-item
            v-for="(segment, index) in pathSegments"
            :key="index"
            @click="navigateToSegment(index)"
          >
            {{ segment }}
          </el-breadcrumb-item>
        </el-breadcrumb>
      </div>

      <!-- 目录列表 -->
      <el-table
        v-loading="loading"
        :data="directories"
        stripe
        height="300"
        style="cursor: pointer"
        @row-click="handleRowClick"
        @row-dblclick="handleRowDblClick"
      >
        <el-table-column prop="name" label="名称" min-width="200">
          <template #default="{ row }">
            <div class="directory-name">
              <el-icon><Folder /></el-icon>
              <span>{{ row.name }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="modified_at" label="修改时间" width="180">
          <template #default="{ row }">
            {{ row.modified_at ? formatDate(row.modified_at) : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_accessible ? 'success' : 'danger'" size="small">
              {{ row.is_accessible ? '可访问' : '不可访问' }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>

      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleConfirm">
            确定选择
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { FolderOpened, Folder, Back } from '@element-plus/icons-vue'
import request from '@/api/request'
import { getDefaultBrowsePath } from '@/api/modules/filesystem'

interface DirectoryItem {
  name: string
  path: string
  size: number
  modified_at?: string
  is_accessible: boolean
}

interface Props {
  modelValue: string
  readonly?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  readonly: false
})

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
  (e: 'change', value: string): void
}>()

const currentPath = ref(props.modelValue)
const dialogVisible = ref(false)
const loading = ref(false)
const directories = ref<DirectoryItem[]>([])
const parentPath = ref<string | null>(null)
const history = ref<string[]>([])
const selectedPath = ref('')
const defaultBrowsePath = ref<string | null>(null)

// 路径分段（用于面包屑导航）
const pathSegments = computed(() => {
  // 处理 Unix 和 Windows 路径
  const normalized = currentPath.value.replace(/\\/g, '/')
  // 去掉开头的 /
  const withoutRoot = normalized.startsWith('/') ? normalized.slice(1) : normalized
  return withoutRoot.split('/').filter(Boolean)
})

// 监听外部值变化
watch(() => props.modelValue, (newVal) => {
  currentPath.value = newVal
})

// 监听当前路径变化
watch(currentPath, (newVal) => {
  emit('update:modelValue', newVal)
  emit('change', newVal)
})

// 浏览目录
async function browseDirectory(path: string) {
  loading.value = true
  try {
    const response = await request.get('/file-system/browse-directory', {
      params: { path, show_hidden: false }
    })

    const data = response.data as {
      current_path: string
      parent_path: string | null
      directories: DirectoryItem[]
    }

    currentPath.value = data.current_path
    parentPath.value = data.parent_path
    directories.value = data.directories
  } catch (error: any) {
    ElMessage.error('浏览目录失败: ' + (error.message || '未知错误'))
    directories.value = []
  } finally {
    loading.value = false
  }
}

// 打开对话框时加载初始路径
watch(dialogVisible, async (visible) => {
  if (visible) {
    history.value = []
    selectedPath.value = currentPath.value

    // 如果已有路径值，直接使用
    if (currentPath.value) {
      browseDirectory(currentPath.value)
      return
    }

    // 无路径时，尝试获取默认浏览路径（Docker 环境使用挂载基础目录）
    if (defaultBrowsePath.value === null) {
      try {
        const res = await getDefaultBrowsePath()
        defaultBrowsePath.value = res.data.default_path || '/'
      } catch {
        defaultBrowsePath.value = '/'
      }
    }
    browseDirectory(defaultBrowsePath.value!)
  }
})

// 处理路径输入变化
function handlePathChange(value: string) {
  currentPath.value = value
}

// 处理行单击（选择但不进入）
function handleRowClick(row: DirectoryItem) {
  selectedPath.value = row.path
}

// 处理行双击（进入目录）
function handleRowDblClick(row: DirectoryItem) {
  if (!row.is_accessible) {
    ElMessage.warning('该目录不可访问')
    return
  }

  // 保存历史
  history.value.push(currentPath.value)
  browseDirectory(row.path)
}

// 返回上一级
function navigateBack() {
  const previous = history.value.pop()
  if (previous) {
    browseDirectory(previous)
  }
}

// 导航到根目录
function navigateToRoot() {
  const root = currentPath.value.includes('/') ? '/' : 'C:\\'
  history.value = []
  browseDirectory(root)
}

// 导航到面包屑的某一段
function navigateToSegment(index: number) {
  const segments = pathSegments.value.slice(0, index + 1)
  const isUnixPath = currentPath.value.startsWith('/')
  const newPath = isUnixPath ? '/' + segments.join('/') : segments.join('\\')

  history.value = []
  browseDirectory(newPath)
}

// 确认选择
function handleConfirm() {
  emit('update:modelValue', selectedPath.value)
  emit('change', selectedPath.value)
  dialogVisible.value = false
}

// 格式化日期
function formatDate(dateString: string): string {
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN')
}
</script>

<style scoped>
.directory-browser {
  width: 100%;
}

.path-navigator {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  padding: 12px;
  background: var(--bg-color-overlay);
  border: 1px solid var(--border-color);
  border-radius: 4px;
}

.path-navigator :deep(.el-breadcrumb) {
  flex: 1;
}

.path-navigator :deep(.el-breadcrumb__item) {
  cursor: pointer;
}

.path-navigator :deep(.el-breadcrumb__inner),
.path-navigator :deep(.el-breadcrumb__separator) {
  color: var(--text-color-regular);
}

.path-navigator :deep(.el-breadcrumb__item:hover .el-breadcrumb__inner) {
  color: var(--primary-color);
}

.directory-name {
  display: flex;
  align-items: center;
  gap: 8px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.el-table :deep(.el-table__row) {
  transition: background-color 0.2s;
}

.el-table :deep(.el-table__row:hover) {
  background-color: var(--el-table-row-hover-bg-color);
}
</style>
