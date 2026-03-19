<template>
  <div class="settings-section">
    <div class="section-header">
      <div>
        <h3>用户管理</h3>
        <p class="section-description">管理系统用户和权限</p>
      </div>
      <el-button type="primary" :icon="Plus" @click="handleCreate">添加用户</el-button>
    </div>

    <!-- 过滤器 -->
    <div class="filter-container">
      <el-select v-model="filters.role" placeholder="角色" clearable @change="loadUsers">
        <el-option label="管理员" value="admin" />
        <el-option label="普通用户" value="user" />
      </el-select>
      <el-select v-model="filters.is_active" placeholder="状态" clearable @change="loadUsers">
        <el-option label="激活" :value="true" />
        <el-option label="禁用" :value="false" />
      </el-select>
    </div>

    <!-- 用户列表 -->
    <el-table v-loading="loading" :data="users" style="width: 100%">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="username" label="用户名" min-width="150" />
      <el-table-column prop="email" label="邮箱" min-width="200" />
      <el-table-column prop="display_name" label="显示名称" min-width="150" />
      <el-table-column prop="role" label="角色" width="100">
        <template #default="{ row }">
          <el-tag v-if="row.role === 'admin'" type="danger">管理员</el-tag>
          <el-tag v-else type="primary">普通用户</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="is_active" label="状态" width="100">
        <template #default="{ row }">
          <el-tag v-if="row.is_active" type="success">激活</el-tag>
          <el-tag v-else type="info">禁用</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="is_verified" label="邮箱验证" width="120">
        <template #default="{ row }">
          <el-tag v-if="row.is_verified" type="success" size="small">已验证</el-tag>
          <el-tag v-else type="warning" size="small">未验证</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="last_login_at" label="上次登录" width="180">
        <template #default="{ row }">
          {{ row.last_login_at ? formatDate(row.last_login_at) : '从未登录' }}
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="180">
        <template #default="{ row }">
          {{ formatDate(row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <el-button link type="warning" size="small" @click="handleEdit(row)">编辑</el-button>
          <el-button
            link
            type="danger"
            size="small"
            :disabled="row.id === currentUser?.id"
            @click="handleDelete(row)"
          >
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 空状态 -->
    <el-empty v-if="!loading && users.length === 0" description="暂无用户数据" style="margin-top: 20px" />

    <!-- 分页 -->
    <el-pagination
      v-if="total > 0"
      v-model:current-page="pagination.page"
      v-model:page-size="pagination.page_size"
      class="pagination"
      :total="total"
      :page-sizes="[10, 20, 50, 100]"
      layout="total, sizes, prev, pager, next, jumper"
      @current-change="loadUsers"
      @size-change="loadUsers"
    />

    <!-- 创建/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogMode === 'create' ? '添加用户' : '编辑用户'"
      width="600px"
      @close="handleDialogClose"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item v-if="dialogMode === 'create'" label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="请输入用户名（3-50字符）" />
        </el-form-item>
        <el-form-item v-if="dialogMode === 'create'" label="密码" prop="password">
          <el-input v-model="form.password" type="password" placeholder="请输入密码（至少6字符）" show-password />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" type="email" placeholder="请输入邮箱" />
        </el-form-item>
        <el-form-item label="显示名称" prop="display_name">
          <el-input v-model="form.display_name" placeholder="请输入显示名称" />
        </el-form-item>
        <el-form-item v-if="dialogMode === 'create'" label="角色" prop="role">
          <el-select v-model="form.role" placeholder="请选择角色">
            <el-option label="管理员" value="admin" />
            <el-option label="普通用户" value="user" />
          </el-select>
        </el-form-item>
        <el-form-item label="时区" prop="timezone">
          <el-select v-model="form.timezone" placeholder="请选择时区" filterable>
            <el-option label="Asia/Shanghai (UTC+8)" value="Asia/Shanghai" />
            <el-option label="UTC" value="UTC" />
            <el-option label="America/New_York (UTC-5)" value="America/New_York" />
            <el-option label="Europe/London (UTC+0)" value="Europe/London" />
          </el-select>
        </el-form-item>
        <el-form-item label="语言" prop="language">
          <el-select v-model="form.language" placeholder="请选择语言">
            <el-option label="简体中文" value="zh-CN" />
            <el-option label="English" value="en-US" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="dialogMode === 'edit'" label="状态" prop="is_active">
          <el-switch v-model="form.is_active" active-text="激活" inactive-text="禁用" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          {{ dialogMode === 'create' ? '创建' : '更新' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox, FormInstance, FormRules } from 'element-plus'
import { Plus, Edit, Delete } from '@element-plus/icons-vue'
import type { User } from '@/types'
import { getUserList, createUser, updateUser, deleteUser } from '@/api/modules/user'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const currentUser = computed(() => userStore.userInfo)

// 数据
const loading = ref(false)
const users = ref<User[]>([])
const total = ref(0)
const pagination = reactive({
  page: 1,
  page_size: 20
})
const filters = reactive({
  role: undefined as string | undefined,
  is_active: undefined as boolean | undefined
})

// 对话框
const dialogVisible = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const formRef = ref<FormInstance>()
const submitting = ref(false)

// 表单数据
const form = reactive({
  username: '',
  password: '',
  email: '',
  display_name: '',
  role: 'user',
  timezone: 'Asia/Shanghai',
  language: 'zh-CN',
  is_active: true
})

const currentEditId = ref<number | null>(null)

// 表单验证规则
const rules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '用户名长度在3-50个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少6个字符', trigger: 'blur' }
  ],
  email: [
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' }
  ],
  role: [
    { required: true, message: '请选择角色', trigger: 'change' }
  ]
}

// 加载用户列表
const loadUsers = async () => {
  loading.value = true
  try {
    const response = await getUserList({
      page: pagination.page,
      page_size: pagination.page_size,
      role: filters.role,
      is_active: filters.is_active
    })
    users.value = response.data.items
    total.value = response.data.total
  } catch (error) {
    console.error('Failed to load users:', error)
    ElMessage.error('加载用户列表失败')
  } finally {
    loading.value = false
  }
}

// 格式化日期
const formatDate = (dateStr: string) => {
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 处理创建
const handleCreate = () => {
  dialogMode.value = 'create'
  currentEditId.value = null
  resetForm()
  dialogVisible.value = true
}

// 处理编辑
const handleEdit = (user: User) => {
  dialogMode.value = 'edit'
  currentEditId.value = user.id

  // 填充表单
  Object.assign(form, {
    email: user.email || '',
    display_name: user.display_name || '',
    timezone: user.timezone || 'Asia/Shanghai',
    language: user.language || 'zh-CN',
    is_active: user.is_active
  })

  dialogVisible.value = true
}

// 处理删除
const handleDelete = async (user: User) => {
  if (user.id === currentUser.value?.id) {
    ElMessage.warning('不能删除自己')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确定要删除用户 "${user.username}" 吗？此操作不可恢复。`,
      '确认删除',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await deleteUser(user.id)
    ElMessage.success('删除成功')
    loadUsers()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Failed to delete user:', error)
      ElMessage.error('删除失败')
    }
  }
}

// 处理提交
const handleSubmit = async () => {
  if (!formRef.value) return

  try {
    await formRef.value.validate()

    submitting.value = true

    if (dialogMode.value === 'create') {
      await createUser(form)
      ElMessage.success('创建成功')
    } else {
      await updateUser(currentEditId.value!, {
        email: form.email || undefined,
        display_name: form.display_name || undefined,
        timezone: form.timezone,
        language: form.language,
        is_active: form.is_active
      })
      ElMessage.success('更新成功')
    }

    dialogVisible.value = false
    loadUsers()
  } catch (error) {
    console.error('Failed to submit form:', error)
    if (error !== false) {
      ElMessage.error(dialogMode.value === 'create' ? '创建失败' : '更新失败')
    }
  } finally {
    submitting.value = false
  }
}

// 重置表单
const resetForm = () => {
  if (formRef.value) {
    formRef.value.resetFields()
  }
  Object.assign(form, {
    username: '',
    password: '',
    email: '',
    display_name: '',
    role: 'user',
    timezone: 'Asia/Shanghai',
    language: 'zh-CN',
    is_active: true
  })
}

// 对话框关闭回调
const handleDialogClose = () => {
  resetForm()
}

// 初始化
onMounted(() => {
  loadUsers()
})
</script>

<style scoped>
.settings-section {
  padding: 20px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

h3 {
  margin: 0 0 8px 0;
  font-size: 18px;
}

.section-description {
  margin: 0;
  color: #909399;
  font-size: 14px;
}

.filter-container {
  margin-bottom: 20px;
  display: flex;
  gap: 10px;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>
