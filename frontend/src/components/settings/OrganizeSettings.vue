<template>
  <div class="settings-section">
    <h3>整理配置管理</h3>
    <p class="section-description">管理媒体文件整理规则和模板</p>

    <div class="toolbar">
      <el-button :icon="Setting" :loading="initializing" @click="handleInitDefaults">
        初始化默认配置
      </el-button>
      <el-button type="primary" :icon="Plus" @click="handleCreate">添加配置</el-button>
    </div>

    <!-- 过滤器 -->
    <div class="filter-container">
      <el-select
        v-model="filters.media_type"
        placeholder="媒体类型"
        clearable
        style="width: 200px"
        @change="loadConfigs"
      >
        <el-option label="全部" value="" />
        <el-option label="电影" value="movie" />
        <el-option label="电视剧" value="tv" />
        <el-option label="动漫" value="anime" />
      </el-select>
      <el-select
        v-model="filters.is_enabled"
        placeholder="状态"
        clearable
        style="width: 200px"
        @change="loadConfigs"
      >
        <el-option label="全部" :value="undefined" />
        <el-option label="已启用" :value="true" />
        <el-option label="已禁用" :value="false" />
      </el-select>
    </div>

    <!-- 配置列表 -->
    <el-table v-loading="loading" :data="configs" style="width: 100%">
      <el-table-column prop="name" label="配置名称" min-width="130" />
      <el-table-column label="媒体类型" width="100">
        <template #default="{ row }">
          <el-tag>{{ MediaTypeLabels[row.media_type] || row.media_type }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="dir_template" label="目录模板" min-width="200" show-overflow-tooltip />
      <el-table-column prop="filename_template" label="文件名模板" min-width="200" show-overflow-tooltip />
      <el-table-column label="整理模式" width="180">
        <template #default="{ row }">
          <span style="white-space: nowrap">{{ OrganizeModeLabels[row.organize_mode] || row.organize_mode }}</span>
        </template>
      </el-table-column>
      <el-table-column label="生成NFO" width="90">
        <template #default="{ row }">
          <el-tag v-if="row.generate_nfo" type="success" size="small">是</el-tag>
          <el-tag v-else type="info" size="small">否</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="80">
        <template #default="{ row }">
          <el-tag v-if="row.is_enabled" type="success" size="small">启用</el-tag>
          <el-tag v-else type="info" size="small">禁用</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="默认" width="70">
        <template #default="{ row }">
          <el-tag v-if="row.is_default" type="primary" size="small">是</el-tag>
          <el-tag v-else type="info" size="small">否</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="120" fixed="right">
        <template #default="{ row }">
          <el-button link type="warning" size="small" @click="handleEdit(row)">编辑</el-button>
          <el-button
            link
            type="danger"
            size="small"
            :disabled="row.is_default"
            @click="handleDelete(row)"
          >
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 空状态 -->
    <el-empty
      v-if="!loading && configs.length === 0"
      description="暂无配置数据"
      style="margin-top: 20px"
    />

    <!-- 分页 -->
    <el-pagination
      v-if="pagination.total > 0"
      v-model:current-page="pagination.page"
      v-model:page-size="pagination.size"
      class="pagination"
      :total="pagination.total"
      :page-sizes="[10, 20, 50]"
      layout="total, sizes, prev, pager, next, jumper"
      @current-change="loadConfigs"
      @size-change="loadConfigs"
    />

    <!-- 创建/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogMode === 'create' ? '添加配置' : '编辑配置'"
      width="900px"
      @close="handleDialogClose"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="140px">
        <el-tabs v-model="activeTab">
          <el-tab-pane label="基本信息" name="basic">
            <el-form-item label="配置名称" prop="name">
              <el-input v-model="form.name" placeholder="例如: 电影默认配置" />
            </el-form-item>
            <el-form-item label="媒体类型" prop="media_type">
              <el-select v-model="form.media_type" placeholder="请选择媒体类型">
                <el-option label="电影" value="movie" />
                <el-option label="电视剧" value="tv" />
                <el-option label="动漫" value="anime" />
              </el-select>
              <el-text size="small" type="info" style="display: block; margin-top: 5px">
                整理时将使用此媒体类型对应的存储挂载点，优先选择同盘挂载点。
                <el-link type="primary" @click="$router.push('/settings?tab=storage')">前往存储配置 →</el-link>
              </el-text>
            </el-form-item>
            <el-form-item label="是否启用" prop="is_enabled">
              <el-switch v-model="form.is_enabled" />
            </el-form-item>
          </el-tab-pane>

          <el-tab-pane label="目录和文件名" name="template">
            <el-form-item label="目录模板" prop="dir_template">
              <el-input
                v-model="form.dir_template"
                placeholder="电影: {title} ({year}) | 剧集: {title} ({year})/Season {season}"
                clearable
              />
              <el-text size="small" type="info" style="display: block">
                电影可用: {title}(标题), {year}(年份), {resolution}(分辨率)
              </el-text>
              <el-text size="small" type="info" style="display: block">
                剧集可用: {title}, {year}, {season}(季度，不补零), {season:02d}(季度，补零)
              </el-text>
              <el-text size="small" type="info" style="display: block">
                成人可用: {title}, {product_number}(番号), {year}, {maker}(片商), {actress}(演员), {resolution}
              </el-text>
            </el-form-item>
            <el-form-item label="文件名模板" prop="filename_template">
              <el-input
                v-model="form.filename_template"
                placeholder="电影: {title} ({year}) | 剧集: {title} - S{season:02d}E{episode:02d} - {episode_title}"
                clearable
              />
              <el-text size="small" type="info" style="display: block">
                电影可用: {title}, {year}, {resolution}, {video_codec}, {audio_codec}
              </el-text>
              <el-text size="small" type="info" style="display: block">
                剧集可用: {title}, {season:02d}, {episode:02d}, {episode_title}(集标题)
              </el-text>
              <el-text size="small" type="info" style="display: block">
                成人可用: {title}, {product_number}(番号), {year}, {maker}(片商), {actress}(演员)
              </el-text>
            </el-form-item>
          </el-tab-pane>

          <el-tab-pane label="整理选项" name="organize">
            <el-form-item label="整理模式" prop="organize_mode">
              <el-select v-model="form.organize_mode">
                <el-option label="硬链接（推荐）" value="hardlink" />
                <el-option label="Reflink（Btrfs推荐）" value="reflink" />
                <el-option label="软链接" value="symlink" />
                <el-option label="移动文件" value="move" />
                <el-option label="复制文件" value="copy" />
              </el-select>
              <el-text size="small" type="info" style="display: block; margin-top: 5px">
                硬链接：不占用额外空间，原文件和目标文件独立；Reflink：适用于Btrfs文件系统，可跨共享目录且节省空间；软链接：类似快捷方式
              </el-text>
            </el-form-item>
            <el-form-item label="覆盖已存在文件">
              <el-switch v-model="form.overwrite_existing" />
            </el-form-item>
            <el-form-item label="自动重命名">
              <el-switch v-model="form.auto_rename" />
              <el-text size="small" type="info" style="margin-left: 10px">
                如果文件已存在，自动添加序号
              </el-text>
            </el-form-item>
          </el-tab-pane>

          <el-tab-pane label="NFO和图片" name="metadata">
            <el-form-item label="生成NFO文件" prop="generate_nfo">
              <el-switch v-model="form.generate_nfo" />
            </el-form-item>
            <el-form-item v-if="form.generate_nfo" label="NFO格式" prop="nfo_format">
              <el-select v-model="form.nfo_format">
                <el-option label="Jellyfin" value="jellyfin" />
                <el-option label="Emby" value="emby" />
                <el-option label="Plex" value="plex" />
                <el-option label="Kodi" value="kodi" />
              </el-select>
            </el-form-item>
            <el-form-item label="下载海报">
              <el-switch v-model="form.download_poster" />
            </el-form-item>
            <el-form-item label="下载背景图">
              <el-switch v-model="form.download_backdrop" />
            </el-form-item>
            <el-form-item label="下载演员图片">
              <el-switch v-model="form.download_actor_images" />
            </el-form-item>
          </el-tab-pane>

          <el-tab-pane label="Jellyfin集成" name="jellyfin">
            <el-form-item label="同步到Jellyfin">
              <el-switch v-model="form.jellyfin_sync_enabled" />
            </el-form-item>
            <el-form-item v-if="form.jellyfin_sync_enabled" label="Jellyfin库ID">
              <el-input v-model="form.jellyfin_library_id" placeholder="留空则使用全局配置" />
            </el-form-item>
          </el-tab-pane>
        </el-tabs>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          {{ dialogMode === 'create' ? '创建' : '保存' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Edit, Delete, Setting } from '@element-plus/icons-vue'
import type { FormInstance, FormRules } from 'element-plus'
import type {
  OrganizeConfig,
  OrganizeConfigCreate,
  OrganizeConfigUpdate
} from '@/types/organize'
import {
  getOrganizeConfigList,
  createOrganizeConfig,
  updateOrganizeConfig,
  deleteOrganizeConfig,
  initDefaultConfigs,
  OrganizeModeLabels,
  MediaTypeLabels
} from '@/api/modules/organize'

const loading = ref(false)
const initializing = ref(false)
const submitting = ref(false)
const configs = ref<OrganizeConfig[]>([])
const dialogVisible = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const activeTab = ref('basic')
const formRef = ref<FormInstance>()

const filters = reactive({
  media_type: '',
  is_enabled: undefined as boolean | undefined
})

const pagination = reactive({
  page: 1,
  size: 20,
  total: 0
})

const defaultForm: OrganizeConfigCreate = {
  name: '',
  media_type: 'movie',
  library_root: '',
  dir_template: '',
  filename_template: '',
  season_folder_template: '',
  organize_mode: 'hardlink',
  overwrite_existing: false,
  auto_rename: true,
  generate_nfo: true,
  nfo_format: 'jellyfin',
  download_poster: true,
  download_backdrop: true,
  download_actor_images: false,
  jellyfin_sync_enabled: false,
  jellyfin_library_id: '',
  is_enabled: true
}

const form = reactive<OrganizeConfigCreate & { id?: number }>({ ...defaultForm })

const rules: FormRules = {
  name: [
    { required: true, message: '请输入配置名称', trigger: 'blur' },
    { min: 2, max: 200, message: '长度在 2 到 200 个字符', trigger: 'blur' }
  ],
  media_type: [{ required: true, message: '请选择媒体类型', trigger: 'change' }],
  dir_template: [{ required: true, message: '请输入目录模板', trigger: 'blur' }],
  filename_template: [{ required: true, message: '请输入文件名模板', trigger: 'blur' }],
  organize_mode: [{ required: true, message: '请选择整理模式', trigger: 'change' }]
}

onMounted(() => {
  loadConfigs()
})

async function loadConfigs() {
  loading.value = true
  try {
    const res = await getOrganizeConfigList({
      skip: (pagination.page - 1) * pagination.size,
      limit: pagination.size,
      media_type: filters.media_type || undefined,
      is_enabled: filters.is_enabled
    })
    configs.value = res.data.items
    pagination.total = res.data.total
  } catch (error: any) {
    ElMessage.error(error.message || '加载配置列表失败')
  } finally {
    loading.value = false
  }
}

async function handleInitDefaults() {
  try {
    await ElMessageBox.confirm(
      '将创建默认的电影、电视剧和动漫整理配置。已存在的默认配置不会被覆盖。',
      '初始化默认配置',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'info'
      }
    )
    initializing.value = true
    await initDefaultConfigs()
    ElMessage.success('默认配置初始化成功')
    loadConfigs()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '初始化失败')
    }
  } finally {
    initializing.value = false
  }
}

