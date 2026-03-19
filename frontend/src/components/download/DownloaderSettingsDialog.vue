<template>
  <el-dialog v-model="dialogVisible" title="下载器配置管理" width="90%" :before-close="handleClose">
    <el-button type="primary" :icon="Plus" style="margin-bottom: 20px" @click="showAddDialog">
      添加下载器
    </el-button>

    <el-table v-loading="loading" :data="downloaders" style="width: 100%">
      <el-table-column prop="name" label="名称" width="150" />
      <el-table-column label="类型" width="120">
        <template #default="{ row }">
          {{ DownloaderTypeLabels[row.type] }}
        </template>
      </el-table-column>
      <el-table-column label="连接地址" width="250">
        <template #default="{ row }">
          {{ (row.use_ssl ? 'https://' : 'http://') + row.host + ':' + row.port }}
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.status === 'online' ? 'success' : 'danger'">
            {{ DownloaderStatusLabels[row.status] }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="默认" width="80">
        <template #default="{ row }">
          <el-tag v-if="row.is_default" type="success">默认</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="启用" width="80">
        <template #default="{ row }">
          <el-switch
            v-model="row.is_enabled"
            :loading="row._updating"
            @change="updateDownloader(row)"
          />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="210" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click="testConnection(row.id)">
            测试连接
          </el-button>
          <el-button link type="warning" size="small" @click="showEditDialog(row)">
            编辑
          </el-button>
          <el-button link type="danger" size="small" @click="deleteDownloader(row.id)">
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 添加/编辑下载器对话框 -->
    <el-dialog
      v-model="formDialogVisible"
      :title="isEdit ? '编辑下载器' : '添加下载器'"
      width="700px"
      :append-to-body="true"
    >
      <el-tabs v-model="activeTabName">
        <!-- 基础配置 -->
        <el-tab-pane label="基础配置" name="basic">
          <el-form ref="formRef" :model="form" :rules="rules" label-width="140px">
            <el-form-item label="名称" prop="name">
              <el-input v-model="form.name" placeholder="如：qBittorrent-本地" />
            </el-form-item>

            <el-form-item label="类型" prop="type">
              <el-select v-model="form.type" placeholder="请选择" @change="onTypeChange">
                <el-option label="qBittorrent" value="qbittorrent" />
                <el-option label="Transmission" value="transmission" />
                <el-option label="Synology Download Station" value="synology_ds" />
              </el-select>
            </el-form-item>

            <el-form-item label="主机地址" prop="host">
              <el-input v-model="form.host" placeholder="localhost 或 IP地址" />
            </el-form-item>

            <el-form-item label="端口" prop="port">
              <el-input-number v-model="form.port" :min="1" :max="65535" />
            </el-form-item>

            <el-form-item label="使用SSL">
              <el-switch v-model="form.use_ssl" />
            </el-form-item>

            <el-form-item label="用户名" prop="username">
              <el-input v-model="form.username" placeholder="下载器用户名" />
            </el-form-item>

            <el-form-item label="密码" prop="password">
              <el-input
                v-model="form.password"
                type="password"
                placeholder="下载器密码"
                show-password
              />
            </el-form-item>

            <el-form-item label="设为默认">
              <el-switch v-model="form.is_default" />
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- 高级配置 -->
        <el-tab-pane label="高级配置" name="advanced">
          <el-form :model="form" label-width="140px">
            <el-form-item label="HR处理策略">
              <el-select v-model="form.hr_strategy">
                <el-option label="不处理" value="none" />
                <el-option label="自动设置做种限制" value="auto_limit" />
                <el-option label="手动处理" value="manual" />
              </el-select>
            </el-form-item>

            <el-form-item label="最大并发下载">
              <el-input-number v-model="form.max_concurrent_downloads" :min="1" :max="20" />
            </el-form-item>

            <el-form-item label="下载速度限制">
              <el-input-number
                v-model="form.download_speed_limit"
                :min="0"
                placeholder="KB/s，0为不限制"
              />
              <span style="margin-left: 10px; color: #909399">KB/s，0为不限制</span>
            </el-form-item>

            <el-form-item label="上传速度限制">
              <el-input-number
                v-model="form.upload_speed_limit"
                :min="0"
                placeholder="KB/s，0为不限制"
              />
              <span style="margin-left: 10px; color: #909399">KB/s，0为不限制</span>
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>

      <template #footer>
        <el-button @click="formDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitForm">
          {{ isEdit ? '更新' : '创建' }}
        </el-button>
      </template>
    </el-dialog>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { Plus, Edit, Delete, Connection } from '@element-plus/icons-vue'
import {
  getDownloaderList,
  createDownloader,
  updateDownloader as updateDownloaderAPI,
  deleteDownloader as deleteDownloaderAPI,
  testDownloaderConnection,
  type DownloaderConfig,
  type DownloaderConfigCreate,
  DownloaderTypeLabels,
  DownloaderStatusLabels
} from '@/api/modules/download'

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'refresh'): void
}>()

const dialogVisible = ref(props.modelValue)
const formDialogVisible = ref(false)
const activeTabName = ref('basic')
const loading = ref(false)
const submitting = ref(false)
const isEdit = ref(false)
const editId = ref<number>()

