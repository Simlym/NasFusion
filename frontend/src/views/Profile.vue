<template>
  <div class="page-container">
    <el-card class="page-header">
      <h1>个人设置</h1>
      <p>管理您的个人信息和偏好设置</p>
    </el-card>

    <el-row :gutter="20">
      <!-- 左侧：个人信息 -->
      <el-col :span="14">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>个人信息</span>
            </div>
          </template>

          <el-form ref="userFormRef" :model="userForm" :rules="userRules" label-width="120px">
            <el-form-item label="头像">
              <div class="avatar-container">
                <el-avatar :size="80" :src="userForm.avatar_url || undefined">
                  {{ userForm.username?.charAt(0).toUpperCase() }}
                </el-avatar>
                <el-button
                  type="primary"
                  size="small"
                  class="upload-btn"
                  @click="handleAvatarUpload"
                >
                  更换头像
                </el-button>
              </div>
            </el-form-item>

            <el-form-item label="用户名">
              <el-input v-model="userForm.username" disabled />
            </el-form-item>

            <el-form-item label="邮箱" prop="email">
              <el-input v-model="userForm.email" type="email" placeholder="请输入邮箱">
                <template v-if="userForm.email && !userForm.is_verified" #append>
                  <el-button @click="handleSendVerification">发送验证邮件</el-button>
                </template>
              </el-input>
              <div v-if="userForm.is_verified" class="verification-tag">
                <el-tag type="success" size="small">已验证</el-tag>
              </div>
              <div v-else-if="userForm.email" class="verification-tag">
                <el-tag type="warning" size="small">未验证</el-tag>
              </div>
            </el-form-item>

            <el-form-item label="显示名称" prop="display_name">
              <el-input v-model="userForm.display_name" placeholder="请输入显示名称" />
            </el-form-item>

            <el-form-item label="时区" prop="timezone">
              <el-select v-model="userForm.timezone" placeholder="请选择时区" filterable>
                <el-option label="Asia/Shanghai (UTC+8)" value="Asia/Shanghai" />
                <el-option label="UTC" value="UTC" />
                <el-option label="America/New_York (UTC-5)" value="America/New_York" />
                <el-option label="Europe/London (UTC+0)" value="Europe/London" />
              </el-select>
            </el-form-item>

            <el-form-item label="语言" prop="language">
              <el-select v-model="userForm.language" placeholder="请选择语言">
                <el-option label="简体中文" value="zh-CN" />
                <el-option label="English" value="en-US" />
              </el-select>
            </el-form-item>

            <el-form-item>
              <el-button type="primary" :loading="userSubmitting" @click="handleUpdateUserInfo">
                保存个人信息
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <!-- 修改密码 -->
        <el-card style="margin-top: 20px">
          <template #header>
            <div class="card-header">
              <span>修改密码</span>
            </div>
          </template>

          <el-form
            ref="passwordFormRef"
            :model="passwordForm"
            :rules="passwordRules"
            label-width="120px"
          >
            <el-form-item label="旧密码" prop="old_password">
              <el-input
                v-model="passwordForm.old_password"
                type="password"
                placeholder="请输入旧密码"
                show-password
              />
            </el-form-item>

            <el-form-item label="新密码" prop="new_password">
              <el-input
                v-model="passwordForm.new_password"
                type="password"
                placeholder="请输入新密码"
                show-password
              />
            </el-form-item>

            <el-form-item label="确认密码" prop="confirm_password">
              <el-input
                v-model="passwordForm.confirm_password"
                type="password"
                placeholder="请再次输入新密码"
                show-password
              />
            </el-form-item>

            <el-form-item>
              <el-button type="primary" :loading="passwordSubmitting" @click="handleChangePassword">
                修改密码
              </el-button>
              <el-button @click="resetPasswordForm">重置</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <!-- 右侧：偏好设置 -->
      <el-col :span="10">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>偏好设置</span>
            </div>
          </template>

          <el-form ref="profileFormRef" :model="profileForm" label-width="140px">
            <el-divider content-position="left">界面设置</el-divider>

            <el-form-item label="主题">
              <el-radio-group v-model="profileForm.ui_theme">
                <el-radio label="light">浅色</el-radio>
                <el-radio label="dark">深色</el-radio>
                <el-radio label="ocean">海洋</el-radio>
                <el-radio label="auto">跟随系统</el-radio>
              </el-radio-group>
            </el-form-item>

            <el-form-item label="每页显示数量">
              <el-input-number v-model="profileForm.items_per_page" :min="10" :max="200" />
            </el-form-item>

            <el-divider content-position="left">下载设置</el-divider>

            <el-form-item label="最小做种数">
              <el-input-number v-model="profileForm.min_seeders" :min="0" />
            </el-form-item>

            <el-form-item label="最大自动下载(GB)">
              <el-input-number v-model="profileForm.max_auto_download_size_gb" :min="0" />
            </el-form-item>

            <el-form-item label="自动开始下载">
              <el-switch v-model="profileForm.auto_start_download" />
            </el-form-item>

            <el-divider content-position="left">通知设置</el-divider>

            <el-form-item label="启用通知">
              <el-switch v-model="profileForm.notification_enabled" />
            </el-form-item>

            <el-form-item label="邮件通知">
              <el-switch v-model="profileForm.email_notifications" />
            </el-form-item>

            <el-form-item label="推送通知">
              <el-switch v-model="profileForm.push_notifications" />
            </el-form-item>

            <el-divider content-position="left">AI推荐</el-divider>

            <el-form-item label="启用AI推荐">
              <el-switch v-model="profileForm.ai_recommendations_enabled" />
            </el-form-item>

            <el-form-item label="推荐频率">
              <el-select
                v-model="profileForm.recommendation_frequency"
                :disabled="!profileForm.ai_recommendations_enabled"
              >
                <el-option label="每天" value="daily" />
                <el-option label="每周" value="weekly" />
                <el-option label="每月" value="monthly" />
              </el-select>
            </el-form-item>

            <el-divider content-position="left">隐私设置</el-divider>

            <el-form-item label="分享匿名统计">
              <el-switch v-model="profileForm.share_anonymous_stats" />
            </el-form-item>

            <el-form-item label="公开观影列表">
              <el-switch v-model="profileForm.public_watchlist" />
            </el-form-item>

            <el-form-item>
              <el-button type="primary" :loading="profileSubmitting" @click="handleUpdateProfile">
                保存偏好设置
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
    </el-row>

    <!-- 头像上传对话框 -->
    <el-dialog v-model="avatarDialogVisible" title="更换头像" width="500px">
      <div class="avatar-upload-container">
        <el-upload
          class="avatar-uploader"
          :auto-upload="false"
          :show-file-list="false"
          :on-change="handleAvatarChange"
          accept="image/jpeg,image/png,image/jpg,image/gif,image/webp"
        >
          <el-avatar v-if="previewAvatar" :size="150" :src="previewAvatar" />
          <el-avatar v-else :size="150">
            <el-icon><Plus /></el-icon>
          </el-avatar>
        </el-upload>
        <div class="upload-hint">
          <p>支持 JPG, PNG, GIF, WebP 格式，文件大小不超过 5MB</p>
        </div>
      </div>
      <template #footer>
        <el-button @click="avatarDialogVisible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="uploading"
          :disabled="!selectedFile"
          @click="handleUploadAvatar"
        >
          上传
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, FormInstance, FormRules } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import type { UploadFile } from 'element-plus'
import {
  getMyInfo,
  updateMyInfo,
  changePassword,
  getUserProfile,
  updateUserProfile,
  uploadAvatar
} from '@/api/modules/user'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()

