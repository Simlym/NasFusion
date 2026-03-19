<template>
  <el-dialog v-model="dialogVisible" title="创建下载任务" width="600px" :before-close="handleClose">
    <el-form ref="formRef" :model="form" :rules="rules" label-width="120px">
      <el-form-item label="资源名称">
        <div>{{ resource?.title }}</div>
      </el-form-item>

      <el-form-item label="资源大小">
        <div>{{ formatSize(resource?.sizeBytes || 0) }}</div>
      </el-form-item>

      <el-form-item label="下载器" prop="downloader_config_id">
        <el-select
          v-model="form.downloader_config_id"
          placeholder="请选择下载器"
          style="width: 100%"
          @change="handleDownloaderChange"
        >
          <el-option
            v-for="downloader in downloaders"
            :key="downloader.id"
            :label="downloader.name"
            :value="downloader.id"
          >
            <span>{{ downloader.name }}</span>
            <el-tag
              v-if="downloader.is_default"
              type="success"
              size="small"
              style="margin-left: 10px"
            >
              默认
            </el-tag>
          </el-option>
        </el-select>
      </el-form-item>

      <el-form-item label="保存路径" prop="save_path">
        <el-select
          v-model="form.save_path"
          placeholder="请选择保存路径"
          style="width: 100%"
          allow-create
          filterable
        >
          <el-option
            v-for="mount in availablePaths"
            :key="mount.id"
            :label="mount.container_path"
            :value="mount.container_path"
          >
            <div style="display: flex; align-items: center; justify-content: space-between; width: 100%">
              <span>{{ mount.name }}</span>
              <span style="display: flex; align-items: center; gap: 8px;">
                <el-tag v-if="mount.is_same_disk" type="primary" size="small">💾 同盘</el-tag>
                <span v-if="mount.free_space" style="color: #909399; font-size: 12px">
                  剩余 {{ formatStorageSize(mount.free_space) }}
                </span>
              </span>
            </div>
          </el-option>
        </el-select>
        <div style="font-size: 12px; color: #909399; margin-top: 4px">
          {{ resource?.category ? `当前分类：${getCategoryLabel(resource.category)}` : '' }}
          <span v-if="availablePaths.find(m => m.is_same_disk)" style="color: #409EFF; margin-left: 8px">
            ✓ 有同盘下载点可用（支持硬链接）
          </span>
        </div>
      </el-form-item>

      <el-form-item label="自动整理">
        <el-switch v-model="form.auto_organize" />
        <div style="font-size: 12px; color: #909399; margin-left: 10px">下载完成后自动整理文件</div>
      </el-form-item>

      <el-form-item v-if="form.auto_organize" label="整理配置" prop="organize_config_id">
        <el-select
          v-model="form.organize_config_id"
          placeholder="请选择整理配置"
          style="width: 100%"
        >
          <el-option
            v-for="config in organizeConfigs"
            :key="config.id"
            :label="config.name"
            :value="config.id"
          >
            <span>{{ config.name }}</span>
            <el-tag
              v-if="config.is_default"
              type="success"
              size="small"
              style="margin-left: 10px"
            >
              默认
            </el-tag>
          </el-option>
        </el-select>
        <div style="font-size: 12px; color: #909399; margin-top: 4px">
          选择文件命名、NFO生成等整理规则
        </div>
      </el-form-item>

      <el-form-item v-if="form.auto_organize" label="存储位置" prop="storage_mount_id">
        <el-select
          v-model="form.storage_mount_id"
          placeholder="请选择存储位置"
          style="width: 100%"
        >
          <el-option
            v-for="mount in storageMounts"
            :key="mount.id"
            :label="`${mount.name} (${mount.container_path})`"
            :value="mount.id"
          >
            <div style="display: flex; align-items: center; justify-content: space-between; width: 100%">
              <span>{{ mount.name }}</span>
              <span style="display: flex; align-items: center; gap: 8px;">
                <el-tag v-if="mount.is_default" type="success" size="small">默认</el-tag>
                <span v-if="mount.free_space" style="color: #909399; font-size: 12px">
                  剩余 {{ formatStorageSize(mount.free_space) }}
                </span>
              </span>
            </div>
          </el-option>
        </el-select>
        <div style="font-size: 12px; color: #909399; margin-top: 4px">
          选择文件最终整理到的媒体库位置
        </div>
      </el-form-item>

      <el-form-item label="保持做种">
        <el-switch v-model="form.keep_seeding" />
      </el-form-item>

      <el-form-item v-if="resource?.hasHr" label="HR要求">
        <el-alert type="warning" :closable="false">
          <template #title>
            <div>此资源有HR要求</div>
            <div v-if="resource.hrRatio">分享率要求：{{ resource.hrRatio }}</div>
            <div v-if="resource.hrSeedTime">做种时长：{{ resource.hrSeedTime }} 小时</div>
            <div v-if="resource.hrDays">做种天数：{{ resource.hrDays }} 天</div>
          </template>
        </el-alert>
      </el-form-item>

      <el-form-item label="做种时长限制" prop="seeding_time_limit">
        <el-input-number
          v-model="form.seeding_time_limit"
          :min="0"
          placeholder="小时，0为不限制"
          style="width: 100%"
        />
        <div style="font-size: 12px; color: #909399; margin-top: 4px">设置0或留空表示不限制</div>
      </el-form-item>

      <el-form-item label="分享率限制" prop="seeding_ratio_limit">
        <el-input-number
          v-model="form.seeding_ratio_limit"
          :min="0"
          :step="0.1"
          :precision="1"
          placeholder="分享率，0为不限制"
          style="width: 100%"
        />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="handleClose">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submitForm">创建下载任务</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, watch } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import {
  getDownloaderList,
  createDownloadTask,
  type DownloaderConfig,
  type DownloadTaskCreate
} from '@/api/modules/download'
import {
  getDownloadMountsForMedia,
  getStorageMounts,
  formatSize as formatStorageSize,
  type StorageMount
} from '@/api/modules/storage'
import {
  getOrganizeConfigList,
  getDefaultOrganizeConfig,
  type OrganizeConfig
} from '@/api/modules/organize'
import type { PTResource } from '@/types/resource'
import { formatSize } from '@/utils/format'

