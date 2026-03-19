<template>
  <div class="system-settings">
    <div class="settings-grid">
      <!-- 左列 -->
      <div class="settings-col">
        <!-- 媒体库设置 -->
        <el-card class="settings-card">
          <template #header>
            <span>媒体库设置</span>
          </template>
          <el-form label-width="160px">
            <!-- 限制级内容开关：功能保留，暂时隐藏入口，如需开放取消此注释 -->
            <el-form-item v-if="false" label="限制级内容（18+）">
              <el-switch
                v-model="showAdultContent"
                :loading="loading"
                :before-change="beforeAdultContentChange"
                @change="updateShowAdultContent"
              />
              <div class="form-item-tips">
                开启后，媒体库中将显示限制级（18+）内容
              </div>
            </el-form-item>

            <el-form-item label="电影显示动画">
              <el-switch
                v-model="movieShowAnime"
                :loading="animeSettingLoading"
                @change="handleMovieShowAnimeChange"
              />
              <div class="form-item-tips">
                开启后，电影列表中将包含动画类型（默认不显示，动画内容在"动画"分类中展示）
              </div>
            </el-form-item>

            <el-form-item label="剧集显示动画">
              <el-switch
                v-model="tvShowAnime"
                :loading="animeSettingLoading"
                @change="handleTVShowAnimeChange"
              />
              <div class="form-item-tips">
                开启后，剧集列表中将包含动画类型（默认不显示，动画内容在"动画"分类中展示）
              </div>
            </el-form-item>
          </el-form>
        </el-card>

        <!-- 首页设置 -->
        <el-card class="settings-card">
          <template #header>
            <span>首页设置</span>
          </template>
          <el-form label-width="160px">
            <el-form-item label="背景图数量">
              <el-input-number
                v-model="backdropCount"
                :min="1"
                :max="50"
                :step="1"
                :loading="backdropCountLoading"
                controls-position="right"
                style="width: 150px"
                @change="handleBackdropCountChange"
              />
              <div class="form-item-tips">
                首页 Hero 轮播背景图的显示数量，范围 1-50，默认 10
              </div>
            </el-form-item>
          </el-form>
        </el-card>
      </div>

      <!-- 右列 -->
      <div class="settings-col">
        <!-- 日志设置 -->
        <el-card class="settings-card">
          <template #header>
            <span>日志设置</span>
          </template>
          <el-form label-width="120px">
            <el-form-item label="配置文件默认">
              <div style="display: flex; align-items: center; gap: 10px;">
                <el-tag :type="getLogLevelTagType(logLevelInfo.config_level)" size="large">
                  {{ logLevelInfo.config_level }}
                </el-tag>
                <span class="level-hint">应用重启后恢复此级别</span>
              </div>
            </el-form-item>

            <el-form-item label="当前运行级别">
              <div style="display: flex; align-items: center; gap: 10px;">
                <el-select
                  v-model="currentLogLevel"
                  :loading="logLevelLoading"
                  placeholder="选择日志级别"
                  style="width: 150px"
                  @change="handleLogLevelChange"
                >
                  <el-option
                    v-for="level in logLevelInfo.available_levels"
                    :key="level"
                    :label="level"
                    :value="level"
                  >
                    <div style="display: flex; align-items: center; justify-content: space-between;">
                      <span>{{ level }}</span>
                      <el-tag
                        :type="getLogLevelTagType(level)"
                        size="small"
                        style="margin-left: 10px;"
                      >
                        {{ getLevelDescription(level) }}
                      </el-tag>
                    </div>
                  </el-option>
                </el-select>
                <el-button
                  v-if="currentLogLevel !== logLevelInfo.config_level"
                  size="small"
                  @click="resetLogLevel"
                >
                  重置为默认
                </el-button>
              </div>
              <div class="form-item-tips">
                <el-icon style="vertical-align: middle;"><Warning /></el-icon>
                此设置为临时生效，应用重启后将恢复为配置文件默认值。
                调整日志级别可用于临时排查问题，DEBUG 级别会输出更详细的日志信息。
              </div>
            </el-form-item>
          </el-form>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Warning } from '@element-plus/icons-vue'
import { useSettingsStore } from '@/stores'
import { getLogLevel, setLogLevel } from '@/api/modules/log'
import { getSetting, upsertSetting } from '@/api/modules/settings'

const settingsStore = useSettingsStore()

const loading = ref(false)
const animeSettingLoading = ref(false)

const showAdultContent = computed({
  get: () => settingsStore.showAdultContent,
  set: () => {}
})

const movieShowAnime = computed({
  get: () => settingsStore.movieShowAnime,
  set: () => {}
})

const tvShowAnime = computed({
  get: () => settingsStore.tvShowAnime,
  set: () => {}
})

// 开启前弹出年龄确认，关闭不需要确认
const beforeAdultContentChange = async (): Promise<boolean> => {
  if (settingsStore.showAdultContent) {
    // 当前已开启，直接允许关闭
    return true
  }
  try {
    await ElMessageBox.confirm(
      `<div style="font-size:12px;color:var(--el-text-color-secondary);line-height:1.8">
        <p style="margin:0 0 10px">开启前请仔细阅读以下声明：</p>
        <ul style="margin:0;padding-left:16px;display:flex;flex-direction:column;gap:4px">
          <li>您已年满 18 周岁，或符合所在地区法定成年年龄</li>
          <li>您所在的国家或地区允许访问此类限制级内容</li>
          <li>本系统仅作为个人媒体资源管理工具，不托管、不传播任何内容</li>
          <li>您将对自己访问、下载及使用相关内容的行为承担全部法律责任</li>
          <li>本系统开发者不对任何因使用限制级内容功能产生的法律纠纷负责</li>
        </ul>
        <p style="margin:10px 0 0;color:var(--el-text-color-placeholder)">继续操作即视为您已阅读并同意上述声明。</p>
      </div>`,
      '限制级内容访问声明',
      {
        confirmButtonText: '我已年满 18 周岁，同意以上声明',
        cancelButtonText: '取消',
        type: 'warning',
        confirmButtonClass: 'el-button--danger',
        dangerouslyUseHTMLString: true,
      }
    )
    return true
  } catch {
    return false
  }
}

