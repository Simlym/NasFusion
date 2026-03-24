<template>
  <div class="sites-settings">
    <!-- 工具栏 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <el-select v-model="filters.status" placeholder="状态筛选" clearable style="width: 130px" @change="loadSites">
          <el-option label="正常" value="active" />
          <el-option label="未激活" value="inactive" />
          <el-option label="错误" value="error" />
        </el-select>
      </div>
      <div class="toolbar-right">
        <el-button v-if="sites.length > 0" :icon="Refresh" :loading="batchRefreshing"
          @click="handleBatchRefreshProfile">批量刷新</el-button>
        <el-button type="primary" :icon="Plus" @click="handleQuickCreate">快速添加</el-button>
        <el-button :icon="Setting" @click="handleCreate">手动配置</el-button>
        <el-button-group>
          <el-button :type="viewMode === 'card' ? 'primary' : 'default'" :icon="Grid" @click="viewMode = 'card'" />
          <el-button :type="viewMode === 'table' ? 'primary' : 'default'" :icon="List" @click="viewMode = 'table'" />
        </el-button-group>
      </div>
    </div>

    <!-- 卡片视图 -->
    <div v-if="viewMode === 'card'" v-loading="loading" class="site-cards">
      <div v-for="site in sites" :key="site.id" class="site-card"
        :class="{ 'site-card--error': site.status === 'error' }"
        :style="{ '--site-accent': getSiteColor(site.type) }">

        <!-- 彩色顶部强调条 -->
        <div class="card-accent-bar"></div>

        <!-- 卡片头部 -->
        <div class="card-header">
          <div class="card-title-row">
            <div class="site-logo" :style="{ background: getSiteColor(site.type) }">
              {{ getSiteShortName(site.type) }}
            </div>
            <div class="card-title-info">
              <div class="site-name">{{ site.name }}</div>
              <span class="status-badge" :class="'badge--' + (site.health_status || 'unknown')">
                <span class="status-dot" :class="'dot--' + (site.health_status || 'unknown')"></span>
                {{ healthLabel(site.health_status) }}
              </span>
            </div>
          </div>
          <el-dropdown trigger="click" @command="(cmd: string) => handleCardCommand(cmd, site)">
            <el-button :icon="MoreFilled" text circle />
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="edit"><el-icon><Edit /></el-icon> 编辑配置</el-dropdown-item>
                <el-dropdown-item command="refresh-profile"><el-icon><User /></el-icon> 刷新用户信息</el-dropdown-item>
                <el-dropdown-item command="sync-metadata"><el-icon><Refresh /></el-icon> 同步站点元数据</el-dropdown-item>
                <el-dropdown-item divided command="delete"><el-icon><Delete /></el-icon> 删除站点</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>

        <!-- 用户信息 -->
        <div v-if="site.user_profile" class="user-profile-section">
          <!-- 用户名 + 等级 -->
          <div class="profile-header">
            <span class="profile-username">
              <el-icon :size="12"><User /></el-icon>
              {{ site.user_profile.username || '-' }}
            </span>
            <el-tag v-if="site.user_profile.user_class" size="small" effect="plain" type="warning">
              {{ site.user_profile.user_class }}
            </el-tag>
          </div>

          <!-- 主要指标：上传 / 下载 / 分享率 -->
          <div class="primary-metrics">
            <div class="metric-item metric-upload">
              <span class="metric-label">上传</span>
              <span class="metric-value">{{ site.user_profile.uploaded_text || formatFileSize(site.user_profile.uploaded || 0) }}</span>
            </div>
            <div class="metric-item metric-download">
              <span class="metric-label">下载</span>
              <span class="metric-value">{{ site.user_profile.downloaded_text || formatFileSize(site.user_profile.downloaded || 0) }}</span>
            </div>
            <div class="metric-item"
              :class="(site.user_profile.ratio ?? 0) >= 1 || site.user_profile.ratio === -1 ? 'metric-ratio-good' : 'metric-ratio-bad'">
              <span class="metric-label">分享率</span>
              <span class="metric-value">{{ formatRatio(site.user_profile.ratio) }}</span>
            </div>
          </div>

          <!-- 次要指标：做种 / 做种量 / 积分 -->
          <div class="secondary-metrics">
            <div class="sec-metric">
              <span class="sec-label">做种</span>
              <span class="sec-value">{{ site.user_profile.seeding_count ?? '-' }}</span>
            </div>
            <div class="sec-metric">
              <span class="sec-label">做种量</span>
              <span class="sec-value">{{ site.user_profile.seeding_size_text || (site.user_profile.seeding_size ? formatFileSize(site.user_profile.seeding_size) : '-') }}</span>
            </div>
            <div class="sec-metric">
              <span class="sec-label">积分</span>
              <span class="sec-value">{{ site.user_profile.bonus != null ? formatNumber(Math.floor(site.user_profile.bonus)) : '-' }}</span>
            </div>
          </div>
        </div>
        <div v-else class="user-profile-empty">
          <el-button link type="primary" size="small" :loading="refreshingProfileId === site.id"
            @click="handleRefreshProfile(site)">
            <el-icon><User /></el-icon> 获取用户信息
          </el-button>
        </div>
      </div>

      <!-- 添加站点占位卡 -->
      <div class="site-card site-card--add" @click="handleQuickCreate">
        <el-icon :size="32" color="var(--text-color-muted)">
          <Plus />
        </el-icon>
        <span class="add-text">添加站点</span>
      </div>
    </div>

    <!-- 表格视图 -->
    <div v-if="viewMode === 'table'" v-loading="loading">
      <el-table :data="sites" style="width: 100%" @sort-change="handleSortChange">
        <el-table-column prop="name" label="站点" min-width="140" show-overflow-tooltip sortable="custom">
          <template #default="{ row }">
            <div class="table-site-name">
              <div class="site-logo site-logo--sm" :style="{ background: getSiteColor(row.type) }">
                {{ getSiteShortName(row.type) }}
              </div>
              <div class="name-text">{{ row.name }}</div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="health_status" label="健康" width="75">
          <template #default="{ row }">
            <span class="status-badge" :class="'badge--' + (row.health_status || 'unknown')">
              <span class="status-dot" :class="'dot--' + (row.health_status || 'unknown')"></span>
              {{ healthLabel(row.health_status) }}
            </span>
          </template>
        </el-table-column>
        <!-- <el-table-column label="同步" width="75">
          <template #default="{ row }">
            <el-tag v-if="row.sync_enabled" size="small" type="success">启用</el-tag>
            <el-tag v-else size="small" type="info">禁用</el-tag>
          </template>
        </el-table-column> -->

        <el-table-column label="用户名" min-width="100" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.user_profile?.username" class="table-cell-value">{{ row.user_profile.username }}</span>
            <el-button v-else link type="primary" size="small" :loading="refreshingProfileId === row.id"
              @click="handleRefreshProfile(row)">获取</el-button>
          </template>
        </el-table-column>
        <el-table-column label="等级" min-width="100" show-overflow-tooltip>
          <template #default="{ row }">
            <el-tag v-if="row.user_profile?.user_class" size="small" effect="plain" type="warning">{{
              row.user_profile.user_class }}</el-tag>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="邮箱" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.user_profile?.email" class="table-cell-value">{{ row.user_profile.email }}</span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="上传" width="85">
          <template #default="{ row }">
            <span v-if="row.user_profile" class="table-cell-value">{{ row.user_profile.uploaded_text ||
              formatFileSize(row.user_profile.uploaded || 0) }}</span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="下载" width="85">
          <template #default="{ row }">
            <span v-if="row.user_profile" class="table-cell-value">{{ row.user_profile.downloaded_text ||
              formatFileSize(row.user_profile.downloaded || 0) }}</span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="分享率" width="70">
          <template #default="{ row }">
            <span v-if="row.user_profile" class="table-cell-value"
              :class="{ 'ratio-good': (row.user_profile.ratio ?? 0) >= 1 || row.user_profile.ratio === -1 }">
              {{ formatRatio(row.user_profile.ratio) }}
            </span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="做种" width="60">
          <template #default="{ row }">
            <span v-if="row.user_profile" class="table-cell-value">{{ row.user_profile.seeding_count ?? '-' }}</span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="做种量" width="85">
          <template #default="{ row }">
            <span v-if="row.user_profile && (row.user_profile.seeding_size || row.user_profile.seeding_size_text)"
              class="table-cell-value">
              {{ row.user_profile.seeding_size_text || formatFileSize(row.user_profile.seeding_size || 0) }}
            </span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="积分" width="85">
          <template #default="{ row }">
            <span v-if="row.user_profile?.bonus != null" class="table-cell-value">{{
              formatNumber(Math.floor(row.user_profile.bonus)) }}</span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="入站时间" width="95">
          <template #default="{ row }">
            <span v-if="row.user_profile?.join_date" class="table-cell-value">{{ formatDate(row.user_profile.join_date)
              }}</span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="同步状态" width="85">
          <template #default="{ row }">
            <el-tag v-if="row.last_sync_status" size="small" :type="getSyncStatusType(row.last_sync_status)">
              {{ getSyncStatusLabel(row.last_sync_status) }}
            </el-tag>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="最后同步" width="115">
          <template #default="{ row }">
            <span v-if="row.last_sync_at" class="table-cell-value">{{ formatDateTime(row.last_sync_at) }}</span>
            <span v-else class="text-muted">未同步</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button link type="warning" size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button link type="danger" size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 空状态 -->
    <el-empty v-if="!loading && sites.length === 0 && viewMode === 'table'" description="暂无站点数据">
      <el-button type="primary" @click="handleQuickCreate">快速添加站点</el-button>
    </el-empty>

    <!-- 分页 -->
    <el-pagination v-if="total > pagination.page_size" v-model:current-page="pagination.page"
      v-model:page-size="pagination.page_size" class="pagination" :total="total" :page-sizes="[10, 20, 50, 100]"
      layout="total, sizes, prev, pager, next" @current-change="loadSites" @size-change="loadSites" />

    <!-- 快速添加对话框（从预设创建） -->
    <el-dialog v-model="quickDialogVisible" title="快速添加站点" width="500px" @close="handleQuickDialogClose">
      <el-form ref="quickFormRef" :model="quickForm" :rules="quickRules" label-width="100px">
        <el-form-item label="选择站点" prop="preset_id">
          <el-select v-model="quickForm.preset_id" placeholder="请选择站点" style="width: 100%" @change="handlePresetChange">
            <el-option v-for="preset in presets" :key="preset.id" :label="preset.display_name" :value="preset.id">
              <span>{{ preset.display_name }}</span>
              <span style="color: #8492a6; font-size: 12px; margin-left: 8px">{{ preset.description }}</span>
            </el-option>
          </el-select>
        </el-form-item>

        <template v-if="selectedPreset">
          <el-alert :title="`${selectedPreset.display_name} - ${selectedPreset.description}`" type="info"
            :closable="false" style="margin-bottom: 16px" />

          <el-form-item v-if="selectedPreset.auth_fields?.includes('cookie')" label="Cookie" prop="auth_cookie">
            <el-input v-model="quickForm.auth_cookie" type="textarea" :rows="3" placeholder="请输入Cookie（从浏览器开发者工具复制）" />
          </el-form-item>

          <el-form-item v-if="selectedPreset.auth_fields?.includes('passkey')" label="Passkey" prop="auth_passkey">
            <el-input v-model="quickForm.auth_passkey" placeholder="请输入Passkey（从站点控制面板获取）" />
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
    <el-dialog v-model="dialogVisible" :title="dialogMode === 'create' ? '手动添加站点' : '编辑站点'" width="800px"
      @close="handleDialogClose">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="140px">
        <el-tabs v-model="activeTab">
          <el-tab-pane label="基本信息" name="basic">
            <el-form-item label="站点名称" prop="name">
              <el-input v-model="form.name" placeholder="请输入站点名称" />
            </el-form-item>
            <el-form-item label="站点类型" prop="type">
              <el-select v-model="form.type" placeholder="请选择站点类型">
                <el-option v-for="option in SITE_TYPE_OPTIONS" :key="option.value" :label="option.label"
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
                <el-option v-for="option in AUTH_TYPE_OPTIONS" :key="option.value" :label="option.label"
                  :value="option.value" />
              </el-select>
            </el-form-item>
            <el-form-item v-if="form.auth_type === 'cookie'" label="Cookie" prop="auth_cookie">
              <el-input v-model="form.auth_cookie" type="textarea" :rows="3" :placeholder="dialogMode === 'edit' && currentEditSite?.has_auth_cookie
                ? '已保存（留空则不修改）'
                : '请输入Cookie'
                " />
              <el-text v-if="dialogMode === 'edit' && currentEditSite?.has_auth_cookie" type="success" size="small">
                Cookie 已保存，留空则保持不变
              </el-text>
            </el-form-item>
            <el-form-item v-if="form.auth_type === 'passkey'" label="Passkey" prop="auth_passkey">
              <el-input v-model="form.auth_passkey" :placeholder="dialogMode === 'edit' && currentEditSite?.has_auth_passkey
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
                <el-input v-model="form.auth_password" type="password" :placeholder="dialogMode === 'edit' && currentEditSite?.has_auth_password
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
import {
  Plus, Setting, Grid, List, MoreFilled, Edit, Refresh, Delete, User
} from '@element-plus/icons-vue'
import type { PTSite, PTSiteForm } from '@/types'
import {
  getSiteList,
  createSite,
  updateSite,
  deleteSite,
  syncSiteCategories,
  syncSiteMetadata,
  getSitePresets,
  createSiteFromPreset,
  refreshSiteProfile,
  testSiteConnection,
  type SitePreset,
  type CreateFromPresetForm
} from '@/api/modules/site'
import { SITE_TYPE_OPTIONS, AUTH_TYPE_OPTIONS } from '@/constants/site'
import { AuthType, SyncMode } from '@/types/site'
import { formatNumber, formatFileSize } from '@/utils/format'

