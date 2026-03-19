<template>
  <div class="placeholder-view">
    <el-empty :description="`${type}功能即将上线`">
      <template #image>
        <el-icon :size="80" color="var(--text-color-secondary)">
          <Box />
        </el-icon>
      </template>
      <template #default>
        <p class="placeholder-message">
          {{ type }}资源管理功能正在开发中，敬请期待...
        </p>
        <p class="placeholder-hint">
          您可以先使用"资源发现"功能浏览PT站点的原始资源
        </p>
      </template>
    </el-empty>
  </div>
</template>

<script setup lang="ts">
import { Box } from '@element-plus/icons-vue'

defineProps<{
  type: string
}>()
</script>

<style scoped>
.placeholder-view {
  padding: 60px 20px;
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 400px;
}

.placeholder-message {
  font-size: 16px;
  color: var(--text-color-regular);
  margin: 16px 0 8px 0;
}

.placeholder-hint {
  font-size: 14px;
  color: var(--text-color-secondary);
  margin: 0;
}
</style>