// 对话框
const avatarDialogVisible = ref(false)

// 头像上传
const uploading = ref(false)
const selectedFile = ref<File | null>(null)
const previewAvatar = ref('')

// 用户信息表单
const userFormRef = ref<FormInstance>()
const userSubmitting = ref(false)
const userForm = reactive({
  username: '',
  email: '',
  display_name: '',
  avatar_url: '',
  timezone: 'Asia/Shanghai',
  language: 'zh-CN',
  is_verified: false
})

const userRules: FormRules = {
  email: [{ type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' }]
}

// 密码表单
const passwordFormRef = ref<FormInstance>()
const passwordSubmitting = ref(false)
const passwordForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: ''
})

const validateConfirmPassword = (rule: any, value: any, callback: any) => {
  if (value === '') {
    callback(new Error('请再次输入新密码'))
  } else if (value !== passwordForm.new_password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const passwordRules: FormRules = {
  old_password: [{ required: true, message: '请输入旧密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少6个字符', trigger: 'blur' }
  ],
  confirm_password: [{ required: true, validator: validateConfirmPassword, trigger: 'blur' }]
}

// 偏好设置表单
const profileFormRef = ref<FormInstance>()
const profileSubmitting = ref(false)
const profileForm = reactive({
  ui_theme: 'ocean' as 'light' | 'dark' | 'ocean' | 'auto',
  language: 'zh-CN',
  timezone: 'Asia/Shanghai',
  items_per_page: 50,
  min_seeders: 0,
  max_auto_download_size_gb: 50,
  auto_start_download: true,
  notification_enabled: true,
  email_notifications: false,
  push_notifications: false,
  ai_recommendations_enabled: false,
  recommendation_frequency: 'weekly',
  share_anonymous_stats: true,
  public_watchlist: false
})

// 加载用户信息
const loadUserInfo = async () => {
  try {
    const user = await getMyInfo()
    Object.assign(userForm, {
      username: user.username,
      email: user.email || '',
      display_name: user.display_name || '',
      avatar_url: user.avatar_url || '',
      timezone: user.timezone || 'Asia/Shanghai',
      language: user.language || 'zh-CN',
      is_verified: user.is_verified
    })
  } catch (error) {
    console.error('Failed to load user info:', error)
    ElMessage.error('加载用户信息失败')
  }
}

// 加载用户配置
const loadUserProfile = async () => {
  try {
    const profile = await getUserProfile()
    Object.assign(profileForm, {
      ui_theme: profile.ui_theme || 'ocean',
      language: profile.language || 'zh-CN',
      timezone: profile.timezone || 'Asia/Shanghai',
      items_per_page: profile.items_per_page || 50,
      min_seeders: profile.min_seeders || 0,
      max_auto_download_size_gb: profile.max_auto_download_size_gb || 50,
      auto_start_download: profile.auto_start_download !== false,
      notification_enabled: profile.notification_enabled !== false,
      email_notifications: profile.email_notifications || false,
      push_notifications: profile.push_notifications || false,
      ai_recommendations_enabled: profile.ai_recommendations_enabled || false,
      recommendation_frequency: profile.recommendation_frequency || 'weekly',
      share_anonymous_stats: profile.share_anonymous_stats !== false,
      public_watchlist: profile.public_watchlist || false
    })
  } catch (error) {
    console.error('Failed to load user profile:', error)
    // 配置可能不存在，不显示错误
  }
}

// 更新用户信息
const handleUpdateUserInfo = async () => {
  if (!userFormRef.value) return

  try {
    await userFormRef.value.validate()

    userSubmitting.value = true
    await updateMyInfo({
      email: userForm.email || undefined,
      display_name: userForm.display_name || undefined,
      timezone: userForm.timezone,
      language: userForm.language
    })

    ElMessage.success('个人信息更新成功')

    // 更新store中的用户信息
    await userStore.fetchUserInfo()
  } catch (error) {
    console.error('Failed to update user info:', error)
    if (error !== false) {
      ElMessage.error('更新失败')
    }
  } finally {
    userSubmitting.value = false
  }
}

// 修改密码
const handleChangePassword = async () => {
  if (!passwordFormRef.value) return

  try {
    await passwordFormRef.value.validate()

    passwordSubmitting.value = true
    await changePassword({
      old_password: passwordForm.old_password,
      new_password: passwordForm.new_password
    })

    ElMessage.success('密码修改成功')
    resetPasswordForm()
  } catch (error) {
    console.error('Failed to change password:', error)
    if (error !== false) {
      ElMessage.error('修改密码失败，请检查旧密码是否正确')
    }
  } finally {
    passwordSubmitting.value = false
  }
}

// 重置密码表单
const resetPasswordForm = () => {
  if (passwordFormRef.value) {
    passwordFormRef.value.resetFields()
  }
  Object.assign(passwordForm, {
    old_password: '',
    new_password: '',
    confirm_password: ''
  })
}

// 更新偏好设置
const handleUpdateProfile = async () => {
  if (!profileFormRef.value) return

  try {
    profileSubmitting.value = true
    await updateUserProfile(profileForm)

    ElMessage.success('偏好设置更新成功')
  } catch (error) {
    console.error('Failed to update profile:', error)
    ElMessage.error('更新失败')
  } finally {
    profileSubmitting.value = false
  }
}

// 头像上传
const handleAvatarUpload = () => {
  selectedFile.value = null
  previewAvatar.value = ''
  avatarDialogVisible.value = true
}

// 处理头像文件选择
const handleAvatarChange = (file: UploadFile) => {
  if (!file.raw) return

  // 验证文件大小
  const maxSize = 5 * 1024 * 1024 // 5MB
  if (file.size! > maxSize) {
    ElMessage.error('文件大小不能超过 5MB')
    return
  }

  // 验证文件类型
  const allowedTypes = ['image/jpeg', 'image/png', 'image/jpg', 'image/gif', 'image/webp']
  if (!allowedTypes.includes(file.raw.type)) {
    ElMessage.error('只支持 JPG, PNG, GIF, WebP 格式的图片')
    return
  }

  selectedFile.value = file.raw

  // 预览图片
  const reader = new FileReader()
  reader.onload = (e) => {
    previewAvatar.value = e.target?.result as string
  }
  reader.readAsDataURL(file.raw)
}

// 上传头像
const handleUploadAvatar = async () => {
  if (!selectedFile.value) {
    ElMessage.warning('请先选择图片')
    return
  }

  uploading.value = true
  try {
    const result = await uploadAvatar(selectedFile.value)
    ElMessage.success(result.message || '头像上传成功')

    // 更新用户信息中的头像
    userForm.avatar_url = result.avatar_url
    await userStore.fetchUserInfo()

    avatarDialogVisible.value = false
  } catch (error) {
    console.error('Failed to upload avatar:', error)
    ElMessage.error('上传失败')
  } finally {
    uploading.value = false
  }
}

// 发送验证邮件
const handleSendVerification = () => {
  ElMessage.info('邮箱验证功能即将推出...')
}

// 初始化
onMounted(() => {
  loadUserInfo()
  loadUserProfile()
})
</script>

<style scoped>
.page-container {
  width: 100%;
}

.page-header {
  margin-bottom: 20px;
}

.page-header h1 {
  margin: 0 0 10px 0;
  font-size: 24px;
}

.page-header p {
  margin: 0;
  color: #909399;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.avatar-container {
  display: flex;
  align-items: center;
  gap: 20px;
}

.upload-btn {
  margin-left: 10px;
}

.verification-tag {
  margin-top: 5px;
}

.avatar-upload-container {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  min-height: 200px;
}

.avatar-uploader {
  text-align: center;
}

.avatar-uploader :deep(.el-upload) {
  cursor: pointer;
  position: relative;
  overflow: hidden;
  border-radius: 50%;
}

.avatar-uploader :deep(.el-upload:hover) {
  opacity: 0.8;
}

.upload-hint {
  margin-top: 20px;
  text-align: center;
  color: #909399;
  font-size: 14px;
}
</style>
