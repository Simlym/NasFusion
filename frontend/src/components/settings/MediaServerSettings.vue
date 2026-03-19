<template>
  <div class="settings-section">
    <div class="section-header">
      <div>
        <h3>媒体服务器</h3>
        <p class="section-description">
          管理 Jellyfin/Emby/Plex 连接，自动刷新媒体库和同步观看历史
        </p>
      </div>
      <el-button type="primary" :icon="Plus" @click="showAddDialog">添加媒体服务器</el-button>
    </div>

    <el-table v-loading="loading" :data="configs" style="width: 100%">
      <el-table-column prop="name" label="名称" width="150" />
      <el-table-column label="类型" width="120">
        <template #default="{ row }">
          <el-tag>{{ MediaServerTypeLabels[row.type] }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="连接地址" min-width="250">
        <template #default="{ row }">
          {{ getServerBaseUrl(row) }}
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="MediaServerStatusTypes[row.status]">
            {{ MediaServerStatusLabels[row.status] }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="功能" width="150">
        <template #default="{ row }">
          <div style="display: flex; gap: 5px">
            <el-tooltip content="自动刷新媒体库" placement="top">
              <el-icon v-if="row.auto_refresh_library" color="#67c23a" :size="16">
                <Check />
              </el-icon>
            </el-tooltip>
            <el-tooltip content="同步观看历史" placement="top">
              <el-icon v-if="row.sync_watch_history" color="#409eff" :size="16">
                <View />
              </el-icon>
            </el-tooltip>
            <el-tag v-if="row.is_default" type="success" size="small">默认</el-tag>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="最后同步" width="150">
        <template #default="{ row }">
          <span v-if="row.last_sync_at" style="font-size: 12px; color: #909399">
            {{ formatLastPlayed(row.last_sync_at) }}
          </span>
          <span v-else style="color: #c0c4cc">未同步</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="280" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click="testConnection(row.id)">
            测试连接
          </el-button>
          <el-button link type="success" size="small" @click="syncHistory(row.id)">
            同步历史
          </el-button>
          <el-button link type="warning" size="small" @click="showEditDialog(row)">
            编辑
          </el-button>
          <el-button link type="danger" size="small" @click="deleteConfig(row.id)">
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 空状态 -->
    <el-empty
      v-if="!loading && configs.length === 0"
      description="暂无媒体服务器配置"
      style="margin-top: 20px"
    >
      <el-button type="primary" @click="showAddDialog">添加第一个媒体服务器</el-button>
    </el-empty>

    <!-- 添加/编辑对话框 -->
    <el-dialog
      v-model="formDialogVisible"
      :title="isEdit ? '编辑媒体服务器' : '添加媒体服务器'"
      width="700px"
    >
      <el-tabs v-model="activeTabName">
        <!-- 基础配置 -->
        <el-tab-pane label="基础配置" name="basic">
          <el-form ref="formRef" :model="form" :rules="rules" label-width="140px">
            <el-form-item label="服务器类型" prop="type">
              <el-select
                v-model="form.type"
                placeholder="请选择"
                :disabled="isEdit"
                @change="onTypeChange"
              >
                <el-option label="Jellyfin" value="jellyfin" />
                <el-option label="Emby" value="emby" disabled>
                  <span>Emby</span>
                  <el-tag size="small" type="info" style="margin-left: 10px">待支持</el-tag>
                </el-option>
                <el-option label="Plex" value="plex" disabled>
                  <span>Plex</span>
                  <el-tag size="small" type="info" style="margin-left: 10px">待支持</el-tag>
                </el-option>
              </el-select>
              <div class="form-item-tips">
                当前支持 Jellyfin，Emby 和 Plex 将在后续版本支持
              </div>
            </el-form-item>

            <el-form-item label="配置名称" prop="name">
              <el-input v-model="form.name" placeholder="如：家庭Jellyfin服务器" />
            </el-form-item>

            <el-form-item label="主机地址" prop="host">
              <el-input v-model="form.host" placeholder="localhost 或 IP地址" />
            </el-form-item>

            <el-form-item label="端口" prop="port">
              <el-input-number v-model="form.port" :min="1" :max="65535" />
            </el-form-item>

            <el-form-item label="使用SSL">
              <el-switch v-model="form.use_ssl" />
              <div class="form-item-tips">启用后将使用 HTTPS 协议连接</div>
            </el-form-item>

            <!-- Jellyfin/Emby 使用 API Key -->
            <el-form-item
              v-if="form.type === 'jellyfin' || form.type === 'emby'"
              label="API Key"
              prop="api_key"
            >
              <el-input
                v-model="form.api_key"
                type="password"
                :placeholder="
                  isEdit && currentEditConfig?.has_api_key
                    ? '已保存（留空则不修改）'
                    : 'Jellyfin/Emby API密钥'
                "
                show-password
              />
              <el-text v-if="isEdit && currentEditConfig?.has_api_key" type="success" size="small">
                ✓ API Key 已保存，留空则保持不变
              </el-text>
              <div class="form-item-tips">
                在 Jellyfin 控制台 → 管理 → API密钥 中创建
              </div>
            </el-form-item>

            <!-- Plex 使用 Token -->
            <el-form-item v-if="form.type === 'plex'" label="访问令牌" prop="token">
              <el-input
                v-model="form.token"
                type="password"
                :placeholder="
                  isEdit && currentEditConfig?.has_token
                    ? '已保存（留空则不修改）'
                    : 'Plex 访问令牌'
                "
                show-password
              />
              <el-text v-if="isEdit && currentEditConfig?.has_token" type="success" size="small">
                ✓ Token 已保存，留空则保持不变
              </el-text>
              <div class="form-item-tips">
                访问
                <a
                  href="https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/"
                  target="_blank"
                  >Plex 官方文档</a
                >
                获取令牌
              </div>
            </el-form-item>

            <el-form-item label="设为默认">
              <el-switch v-model="form.is_default" />
              <div class="form-item-tips">默认服务器将优先用于自动操作</div>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- 功能配置 -->
        <el-tab-pane label="功能配置" name="features">
          <el-form :model="form" label-width="180px">
            <el-form-item label="文件整理后自动刷新">
              <el-switch v-model="form.auto_refresh_library" />
              <div class="form-item-tips">
                媒体文件整理完成后，自动通知媒体服务器刷新媒体库
              </div>
            </el-form-item>

            <el-form-item label="同步观看历史">
              <el-switch v-model="form.sync_watch_history" />
              <div class="form-item-tips">
                定期从媒体服务器同步观看记录，用于 AI 推荐功能
              </div>
            </el-form-item>

            <el-form-item
              v-if="form.sync_watch_history"
              label="同步间隔（分钟）"
              prop="watch_history_sync_interval"
            >
              <el-input-number v-model="form.watch_history_sync_interval" :min="10" :max="1440" />
              <div class="form-item-tips">建议设置为 60 分钟，最短 10 分钟</div>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- 高级配置 -->
        <el-tab-pane label="高级配置" name="advanced">
          <el-form :model="form" label-width="180px">
            <el-form-item label="服务器用户ID">
              <el-input
                v-model="serverUserId"
                placeholder="留空则使用管理员账户"
                clearable
              />
              <div class="form-item-tips">
                用于同步观看历史的服务器用户ID，可在媒体服务器用户设置中查看
              </div>
            </el-form-item>

            <el-form-item label="路径映射">
              <el-button size="small" @click="addPathMapping">添加映射</el-button>
              <div class="form-item-tips" style="margin-bottom: 10px">
                如果媒体服务器和 NasFusion 的文件路径不同，需要配置路径映射
              </div>
              <div
                v-for="(mapping, index) in pathMappings"
                :key="index"
                style="display: flex; gap: 10px; margin-bottom: 10px"
              >
                <el-input
                  v-model="mapping.server_path"
                  placeholder="服务器路径 (如: /media)"
                  style="flex: 1"
                />
                <el-input
                  v-model="mapping.local_path"
                  placeholder="本地路径 (如: D:/media)"
                  style="flex: 1"
                />
                <el-button type="danger" :icon="Delete" @click="removePathMapping(index)" />
              </div>
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>

      <template #footer>
        <el-button @click="formDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitForm">
          {{ isEdit ? '更新' : '创建' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { Plus, Delete, Check, View } from '@element-plus/icons-vue'
import api from '@/api'
import {
  MediaServerType,
  MediaServerTypeLabels,
  MediaServerStatusLabels,
  MediaServerStatusTypes,
  MediaServerDefaultPorts,
  getServerBaseUrl,
  formatLastPlayed,
  validateServerConfig,
  type MediaServerConfig,
  type MediaServerConfigCreate
} from '@/types/mediaServer'

const formDialogVisible = ref(false)
const activeTabName = ref('basic')
const loading = ref(false)
const submitting = ref(false)
const isEdit = ref(false)
const editId = ref<number>()
const currentEditConfig = ref<MediaServerConfig | null>(null)

const configs = ref<MediaServerConfig[]>([])

const formRef = ref<FormInstance>()
const form = reactive<MediaServerConfigCreate>({
  type: MediaServerType.JELLYFIN,
  name: '',
  host: 'localhost',
  port: 8096,
  use_ssl: false,
  api_key: '',
  token: '',
  is_default: false,
  auto_refresh_library: true,
  sync_watch_history: true,
  watch_history_sync_interval: 60,
  library_path_mappings: []
})

// 服务器用户ID（存储在 server_config 中）
const serverUserId = ref('')

// 路径映射
const pathMappings = ref<Array<{ server_path: string; local_path: string }>>([])

const rules: FormRules = {
  type: [{ required: true, message: '请选择服务器类型', trigger: 'change' }],
  name: [{ required: true, message: '请输入配置名称', trigger: 'blur' }],
  host: [{ required: true, message: '请输入主机地址', trigger: 'blur' }],
  port: [{ required: true, message: '请输入端口号', trigger: 'blur' }],
  api_key: [
    {
      trigger: 'blur',
      validator: (rule: any, value: any, callback: any) => {
        // 编辑模式下，如果已有 API Key，则允许为空
        if (isEdit.value && currentEditConfig.value?.has_api_key && !value) {
          callback()
          return
        }
        // 创建模式或没有已保存的 API Key 时，必须填写
        if (
          (form.type === MediaServerType.JELLYFIN || form.type === MediaServerType.EMBY) &&
          !value
        ) {
          callback(new Error('请输入 API Key'))
        } else {
          callback()
        }
      }
    }
  ],
  token: [
    {
      trigger: 'blur',
      validator: (rule: any, value: any, callback: any) => {
        // 编辑模式下，如果已有 Token，则允许为空
        if (isEdit.value && currentEditConfig.value?.has_token && !value) {
          callback()
          return
        }
        // 创建模式或没有已保存的 Token 时，必须填写
        if (form.type === MediaServerType.PLEX && !value) {
          callback(new Error('请输入访问令牌'))
        } else {
          callback()
        }
      }
    }
  ],
  watch_history_sync_interval: [
    { required: true, message: '请输入同步间隔', trigger: 'blur' },
    {
      type: 'number',
      min: 10,
      max: 1440,
      message: '同步间隔必须在 10-1440 分钟之间',
      trigger: 'blur'
    }
  ]
}

// 加载配置列表
const loadConfigs = async () => {
  loading.value = true
  try {
    const res = await api.mediaServer.getMediaServerConfigs()
    configs.value = res.data
  } catch (error: any) {
    console.error('Failed to load configs:', error)
    ElMessage.error(error.response?.data?.detail || '加载配置失败')
  } finally {
    loading.value = false
  }
}

// 服务器类型变更
const onTypeChange = (type: MediaServerType) => {
  // 自动更新端口号
  form.port = MediaServerDefaultPorts[type]
}

// 添加路径映射
const addPathMapping = () => {
  pathMappings.value.push({ server_path: '', local_path: '' })
}

// 删除路径映射
const removePathMapping = (index: number) => {
  pathMappings.value.splice(index, 1)
}

// 显示添加对话框
const showAddDialog = () => {
  isEdit.value = false
  currentEditConfig.value = null
  resetForm()
  formDialogVisible.value = true
}

// 显示编辑对话框
const showEditDialog = (config: MediaServerConfig) => {
  isEdit.value = true
  editId.value = config.id
  currentEditConfig.value = config
  activeTabName.value = 'basic'

  // 填充表单
  Object.assign(form, {
    type: config.type,
    name: config.name,
    host: config.host,
    port: config.port,
    use_ssl: config.use_ssl,
    api_key: '', // 不回显敏感信息
    token: '',
    is_default: config.is_default,
    auto_refresh_library: config.auto_refresh_library,
    sync_watch_history: config.sync_watch_history,
    watch_history_sync_interval: config.watch_history_sync_interval
  })

  // 清空路径映射
  pathMappings.value = []
  serverUserId.value = ''

  formDialogVisible.value = true
}

// 重置表单
const resetForm = () => {
  Object.assign(form, {
    type: MediaServerType.JELLYFIN,
    name: '',
    host: 'localhost',
    port: 8096,
    use_ssl: false,
    api_key: '',
    token: '',
    is_default: false,
    auto_refresh_library: true,
    sync_watch_history: true,
    watch_history_sync_interval: 60
  })
  pathMappings.value = []
  serverUserId.value = ''
  formRef.value?.clearValidate()
  activeTabName.value = 'basic'
}

// 提交表单
const submitForm = async () => {
  if (!formRef.value) return

  try {
    await formRef.value.validate()
  } catch (error) {
    ElMessage.warning('请检查表单填写')
    return
  }

  // 创建模式下验证配置（编辑模式下跳过，因为 API KEY 可能为空）
  if (!isEdit.value) {
    const errors = validateServerConfig(form)
    if (errors.length > 0) {
      ElMessage.error(errors[0])
      return
    }
  }

  submitting.value = true
  try {
    // 构建提交数据
    const submitData: MediaServerConfigCreate = {
      ...form,
      library_path_mappings: pathMappings.value.filter(
        (m) => m.server_path && m.local_path
      ),
      server_config: serverUserId.value ? { server_user_id: serverUserId.value } : undefined
    }

    if (isEdit.value && editId.value) {
      // 更新（不提交空的敏感字段）
      const updateData: any = { ...submitData }
      if (!updateData.api_key) delete updateData.api_key
      if (!updateData.token) delete updateData.token
      delete updateData.type // 类型不允许修改

      await api.mediaServer.updateMediaServerConfig(editId.value, updateData)
      ElMessage.success('更新成功')
    } else {
      // 创建
      await api.mediaServer.createMediaServerConfig(submitData)
      ElMessage.success('创建成功')
    }

    formDialogVisible.value = false
    await loadConfigs()
  } catch (error: any) {
    console.error('Failed to submit form:', error)
    ElMessage.error(error.response?.data?.detail || '操作失败')
  } finally {
    submitting.value = false
  }
}

// 测试连接
const testConnection = async (configId: number) => {
  const config = configs.value.find((c) => c.id === configId)
  if (!config) return

  ElMessage.info('正在测试连接...')
  try {
    const res = await api.mediaServer.testMediaServerConnection(configId)
    if (res.data.success) {
      ElMessage.success(res.data.message || '连接成功！')
      // 刷新列表以更新状态
      await loadConfigs()
    } else {
      ElMessage.error(res.data.message || '连接失败')
    }
  } catch (error: any) {
    console.error('Test connection failed:', error)
    ElMessage.error(error.response?.data?.detail || '连接测试失败')
  }
}

// 同步观看历史
const syncHistory = async (configId: number) => {
  const config = configs.value.find((c) => c.id === configId)
  if (!config) return

  ElMessage.info('正在同步观看历史...')
  try {
    const res = await api.mediaServer.syncWatchHistory(configId)
    ElMessage.success(
      `同步完成！新增 ${res.data.new_count} 条，更新 ${res.data.updated_count} 条`
    )
    await loadConfigs()
  } catch (error: any) {
    console.error('Sync history failed:', error)
    ElMessage.error(error.response?.data?.detail || '同步失败')
  }
}

// 删除配置
const deleteConfig = async (configId: number) => {
  const config = configs.value.find((c) => c.id === configId)
  if (!config) return

  try {
    await ElMessageBox.confirm(`确定要删除配置"${config.name}"吗？`, '确认删除', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消'
    })

    await api.mediaServer.deleteMediaServerConfig(configId)
    ElMessage.success('删除成功')
    await loadConfigs()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('Delete config failed:', error)
      ElMessage.error(error.response?.data?.detail || '删除失败')
    }
  }
}

onMounted(() => {
  loadConfigs()
})
</script>

<style scoped>
.settings-section {
  width: 100%;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.section-header h3 {
  margin: 0 0 5px 0;
  font-size: 18px;
}

.section-description {
  margin: 0;
  font-size: 14px;
  color: #909399;
}

.form-item-tips {
  font-size: 12px;
  color: #909399;
  margin-top: 5px;
  line-height: 1.5;
}

.form-item-tips a {
  color: #409eff;
  text-decoration: none;
}

.form-item-tips a:hover {
  text-decoration: underline;
}
</style>
