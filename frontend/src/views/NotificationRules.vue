<template>
  <div class="notification-rules-container">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-left">
        <el-button icon="ArrowLeft" @click="goBack">返回</el-button>
        <h2>通知规则管理</h2>
      </div>
      <div class="header-right">
        <el-button type="primary" icon="Plus" @click="createRule">创建规则</el-button>
      </div>
    </div>

    <!-- 筛选区域 -->
    <el-card class="filter-card">
      <el-form :inline="true" :model="filterForm">
        <el-form-item label="事件类型">
          <el-select
            v-model="filterForm.eventType"
            placeholder="全部"
            clearable
            style="width: 250px"
            filterable
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
              />
            </el-option-group>
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filterForm.enabled" placeholder="全部" clearable style="width: 120px">
            <el-option label="已启用" :value="true" />
            <el-option label="已禁用" :value="false" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" icon="Search" @click="loadRules">查询</el-button>
          <el-button icon="Refresh" @click="resetFilters">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 规则列表 -->
    <el-card class="rules-card">
      <el-table v-loading="loading" :data="rules" stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="规则名称" min-width="200" />
        <el-table-column prop="eventType" label="事件类型" width="200">
          <template #default="{ row }">
            <el-tag>{{ getEventTypeName(row.eventType) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="通知渠道" width="200">
          <template #default="{ row }">
            <el-tag
              v-for="channelId in row.channelIds"
              :key="channelId"
              size="small"
              style="margin-right: 5px"
            >
              {{ getChannelName(channelId) }}
            </el-tag>
            <el-tag v-if="row.sendInApp" type="info" size="small">站内信</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="条件" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.conditions && Object.keys(row.conditions).length > 0" type="warning">
              {{ Object.keys(row.conditions).length }} 个
            </el-tag>
            <span v-else style="color: #999">无条件</span>
          </template>
        </el-table-column>
        <el-table-column label="静默时段" width="100">
          <template #default="{ row }">
            <el-icon v-if="row.silentHours?.enabled" color="orange">
              <BellFilled />
            </el-icon>
            <span v-else style="color: #999">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="enabled" label="状态" width="100">
          <template #default="{ row }">
            <el-switch
              v-model="row.enabled"
              :loading="row._toggling"
              @change="toggleRule(row)"
            />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="210" fixed="right">
          <template #default="{ row }">
            <el-button link type="warning" size="small" @click="editRule(row)">编辑</el-button>
            <el-button link type="primary" size="small" @click="testRule(row)">测试</el-button>
            <el-button link type="danger" size="small" @click="deleteRule(row)">删除</el-button>
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
        @size-change="loadRules"
        @current-change="loadRules"
      />
    </el-card>

    <!-- 规则编辑对话框 -->
    <el-dialog
      v-model="ruleDialogVisible"
      :title="isEditMode ? '编辑规则' : '创建规则'"
      width="800px"
      @close="resetRuleForm"
    >
      <el-form
        ref="ruleFormRef"
        :model="ruleForm"
        :rules="ruleFormRules"
        label-width="120px"
      >
        <!-- 基本信息 -->
        <el-divider content-position="left">基本信息</el-divider>
        <el-form-item label="规则名称" prop="name">
          <el-input v-model="ruleForm.name" placeholder="请输入规则名称" />
        </el-form-item>
        <el-form-item label="事件类型" prop="eventType">
          <el-select
            v-model="ruleForm.eventType"
            placeholder="请选择事件类型"
            style="width: 100%"
            filterable
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
        <el-form-item label="启用规则" prop="enabled">
          <el-switch v-model="ruleForm.enabled" />
        </el-form-item>
        <el-form-item label="优先级" prop="priority">
          <el-select v-model="ruleForm.priority" placeholder="请选择优先级" style="width: 100%">
            <el-option label="低" value="low" />
            <el-option label="普通" value="medium" />
            <el-option label="高" value="high" />
            <el-option label="紧急" value="urgent" />
          </el-select>
        </el-form-item>

        <!-- 通知渠道 -->
        <el-divider content-position="left">通知渠道</el-divider>
        <el-form-item label="发送站内信">
          <el-switch v-model="ruleForm.sendInApp" />
        </el-form-item>
        <el-form-item label="外部渠道" prop="channelIds">
          <el-select
            v-model="ruleForm.channelIds"
            multiple
            placeholder="请选择通知渠道"
            style="width: 100%"
          >
            <el-option
              v-for="channel in availableChannels"
              :key="channel.id"
              :label="channel.name"
              :value="channel.id"
              :disabled="!channel.isActive"
            >
              <div style="display: flex; justify-content: space-between; align-items: center">
                <span>
                  <el-tag :type="getChannelColor(channel.type)" size="small" style="margin-right: 8px">
                    {{ channel.type }}
                  </el-tag>
                  {{ channel.name }}
                </span>
                <el-tag v-if="!channel.isActive" type="danger" size="small">已禁用</el-tag>
              </div>
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="通知模板">
          <el-select
            v-model="ruleForm.templateId"
            placeholder="使用默认模板"
            clearable
            style="width: 100%"
          >
            <el-option
              v-for="template in availableTemplates"
              :key="template.id"
              :label="template.name"
              :value="template.id"
            />
          </el-select>
        </el-form-item>

        <!-- 触发条件 -->
        <el-divider content-position="left">触发条件（可选）</el-divider>
        <el-form-item label="过滤条件">
          <el-button
            size="small"
            icon="Plus"
            style="margin-bottom: 10px"
            @click="addCondition"
          >
            添加条件
          </el-button>
          <div v-for="(condition, index) in conditions" :key="index" class="condition-item">
            <el-select
              v-model="condition.field"
              placeholder="字段"
              style="width: 150px; margin-right: 10px"
            >
              <el-option label="文件大小(GB)" value="size_gb" />
              <el-option label="质量" value="quality" />
              <el-option label="促销类型" value="promotion_type" />
              <el-option label="站点名称" value="site_name" />
              <el-option label="媒体类型" value="media_type" />
            </el-select>
            <el-select
              v-model="condition.operator"
              placeholder="运算符"
              style="width: 120px; margin-right: 10px"
            >
              <el-option label="等于" value="eq" />
              <el-option label="不等于" value="ne" />
              <el-option label="大于" value="gt" />
              <el-option label="小于" value="lt" />
              <el-option label="大于等于" value="gte" />
              <el-option label="小于等于" value="lte" />
              <el-option label="包含" value="contains" />
              <el-option label="在列表中" value="in" />
            </el-select>
            <el-input
              v-model="condition.value"
              placeholder="值"
              style="width: 200px; margin-right: 10px"
            />
            <el-button
              icon="Delete"
              type="danger"
              size="small"
              @click="removeCondition(index)"
            />
          </div>
          <el-alert
            v-if="conditions.length === 0"
            title="无条件限制，所有事件都会触发通知"
            type="info"
            :closable="false"
            show-icon
          />
        </el-form-item>

        <!-- 高级设置 -->
        <el-divider content-position="left">高级设置</el-divider>
        <el-form-item label="静默时段">
          <el-switch v-model="silentHoursEnabled" />
        </el-form-item>
        <el-form-item v-if="silentHoursEnabled" label="时段设置">
          <el-button
            size="small"
            icon="Plus"
            style="margin-bottom: 10px"
            @click="addSilentPeriod"
          >
            添加时段
          </el-button>
          <div v-for="(period, index) in silentPeriods" :key="index" class="silent-period-item">
            <el-select
              v-model="period.days"
              multiple
              placeholder="选择星期（空表示每天）"
              style="width: 200px; margin-right: 10px"
            >
              <el-option label="周一" value="monday" />
              <el-option label="周二" value="tuesday" />
              <el-option label="周三" value="wednesday" />
              <el-option label="周四" value="thursday" />
              <el-option label="周五" value="friday" />
              <el-option label="周六" value="saturday" />
              <el-option label="周日" value="sunday" />
            </el-select>
            <el-time-picker
              v-model="period.start"
              placeholder="开始时间"
              format="HH:mm"
              value-format="HH:mm"
              style="width: 150px; margin-right: 10px"
            />
            <el-time-picker
              v-model="period.end"
              placeholder="结束时间"
              format="HH:mm"
              value-format="HH:mm"
              style="width: 150px; margin-right: 10px"
            />
            <el-button
              icon="Delete"
              type="danger"
              size="small"
              @click="removeSilentPeriod(index)"
            />
          </div>
        </el-form-item>
        <el-form-item label="去重窗口">
          <el-input-number
            v-model="ruleForm.deduplicationWindow"
            :min="0"
            :max="86400"
            :step="60"
            placeholder="秒"
            style="width: 200px"
          />
          <span style="margin-left: 10px; color: #999">
            在此时间内相同事件不会重复通知（0表示不去重）
          </span>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="ruleDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveRule">保存</el-button>
      </template>
    </el-dialog>

    <!-- 测试对话框 -->
    <el-dialog v-model="testDialogVisible" title="测试规则" width="600px">
      <el-alert
        title="发送测试事件来验证规则是否能正确触发"
        type="info"
        :closable="false"
        style="margin-bottom: 20px"
      />
      <el-form label-width="120px">
        <el-form-item label="事件类型">
          <el-tag>{{ getEventTypeName(currentTestRule?.eventType || '') }}</el-tag>
        </el-form-item>
        <el-form-item label="测试数据">
          <el-input
            v-model="testEventData"
            type="textarea"
            :rows="10"
            placeholder='输入 JSON 格式的测试数据，例如: {"size_gb": 10, "quality": "1080p"}'
          />
        </el-form-item>
      </el-form>

      <!-- 测试结果 -->
      <el-alert
        v-if="testResult"
        :title="testResult.shouldNotify ? '✅ 规则会触发通知' : '❌ 规则不会触发通知'"
        :type="testResult.shouldNotify ? 'success' : 'warning'"
        :closable="false"
        style="margin-top: 20px"
      >
        <template #default>
          <div style="margin-top: 10px">
            <p><strong>条件匹配:</strong> {{ testResult.conditionsMet ? '是' : '否' }}</p>
            <p><strong>静默时段:</strong> {{ testResult.inSilentHours ? '是（会被跳过）' : '否' }}</p>
            <p><strong>去重检查:</strong> {{ testResult.wouldDeduplicate ? '是（会被跳过）' : '否' }}</p>
            <el-divider />
            <pre style="background: #f5f5f5; padding: 10px; border-radius: 4px; overflow: auto">{{
              JSON.stringify(testResult.details, null, 2)
            }}</pre>
          </div>
        </template>
      </el-alert>

      <template #footer>
        <el-button @click="testDialogVisible = false">关闭</el-button>
        <el-button type="primary" :loading="testing" @click="runTest">运行测试</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, FormInstance, FormRules } from 'element-plus'
import { BellFilled } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import {
  getNotificationRuleList,
  createNotificationRule,
  updateNotificationRule,
  deleteNotificationRule,
  testNotificationRule,
  toggleNotificationRule,
  getNotificationChannelList,
  getNotificationTemplateList
} from '@/api/modules/notification'
import type {
  NotificationRule,
  NotificationRuleForm,
  NotificationChannel,
  NotificationTemplate
} from '@/types'

const router = useRouter()
const userStore = useUserStore()

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

// 列表数据
const loading = ref(false)
const rules = ref<NotificationRule[]>([])
const availableChannels = ref<NotificationChannel[]>([])
const availableTemplates = ref<NotificationTemplate[]>([])

// 筛选条件
const filterForm = reactive({
  eventType: '',
  enabled: undefined as boolean | undefined
})

// 分页
const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

// 对话框
const ruleDialogVisible = ref(false)
const isEditMode = ref(false)
const saving = ref(false)
const ruleFormRef = ref<FormInstance>()

// 规则表单
const ruleForm = reactive<NotificationRuleForm>({
  name: '',
  enabled: true,
  eventType: '',
  conditions: {},
  channelIds: [],
  sendInApp: true,
  templateId: undefined,
  silentHours: undefined,
  deduplicationWindow: 0,
  priority: 'medium'
})

const ruleFormRules: FormRules = {
  name: [{ required: true, message: '请输入规则名称', trigger: 'blur' }],
  eventType: [{ required: true, message: '请选择事件类型', trigger: 'change' }]
}

// 条件构建器
interface Condition {
  field: string
  operator: string
  value: string
}

const conditions = ref<Condition[]>([])

const addCondition = () => {
  conditions.value.push({ field: '', operator: 'eq', value: '' })
}

const removeCondition = (index: number) => {
  conditions.value.splice(index, 1)
}

// 静默时段
interface SilentPeriod {
  days: string[]
  start: string
  end: string
}

const silentHoursEnabled = ref(false)
const silentPeriods = ref<SilentPeriod[]>([])

const addSilentPeriod = () => {
  silentPeriods.value.push({ days: [], start: '22:00', end: '08:00' })
}

const removeSilentPeriod = (index: number) => {
  silentPeriods.value.splice(index, 1)
}

// 测试对话框
const testDialogVisible = ref(false)
const currentTestRule = ref<NotificationRule | null>(null)
const testEventData = ref('')
const testResult = ref<any>(null)
const testing = ref(false)

// 加载规则列表
const loadRules = async () => {
  loading.value = true
  try {
    const params: any = {
      skip: (pagination.page - 1) * pagination.pageSize,
      limit: pagination.pageSize
    }

    if (filterForm.eventType) {
      params.eventType = filterForm.eventType
    }
    if (filterForm.enabled !== undefined) {
      params.enabled = filterForm.enabled
    }

    const res = await getNotificationRuleList(params)
    if (res.data) {
      rules.value = res.data.items || []
      pagination.total = res.data.total || 0
    }
  } catch (error) {
    console.error('Failed to load rules:', error)
    ElMessage.error('加载规则列表失败')
  } finally {
    loading.value = false
  }
}

// 加载可用渠道
const loadChannels = async () => {
  try {
    const res = await getNotificationChannelList()
    if (res.data) {
      availableChannels.value = res.data
    }
  } catch (error) {
    console.error('Failed to load channels:', error)
  }
}

// 加载可用模板
const loadTemplates = async () => {
  try {
    const res = await getNotificationTemplateList()
    if (res.data) {
      availableTemplates.value = res.data.items || []
    }
  } catch (error) {
    console.error('Failed to load templates:', error)
  }
}

// 创建规则
const createRule = () => {
  isEditMode.value = false
  resetRuleForm()
  ruleDialogVisible.value = true
}

// 编辑规则
const editRule = (rule: NotificationRule) => {
  isEditMode.value = true
  Object.assign(ruleForm, {
    name: rule.name,
    enabled: rule.enabled,
    eventType: rule.eventType,
    conditions: rule.conditions || {},
    channelIds: rule.channelIds || [],
    sendInApp: rule.sendInApp,
    templateId: rule.templateId,
    silentHours: rule.silentHours,
    deduplicationWindow: rule.deduplicationWindow || 0,
    priority: rule.priority || 'medium'
  })

  // 解析条件
  if (rule.conditions) {
    conditions.value = Object.entries(rule.conditions).map(([field, config]: [string, any]) => ({
      field,
      operator: config.operator || 'eq',
      value: String(config.value || '')
    }))
  } else {
    conditions.value = []
  }

  // 解析静默时段
  if (rule.silentHours && rule.silentHours.enabled) {
    silentHoursEnabled.value = true
    silentPeriods.value = rule.silentHours.periods || []
  } else {
    silentHoursEnabled.value = false
    silentPeriods.value = []
  }

  ruleForm._id = rule.id
  ruleDialogVisible.value = true
}

// 保存规则
const saveRule = async () => {
  if (!ruleFormRef.value) return

  await ruleFormRef.value.validate(async (valid) => {
    if (!valid) return

    saving.value = true
    try {
      // 构建条件对象
      const conditionsObj: Record<string, any> = {}
      conditions.value.forEach((cond) => {
        if (cond.field && cond.operator && cond.value) {
          conditionsObj[cond.field] = {
            operator: cond.operator,
            value: cond.value
          }
        }
      })

      // 构建静默时段
      let silentHours = undefined
      if (silentHoursEnabled.value && silentPeriods.value.length > 0) {
        silentHours = {
          enabled: true,
          periods: silentPeriods.value
        }
      }

      // 检查渠道选择
    if (!ruleForm.sendInApp && (!ruleForm.channelIds || ruleForm.channelIds.length === 0)) {
      ElMessage.error('请至少选择一种通知方式（站内信或外部渠道）')
      return
    }

    const data: any = {
        name: ruleForm.name,
        enabled: ruleForm.enabled,
        eventType: ruleForm.eventType,  // 使用前端字段名
        conditions: Object.keys(conditionsObj).length > 0 ? conditionsObj : undefined,
        channelIds: ruleForm.channelIds || [],  // 使用前端字段名
        sendInApp: ruleForm.sendInApp,   // 使用前端字段名
        templateId: ruleForm.templateId || undefined,  // 使用前端字段名
        silentHours: silentHours,         // 使用前端字段名
        deduplicationWindow: ruleForm.deduplicationWindow || undefined,  // 使用前端字段名
        priority: mapPriorityToNumber(ruleForm.priority),  // 转换为数字
        userId: userStore.user?.id || 1  // 使用前端字段名
      }

      if (isEditMode.value && ruleForm._id) {
        await updateNotificationRule(ruleForm._id, data)
        ElMessage.success('规则更新成功')
      } else {
        await createNotificationRule(data)
        ElMessage.success('规则创建成功')
      }

      ruleDialogVisible.value = false
      await loadRules()
    } catch (error) {
      console.error('Failed to save rule:', error)
      ElMessage.error('保存失败')
    } finally {
      saving.value = false
    }
  })
}

// 切换规则状态
const toggleRule = async (rule: NotificationRule) => {
  rule._toggling = true
  try {
    await toggleNotificationRule(rule.id)
    ElMessage.success(rule.enabled ? '规则已启用' : '规则已禁用')
  } catch (error) {
    console.error('Failed to toggle rule:', error)
    // 恢复状态
    rule.enabled = !rule.enabled
    ElMessage.error('操作失败')
  } finally {
    rule._toggling = false
  }
}

// 删除规则
const deleteRule = async (rule: NotificationRule) => {
  try {
    await ElMessageBox.confirm(`确定要删除规则"${rule.name}"吗？`, '确认删除', {
      type: 'warning'
    })

    await deleteNotificationRule(rule.id)
    ElMessage.success('删除成功')
    await loadRules()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Failed to delete rule:', error)
      ElMessage.error('删除失败')
    }
  }
}

