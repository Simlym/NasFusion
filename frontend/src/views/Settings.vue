<template>
  <div class="page-container">
    <!-- Tab 内容 -->
    <div class="settings-content">
      <SystemSettings v-if="activeTab === 'system'" />
      <SitesSettings v-else-if="activeTab === 'pt-sites'" />
      <DownloaderSettings v-else-if="activeTab === 'downloaders'" />
      <MediaServerSettings v-else-if="activeTab === 'media-servers'" />
      <StorageSettings v-else-if="activeTab === 'storage'" />
      <MediaScrapingSettings v-else-if="activeTab === 'media-scraping'" />
      <NotificationManager v-else-if="activeTab === 'notifications'" />
      <!-- 兼容旧的标签名 -->
      <SitesSettings v-else-if="activeTab === 'sites'" />
      <DownloaderSettings v-else-if="activeTab === 'downloader'" />
      <OrganizeSettings v-else-if="activeTab === 'organize'" />
      <NotificationManager v-else-if="activeTab === 'notification'" />
      <MediaScrapingSettings v-else-if="activeTab === 'metadata'" />
      <SystemSettings v-else-if="activeTab === 'advanced'" />
      <UsersManagement v-else-if="activeTab === 'users' && isAdmin" />
      <MCPServerSettings v-else-if="activeTab === 'mcp-servers'" />
      <LLMSettings v-else-if="activeTab === 'llm'" />
      <LoginSecurity v-else-if="activeTab === 'login-security'" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '@/api'
import { useUserStore } from '@/stores/user'
import MediaScrapingSettings from '@/components/settings/MediaScrapingSettings.vue'
import SystemSettings from '@/components/settings/SystemSettings.vue'
import StorageSettings from '@/components/settings/StorageSettings.vue'
import LoginSecurity from '@/components/settings/LoginSecurity.vue'
import MCPServerSettings from '@/components/settings/MCPServerSettings.vue'
import LLMSettings from '@/components/settings/LLMSettings.vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

// 从路由查询参数初始化标签页，默认为 system
const activeTab = ref((route.query.tab as string) || 'system')
const isAdmin = computed(() => userStore.user?.role === 'admin')

// 标签页切换处理函数
const handleTabChange = (tabName: string) => {
  // 更新URL查询参数
  router.push({
    query: { ...route.query, tab: tabName }
  })
}

// 监听路由变化，同步标签页状态
watch(
  () => route.query.tab,
  (newTab) => {
    if (newTab && typeof newTab === 'string' && newTab !== activeTab.value) {
      activeTab.value = newTab
    }
  }
)

// TMDB设置
const metadataLoading = ref(false)
const saving = ref(false)
const testing = ref(false)
const tmdbApiKey = ref('')
const tmdbProxy = ref('')

// 加载TMDB设置
const loadTMDBSettings = async () => {
  metadataLoading.value = true
  try {
    // 加载API Key
    try {
      const apiKeyRes = await api.settings.getSetting('metadata', 'tmdb_api_key')
      if (apiKeyRes.data) {
        tmdbApiKey.value = apiKeyRes.data.value || ''
      }
    } catch (error) {
      console.log('TMDB API Key not configured')
    }

    // 加载代理设置
    try {
      const proxyRes = await api.settings.getSetting('metadata', 'tmdb_proxy')
      if (proxyRes.data) {
        tmdbProxy.value = proxyRes.data.value || ''
      }
    } catch (error) {
      console.log('TMDB proxy not configured')
    }

    ElMessage.success('加载设置成功')
  } catch (error) {
    console.error('Failed to load TMDB settings:', error)
    ElMessage.error('加载设置失败')
  } finally {
    metadataLoading.value = false
  }
}

// 保存TMDB设置
const saveTMDBSettings = async () => {
  if (!tmdbApiKey.value) {
    ElMessage.warning('请输入TMDB API Key')
    return
  }

  saving.value = true
  try {
    // 保存API Key
    await api.settings.upsertSetting(
      'metadata',
      'tmdb_api_key',
      tmdbApiKey.value,
      'TMDB API密钥，用于电影元数据识别'
    )

    // 保存代理（如果有）
    if (tmdbProxy.value) {
      await api.settings.upsertSetting(
        'metadata',
        'tmdb_proxy',
        tmdbProxy.value,
        'TMDB API代理地址（可选）'
      )
    }

    ElMessage.success('TMDB设置保存成功！现在可以使用TMDB识别资源了')
  } catch (error: any) {
    console.error('Failed to save TMDB settings:', error)
    ElMessage.error(error.response?.data?.detail || '保存设置失败')
  } finally {
    saving.value = false
  }
}

// 测试TMDB连接
const testTMDBConnection = async () => {
  if (!tmdbApiKey.value) {
    ElMessage.warning('请先输入TMDB API Key')
    return
  }

  testing.value = true
  try {
    // TODO: 调用后端测试接口
    ElMessage.info('测试功能开发中，请直接保存后使用资源识别功能测试')
  } catch (error) {
    console.error('Test connection failed:', error)
    ElMessage.error('连接测试失败')
  } finally {
    testing.value = false
  }
}

onMounted(() => {
  // 设置页面标题
  document.title = '系统设置 - NasFusion'

  // 自动加载TMDB设置（如果切换到元数据设置标签页）
  if (activeTab.value === 'metadata') {
    loadTMDBSettings()
  }
})
</script>

<style scoped>
.page-container {
  width: 100%;
}

.page-header {
  margin-bottom: var(--nf-spacing-lg);
}

.page-header h1 {
  margin: 0 0 var(--nf-spacing-sm) 0;
  font-size: var(--nf-font-size-h2);
  color: var(--nf-text-primary);
}

.page-header p {
  margin: 0;
  color: var(--nf-text-secondary);
}

h3 {
  margin: 0 0 var(--nf-spacing-lg) 0;
  font-size: var(--nf-font-size-h4);
  color: var(--nf-text-primary);
}

.form-item-tips {
  font-size: var(--nf-font-size-mini);
  color: var(--nf-text-secondary);
  margin-top: var(--nf-spacing-xs);
  line-height: var(--nf-line-height-base);
}

.form-item-tips a {
  color: var(--nf-primary);
  text-decoration: none;
}

.form-item-tips a:hover {
  color: var(--nf-primary-light);
  text-decoration: underline;
}
</style>
