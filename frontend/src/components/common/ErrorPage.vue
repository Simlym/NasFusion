<template>
  <div class="error-page">
    <div class="error-content">
      <div class="error-icon-wrapper">
        <el-icon :size="120" class="error-icon">
          <component :is="iconComponent" />
        </el-icon>
      </div>

      <div class="error-code">{{ errorCode }}</div>
      <h1 class="error-title">{{ title }}</h1>
      <p class="error-description">{{ description }}</p>

      <div class="error-actions">
        <el-button type="primary" size="large" @click="handlePrimary">
          {{ primaryButtonText }}
        </el-button>
        <el-button v-if="showSecondary" size="large" @click="handleSecondary">
          {{ secondaryButtonText }}
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { WarningFilled, CircleClose, Lock, QuestionFilled } from '@element-plus/icons-vue'

const props = withDefaults(
  defineProps<{
    errorCode?: string | number
    title?: string
    description?: string
    icon?: 'warning' | 'error' | 'lock' | 'question'
    primaryButtonText?: string
    secondaryButtonText?: string
    showSecondary?: boolean
    onPrimary?: () => void
    onSecondary?: () => void
  }>(),
  {
    errorCode: '404',
    title: '页面未找到',
    description: '抱歉，您访问的页面不存在或已被移除',
    icon: 'warning',
    primaryButtonText: '返回首页',
    secondaryButtonText: '返回上一页',
    showSecondary: true
  }
)

const router = useRouter()

const iconComponent = computed(() => {
  switch (props.icon) {
    case 'error':
      return CircleClose
    case 'lock':
      return Lock
    case 'question':
      return QuestionFilled
    default:
      return WarningFilled
  }
})

const handlePrimary = () => {
  if (props.onPrimary) {
    props.onPrimary()
  } else {
    router.push('/')
  }
}

const handleSecondary = () => {
  if (props.onSecondary) {
    props.onSecondary()
  } else {
    router.back()
  }
}
</script>

<style scoped>
.error-page {
  min-height: 60vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-xl);
}

.error-content {
  text-align: center;
  max-width: 600px;
  animation: contentFadeIn 0.5s var(--ease-out-back);
}

.error-icon-wrapper {
  margin-bottom: var(--spacing-lg);
  animation: errorShake 0.6s ease-in-out;
}

@keyframes errorShake {
  0%, 100% {
    transform: translateX(0);
  }
  10%, 30%, 50%, 70%, 90% {
    transform: translateX(-8px);
  }
  20%, 40%, 60%, 80% {
    transform: translateX(8px);
  }
}

.error-icon {
  color: var(--warning-color);
  opacity: 0.8;
}

.error-code {
  font-size: 80px;
  font-weight: 800;
  background: var(--gradient-primary);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  line-height: 1;
  margin-bottom: var(--spacing-md);
  letter-spacing: -2px;
}

.error-title {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-color-primary);
  margin: 0 0 var(--spacing-md) 0;
  letter-spacing: -0.5px;
}

.error-description {
  font-size: 16px;
  color: var(--text-color-secondary);
  margin: 0 0 var(--spacing-xl) 0;
  line-height: 1.6;
}

.error-actions {
  display: flex;
  gap: var(--spacing-md);
  justify-content: center;
  flex-wrap: wrap;
}

/* 响应式 */
@media (max-width: 768px) {
  .error-code {
    font-size: 60px;
  }

  .error-title {
    font-size: 24px;
  }

  .error-description {
    font-size: 14px;
  }

  .error-actions {
    flex-direction: column;
    width: 100%;
  }

  .error-actions .el-button {
    width: 100%;
  }
}
</style>