// 站点 Logo 颜色映射
const SITE_COLORS: Record<string, string> = {
  mteam: '#1a73e8',
  hdsky: '#0ea5e9',
  chdbits: '#8b5cf6',
  pthome: '#f59e0b',
  ourbits: '#10b981',
  hdchina: '#ef4444',
  nexusphp: '#64748b',
  gazelle: '#ec4899',
  unit3d: '#6366f1',
  other: '#94a3b8'
}

// 站点短名映射
const SITE_SHORT_NAMES: Record<string, string> = {
  mteam: 'MT',
  hdsky: 'HS',
  chdbits: 'CD',
  pthome: 'PH',
  ourbits: 'OB',
  hdchina: 'HC',
  nexusphp: 'NP',
  gazelle: 'GZ',
  unit3d: 'U3',
  other: 'PT'
}

const getSiteColor = (type: string) => SITE_COLORS[type] || SITE_COLORS.other
const getSiteShortName = (type: string) => SITE_SHORT_NAMES[type] || 'PT'

// 视图模式
const viewMode = ref<'card' | 'table'>('card')

// 数据
const loading = ref(false)
const sites = ref<PTSite[]>([])
const total = ref(0)
const pagination = reactive({ page: 1, page_size: 50 })
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

const selectedPreset = computed(() => presets.value.find(p => p.id === quickForm.preset_id))

