/**
 * 下载状态管理
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { DownloadTask } from '@/types'
import api from '@/api'

export const useDownloadStore = defineStore('download', () => {
  // 状态
  const tasks = ref<DownloadTask[]>([])
  const loading = ref(false)

  // 计算属性
  const downloadingTasks = computed(() =>
    tasks.value.filter((t) => t.status === 'downloading')
  )

  const completedTasks = computed(() =>
    tasks.value.filter((t) => t.status === 'completed')
  )

  const seedingTasks = computed(() =>
    tasks.value.filter((t) => t.status === 'seeding')
  )

  // 获取下载任务列表
  async function fetchTasks() {
    try {
      loading.value = true
      const response = await api.download.getDownloadTaskList()
      if (response.data) {
        tasks.value = response.data.items
        return true
      }
      return false
    } catch (error) {
      console.error('Fetch download tasks failed:', error)
      return false
    } finally {
      loading.value = false
    }
  }


  // 创建下载任务
  async function createTask(data: { ptResourceId: number; clientId?: number; savePath?: string }) {
    try {
      const response = await api.download.createDownloadTask(data)
      if (response.data) {
        tasks.value.push(response.data)
        return true
      }
      return false
    } catch (error) {
      console.error('Create download task failed:', error)
      return false
    }
  }

  // 暂停任务
  async function pauseTask(id: number) {
    try {
      await api.download.controlDownloadTask(id, { action: 'pause' })
      const task = tasks.value.find((t) => t.id === id)
      if (task) {
        task.status = 'paused'
      }
      return true
    } catch (error) {
      console.error('Pause task failed:', error)
      return false
    }
  }

  // 恢复任务
  async function resumeTask(id: number) {
    try {
      await api.download.controlDownloadTask(id, { action: 'resume' })
      const task = tasks.value.find((t) => t.id === id)
      if (task) {
        task.status = 'downloading'
      }
      return true
    } catch (error) {
      console.error('Resume task failed:', error)
      return false
    }
  }

  // 删除任务
  async function deleteTask(id: number, deleteFiles = false) {
    try {
      await api.download.controlDownloadTask(id, { action: 'delete', delete_files: deleteFiles })
      tasks.value = tasks.value.filter((t) => t.id !== id)
      return true
    } catch (error) {
      console.error('Delete task failed:', error)
      return false
    }
  }

  return {
    tasks,
    loading,
    downloadingTasks,
    completedTasks,
    seedingTasks,
    fetchTasks,
    createTask,
    pauseTask,
    resumeTask,
    deleteTask
  }
})
