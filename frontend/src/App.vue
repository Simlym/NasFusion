<template>
  <router-view />
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useSettingsStore } from '@/stores'
import { getToken } from '@/api/request'

// 初始化全局系统设置
const settingsStore = useSettingsStore()

onMounted(async () => {
  // 只有已登录用户才加载系统设置（避免未登录时 401 导致循环重定向）
  if (!settingsStore.initialized && getToken()) {
    await settingsStore.initSettings()
  }
})
</script>

<style>
#app {
  width: 100%;
  height: 100vh;
  margin: 0;
  padding: 0;
  background-color: var(--nf-bg-page, #1a1726);
}
</style>
