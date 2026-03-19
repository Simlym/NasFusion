<template>
  <Icon
    v-if="isIconify"
    :icon="name"
    :width="size"
    :height="size"
    class="app-icon"
    :style="colorStyle"
  />
  <el-icon v-else :size="numericSize" class="app-icon" :style="colorStyle">
    <component :is="elIcon" />
  </el-icon>
</template>

<script setup lang="ts">
import { computed, defineAsyncComponent } from 'vue'
import { Icon } from '@iconify/vue'

const props = withDefaults(defineProps<{
  /** 图标名称，支持：
   *  - Iconify 格式：'lucide:film'、'mdi:home' 等
   *  - Element Plus 图标名（字符串）：'HomeFilled'、'Setting' 等（自动降级）
   */
  name: string
  /** 图标尺寸，支持数字(px)或 CSS 字符串 */
  size?: number | string
  /** 图标颜色（可选，不传则继承父级颜色） */
  color?: string
}>(), {
  size: 16,
  color: undefined,
})

/** 判断是否为 Iconify 格式（含冒号） */
const isIconify = computed(() => props.name.includes(':'))

/** 数字尺寸（用于 el-icon :size） */
const numericSize = computed(() => {
  const s = props.size
  if (typeof s === 'number') return s
  return parseInt(s) || 16
})

/** Iconify :width/:height 接受 string | number */
const size = computed(() => props.size)

const colorStyle = computed(() =>
  props.color ? { color: props.color } : {}
)

/**
 * Element Plus 图标降级：动态异步加载
 * 仅在 isIconify 为 false 时执行
 */
const elIcon = computed(() => {
  if (isIconify.value) return null
  return defineAsyncComponent(() =>
    import('@element-plus/icons-vue').then((m) => {
      const icon = (m as Record<string, unknown>)[props.name]
      if (!icon) {
        console.warn(`[AppIcon] 未找到 Element Plus 图标: ${props.name}`)
        return m.QuestionFilled
      }
      return icon as Parameters<typeof defineAsyncComponent>[0] extends () => Promise<infer T> ? T : never
    })
  )
})
</script>

<style scoped>
.app-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  vertical-align: middle;
  flex-shrink: 0;
}
</style>
