<template>
  <div class="media-scraping-settings">
    <el-form v-loading="loading" label-width="140px" style="max-width: 700px">
      <el-alert
        title="TMDB配置说明"
        description="TMDB是用于识别电影资源的备选方案,配置后系统将自动使用：豆瓣 → TMDB(IMDB ID) → TMDB(搜索) 的三重识别策略。"
        type="info"
        :closable="false"
        style="margin-bottom: 20px"
      />

      <el-form-item label="TMDB API Key">
        <el-input
          v-model="tmdbApiKey"
          type="password"
          placeholder="请输入TMDB API Key"
          show-password
          clearable
        />
        <div class="form-item-tips">
          <a href="https://www.themoviedb.org/settings/api" target="_blank">
            如何获取TMDB API Key？
          </a>
          <span class="hint-text">
            （免费申请，无需付费）
          </span>
        </div>
      </el-form-item>

      <el-form-item label="TMDB代理地址">
        <el-input
          v-model="tmdbProxy"
          placeholder="http://127.0.0.1:7890（可选）"
          clearable
        />
        <div class="form-item-tips">
          如果TMDB API访问受限，可配置代理服务器
        </div>
      </el-form-item>

      <el-divider />

      <el-alert
        title="TVDB配置说明"
        description="TVDB是电视剧元数据的备选数据源，当TMDB无法获取单集信息时会自动尝试使用TVDB。"
        type="info"
        :closable="false"
        style="margin-bottom: 20px"
      />

      <el-form-item label="TVDB API Key">
        <el-input
          v-model="tvdbApiKey"
          type="password"
          placeholder="请输入TVDB API Key"
          show-password
          clearable
        />
        <div class="form-item-tips">
          <a href="https://thetvdb.com/dashboard/account/apikey" target="_blank">
            如何获取TVDB API Key？
          </a>
          <span class="hint-text">
            （需注册账号，免费使用）
          </span>
        </div>
      </el-form-item>

      <el-form-item label="TVDB PIN">
        <el-input
          v-model="tvdbPin"
          type="password"
          placeholder="订阅者PIN（可选）"
          show-password
          clearable
        />
        <div class="form-item-tips">
          订阅用户的PIN码，普通用户可留空
        </div>
      </el-form-item>

      <el-form-item label="TVDB代理地址">
        <el-input
          v-model="tvdbProxy"
          placeholder="http://127.0.0.1:7890（可选）"
          clearable
        />
        <div class="form-item-tips">
          如果TVDB API访问受限，可配置代理服务器
        </div>
      </el-form-item>

      <el-divider />

      <el-form-item label="识别优先级">
        <div class="priority-list">
          <div
            v-for="(sourceId, index) in priorityConfig.enabled_sources"
            :key="sourceId"
            class="priority-item"
          >
            <span class="priority-number">{{ index + 1 }}</span>
            <div class="priority-content">
              <div class="priority-name">{{ getSourceName(sourceId) }}</div>
              <div class="priority-desc">{{ getSourceDescription(sourceId) }}</div>
            </div>
            <div class="priority-actions">
              <el-button
                :disabled="index === 0"
                size="small"
                @click="moveUp(index)"
              >
                <el-icon><Top /></el-icon>
              </el-button>
              <el-button
                :disabled="index === priorityConfig.enabled_sources.length - 1"
                size="small"
                @click="moveDown(index)"
              >
                <el-icon><Bottom /></el-icon>
              </el-button>
            </div>
          </div>
        </div>
        <div class="form-item-tips" style="margin-top: 10px">
          优先级顺序决定了资源识别时的尝试顺序，越靠前优先级越高。建议将"本地缓存"放在首位以减少API调用。
        </div>
      </el-form-item>

      <el-divider />

      <el-form-item label="豆瓣API">
        <el-tag type="success">已配置（通过PT站点）</el-tag>
        <div class="form-item-tips">
          豆瓣API通过MTeam站点配置获取，无需单独配置
        </div>
      </el-form-item>

      <el-divider />

      <!-- 保存按钮 -->
      <el-form-item>
        <el-button type="primary" size="large" :loading="saving" @click="saveAllSettings">
          保存所有设置
        </el-button>
        <el-button :loading="testing" @click="testTMDBConnection">测试TMDB连接</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Top, Bottom } from '@element-plus/icons-vue'
import {
  getIdentificationPriority,
  updateIdentificationPriority,
  getSetting,
  upsertSetting
} from '@/api/modules/settings'

const loading = ref(false)
const saving = ref(false)
const testing = ref(false)

// TMDB 配置
const tmdbApiKey = ref('')
const tmdbProxy = ref('')