const updateShowAdultContent = async (value: string | number | boolean) => {
  const boolValue = Boolean(value)
  loading.value = true
  try {
    await settingsStore.updateShowAdultContent(boolValue)
    ElMessage.success('设置已更新')
  } catch (error) {
    console.error('更新限制级内容显示设置失败:', error)
    ElMessage.error('更新设置失败')
  } finally {
    loading.value = false
  }
}

const handleMovieShowAnimeChange = async (value: string | number | boolean) => {
  const boolValue = Boolean(value)
  animeSettingLoading.value = true
  try {
    await settingsStore.updateMovieShowAnime(boolValue)
    ElMessage.success('设置已更新')
  } catch (error) {
    console.error('更新电影动画显示设置失败:', error)
    ElMessage.error('更新设置失败')
  } finally {
    animeSettingLoading.value = false
  }
}

const handleTVShowAnimeChange = async (value: string | number | boolean) => {
  const boolValue = Boolean(value)
  animeSettingLoading.value = true
  try {
    await settingsStore.updateTVShowAnime(boolValue)
    ElMessage.success('设置已更新')
  } catch (error) {
    console.error('更新剧集动画显示设置失败:', error)
    ElMessage.error('更新设置失败')
  } finally {
    animeSettingLoading.value = false
  }
}

// ===== 首页背景图数量设置 =====
const backdropCount = ref<number>(10)
const backdropCountLoading = ref(false)

const loadBackdropCount = async () => {
  try {
    const res = await getSetting('homepage', 'backdrop_count')
    if (res?.data?.value) {
      backdropCount.value = parseInt(res.data.value) || 10
    }
  } catch {
    backdropCount.value = 10
  }
}

const handleBackdropCountChange = async (value: number | undefined) => {
  if (value === undefined || value === null) return
  backdropCountLoading.value = true
  try {
    await upsertSetting('homepage', 'backdrop_count', String(value), '首页Hero背景图显示数量')
    ElMessage.success('设置已更新')
  } catch (error) {
    console.error('更新背景图数量失败:', error)
    ElMessage.error('更新设置失败')
  } finally {
    backdropCountLoading.value = false
  }
}

// ===== 日志级别设置 =====
const logLevelLoading = ref(false)
const currentLogLevel = ref('')
const logLevelInfo = ref({
  config_level: 'INFO',
  runtime_level: 'INFO',
  available_levels: ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
})

const loadLogLevel = async () => {
  logLevelLoading.value = true
  try {
    const res = await getLogLevel()
    if (res?.data) {
      logLevelInfo.value = res.data
      currentLogLevel.value = res.data.runtime_level
    }
  } catch (error) {
    console.error('加载日志级别失败:', error)
    ElMessage.error('加载日志级别失败')
  } finally {
    logLevelLoading.value = false
  }
}

const handleLogLevelChange = async (level: string) => {
  logLevelLoading.value = true
  try {
    const res = await setLogLevel(level)
    if (res?.data) {
      ElMessage.success(res.data.message)
      logLevelInfo.value.runtime_level = res.data.runtime_level
    }
  } catch (error: any) {
    console.error('设置日志级别失败:', error)
    ElMessage.error(error.response?.data?.detail || '设置日志级别失败')
    currentLogLevel.value = logLevelInfo.value.runtime_level
  } finally {
    logLevelLoading.value = false
  }
}

const resetLogLevel = async () => {
  currentLogLevel.value = logLevelInfo.value.config_level
  await handleLogLevelChange(logLevelInfo.value.config_level)
}

const getLogLevelTagType = (level: string) => {
  const levelMap: Record<string, any> = {
    'DEBUG': 'info',
    'INFO': 'success',
    'WARNING': 'warning',
    'ERROR': 'danger',
    'CRITICAL': 'danger'
  }
  return levelMap[level] || ''
}

const getLevelDescription = (level: string) => {
  const descMap: Record<string, string> = {
    'DEBUG': '调试',
    'INFO': '信息',
    'WARNING': '警告',
    'ERROR': '错误',
    'CRITICAL': '严重'
  }
  return descMap[level] || level
}

onMounted(() => {
  settingsStore.reloadSettings()
  loadLogLevel()
  loadBackdropCount()
})
</script>

<style scoped>
.system-settings {
  padding: var(--nf-spacing-lg);
}

.settings-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--nf-spacing-lg);
  align-items: start;
}

.settings-col {
  display: flex;
  flex-direction: column;
  gap: var(--nf-spacing-lg);
}

.form-item-tips {
  font-size: var(--nf-font-size-mini);
  color: var(--nf-text-secondary);
  margin-top: var(--nf-spacing-xs);
  line-height: var(--nf-line-height-base);
  width: 100%;
}

.level-hint {
  color: var(--nf-text-secondary);
  font-size: var(--nf-font-size-mini);
}

.settings-card {
  border-radius: var(--nf-radius-base);
}

.el-card :deep(.el-card__header) {
  background-color: var(--nf-bg-container);
  border-bottom: 1px solid var(--nf-border-base);
  color: var(--nf-text-primary);
}

@media (max-width: 768px) {
  .settings-grid {
    grid-template-columns: 1fr;
  }
}
</style>
