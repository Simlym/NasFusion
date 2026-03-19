<template>
  <div class="notification-templates-container">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-left">
        <el-button icon="ArrowLeft" @click="goBack">返回</el-button>
        <h2>通知模板管理</h2>
      </div>
      <div class="header-right">
        <el-button type="success" icon="Refresh" :loading="initializing" @click="initSystemTemplates">
          初始化系统模板
        </el-button>
        <el-button type="primary" icon="Plus" @click="createTemplate">创建模板</el-button>
      </div>
    </div>

    <!-- 筛选区域 -->
    <el-card class="filter-card">
      <el-form :inline="true" :model="filterForm">
        <el-form-item label="事件类型">
          <el-select v-model="filterForm.eventType" placeholder="全部" clearable style="width: 200px">
            <el-option
              v-for="event in eventTypes"
              :key="event.value"
              :label="event.label"
              :value="event.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="语言">
          <el-select v-model="filterForm.language" placeholder="全部" clearable style="width: 120px">
            <el-option label="简体中文" value="zh-CN" />
            <el-option label="English" value="en-US" />
          </el-select>
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="filterForm.isSystem" placeholder="全部" clearable style="width: 120px">
            <el-option label="系统模板" :value="true" />
            <el-option label="自定义模板" :value="false" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" icon="Search" @click="loadTemplates">查询</el-button>
          <el-button icon="Refresh" @click="resetFilters">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 模板列表 -->
    <el-card class="templates-card">
      <el-table v-loading="loading" :data="templates" stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="模板名称" min-width="200" />
        <el-table-column prop="eventType" label="事件类型" width="180">
          <template #default="{ row }">
            <el-tag>{{ getEventTypeName(row.eventType) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="language" label="语言" width="100">
          <template #default="{ row }">
            <el-tag type="info" size="small">{{ getLanguageName(row.language) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="format" label="格式" width="100">
          <template #default="{ row }">
            <el-tag :type="row.format === 'markdown' ? 'success' : ''">{{ row.format }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="变量" width="150">
          <template #default="{ row }">
            <el-tag
              v-for="variable in row.variables?.slice(0, 3)"
              :key="variable"
              size="small"
              style="margin-right: 5px"
            >
              {{ variable }}
            </el-tag>
            <el-tag v-if="row.variables && row.variables.length > 3" size="small" type="info">
              +{{ row.variables.length - 3 }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="isSystem" label="类型" width="100">
          <template #default="{ row }">
            <el-tag :type="row.isSystem ? 'warning' : 'success'">
              {{ row.isSystem ? '系统' : '自定义' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="viewTemplate(row)">查看</el-button>
            <el-button link type="success" size="small" @click="previewTemplate(row)">
              预览
            </el-button>
            <el-dropdown @command="(cmd) => handleTemplateCommand(cmd, row)">
              <el-button link type="info" size="small">
                更多<el-icon class="el-icon--right"><ArrowDown /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item
                    v-if="!row.isSystem"
                    command="edit"
                    icon="Edit"
                  >
                    编辑
                  </el-dropdown-item>
                  <el-dropdown-item
                    v-if="!row.isSystem"
                    command="delete"
                    icon="Delete"
                    divided
                  >
                    删除
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :total="pagination.total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        style="margin-top: 20px; justify-content: center"
        @size-change="loadTemplates"
        @current-change="loadTemplates"
      />
    </el-card>

    <!-- 模板编辑对话框 -->
    <el-dialog
      v-model="templateDialogVisible"
      :title="isEditMode ? '编辑模板' : isViewMode ? '查看模板' : '创建模板'"
      width="900px"
      @close="resetTemplateForm"
    >
      <el-form
        ref="templateFormRef"
        :model="templateForm"
        :rules="templateFormRules"
        label-width="120px"
        :disabled="isViewMode"
      >
        <!-- 基本信息 -->
        <el-divider content-position="left">基本信息</el-divider>
        <el-form-item label="模板名称" prop="name">
          <el-input v-model="templateForm.name" placeholder="请输入模板名称" />
        </el-form-item>
        <el-form-item label="事件类型" prop="eventType">
          <el-select
            v-model="templateForm.eventType"
            placeholder="请选择事件类型"
            style="width: 100%"
            @change="onEventTypeChange"
          >
            <el-option-group
              v-for="group in eventTypeGroups"
              :key="group.label"
              :label="group.label"
            >
              <el-option
                v-for="event in group.options"
                :key="event.value"
                :label="event.label"
                :value="event.value"
              >
                <div style="display: flex; justify-content: space-between">
                  <span>{{ event.label }}</span>
                  <span style="color: #999; font-size: 12px">{{ event.description }}</span>
                </div>
              </el-option>
            </el-option-group>
          </el-select>
        </el-form-item>
        <el-form-item label="语言" prop="language">
          <el-select v-model="templateForm.language" placeholder="请选择语言" style="width: 100%">
            <el-option label="简体中文" value="zh-CN" />
            <el-option label="English" value="en-US" />
          </el-select>
        </el-form-item>
        <el-form-item label="格式" prop="format">
          <el-select v-model="templateForm.format" placeholder="请选择格式" style="width: 100%">
            <el-option label="纯文本" value="text" />
            <el-option label="Markdown" value="markdown" />
            <el-option label="HTML" value="html" />
          </el-select>
        </el-form-item>

        <!-- 可用变量提示 -->
        <el-alert
          v-if="availableVariables.length > 0"
          :title="`可用变量: ${availableVariables.join(', ')}`"
          type="info"
          :closable="false"
          style="margin-bottom: 20px"
        >
          <template #default>
            <p style="margin: 5px 0">在模板中使用变量格式: &#123;&#123; variable_name &#125;&#125;</p>
            <p style="margin: 5px 0; font-size: 12px; color: #666">
              例如: &#123;&#123; media_name &#125;&#125;, &#123;&#123; quality &#125;&#125;, &#123;&#123; size_gb &#125;&#125;
            </p>
          </template>
        </el-alert>

        <!-- 模板内容 -->
        <el-divider content-position="left">模板内容</el-divider>
        <el-form-item label="标题模板" prop="titleTemplate">
          <el-input
            v-model="templateForm.titleTemplate"
            placeholder="例如: 【订阅匹配】{{ media_name }}"
            @blur="validateTemplateField('title')"
          />
          <div v-if="titleValidation.errors.length > 0" class="validation-error">
            <el-icon color="red"><WarningFilled /></el-icon>
            <span v-for="(error, index) in titleValidation.errors" :key="index">{{ error }}</span>
          </div>
          <div v-else-if="titleValidation.variables.length > 0" class="validation-success">
            <el-icon color="green"><SuccessFilled /></el-icon>
            <span>检测到变量: {{ titleValidation.variables.join(', ') }}</span>
          </div>
        </el-form-item>
        <el-form-item label="内容模板" prop="contentTemplate">
          <el-input
            v-model="templateForm.contentTemplate"
            type="textarea"
            :rows="8"
            placeholder="输入模板内容，使用 {{ variable }} 引用变量"
            @blur="validateTemplateField('content')"
          />
          <div v-if="contentValidation.errors.length > 0" class="validation-error">
            <el-icon color="red"><WarningFilled /></el-icon>
            <span v-for="(error, index) in contentValidation.errors" :key="index">{{ error }}</span>
          </div>
          <div v-else-if="contentValidation.variables.length > 0" class="validation-success">
            <el-icon color="green"><SuccessFilled /></el-icon>
            <span>检测到变量: {{ contentValidation.variables.join(', ') }}</span>
          </div>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="templateDialogVisible = false">
          {{ isViewMode ? '关闭' : '取消' }}
        </el-button>
        <el-button v-if="!isViewMode" type="primary" :loading="saving" @click="saveTemplate">
          保存
        </el-button>
      </template>
    </el-dialog>

    <!-- 预览对话框 -->
    <el-dialog v-model="previewDialogVisible" title="模板预览" width="700px">
      <el-alert
        title="输入测试数据预览渲染效果"
        type="info"
        :closable="false"
        style="margin-bottom: 20px"
      />

      <el-form label-width="120px">
        <el-form-item label="模板名称">
          <el-tag>{{ currentPreviewTemplate?.name }}</el-tag>
        </el-form-item>
        <el-form-item label="测试数据">
          <el-input
            v-model="previewVariables"
            type="textarea"
            :rows="6"
            placeholder='输入 JSON 格式的变量数据，例如: {"media_name": "复仇者联盟", "quality": "1080p"}'
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="rendering" @click="renderPreview">渲染预览</el-button>
        </el-form-item>
      </el-form>

      <!-- 渲染结果 -->
      <el-card v-if="renderResult" class="preview-result" shadow="never">
        <template #header>
          <div style="display: flex; justify-content: space-between; align-items: center">
            <span>渲染结果</span>
            <el-tag type="success">{{ currentPreviewTemplate?.format }}</el-tag>
          </div>
        </template>
        <div class="preview-content">
          <div class="preview-item">
            <div class="preview-label">标题:</div>
            <div class="preview-value">{{ renderResult.title }}</div>
          </div>
          <el-divider />
          <div class="preview-item">
            <div class="preview-label">内容:</div>
            <div
              class="preview-value"
              v-html="formatPreviewContent(renderResult.content)"
            ></div>
          </div>
        </div>
      </el-card>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, FormInstance, FormRules } from 'element-plus'
import { WarningFilled, SuccessFilled, ArrowDown } from '@element-plus/icons-vue'
import {
  getNotificationTemplateList,
  createNotificationTemplate,
  updateNotificationTemplate,
  deleteNotificationTemplate,
  validateNotificationTemplate,
  renderNotificationTemplate,
  initSystemTemplates as initSystemTemplatesAPI
} from '@/api/modules/notification'
import type { NotificationTemplate, NotificationTemplateForm } from '@/types'

const router = useRouter()

// 事件类型分组定义
const eventTypeGroups = [
  {
    label: '📺 订阅相关',
    options: [
      { value: 'subscription_matched', label: '订阅匹配', description: '订阅资源匹配成功时' },
      { value: 'subscription_downloaded', label: '订阅下载', description: '订阅资源下载完成时' },
      { value: 'subscription_completed', label: '订阅完成', description: '订阅全部完成时' },
      { value: 'subscription_no_resource', label: '订阅无资源', description: '订阅没有可用资源时' }
    ]
  },
  {
    label: '⬇️ 下载相关',
    options: [
      { value: 'download_started', label: '下载开始', description: '下载任务开始时' },
      { value: 'download_completed', label: '下载完成', description: '下载任务完成时' },
      { value: 'download_failed', label: '下载失败', description: '下载任务失败时' },
      { value: 'download_paused', label: '下载暂停', description: '下载任务暂停时' }
    ]
  },
  {
    label: '🎯 资源相关',
    options: [
      { value: 'resource_free_promotion', label: '免费促销', description: '发现免费促销资源时' },
      { value: 'resource_2x_promotion', label: '2倍促销', description: '发现2倍促销资源时' },
      { value: 'resource_high_quality', label: '高质量资源', description: '发现高质量资源时' }
    ]
  },
  {
    label: '🌐 PT站点相关',
    options: [
      { value: 'site_connection_failed', label: '站点连接失败', description: 'PT站点连接失败时' },
      { value: 'site_auth_expired', label: '站点认证过期', description: 'PT站点认证过期时' },
      { value: 'site_sync_completed', label: '站点同步完成', description: 'PT站点资源同步完成时' }
    ]
  },
  {
    label: '📁 媒体文件相关',
    options: [
      { value: 'media_scan_completed', label: '媒体扫描完成', description: '媒体文件扫描完成时' },
      { value: 'media_organized', label: '媒体整理完成', description: '媒体文件整理完成时' },
      { value: 'media_metadata_scraped', label: '媒体元数据刮削', description: '媒体元数据刮削完成时' }
    ]
  },
  {
    label: '⚙️ 任务相关',
    options: [
      { value: 'task_failed', label: '任务失败', description: '后台任务执行失败时' },
      { value: 'task_completed', label: '任务完成', description: '后台任务执行完成时' }
    ]
  },
  {
    label: '🖥️ 系统相关',
    options: [
      { value: 'system_error', label: '系统错误', description: '系统发生错误时' },
      { value: 'disk_space_low', label: '磁盘空间不足', description: '磁盘空间不足时' },
      { value: 'user_login_anomaly', label: '用户登录异常', description: '检测到异常登录时' },
      { value: 'system_update_available', label: '系统更新可用', description: '有新版本可用时' }
    ]
  }
]

// 扁平化的事件类型列表，用于查找
const eventTypes = eventTypeGroups.flatMap(group => group.options)

// 事件类型变量映射
const eventVariablesMap: Record<string, string[]> = {
  // 订阅相关
  'subscription_matched': [
    'media_name',
    'quality',
    'size_gb',
    'site_name',
    'promotion_type',
    'seeders',
    'leechers'
  ],
  'subscription_downloaded': ['media_name', 'size_gb', 'site_name', 'save_path'],
  'subscription_completed': ['media_name', 'total_episodes', 'downloaded_episodes', 'duration'],
  'subscription_no_resource': ['media_name', 'subscription_id', 'last_check_at'],

  // 下载相关
  'download_started': ['media_name', 'size_gb', 'torrent_hash', 'site_name'],
  'download_completed': ['media_name', 'size_gb', 'save_path', 'duration', 'ratio'],
  'download_failed': ['media_name', 'error_message', 'torrent_hash', 'retry_count'],
  'download_paused': ['media_name', 'progress', 'reason'],

  // 资源相关
  'resource_free_promotion': ['media_name', 'site_name', 'size_gb', 'promotion_end_at'],
  'resource_2x_promotion': ['media_name', 'site_name', 'size_gb', 'promotion_end_at'],
  'resource_high_quality': ['media_name', 'site_name', 'quality', 'size_gb', 'seeders'],

  // PT站点相关
  'site_connection_failed': ['site_name', 'error_message', 'last_success_at'],
  'site_auth_expired': ['site_name', 'expired_at'],
  'site_sync_completed': ['site_name', 'resources_count', 'duration'],

  // 媒体文件相关
  'media_scan_completed': ['directory', 'files_found', 'duration'],
  'media_organized': ['media_name', 'source_path', 'target_path', 'media_type'],
  'media_metadata_scraped': ['media_name', 'tmdb_id', 'source'],

  // 任务相关
  'task_failed': ['task_name', 'error_message', 'task_type'],
  'task_completed': ['task_name', 'duration', 'result'],

  // 系统相关
  'system_error': ['error_type', 'error_message', 'timestamp', 'module'],
  'disk_space_low': ['disk_path', 'available_gb', 'total_gb', 'usage_percent'],
  'user_login_anomaly': ['username', 'ip_address', 'login_at', 'reason'],
  'system_update_available': ['current_version', 'new_version', 'release_notes']
}

// 列表数据
const loading = ref(false)
const templates = ref<NotificationTemplate[]>([])

// 筛选条件
const filterForm = reactive({
  eventType: '',
  language: '',
  isSystem: undefined as boolean | undefined
})

// 分页
const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

// 对话框
const templateDialogVisible = ref(false)
const isEditMode = ref(false)
const isViewMode = ref(false)
const saving = ref(false)
const templateFormRef = ref<FormInstance>()
const initializing = ref(false)

// 模板表单
const templateForm = reactive<NotificationTemplateForm & { _id?: number }>({
  name: '',
  eventType: '',
  language: 'zh-CN',
  format: 'text',
  titleTemplate: '',
  contentTemplate: '',
  variables: []
})

const templateFormRules: FormRules = {
  name: [{ required: true, message: '请输入模板名称', trigger: 'blur' }],
  eventType: [{ required: true, message: '请选择事件类型', trigger: 'change' }],
  language: [{ required: true, message: '请选择语言', trigger: 'change' }],
  format: [{ required: true, message: '请选择格式', trigger: 'change' }],
  titleTemplate: [{ required: true, message: '请输入标题模板', trigger: 'blur' }],
  contentTemplate: [{ required: true, message: '请输入内容模板', trigger: 'blur' }]
}

// 模板验证
interface ValidationResult {
  valid: boolean
  errors: string[]
  variables: string[]
}

const titleValidation = reactive<ValidationResult>({ valid: true, errors: [], variables: [] })
const contentValidation = reactive<ValidationResult>({ valid: true, errors: [], variables: [] })

// 预览对话框
const previewDialogVisible = ref(false)
const currentPreviewTemplate = ref<NotificationTemplate | null>(null)
const previewVariables = ref('')
const renderResult = ref<{ title: string; content: string } | null>(null)
const rendering = ref(false)

// 计算可用变量
const availableVariables = computed(() => {
  return eventVariablesMap[templateForm.eventType] || []
})

// 加载模板列表
const loadTemplates = async () => {
  loading.value = true
  try {
    const params: any = {}

    if (filterForm.eventType) {
      params.eventType = filterForm.eventType
    }
    if (filterForm.language) {
      params.language = filterForm.language
    }
    if (filterForm.isSystem !== undefined) {
      params.isSystem = filterForm.isSystem
    }

    const res = await getNotificationTemplateList(params)
    if (res.data) {
      templates.value = res.data.items || []
      pagination.total = res.data.total || 0
    }
  } catch (error) {
    console.error('Failed to load templates:', error)
    ElMessage.error('加载模板列表失败')
  } finally {
    loading.value = false
  }
}

// 初始化系统模板
const initSystemTemplates = async () => {
  try {
    await ElMessageBox.confirm(
      '此操作将初始化所有系统模板（已存在的不会重复创建），是否继续？',
      '确认初始化',
      { type: 'info' }
    )

    initializing.value = true
    const res = await initSystemTemplatesAPI()
    if (res.data) {
      ElMessage.success(res.data.message || '初始化成功')
      await loadTemplates()
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Failed to init system templates:', error)
      ElMessage.error('初始化失败')
    }
  } finally {
    initializing.value = false
  }
}

// 创建模板
const createTemplate = () => {
  isEditMode.value = false
  isViewMode.value = false
  resetTemplateForm()
  templateDialogVisible.value = true
}

// 查看模板
const viewTemplate = (template: NotificationTemplate) => {
  isEditMode.value = false
  isViewMode.value = true
  loadTemplateData(template)
  templateDialogVisible.value = true
}

// 编辑模板
const editTemplate = (template: NotificationTemplate) => {
  isEditMode.value = true
  isViewMode.value = false
  loadTemplateData(template)
  templateDialogVisible.value = true
}

// 加载模板数据到表单
const loadTemplateData = (template: NotificationTemplate) => {
  Object.assign(templateForm, {
    name: template.name,
    eventType: template.eventType,
    language: template.language,
    format: template.format,
    titleTemplate: template.titleTemplate,
    contentTemplate: template.contentTemplate,
    variables: template.variables || [],
    _id: template.id
  })

  // 重置验证状态
  titleValidation.valid = true
  titleValidation.errors = []
  titleValidation.variables = template.variables || []
  contentValidation.valid = true
  contentValidation.errors = []
  contentValidation.variables = template.variables || []
}

// 事件类型变化
const onEventTypeChange = () => {
  // 清空验证状态
  titleValidation.errors = []
  titleValidation.variables = []
  contentValidation.errors = []
  contentValidation.variables = []
}

// 验证模板字段
const validateTemplateField = async (field: 'title' | 'content') => {
  const templateStr = field === 'title' ? templateForm.titleTemplate : templateForm.contentTemplate
  const validation = field === 'title' ? titleValidation : contentValidation

  if (!templateStr) {
    validation.valid = true
    validation.errors = []
    validation.variables = []
    return
  }

  try {
    const res = await validateNotificationTemplate(templateStr)
    if (res.data) {
      validation.valid = res.data.valid
      validation.errors = res.data.errors || []
      validation.variables = res.data.variables || []
    }
  } catch (error) {
    console.error('Failed to validate template:', error)
  }
}

// 保存模板
const saveTemplate = async () => {
  if (!templateFormRef.value) return

  await templateFormRef.value.validate(async (valid) => {
    if (!valid) return

    // 验证模板语法
    await validateTemplateField('title')
    await validateTemplateField('content')

    if (!titleValidation.valid || !contentValidation.valid) {
      ElMessage.error('模板语法错误，请检查')
      return
    }

    saving.value = true
    try {
      const data: NotificationTemplateForm = {
        name: templateForm.name,
        eventType: templateForm.eventType,
        language: templateForm.language,
        format: templateForm.format,
        titleTemplate: templateForm.titleTemplate,
        contentTemplate: templateForm.contentTemplate,
        variables: [...titleValidation.variables, ...contentValidation.variables]
      }

      if (isEditMode.value && templateForm._id) {
        await updateNotificationTemplate(templateForm._id, data)
        ElMessage.success('模板更新成功')
      } else {
        await createNotificationTemplate(data)
        ElMessage.success('模板创建成功')
      }

      templateDialogVisible.value = false
      await loadTemplates()
    } catch (error) {
      console.error('Failed to save template:', error)
      ElMessage.error('保存失败')
    } finally {
      saving.value = false
    }
  })
}

// 处理模板下拉菜单命令
const handleTemplateCommand = (command: string, template: NotificationTemplate) => {
  if (command === 'edit') {
    editTemplate(template)
  } else if (command === 'delete') {
    deleteTemplate(template)
  }
}

// 删除模板
const deleteTemplate = async (template: NotificationTemplate) => {
  try {
    await ElMessageBox.confirm(`确定要删除模板"${template.name}"吗？`, '确认删除', {
      type: 'warning'
    })

    await deleteNotificationTemplate(template.id)
    ElMessage.success('删除成功')
    await loadTemplates()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Failed to delete template:', error)
      ElMessage.error('删除失败')
    }
  }
}

// 预览模板
const previewTemplate = (template: NotificationTemplate) => {
  currentPreviewTemplate.value = template
  const variables = eventVariablesMap[template.eventType] || []
  const sampleData: Record<string, any> = {}

  // 生成示例数据
  variables.forEach((variable) => {
    if (variable === 'media_name') sampleData[variable] = '复仇者联盟4'
    else if (variable === 'quality') sampleData[variable] = '1080p'
    else if (variable === 'size_gb') sampleData[variable] = 15.5
    else if (variable === 'site_name') sampleData[variable] = 'MTeam'
    else if (variable === 'promotion_type') sampleData[variable] = '免费'
    else sampleData[variable] = `示例${variable}`
  })

  previewVariables.value = JSON.stringify(sampleData, null, 2)
  renderResult.value = null
  previewDialogVisible.value = true
}

// 渲染预览
const renderPreview = async () => {
  if (!currentPreviewTemplate.value) return

  rendering.value = true
  try {
    const variables = JSON.parse(previewVariables.value)
    const res = await renderNotificationTemplate(currentPreviewTemplate.value.id, variables)
    if (res.data) {
      renderResult.value = res.data
    }
  } catch (error) {
    console.error('Failed to render preview:', error)
    ElMessage.error('渲染失败，请检查输入的 JSON 格式')
  } finally {
    rendering.value = false
  }
}

// 格式化预览内容
const formatPreviewContent = (content: string) => {
  if (currentPreviewTemplate.value?.format === 'markdown') {
    // 简单的 Markdown 渲染（实际项目中应使用专业的 Markdown 渲染库）
    return content
      .replace(/\n/g, '<br>')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
  } else if (currentPreviewTemplate.value?.format === 'html') {
    return content
  } else {
    return content.replace(/\n/g, '<br>')
  }
}

// 重置筛选
const resetFilters = () => {
  filterForm.eventType = ''
  filterForm.language = ''
  filterForm.isSystem = undefined
  pagination.page = 1
  loadTemplates()
}

// 重置表单
const resetTemplateForm = () => {
  Object.assign(templateForm, {
    name: '',
    eventType: '',
    language: 'zh-CN',
    format: 'text',
    titleTemplate: '',
    contentTemplate: '',
    variables: [],
    _id: undefined
  })
  titleValidation.valid = true
  titleValidation.errors = []
  titleValidation.variables = []
  contentValidation.valid = true
  contentValidation.errors = []
  contentValidation.variables = []
}

// 辅助函数
const getEventTypeName = (type: string) => {
  return eventTypes.find((e) => e.value === type)?.label || type
}

const getLanguageName = (lang: string) => {
  const langMap: Record<string, string> = {
    'zh-CN': '简中',
    'en-US': 'EN'
  }
  return langMap[lang] || lang
}

const goBack = () => {
  router.back()
}

// 初始化
onMounted(() => {
  loadTemplates()
})
</script>

<style scoped lang="scss">
.notification-templates-container {
  padding: 20px;

  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;

    .header-left {
      display: flex;
      align-items: center;
      gap: 15px;

      h2 {
        margin: 0;
        font-size: 24px;
        font-weight: 600;
      }
    }
  }

  .filter-card {
    margin-bottom: 20px;
  }

  .templates-card {
    min-height: 400px;
  }

  .validation-error {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-top: 8px;
    color: #f56c6c;
    font-size: 12px;
  }

  .validation-success {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-top: 8px;
    color: #67c23a;
    font-size: 12px;
  }

  .preview-result {
    margin-top: 20px;

    .preview-content {
      .preview-item {
        margin-bottom: 15px;

        .preview-label {
          font-weight: 600;
          margin-bottom: 8px;
          color: #606266;
        }

        .preview-value {
          padding: 12px;
          background: #f5f7fa;
          border-radius: 4px;
          line-height: 1.6;
        }
      }
    }
  }
}
</style>