// TVDB 配置
const tvdbApiKey = ref('')
const tvdbPin = ref('')
const tvdbProxy = ref('')

// 识别优先级配置
const priorityConfig = reactive({
  enabled_sources: [] as string[]
})

// 识别源元数据
const sourceMetadata: Record<string, { name: string; description: string }> = {
  local_cache: {
    name: '本地缓存',
    description: '优先从本地数据库查找已识别的资源（基于豆瓣ID或IMDB ID）'
  },
  mteam_douban: {
    name: 'MTeam豆瓣接口',
    description: '通过MTeam站点的豆瓣接口获取详细信息（免费，准确）'
  },
  douban_api: {
    name: '豆瓣API',
    description: '通过豆瓣ID直接查询豆瓣API（需要资源已有豆瓣ID）'
  },
  douban_search: {
    name: '豆瓣搜索',
    description: '通过标题和年份搜索豆瓣（可能不准确）'
  },
  tmdb_by_imdb: {
    name: 'TMDB精确匹配',
    description: '通过IMDB ID查询TMDB（需要资源已有IMDB ID）'
  },
  tmdb_search: {
    name: 'TMDB搜索',
    description: '通过标题和年份搜索TMDB（可能不准确，最后兜底）'
  }
}

const getSourceName = (sourceId: string) => {
  return sourceMetadata[sourceId]?.name || sourceId
}

const getSourceDescription = (sourceId: string) => {
  return sourceMetadata[sourceId]?.description || ''
}

// 向上移动
const moveUp = (index: number) => {
  if (index > 0) {
    const temp = priorityConfig.enabled_sources[index]
    priorityConfig.enabled_sources[index] = priorityConfig.enabled_sources[index - 1]
    priorityConfig.enabled_sources[index - 1] = temp
  }
}

// 向下移动
const moveDown = (index: number) => {
  if (index < priorityConfig.enabled_sources.length - 1) {
    const temp = priorityConfig.enabled_sources[index]
    priorityConfig.enabled_sources[index] = priorityConfig.enabled_sources[index + 1]
    priorityConfig.enabled_sources[index + 1] = temp
  }
}

// 加载识别优先级
const loadPriorityConfig = async () => {
  try {
    const res = await getIdentificationPriority()
    if (res.data && res.data.enabled_sources) {
      priorityConfig.enabled_sources = [...res.data.enabled_sources]
    }
  } catch (error) {
    console.error('Failed to load identification priority:', error)
    ElMessage.error('加载识别优先级失败')
  }
}

// 加载TMDB设置
const loadTMDBSettings = async () => {
  try {
    // 加载 TMDB API Key
    try {
      const apiKeyRes = await getSetting('metadata_scraping', 'tmdb_api_key')
      const settingData = apiKeyRes.data?.data || apiKeyRes.data
      if (settingData && settingData.value) {
        tmdbApiKey.value = settingData.value
      }
    } catch (error: any) {
      // 404 表示设置不存在，使用默认值
      if (error.response?.status !== 404) {
        console.error('Failed to load TMDB API Key:', error)
      }
    }

    // 加载 TMDB 代理
    try {
      const proxyRes = await getSetting('metadata_scraping', 'tmdb_proxy')
      const settingData = proxyRes.data?.data || proxyRes.data
      if (settingData && settingData.value) {
        tmdbProxy.value = settingData.value
      }
    } catch (error: any) {
      // 404 表示设置不存在，使用默认值
      if (error.response?.status !== 404) {
        console.error('Failed to load TMDB proxy:', error)
      }
    }
  } catch (error) {
    console.error('Failed to load TMDB settings:', error)
  }
}

// 加载TVDB设置
const loadTVDBSettings = async () => {
  try {
    // 加载 TVDB API Key
    try {
      const apiKeyRes = await getSetting('metadata_scraping', 'tvdb_api_key')
      const settingData = apiKeyRes.data?.data || apiKeyRes.data
      if (settingData && settingData.value) {
        tvdbApiKey.value = settingData.value
      }
    } catch (error: any) {
      if (error.response?.status !== 404) {
        console.error('Failed to load TVDB API Key:', error)
      }
    }

    // 加载 TVDB PIN
    try {
      const pinRes = await getSetting('metadata_scraping', 'tvdb_pin')
      const settingData = pinRes.data?.data || pinRes.data
      if (settingData && settingData.value) {
        tvdbPin.value = settingData.value
      }
    } catch (error: any) {
      if (error.response?.status !== 404) {
        console.error('Failed to load TVDB PIN:', error)
      }
    }

    // 加载 TVDB 代理
    try {
      const proxyRes = await getSetting('metadata_scraping', 'tvdb_proxy')
      const settingData = proxyRes.data?.data || proxyRes.data
      if (settingData && settingData.value) {
        tvdbProxy.value = settingData.value
      }
    } catch (error: any) {
      if (error.response?.status !== 404) {
        console.error('Failed to load TVDB proxy:', error)
      }
    }
  } catch (error) {
    console.error('Failed to load TVDB settings:', error)
  }
}