interface Props {
  modelValue: boolean
  resource: PTResource | null
  // 统一资源信息（从媒体详情页传入）
  unifiedTableName?: string
  unifiedResourceId?: number
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'success', executionId?: number): void
}>()

const dialogVisible = ref(props.modelValue)
const submitting = ref(false)
const downloaders = ref<DownloaderConfig[]>([])
const availablePaths = ref<StorageMount[]>([])
const organizeConfigs = ref<OrganizeConfig[]>([])
const storageMounts = ref<StorageMount[]>([])

const formRef = ref<FormInstance>()
const form = reactive({
  pt_resource_id: 0,
  downloader_config_id: undefined as number | undefined,
  media_type: '',
  torrent_name: '',
  save_path: '',
  auto_organize: true,
  organize_config_id: undefined as number | undefined,
  storage_mount_id: undefined as number | undefined,
  keep_seeding: true,
  seeding_time_limit: undefined as number | undefined,
  seeding_ratio_limit: undefined as number | undefined,
  unified_table_name: undefined as string | undefined,
  unified_resource_id: undefined as number | undefined
})

const rules: FormRules = {
  downloader_config_id: [{ required: true, message: '请选择下载器', trigger: 'change' }],
  save_path: [{ required: true, message: '请选择保存路径', trigger: 'change' }]
}

// 监听props变化
watch(
  () => props.modelValue,
  (val) => {
    dialogVisible.value = val
    if (val && props.resource) {
      initForm()
    }
  }
)

watch(dialogVisible, (val) => {
  emit('update:modelValue', val)
})

// 获取分类标签
function getCategoryLabel(category: string) {
  const labels: Record<string, string> = {
    movie: '电影',
    tv: '电视剧',
    music: '音乐',
    book: '书籍',
    anime: '动漫',
    adult: '成人',
    game: '游戏',
    other: '其他'
  }
  return labels[category] || category
}

// 初始化表单
async function initForm() {
  if (!props.resource) return

  form.pt_resource_id = props.resource.id
  form.media_type = props.resource.category || 'other'
  form.torrent_name = props.resource.title || ''

  // 设置统一资源信息（如果从媒体详情页传入）
  form.unified_table_name = props.unifiedTableName
  form.unified_resource_id = props.unifiedResourceId

  // 加载下载器列表
  await loadDownloaders()

  // 加载整理配置和存储挂载点（如果启用自动整理）
  if (form.auto_organize) {
    await loadOrganizeOptions()
  }

  // 如果有HR要求，自动设置做种限制
  if (props.resource.hasHr) {
    if (props.resource.hrSeedTime) {
      form.seeding_time_limit = props.resource.hrSeedTime
    }
    if (props.resource.hrRatio) {
      form.seeding_ratio_limit = parseFloat(props.resource.hrRatio.toString())
    }
  }
}

