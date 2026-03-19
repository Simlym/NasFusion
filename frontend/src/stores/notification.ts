/**
 * 通知状态管理
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { NotificationMessage, NotificationStats } from '@/types'
import api from '@/api'

export const useNotificationStore = defineStore('notification', () => {
  // 状态
  const messages = ref<NotificationMessage[]>([])
  const stats = ref<NotificationStats | null>(null)
  const loading = ref(false)

  // 计算属性
  const unreadMessages = computed(() => messages.value.filter((m) => !m.isRead))

  const unreadCount = computed(() => unreadMessages.value.length)

  // 获取通知消息列表
  async function fetchMessages(isRead?: boolean) {
    try {
      loading.value = true
      const response = await api.notification.getNotificationMessageList({ isRead })
      if (response.data) {
        messages.value = response.data.items
        return true
      }
      return false
    } catch (error) {
      console.error('Fetch notifications failed:', error)
      return false
    } finally {
      loading.value = false
    }
  }

  // 获取通知统计
  async function fetchStats() {
    try {
      const response = await api.notification.getNotificationStats()
      if (response.data) {
        stats.value = response.data
        return true
      }
      return false
    } catch (error) {
      console.error('Fetch notification stats failed:', error)
      return false
    }
  }

  // 标记为已读
  async function markAsRead(id: number) {
    try {
      await api.notification.markNotificationAsRead(id)
      const message = messages.value.find((m) => m.id === id)
      if (message) {
        message.isRead = true
      }
      return true
    } catch (error) {
      console.error('Mark as read failed:', error)
      return false
    }
  }

  // 标记所有为已读
  async function markAllAsRead() {
    try {
      await api.notification.markAllNotificationsAsRead()
      messages.value.forEach((m) => {
        m.isRead = true
      })
      return true
    } catch (error) {
      console.error('Mark all as read failed:', error)
      return false
    }
  }

  // 删除通知
  async function deleteMessage(id: number) {
    try {
      await api.notification.deleteNotification(id)
      messages.value = messages.value.filter((m) => m.id !== id)
      return true
    } catch (error) {
      console.error('Delete notification failed:', error)
      return false
    }
  }

  return {
    messages,
    stats,
    loading,
    unreadMessages,
    unreadCount,
    fetchMessages,
    fetchStats,
    markAsRead,
    markAllAsRead,
    deleteMessage
  }
})
