<template>
  <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑订阅' : '创建订阅'" width="800px" :before-close="handleClose">
    <el-tabs v-model="activeTab" class="subscription-tabs">
      <!-- Tab 1: 基本信息 -->
      <el-tab-pane label="基本信息" name="basic">
        <el-form ref="basicFormRef" :model="formData" :rules="basicRules" label-width="100px"
          class="tab-form compact-form">
          <!-- 标题信息 -->
          <div class="info-header">
            <el-tag :type="formData.mediaType === 'tv' ? 'success' : 'primary'" size="small">
              {{ formData.mediaType === 'tv' ? '电视剧' : '电影' }}
            </el-tag>
            <span class="info-title">{{ formData.title }}</span>
            <span v-if="formData.originalTitle" class="info-original-title">{{ formData.originalTitle }}</span>
          </div>

          <!-- 电视剧特有字段 -->
          <template v-if="formData.mediaType === 'tv'">
            <el-row :gutter="16">
              <el-col :span="8">
                <el-form-item label="订阅季度" prop="currentSeason" required>
                  <el-select v-model="formData.currentSeason" placeholder="选择季度">
                    <el-option v-for="season in availableSeasons" :key="season" :label="`第 ${season} 季`"
                      :value="season" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="总集数" prop="totalEpisodes" required>
                  <el-input-number v-model="formData.totalEpisodes" :min="1" :max="999" placeholder="本季总集数"
                    controls-position="right" />
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="起始集数" prop="startEpisode">
                  <el-input-number v-model="formData.startEpisode" :min="1" :max="999" placeholder="从第几集"
                    controls-position="right" />
                </el-form-item>
              </el-col>
            </el-row>
          </template>

          <el-form-item label="用户备注">
            <el-input v-model="formData.userNotes" type="textarea" :rows="2" placeholder="添加个人备注（可选）" />
          </el-form-item>

          <el-form-item label="收藏">
            <el-switch v-model="formData.isFavorite" />
          </el-form-item>
        </el-form>
      </el-tab-pane>

      <!-- Tab 2: 下载设置 -->
      <el-tab-pane label="下载设置" name="download">
        <el-form :model="formData" label-width="100px" class="tab-form compact-form">
          <el-form-item label="自动下载">
            <el-switch v-model="formData.autoDownload" />
            <div class="form-tip">发现匹配资源后自动提交下载</div>
          </el-form-item>
          <el-form-item v-if="formData.mediaType === 'tv'" label="追更方式">
            <el-radio-group v-model="formData.rules!.episodeTypePreference">
              <el-radio value="both">
                灵活匹配
                <el-tooltip content="同时监控单集和打包资源，哪个好下哪个" placement="top">
                  <el-icon class="info-icon">
                    <QuestionFilled />
                  </el-icon>
                </el-tooltip>
              </el-radio>
              <el-radio value="single_preferred">
                逐集追更
                <el-tooltip content="只下载单集资源，适合正在更新的剧集" placement="top">
                  <el-icon class="info-icon">
                    <QuestionFilled />
                  </el-icon>
                </el-tooltip>
              </el-radio>
              <el-radio value="season_preferred">
                季度打包
                <el-tooltip content="只下载全集打包资源，忽略单集，适合完结后订阅" placement="top">
                  <el-icon class="info-icon">
                    <QuestionFilled />
                  </el-icon>
                </el-tooltip>
              </el-radio>
            </el-radio-group>
          </el-form-item>




          <!-- <el-divider content-position="left">匹配过滤规则</el-divider> -->
          <el-row :gutter="16">
            <el-form-item label="质量优先级">
              <el-select v-model="formData.rules!.qualityPriority" multiple placeholder="从高到低选择">
                <el-option label="2160p (4K)" value="2160p" />
                <el-option label="1080p (全高清)" value="1080p" />
                <el-option label="720p (高清)" value="720p" />
                <el-option label="480p (标清)" value="480p" />
              </el-select>
              <div class="form-tip">优先匹配排在前面的质量</div>
            </el-form-item>
            <el-col :span="12">
              <el-form-item label="站点优先级">
                <el-select v-model="formData.rules!.sitePriority" multiple placeholder="所有站点（默认）"
                  :loading="sitesLoading">
                  <el-option v-for="site in ptSites" :key="site.id" :label="site.name" :value="site.id" />
                </el-select>
                <div class="form-tip">优先从指定站点下载</div>
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item label="促销要求">
            <el-select v-model="formData.rules!.promotionRequired" multiple placeholder="不限促销类型" style="width: 100%">
              <el-option label="免费 (Free)" value="free" />
              <el-option label="2X免费 (2XFree)" value="2xfree" />
              <el-option label="2X上传" value="2x" />
              <el-option label="半价 (50%)" value="50%" />
              <el-option label="三折 (30%)" value="30%" />
            </el-select>
            <div class="form-tip">只下载符合特定促销条件的资源</div>
          </el-form-item>

          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item label="最小文件">
                <el-select v-model="formData.rules!.minFileSize" placeholder="不限">
                  <el-option label="不限" :value="0" />
                  <el-option label="> 500 MB" :value="500" />
                  <el-option label="> 1 GB" :value="1024" />
                  <el-option label="> 2 GB" :value="2048" />
                  <el-option label="> 5 GB" :value="5120" />
                </el-select>
                <div class="form-tip">过滤过度压制的资源</div>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="最小做种">
                <el-input-number v-model="formData.rules!.minSeeders" :min="0" :max="9999" placeholder="0"
                  controls-position="right" />
                <div class="form-tip">确保下载速度</div>
              </el-form-item>
            </el-col>
          </el-row>
        </el-form>
      </el-tab-pane>

      <!-- Tab 3: 整理设置 -->
      <el-tab-pane label="整理设置" name="organize">
        <el-form :model="formData" label-width="100px" class="tab-form compact-form">
          <el-form-item label="自动整理">
            <el-switch v-model="formData.autoOrganize" />
            <div class="form-tip">下载完成后自动整理文件到媒体库</div>
          </el-form-item>

          <template v-if="formData.autoOrganize">
            <el-form-item label="整理配置">
              <el-select v-model="formData.organizeConfigId" placeholder="使用全局默认配置" clearable
                :loading="organizeConfigsLoading" style="width: 100%">
                <el-option v-for="cfg in organizeConfigs" :key="cfg.id"
                  :label="`${cfg.name}${cfg.is_default ? ' (默认)' : ''}`" :value="cfg.id" />
              </el-select>
              <div class="form-tip">留空使用该媒体类型的全局默认整理配置</div>
            </el-form-item>
            <el-form-item label="存储挂载点">
              <el-select v-model="formData.storageMountId" placeholder="使用全局默认挂载点" clearable
                :loading="storageMountsLoading" style="width: 100%">
                <el-option v-for="mount in storageMounts" :key="mount.id"
                  :label="`${mount.name}${mount.is_default ? ' (默认)' : ''} — ${mount.container_path}`"
                  :value="mount.id" />
              </el-select>
              <div class="form-tip">留空使用该媒体类型的全局默认媒体库挂载点</div>
            </el-form-item>

          </template>

          <!-- 整理目录覆写（仅TV，不受自动整理控制） -->
          <template v-if="formData.mediaType === 'tv'">
            <el-divider content-position="left">整理目录设置</el-divider>
            <el-row :gutter="16">
              <el-col :span="16">
                <el-form-item label="覆写目录名">
                  <el-input v-model="formData.overrideFolder" placeholder="如：仙逆 (2023)" />
                  <div class="form-tip"><strong>优先级最高</strong>，直接使用此目录名作为整理目录名字</div>
                </el-form-item>
              </el-col>
            </el-row>

            <el-row :gutter="16">
              <el-col :span="12">
                <el-form-item label="覆写标题">
                  <el-input v-model="formData.overrideTitle" placeholder="如：仙逆（而非'仙逆 年番2'）" />
                  <div class="form-tip">用于目录名字生成，留空使用原标题</div>
                </el-form-item>
              </el-col>
              <el-col :span="10">
                <el-form-item label="用于资源同步">
                  <el-switch v-model="formData.useOverrideForSync" :disabled="!formData.overrideTitle" />
                  <div class="form-tip">使用覆写标题做资源搜索</div>
                </el-form-item>
              </el-col>
            </el-row>

            <el-row :gutter="16">
              <el-col :span="12">
                <el-form-item label="覆写年份">
                  <el-input-number v-model="formData.overrideYear" :min="1900" :max="2100" placeholder="如：2023"
                    controls-position="right" />
                  <div class="form-tip">用于目录名字生成，留空使用原年份</div>
                </el-form-item>
              </el-col>

            </el-row>
          </template>
        </el-form>
      </el-tab-pane>

      <!-- Tab 4: 高级设置 -->
      <el-tab-pane label="高级设置" name="advanced">
        <el-form :model="formData" label-width="100px" class="tab-form compact-form">


          <!-- 绝对集数匹配（仅TV） -->
          <template v-if="formData.mediaType === 'tv'">
            <el-divider content-position="left">长篇动画/年番</el-divider>

            <el-row :gutter="16" align="middle">
              <el-col :span="8">
                <el-form-item label="绝对集数">
                  <el-switch v-model="useAbsoluteEpisode" />
                  <el-tooltip content="用于连续动画（年番）的匹配，不区分季度，只看集数，开启此项可增强匹配能力" placement="top">
                    <el-icon class="info-icon">
                      <QuestionFilled />
                    </el-icon>
                  </el-tooltip>
                </el-form-item>
              </el-col>
              <template v-if="useAbsoluteEpisode">
                <el-col :span="8">
                  <el-form-item label="起始集数">
                    <el-input-number v-model="formData.absoluteEpisodeStart" :min="1" :max="9999" placeholder="如：77"
                      controls-position="right" />
                  </el-form-item>
                </el-col>
                <el-col :span="8">
                  <el-form-item label="结束集数">
                    <el-input-number v-model="formData.absoluteEpisodeEnd" :min="1" :max="9999" placeholder="留空持续追更"
                      controls-position="right" />
                  </el-form-item>
                </el-col>
              </template>
            </el-row>

            <el-form-item label="关联资源">
              <el-select v-model="formData.relatedTvIds" multiple filterable remote :remote-method="handleRemoteSearch"
                placeholder="输入关键词搜索同系列的其他资源" style="width: 100%" :loading="relatedTvsLoading">
                <el-option v-for="tv in relatedTvOptions" :key="tv.id" :label="`${tv.title} (${tv.year || '未知年份'})`"
                  :value="tv.id" />
              </el-select>
              <div class="form-tip">
                关联同系列的不同版资源（如年番/季度/剧场版），匹配时会同时检查所有关联条目。
              </div>
            </el-form-item>
          </template>

        </el-form>
      </el-tab-pane>
    </el-tabs>

    <template #footer>
      <span class="dialog-footer">
        <el-button @click="handleClose">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          {{ isEdit ? '保存' : '创建订阅' }}
        </el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { QuestionFilled } from '@element-plus/icons-vue'
