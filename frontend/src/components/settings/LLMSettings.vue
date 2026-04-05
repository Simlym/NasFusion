<template>
  <div class="settings-section">
    <div class="section-header">
      <div>
        <h3>LLM 配置</h3>
        <p class="section-description">管理 LLM 供应商配置，AI 助手将使用这些配置进行对话</p>
      </div>
      <el-button type="primary" :icon="Plus" @click="showAddDialog">添加配置</el-button>
    </div>

    <el-table v-loading="loading" :data="configs" style="width: 100%" row-key="id">
      <el-table-column prop="name" label="名称" width="150" />
      <el-table-column label="供应商" width="120">
        <template #default="{ row }">
          {{ getProviderDisplayName(row.provider) }}
        </template>
      </el-table-column>
      <el-table-column prop="model" label="模型" min-width="150" />
      <el-table-column label="启用" width="80">
        <template #default="{ row }">
          <el-switch
            v-model="row.is_enabled"
            :loading="row._updating"
            @change="toggleEnabled(row)"
          />
        </template>
      </el-table-column>
      <el-table-column label="最后测试" width="180">
        <template #default="{ row }">
          <span v-if="row.last_test_at" style="font-size: 12px; color: #909399;">
            {{ formatTime(row.last_test_at) }}
          </span>
          <span v-else style="color: #c0c4cc;">-</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" :loading="row._testing" @click="handleTest(row)">
            测试
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
    <el-empty v-if="!loading && configs.length === 0" description="暂无 LLM 配置" style="margin-top: 20px">
      <el-button type="primary" @click="showAddDialog">添加第一个 LLM 配置</el-button>
    </el-empty>

    <!-- 添加/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑 LLM 配置' : '添加 LLM 配置'"
      width="600px"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="120px">
        <el-form-item label="配置名称" prop="name">
          <el-input v-model="form.name" placeholder="如：我的OpenAI" />
        </el-form-item>

        <el-form-item label="供应商" prop="provider">
          <el-select
            v-model="form.provider"
            style="width: 100%;"
            @change="onProviderChange"
            :disabled="isEdit"
          >
            <el-option
              v-for="p in providerTypes"
              :key="p.provider"
              :label="p.display_name"
              :value="p.provider"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="模型" prop="model">
          <el-select
            v-if="currentProviderHasModels"
            v-model="form.model"
            style="width: 100%;"
          >
            <el-option
              v-for="m in currentModels"
              :key="m.id"
              :label="m.name"
              :value="m.id"
            />
          </el-select>
          <el-select
            v-else
            v-model="form.model"
            style="width: 100%;"
            filterable
            allow-create
            default-first-option
            placeholder="输入或选择模型名称"
          >
            <el-option
              v-for="m in currentModels"
              :key="m.id"
              :label="m.name"
              :value="m.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="API Key" prop="api_key">
          <el-input
            v-model="form.api_key"
            type="password"
            show-password
            :placeholder="isEdit ? '留空则不修改' : '请输入 API Key'"
          />
        </el-form-item>

        <el-form-item label="API 地址">
          <el-input
            v-model="form.api_base"
            :placeholder="currentDefaultApiBase || '可选，使用默认地址'"
          />
        </el-form-item>

        <el-form-item label="代理">
          <el-input
            v-model="form.proxy"
            placeholder="可选，如 http://127.0.0.1:7890"
          />
        </el-form-item>

        <el-form-item label="温度">
          <el-slider
            v-model="form.temperature"
            :min="0"
            :max="1"
            :step="0.1"
            show-input
            style="width: 100%"
          />
        </el-form-item>

        <el-form-item label="Max Tokens">
          <el-input-number v-model="form.max_tokens" :min="100" :max="128000" :step="512" style="width: 100%" />
        </el-form-item>

        <el-form-item label="Top P">
          <el-slider
            v-model="form.top_p"
            :min="0"
            :max="1"
            :step="0.05"
            show-input
            style="width: 100%"
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
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import {
  getLLMConfigs,
  createLLMConfig,
  updateLLMConfig,
  deleteLLMConfig,
  testLLMConfig,
  getProviderTypes,
  type LLMConfig,
  type LLMConfigCreate,
  type ProviderTypeInfo,
} from '@/api/modules/llmConfig'

interface ConfigRow extends LLMConfig {
  _updating?: boolean
  _testing?: boolean
}

const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const editId = ref<number>()
const configs = ref<ConfigRow[]>([])
const providerTypes = ref<ProviderTypeInfo[]>([])

const formRef = ref<FormInstance>()

const form = reactive({
  name: '',
  provider: 'zhipu',
  model: 'glm-5',
  api_key: '',
  api_base: '',
  proxy: '',
  temperature: 0.7,
  max_tokens: 2048,
  top_p: 0.9,
  is_enabled: true,
})

