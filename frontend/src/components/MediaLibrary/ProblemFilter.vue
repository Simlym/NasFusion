<template>
  <div class="problem-filter">
    <el-space wrap>
      <span class="filter-label">问题筛选:</span>

      <el-check-tag
        v-for="item in problemTypes"
        :key="item.value"
        :checked="selectedIssues.includes(item.value)"
        @change="handleToggle(item.value)"
      >
        <el-icon><component :is="item.icon" /></el-icon>
        {{ item.label }}
        <el-badge
          v-if="issueCounts[item.value] > 0"
          :value="issueCounts[item.value]"
          type="danger"
          :offset="[5, -5]"
        />
      </el-check-tag>

      <el-button
        v-if="selectedIssues.length > 0"
        link
        type="primary"
        size="small"
        @click="clearAll"
      >
        清空
      </el-button>
    </el-space>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { Picture, Document, QuestionFilled, CopyDocument, FolderDelete } from '@element-plus/icons-vue'

interface Props {
  modelValue?: string[]
  counts?: Record<string, number>
}

interface Emits {
  (e: 'update:modelValue', value: string[]): void
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: () => [],
  counts: () => ({})
})

const emit = defineEmits<Emits>()

const selectedIssues = ref<string[]>([...props.modelValue])
const issueCounts = ref<Record<string, number>>({ ...props.counts })

/**
 * 问题类型定义
 */
const problemTypes = [
  {
    value: 'missing_poster',
    label: '缺少海报',
    icon: Picture
  },
  {
    value: 'missing_nfo',
    label: '缺少NFO',
    icon: Document
  },
  {
    value: 'unidentified',
    label: '未识别',
    icon: QuestionFilled
  },
  {
    value: 'duplicate',
    label: '重复文件',
    icon: CopyDocument
  },
  {
    value: 'missing_files',
    label: '缺少文件',
    icon: FolderDelete
  }
]

/**
 * 切换选择
 */
const handleToggle = (value: string) => {
  // 单选逻辑：如果已选中该项，则取消选中；如果未选中，则选中该项并清除其他选择
  const index = selectedIssues.value.indexOf(value)
  if (index > -1) {
    selectedIssues.value = []
  } else {
    selectedIssues.value = [value]
  }
  emit('update:modelValue', selectedIssues.value)
}

/**
 * 清空所有选择
 */
const clearAll = () => {
  selectedIssues.value = []
  emit('update:modelValue', [])
}

/**
 * 监听外部变化
 */
watch(
  () => props.modelValue,
  (newVal) => {
    selectedIssues.value = [...newVal]
  }
)

watch(
  () => props.counts,
  (newVal) => {
    issueCounts.value = { ...newVal }
  },
  { deep: true }
)
</script>

<style scoped lang="scss">
.problem-filter {
  .filter-label {
    font-size: 14px;
    color: var(--el-text-color-regular);
    font-weight: 500;
  }

  .el-check-tag {
    cursor: pointer;
    user-select: none;
    position: relative;

    .el-icon {
      margin-right: 4px;
    }
  }
}
</style>