function handleCreate() {
  dialogMode.value = 'create'
  Object.assign(form, defaultForm)
  dialogVisible.value = true
  activeTab.value = 'basic'
}

function handleEdit(row: OrganizeConfig) {
  dialogMode.value = 'edit'
  Object.assign(form, {
    id: row.id,
    name: row.name,
    media_type: row.media_type,
    library_root: row.library_root,
    dir_template: row.dir_template,
    filename_template: row.filename_template,
    season_folder_template: row.season_folder_template || '',
    organize_mode: row.organize_mode,
    overwrite_existing: row.overwrite_existing,
    auto_rename: row.auto_rename,
    generate_nfo: row.generate_nfo,
    nfo_format: row.nfo_format,
    download_poster: row.download_poster,
    download_backdrop: row.download_backdrop,
    download_actor_images: row.download_actor_images,
    jellyfin_sync_enabled: row.jellyfin_sync_enabled,
    jellyfin_library_id: row.jellyfin_library_id || '',
    is_enabled: row.is_enabled
  })
  dialogVisible.value = true
  activeTab.value = 'basic'
}

async function handleSubmit() {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (!valid) return

    submitting.value = true
    try {
      if (dialogMode.value === 'create') {
        await createOrganizeConfig(form as OrganizeConfigCreate)
        ElMessage.success('创建成功')
      } else {
        const { id, ...updateData } = form
        await updateOrganizeConfig(id!, updateData as OrganizeConfigUpdate)
        ElMessage.success('更新成功')
      }
      dialogVisible.value = false
      loadConfigs()
    } catch (error: any) {
      ElMessage.error(error.message || '操作失败')
    } finally {
      submitting.value = false
    }
  })
}

async function handleDelete(row: OrganizeConfig) {
  try {
    await ElMessageBox.confirm(`确定删除配置 "${row.name}" 吗？`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await deleteOrganizeConfig(row.id)
    ElMessage.success('删除成功')
    loadConfigs()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '删除失败')
    }
  }
}

function handleDialogClose() {
  formRef.value?.resetFields()
}
</script>

<style scoped>
.settings-section {
  padding: 20px;
}

h3 {
  margin: 0 0 8px 0;
  font-size: 18px;
  font-weight: 600;
}

.section-description {
  margin: 0 0 20px 0;
  color: var(--text-color-secondary);
  font-size: 14px;
}

.toolbar {
  margin-bottom: 16px;
  display: flex;
  gap: 10px;
}

.filter-container {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>