const rules: FormRules = {
  name: [{ required: true, message: '请输入配置名称', trigger: 'blur' }],
  provider: [{ required: true, message: '请选择供应商', trigger: 'change' }],
  model: [{ required: true, message: '请输入或选择模型', trigger: 'blur' }],
}

const currentProviderInfo = computed(() => {
  return providerTypes.value.find(p => p.provider === form.provider)
})

const currentProviderHasModels = computed(() => {
  return currentProviderInfo.value?.has_predefined_models ?? false
})

const currentModels = computed(() => {
  return currentProviderInfo.value?.models || []
})

const currentDefaultApiBase = computed(() => {
  return currentProviderInfo.value?.default_api_base || ''
})

function getProviderDisplayName(provider: string): string {
  const info = providerTypes.value.find(p => p.provider === provider)
  return info?.display_name || provider
}

function formatTime(time: string): string {
  if (!time) return ''
  const date = new Date(time)
  return date.toLocaleString()
}

function onProviderChange() {
  const info = currentProviderInfo.value
  if (info?.models?.length) {
    form.model = info.models[0].id
  } else {
    form.model = ''
  }
  if (info?.default_api_base) {
    form.api_base = info.default_api_base
  }
}

function resetForm() {
  Object.assign(form, {
    name: '',
    provider: 'zhipu',
    model: 'glm-5',
    api_key: '',
    api_base: '',
    proxy: '',
    temperature: 0.7,
    max_tokens: 2048,
    top_p: 0.9,
    is_enabled: true,
  })
  formRef.value?.clearValidate()
}

function showAddDialog() {
  isEdit.value = false
  resetForm()
  // 设置默认 api_base
  const zhipuInfo = providerTypes.value.find(p => p.provider === 'zhipu')
  if (zhipuInfo?.default_api_base) {
    form.api_base = zhipuInfo.default_api_base
  }
  dialogVisible.value = true
}

function showEditDialog(config: LLMConfig) {
  isEdit.value = true
  editId.value = config.id
  Object.assign(form, {
    name: config.name,
    provider: config.provider,
    model: config.model,
    api_key: '',
    api_base: config.api_base || '',
    proxy: config.proxy || '',
    temperature: parseFloat(config.default_temperature || '0.7'),
    max_tokens: config.default_max_tokens || 2048,
    top_p: parseFloat(config.default_top_p || '0.9'),
    is_enabled: config.is_enabled,
  })
  dialogVisible.value = true
}

async function loadConfigs() {
  loading.value = true
  try {
    const res = await getLLMConfigs()
    configs.value = (res.data || []).map(c => ({ ...c, _updating: false, _testing: false }))
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '加载 LLM 配置列表失败')
  } finally {
    loading.value = false
  }
}

async function loadProviderTypes() {
  try {
    const res = await getProviderTypes()
    providerTypes.value = res.data?.providers || []
  } catch (error) {
    console.error('加载供应商类型失败:', error)
  }
}

async function submitForm() {
  const valid = await formRef.value?.validate()
  if (!valid) return

  submitting.value = true
  try {
    const data: any = {
      name: form.name,
      provider: form.provider,
      model: form.model,
      api_base: form.api_base || undefined,
      proxy: form.proxy || undefined,
      default_temperature: form.temperature.toString(),
      default_max_tokens: form.max_tokens,
      default_top_p: form.top_p.toString(),
      is_enabled: form.is_enabled,
    }

    if (form.api_key) {
      data.api_key = form.api_key
    }

    if (isEdit.value && editId.value) {
      if (!form.api_key) delete data.api_key
      await updateLLMConfig(editId.value, data)
      ElMessage.success('更新成功')
    } else {
      if (!form.api_key) {
        ElMessage.warning('请输入 API Key')
        submitting.value = false
        return
      }
      await createLLMConfig(data)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    await loadConfigs()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '操作失败')
  } finally {
    submitting.value = false
  }
}

async function toggleEnabled(config: ConfigRow) {
  config._updating = true
  try {
    await updateLLMConfig(config.id, { is_enabled: config.is_enabled })
    ElMessage.success('更新成功')
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '更新失败')
    config.is_enabled = !config.is_enabled
  } finally {
    config._updating = false
  }
}

async function handleTest(config: ConfigRow) {
  config._testing = true
  try {
    const res = await testLLMConfig(config.id)
    if (res.data.success) {
      ElMessage.success(`连接成功！延迟: ${res.data.latency_ms}ms`)
      await loadConfigs()
    } else {
      ElMessage.error(res.data.message || '连接失败')
    }
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '测试连接失败')
  } finally {
    config._testing = false
  }
}

async function handleDelete(id: number) {
  try {
    await ElMessageBox.confirm('确定删除这个 LLM 配置吗？', '确认删除', { type: 'warning' })
    await deleteLLMConfig(id)
    ElMessage.success('删除成功')
    await loadConfigs()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || '删除失败')
    }
  }
}

onMounted(async () => {
  await loadProviderTypes()
  await loadConfigs()
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
</style>
