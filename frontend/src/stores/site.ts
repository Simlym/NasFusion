/**
 * PT站点状态管理
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { PTSite, PTSiteStats } from '@/types'
import api from '@/api'

export const useSiteStore = defineStore('site', () => {
  // 状态
  const sites = ref<PTSite[]>([])
  const stats = ref<PTSiteStats[]>([])
  const loading = ref(false)

  // 获取站点列表
  async function fetchSites() {
    try {
      loading.value = true
      const response = await api.site.getSiteList()
      if (response.data) {
        sites.value = response.data.items
        return true
      }
      return false
    } catch (error) {
      console.error('Fetch sites failed:', error)
      return false
    } finally {
      loading.value = false
    }
  }

  // 获取站点统计
  async function fetchSiteStats() {
    try {
      const response = await api.site.getSiteStats()
      if (response.data) {
        // 转换API响应格式到前端类型
        stats.value = response.data.map((item) => ({
          siteId: item.site_id,
          siteName: item.site_name,
          totalResources: item.total_resources,
          todayAdded: item.today_added,
          syncStatus: item.sync_status,
          lastSyncTime: item.last_sync_time,
          healthStatus: item.health_status
        }))
        return true
      }
      return false
    } catch (error) {
      console.error('Fetch site stats failed:', error)
      return false
    }
  }

  // 添加站点
  async function addSite(siteData: any) {
    try {
      const response = await api.site.createSite(siteData)
      if (response.data) {
        sites.value.push(response.data)
        return true
      }
      return false
    } catch (error) {
      console.error('Add site failed:', error)
      return false
    }
  }

  // 更新站点
  async function updateSite(id: number, siteData: any) {
    try {
      const response = await api.site.updateSite(id, siteData)
      if (response.data) {
        const index = sites.value.findIndex((s) => s.id === id)
        if (index !== -1) {
          sites.value[index] = response.data
        }
        return true
      }
      return false
    } catch (error) {
      console.error('Update site failed:', error)
      return false
    }
  }

  // 删除站点
  async function deleteSite(id: number) {
    try {
      await api.site.deleteSite(id)
      sites.value = sites.value.filter((s) => s.id !== id)
      return true
    } catch (error) {
      console.error('Delete site failed:', error)
      return false
    }
  }

  // 测试站点连接
  async function testConnection(id: number) {
    try {
      const response = await api.site.testSiteConnection(id)
      return response.data
    } catch (error) {
      console.error('Test connection failed:', error)
      return { success: false, message: '测试失败' }
    }
  }

  // 触发站点同步
  async function triggerSync(id: number) {
    try {
      await api.site.triggerSiteSync(id)
      return true
    } catch (error) {
      console.error('Trigger sync failed:', error)
      return false
    }
  }

  return {
    sites,
    stats,
    loading,
    fetchSites,
    fetchSiteStats,
    addSite,
    updateSite,
    deleteSite,
    testConnection,
    triggerSync
  }
})
