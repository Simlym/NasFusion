<template>
  <div class="problem-filter">
    <!-- Mobile: 下拉选择 -->
    <el-select
      v-if="isMobile"
      v-model="selectedSingle"
      placeholder="问题筛选"
      clearable
      style="width: 100%"
      @change="handleSelectChange"
      @clear="clearAll"
    >
      <el-option
        v-for="item in problemTypes"
        :key="item.value"
        :value="item.value"
        :label="issueCounts[item.value] > 0 ? `${item.label} (${issueCounts[item.value]})` : item.label"
      />
    </el-select>

    <!-- Desktop: check tag 列表 -->
    <el-space v-else wrap>
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
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
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

// 移动端单选值（同步自 selectedIssues）
const selectedSingle = computed({
  get: () => selectedIssues.value[0] ?? null,
  set: (val) => {
    selectedIssues.value = val ? [val] : []
    emit('update:modelValue', selectedIssues.value)
  }
})

const problemTypes = [
  { value: 'missing_poster', label: '缺少海报', icon: Picture },
  { value: 'missing_nfo',    label: '缺少NFO',  icon: Document },
  { value: 'unidentified',   label: '未识别',   icon: QuestionFilled },
  { value: 'duplicate',      label: '重复文件', icon: CopyDocument },
  { value: 'missing_files',  label: '缺少文件', icon: FolderDelete }
]

// 移动端检测
const isMobile = ref(window.innerWidth <= 768)
const onResize = () => { isMobile.value = window.innerWidth <= 768 }
onMounted(() => window.addEventListener('resize', onResize))
onUnmounted(() => window.removeEventListener('resize', onResize))

const handleSelectChange = (val: string | null) => {
  selectedIssues.value = val ? [val] : []
  emit('update:modelValue', selectedIssues.value)
}

const handleToggle = (value: string) => {
  const index = selectedIssues.value.indexOf(value)
  selectedIssues.value = index > -1 ? [] : [value]
  emit('update:modelValue', selectedIssues.value)
}

const clearAll = () => {
  selectedIssues.value = []
  emit('update:modelValue', [])
}

watch(() => props.modelValue, (v) => { selectedIssues.value = [...v] })
watch(() => props.counts, (v) => { issueCounts.value = { ...v } }, { deep: true })
</script>

<style scoped lang="scss">
.problem-filter {
  .filter-label {
    font-size: 13px;
    color: var(--el-text-color-regular);
    font-weight: 500;
  }

  .el-check-tag {
    cursor: pointer;
    user-select: none;
    position: relative;
    padding: 4px 10px;
    font-size: 13px;
    line-height: 1.4;
    border-radius: 4px;

    .el-icon {
      margin-right: 3px;
      font-size: 13px;
    }
  }
}
</style>