const quickRules: FormRules = {
  preset_id: [{ required: true, message: '请选择站点', trigger: 'change' }]
}

// 手动配置对话框
const dialogVisible = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const activeTab = ref('basic')
const formRef = ref<FormInstance>()
const submitting = ref(false)
const refreshingProfileId = ref<number | null>(null)
const batchRefreshing = ref(false)

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

const proxyEnabled = ref(false)
const proxyConfig = reactive({
  type: 'http',
  host: '',
  port: 7890,
  username: '',
  password: ''
})

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

// 辅助函数
const healthLabel = (status?: string) => {
  const map: Record<string, string> = { healthy: '健康', unhealthy: '异常' }
  return status ? (map[status] || '未检查') : '未检查'
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
  quickForm.auth_cookie = ''
  quickForm.auth_passkey = ''
  quickForm.name = ''
}

// 快速创建
const handleQuickCreate = async () => {
  await loadPresets()
  resetQuickForm()
  quickDialogVisible.value = true
}

const handleQuickSubmit = async () => {
  if (!quickFormRef.value) return
  try {
    await quickFormRef.value.validate()
    if (selectedPreset.value?.auth_fields?.includes('cookie') && !quickForm.auth_cookie) {
      ElMessage.warning('请输入Cookie')
      return
    }
    submitting.value = true
    await createSiteFromPreset(quickForm)
    ElMessage({ message: '站点创建成功，基础数据正在后台同步中...', type: 'success', duration: 4000 })
    quickDialogVisible.value = false
    loadSites()
  } catch (error) {
    console.error('Failed to create site from preset:', error)
    ElMessage.error('创建失败')
  } finally {
    submitting.value = false
  }
}

