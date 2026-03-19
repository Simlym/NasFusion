<template>
  <div class="media-servers-page">
    <!-- 根据路由参数显示对应组件 -->
    <MediaServerOverview v-if="activeTab === 'overview'" />
    <WatchHistory v-else-if="activeTab === 'history'" />
    <MediaLibrary v-else-if="activeTab === 'library'" />
    <!-- 默认显示概览 -->
    <MediaServerOverview v-else />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import MediaServerOverview from '@/components/media/MediaServerOverview.vue'
import WatchHistory from '@/components/media/WatchHistory.vue'
import MediaLibrary from '@/components/media/MediaLibrary.vue'

defineOptions({
  name: 'MediaServers'
})

const route = useRoute()

// 从路由查询参数读取页签，默认为 overview
const activeTab = computed(() => (route.query.tab as string) || 'overview')
</script>

<style scoped>
.media-servers-page {
  width: 100%;
  height: 100%;
}
</style>

