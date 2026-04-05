<template>
  <div class="media-server-overview">
    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stats-row">
      <el-col v-for="stat in summaryStats" :key="stat.label" :xs="24" :sm="12" :md="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" :style="{ backgroundColor: stat.bgColor }">
              <AppIcon :name="stat.icon" :color="stat.color" :size="20" />
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stat.value }}</div>
              <div class="stat-label">{{ stat.label }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 媒体库标题 -->
    <div class="section-title">
      <h3>媒体库分布</h3>
      <div class="section-actions">
        <el-button v-if="configs.length === 1" size="small" :icon="Setting" @click="openFilterDialog(configs[0])">
          显示设置
        </el-button>
        <el-dropdown v-else-if="configs.length > 1" @command="openFilterDialogById">
          <el-button size="small" :icon="Setting">
            显示设置
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item v-for="s in configs" :key="s.id" :command="s.id">
                {{ s.name }}
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>
    
    <el-row v-if="allLibraries.length > 0" :gutter="20" class="libraries-grid">
      <el-col v-for="lib in allLibraries" :key="lib.config_id + lib.id" :xs="24" :sm="12" :md="8" :lg="6">
        <el-card shadow="hover" class="library-card" :body-style="{ padding: '0px' }" @click="handleLibraryClick(lib)">
          <div class="library-cover">
            <el-image 
              v-if="lib.image_url" 
              :src="getMediaServerImageUrl(lib.image_url, lib.config_id)" 
              fit="cover"
              lazy
              class="cover-image"
            >
              <template #placeholder>
                <div class="image-placeholder shimmer"></div>
              </template>
              <template #error>
                <div class="image-placeholder">
                  <el-icon><Collection /></el-icon>
                </div>
              </template>
            </el-image>
            <!-- 极简底栏悬浮层 -->
            <div class="library-overlay">
              <div class="overlay-info-bar">
                <div class="info-left">
                  <span class="info-item count">
                    <span class="val">{{ lib.item_count || 0 }}</span>
                    <span class="unit">项目</span>
                  </span>
                  <span class="info-divider"></span>
                  <span v-if="lib.last_scan_at" class="info-item time">
                    <el-icon><Calendar /></el-icon>
                    {{ formatDate(lib.last_scan_at) }}
                  </span>
                  <span v-else class="info-item time">未扫描</span>
                </div>
                
                <div class="info-right">
                  <el-tooltip content="扫描媒体库" placement="top">
                    <el-button 
                      type="primary" 
                      circle
                      size="small"
                      :icon="Refresh" 
                      :loading="refreshing[lib.config_id]"
                      @click.stop="handleRefresh(lib.config_id, lib.id)"
                    />
                  </el-tooltip>
                </div>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 过滤器对话框 -->
    <LibraryFilterDialog 
      ref="filterDialog" 
      :config-id="selectedConfigId"
      :config="selectedConfig"
      @updated="handleSettingsUpdated"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { Refresh, Calendar, Setting } from '@element-plus/icons-vue'
import AppIcon from '@/components/common/AppIcon.vue'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import 'dayjs/locale/zh-cn'

dayjs.extend(relativeTime)
dayjs.locale('zh-cn')
import api from '@/api'
import type { MediaServerConfig, MediaServerStats, MediaServerLibrary } from '@/types/mediaServer'
import { ElMessage } from 'element-plus'
import { getMediaServerImageUrl } from '@/utils'
import LibraryFilterDialog from './LibraryFilterDialog.vue'

const router = useRouter()

const configs = ref<MediaServerConfig[]>([])
const serverStats = ref<Record<number, MediaServerStats>>({})
const allLibraries = ref<(MediaServerLibrary & { server_name: string, config_id: number })[]>([])
const refreshing = ref<Record<number, boolean>>({})
const filterDialog = ref<any>(null)
const selectedConfigId = ref<number | undefined>(undefined)
const selectedConfig = ref<MediaServerConfig | undefined>(undefined)
const globalStats = ref({
  total_movies: 0,
  total_tvs: 0,
  total_episodes: 0,
  total_users: 0
})

const summaryStats = computed(() => [
  {
    label: '电影总数',
    value: globalStats.value.total_movies,
    icon: 'lucide:film',
    color: '#6366f1',
    bgColor: 'rgba(99, 102, 241, 0.1)'
  },
  {
    label: '剧集总数',
    value: globalStats.value.total_tvs,
    icon: 'lucide:tv',
    color: '#10b981',
    bgColor: 'rgba(16, 185, 129, 0.1)'
  },
  {
    label: '总集数',
    value: globalStats.value.total_episodes,
    icon: 'Collection',
    color: '#f59e0b',
    bgColor: 'rgba(245, 158, 11, 0.1)'
  },
  {
    label: '活跃用户',
    value: globalStats.value.total_users,
    icon: 'User',
    color: '#3b82f6',
    bgColor: 'rgba(59, 130, 246, 0.1)'
  }
])

const loadData = async () => {
  // 重置数据，防止重复累加
  allLibraries.value = []
  serverStats.value = {}
  globalStats.value = {
    total_movies: 0,
    total_tvs: 0,
    total_episodes: 0,
    total_users: 0
  }

  try {
    const res = await api.mediaServer.getMediaServerConfigs()
    configs.value = res.data
    
    // 异步加载每个服务器的统计信息和库
    configs.value.forEach(async (config) => {
      try {
        const [statsRes, libRes] = await Promise.all([
          api.mediaServer.getMediaServerStats(config.id),
          api.mediaServer.getMediaServerLibraries(config.id)
        ])
        
        serverStats.value[config.id] = statsRes.data
        
        // 合并库列表
        const libs = libRes.data.map(l => ({ 
          ...l, 
          server_name: config.name, 
          config_id: config.id 
        }))
        allLibraries.value = [...allLibraries.value, ...libs]
        
        // 累加全局统计
        globalStats.value.total_movies += statsRes.data.movie_count || 0
        globalStats.value.total_tvs += statsRes.data.tv_count || 0
        globalStats.value.total_episodes += statsRes.data.episode_count || 0
        // 用户数取最大值或合并去重（此处简化）
        globalStats.value.total_users = Math.max(globalStats.value.total_users, statsRes.data.user_count || 0)
        
      } catch (err) {
        console.error(`Failed to load stats for server ${config.id}:`, err)
      }
    })
  } catch (err) {
    ElMessage.error('获取媒体服务器配置失败')
  }
}

const handleSettingsUpdated = () => {
  loadData()
}

const handleRefresh = async (configId: number, libraryId?: string) => {
  refreshing.value[configId] = true
  try {
    await api.mediaServer.refreshMediaServerLibrary(configId, libraryId)
    ElMessage.success('刷新请求已发送')
  } catch (err) {
    ElMessage.error('刷新失败')
  } finally {
    refreshing.value[configId] = false
  }
}

const openFilterDialog = (server: MediaServerConfig) => {
  selectedConfigId.value = server.id
  selectedConfig.value = server
  nextTick(() => {
    filterDialog.value?.open()
  })
}

const openFilterDialogById = (configId: number) => {
  const server = configs.value.find(c => c.id === configId)
  if (server) openFilterDialog(server)
}

const handleLibraryClick = (lib: any) => {
  router.push({
    path: '/media-servers',
    query: { tab: 'library', config_id: lib.config_id, library_id: lib.id }
  })
}

const formatDate = (date: string) => {
  if (!date) return '-'
  return dayjs(date).fromNow()
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.media-server-overview {
  padding: 8px 24px;
}

.stats-row {
  margin-bottom: 24px;
}

.stat-card {
  border-radius: 12px;
  border: none;
  transition: all 0.3s;
}

.stat-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-color-primary);
  line-height: 1.2;
}