// 测试规则
const testRule = (rule: NotificationRule) => {
  currentTestRule.value = rule
  testEventData.value = JSON.stringify(
    {
      size_gb: 10,
      quality: '1080p',
      promotion_type: 'free',
      site_name: 'MTeam'
    },
    null,
    2
  )
  testResult.value = null
  testDialogVisible.value = true
}

// 运行测试
const runTest = async () => {
  if (!currentTestRule.value) return

  testing.value = true
  try {
    const eventData = JSON.parse(testEventData.value)
    const res = await testNotificationRule(currentTestRule.value.id, eventData)
    if (res.data) {
      testResult.value = res.data
    }
  } catch (error) {
    console.error('Failed to test rule:', error)
    ElMessage.error('测试失败，请检查输入的 JSON 格式')
  } finally {
    testing.value = false
  }
}

// 重置筛选
const resetFilters = () => {
  filterForm.eventType = ''
  filterForm.enabled = undefined
  pagination.page = 1
  loadRules()
}

// 重置表单
const resetRuleForm = () => {
  Object.assign(ruleForm, {
    name: '',
    enabled: true,
    eventType: '',
    conditions: {},
    channelIds: [],
    sendInApp: true,
    templateId: undefined,
    silentHours: undefined,
    deduplicationWindow: 0,
    priority: 'medium',
    _id: undefined
  })
  conditions.value = []
  silentHoursEnabled.value = false
  silentPeriods.value = []
}

