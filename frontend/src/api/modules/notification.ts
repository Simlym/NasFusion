/**
 * 通知相关 API
 */

import request from '../request'
import {
  NotificationChannel,
  NotificationChannelForm,
  NotificationMessage,
  NotificationStats,
  NotificationRule,
  NotificationRuleForm,
  NotificationTemplate,
  NotificationTemplateForm,
  NotificationLog,
  DispatchStatistics
} from '@/types'
import { PaginationParams, PaginationResponse, ApiResponse } from '@/types'

// 获取通知渠道列表
export function getNotificationChannelList() {
  return request.get<{
    total: number
    items: NotificationChannel[]
  }>('/notification-channels')
}

// 创建通知渠道
export function createNotificationChannel(data: NotificationChannelForm) {
  return request.post<NotificationChannel>('/notification-channels', data)
}

// 更新通知渠道
export function updateNotificationChannel(id: number, data: Partial<NotificationChannelForm>) {
  return request.put<NotificationChannel>(`/notification-channels/${id}`, data)
}

// 删除通知渠道
export function deleteNotificationChannel(id: number) {
  return request.delete<void>(`/notification-channels/${id}`)
}

// 测试通知渠道
export function testNotificationChannel(id: number) {
  return request.post<{ success: boolean; message: string }>(
    `/notification-channels/${id}/test`
  )
}

// 获取通知消息列表
export function getNotificationMessageList(params?: { page?: number; page_size?: number; status?: string; notification_type?: string; priority?: string }) {
  return request.get<{
    total: number
    items: NotificationMessage[]
    unread_count: number
  }>('/notifications', {
    params
  })
}

// 标记通知为已读
export function markNotificationAsRead(id: number) {
  return request.put<ApiResponse<void>>(`/notifications/${id}/read`)
}

// 标记所有通知为已读
export function markAllNotificationsAsRead() {
  return request.put<ApiResponse<void>>('/notifications/read-all')
}

// 删除通知
export function deleteNotification(id: number) {
  return request.delete<ApiResponse<void>>(`/notifications/${id}`)
}

// 获取通知统计
export function getNotificationStats() {
  return request.get<ApiResponse<NotificationStats>>('/notifications/stats')
}

// ==================== 通知规则 API ====================

// 获取通知规则列表
export function getNotificationRuleList(params?: { eventType?: string; enabled?: boolean } & PaginationParams) {
  return request.get<ApiResponse<PaginationResponse<NotificationRule>>>('/notification-rules', {
    params
  })
}

// 获取通知规则详情
export function getNotificationRule(id: number) {
  return request.get<ApiResponse<NotificationRule>>(`/notification-rules/${id}`)
}

// 创建通知规则
export function createNotificationRule(data: NotificationRuleForm) {
  return request.post<ApiResponse<NotificationRule>>('/notification-rules', data)
}

// 更新通知规则
export function updateNotificationRule(id: number, data: Partial<NotificationRuleForm>) {
  return request.put<ApiResponse<NotificationRule>>(`/notification-rules/${id}`, data)
}

// 删除通知规则
export function deleteNotificationRule(id: number) {
  return request.delete<ApiResponse<void>>(`/notification-rules/${id}`)
}

// 测试通知规则
export function testNotificationRule(id: number, eventData: Record<string, any>) {
  return request.post<ApiResponse<{
    ruleId: number
    eventType: string
    shouldNotify: boolean
    conditionsMet: boolean
    inSilentHours: boolean
    wouldDeduplicate: boolean
    details: Record<string, any>
  }>>(`/notification-rules/${id}/test`, eventData)
}

// 切换通知规则启用状态
export function toggleNotificationRule(id: number) {
  return request.post<ApiResponse<{
    ruleId: number
    enabled: boolean
    message: string
  }>>(`/notification-rules/${id}/toggle`)
}

// ==================== 通知模板 API ====================

// 获取通知模板列表
export function getNotificationTemplateList(params?: { eventType?: string; language?: string; isSystem?: boolean; limit?: number }) {
  return request.get<{
    total: number
    items: NotificationTemplate[]
  }>('/notification-templates', {
    params
  })
}

