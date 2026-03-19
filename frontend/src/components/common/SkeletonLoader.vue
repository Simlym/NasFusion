<template>
  <div class="skeleton-loader" :class="[variant, { animated }]">
    <!-- Card skeleton -->
    <div v-if="type === 'card'" class="skeleton-card">
      <div v-if="showImage" class="skeleton-image"></div>
      <div class="skeleton-content">
        <div class="skeleton-title"></div>
        <div class="skeleton-text"></div>
        <div class="skeleton-text short"></div>
      </div>
    </div>

    <!-- List skeleton -->
    <div v-else-if="type === 'list'" class="skeleton-list">
      <div v-for="i in count" :key="i" class="skeleton-list-item">
        <div v-if="showAvatar" class="skeleton-avatar"></div>
        <div class="skeleton-list-content">
          <div class="skeleton-title"></div>
          <div class="skeleton-text short"></div>
        </div>
      </div>
    </div>

    <!-- Table skeleton -->
    <div v-else-if="type === 'table'" class="skeleton-table">
      <div class="skeleton-table-header">
        <div v-for="i in columns" :key="i" class="skeleton-table-cell"></div>
      </div>
      <div v-for="i in rows" :key="i" class="skeleton-table-row">
        <div v-for="j in columns" :key="j" class="skeleton-table-cell"></div>
      </div>
    </div>

    <!-- Text skeleton -->
    <div v-else-if="type === 'text'" class="skeleton-text-block">
      <div v-for="i in count" :key="i" class="skeleton-text" :class="{ short: i % 3 === 0 }"></div>
    </div>

    <!-- Custom skeleton -->
    <div v-else class="skeleton-custom">
      <slot></slot>
    </div>
  </div>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    type?: 'card' | 'list' | 'table' | 'text' | 'custom'
    variant?: 'light' | 'dark'
    animated?: boolean
    showImage?: boolean
    showAvatar?: boolean
    count?: number
    rows?: number
    columns?: number
  }>(),
  {
    type: 'card',
    variant: 'light',
    animated: true,
    showImage: true,
    showAvatar: true,
    count: 3,
    rows: 5,
    columns: 4
  }
)
</script>

<style scoped>
.skeleton-loader {
  width: 100%;
}

/* ========== 基础骨架样式 ========== */
.skeleton-card,
.skeleton-list-item,
.skeleton-table,
.skeleton-text-block {
  background: var(--bg-color-light);
  border-radius: var(--border-radius-lg);
  padding: var(--spacing-md);
}

.skeleton-card {
  overflow: hidden;
}

.skeleton-image {
  width: 100%;
  height: 200px;
  background: var(--bg-color-overlay);
  border-radius: var(--border-radius-md);
  margin-bottom: var(--spacing-md);
}

.skeleton-content {
  padding: var(--spacing-sm) 0;
}

.skeleton-title {
  height: 24px;
  background: var(--bg-color-overlay);
  border-radius: var(--border-radius-sm);
  margin-bottom: var(--spacing-sm);
  width: 70%;
}

.skeleton-text {
  height: 16px;
  background: var(--bg-color-overlay);
  border-radius: var(--border-radius-sm);
  margin-bottom: var(--spacing-xs);
  width: 100%;
}

.skeleton-text.short {
  width: 60%;
}

/* ========== 列表骨架 ========== */
.skeleton-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.skeleton-list-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.skeleton-avatar {
  width: 48px;
  height: 48px;
  background: var(--bg-color-overlay);
  border-radius: 50%;
  flex-shrink: 0;
}

.skeleton-list-content {
  flex: 1;
}

/* ========== 表格骨架 ========== */
.skeleton-table {
  padding: 0;
}

.skeleton-table-header,
.skeleton-table-row {
  display: grid;
  gap: var(--spacing-md);
  padding: var(--spacing-md);
  border-bottom: 1px solid var(--border-color-light);
}

.skeleton-table-header .skeleton-table-cell {
  height: 20px;
  background: var(--bg-color-overlay);
  border-radius: var(--border-radius-sm);
}

.skeleton-table-row .skeleton-table-cell {
  height: 16px;
  background: var(--bg-color-overlay);
  border-radius: var(--border-radius-sm);
}

.skeleton-table-row:last-child {
  border-bottom: none;
}

/* ========== 文本块骨架 ========== */
.skeleton-text-block {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

/* ========== 动画效果 ========== */
.skeleton-loader.animated .skeleton-image,
.skeleton-loader.animated .skeleton-title,
.skeleton-loader.animated .skeleton-text,
.skeleton-loader.animated .skeleton-avatar,
.skeleton-loader.animated .skeleton-table-cell {
  position: relative;
  overflow: hidden;
}

.skeleton-loader.animated .skeleton-image::before,
.skeleton-loader.animated .skeleton-title::before,
.skeleton-loader.animated .skeleton-text::before,
.skeleton-loader.animated .skeleton-avatar::before,
.skeleton-loader.animated .skeleton-table-cell::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(255, 255, 255, 0.1) 50%,
    transparent 100%
  );
  animation: shimmer 2s infinite;
}

html.dark .skeleton-loader.animated .skeleton-image::before,
html.dark .skeleton-loader.animated .skeleton-title::before,
html.dark .skeleton-loader.animated .skeleton-text::before,
html.dark .skeleton-loader.animated .skeleton-avatar::before,
html.dark .skeleton-loader.animated .skeleton-table-cell::before {
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(255, 255, 255, 0.05) 50%,
    transparent 100%
  );
}

@keyframes shimmer {
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(100%);
  }
}

/* ========== 深色模式 ========== */
html.dark .skeleton-card,
html.dark .skeleton-list-item,
html.dark .skeleton-table,
html.dark .skeleton-text-block {
  background: var(--bg-color-light);
}

html.dark .skeleton-image,
html.dark .skeleton-title,
html.dark .skeleton-text,
html.dark .skeleton-avatar,
html.dark .skeleton-table-cell {
  background: var(--bg-color-overlay);
}

/* ========== 响应式 ========== */
@media (max-width: 768px) {
  .skeleton-image {
    height: 150px;
  }

  .skeleton-table-header,
  .skeleton-table-row {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
