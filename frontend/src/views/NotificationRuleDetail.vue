<template>
  <div class="notification-rule-detail-container">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-left">
        <el-button icon="ArrowLeft" @click="goBack">返回</el-button>
        <h2>{{ isEdit ? '编辑通知规则' : '创建通知规则' }}</h2>
      </div>
      <div class="header-right">
        <el-button @click="goBack">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveRule">
          {{ isEdit ? '保存' : '创建' }}
        </el-button>
      </div>
    </div>

    <!-- 表单内容 -->
    <el-form
      ref="formRef"
      :model="formData"
      :rules="formRules"
      label-width="120px"
      class="rule-form"
    >
      <!-- 基本信息 -->
      <el-card header="基本信息" class="form-card">
        <el-form-item label="规则名称" prop="name">
          <el-input v-model="formData.name" placeholder="请输入规则名称" />
        </el-form-item>

        <el-form-item label="事件类型" prop="eventType">
          <el-select
            v-model="formData.eventType"
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
              />
            </el-option-group>
          </el-select>
        </el-form-item>

        <el-form-item label="描述">
          <el-input
            v-model="formData.description"
            type="textarea"
            :rows="3"
            placeholder="规则描述（可选）"
          />
        </el-form-item>

        <el-form-item label="启用状态">
          <el-switch v-model="formData.enabled" />
        </el-form-item>
      </el-card>

      <!-- 通知渠道 -->
      <el-card header="通知渠道" class="form-card">
        <el-form-item label="站内信">
          <el-switch v-model="formData.sendInApp" />
        </el-form-item>

        <el-form-item label="外部渠道">
          <el-checkbox-group v-model="formData.channelIds">
            <el-checkbox
              v-for="channel in availableChannels"
              :key="channel.id"
              :value="channel.id"
              :disabled="!channel.enabled"
            >
              {{ channel.name }} ({{ getChannelTypeName(channel.channelType) }})
              <el-tag v-if="!channel.enabled" type="info" size="small">已禁用</el-tag>
            </el-checkbox>
          </el-checkbox-group>
        </el-form-item>
      </el-card>

      <!-- 触发条件 -->
      <el-card header="触发条件" class="form-card">
        <el-form-item label="优先级过滤">
          <el-select
            v-model="formData.conditions.priority"
            placeholder="不限"
            clearable
            style="width: 200px"
          >
            <el-option label="紧急及以上" value="urgent" />
            <el-option label="高及以上" value="high" />
            <el-option label="普通及以上" value="normal" />
          </el-select>
        </el-form-item>

        <el-form-item label="关键词过滤">
          <el-input
            v-model="formData.conditions.keywords"
            placeholder="标题中包含的关键词，多个用逗号分隔"
          />
        </el-form-item>

        <el-form-item label="时间范围">
          <el-time-picker
            v-model="formData.conditions.timeRange"
            is-range
            range-separator="至"
            start-placeholder="开始时间"
            end-placeholder="结束时间"
            format="HH:mm"
          />
        </el-form-item>
      </el-card>

      <!-- 静默设置 -->
      <el-card header="静默设置" class="form-card">
        <el-form-item label="启用静默">
          <el-switch v-model="formData.silentHours.enabled" />
        </el-form-item>

        <template v-if="formData.silentHours.enabled">
          <el-form-item label="静默时段">
            <el-time-picker
              v-model="formData.silentHours.startTime"
              placeholder="开始时间"
              format="HH:mm"
            />
            <span style="margin: 0 10px">至</span>
            <el-time-picker
              v-model="formData.silentHours.endTime"
              placeholder="结束时间"
              format="HH:mm"
            />
          </el-form-item>

          <el-form-item label="静默日期">
            <el-checkbox-group v-model="formData.silentHours.days">
              <el-checkbox value="1">周一</el-checkbox>
              <el-checkbox value="2">周二</el-checkbox>
              <el-checkbox value="3">周三</el-checkbox>
              <el-checkbox value="4">周四</el-checkbox>
              <el-checkbox value="5">周五</el-checkbox>
              <el-checkbox value="6">周六</el-checkbox>
              <el-checkbox value="0">周日</el-checkbox>
            </el-checkbox-group>
          </el-form-item>
        </template>
      </el-card>

      <!-- 频率控制 -->
      <el-card header="频率控制" class="form-card">
        <el-form-item label="去重间隔">
          <el-input-number
            v-model="formData.deduplicationMinutes"
            :min="0"
            :max="1440"
            controls-position="right"
          />
          <span style="margin-left: 10px">分钟（0 表示不去重）</span>
        </el-form-item>

        <el-form-item label="每日限制">
          <el-input-number
            v-model="formData.dailyLimit"
            :min="0"
            controls-position="right"
          />
          <span style="margin-left: 10px">条（0 表示不限制）</span>
        </el-form-item>
      </el-card>
    </el-form>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import type { NotificationRule, NotificationChannel, NotificationRuleForm } from '@/types'
import {
  getNotificationRule,
  createNotificationRule,
  updateNotificationRule,
  getNotificationChannelList
} from '@/api/modules/notification'

const route = useRoute()
const router = useRouter()

// 是否为编辑模式
const isEdit = computed(() => !!route.params.id)

// 表单引用
const formRef = ref<FormInstance>()

