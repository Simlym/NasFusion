<template>
  <div class="empty-state" :class="size">
    <div class="empty-icon-wrapper">
      <el-icon :size="iconSize" class="empty-icon">
        <component :is="iconComponent" />
      </el-icon>
    </div>

    <h3 v-if="title" class="empty-title">{{ title }}</h3>
    <p v-if="description" class="empty-description">{{ description }}</p>

    <div v-if="showAction" class="empty-actions">
      <el-button
        :type="actionType"
        :size="actionSize"
        :icon="actionIcon"
        @click="handleAction"
      >
        {{ actionText }}
      </el-button>
    </div>

    <!-- 自定义action插槽（保持向后兼容） -->
    <div v-if="$slots.action" class="empty-action">
      <slot name="action"></slot>
    </div>

    <!-- 默认插槽 -->
    <slot></slot>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import {
  DocumentDelete,
  FolderOpened,
  Search,
  InfoFilled,
  WarningFilled,
  Plus
} from '@element-plus/icons-vue'

const props = withDefaults(
  defineProps<{
    icon?: any
    iconType?: 'document' | 'folder' | 'search' | 'info' | 'warning'
    title?: string
    description?: string
    size?: 'small' | 'medium' | 'large'
    showAction?: boolean
    actionText?: string
    actionType?: 'primary' | 'success' | 'warning' | 'danger' | 'info' | 'default'
    actionIcon?: any
    onAction?: () => void
  }>(),
  {
    icon: undefined,
    iconType: 'folder',
    title: '暂无数据',
    description: '',
    size: 'medium',
    showAction: false,
    actionText: '新建',
    actionType: 'primary',
    actionIcon: Plus
  }
)

const emit = defineEmits<{
  action: []
}>()

const iconComponent = computed(() => {
  // 优先使用传入的icon prop（保持向后兼容）
  if (props.icon) {
    return props.icon
  }

  // 使用iconType
  switch (props.iconType) {
    case 'document':
      return DocumentDelete
    case 'search':
      return Search
    case 'info':
      return InfoFilled
    case 'warning':
      return WarningFilled
    default:
      return FolderOpened
  }
})

const iconSize = computed(() => {
  switch (props.size) {
    case 'small':
      return 64
    case 'large':
      return 120
    default:
      return 96
  }
})

const actionSize = computed(() => {
  switch (props.size) {
    case 'small':
      return 'small'
    case 'large':
      return 'large'
    default:
      return 'default'
  }
})

const handleAction = () => {
  if (props.onAction) {
    props.onAction()
  }
  emit('action')
}
</script>

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-xl);
  text-align: center;
  animation: contentFadeIn 0.4s var(--ease-out-back);
}

.empty-state.small {
  padding: var(--spacing-lg);
}

.empty-state.large {
  padding: var(--spacing-xxl);
  min-height: 400px;
}

.empty-icon-wrapper {
  margin-bottom: var(--spacing-lg);
  animation: floatUpDown 3s ease-in-out infinite;
}

@keyframes floatUpDown {
  0%,
  100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-10px);
  }
}

.empty-icon {
  color: var(--text-color-tertiary);
  opacity: 0.5;
}

.empty-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-color-primary);
  margin: 0 0 var(--spacing-sm) 0;
}

.empty-state.small .empty-title {
  font-size: 16px;
}

.empty-state.large .empty-title {
  font-size: 22px;
}

.empty-description {
  font-size: 14px;
  color: var(--text-color-secondary);
  margin: 0 0 var(--spacing-lg) 0;
  max-width: 400px;
  line-height: 1.6;
}

.empty-state.small .empty-description {
  font-size: 13px;
  margin-bottom: var(--spacing-md);
}

.empty-state.large .empty-description {
  font-size: 15px;
  max-width: 500px;
}

.empty-actions,
.empty-action {
  margin-top: var(--spacing-md);
}

/* 响应式 */
@media (max-width: 768px) {
  .empty-state {
    padding: var(--spacing-lg);
  }

  .empty-state.large {
    min-height: 300px;
    padding: var(--spacing-xl);
  }

  .empty-title {
    font-size: 16px;
  }

  .empty-description {
    font-size: 13px;
  }
}
</style>
