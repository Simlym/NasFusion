<template>
  <div class="page-container">
    <!-- 页面标题 -->
    <el-card class="page-header">
      <div class="header-content">
        <div>
          <h1>消息中心</h1>
          <p>查看系统消息和站外通知发送记录</p>
        </div>
      </div>
    </el-card>

    <!-- 导航提示 -->
    <el-alert
      :closable="false"
      type="info"
      style="margin-bottom: 20px"
    >
      <template #default>
        想要配置通知渠道、规则或模板？
        <el-link
          type="primary"
          underline="never"
          style="margin-left: 8px"
          @click="router.push('/settings?tab=notifications')"
        >
          前往通知设置 →
        </el-link>
      </template>
    </el-alert>

    <!-- Tab 切换 -->
    <el-tabs v-model="activeTab" class="main-tabs">
      <!-- Tab 1: 站内消息 -->
      <el-tab-pane label="站内消息" name="messages">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>
                通知消息
                <el-badge v-if="unreadCount > 0" :value="unreadCount" :max="99" class="badge-margin" />
              </span>
              <div class="header-actions">
                <el-select
                  v-model="messageFilter.status"
                  placeholder="全部状态"
                  clearable
                  class="filter-select"
                  @change="loadMessages"
                >
                  <el-option label="全部" value="" />
                  <el-option label="未读" value="unread" />
                  <el-option label="已读" value="read" />
                </el-select>
                <el-button type="primary" text :disabled="unreadCount === 0" @click="markAllAsRead">
                  全部标记为已读
                </el-button>
              </div>
            </div>
          </template>

          <!-- 桌面端：消息表格 -->
          <el-table
            v-if="!isMobile"
            v-loading="messagesLoading"
            :data="messages"
            style="width: 100%"
            row-class-name="message-row"
            @row-click="handleMessageClick"
          >
            <el-table-column width="50">
              <template #default="{ row }">
                <div v-if="row.status === 'unread'" class="unread-indicator"></div>
              </template>
            </el-table-column>
            <el-table-column prop="title" label="标题" min-width="250" show-overflow-tooltip>
              <template #default="{ row }">
                <span :class="{ 'unread-text': row.status === 'unread' }">{{ row.title }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="notificationType" label="类型" width="140">
              <template #default="{ row }">
                <el-tag :type="getEventTypeTag(row.notificationType)" size="small">
                  {{ getEventTypeName(row.notificationType) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="priority" label="优先级" width="100">
              <template #default="{ row }">
                <el-tag :type="getPriorityTag(row.priority)" size="small">
                  {{ getPriorityName(row.priority) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="createdAt" label="时间" width="180">
              <template #default="{ row }">
                {{ formatDateTime(row.createdAt) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="140" fixed="right">
              <template #default="{ row }">
                <el-button
                  link
                  type="primary"
                  size="small"
                  @click.stop="viewMessage(row)"
                >
                  查看
                </el-button>
                <el-button
                  link
                  type="danger"
                  size="small"
                  @click.stop="deleteMessage(row)"
                >
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <!-- 移动端：消息卡片列表 -->
          <div v-if="isMobile" v-loading="messagesLoading" class="msg-cards-mobile">
            <div
              v-for="msg in messages"
              :key="msg.id"
              class="msg-card-mobile"
              :class="{ 'msg-card-mobile--unread': msg.status === 'unread' }"
              @click="viewMessage(msg)"
            >
              <div class="msg-card-top">
                <div class="msg-card-title-row">
                  <div v-if="msg.status === 'unread'" class="unread-indicator"></div>
                  <span class="msg-card-title" :class="{ 'unread-text': msg.status === 'unread' }">{{ msg.title }}</span>
                </div>
                <el-tag :type="getPriorityTag(msg.priority)" size="small">
                  {{ getPriorityName(msg.priority) }}
                </el-tag>
              </div>
              <div class="msg-card-meta">
                <el-tag :type="getEventTypeTag(msg.notificationType)" size="small">
                  {{ getEventTypeName(msg.notificationType) }}
                </el-tag>
                <span class="msg-card-time">{{ formatDateTime(msg.createdAt) }}</span>
              </div>
              <div class="msg-card-actions">
                <el-button link type="primary" size="small" @click.stop="viewMessage(msg)">查看</el-button>
                <el-button link type="danger" size="small" @click.stop="deleteMessage(msg)">删除</el-button>
              </div>
            </div>
          </div>

          <!-- 分页 -->
          <el-pagination
            v-if="messagePagination.total > 0"
            v-model:current-page="messagePagination.page"
            v-model:page-size="messagePagination.pageSize"
            :total="messagePagination.total"
            :page-sizes="[10, 20, 50, 100]"
            :layout="isMobile ? 'total, prev, pager, next' : 'total, sizes, prev, pager, next'"
            :small="isMobile"
            class="notification-pagination"
            @size-change="loadMessages"
            @current-change="loadMessages"
          />

          <!-- 空状态 -->
          <el-empty v-if="messages.length === 0 && !messagesLoading" description="暂无通知消息" />
        </el-card>
      </el-tab-pane>

      <!-- Tab 2: 站外消息历史 -->
      <el-tab-pane label="站外消息历史" name="external">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>站外通知发送记录</span>
              <div class="header-actions">
                <el-select
                  v-model="externalFilter.status"
                  placeholder="全部状态"
                  clearable
                  class="filter-select"
                  @change="loadExternalMessages"
                >
                  <el-option label="全部" value="" />
                  <el-option label="已发送" value="sent" />
                  <el-option label="发送失败" value="failed" />
                  <el-option label="待发送" value="pending" />
                </el-select>
                <el-select
                  v-model="externalFilter.channelType"
                  placeholder="全部渠道"
                  clearable
                  class="filter-select"
                  @change="loadExternalMessages"
                >
                  <el-option label="全部" value="" />
                  <el-option label="Telegram" value="telegram" />
                  <el-option label="Email" value="email" />
                  <el-option label="Webhook" value="webhook" />
                </el-select>
                <el-button :icon="Refresh" @click="loadExternalMessages">刷新</el-button>
              </div>
            </div>
          </template>

          <!-- 桌面端：站外消息表格 -->
          <el-table
            v-if="!isMobile"
            v-loading="externalLoading"
            :data="externalMessages"
            style="width: 100%"
          >
            <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
            <el-table-column prop="channelType" label="渠道" width="120">
              <template #default="{ row }">
                <el-tag :type="getChannelTypeTag(row.channelType)" size="small">
                  {{ getChannelTypeName(row.channelType) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="getExternalStatusTag(row.status)" size="small">
                  {{ getExternalStatusName(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="sentAt" label="发送时间" width="180">
              <template #default="{ row }">
                {{ row.sentAt ? formatDateTime(row.sentAt) : '-' }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="80" fixed="right">
              <template #default="{ row }">
                <el-button
                  link
                  type="primary"
                  size="small"
                  @click="viewExternalMessage(row)"
                >
                  查看
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <!-- 移动端：站外消息卡片列表 -->
          <div v-if="isMobile" v-loading="externalLoading" class="msg-cards-mobile">
            <div
              v-for="msg in externalMessages"
              :key="msg.id"
              class="msg-card-mobile"
              @click="viewExternalMessage(msg)"
            >
              <div class="msg-card-top">
                <span class="msg-card-title">{{ msg.title }}</span>
              </div>
              <div class="msg-card-meta">
                <el-tag :type="getChannelTypeTag(msg.channelType)" size="small">
                  {{ getChannelTypeName(msg.channelType) }}
                </el-tag>
                <el-tag :type="getExternalStatusTag(msg.status)" size="small">
                  {{ getExternalStatusName(msg.status) }}
                </el-tag>
                <span class="msg-card-time">{{ msg.sentAt ? formatDateTime(msg.sentAt) : '-' }}</span>
              </div>
            </div>
          </div>

          <!-- 分页 -->
          <el-pagination
            v-if="externalPagination.total > 0"
            v-model:current-page="externalPagination.page"
            v-model:page-size="externalPagination.pageSize"
            :total="externalPagination.total"
            :page-sizes="[10, 20, 50, 100]"
            :layout="isMobile ? 'total, prev, pager, next' : 'total, sizes, prev, pager, next, jumper'"
            :small="isMobile"
            class="notification-pagination"
            @size-change="loadExternalMessages"
            @current-change="loadExternalMessages"
          />

          <!-- 空状态 -->
          <el-empty v-if="externalMessages.length === 0 && !externalLoading" description="暂无站外消息发送记录" />
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <!-- 消息详情对话框 -->
    <el-dialog
      v-model="messageDialogVisible"
      :title="currentMessage?.title"
      :width="isMobile ? '95%' : '600px'"
    >
      <div v-if="currentMessage" class="message-detail">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="类型">
            <el-tag :type="getEventTypeTag(currentMessage.notificationType)" size="small">
              {{ getEventTypeName(currentMessage.notificationType) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="优先级">
            <el-tag :type="getPriorityTag(currentMessage.priority)" size="small">
              {{ getPriorityName(currentMessage.priority) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="时间">
            {{ formatDateTime(currentMessage.createdAt) }}
          </el-descriptions-item>
        </el-descriptions>
        <div class="message-content">
          <h4>消息内容</h4>
          <pre>{{ currentMessage.content }}</pre>
        </div>
      </div>
      <template #footer>
        <el-button @click="messageDialogVisible = false">关闭</el-button>
        <el-button
          v-if="currentMessage?.status === 'unread'"
          type="primary"
          @click="markAsReadAndClose"
        >
          标记已读
        </el-button>
      </template>
    </el-dialog>

    <!-- 站外消息详情对话框 -->
    <el-dialog
      v-model="externalDialogVisible"
      :title="currentExternalMessage?.title"
      :width="isMobile ? '95%' : '700px'"
    >
      <div v-if="currentExternalMessage" class="external-message-detail">
        <el-descriptions :column="isMobile ? 1 : 2" border>
          <el-descriptions-item label="消息类型">
            <el-tag :type="getEventTypeTag(currentExternalMessage.notificationType)" size="small">
              {{ getEventTypeName(currentExternalMessage.notificationType) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="渠道类型">
            <el-tag :type="getChannelTypeTag(currentExternalMessage.channelType || '')" size="small">
              {{ getChannelTypeName(currentExternalMessage.channelType || '') }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="发送状态">
            <el-tag :type="getExternalStatusTag(currentExternalMessage.status)" size="small">
              {{ getExternalStatusName(currentExternalMessage.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="重试次数">
            {{ currentExternalMessage.retryCount }}
          </el-descriptions-item>
          <el-descriptions-item label="创建时间" :span="2">
            {{ formatDateTime(currentExternalMessage.createdAt) }}
          </el-descriptions-item>
          <el-descriptions-item label="发送时间" :span="2">
            {{ currentExternalMessage.sentAt ? formatDateTime(currentExternalMessage.sentAt) : '未发送' }}
          </el-descriptions-item>
          <el-descriptions-item v-if="currentExternalMessage.errorMessage" label="错误信息" :span="2">
            <el-text type="danger">{{ currentExternalMessage.errorMessage }}</el-text>
          </el-descriptions-item>
        </el-descriptions>
        <div class="message-content">
          <h4>消息内容</h4>
          <pre>{{ currentExternalMessage.content }}</pre>
        </div>
        <div v-if="currentExternalMessage.responseData" class="message-response">
          <h4>响应数据</h4>
          <pre>{{ JSON.stringify(currentExternalMessage.responseData, null, 2) }}</pre>
        </div>
      </div>
      <template #footer>
        <el-button @click="externalDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  View,
  Delete,
  Refresh
} from '@element-plus/icons-vue'
import type { NotificationMessage } from '@/types'
import {
  getNotificationMessageList,
  markNotificationAsRead,
  markAllNotificationsAsRead,
  deleteNotification,
  getExternalNotifications,
  type NotificationExternal
} from '@/api/modules/notification'
import { formatDateTime } from '@/utils'

const router = useRouter()

// 移动端检测
const isMobile = ref(window.innerWidth <= 768)
const handleMobileResize = () => {
  isMobile.value = window.innerWidth <= 768
}

// Tab 状态
const activeTab = ref('messages')

// ==================== 消息中心 ====================
const messagesLoading = ref(false)
const messages = ref<NotificationMessage[]>([])
const unreadCount = ref(0)
const messageFilter = reactive({
  status: ''
})
const messagePagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

const messageDialogVisible = ref(false)
const currentMessage = ref<NotificationMessage | null>(null)

// 加载消息列表
const loadMessages = async () => {
  messagesLoading.value = true
  try {
    const res = await getNotificationMessageList({
      page: messagePagination.page,
      page_size: messagePagination.pageSize,
      status: messageFilter.status || undefined
    })
    // 后端直接返回 SystemNotificationListResponse
    if (res.data) {
      messages.value = res.data.items || []
      messagePagination.total = res.data.total || 0
      unreadCount.value = res.data.unread_count || 0
    }
  } catch (error) {
    console.error('加载消息列表失败:', error)
    ElMessage.error('加载消息列表失败')
  } finally {
    messagesLoading.value = false
  }
}

// 点击消息行
const handleMessageClick = (row: NotificationMessage) => {
  viewMessage(row)
}

// 查看消息
const viewMessage = async (message: NotificationMessage) => {
  currentMessage.value = message
  messageDialogVisible.value = true

  // 如果是未读消息，自动标记为已读
  if (message.status === 'unread') {
    try {
      await markNotificationAsRead(message.id)
      message.status = 'read'
      unreadCount.value = Math.max(0, unreadCount.value - 1)
    } catch (error) {
      console.error('标记已读失败:', error)
    }
  }
}

// 标记已读并关闭
const markAsReadAndClose = () => {
  messageDialogVisible.value = false
}

// 全部标记为已读
const markAllAsRead = async () => {
  try {
    await markAllNotificationsAsRead()
    ElMessage.success('已全部标记为已读')
    await loadMessages()
  } catch (error) {
    ElMessage.error('操作失败')
  }
}

// 删除消息
const deleteMessage = async (message: NotificationMessage) => {
  try {
    await ElMessageBox.confirm('确定要删除这条通知吗？', '确认删除', {
      type: 'warning'
    })
    await deleteNotification(message.id)
    ElMessage.success('删除成功')
    await loadMessages()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

// ==================== 站外消息历史 ====================
const externalLoading = ref(false)
const externalMessages = ref<NotificationExternal[]>([])
const externalFilter = reactive({
  status: '',
  channelType: ''
})
const externalPagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

const externalDialogVisible = ref(false)
const currentExternalMessage = ref<NotificationExternal | null>(null)

// 加载站外消息列表
const loadExternalMessages = async () => {
  externalLoading.value = true
  try {
    const res = await getExternalNotifications({
      page: externalPagination.page,
      page_size: externalPagination.pageSize,
      status: externalFilter.status || undefined,
      channel_type: externalFilter.channelType || undefined
    })
    if (res.data) {
      externalMessages.value = res.data.items || []
      externalPagination.total = res.data.total || 0
    }
  } catch (error) {
    console.error('加载站外消息失败:', error)
    ElMessage.error('加载站外消息失败')
  } finally {
    externalLoading.value = false
  }
}

// 查看站外消息详情
const viewExternalMessage = (message: NotificationExternal) => {
  currentExternalMessage.value = message
  externalDialogVisible.value = true
}

// 监听 Tab 切换
watch(activeTab, (newTab) => {
  if (newTab === 'external') {
    loadExternalMessages()
  }
})

// ==================== 辅助函数 ====================
const getEventTypeName = (type: string) => {
  const map: Record<string, string> = {
    // 订阅相关
    subscription_matched: '订阅匹配',
    subscription_downloaded: '订阅下载',
    subscription_completed: '订阅完成',
    subscription_no_resource: '订阅无资源',
    // 下载相关
    download_started: '下载开始',
    download_completed: '下载完成',
    download_failed: '下载失败',
    download_paused: '下载暂停',
    // 资源相关
    resource_free_promotion: '免费促销',
    resource_2x_promotion: '2倍促销',
    resource_high_quality: '高质量资源',
    // PT站点相关
    site_connection_failed: '站点连接失败',
    site_auth_expired: '站点认证过期',
    site_sync_completed: '站点同步完成',
    // 媒体文件相关
    media_scan_completed: '媒体扫描完成',
    media_organized: '媒体整理完成',
    media_metadata_scraped: '媒体元数据刮削',
    // 任务相关
    task_failed: '任务失败',
    task_completed: '任务完成',
    // 系统相关
    system_error: '系统错误',
    disk_space_low: '磁盘空间不足',
    user_login_anomaly: '用户登录异常',
    system_update_available: '系统更新可用'
  }
  return map[type] || type
}

const getEventTypeTag = (type: string) => {
  const map: Record<string, any> = {
    // 订阅相关
    subscription_matched: 'success',
    subscription_downloaded: 'primary',
    subscription_completed: 'success',
    subscription_no_resource: 'warning',
    // 下载相关
    download_started: 'info',
    download_completed: 'success',
    download_failed: 'danger',
    download_paused: 'warning',
    // 资源相关
    resource_free_promotion: 'success',
    resource_2x_promotion: 'primary',
    resource_high_quality: 'warning',
    // PT站点相关
    site_connection_failed: 'danger',
    site_auth_expired: 'danger',
    site_sync_completed: 'success',
    // 媒体文件相关
    media_scan_completed: 'info',
    media_organized: 'success',
    media_metadata_scraped: 'primary',
    // 任务相关
    task_failed: 'danger',
    task_completed: 'success',
    // 系统相关
    system_error: 'danger',
    disk_space_low: 'danger',
    user_login_anomaly: 'danger',
    system_update_available: 'info'
  }
  return map[type] || ''
}

const getPriorityName = (priority: string) => {
  const map: Record<string, string> = {
    urgent: '紧急',
    high: '高',
    normal: '普通',
    low: '低'
  }
  return map[priority] || '普通'
}

const getPriorityTag = (priority: string) => {
  const map: Record<string, any> = {
    urgent: 'danger',
    high: 'warning',
    normal: '',
    low: 'info'
  }
  return map[priority] || ''
}

const getChannelTypeName = (type: string) => {
  const map: Record<string, string> = {
    telegram: 'Telegram',
    email: '邮件',
    webhook: 'Webhook'
  }
  return map[type] || type
}

const getChannelTypeTag = (type: string) => {
  const tags: Record<string, string> = {
    telegram: 'primary',
    email: 'success',
    webhook: 'warning'
  }
  return tags[type] || 'info'
}

const getExternalStatusTag = (status: string) => {
  const tags: Record<string, string> = {
    sent: 'success',
    failed: 'danger',
    pending: 'warning'
  }
  return tags[status] || 'info'
}

const getExternalStatusName = (status: string) => {
  const names: Record<string, string> = {
    sent: '已发送',
    failed: '发送失败',
    pending: '待发送'
  }
  return names[status] || status
}

// ==================== 生命周期 ====================
onMounted(() => {
  loadMessages()
  window.addEventListener('resize', handleMobileResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleMobileResize)
})
</script>

<style scoped>
.page-container {
  width: 100%;
}

.page-header {
  margin-bottom: 20px;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.page-header h1 {
  margin: 0 0 10px 0;
  font-size: 24px;
}

.page-header p {
  margin: 0;
  color: var(--text-color-secondary, #909399);
}

.main-tabs {
  margin-top: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.header-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.filter-select {
  width: 120px;
}

.notification-pagination {
  margin-top: 20px;
  justify-content: flex-end;
}

.badge-margin {
  margin-left: 8px;
}

.message-row {
  cursor: pointer;
}

.message-row:hover {
  background-color: var(--bg-color-overlay, #f5f7fa);
}

.unread-text {
  font-weight: 600;
}

.message-detail {
  padding: 10px 0;
}

.message-content {
  margin-top: 20px;
}

.message-content h4 {
  margin-bottom: 10px;
}

.message-content pre {
  white-space: pre-wrap;
  word-break: break-word;
  background-color: var(--bg-color-overlay, #f5f7fa);
  color: var(--text-color-regular, inherit);
  padding: 15px;
  border-radius: 4px;
  line-height: 1.6;
}

.channel-card {
  margin-bottom: 16px;
}

.channel-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.channel-info {
  flex: 1;
}

.channel-info h4 {
  margin: 0 0 4px 0;
  font-size: 16px;
}

.channel-info p {
  margin: 0;
  color: var(--text-color-secondary, #909399);
  font-size: 13px;
}

.channel-body {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.channel-test-time {
  font-size: 12px;
  color: var(--text-color-secondary, #909399);
}

.channel-actions {
  display: flex;
  gap: 8px;
}

.unread-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: #409EFF;
  margin: 0 auto;
}

.external-message-detail {
  padding: 10px 0;
}

.message-response {
  margin-top: 20px;
}

.message-response h4 {
  margin-bottom: 10px;
}

/* ==================== 移动端卡片视图 ==================== */
.msg-cards-mobile {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.msg-card-mobile {
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 10px;
  padding: 12px 14px;
  cursor: pointer;
  transition: box-shadow 0.18s;
}

.msg-card-mobile:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.msg-card-mobile--unread {
  border-left: 3px solid #409EFF;
}

.msg-card-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}

.msg-card-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
}

.msg-card-title {
  font-size: 14px;
  color: var(--el-text-color-primary);
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.msg-card-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.msg-card-time {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-left: auto;
}

.msg-card-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid var(--el-border-color-extra-light);
}

/* ==================== 响应式设计 ==================== */
@media (max-width: 768px) {
  .page-header h1 {
    font-size: 20px;
  }

  .header-content {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }

  .card-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }

  .header-actions {
    width: 100%;
    justify-content: flex-start;
  }

  .filter-select {
    width: 100px;
  }

  .notification-pagination {
    justify-content: center;
  }

  .message-content pre {
    font-size: 13px;
    padding: 10px;
  }
}
</style>
