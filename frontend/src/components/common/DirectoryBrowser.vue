<template>
  <el-dialog
    v-model="dialogVisible"
    title="选择目录"
    width="700px"
    :before-close="handleClose"
  >
    <!-- 当前路径导航 -->
    <div class="path-navigation">
      <el-breadcrumb separator="/">
        <el-breadcrumb-item
          v-for="(segment, index) in pathSegments"
          :key="index"
          class="breadcrumb-item"
          @click="navigateToIndex(index)"
        >
          {{ segment || '根目录' }}
        </el-breadcrumb-item>
      </el-breadcrumb>
    </div>

    <!-- 父目录按钮 -->
    <el-button
      v-if="currentPath !== '/' && parentPath"
      type="primary"
      text
      :icon="Back"
      style="margin-bottom: 10px"
      @click="navigateUp"
    >
      上级目录
    </el-button>

    <!-- 目录列表 -->
    <el-table
      v-loading="loading"
      :data="directories"
      style="width: 100%; margin-top: 10px"
      max-height="400"
      @row-click="handleRowClick"
    >
      <el-table-column prop="name" label="目录名称">
        <template #default="{ row }">
          <el-icon style="margin-right: 8px"><Folder /></el-icon>
          {{ row.name }}
        </template>
      </el-table-column>
      <el-table-column prop="modified_at" label="修改时间" width="180">
        <template #default="{ row }">
          {{ row.modified_at ? formatDateTime(row.modified_at) : '-' }}
        </template>
      </el-table-column>
      <el-table-column label="状态" width="80">
        <template #default="{ row }">
          <el-tag v-if="row.is_accessible" type="success" size="small">可访问</el-tag>
          <el-tag v-else type="danger" size="small">无权限</el-tag>
        </template>
      </el-table-column>
    </el-table>

    <!-- 空状态 -->
    <el-empty
      v-if="!loading && directories.length === 0"
      description="该目录下没有子目录"
      :image-size="80"
    />

    <!-- 当前选择 -->
    <div class="selected-path">
      <span>当前选择：</span>
      <el-tag type="primary">{{ currentPath }}</el-tag>
    </div>

    <template #footer>
      <el-button @click="handleClose">取消</el-button>
      <el-button type="primary" @click="handleConfirm">确定</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Folder, Back } from '@element-plus/icons-vue'
import api from '@/api'
import { formatDateTime } from '@/utils/format'
import type { DirectoryItem } from '@/api/modules/filesystem'

// Props & Emits
interface Props {
  modelValue: boolean
  initialPath?: string
}

interface Emits {
  (e: 'update:modelValue', value: boolean): void
  (e: 'select', path: string): void
}

const props = withDefaults(defineProps<Props>(), {
  initialPath: '/'
})

const emit = defineEmits<Emits>()

// State
const dialogVisible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

const loading = ref(false)
const currentPath = ref(props.initialPath || '/')
const parentPath = ref<string | null>(null)
const directories = ref<DirectoryItem[]>([])

// Computed
const pathSegments = computed(() => {
  return currentPath.value.split(/[/\\]/).filter(Boolean)
})

// Methods
async function loadDirectory(path: string) {
  loading.value = true
  try {
    const res = await api.filesystem.browseDirectory(path)
    directories.value = res.data.directories
    currentPath.value = res.data.current_path
    parentPath.value = res.data.parent_path
  } catch (error: any) {
    ElMessage.error(error.message || '加载目录失败')
  } finally {
    loading.value = false
  }
}

function navigateUp() {
  if (parentPath.value) {
    loadDirectory(parentPath.value)
  }
}

function navigateToIndex(index: number) {
  const segments = pathSegments.value.slice(0, index + 1)
  const newPath = '/' + segments.join('/')
  loadDirectory(newPath)
}

function handleRowClick(row: DirectoryItem) {
  if (row.is_accessible) {
    loadDirectory(row.path)
  } else {
    ElMessage.warning('该目录无访问权限')
  }
}

function handleClose() {
  dialogVisible.value = false
}

function handleConfirm() {
  emit('select', currentPath.value)
  dialogVisible.value = false
}

// Watch
watch(
  () => props.modelValue,
  (visible) => {
    if (visible) {
      currentPath.value = props.initialPath || '/'
      loadDirectory(currentPath.value)
    }
  }
)
</script>

<style scoped>
.path-navigation {
  margin-bottom: 16px;
  padding: 10px;
  background-color: var(--bg-color-overlay);
  border: 1px solid var(--border-color);
  border-radius: 4px;
}

.breadcrumb-item {
  cursor: pointer;
}

.breadcrumb-item:hover {
  color: var(--primary-color);
}

.selected-path {
  margin-top: 16px;
  padding: 10px;
  background-color: var(--bg-color-overlay);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-color-primary);
}
</style>