// 保存TMDB设置
const saveTMDBSettings = async () => {
  // 保存 TMDB API Key (必填项)
  if (tmdbApiKey.value) {
    await upsertSetting(
      'metadata_scraping',
      'tmdb_api_key',
      tmdbApiKey.value,
      'TMDB API密钥，用于电影元数据识别'
    )
  }

  // 保存 TMDB 代理 (可选项)
  if (tmdbProxy.value) {
    await upsertSetting(
      'metadata_scraping',
      'tmdb_proxy',
      tmdbProxy.value,
      'TMDB API代理地址（可选）'
    )
  }
}

// 保存TVDB设置
const saveTVDBSettings = async () => {
  // 保存 TVDB API Key (可选项)
  if (tvdbApiKey.value) {
    await upsertSetting(
      'metadata_scraping',
      'tvdb_api_key',
      tvdbApiKey.value,
      'TVDB API密钥，用于电视剧元数据获取'
    )
  }

  // 保存 TVDB PIN (可选项)
  if (tvdbPin.value) {
    await upsertSetting(
      'metadata_scraping',
      'tvdb_pin',
      tvdbPin.value,
      'TVDB订阅者PIN码（可选）'
    )
  }

  // 保存 TVDB 代理 (可选项)
  if (tvdbProxy.value) {
    await upsertSetting(
      'metadata_scraping',
      'tvdb_proxy',
      tvdbProxy.value,
      'TVDB API代理地址（可选）'
    )
  }
}

// 保存所有设置(合并保存)
const saveAllSettings = async () => {
  saving.value = true
  try {
    // 串行保存所有配置（避免SQLite并发写入冲突）
    await saveTMDBSettings()
    await saveTVDBSettings()
    await updateIdentificationPriority(priorityConfig.enabled_sources)

    ElMessage.success('所有设置保存成功！')
  } catch (error: any) {
    console.error('Failed to save settings:', error)
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
    // TODO: 调用测试接口
    await new Promise(resolve => setTimeout(resolve, 2000))
    ElMessage.info('测试功能开发中，请直接保存后使用资源识别功能测试')
  } catch (error) {
    console.error('Test connection failed:', error)
    ElMessage.error('连接测试失败')
  } finally {
    testing.value = false
  }
}

onMounted(async () => {
  loading.value = true
  try {
    await Promise.all([
      loadTMDBSettings(),
      loadTVDBSettings(),
      loadPriorityConfig()
    ])
  } catch (error) {
    console.error('Failed to load settings:', error)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.media-scraping-settings {
  padding: var(--nf-spacing-lg);
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

.hint-text {
  margin-left: var(--nf-spacing-sm);
  color: var(--nf-text-secondary);
  font-size: var(--nf-font-size-mini);
}

/* 识别优先级列表样式 */
.priority-list {
  width: 100%;
  max-width: 600px;
}

.priority-item {
  display: flex;
  align-items: center;
  padding: var(--nf-spacing-md);
  margin-bottom: var(--nf-spacing-sm);
  background: var(--nf-bg-container);
  border-radius: var(--nf-radius-sm);
  border: 1px solid var(--nf-border-base);
  transition: all var(--nf-transition-base) var(--nf-ease-in-out);
}

.priority-item:hover {
  background: var(--nf-bg-overlay);
  border-color: var(--nf-primary);
}

.priority-number {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  margin-right: var(--nf-spacing-md);
  background: var(--nf-primary);
  color: white;
  border-radius: 50%;
  font-weight: var(--nf-font-weight-bold);
  font-size: var(--nf-font-size-base);
  flex-shrink: 0;
}

.priority-content {
  flex: 1;
  min-width: 0;
}

.priority-name {
  font-size: var(--nf-font-size-base);
  font-weight: var(--nf-font-weight-medium);
  color: var(--nf-text-primary);
  margin-bottom: var(--nf-spacing-xs);
}

.priority-desc {
  font-size: var(--nf-font-size-mini);
  color: var(--nf-text-secondary);
  line-height: var(--nf-line-height-base);
}

.priority-actions {
  display: flex;
  gap: var(--nf-spacing-xs);
  margin-left: var(--nf-spacing-md);
  flex-shrink: 0;
}

.priority-actions .el-button {
  padding: var(--nf-spacing-xs) var(--nf-spacing-sm);
}
</style>