/**
 * 通知相关类型定义
 */

// 通知类型
export enum NotificationType {
  INFO = 'info',
  SUCCESS = 'success',
  WARNING = 'warning',
  ERROR = 'error'
}

// 通知渠道类型
export enum NotificationChannelType {
  TELEGRAM = 'telegram',
  EMAIL = 'email',
  WEBHOOK = 'webhook',
  DISCORD = 'discord'
}

// 通知渠道
export interface NotificationChannel {
  id: number
  userId?: number
  name: string
  type: NotificationChannelType
  isActive: boolean
  isDefault: boolean
  config: Record<string, any>
  eventTypes?: string[]
  createdAt: string
  updatedAt: string
}

// 通知消息
export interface NotificationMessage {
  id: number
  userId?: number
  channelId?: number
  type: NotificationType
  title: string
  message: string
  eventType: string
  relatedId?: number
  relatedType?: string
  isRead: boolean
  sentAt?: string
  failedReason?: string
  metadata?: Record<string, any>
  createdAt: string
}

// 通知渠道表单
export interface NotificationChannelForm {
  name: string
  type: NotificationChannelType
  isActive: boolean
  isDefault: boolean
  config: Record<string, any>
  eventTypes?: string[]
}

// 通知统计
export interface NotificationStats {
  total: number
  unread: number
  todaySent: number
  failedToday: number
}

// 通知规则
export interface NotificationRule {
  id: number
  userId: number
  name: string
  enabled: boolean
  eventType: string
  conditions?: Record<string, any>
  channelIds: number[]
  sendInApp: boolean
  templateId?: number
  silentHours?: {
    enabled: boolean
    periods: Array<{
      days?: string[]
      start: string
      end: string
    }>
  }
  deduplicationWindow?: number
  priority?: string
  createdAt: string
  updatedAt: string
}

// 通知规则表单
export interface NotificationRuleForm {
  name: string
  enabled: boolean
  eventType: string
  conditions?: Record<string, any>
  channelIds: number[]
  sendInApp: boolean
  templateId?: number
  silentHours?: {
    enabled: boolean
    periods: Array<{
      days?: string[]
      start: string
      end: string
    }>
  }
  deduplicationWindow?: number
  priority?: string
}

// 通知模板
export interface NotificationTemplate {
  id: number
  userId?: number
  eventType: string
  name: string
  language: string
  format: string
  titleTemplate: string
  contentTemplate: string
  variables?: string[]
  isSystem: boolean
  createdAt: string
  updatedAt: string
}

// 通知模板表单
export interface NotificationTemplateForm {
  eventType: string
  name: string
  language: string
  format: string
  titleTemplate: string
  contentTemplate: string
  variables?: string[]
  isSystem?: boolean
}

// 通知日志
export interface NotificationLog {
  id: number
  userId: number
  channelId?: number
  notificationType: string
  title: string
  content: string
  status: string
  errorMessage?: string
  metadata?: Record<string, any>
  sentAt?: string
  createdAt: string
}

// 调度统计
export interface DispatchStatistics {
  total: number
  success: number
  failed: number
  successRate: number
  days: number
  byEventType: Array<{
    eventType: string
    count: number
  }>
  byChannel: Array<{
    channelId: number
    count: number
  }>
}
