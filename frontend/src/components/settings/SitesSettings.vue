<template>
  <div class="settings-section">
    <div class="section-header">
      <div>
        <h3>PT站点管理</h3>
        <p class="section-description">管理和配置PT站点连接</p>
      </div>
    </div>

    <!-- 过滤器 -->
    <div class="filter-container">
      <el-select v-model="filters.status" placeholder="状态" clearable style="width: 120px" @change="loadSites">
        <el-option label="正常" value="active" />
        <el-option label="未激活" value="inactive" />
        <el-option label="错误" value="error" />
      </el-select>
      <el-select v-model="filters.sync_enabled" placeholder="同步状态" clearable style="width: 120px" @change="loadSites">
        <el-option label="已启用" :value="true" />
        <el-option label="未启用" :value="false" />
      </el-select>
      <el-button type="primary" :icon="Plus" @click="handleQuickCreate">快速添加</el-button>
      <el-button :icon="Setting" @click="handleCreate">手动配置</el-button>
    </div>

    <!-- 站点列表 -->
    <el-table v-loading="loading" :data="sites" style="width: 100%" @sort-change="handleSortChange">
      <el-table-column prop="name" label="站点名称" min-width="150" sortable="custom" />
      <el-table-column prop="domain" label="域名" min-width="200" />
      <el-table-column prop="type" label="类型" width="120" />
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag v-if="row.status === 'active'" type="success">正常</el-tag>
          <el-tag v-else-if="row.status === 'inactive'" type="info">未激活</el-tag>
          <el-tag v-else type="danger">错误</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="health_status" label="健康状态" width="120">
        <template #default="{ row }">
          <el-tag v-if="row.health_status === 'healthy'" type="success">健康</el-tag>
          <el-tag v-else-if="row.health_status === 'unhealthy'" type="warning">不健康</el-tag>
          <el-tag v-else type="info">未检查</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="sync_enabled" label="同步" width="80">
        <template #default="{ row }">
          <el-tag v-if="row.sync_enabled" type="success" size="small">启用</el-tag>
          <el-tag v-else type="info" size="small">禁用</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="210" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" :loading="testingId === row.id" @click="handleTest(row)">
            测试
          </el-button>
          <el-button link type="warning" size="small" @click="handleEdit(row)">编辑</el-button>
          <el-button link type="danger" size="small" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 空状态 -->
    <el-empty v-if="!loading && sites.length === 0" description="暂无站点数据" style="margin-top: 20px" />

    <!-- 分页 -->
    <el-pagination
      v-if="total > 0" v-model:current-page="pagination.page" v-model:page-size="pagination.page_size"
      class="pagination" :total="total" :page-sizes="[10, 20, 50, 100]"
      layout="total, sizes, prev, pager, next, jumper" @current-change="loadSites" @size-change="loadSites" />

    <!-- 快速添加对话框（从预设创建） -->
    <el-dialog v-model="quickDialogVisible" title="快速添加站点" width="500px" @close="handleQuickDialogClose">
      <el-form ref="quickFormRef" :model="quickForm" :rules="quickRules" label-width="100px">
        <el-form-item label="选择站点" prop="preset_id">
          <el-select v-model="quickForm.preset_id" placeholder="请选择站点" style="width: 100%" @change="handlePresetChange">
            <el-option
              v-for="preset in presets"
              :key="preset.id"
              :label="preset.display_name"
              :value="preset.id"
            >
              <span>{{ preset.display_name }}</span>
              <span style="color: #8492a6; font-size: 12px; margin-left: 8px">{{ preset.description }}</span>
            </el-option>
          </el-select>
        </el-form-item>

        <template v-if="selectedPreset">
          <el-alert
            :title="`${selectedPreset.display_name} - ${selectedPreset.description}`"
            type="info"
            :closable="false"
            style="margin-bottom: 16px"
          />

          <el-form-item v-if="selectedPreset.auth_fields?.includes('cookie')" label="Cookie" prop="auth_cookie">
            <el-input
              v-model="quickForm.auth_cookie"
              type="textarea"
              :rows="3"
              placeholder="请输入Cookie（从浏览器开发者工具复制）"
            />
          </el-form-item>

          <el-form-item v-if="selectedPreset.auth_fields?.includes('passkey')" label="Passkey" prop="auth_passkey">
            <el-input
              v-model="quickForm.auth_passkey"
              placeholder="请输入Passkey（从站点控制面板获取）"
            />
          </el-form-item>

          <el-collapse>
            <el-collapse-item title="高级选项" name="advanced">
              <el-form-item label="自定义名称">
                <el-input v-model="quickForm.name" :placeholder="selectedPreset.display_name" />
              </el-form-item>
              <el-form-item label="启用同步">
                <el-switch v-model="quickForm.sync_enabled" />
              </el-form-item>
            </el-collapse-item>
          </el-collapse>
        </template>
      </el-form>

      <template #footer>
        <el-button @click="quickDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" :disabled="!selectedPreset" @click="handleQuickSubmit">
          创建站点
        </el-button>
      </template>
    </el-dialog>

    <!-- 手动配置对话框 -->
    <el-dialog
      v-model="dialogVisible" :title="dialogMode === 'create' ? '手动添加站点' : '编辑站点'" width="800px"
      @close="handleDialogClose">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="140px">
        <el-tabs v-model="activeTab">
          <el-tab-pane label="基本信息" name="basic">
            <el-form-item label="站点名称" prop="name">
              <el-input v-model="form.name" placeholder="请输入站点名称" />
            </el-form-item>
            <el-form-item label="站点类型" prop="type">
              <el-select v-model="form.type" placeholder="请选择站点类型">
                <el-option
                  v-for="option in SITE_TYPE_OPTIONS" :key="option.value" :label="option.label"
                  :value="option.value" />
              </el-select>
            </el-form-item>
            <el-form-item label="域名" prop="domain">
              <el-input v-model="form.domain" placeholder="例如: example.com" />
            </el-form-item>
            <el-form-item label="站点地址" prop="base_url">
              <el-input v-model="form.base_url" placeholder="例如: https://example.com" />
            </el-form-item>
          </el-tab-pane>

          <el-tab-pane label="认证配置" name="auth">
            <el-form-item label="认证方式" prop="auth_type">
              <el-select v-model="form.auth_type" placeholder="请选择认证方式">
                <el-option
                  v-for="option in AUTH_TYPE_OPTIONS" :key="option.value" :label="option.label"
                  :value="option.value" />
              </el-select>
            </el-form-item>
            <el-form-item v-if="form.auth_type === 'cookie'" label="Cookie" prop="auth_cookie">
              <el-input
                v-model="form.auth_cookie" type="textarea" :rows="3" :placeholder="dialogMode === 'edit' && currentEditSite?.has_auth_cookie
                  ? '已保存（留空则不修改）'
                  : '请输入Cookie'
                  " />
              <el-text v-if="dialogMode === 'edit' && currentEditSite?.has_auth_cookie" type="success" size="small">
                Cookie 已保存，留空则保持不变
              </el-text>
            </el-form-item>
            <el-form-item v-if="form.auth_type === 'passkey'" label="Passkey" prop="auth_passkey">
              <el-input
                v-model="form.auth_passkey" :placeholder="dialogMode === 'edit' && currentEditSite?.has_auth_passkey
                  ? '已保存（留空则不修改）'
                  : '请输入Passkey'
                  " />
              <el-text v-if="dialogMode === 'edit' && currentEditSite?.has_auth_passkey" type="success" size="small">
                Passkey 已保存，留空则保持不变
              </el-text>
            </el-form-item>
            <template v-if="form.auth_type === 'user_pass'">
              <el-form-item label="用户名" prop="auth_username">
                <el-input v-model="form.auth_username" placeholder="请输入用户名" />
              </el-form-item>
              <el-form-item label="密码" prop="auth_password">
                <el-input
                  v-model="form.auth_password" type="password" :placeholder="dialogMode === 'edit' && currentEditSite?.has_auth_password
                    ? '已保存（留空则不修改）'
                    : '请输入密码'
                    " show-password />
                <el-text v-if="dialogMode === 'edit' && currentEditSite?.has_auth_password" type="success" size="small">
                  密码已保存，留空则保持不变
                </el-text>
              </el-form-item>
            </template>
          </el-tab-pane>

          <el-tab-pane label="同步配置" name="sync">
            <el-form-item label="启用同步">
              <el-switch v-model="form.sync_enabled" />
            </el-form-item>
            <el-form-item label="同步策略" prop="sync_strategy">
              <el-select v-model="form.sync_strategy" placeholder="请选择同步策略">
                <el-option label="基于时间" value="time_based" />
                <el-option label="基于页面" value="page_based" />
                <el-option label="基于ID" value="id_based" />
              </el-select>
            </el-form-item>
            <el-form-item label="同步间隔(分钟)">
              <el-input-number v-model="form.sync_interval" :min="1" :max="1440" />
            </el-form-item>
            <el-form-item label="请求间隔(秒)">
              <el-input-number v-model="form.request_interval" :min="1" :max="60" />
            </el-form-item>
            <el-form-item label="每日最大请求数">
              <el-input-number v-model="form.max_requests_per_day" :min="0" />
            </el-form-item>
          </el-tab-pane>

          <el-tab-pane label="代理配置" name="proxy">
            <el-form-item label="启用代理">
              <el-switch v-model="proxyEnabled" @change="handleProxyToggle" />
            </el-form-item>
            <template v-if="proxyEnabled">
              <el-form-item label="代理类型">
                <el-select v-model="proxyConfig.type" placeholder="请选择代理类型">
                  <el-option label="HTTP" value="http" />
                  <el-option label="HTTPS" value="https" />
                  <el-option label="SOCKS5" value="socks5" />
                </el-select>
              </el-form-item>
              <el-form-item label="代理地址">
                <el-input v-model="proxyConfig.host" placeholder="例如: 127.0.0.1" />
              </el-form-item>
              <el-form-item label="代理端口">
                <el-input-number v-model="proxyConfig.port" :min="1" :max="65535" />
              </el-form-item>
              <el-form-item label="用户名">
                <el-input v-model="proxyConfig.username" placeholder="可选" />
              </el-form-item>
              <el-form-item label="密码">
                <el-input v-model="proxyConfig.password" type="password" placeholder="可选" show-password />
              </el-form-item>
            </template>
          </el-tab-pane>
        </el-tabs>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          {{ dialogMode === 'create' ? '创建' : '更新' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox, FormInstance, FormRules } from 'element-plus'
import { Plus, Setting } from '@element-plus/icons-vue'
import type { PTSite, PTSiteForm } from '@/types'
import {
  getSiteList,
  createSite,
  updateSite,
  deleteSite,
  testSiteConnection,
  getSitePresets,
  createSiteFromPreset,
  type SitePreset,
  type CreateFromPresetForm
} from '@/api/modules/site'
import { SITE_TYPE_OPTIONS, AUTH_TYPE_OPTIONS } from '@/constants/site'
import { AuthType, SyncMode } from '@/types/site'

// 数据
const loading = ref(false)
const sites = ref<PTSite[]>([])
const total = ref(0)
const pagination = reactive({
  page: 1,
  page_size: 20
})
const filters = reactive({
  status: undefined as string | undefined,
  sync_enabled: undefined as boolean | undefined
})

// 站点预设
const presets = ref<SitePreset[]>([])
const presetsLoaded = ref(false)

// 快速添加对话框
const quickDialogVisible = ref(false)
const quickFormRef = ref<FormInstance>()
const quickForm = reactive<CreateFromPresetForm>({
  preset_id: '',
  auth_cookie: '',
  auth_passkey: '',
  name: '',
  sync_enabled: true
})

// 选中的预设
const selectedPreset = computed(() => {
  return presets.value.find(p => p.id === quickForm.preset_id)
})

// 快速添加表单验证
const quickRules: FormRules = {
  preset_id: [{ required: true, message: '请选择站点', trigger: 'change' }]
}

// 手动配置对话框
const dialogVisible = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const activeTab = ref('basic')
const formRef = ref<FormInstance>()
const submitting = ref(false)
const testingId = ref<number | null>(null)

// 表单数据
const form = reactive<PTSiteForm>({
  name: '',
  type: '',
  domain: '',
  base_url: '',
  auth_type: AuthType.COOKIE,
  auth_cookie: '',
  auth_passkey: '',
  auth_username: '',
  auth_password: '',
  sync_enabled: true,
  sync_strategy: SyncMode.TIME_BASED,
  sync_interval: 60,
  request_interval: 3,
  max_requests_per_day: 1000
})

const currentEditId = ref<number | null>(null)
const currentEditSite = ref<PTSite | null>(null)

// 代理配置
const proxyEnabled = ref(false)
const proxyConfig = reactive({
  type: 'http',
  host: '',
  port: 7890,
  username: '',
  password: ''
})

// 表单验证规则
const rules: FormRules = {
  name: [{ required: true, message: '请输入站点名称', trigger: 'blur' }],
  type: [{ required: true, message: '请选择站点类型', trigger: 'change' }],
  domain: [{ required: true, message: '请输入域名', trigger: 'blur' }],
  base_url: [
    { required: true, message: '请输入站点地址', trigger: 'blur' },
    { type: 'url', message: '请输入有效的URL', trigger: 'blur' }
  ],
  auth_type: [{ required: true, message: '请选择认证方式', trigger: 'change' }]
}

// 加载站点预设
const loadPresets = async () => {
  if (presetsLoaded.value) return
  try {
    const response = await getSitePresets()
    presets.value = response.data.presets
    presetsLoaded.value = true
  } catch (error) {
    console.error('Failed to load presets:', error)
  }
}

// 加载站点列表
const loadSites = async () => {
  loading.value = true
  try {
    const response = await getSiteList({
      page: pagination.page,
      page_size: pagination.page_size,
      status: filters.status,
      sync_enabled: filters.sync_enabled
    })
    sites.value = response.data.items
    total.value = response.data.total
  } catch (error) {
    console.error('Failed to load sites:', error)
    ElMessage.error('加载站点列表失败')
  } finally {
    loading.value = false
  }
}

// 处理预设选择变化
const handlePresetChange = () => {
  // 清空认证字段
  quickForm.auth_cookie = ''
  quickForm.auth_passkey = ''
  quickForm.name = ''
}

// 处理快速创建
const handleQuickCreate = async () => {
  await loadPresets()
  resetQuickForm()
  quickDialogVisible.value = true
}

// 处理快速创建提交
const handleQuickSubmit = async () => {
  if (!quickFormRef.value) return

  try {
    await quickFormRef.value.validate()

    // 验证必填的认证信息
    if (selectedPreset.value?.auth_fields?.includes('cookie') && !quickForm.auth_cookie) {
      ElMessage.warning('请输入Cookie')
      return
    }

    submitting.value = true

    await createSiteFromPreset(quickForm)
    ElMessage({
      message: '站点创建成功，基础数据正在后台同步中...',
      type: 'success',
      duration: 4000
    })

    quickDialogVisible.value = false
    loadSites()
  } catch (error) {
    console.error('Failed to create site from preset:', error)
    ElMessage.error('创建失败')
  } finally {
    submitting.value = false
  }
}

// 重置快速添加表单
const resetQuickForm = () => {
  Object.assign(quickForm, {
    preset_id: '',
    auth_cookie: '',
    auth_passkey: '',
    name: '',
    sync_enabled: true
  })
}

// 快速添加对话框关闭
const handleQuickDialogClose = () => {
  resetQuickForm()
}

// 处理手动创建
const handleCreate = () => {
  dialogMode.value = 'create'
  currentEditId.value = null
  resetForm()
  dialogVisible.value = true
}

// 处理编辑
const handleEdit = (site: PTSite) => {
  dialogMode.value = 'edit'
  currentEditId.value = site.id
  currentEditSite.value = site

  // 填充表单（不包括认证字段）
  Object.assign(form, {
    name: site.name,
    type: site.type,
    domain: site.domain,
    base_url: site.base_url,
    auth_type: site.auth_type,
    auth_cookie: '',
    auth_passkey: '',
    auth_username: '',
    auth_password: '',
    sync_enabled: site.sync_enabled,
    sync_strategy: site.sync_strategy,
    sync_interval: site.sync_interval,
    request_interval: site.request_interval,
    max_requests_per_day: site.max_requests_per_day
  })

  // 处理代理配置
  if (site.proxy_config && Object.keys(site.proxy_config).length > 0) {
    proxyEnabled.value = true
    Object.assign(proxyConfig, site.proxy_config)
  } else {
    proxyEnabled.value = false
  }

  dialogVisible.value = true
}

// 处理删除
const handleDelete = async (site: PTSite) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除站点 "${site.name}" 吗？此操作不可恢复。`,
      '确认删除',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await deleteSite(site.id)
    ElMessage.success('删除成功')
    loadSites()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Failed to delete site:', error)
      ElMessage.error('删除失败')
    }
  }
}

// 处理测试连接
const handleTest = async (site: PTSite) => {
  testingId.value = site.id
  try {
    const result = await testSiteConnection(site.id)
    if (result.data.success) {
      ElMessage.success(`连接成功: ${result.data.message}`)
    } else {
      ElMessage.warning(`连接失败: ${result.data.message}`)
    }
  } catch (error) {
    console.error('Failed to test connection:', error)
    ElMessage.error('测试连接失败')
  } finally {
    testingId.value = null
  }
}

// 处理提交
const handleSubmit = async () => {
  if (!formRef.value) return

  try {
    await formRef.value.validate()

    submitting.value = true

    // 准备提交数据
    const submitData: any = { ...form }

    // 处理代理配置
    if (proxyEnabled.value && proxyConfig.host) {
      submitData.proxy_config = { ...proxyConfig }
    } else {
      submitData.proxy_config = null
    }

    // 编辑模式下，过滤掉空的认证字段（空字符串表示不修改）
    if (dialogMode.value === 'edit') {
      const authFields = ['auth_cookie', 'auth_passkey', 'auth_username', 'auth_password']
      authFields.forEach(field => {
        if (!submitData[field]) {
          delete submitData[field]
        }
      })
    }

    if (dialogMode.value === 'create') {
      await createSite(submitData)
      ElMessage({
        message: '站点创建成功，基础数据正在后台同步中...',
        type: 'success',
        duration: 4000
      })
    } else {
      await updateSite(currentEditId.value!, submitData)
      ElMessage.success('更新成功')
    }

    dialogVisible.value = false
    loadSites()
  } catch (error) {
    console.error('Failed to submit form:', error)
    if (error !== false) {
      ElMessage.error(dialogMode.value === 'create' ? '创建失败' : '更新失败')
    }
  } finally {
    submitting.value = false
  }
}

// 重置表单
const resetForm = () => {
  if (formRef.value) {
    formRef.value.resetFields()
  }
  Object.assign(form, {
    name: '',
    type: '',
    domain: '',
    base_url: '',
    auth_type: 'cookie',
    auth_cookie: '',
    auth_passkey: '',
    auth_username: '',
    auth_password: '',
    sync_enabled: true,
    sync_strategy: 'time_based',
    sync_interval: 60,
    request_interval: 3,
    max_requests_per_day: 1000
  })
  proxyEnabled.value = false
  Object.assign(proxyConfig, {
    type: 'http',
    host: '',
    port: 7890,
    username: '',
    password: ''
  })
  activeTab.value = 'basic'
}

// 对话框关闭回调
const handleDialogClose = () => {
  resetForm()
  currentEditId.value = null
  currentEditSite.value = null
}

// 代理开关切换
const handleProxyToggle = (enabled: boolean) => {
  if (!enabled) {
    Object.assign(proxyConfig, {
      type: 'http',
      host: '',
      port: 7890,
      username: '',
      password: ''
    })
  }
}

// 处理排序
const handleSortChange = ({ prop, order }: any) => {
  console.log('Sort:', prop, order)
}

// 初始化
onMounted(() => {
  loadSites()
})
</script>

<style scoped>
.settings-section {
  padding: 20px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
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

.filter-container {
  margin-bottom: 16px;
  display: flex;
  gap: 10px;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>
