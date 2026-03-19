<template>
  <div class="page-container">
    <!-- 页面内容区域 -->
    <keep-alive :include="['MoviesView', 'TVSeriesView', 'AnimeView', 'AdultView']">
      <MoviesView v-if="activeTab === 'movies'" />
      <TVSeriesView v-else-if="activeTab === 'tv'" />
      <AnimeView v-else-if="activeTab === 'anime'" />
      <PlaceholderView v-else-if="activeTab === 'music'" type="音乐" />
      <PlaceholderView v-else-if="activeTab === 'books'" type="电子书" />
      <AdultView v-else-if="activeTab === 'adult'" />
    </keep-alive>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, defineOptions } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import MoviesView from './Movies.vue'
import TVSeriesView from './TVSeries.vue'
import AnimeView from './Anime.vue'
import AdultView from './Adult.vue'
import PlaceholderView from '@/components/media/PlaceholderView.vue'

// 定义组件名称，用于 keep-alive 缓存
defineOptions({
  name: 'MediaLibrary'
})

const router = useRouter()
const route = useRoute()

// 初始化时从路由查询参数读取页签，默认为 movies
const activeTab = ref((route.query.tab as string) || 'movies')

// 监听路由变化，同步更新 activeTab（仅在值变化时更新，避免冗余）
watch(
  () => route.query.tab,
  (newTab) => {
    if (newTab && typeof newTab === 'string' && newTab !== activeTab.value) {
      activeTab.value = newTab
    }
  }
)
</script>

<style scoped>
.page-container {
  width: 100%;
  height: 100%;
}
</style>
