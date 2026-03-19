/**
 * 用户状态管理
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { User, UserProfile, LoginForm } from '@/types'
import api from '@/api'
import { getToken, setToken, setRefreshToken, clearTokens } from '@/api/request'

// 用户信息缓存键
const USER_INFO_KEY = 'user_info'

// 从 localStorage 获取用户信息
function getUserFromStorage(): User | null {
  try {
    const userStr = localStorage.getItem(USER_INFO_KEY)
    return userStr ? JSON.parse(userStr) : null
  } catch (error) {
    console.error('Failed to parse user info from storage:', error)
    return null
  }
}

// 保存用户信息到 localStorage
function saveUserToStorage(user: User | null): void {
  if (user) {
    localStorage.setItem(USER_INFO_KEY, JSON.stringify(user))
  } else {
    localStorage.removeItem(USER_INFO_KEY)
  }
}

export const useUserStore = defineStore('user', () => {
  // 状态（从 localStorage 恢复）
  const user = ref<User | null>(getUserFromStorage())
  const profile = ref<UserProfile | null>(null)
  const token = ref<string | null>(getToken())
  const isLoggedIn = ref<boolean>(!!token.value)

  // 登录
  async function login(loginForm: LoginForm) {
    const response = await api.user.login(loginForm)
    if (response?.data) {
      const tokenData = response.data

      // 保存 token
      setToken(tokenData.access_token, tokenData.expires_in)
      if (tokenData.refresh_token) {
        setRefreshToken(tokenData.refresh_token)
      }

      token.value = tokenData.access_token
      isLoggedIn.value = true

      // 获取用户信息
      await fetchCurrentUser()

      return true
    }
    return false
  }

  // 登出
  async function logout() {
    // 清除本地数据
    clearTokens()
    saveUserToStorage(null)
    token.value = null
    user.value = null
    profile.value = null
    isLoggedIn.value = false
  }

  // 获取当前用户信息
  async function fetchCurrentUser() {
    try {
      const response = await api.user.getCurrentUser()
      if (response?.data) {
        user.value = response.data
        saveUserToStorage(response.data)
        return true
      }
      return false
    } catch (error) {
      console.error('Fetch current user failed:', error)
      // 获取失败时清除缓存的用户信息
      user.value = null
      saveUserToStorage(null)
      throw error
    }
  }

  // 获取用户配置
  async function fetchUserProfile() {
    try {
      const response = await api.user.getUserProfile()
      if (response?.data) {
        profile.value = response.data
        return true
      }
      return false
    } catch (error) {
      console.error('Fetch user profile failed:', error)
      return false
    }
  }

  // 更新用户配置
  async function updateProfile(data: Partial<UserProfile>) {
    try {
      const response = await api.user.updateUserProfile(data)
      if (response?.data) {
        profile.value = response.data
        return true
      }
      return false
    } catch (error) {
      console.error('Update profile failed:', error)
      return false
    }
  }

  return {
    user,
    profile,
    token,
    isLoggedIn,
    login,
    logout,
    fetchCurrentUser,
    fetchUserProfile,
    updateProfile
  }
})