import { createSubscription, updateSubscription } from '@/api/modules/subscription'
import { getSiteList } from '@/api/modules/site'
import { getTVList } from '@/api/modules/tv'
import { getOrganizeConfigList, type OrganizeConfig } from '@/api/modules/organize'
import { getLibraryMountsByCategory, type StorageMount } from '@/api/modules/storage'
import {
  type SubscriptionCreateForm,
  EpisodeTypePreference
} from '@/types/subscription'
import type { PTSite } from '@/types/site'

interface Props {
  visible: boolean
  isEdit?: boolean
  editData?: any
  // 从详情页传入的预填数据
  mediaType?: 'movie' | 'tv'
  unifiedMovieId?: number
  unifiedTvId?: number
  title?: string
  originalTitle?: string
  year?: number
  posterUrl?: string
  tmdbId?: number
  imdbId?: string
  doubanId?: string
  numberOfSeasons?: number
  numberOfEpisodes?: number
}

const props = withDefaults(defineProps<Props>(), {
  visible: false,
  isEdit: false,
  mediaType: 'tv'
})

const emit = defineEmits<{
  (e: 'update:visible', value: boolean): void
  (e: 'success'): void
}>()

const dialogVisible = computed({
  get: () => props.visible,
  set: (val) => emit('update:visible', val)
})