// 获取通知模板详情
export function getNotificationTemplate(id: number) {
  return request.get<ApiResponse<NotificationTemplate>>(`/notification-templates/${id}`)
}

// 创建通知模板
export function createNotificationTemplate(data: NotificationTemplateForm) {
  return request.post<ApiResponse<NotificationTemplate>>('/notification-templates', data)
}

// 更新通知模板
export function updateNotificationTemplate(id: number, data: Partial<NotificationTemplateForm>) {
  return request.put<ApiResponse<NotificationTemplate>>(`/notification-templates/${id}`, data)
}

// 删除通知模板
export function deleteNotificationTemplate(id: number) {
  return request.delete<ApiResponse<void>>(`/notification-templates/${id}`)
}

// 验证模板语法
export function validateNotificationTemplate(templateStr: string) {
  return request.post<ApiResponse<{
    valid: boolean
    errors: string[]
    variables: string[]
  }>>('/notification-templates/validate', null, {
    params: { template_str: templateStr }
  })
}

// 渲染通知模板
export function renderNotificationTemplate(id: number, variables: Record<string, any>) {
  return request.post<ApiResponse<{
    title: string
    content: string
  }>>(`/notification-templates/${id}/render`, variables)
}

// 获取事件对应的模板
export function getTemplateForEvent(eventType: string, language: string = 'zh-CN') {
  return request.get<ApiResponse<NotificationTemplate>>(`/notification-templates/event/${eventType}`, {
    params: { language }
  })
}

// 初始化系统模板（管理员）
export function initSystemTemplates() {
  return request.post<ApiResponse<{
    message: string
    templates: NotificationTemplate[]
  }>>('/notification-templates/system/init')
}

// ==================== 通知调度 API ====================

// 手动调度事件通知
export function dispatchEvent(data: {
  eventType: string
  eventData: Record<string, any>
  userId?: number
  broadcast?: boolean
}) {
  return request.post<ApiResponse<{
    totalRules: number
    inAppSent: number
    channelSent: number
    failed: number
    skipped: number
    logs: number[]
  }>>('/notification-dispatch/dispatch', data)
}

// 发送测试通知
export function sendTestNotification(channelId: number) {
  return request.post<ApiResponse<{
    success: boolean
    message: string
    messageId?: string
  }>>('/notification-dispatch/test', { channel_id: channelId })
}

// 获取通知发送统计
export function getDispatchStatistics(days: number = 7) {
  return request.get<ApiResponse<DispatchStatistics>>('/notification-dispatch/statistics', {
    params: { days }
  })
}

// ==================== 站外消息历史 API ====================

/**
 * 站外消息（通过 Telegram/Email/Webhook 发送的消息记录）
 */
export interface NotificationExternal {
  id: number
  userId: number
  notificationType: string
  channelId?: number
  channelType?: string
  title: string
  content: string
  status: 'pending' | 'sent' | 'failed'
  retryCount: number
  errorMessage?: string
  sentAt?: string
  responseData?: Record<string, any>
  extraData?: Record<string, any>
  createdAt: string
  updatedAt: string
}

// 获取站外消息历史列表
export function getExternalNotifications(params?: {
  page?: number
  page_size?: number
  status?: string
  channel_type?: string
  notification_type?: string
  start_date?: string
  end_date?: string
}) {
  return request.get<{
    total: number
    items: NotificationExternal[]
  }>('/notifications/external', {
    params
  })
}

// 获取站外消息详情
export function getExternalNotification(id: number) {
  return request.get<NotificationExternal>(`/notifications/external/${id}`)
}

// 获取站外消息统计（如果后端有提供）
export function getExternalNotificationStats(days: number = 7) {
  return request.get<ApiResponse<{
    period_days: number
    start_date: string
    end_date: string
    total_sent: number
    success_count: number
    failed_count: number
    pending_count: number
    success_rate: number
    channel_distribution: Record<string, number>
    event_distribution: Record<string, number>
    daily_distribution: Record<string, number>
  }>>('/notifications/external/statistics', {
    params: { days }
  })
}