const resetQuickForm = () => {
  Object.assign(quickForm, { preset_id: '', auth_cookie: '', auth_passkey: '', name: '', sync_enabled: true })
}

const handleQuickDialogClose = () => { resetQuickForm() }

// 手动创建
const handleCreate = () => {
  dialogMode.value = 'create'
  currentEditId.value = null
  resetForm()
  dialogVisible.value = true
}

// 编辑
const handleEdit = (site: PTSite) => {
  dialogMode.value = 'edit'
  currentEditId.value = site.id
  currentEditSite.value = site
  Object.assign(form, {
    name: site.name, type: site.type, domain: site.domain, base_url: site.base_url,
    auth_type: site.auth_type, auth_cookie: '', auth_passkey: '', auth_username: '', auth_password: '',
    sync_enabled: site.sync_enabled, sync_strategy: site.sync_strategy,
    sync_interval: site.sync_interval, request_interval: site.request_interval,
    max_requests_per_day: site.max_requests_per_day
  })
  if (site.proxy_config && Object.keys(site.proxy_config).length > 0) {
    proxyEnabled.value = true
    Object.assign(proxyConfig, site.proxy_config)
  } else {
    proxyEnabled.value = false
  }
  dialogVisible.value = true
}

// 删除
const handleDelete = async (site: PTSite) => {
  try {
    await ElMessageBox.confirm(`确定要删除站点 "${site.name}" 吗？此操作不可恢复。`, '确认删除', {
      confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning'
    })
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

// 刷新用户信息
const handleRefreshProfile = async (site: PTSite) => {
  refreshingProfileId.value = site.id
  try {
    const result = await refreshSiteProfile(site.id)
    if (result.data.success) {
      ElMessage.success('用户信息已更新')
      loadSites()
    } else {
      ElMessage.warning(result.data.message || '获取用户信息失败')
    }
  } catch (error) {
    console.error('Failed to refresh profile:', error)
    ElMessage.error('获取用户信息失败')
  } finally {
    refreshingProfileId.value = null
  }
}

// 批量刷新用户信息（同时更新健康状态）
const handleBatchRefreshProfile = async () => {
  const activeSites = sites.value.filter(s => s.status === 'active')
  if (activeSites.length === 0) {
    ElMessage.warning('没有活跃的站点')
    return
  }
  batchRefreshing.value = true
  try {
    const results = await Promise.allSettled(
      activeSites.map(site =>
        testSiteConnection(site.id).then(res =>
          res.data.success ? refreshSiteProfile(site.id) : Promise.reject(res.data.message)
        )
      )
    )
    const succeeded = results.filter(r => r.status === 'fulfilled').length
    ElMessage.success(`已刷新 ${succeeded}/${activeSites.length} 个站点`)
    loadSites()
  } catch {
    ElMessage.error('批量刷新失败')
  } finally {
    batchRefreshing.value = false
  }
}

// 同步站点元数据（分类 + 元数据）
const handleSyncMetadata = async (site: PTSite) => {
  try {
    const results = await Promise.allSettled([
      syncSiteCategories(site.id),
      syncSiteMetadata(site.id)
    ])
    const allOk = results.every(r => r.status === 'fulfilled')
    if (allOk) {
      ElMessage.success('元数据同步任务已提交')
    } else {
      ElMessage.warning('部分同步任务提交失败')
    }
  } catch {
    ElMessage.error('同步失败')
  }
}

// 格式化分享率
const formatRatio = (ratio?: number) => {
  if (ratio === undefined || ratio === null) return '-'
  if (ratio === -1) return '∞'
  return ratio.toFixed(2)
}

// 格式化日期（仅日期部分）
const formatDate = (dateStr?: string) => {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  if (isNaN(date.getTime())) return dateStr.substring(0, 10)
  return date.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' }).replace(/\//g, '-')
}

// 格式化日期时间
const formatDateTime = (dateStr?: string) => {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  if (isNaN(date.getTime())) return dateStr
  return date.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }).replace(/\//g, '-')
}

// 获取同步状态类型
const getSyncStatusType = (status?: string) => {
  const typeMap: Record<string, any> = {
    'success': 'success',
    'completed': 'success',
    'failed': 'danger',
    'error': 'danger',
    'running': 'primary',
    'pending': 'info'
  }
  return typeMap[status || ''] || 'info'
}

// 获取同步状态标签
const getSyncStatusLabel = (status?: string) => {
  const labelMap: Record<string, string> = {
    'success': '成功',
    'completed': '完成',
    'failed': '失败',
    'error': '错误',
    'running': '同步中',
    'pending': '待同步'
  }
  return labelMap[status || ''] || status
}

// 卡片菜单命令
const handleCardCommand = async (command: string, site: PTSite) => {
  switch (command) {
    case 'edit':
      handleEdit(site)
      break
    case 'refresh-profile':
      handleRefreshProfile(site)
      break
    case 'sync-metadata':
      handleSyncMetadata(site)
      break
    case 'delete':
      handleDelete(site)
      break
  }
}

// 表单提交
const handleSubmit = async () => {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
    submitting.value = true
    const submitData: any = { ...form }
    if (proxyEnabled.value && proxyConfig.host) {
      submitData.proxy_config = { ...proxyConfig }
    } else {
      submitData.proxy_config = null
    }
    if (dialogMode.value === 'edit') {
      const authFields = ['auth_cookie', 'auth_passkey', 'auth_username', 'auth_password']
      authFields.forEach(field => { if (!submitData[field]) delete submitData[field] })
    }
    if (dialogMode.value === 'create') {
      await createSite(submitData)
      ElMessage({ message: '站点创建成功，基础数据正在后台同步中...', type: 'success', duration: 4000 })
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

const resetForm = () => {
  if (formRef.value) formRef.value.resetFields()
  Object.assign(form, {
    name: '', type: '', domain: '', base_url: '',
    auth_type: 'cookie', auth_cookie: '', auth_passkey: '', auth_username: '', auth_password: '',
    sync_enabled: true, sync_strategy: 'time_based', sync_interval: 60, request_interval: 3, max_requests_per_day: 1000
  })
  proxyEnabled.value = false
  Object.assign(proxyConfig, { type: 'http', host: '', port: 7890, username: '', password: '' })
  activeTab.value = 'basic'
}

const handleDialogClose = () => {
  resetForm()
  currentEditId.value = null
  currentEditSite.value = null
}

const handleProxyToggle = (enabled: string | number | boolean) => {
  if (!enabled) Object.assign(proxyConfig, { type: 'http', host: '', port: 7890, username: '', password: '' })
}

const handleSortChange = ({ prop, order }: any) => {
  console.log('Sort:', prop, order)
}

onMounted(() => { loadSites() })
</script>

<style scoped>
.sites-settings {
  padding: 20px;
}

/* 工具栏 */
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 10px;
}

.toolbar-left,
.toolbar-right {
  display: flex;
  gap: 10px;
  align-items: center;
}

/* 站点卡片网格 */
.site-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
  min-height: 100px;
}

.site-card {
  background: var(--bg-color-light);
  border: 1px solid var(--border-color-light);
  border-radius: var(--border-radius-md);
  padding: 18px;
  padding-top: 15px;
  transition: box-shadow 0.2s, transform 0.2s, border-color 0.2s;
  display: flex;
  flex-direction: column;
  gap: 14px;
  overflow: hidden;
  position: relative;
}

.site-card:hover {
  box-shadow: var(--box-shadow-md);
  transform: translateY(-2px);
  border-color: var(--site-accent, var(--border-color));
}

/* 顶部彩色强调条 */
.card-accent-bar {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: var(--site-accent, var(--primary-color));
  border-radius: var(--border-radius-md) var(--border-radius-md) 0 0;
}

.site-card--error {
  border-color: var(--danger-color);
}

.site-card--add {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: 10px;
  cursor: pointer;
  border-style: dashed;
  border-color: var(--border-color);
  min-height: 200px;
}

.site-card--add:hover {
  border-color: var(--primary-color);
  background: var(--bg-color-overlay);
}

.add-text {
  font-size: 14px;
  color: var(--text-color-muted);
}

/* 卡片头部 */
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.card-title-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* 站点 Logo */
.site-logo {
  width: 42px;
  height: 42px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 800;
  color: #fff;
  flex-shrink: 0;
  letter-spacing: 1px;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.15);
}