const activeTab = ref('basic')
const basicFormRef = ref<FormInstance>()
const submitting = ref(false)
const sitesLoading = ref(false)
const ptSites = ref<PTSite[]>([])

// 整理设置相关
const organizeConfigsLoading = ref(false)
const organizeConfigs = ref<OrganizeConfig[]>([])
const storageMountsLoading = ref(false)
const storageMounts = ref<StorageMount[]>([])

// 高级设置相关
const useAbsoluteEpisode = ref(false)
const relatedTvsLoading = ref(false)
const relatedTvOptions = ref<Array<{ id: number; title: string; year?: number }>>([])

// 通用搜索方法
const searchRelatedTvs = async (keyword: string) => {
  try {
    relatedTvsLoading.value = true
    const res = await getTVList({ search: keyword, page: 1, pageSize: 50 })
    relatedTvOptions.value = (res.data.items || [])
      .filter((tv: any) => tv.id !== props.unifiedTvId) // 排除当前资源
      .map((tv: any) => ({
        id: tv.id,
        title: tv.title,
        year: tv.year
      }))
  } catch (error) {
    console.error('搜索TV资源失败:', error)
    relatedTvOptions.value = []
  } finally {
    relatedTvsLoading.value = false
  }
}

// 远程搜索处理
const handleRemoteSearch = (query: string) => {
  if (query && query.trim()) {
    searchRelatedTvs(query.trim())
  } else {
    // 恢复默认推荐
    loadRelatedTvOptions()
  }
}

