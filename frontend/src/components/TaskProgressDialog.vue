<template>
  <el-dialog
    v-model="visible"
    title="任务进度"
    width="700px"
    :close-on-click-modal="false"
    :close-on-press-escape="false"
    :show-close="false"
  >
    <div class="progress-content">
      <!-- 进度条 -->
      <el-progress
        :percentage="progress"
        :status="progressStatus"
        :stroke-width="20"
      />

      <!-- 任务信息 -->
      <div class="task-info">
        <p class="task-name">{{ taskExecution?.task_name || '任务处理中' }}</p>
        <p class="task-status">
          状态: <el-tag :type="statusType">{{ statusText }}</el-tag>
        </p>

        <!-- 步骤式进度（如果有steps） -->
        <div v-if="progressDetail?.steps" class="steps-container">
          <el-steps :active="progressDetail.current_step" finish-status="success" process-status="process">
            <el-step
              v-for="(step, index) in progressDetail.steps"
              :key="index"
              :title="step.name"
              :description="step.message"
              :status="getStepStatus(step)"
            >
              <template #icon>
                <el-icon v-if="step.status === 'completed'" class="step-icon-success">
                  <CircleCheck />
                </el-icon>
                <el-icon v-else-if="step.status === 'running'" class="step-icon-running">
                  <Loading />
                </el-icon>
                <el-icon v-else-if="step.status === 'failed'" class="step-icon-failed">
                  <CircleClose />
                </el-icon>
                <el-icon v-else class="step-icon-pending">
                  <Clock />
                </el-icon>
              </template>
            </el-step>
          </el-steps>
        </div>

        <!-- 批量处理进度（兼容旧格式） -->
        <div v-else-if="progressDetail && (progressDetail.processed !== undefined)" class="progress-detail">
          <span>已处理: {{ progressDetail.processed }} / {{ progressDetail.total }}</span>
          <span style="margin-left: 20px">成功: {{ progressDetail.success }}</span>
          <span style="margin-left: 20px">失败: {{ progressDetail.failed }}</span>
          <span style="margin-left: 20px">跳过: {{ progressDetail.skipped }}</span>
        </div>
      </div>

      <!-- 错误信息 -->
      <el-alert
        v-if="taskExecution?.error_message"
        type="error"
        :title="taskExecution.error_message"
        :closable="false"
        style="margin-top: 15px"
      />
    </div>

    <template #footer>
      <span v-if="isRunning" style="color: #909399; font-size: 14px; margin-right: auto;">
        任务在后台继续执行，可以关闭此窗口
      </span>
      <el-button :type="isRunning ? 'default' : 'primary'" @click="handleClose">
        {{ isRunning ? '后台运行' : '关闭' }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { CircleCheck, Loading, CircleClose, Clock } from '@element-plus/icons-vue'
import { getTaskExecution } from '@/api/modules/task'
import type { TaskExecution } from '@/types'

interface Props {
  modelValue: boolean
  taskExecutionId?: number
}

interface Emits {
  (e: 'update:modelValue', value: boolean): void
  (e: 'completed', result: any): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const taskExecution = ref<TaskExecution | null>(null)
const progress = ref(0)
const progressDetail = ref<any>(null)
let pollingTimer: NodeJS.Timeout | null = null

const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

const isRunning = computed(() => {
  return taskExecution.value?.status === 'pending' || taskExecution.value?.status === 'running'
})

const statusText = computed(() => {
  const statusMap: Record<string, string> = {
    pending: '等待中',
    running: '执行中',
    completed: '已完成',
    failed: '失败',
    cancelled: '已取消',
    timeout: '超时'
  }
  return statusMap[taskExecution.value?.status || ''] || '未知'
})

const statusType = computed(() => {
  const typeMap: Record<string, any> = {
    pending: 'info',
    running: 'primary',
    completed: 'success',
    failed: 'danger',
    cancelled: 'warning',
    timeout: 'warning'
  }
  return typeMap[taskExecution.value?.status || ''] || 'info'
})

const progressStatus = computed(() => {
  if (taskExecution.value?.status === 'completed') return 'success'
  if (taskExecution.value?.status === 'failed') return 'exception'
  return undefined
})

const getStepStatus = (step: any) => {
  if (step.status === 'completed') return 'success'
  if (step.status === 'running') return 'process'
  if (step.status === 'failed') return 'error'
  return 'wait'
}

const loadTaskExecution = async () => {
  if (!props.taskExecutionId) return

  try {
    const response = await getTaskExecution(props.taskExecutionId)
    if (response?.data) {
      taskExecution.value = response.data
      progress.value = response.data.progress || 0
      progressDetail.value = response.data.progress_detail

      // 检查是否完成
      if (['completed', 'failed', 'cancelled', 'timeout'].includes(response.data.status)) {
        stopPolling()

        if (response.data.status === 'completed') {
          ElMessage.success(`${taskExecution.value?.task_name || '任务'}完成`)
          emit('completed', response.data.result)
        } else if (response.data.status === 'failed') {
          ElMessage.error(`${taskExecution.value?.task_name || '任务'}失败`)
        }
      }
    }
  } catch (error: any) {
    console.error('Failed to load task execution:', error)
  }
}

const startPolling = () => {
  if (pollingTimer) return

  // 立即加载一次
  loadTaskExecution()

  // 每2秒轮询一次
  pollingTimer = setInterval(() => {
    loadTaskExecution()
  }, 2000)
}

const stopPolling = () => {
  if (pollingTimer) {
    clearInterval(pollingTimer)
    pollingTimer = null
  }
}

const handleClose = () => {
  stopPolling()
  visible.value = false
}

// 监听对话框打开
watch(() => props.modelValue, (newVal) => {
  if (newVal && props.taskExecutionId) {
    startPolling()
  } else {
    stopPolling()
  }
})

// 组件卸载时清理
onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped>
.progress-content {
  padding: 20px 0;
}

.task-info {
  margin-top: 20px;
}

.task-name {
  font-size: 16px;
  font-weight: 500;
  margin-bottom: 10px;
  color: var(--text-color-primary);
}

.task-status {
  margin-bottom: 10px;
  color: var(--text-color-regular);
}

.progress-detail {
  margin-top: 10px;
  font-size: 14px;
  color: var(--text-color-secondary);
}

.steps-container {
  margin-top: 20px;
  padding: 15px;
  background: var(--bg-color-overlay);
  border-radius: 8px;
}

/* 缩小步骤文字大小 */
.steps-container :deep(.el-step__title) {
  font-size: 13px;
  line-height: 1.4;
  color: var(--text-color-regular);
}

.steps-container :deep(.el-step.is-process .el-step__title) {
  color: var(--primary-color);
  font-weight: bold;
}

.steps-container :deep(.el-step.is-success .el-step__title) {
  color: var(--success-color);
}

.steps-container :deep(.el-step.is-error .el-step__title) {
  color: var(--danger-color);
}

.steps-container :deep(.el-step__description) {
  font-size: 12px;
  line-height: 1.3;
  margin-top: 2px;
  color: var(--text-color-secondary);
}

/* 调整步骤间距 */
.steps-container :deep(.el-step__head) {
  width: 24px;
}

.steps-container :deep(.el-step__icon) {
  width: 24px;
  height: 24px;
  font-size: 12px;
}

.steps-container :deep(.el-step__main) {
  padding-left: 8px;
}

.step-icon-success {
  color: var(--success-color);
  animation: none;
}

.step-icon-running {
  color: var(--primary-color);
  animation: rotate 1.5s linear infinite;
}

.step-icon-failed {
  color: var(--danger-color);
}

.step-icon-pending {
  color: var(--text-color-muted);
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>