// 加载整理配置和存储挂载点
async function loadOrganizeOptions() {
  // 优先从 unified_table_name 推断媒体类型（因为这代表实际的存储位置）
  // 否则使用 resource.category
  // 最后使用默认值
  let mediaType = 'movie' // 默认值

  if (form.unified_table_name === 'unified_movies') {
    mediaType = 'movie'
  } else if (form.unified_table_name === 'unified_tv_series') {
    mediaType = 'tv'
  } else if (form.unified_table_name === 'unified_music') {
    mediaType = 'music'
  } else if (form.unified_table_name === 'unified_books') {
    mediaType = 'book'
  } else if (form.media_type) {
    // 如果没有 unified_table_name，使用 resource.category
    mediaType = form.media_type
  }

  try {
    // 加载整理配置列表
    const configRes = await getOrganizeConfigList({
      media_type: mediaType,
      is_enabled: true
    })
    organizeConfigs.value = configRes.data.items

    // 自动选择默认配置
    const defaultConfig = organizeConfigs.value.find(c => c.is_default)
    if (defaultConfig) {
      form.organize_config_id = defaultConfig.id
    } else if (organizeConfigs.value.length > 0) {
      form.organize_config_id = organizeConfigs.value[0].id
    }

    // 加载存储挂载点（媒体库类型）
    const mountRes = await getStorageMounts({
      mount_type: 'library',
      media_category: mediaType,
      is_enabled: true
    })
    storageMounts.value = mountRes.data.items

    // 自动选择默认挂载点
    const defaultMount = storageMounts.value.find(m => m.is_default)
    if (defaultMount) {
      form.storage_mount_id = defaultMount.id
    } else if (storageMounts.value.length > 0) {
      form.storage_mount_id = storageMounts.value[0].id
    }
  } catch (error: any) {
    console.error('加载整理选项失败:', error)
    ElMessage.error('加载整理选项失败: ' + (error.message || '未知错误'))
  }
}

// 加载下载器列表
async function loadDownloaders() {
  try {
    const res = await getDownloaderList({ is_enabled: true })
    downloaders.value = res.data.items

    // 如果有默认下载器，自动选中
    const defaultDownloader = downloaders.value.find((d) => d.is_default)
    if (defaultDownloader) {
      form.downloader_config_id = defaultDownloader.id
      await loadCategoryPaths(defaultDownloader)
    } else if (downloaders.value.length > 0) {
      form.downloader_config_id = downloaders.value[0].id
      await loadCategoryPaths(downloaders.value[0])
    }
  } catch (error: any) {
    ElMessage.error('加载下载器列表失败')
  }
}

// 下载器改变时，加载对应的分类路径
async function handleDownloaderChange(downloaderId: number) {
  const downloader = downloaders.value.find((d) => d.id === downloaderId)
  if (downloader) {
    await loadCategoryPaths(downloader)
  }
}

// 加载下载挂载点（使用新的挂载点 API）
async function loadCategoryPaths(_downloader: DownloaderConfig) {
  if (!props.resource?.category) {
    availablePaths.value = []
    form.save_path = ''
    return
  }

  try {
    // 使用新的挂载点 API 获取推荐的下载目录
    const response = await getDownloadMountsForMedia({
      media_category: props.resource.category
    })
    
    const mounts = response.data?.mounts || []
    availablePaths.value = mounts
    
    // 自动选择第一个挂载点（已按同盘优先和剩余空间排序）
    if (mounts.length > 0) {
      // 优先选择同盘的挂载点（支持硬链接）
      const sameDiskMount = mounts.find((m: StorageMount) => m.is_same_disk)
      if (sameDiskMount) {
        form.save_path = sameDiskMount.container_path
      } else {
        form.save_path = mounts[0].container_path
      }
    } else {
      // 如果没有配置挂载点，使用默认路径
      form.save_path = `/app/data/downloads`
    }
  } catch (error: any) {
    console.error('加载下载挂载点失败:', error)
    // 如果加载失败，使用默认路径
    form.save_path = `/app/data/downloads`
    availablePaths.value = []
  }
}

// 提交表单
async function submitForm() {
  const valid = await formRef.value?.validate()
  if (!valid) return

  // 验证必填字段
  if (!form.downloader_config_id) {
    ElMessage.error('请选择下载器')
    return
  }

  submitting.value = true
  try {
    const taskData: DownloadTaskCreate = {
      pt_resource_id: form.pt_resource_id,
      downloader_config_id: form.downloader_config_id,
      media_type: form.media_type,
      torrent_name: form.torrent_name,
      save_path: form.save_path,
      auto_organize: form.auto_organize,
      organize_config_id: form.organize_config_id,
      storage_mount_id: form.storage_mount_id,
      keep_seeding: form.keep_seeding,
      seeding_time_limit: form.seeding_time_limit,
      seeding_ratio_limit: form.seeding_ratio_limit,
      unified_table_name: form.unified_table_name,
      unified_resource_id: form.unified_resource_id
    }

    const response = await createDownloadTask(taskData)
    ElMessage.success('下载任务已提交，正在后台处理')

    // 响应拦截器已经解包了 data
    const responseData = response.data?.data || response.data
    if (responseData?.execution_id) {
      emit('success', responseData.execution_id)
    } else {
      emit('success')
    }

    handleClose()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '创建下载任务失败')
  } finally {
    submitting.value = false
  }
}

// 关闭对话框
function handleClose() {
  dialogVisible.value = false
  formRef.value?.resetFields()
}
</script>
