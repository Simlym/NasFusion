<template>
  <div class="settings-section">
    <div class="section-header">
      <div>
        <h3>MCP 服务器配置</h3>
        <p class="section-description">管理外部 MCP Server 连接，为 AI 助手扩展工具能力</p>
      </div>
      <el-button type="primary" :icon="Plus" @click="showAddDialog">添加服务器</el-button>
    </div>

    <el-table v-loading="loading" :data="servers" style="width: 100%" row-key="id">
      <el-table-column type="expand">
        <template #default="{ row }">
          <div class="tools-expand" v-if="row._tools && row._tools.length > 0">
            <el-tag v-for="tool in row._tools" :key="tool.name" size="small" style="margin: 2px 4px;">
              {{ tool.name }}
            </el-tag>
          </div>
          <div class="tools-expand" v-else>
            <span style="color: #909399;">暂无工具信息，请点击"同步工具"获取</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="name" label="名称" width="150" />
      <el-table-column label="传输类型" width="100">
        <template #default="{ row }">
          <el-tag :type="row.transport_type === 'http' ? 'info' : 'warning'" size="small">
            {{ row.transport_type === 'http' ? 'HTTP' : 'Stdio' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="连接地址/命令" min-width="200">
        <template #default="{ row }">
          {{ row.transport_type === 'http' ? row.url : row.command }}
        </template>
      </el-table-column>
      <el-table-column label="工具数量" width="90" align="center">
        <template #default="{ row }">
          <span v-if="row.tools_count != null">{{ row.tools_count }}</span>
          <span v-else style="color: #c0c4cc;">-</span>
        </template>
      </el-table-column>
      <el-table-column label="启用" width="80">
        <template #default="{ row }">
          <el-switch
            v-model="row.is_enabled"
            :loading="row._updating"
            @change="toggleEnabled(row)"
          />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="280" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" :loading="row._testing" @click="testConnection(row)">
            测试连接
          </el-button>
          <el-button link type="success" size="small" :loading="row._syncing" @click="syncTools(row)">
            同步工具
          </el-button>
          <el-button link type="warning" size="small" @click="showEditDialog(row)">
            编辑
          </el-button>
          <el-button link type="danger" size="small" @click="handleDelete(row.id)">
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 空状态 -->
    <el-empty v-if="!loading && servers.length === 0" description="暂无 MCP 服务器配置" style="margin-top: 20px">
      <el-button type="primary" @click="showAddDialog">添加第一个 MCP 服务器</el-button>
    </el-empty>

    <!-- 添加/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑 MCP 服务器' : '添加 MCP 服务器'"
      width="600px"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="120px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" placeholder="如：filesystem、weather" />
        </el-form-item>

        <el-form-item label="描述">
          <el-input v-model="form.description" placeholder="服务器用途描述（选填）" />
        </el-form-item>

        <el-form-item label="传输类型" prop="transport_type">
          <el-select v-model="form.transport_type" style="width: 100%;">
            <el-option label="HTTP (SSE)" value="http" />
            <el-option label="Stdio (本地进程)" value="stdio" />
          </el-select>
        </el-form-item>

        <!-- HTTP 模式 -->
        <el-form-item v-if="form.transport_type === 'http'" label="URL" prop="url">
          <el-input v-model="form.url" placeholder="http://localhost:3000/sse" />
        </el-form-item>

        <!-- Stdio 模式 -->
        <template v-if="form.transport_type === 'stdio'">
          <el-form-item label="命令" prop="command">
            <el-input v-model="form.command" placeholder="如：npx、python、node" />
          </el-form-item>

          <el-form-item label="命令参数">
            <el-input
              v-model="form.command_args_text"
              placeholder="每行一个参数，如：&#10;-m&#10;mcp_server"
              type="textarea"
              :rows="3"
            />
          </el-form-item>

          <el-form-item label="环境变量">
            <el-input
              v-model="form.env_vars_text"
              placeholder="每行一个，格式 KEY=VALUE，如：&#10;API_KEY=sk-xxx&#10;DEBUG=true"
              type="textarea"
              :rows="3"
            />
          </el-form-item>
        </template>

        <el-form-item label="认证类型">
          <el-select v-model="form.auth_type" style="width: 100%;">
            <el-option label="无认证" value="none" />
            <el-option label="Bearer Token" value="bearer" />
            <el-option label="API Key" value="api_key" />
          </el-select>
        </el-form-item>

        <el-form-item v-if="form.auth_type !== 'none'" label="认证 Token" prop="auth_token">
          <el-input
            v-model="form.auth_token"
            type="password"
            show-password
            placeholder="输入认证凭据"
          />
        </el-form-item>

        <el-form-item label="启用">
          <el-switch v-model="form.is_enabled" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitForm">
          {{ isEdit ? '更新' : '创建' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import {
  getMCPServerList,
  createMCPServer,
  updateMCPServer,
  deleteMCPServer,
  testMCPServer,
  syncMCPServerTools,
  type MCPServer,
  type MCPServerCreate,
} from '@/api/modules/mcpServer'

interface ServerRow extends MCPServer {
  _updating?: boolean
  _testing?: boolean
  _syncing?: boolean
  _tools?: { name: string; description?: string }[]
}

const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const editId = ref<number>()
const servers = ref<ServerRow[]>([])

const formRef = ref<FormInstance>()

interface FormData {
  name: string
  description: string
  transport_type: string
  url: string
  command: string
  command_args_text: string
  env_vars_text: string
  auth_type: string
  auth_token: string
  is_enabled: boolean
}

const form = reactive<FormData>({
  name: '',
  description: '',
  transport_type: 'http',
  url: '',
  command: '',
  command_args_text: '',
  env_vars_text: '',
  auth_type: 'none',
  auth_token: '',
  is_enabled: true,
})

const rules: FormRules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  transport_type: [{ required: true, message: '请选择传输类型', trigger: 'change' }],
  url: [{
    validator: (_rule: any, value: string, callback: any) => {
      if (form.transport_type === 'http' && !value) {
        callback(new Error('HTTP 模式下 URL 为必填'))
      } else {
        callback()
      }
    },
    trigger: 'blur',
  }],
  command: [{
    validator: (_rule: any, value: string, callback: any) => {
      if (form.transport_type === 'stdio' && !value) {
        callback(new Error('Stdio 模式下命令为必填'))
      } else {
        callback()
      }
    },
    trigger: 'blur',
  }],
  auth_token: [{
    validator: (_rule: any, value: string, callback: any) => {
      if (form.auth_type !== 'none' && !value) {
        callback(new Error('请输入认证 Token'))
      } else {
        callback()
      }
    },
    trigger: 'blur',
  }],
}

function parseEnvVars(text: string): Record<string, string> | undefined {
  if (!text.trim()) return undefined
  const result: Record<string, string> = {}
  for (const line of text.split('\n')) {
    const trimmed = line.trim()
    if (!trimmed) continue
    const idx = trimmed.indexOf('=')
    if (idx > 0) {
      result[trimmed.substring(0, idx)] = trimmed.substring(idx + 1)
    }
  }
  return Object.keys(result).length > 0 ? result : undefined
}

function parseCommandArgs(text: string): string[] | undefined {
  if (!text.trim()) return undefined
  const args = text.split('\n').map(l => l.trim()).filter(Boolean)
  return args.length > 0 ? args : undefined
}

function buildPayload(): MCPServerCreate {
  const data: MCPServerCreate = {
    name: form.name,
    transport_type: form.transport_type,
    auth_type: form.auth_type,
    is_enabled: form.is_enabled,
  }
  if (form.description) data.description = form.description
  if (form.transport_type === 'http') {
    data.url = form.url
  } else {
    data.command = form.command
    data.command_args = parseCommandArgs(form.command_args_text)
    data.env_vars = parseEnvVars(form.env_vars_text)
  }
  if (form.auth_type !== 'none' && form.auth_token) {
    data.auth_token = form.auth_token
  }
  return data
}

async function loadServers() {
  loading.value = true
  try {
    const res = await getMCPServerList()
    servers.value = (res.data || []).map(s => ({ ...s, _tools: undefined }))
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '加载 MCP 服务器列表失败')
  } finally {
    loading.value = false
  }
}

function resetForm() {
  Object.assign(form, {
    name: '',
    description: '',
    transport_type: 'http',
    url: '',
    command: '',
    command_args_text: '',
    env_vars_text: '',
    auth_type: 'none',
    auth_token: '',
    is_enabled: true,
  })
  formRef.value?.clearValidate()
}

function showAddDialog() {
  isEdit.value = false
  resetForm()
  dialogVisible.value = true
}

function showEditDialog(server: MCPServer) {
  isEdit.value = true
  editId.value = server.id
  Object.assign(form, {
    name: server.name,
    description: server.description || '',
    transport_type: server.transport_type,
    url: server.url || '',
    command: server.command || '',
    command_args_text: '',
    env_vars_text: '',
    auth_type: server.auth_type,
    auth_token: '',
    is_enabled: server.is_enabled,
  })
  dialogVisible.value = true
}

async function submitForm() {
  const valid = await formRef.value?.validate()
  if (!valid) return

  submitting.value = true
  try {
    if (isEdit.value && editId.value) {
      const payload = buildPayload()
      // Don't send auth_token if empty (means unchanged)
      if (!payload.auth_token) delete payload.auth_token
      await updateMCPServer(editId.value, payload)
      ElMessage.success('更新成功')
    } else {
      await createMCPServer(buildPayload())
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    await loadServers()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '操作失败')
  } finally {
    submitting.value = false
  }
}

async function toggleEnabled(server: ServerRow) {
  server._updating = true
  try {
    await updateMCPServer(server.id, { is_enabled: server.is_enabled })
    ElMessage.success('更新成功')
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '更新失败')
    server.is_enabled = !server.is_enabled
  } finally {
    server._updating = false
  }
}

async function handleDelete(id: number) {
  try {
    await ElMessageBox.confirm('确定删除这个 MCP 服务器吗？', '确认删除', { type: 'warning' })
    await deleteMCPServer(id)
    ElMessage.success('删除成功')
    await loadServers()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || '删除失败')
    }
  }
}

async function testConnection(server: ServerRow) {
  server._testing = true
  try {
    const res = await testMCPServer(server.id)
    if (res.data.success) {
      const msg = res.data.tools_count != null
        ? `连接成功，发现 ${res.data.tools_count} 个工具`
        : res.data.message || '连接成功'
      ElMessage.success(msg)
    } else {
      ElMessage.error(res.data.message || '连接失败')
    }
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '测试连接失败')
  } finally {
    server._testing = false
  }
}

async function syncTools(server: ServerRow) {
  server._syncing = true
  try {
    const res = await syncMCPServerTools(server.id)
    if (res.data.success) {
      server.tools_count = res.data.tools_count
      server._tools = res.data.tools || []
      ElMessage.success(`同步成功，共 ${res.data.tools_count} 个工具`)
    }
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '同步工具失败')
  } finally {
    server._syncing = false
  }
}

onMounted(() => {
  loadServers()
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

.tools-expand {
  padding: 12px 20px;
}
</style>
