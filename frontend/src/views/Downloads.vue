<template>
  <div class="page-container">
    <DownloadTaskList v-if="activeTab === 'tasks'" />
    <DownloadFileBrowser v-else-if="activeTab === 'files'" />
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import DownloadTaskList from '@/components/download/DownloadTaskList.vue'
import DownloadFileBrowser from '@/components/download/DownloadFileBrowser.vue'

const route = useRoute()
const activeTab = ref((route.query.tab as string) || 'tasks')

watch(
  () => route.query.tab,
  (newTab) => {
    if (newTab && typeof newTab === 'string') {
      activeTab.value = newTab
    } else {
       activeTab.value = 'tasks'
    }
  },
  { immediate: true }
)

onMounted(() => {
  document.title = '下载中心 - NasFusion'
})
</script>

<style scoped>
.page-container {
  width: 100%;
}
</style>