// 辅助函数
const getEventTypeName = (type: string) => {
  return eventTypes.find((e) => e.value === type)?.label || type
}

// 优先级映射 (字符串转数字)
const mapPriorityToNumber = (priority: string): number => {
  const priorityMap: Record<string, number> = {
    'low': 2,
    'medium': 5,
    'high': 8,
    'urgent': 10
  }
  return priorityMap[priority] || 5  // 默认中等优先级
}

const getChannelName = (channelId: number) => {
  const channel = availableChannels.value.find((c) => c.id === channelId)
  return channel?.name || `渠道 ${channelId}`
}

const getChannelColor = (type: string) => {
  const colorMap: Record<string, string> = {
    telegram: 'primary',
    email: 'success',
    webhook: 'warning',
    discord: ''
  }
  return colorMap[type] || 'info'
}

const goBack = () => {
  router.back()
}

// 初始化
onMounted(() => {
  loadRules()
  loadChannels()
  loadTemplates()
})
</script>

<style scoped lang="scss">
.notification-rules-container {
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

  .rules-card {
    min-height: 400px;
  }

  .condition-item {
    display: flex;
    align-items: center;
    margin-bottom: 10px;
  }

  .silent-period-item {
    display: flex;
    align-items: center;
    margin-bottom: 10px;
  }
}
</style>
