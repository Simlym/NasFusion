/**
 * 用户相关 API
 */

import request from '../request'
import { User, UserProfile, LoginForm, LoginResponse } from '@/types'

export interface UserListParams {
  page?: number
  page_size?: number
  role?: string
  is_active?: boolean
}

export interface UserListResponse {
  items: User[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

// 用户登录
export function login(data: LoginForm) {
  return request.post<LoginResponse>('/auth/login', data)
}

// 获取当前用户信息
export function getCurrentUser() {
  return request.get<User>('/auth/me')
}

// 刷新token
export function refreshToken() {
  return request.post<LoginResponse>('/auth/refresh')
}

// 获取个人信息
export function getMyInfo() {
  return request.get<User>('/users/me')
}

// 更新个人信息
export function updateMyInfo(data: Partial<User>) {
  return request.put<User>('/users/me', data)
}

// 获取用户配置
export function getUserProfile() {
  return request.get<UserProfile>('/users/me/profile')
}

// 更新用户配置
export function updateUserProfile(data: Partial<UserProfile>) {
  return request.put<UserProfile>('/users/me/profile', data)
}

// 修改密码
export function changePassword(data: { old_password: string; new_password: string }) {
  return request.post<{ message: string }>('/users/me/change-password', data)
}

// 创建用户（管理员）
export function createUser(data: any) {
  return request.post<User>('/users', data)
}

// 获取指定用户信息（管理员）
export function getUserById(userId: number) {
  return request.get<User>(`/users/${userId}`)
}

// 更新指定用户信息（管理员）
export function updateUser(userId: number, data: Partial<User>) {
  return request.put<User>(`/users/${userId}`, data)
}

// 获取用户列表（管理员）
export function getUserList(params?: UserListParams) {
  return request.get<UserListResponse>('/users', { params })
}

// 删除用户（管理员）
export function deleteUser(userId: number) {
  return request.delete<void>(`/users/${userId}`)
}

// 上传头像
export function uploadAvatar(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  return request.post<{ avatar_url: string; message: string }>('/users/me/avatar', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}