.site-logo--sm {
  width: 32px;
  height: 32px;
  font-size: 11px;
  border-radius: 8px;
}

.card-title-info {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.site-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-color-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 状态标签 */
.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  padding: 1px 8px;
  border-radius: 10px;
  background: var(--bg-color-overlay);
  color: var(--text-color-secondary);
  width: fit-content;
}

.badge--active {
  background: rgba(16, 185, 129, 0.08);
  color: var(--success-color);
}

.badge--healthy {
  background: rgba(16, 185, 129, 0.08);
  color: var(--success-color);
}

.badge--inactive {
  background: rgba(148, 163, 184, 0.1);
  color: var(--text-color-muted);
}

.badge--error {
  background: rgba(239, 68, 68, 0.08);
  color: var(--danger-color);
}

.badge--unhealthy {
  background: rgba(245, 158, 11, 0.08);
  color: var(--warning-color);
}

.badge--unknown {
  background: rgba(148, 163, 184, 0.1);
  color: var(--text-color-muted);
}

.status-dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.dot--active,
.dot--healthy {
  background: var(--success-color);
}

.dot--inactive,
.dot--unknown {
  background: var(--text-color-muted);
}

.dot--error {
  background: var(--danger-color);
}

.dot--unhealthy {
  background: var(--warning-color);
}