// 加载关联TV资源选项（基于标题关键词搜索）
const loadRelatedTvOptions = async () => {
  if (!props.title) return

  // 智能生成搜索关键词
  let keyword = props.title.trim()

  if (keyword.includes(' ')) {
    // 包含空格，取第一部分
    const parts = keyword.split(/\s+/)
    keyword = parts[0]
    // 如果第一部分太短（<2）且有后续，加上第二部分
    if (keyword.length < 2 && parts.length > 1) {
      keyword += ' ' + parts[1]
    }
  } else {
    // 无空格
    // 纯中文且较长（>4），取前2个字作为模糊搜索
    if (keyword.length > 4 && /^[\u4e00-\u9fa5]+$/.test(keyword)) {
      keyword = keyword.substring(0, 2)
    } else {
      // 其他情况取前4个字符
      keyword = keyword.substring(0, 4)
    }
  }

  await searchRelatedTvs(keyword)
}

// 监听绝对集数开关
watch(useAbsoluteEpisode, (enabled) => {
  if (enabled && !formData.absoluteEpisodeStart) {
    // 默认使用起始集数
    formData.absoluteEpisodeStart = formData.startEpisode || 1
  }
  if (!enabled) {
    formData.absoluteEpisodeStart = undefined
    formData.absoluteEpisodeEnd = undefined
  }
})

// 初始化时如果有绝对集数设置，自动开启开关
watch(() => props.editData, (newData) => {
  if (newData?.absoluteEpisodeStart) {
    useAbsoluteEpisode.value = true
  }
}, { immediate: true })

// 可用的季度列表
const availableSeasons = computed(() => {
  const seasons: number[] = []
  const maxSeasons = props.numberOfSeasons || 10
  for (let i = 1; i <= maxSeasons; i++) {
    seasons.push(i)
  }
  return seasons
})

// 初始化表单数据
const initFormData = () => {
  return {
    mediaType: props.mediaType,
    unifiedMovieId: props.unifiedMovieId,
    unifiedTvId: props.unifiedTvId,
    title: props.title || '',
    originalTitle: props.originalTitle,
    year: props.year,
    posterUrl: props.posterUrl,
    tmdbId: props.tmdbId,
    imdbId: props.imdbId,
    doubanId: props.doubanId,
    source: 'manual',
    subscriptionType: props.mediaType === 'tv' ? 'tv_season' : 'movie_release',
    currentSeason: props.numberOfSeasons || undefined,
    startEpisode: 1,
    totalEpisodes: props.numberOfEpisodes || undefined,
    rules: {
      qualityPriority: ['2160p', '1080p'],
      sitePriority: [],
      promotionRequired: [],
      minSeeders: 0,
      minFileSize: 0,
      episodeTypePreference: EpisodeTypePreference.BOTH
    },
    autoDownload: false,
    autoOrganize: true,
    organizeConfigId: null,
    storageMountId: null,
    isFavorite: false,
    userPriority: 5
  }
}

// 表单数据
const formData = reactive<SubscriptionCreateForm>(initFormData())

// 表单验证规则
const basicRules: FormRules = {
  currentSeason: [
    { required: true, message: '请选择订阅季度', trigger: 'change' }
  ],
  startEpisode: [
    { required: true, message: '请输入起始集数', trigger: 'blur' }
  ],
  totalEpisodes: [
    { required: true, message: '请输入总集数', trigger: 'blur' }
  ]
}

