/**
 * 系统设置状态管理
 * 统一管理全局系统设置，避免重复请求
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api'

export const useSettingsStore = defineStore(
  'settings',
  () => {
    // 媒体库设置
    const showAdultContent = ref<boolean>(false)
    const movieShowAnime = ref<boolean>(false)
    const tvShowAnime = ref<boolean>(false)

    // 加载状态
    const loading = ref<boolean>(false)

    // 是否已初始化
    const initialized = ref<boolean>(false)

    /**
     * 初始化系统设置
     * 在应用启动时调用一次
     */
    async function initSettings() {
      if (initialized.value) {
        return
      }

      loading.value = true
      try {
        // 加载媒体库配置
        await loadMediaLibrarySettings()

        // TODO: 在这里加载其他全局配置
        // await loadDownloadSettings()
        // await loadNotificationSettings()

        initialized.value = true
      } catch (error) {
        console.error('初始化系统设置失败:', error)
      } finally {
        loading.value = false
      }
    }

    /**
     * 加载媒体库设置
     */
    async function loadMediaLibrarySettings() {
      try {
        const { data } = await api.settings.getSettings('media_library')
        const items = data?.items ?? []
        const map = Object.fromEntries(items.map(s => [s.key, s.value]))
        showAdultContent.value = map['show_adult_content'] === 'true'
        movieShowAnime.value = map['movie_show_anime'] === 'true'
        tvShowAnime.value = map['tv_show_anime'] === 'true'
      } catch (error) {
        console.error('加载媒体库设置失败:', error)
        showAdultContent.value = false
        movieShowAnime.value = false
        tvShowAnime.value = false
      }
    }

    /**
     * 更新是否显示成人内容
     * @param value 新值
     */
    async function updateShowAdultContent(value: boolean) {
      try {
        await api.settings.upsertSetting('media_library', 'show_adult_content', value.toString(), '是否显示限制级内容')
        showAdultContent.value = value
      } catch (error) {
        console.error('更新成人内容显示设置失败:', error)
        throw error
      }
    }

    /**
     * 更新电影是否显示动画内容
     * @param value 新值
     */
    async function updateMovieShowAnime(value: boolean) {
      try {
        await api.settings.upsertSetting('media_library', 'movie_show_anime', value.toString(), '电影列表是否显示动画内容')
        movieShowAnime.value = value
      } catch (error) {
        console.error('更新电影动画显示设置失败:', error)
        throw error
      }
    }

    /**
     * 更新剧集是否显示动画内容
     * @param value 新值
     */
    async function updateTVShowAnime(value: boolean) {
      try {
        await api.settings.upsertSetting('media_library', 'tv_show_anime', value.toString(), '剧集列表是否显示动画内容')
        tvShowAnime.value = value
      } catch (error) {
        console.error('更新剧集动画显示设置失败:', error)
        throw error
      }
    }

    /**
     * 重新加载所有设置
     * 在设置页面保存后调用
     */
    async function reloadSettings() {
      initialized.value = false
      await initSettings()
    }

    return {
      // 状态
      showAdultContent,
      movieShowAnime,
      tvShowAnime,
      loading,
      initialized,

      // 方法
      initSettings,
      loadMediaLibrarySettings,
      updateShowAdultContent,
      updateMovieShowAnime,
      updateTVShowAnime,
      reloadSettings
    }
  }
)