/* 用户信息 */
.user-profile-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.user-profile-empty {
  padding: 12px;
  display: flex;
  justify-content: center;
}

.profile-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.profile-username {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-color-primary);
}

/* 主要指标：上传 / 下载 / 分享率 */
.primary-metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 6px;
}

.metric-item {
  background: var(--bg-color-page, var(--bg-color-overlay));
  border: 1px solid var(--border-color-light);
  border-radius: 8px;
  padding: 8px 10px;
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}

.metric-label {
  font-size: 10px;
  color: var(--text-color-muted);
  letter-spacing: 0.3px;
  white-space: nowrap;
}

.metric-value {
  font-size: 13px;
  font-weight: 700;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: var(--text-color-primary);
}

.metric-upload .metric-value {
  color: var(--primary-color);
}

.metric-download .metric-value {
  color: var(--warning-color);
}

.metric-ratio-good .metric-value {
  color: var(--success-color);
}

.metric-ratio-bad .metric-value {
  color: var(--danger-color);
}

.metric-ratio-good {
  border-color: rgba(16, 185, 129, 0.2);
  background: rgba(16, 185, 129, 0.05);
}

.metric-ratio-bad {
  border-color: rgba(239, 68, 68, 0.2);
  background: rgba(239, 68, 68, 0.05);
}

/* 次要指标：做种 / 做种量 / 积分 */
.secondary-metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0 8px;
  padding: 6px 10px;
  background: var(--bg-color-overlay);
  border-radius: 8px;
  border: 1px solid var(--border-color-light);
}

.sec-metric {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.sec-label {
  font-size: 10px;
  color: var(--text-color-muted);
  white-space: nowrap;
}

.sec-value {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-color-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.ratio-good {
  color: var(--success-color);
}

/* 表格视图样式 */
.table-site-name {
  display: flex;
  align-items: center;
  gap: 10px;
}

.name-text {
  font-weight: 600;
  font-size: 14px;
  color: var(--text-color-primary);
}

.table-profile-name {
  font-weight: 600;
  font-size: 13px;
  color: var(--text-color-primary);
}

.table-cell-value {
  font-size: 13px;
  color: var(--text-color-primary);
}

.text-muted {
  color: var(--text-color-muted);
}

/* 分页 */
.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

/* 响应式 */
@media (max-width: 768px) {
  .site-cards {
    grid-template-columns: 1fr;
  }

  .toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .toolbar-left,
  .toolbar-right {
    flex-wrap: wrap;
  }
}
</style>
