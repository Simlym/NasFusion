<template>
  <el-card
    class="stat-card"
    :class="[variant, { 'has-gradient': gradient }]"
    shadow="hover"
  >
    <div class="stat-content">
      <div class="stat-icon-wrapper" :style="iconWrapperStyle">
        <div class="stat-icon">
          <el-icon :size="24">
            <component :is="icon" />
          </el-icon>
        </div>
      </div>
      <div class="stat-info">
        <div class="stat-value">{{ formattedValue }}</div>
        <div class="stat-label">{{ label }}</div>
        <div v-if="trend" class="stat-trend" :class="trendClass">
          <el-icon :size="14">
            <ArrowUp v-if="trend > 0" />
            <ArrowDown v-else />
          </el-icon>
          <span>{{ Math.abs(trend) }}%</span>
        </div>
      </div>
    </div>
    
    <!-- 自定义底部内容 -->
    <div v-if="$slots.footer" class="stat-footer-wrapper">
      <slot name="footer" />
    </div>

    <!-- 背景装饰 -->
    <div class="stat-decoration"></div>
  </el-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ArrowUp, ArrowDown } from '@element-plus/icons-vue'

const props = withDefaults(defineProps<{
  label: string
  value: string | number
  icon: any
  iconColor?: string
  trend?: number
  gradient?: boolean
  variant?: 'primary' | 'success' | 'info' | 'warning' | 'danger' | 'purple' | 'pink' | 'orange' | 'cyan'
}>(), {
  variant: 'primary',
  gradient: false
})

const formattedValue = computed(() => {
  if (typeof props.value === 'number') {
    return props.value.toLocaleString()
  }
  return props.value
})

const iconWrapperStyle = computed(() => {
  if (props.gradient) {
    return {}
  }
  return props.iconColor ? { color: props.iconColor } : {}
})

const trendClass = computed(() => {
  if (!props.trend) return ''
  return props.trend > 0 ? 'trend-up' : 'trend-down'
})
</script>

<style scoped>
.stat-card {
  height: 100%;
  position: relative;
  overflow: hidden;
  border-radius: 16px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  background: var(--bg-color-light);
  border: 1px solid var(--border-color);
}

.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--box-shadow-md);
}

/* 渐变背景变体 */
.stat-card.has-gradient {
  border: none;
  color: white;
}

.stat-card.has-gradient.primary { background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%); }
.stat-card.has-gradient.success { background: linear-gradient(135deg, #10b981 0%, #059669 100%); }
.stat-card.has-gradient.info { background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%); }
.stat-card.has-gradient.warning { background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); }
.stat-card.has-gradient.danger { background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); }
.stat-card.has-gradient.purple { background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%); }
.stat-card.has-gradient.pink { background: linear-gradient(135deg, #ec4899 0%, #db2777 100%); }
.stat-card.has-gradient.orange { background: linear-gradient(135deg, #f97316 0%, #ea580c 100%); }
.stat-card.has-gradient.cyan { background: linear-gradient(135deg, #06b6d4 0%, #0891b2 100%); }

.stat-card.has-gradient .stat-value,
.stat-card.has-gradient .stat-label,
.stat-card.has-gradient .stat-trend {
  color: white;
}

.stat-content {
  position: relative;
  display: flex;
  align-items: center;
  gap: 12px;
  z-index: 1;
  padding: 16px;
}

.stat-footer-wrapper {
  padding: 0 16px 12px 16px;
  position: relative;
  z-index: 1;
}

/* 图标包装器 */
.stat-icon-wrapper {
  position: relative;
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-card:not(.has-gradient) .stat-icon-wrapper {
  background: var(--bg-color-overlay);
  color: var(--text-color-secondary);
}

/* Variant-specific icon colors for non-gradient cards */
.stat-card:not(.has-gradient).purple .stat-icon-wrapper { background: rgba(139, 92, 246, 0.1); color: #7c3aed; }
.stat-card:not(.has-gradient).cyan .stat-icon-wrapper { background: rgba(6, 182, 212, 0.1); color: #0891b2; }
.stat-card:not(.has-gradient).primary .stat-icon-wrapper { background: rgba(59, 130, 246, 0.1); color: #3b82f6; }
.stat-card:not(.has-gradient).pink .stat-icon-wrapper { background: rgba(236, 72, 153, 0.1); color: #db2777; }
.stat-card:not(.has-gradient).info .stat-icon-wrapper { background: rgba(59, 130, 246, 0.1); color: #2563eb; }
.stat-card:not(.has-gradient).success .stat-icon-wrapper { background: rgba(16, 185, 129, 0.1); color: #059669; }
.stat-card:not(.has-gradient).warning .stat-icon-wrapper { background: rgba(245, 158, 11, 0.1); color: #d97706; }
.stat-card:not(.has-gradient).orange .stat-icon-wrapper { background: rgba(249, 115, 22, 0.1); color: #ea580c; }
.stat-card:not(.has-gradient).danger .stat-icon-wrapper { background: rgba(239, 68, 68, 0.1); color: #dc2626; }

.stat-card.has-gradient .stat-icon-wrapper {
  background: rgba(255, 255, 255, 0.2);
  backdrop-filter: blur(4px);
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 20px;
  font-weight: 700;
  letter-spacing: -0.025em;
  color: var(--text-color-primary);
  margin-bottom: 2px;
  line-height: 1.2;
}

.stat-label {
  font-size: 13px;
  color: var(--text-color-secondary);
  font-weight: 500;
}

.stat-trend {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 9999px;
  margin-top: 4px;
}

/* 背景装饰图案 */
.stat-decoration {
  position: absolute;
  right: -20px;
  bottom: -20px;
  width: 140px;
  height: 140px;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.1) 0%, transparent 70%);
  border-radius: 50%;
  pointer-events: none;
  z-index: 0;
}
</style>