// 加载状态
const loading = ref(false)
const saving = ref(false)

// 可用的通知渠道
const availableChannels = ref<NotificationChannel[]>([])

// 表单数据
const formData = reactive<NotificationRuleForm>({
  name: '',
  eventType: '',
  description: '',
  enabled: true,
  channelIds: [],
  sendInApp: true,
  conditions: {
    priority: '',
    keywords: '',
    timeRange: null
  },
  silentHours: {
    enabled: false,
    startTime: null,
    endTime: null,
    days: []
  },
  deduplicationMinutes: 30,
  dailyLimit: 0
})

// 表单验证规则
const formRules: FormRules = {
  name: [
    { required: true, message: '请输入规则名称', trigger: 'blur' },
    { max: 100, message: '规则名称不能超过100个字符', trigger: 'blur' }
  ],
  eventType: [
    { required: true, message: '请选择事件类型', trigger: 'change' }
  ]
}

// 事件类型分组
const eventTypeGroups = [
  {
    label: '订阅相关',
    options: [
      { label: '订阅匹配', value: 'subscription_matched' },
      { label: '订阅下载', value: 'subscription_downloaded' },
      { label: '订阅完成', value: 'subscription_completed' },
      { label: '订阅无资源', value: 'subscription_no_resource' }
    ]
  },
  {
    label: '下载相关',
    options: [
      { label: '下载开始', value: 'download_started' },
      { label: '下载完成', value: 'download_completed' },
      { label: '下载失败', value: 'download_failed' },
      { label: '下载暂停', value: 'download_paused' }
    ]
  },
  {
    label: '资源相关',
    options: [
      { label: '免费促销', value: 'resource_free_promotion' },
      { label: '2倍促销', value: 'resource_2x_promotion' },
      { label: '高质量资源', value: 'resource_high_quality' }
    ]
  },
  {
    label: 'PT站点相关',
    options: [
      { label: '站点连接失败', value: 'site_connection_failed' },
      { label: '站点认证过期', value: 'site_auth_expired' },
      { label: '站点同步完成', value: 'site_sync_completed' }
    ]
  },
  {
    label: '媒体文件相关',
    options: [
      { label: '媒体扫描完成', value: 'media_scan_completed' },
      { label: '媒体整理完成', value: 'media_organized' },
      { label: '媒体元数据刮削', value: 'media_metadata_scraped' }
    ]
  },
  {
    label: '任务相关',
    options: [
      { label: '任务失败', value: 'task_failed' },
      { label: '任务完成', value: 'task_completed' }
    ]
  },
  {
    label: '系统相关',
    options: [
      { label: '系统错误', value: 'system_error' },
      { label: '磁盘空间不足', value: 'disk_space_low' },
      { label: '用户登录异常', value: 'user_login_anomaly' },
      { label: '系统更新可用', value: 'system_update_available' }
    ]
  }
]

// 加载通知渠道
const loadChannels = async () => {
  try {
    const res = await getNotificationChannelList()
    if (res.data) {
      availableChannels.value = res.data.items || []
    }
  } catch (error) {
    ElMessage.error('加载通知渠道失败')
  }
}

// 加载规则详情
const loadRule = async () => {
  if (!isEdit.value) return

  loading.value = true
  try {
    const res = await getNotificationRule(Number(route.params.id))
    if (res.data) {
      const rule = res.data
      Object.assign(formData, {
        name: rule.name,
        eventType: rule.eventType,
        description: rule.description || '',
        enabled: rule.enabled,
        channelIds: rule.channelIds || [],
        sendInApp: rule.sendInApp,
        conditions: rule.conditions || {
          priority: '',
          keywords: '',
          timeRange: null
        },
        silentHours: rule.silentHours || {
          enabled: false,
          startTime: null,
          endTime: null,
          days: []
        },
        deduplicationMinutes: rule.deduplicationMinutes || 30,
        dailyLimit: rule.dailyLimit || 0
      })
    }
  } catch (error) {
    ElMessage.error('加载规则详情失败')
  } finally {
    loading.value = false
  }
}

// 保存规则
const saveRule = async () => {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (!valid) return

    saving.value = true
    try {
      const data = { ...formData }

      if (isEdit.value) {
        await updateNotificationRule(Number(route.params.id), data)
        ElMessage.success('规则更新成功')
      } else {
        await createNotificationRule(data)
        ElMessage.success('规则创建成功')
      }

      goBack()
    } catch (error) {
      ElMessage.error(isEdit.value ? '规则更新失败' : '规则创建失败')
    } finally {
      saving.value = false
    }
  })
}

// 返回
const goBack = () => {
  router.push('/notifications')
}

// 获取渠道类型名称
const getChannelTypeName = (type: string) => {
  const map: Record<string, string> = {
    telegram: 'Telegram',
    email: '邮件',
    webhook: 'Webhook'
  }
  return map[type] || type
}

// 生命周期
onMounted(() => {
  loadChannels()
  loadRule()
})
</script>

<style scoped>
.notification-rule-detail-container {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.header-left h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.header-right {
  display: flex;
  gap: 10px;
}

.rule-form {
  margin-top: 20px;
}

.form-card {
  margin-bottom: 20px;
}

.form-card .el-form-item {
  margin-bottom: 20px;
}
</style>