const downloaders = ref<(DownloaderConfig & { _updating?: boolean })[]>([])

const formRef = ref<FormInstance>()
const form = reactive<DownloaderConfigCreate>({
  name: '',
  type: 'qbittorrent',
  host: 'localhost',
  port: 8080,
  username: 'admin',
  password: '',
  use_ssl: false,
  is_default: false,
  is_enabled: true,
  hr_strategy: 'auto_limit',
  max_concurrent_downloads: 5,
  download_speed_limit: 0,
  upload_speed_limit: 0
})

const rules: FormRules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  type: [{ required: true, message: '请选择类型', trigger: 'change' }],
  host: [{ required: true, message: '请输入主机地址', trigger: 'blur' }],
  port: [{ required: true, message: '请输入端口', trigger: 'blur' }],
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

// 监听props变化
watch(
  () => props.modelValue,
  (val) => {
    dialogVisible.value = val
    if (val) {
      loadDownloaders()
    }
  }
)

// 监听dialog变化
watch(dialogVisible, (val) => {
  emit('update:modelValue', val)
})

// 加载下载器列表
async function loadDownloaders() {
  loading.value = true
  try {
    const res = await getDownloaderList()
    downloaders.value = res.data.items
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '加载下载器列表失败')
  } finally {
    loading.value = false
  }
}

// 显示添加对话框
function showAddDialog() {
  isEdit.value = false
  resetForm()
  formDialogVisible.value = true
}

// 显示编辑对话框
function showEditDialog(downloader: DownloaderConfig) {
  isEdit.value = true
  editId.value = downloader.id

  // 填充表单
  Object.assign(form, {
    name: downloader.name,
    type: downloader.type,
    host: downloader.host,
    port: downloader.port,
    username: downloader.username || '',
    password: '', // 密码不回填
    use_ssl: downloader.use_ssl,
    is_default: downloader.is_default,
    is_enabled: downloader.is_enabled,
    hr_strategy: downloader.hr_strategy,
    max_concurrent_downloads: downloader.max_concurrent_downloads,
    download_speed_limit: downloader.download_speed_limit || 0,
    upload_speed_limit: downloader.upload_speed_limit || 0
  })

  formDialogVisible.value = true
}

// 下载器类型变化时，自动设置默认端口
function onTypeChange(type: string) {
  if (type === 'qbittorrent') {
    form.port = 8080
  } else if (type === 'transmission') {
    form.port = 9091
  } else if (type === 'synology_ds') {
    form.port = 5000
  }
}

// 重置表单
function resetForm() {
  Object.assign(form, {
    name: '',
    type: 'qbittorrent',
    host: 'localhost',
    port: 8080,
    username: 'admin',
    password: '',
    use_ssl: false,
    is_default: false,
    is_enabled: true,
    hr_strategy: 'auto_limit',
    max_concurrent_downloads: 5,
    download_speed_limit: 0,
    upload_speed_limit: 0
  })
  activeTabName.value = 'basic'
  formRef.value?.clearValidate()
}

// 提交表单
async function submitForm() {
  const valid = await formRef.value?.validate()
  if (!valid) return

  submitting.value = true
  try {
    if (isEdit.value && editId.value) {
      // 编辑模式：如果密码为空，不传密码字段
      const updateData: any = { ...form }
      if (!updateData.password) {
        delete updateData.password
      }
      await updateDownloaderAPI(editId.value, updateData)
      ElMessage.success('更新成功')
    } else {
      // 创建模式
      await createDownloader(form)
      ElMessage.success('创建成功')
    }

    formDialogVisible.value = false
    await loadDownloaders()
    emit('refresh')
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '操作失败')
  } finally {
    submitting.value = false
  }
}

// 更新下载器（快捷操作）
async function updateDownloader(downloader: DownloaderConfig & { _updating?: boolean }) {
  downloader._updating = true
  try {
    await updateDownloaderAPI(downloader.id, {
      is_enabled: downloader.is_enabled
    })
    ElMessage.success('更新成功')
    emit('refresh')
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '更新失败')
    // 恢复原状态
    downloader.is_enabled = !downloader.is_enabled
  } finally {
    downloader._updating = false
  }
}

// 删除下载器
async function deleteDownloader(id: number) {
  try {
    await ElMessageBox.confirm('确定删除这个下载器吗？', '确认删除', {
      type: 'warning'
    })

    await deleteDownloaderAPI(id)
    ElMessage.success('删除成功')
    await loadDownloaders()
    emit('refresh')
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || '删除失败')
    }
  }
}

// 测试连接
async function testConnection(id: number) {
  try {
    const res = await testDownloaderConnection(id)
    if (res.data.success) {
      ElMessage.success(res.data.message || '连接成功')
    } else {
      ElMessage.error(res.data.message || '连接失败')
    }
    await loadDownloaders()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '测试连接失败')
  }
}

// 关闭对话框
function handleClose() {
  dialogVisible.value = false
}
</script>

<style scoped>
:deep(.el-dialog__body) {
  padding: 20px;
}
</style>
