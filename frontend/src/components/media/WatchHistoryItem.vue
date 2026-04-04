<template>
  <el-card shadow="hover" class="history-item-card" :body-style="{ padding: '0px' }">
    <div class="item-container">
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
        
        <!-- 进度条悬浮在海报底部 -->
        <div class="progress-overlay">
          <div class="progress-bar" :style="{ width: (history.is_completed ? 100 : history.playback_progress) + '%' }"></div>
        </div>

        <!-- 播放按钮遮罩 (带毛玻璃效果) -->
        <div v-if="history.playback_url" class="play-mask" @click="handlePlay">
          <el-tooltip
            :content="`在 ${history.server_name || '服务器'} 中播放`"
            placement="top"
            :show-after="200"
          >
            <div class="play-btn-wrapper">
              <div class="play-btn">
                <el-icon><CaretRight /></el-icon>
              </div>
              <span class="play-text">跳转播放</span>
            </div>
          </el-tooltip>
        </div>
      </div>

      <!-- 内容详情 -->
      <div class="content-section">
        <div class="item-header">
          <div class="title-row">
            <h4 class="title" :title="history.title">{{ history.title }}</h4>
            <el-tag v-if="history.is_completed" type="success" size="small" effect="plain" class="status-tag">已看完</el-tag>
          </div>
          <p v-if="history.media_type !== 'movie' && (history.season_number !== null || history.episode_number !== null)" class="episode-info">
            {{ formatEpisodeInfo(history.season_number, history.episode_number) }}
          </p>
        </div>

        <div class="item-meta">
          <div class="meta-row">
            <el-icon><Timer /></el-icon>
            <span>{{ formatLastPlayed(history.last_played_at) }}</span>
          </div>
          <div class="meta-row progress-text">
            <span>进度: {{ history.is_completed ? '已看完' : formatPlayProgress(history.play_duration_seconds, history.runtime_seconds).text }}</span>
            <span class="percentage">{{ history.is_completed ? 100 : history.playback_progress }}%</span>
          </div>
        </div>

        <div class="item-footer">
          <div class="server-info">
            <span class="server-badge" :class="history.server_type">
              {{ history.server_name }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import {
  Timer,
  CaretRight
} from '@element-plus/icons-vue'
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

const handlePlay = () => {
  if (props.history.playback_url) {
    window.open(props.history.playback_url, '_blank')
  }
}
</script>

<style scoped>
.history-item-card {
  border-radius: 12px;
  overflow: hidden;
  border: none;
  transition: all 0.3s;
  height: 100%;
}

.history-item-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--box-shadow-md);
}

.item-container {
  display: flex;
  flex-direction: column;
  height: 100%;
}

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
  transition: transform 0.5s;
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
}

.shimmer {
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: shimmer 2s infinite linear;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.progress-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  height: 4px;
  background: rgba(0, 0, 0, 0.2);
}

.progress-bar {
  height: 100%;
  background: var(--el-color-primary);
  box-shadow: 0 0 8px var(--el-color-primary);
}

.play-mask {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(2px);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: all 0.3s ease;
  cursor: pointer;
  z-index: 10;
}

.poster-section:hover .play-mask {
  opacity: 1;
}

.play-btn-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  transform: translateY(10px);
  transition: transform 0.3s ease;
}

.poster-section:hover .play-btn-wrapper {
  transform: translateY(0);
}

.play-btn {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: var(--el-color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 32px;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.4);
  padding-left: 4px; /* 视觉对齐播放器箭头 */
}

.play-text {
  color: white;
  font-size: 13px;
  font-weight: 600;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.5);
  letter-spacing: 1px;
}

.play-btn:hover {
  transform: scale(1.1);
  background: var(--el-color-primary-light-3);
}

.content-section {
  padding: 12px;
  display: flex;
  flex-direction: column;
  flex: 1;
}

.item-header {
  margin-bottom: 12px;
}

.title-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
}

.title {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  line-height: 1.4;
  color: var(--text-color-primary);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  height: 40px; /* 两行固定高度，保持卡片对齐 */
}

.status-tag {
  flex-shrink: 0;
}

.episode-info {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--primary-color);
  font-weight: 500;
}

.item-meta {
  margin-top: auto;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.meta-row {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-color-secondary);
}

.progress-text {
  justify-content: space-between;
}

.percentage {
  font-weight: 600;
  color: var(--text-color-primary);
}

.item-footer {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid var(--border-color-light);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.server-badge {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
  background: var(--el-fill-color-light);
  color: var(--text-color-secondary);
}

.server-badge.jellyfin { border-left: 3px solid #00a4dc; }
.server-badge.emby { border-left: 3px solid #52b54b; }
.server-badge.plex { border-left: 3px solid #e5a00d; }

html.dark .history-item-card {
  background: var(--bg-color-overlay);
}

html.dark .shimmer {
  background: linear-gradient(90deg, #1e293b 25%, #334155 50%, #1e293b 75%);
}
</style>