.stat-label {
  font-size: 13px;
  color: var(--text-color-secondary);
  margin-top: 2px;
}

.section-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 16px 0 16px;
}

.section-title h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.section-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 媒体库卡片样式 */
.libraries-grid {
  margin-bottom: 40px;
}

.library-card {
  margin-bottom: 20px;
  border-radius: 12px;
  overflow: hidden;
  cursor: pointer;
  transition: transform 0.3s, box-shadow 0.3s;
  border: none;
}

.library-card:hover {
  transform: translateY(-5px);
  box-shadow: var(--box-shadow-md);
}

.library-cover {
  position: relative;
  width: 100%;
  aspect-ratio: 16/9;
  background-color: var(--el-fill-color-light);
  overflow: hidden;
}

.cover-image {
  width: 100%;
  height: 100%;
  transition: transform 0.6s cubic-bezier(0.165, 0.84, 0.44, 1);
}

.library-card:hover .cover-image {
  transform: scale(1.1);
}

.image-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 40px;
  color: var(--el-text-color-placeholder);
}

/* 极简底栏悬浮层 */
.library-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  padding: 8px 12px;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  display: flex;
  align-items: center;
  opacity: 0;
  transform: translateY(100%);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  z-index: 2;
}

.library-card:hover .library-overlay {
  opacity: 1;
  transform: translateY(0);
}

.overlay-info-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  color: white;
}

.info-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.info-item {
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 4px;
  opacity: 0.9;
}

.info-item.count .val {
  font-weight: 700;
  color: var(--el-color-primary-light-3); /* 使用更高级的浅色主题色，在深色底栏上更协调 */
}

.info-item.count .unit {
  margin-left: 2px;
  font-size: 10px;
  opacity: 0.7;
}

.info-divider {
  width: 1px;
  height: 12px;
  background: rgba(255, 255, 255, 0.2);
}

.info-item .el-icon {
  font-size: 14px;
}

.info-right {
  display: flex;
  align-items: center;
}

.overlay-actions :deep(.el-button) {
  background: rgba(255, 255, 255, 0.15);
  border: none;
  color: white;
  padding: 6px;
}

.overlay-actions :deep(.el-button:hover) {
  background: var(--el-color-primary);
  transform: scale(1.1);
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

html.dark .library-card {
  background: var(--bg-color-overlay);
}

html.dark .shimmer {
  background: linear-gradient(90deg, #1e293b 25%, #334155 50%, #1e293b 75%);
}

html.dark .stat-card {
  background: var(--bg-color-overlay);
}
</style>
