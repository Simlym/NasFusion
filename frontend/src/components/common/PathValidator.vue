<template>
  <div class="path-validator">
    <!-- 路径输入 -->
    <el-input
      :model-value="modelValue"
      :placeholder="placeholder"
      @update:model-value="handleInput"
      @blur="validatePath"
    >
      <template #prepend>
        <span>{{ label }}</span>
      </template>
      <template #append>
        <el-button :icon="FolderOpened" @click="openBrowser">浏览</el-button>
      </template>
    </el-input>

    <!-- 验证状态 -->
    <div v-if="validation" class="validation-info">
      <div class="validation-row">
        <el-tag :type="validation.exists ? 'success' : 'danger'" size="small">
          {{ validation.exists ? '路径存在' : '路径不存在' }}
        </el-tag>
        <el-tag
          v-if="validation.exists"
          :type="validation.readable ? 'success' : 'warning'"
          size="small"
        >
          {{ validation.readable ? '可读' : '不可读' }}
        </el-tag>
        <el-tag
          v-if="validation.exists"
          :type="validation.writable ? 'success' : 'warning'"
          size="small"
        >
          {{ validation.writable ? '可写' : '不可写' }}
        </el-tag>
      </div>

      <!-- 磁盘信息 -->
      <div v-if="validation.exists && validation.disk_info" class="disk-info">
        <span>
          可用空间：{{ formatDiskSpace(validation.disk_info.free) }} /
          {{ formatDiskSpace(validation.disk_info.total) }}
        </span>
        <el-progress
          :percentage="validation.disk_info.percent"
          :color="getProgressColor(validation.disk_info.percent)"
          :show-text="false"
          style="width: 200px; margin-left: 10px"
        />
      </div>

      <!-- 自动创建按钮 -->
      <div v-if="!validation.exists && showCreateButton" class="create-button">
        <el-button size="small" type="primary" :loading="creating" @click="handleCreateDirectory">
          创建目录
        </el-button>
      </div>

      <!-- 错误信息 -->
      <div v-if="validation.error" class="error-message">
        <el-text type="danger" size="small">{{ validation.error }}</el-text>
      </div>
    </div>

    <!-- 目录浏览器 -->
    <DirectoryBrowser
      v-model="browserVisible"
      :initial-path="modelValue || '/'"
      @select="handleSelectPath"
    />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { FolderOpened } from '@element-plus/icons-vue'
import api from '@/api'
import { formatDiskSpace } from '@/utils/format'
import DirectoryBrowser from './DirectoryBrowser.vue'
import type { PathValidation } from '@/api/modules/filesystem'

// Props & Emits
interface Props {
  modelValue: string
  label?: string
  placeholder?: string
  showCreateButton?: boolean
}

interface Emits {
  (e: 'update:modelValue', value: string): void
}

const props = withDefaults(defineProps<Props>(), {
  label: '目录',
  placeholder: '请输入目录路径',
  showCreateButton: true
})

const emit = defineEmits<Emits>()

// State
const validation = ref<PathValidation | null>(null)
const browserVisible = ref(false)
const creating = ref(false)

// Methods
function handleInput(value: string) {
  emit('update:modelValue', value)
  validation.value = null // 清除旧验证结果
}

async function validatePath() {
  if (!props.modelValue) return

  try {
    const res = await api.filesystem.validatePath(props.modelValue)
    validation.value = res.data
  } catch (error: any) {
    ElMessage.error(error.message || '路径验证失败')
  }
}

function openBrowser() {
  browserVisible.value = true
}

function handleSelectPath(path: string) {
  emit('update:modelValue', path)
  validatePath()
}

async function handleCreateDirectory() {
  if (!props.modelValue) return

  creating.value = true
  try {
    const res = await api.filesystem.createDirectory(props.modelValue)
    if (res.data.success) {
      ElMessage.success('目录创建成功')
      validatePath()
    } else if (res.data.error) {
      ElMessage.error(res.data.error)
    }
  } catch (error: any) {
    ElMessage.error(error.message || '创建目录失败')
  } finally {
    creating.value = false
  }
}

function getProgressColor(percent: number): string {
  if (percent < 70) return '#67c23a'
  if (percent < 90) return '#e6a23c'
  return '#f56c6c'
}

// Expose validate method
defineExpose({
  validatePath
})
</script>

<style scoped>
.path-validator {
  width: 100%;
}

.validation-info {
  margin-top: 8px;
  padding: 8px;
  background-color: #f5f7fa;
  border-radius: 4px;
}

.validation-row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.disk-info {
  display: flex;
  align-items: center;
  font-size: 12px;
  color: #606266;
  margin-top: 8px;
}

.create-button {
  margin-top: 8px;
}

.error-message {
  margin-top: 8px;
}
</style>