// 监听 props 变化更新表单数据
watch(() => props.editData, (newData) => {
  if (newData && props.isEdit) {
    Object.assign(formData, newData)
  }
}, { immediate: true })

// 监听 visible 变化，在打开时重新初始化表单数据（非编辑模式）
watch(() => props.visible, (visible) => {
  if (visible && !props.isEdit) {
    // 重新初始化表单数据以获取最新的 props
    Object.assign(formData, initFormData())
  }
})

// 加载 PT 站点列表
const loadPTSites = async () => {
  try {
    sitesLoading.value = true
    const res = await getSiteList({ page: 1, page_size: 100 })
    // API 直接返回 PTSiteListResponse 类型
    ptSites.value = res.data.items || []
  } catch (error) {
    console.error('加载站点列表失败:', error)
    ptSites.value = []
  } finally {
    sitesLoading.value = false
  }
}

// 加载整理配置列表
const loadOrganizeConfigs = async () => {
  try {
    organizeConfigsLoading.value = true
    const mediaType = formData.mediaType || props.mediaType
    const res = await getOrganizeConfigList({ media_type: mediaType, is_enabled: true })
    organizeConfigs.value = res.data.items || []
  } catch (error) {
    console.error('加载整理配置失败:', error)
    organizeConfigs.value = []
  } finally {
    organizeConfigsLoading.value = false
  }
}

// 加载存储挂载点列表
const loadStorageMounts = async () => {
  try {
    storageMountsLoading.value = true
    const mediaType = formData.mediaType || props.mediaType
    const res = await getLibraryMountsByCategory(mediaType)
    storageMounts.value = res.data.mounts || []
  } catch (error) {
    console.error('加载存储挂载点失败:', error)
    storageMounts.value = []
  } finally {
    storageMountsLoading.value = false
  }
}

// 打开对话框时加载数据
watch(dialogVisible, (visible) => {
  if (visible) {
    loadPTSites()
    loadOrganizeConfigs()
    loadStorageMounts()
    activeTab.value = 'basic'
    // 如果是TV类型，加载关联资源选项
    if (props.mediaType === 'tv') {
      loadRelatedTvOptions()
    }
    // 重置高级设置状态
    if (!props.isEdit) {
      useAbsoluteEpisode.value = false
    }
  }
})

// 关闭对话框
const handleClose = () => {
  dialogVisible.value = false
}

// 提交表单
const handleSubmit = async () => {
  // 验证基本信息
  if (!basicFormRef.value) return
  const valid = await basicFormRef.value.validate().catch(() => false)
  if (!valid) {
    activeTab.value = 'basic'
    return
  }

  try {
    submitting.value = true

    if (props.isEdit && props.editData?.id) {
      // 更新订阅
      await updateSubscription(props.editData.id, formData)
      ElMessage.success('订阅更新成功')
    } else {
      // 创建订阅
      await createSubscription(formData)
      ElMessage.success('订阅创建成功')
    }

    emit('success')
    handleClose()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.message || '操作失败')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped lang="scss">
.subscription-tabs {
  :deep(.el-tabs__content) {
    max-height: 500px;
    overflow-y: auto;
  }
}

.tab-form {
  padding: 16px 16px 0;

  .form-tip {
    font-size: 12px;
    color: #909399;
    margin-top: 2px;
    line-height: 1.4;
  }

  .el-divider {
    margin: 8px 0 16px;
  }
}

.info-icon {
  margin-left: 4px;
  font-size: 14px;
  color: var(--el-text-color-secondary);
  vertical-align: middle;
  cursor: help;
}

.compact-form {

  // 让 select / input-number 撑满列宽
  :deep(.el-select),
  :deep(.el-input-number) {
    width: 100%;
  }

  // 缩减 form-item 之间的间距
  :deep(.el-form-item) {
    margin-bottom: 14px;
  }
}

.info-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 0 12px;
  margin-bottom: 12px;
  border-bottom: 1px solid var(--el-border-color-lighter);

  .info-title {
    font-size: 15px;
    font-weight: 600;
    color: var(--el-text-color-primary);
  }

  .info-original-title {
    font-size: 13px;
    color: var(--el-text-color-secondary);
  }
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>
