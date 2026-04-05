<template>
  <div class="history-item-card" @click="handlePlay">
    <!-- 海报图展示 -->
    <div class="poster-section">
      <el-image
        v-if="history.image_url"
        :src="getMediaServerImageUrl(history.image_url, history.media_server_config_id)"
        fit="cover"
        lazy
        class="poster-image"
      >
        <template #placeholder>
          <div class="image-placeholder shimmer"></div>
        </template>
        <template #error>
          <div class="image-placeholder error">
            <el-icon><Picture /></el-icon>
          </div>
        </template>
      </el-image>
      <div v-else class="image-placeholder no-image">
        <el-icon><VideoCamera v-if="history.media_type === 'movie'" /><Monitor v-else /></el-icon>
      </div>

      <!-- 进度条 -->
      <div class="progress-overlay">
        <div class="progress-bar" :style="{ width: (history.is_completed ? 100 : history.playback_progress) + '%' }"></div>
      </div>

      <!-- 播放按钮遮罩 -->
      <div v-if="history.playback_url" class="play-mask">
        <div class="play-btn">
          <el-icon><CaretRight /></el-icon>
        </div>
      </div>

      <!-- 右上角标签 -->
      <div class="top-badges">
        <span v-if="history.is_completed" class="badge completed">已看完</span>
        <span v-else class="badge progress">{{ history.playback_progress }}%</span>
      </div>
    </div>

    <!-- 卡片底部信息 -->
    <div class="card-info">
      <h4 class="card-title" :title="displayTitle">{{ displayTitle }}</h4>
      <div class="card-meta">
        <span class="meta-left">
          <span class="server-dot" :class="history.server_type"></span>
          {{ formatLastPlayed(history.last_played_at) }}
        </span>
        <span v-if="!history.is_completed && history.play_duration_seconds" class="meta-right">
          {{ formatPlayProgress(history.play_duration_seconds, history.runtime_seconds).text }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { CaretRight } from '@element-plus/icons-vue'
import type { ViewingHistory } from '@/types/mediaServer'
import {
  formatPlayProgress,
  formatLastPlayed,
  formatEpisodeInfo
} from '@/types/mediaServer'
import { getMediaServerImageUrl } from '@/utils'

const props = defineProps<{
  history: ViewingHistory
}>()

const displayTitle = computed(() => {
  const h = props.history
  if (h.media_type !== 'movie' && (h.season_number !== null || h.episode_number !== null)) {
    return `${h.title} · ${formatEpisodeInfo(h.season_number, h.episode_number)}`
  }
  return h.title
})

const handlePlay = () => {
  if (props.history.playback_url) {
    window.open(props.history.playback_url, '_blank')
  }
}
</script>

<style scoped>
.history-item-card {
  border-radius: 10px;
  overflow: hidden;
  transition: transform 0.25s ease, box-shadow 0.25s ease;
  cursor: pointer;
  background: var(--el-bg-color);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.history-item-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
}

/* ====== 海报区域 ====== */
.poster-section {
  position: relative;
  width: 100%;
  aspect-ratio: 16/9;
  background-color: var(--el-fill-color-light);
  overflow: hidden;
}

.poster-image {
  width: 100%;
  height: 100%;
  transition: transform 0.4s ease;
}

.history-item-card:hover .poster-image {
  transform: scale(1.05);
}

.image-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32px;
  color: var(--el-text-color-placeholder);
  background: var(--el-fill-color-light);
}

.shimmer {
  background: linear-gradient(90deg, var(--el-fill-color) 25%, var(--el-fill-color-light) 50%, var(--el-fill-color) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite linear;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* ====== 进度条 ====== */
.progress-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  height: 3px;
  background: rgba(0, 0, 0, 0.15);
  z-index: 3;
}

.progress-bar {
  height: 100%;
  background: var(--el-color-primary);
  border-radius: 0 2px 2px 0;
  transition: width 0.3s ease;
}

/* ====== 右上角标签 ====== */
.top-badges {
  position: absolute;
  top: 8px;
  right: 8px;
  z-index: 4;
  display: flex;
  gap: 4px;
}

.badge {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 10px;
  backdrop-filter: blur(8px);
  line-height: 1.5;
}

.badge.completed {
  background: rgba(103, 194, 58, 0.85);
  color: #fff;
}

.badge.progress {
  background: rgba(0, 0, 0, 0.55);
  color: rgba(255, 255, 255, 0.9);
  font-variant-numeric: tabular-nums;
}

/* ====== 播放遮罩 ====== */
.play-mask {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.25s ease;
  z-index: 5;
}

.history-item-card:hover .play-mask {
  opacity: 1;
}

.play-btn {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.95);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--el-color-primary);
  font-size: 24px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.3);
  padding-left: 2px;
  transform: scale(0.85);
  transition: transform 0.25s ease;
}

.history-item-card:hover .play-btn {
  transform: scale(1);
}

.play-btn:hover {
  transform: scale(1.08);
  background: #fff;
}

/* ====== 底部信息 ====== */
.card-info {
  padding: 12px 14px 14px;
}

.card-title {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  line-height: 1.4;
  color: var(--el-text-color-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 5px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.meta-left {
  display: flex;
  align-items: center;
  gap: 5px;
}

.server-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.server-dot.jellyfin { background: #00a4dc; }
.server-dot.emby { background: #52b54b; }
.server-dot.plex { background: #e5a00d; }

.meta-right {
  color: var(--el-text-color-regular);
}

/* ====== 暗色模式 ====== */
html.dark .history-item-card {
  background: var(--el-bg-color-overlay);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.25);
}

html.dark .history-item-card:hover {
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
}

html.dark .shimmer {
  background: linear-gradient(90deg, #1e293b 25%, #334155 50%, #1e293b 75%);
  background-size: 200% 100%;
}
</style>
