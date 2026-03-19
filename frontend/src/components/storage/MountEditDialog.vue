<template>
  <el-dialog
    v-model="visible"
    :title="isEdit ? '编辑挂载点' : '添加挂载点'"
    width="600px"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <el-form
      ref="formRef"
      :model="formData"
      :rules="rules"
      label-width="120px"
      @submit.prevent="handleSubmit"
    >
      <el-form-item label="挂载点名称" prop="name">
        <el-input
          v-model="formData.name"
          placeholder="如: 电影下载目录、电影媒体库"
        />
      </el-form-item>

      <el-form-item label="挂载点类型" prop="mount_type">
        <el-radio-group v-model="formData.mount_type" :disabled="isEdit">
          <el-radio value="download">下载目录</el-radio>
          <el-radio value="library">媒体库目录</el-radio>
        </el-radio-group>
      </el-form-item>

      <el-form-item label="容器路径" prop="container_path">
        <DirectoryBrowser v-model="formData.container_path" />
        <div class="form-tips">容器内的路径，如 /app/data/downloads/movies</div>
      </el-form-item>

      <el-form-item label="宿主机路径" prop="host_path">
        <el-input
          v-model="formData.host_path"
          placeholder="宿主机上的实际路径，可选"
          clearable
        />
        <div class="form-tips">仅用于显示和参考，不会影响实际挂载</div>
      </el-form-item>

      <el-form-item
        v-if="formData.mount_type === 'library'"
        label="媒体分类"
        prop="media_category"
      >
        <el-select
          v-model="formData.media_category"
          placeholder="选择媒体分类"
          clearable
        >
          <el-option
            v-for="cat in categoryOptions"
            :key="cat.value"
            :label="cat.label"
            :value="cat.value"
          />
        </el-select>
      </el-form-item>

      <el-form-item
        v-if="formData.mount_type === 'library'"
        label="设为默认"
      >
        <el-switch v-model="formData.is_default" />
        <div class="form-tips">同一分类的默认挂载点，整理时优先使用</div>
      </el-form-item>

      <el-form-item label="优先级">
        <el-input-number
          v-model="formData.priority"
          :min="0"
          :max="1000"
          controls-position="right"
        />
        <div class="form-tips">数值越大优先级越高，0-1000</div>
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="handleClose">取消</el-button>
      <el-button type="primary" :loading="saving" @click="handleSubmit">
        {{ isEdit ? '保存' : '创建' }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, watch, computed } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import DirectoryBrowser from './DirectoryBrowser.vue'
import {
  createStorageMount,
  updateStorageMount,
  type StorageMount,
  type StorageMountCreate
} from '@/api/modules/storage'

interface Props {
  modelValue: boolean
  mount?: StorageMount | null
}

const props = withDefaults(defineProps<Props>(), {
  mount: null
})

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'success'): void
}>()

const formRef = ref<FormInstance>()
const saving = ref(false)

const isEdit = computed(() => !!props.mount)

const formData = reactive<StorageMountCreate>({
  name: '',
  mount_type: 'download',
  container_path: '',
  host_path: '',
  media_category: undefined,
  is_default: false,
  priority: 0
})

const categoryOptions = [
  { label: '电影', value: 'movie' },
  { label: '电视剧', value: 'tv' },
  { label: '音乐', value: 'music' },
  { label: '书籍', value: 'book' },
  { label: '动漫', value: 'anime' },
  { label: '成人', value: 'adult' },
  { label: '游戏', value: 'game' },
  { label: '其他', value: 'other' }
]

const rules: FormRules = {
  name: [
    { required: true, message: '请输入挂载点名称', trigger: 'blur' },
    { min: 2, max: 50, message: '名称长度在 2 到 50 个字符', trigger: 'blur' }
  ],
  mount_type: [
    { required: true, message: '请选择挂载点类型', trigger: 'change' }
  ],
  container_path: [
    { required: true, message: '请选择或输入容器路径', trigger: 'blur' }
  ]
}

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

// 监听 mount 变化，初始化表单
watch(() => props.mount, (mount) => {
  if (mount) {
    Object.assign(formData, {
      name: mount.name,
      mount_type: mount.mount_type,
      container_path: mount.container_path,
      host_path: mount.host_path || '',
      media_category: mount.media_category,
      is_default: mount.is_default,
      priority: mount.priority
    })
  } else {
    resetForm()
  }
}, { immediate: true })

function resetForm() {
  Object.assign(formData, {
    name: '',
    mount_type: 'download',
    container_path: '',
    host_path: '',
    media_category: undefined,
    is_default: false,
    priority: 0
  })
  formRef.value?.clearValidate()
}

async function handleSubmit() {
  if (!formRef.value) return

  try {
    await formRef.value.validate()
  } catch {
    return
  }

  saving.value = true
  try {
    if (isEdit.value && props.mount) {
      // 编辑模式：调用更新接口
      await updateStorageMount(props.mount.id, {
        name: formData.name,
        container_path: formData.container_path,
        host_path: formData.host_path || undefined,
        media_category: formData.media_category,
        priority: formData.priority,
        is_default: formData.is_default
      })
      ElMessage.success('更新成功')
    } else {
      // 创建模式
      await createStorageMount({
        name: formData.name,
        mount_type: formData.mount_type,
        container_path: formData.container_path,
        host_path: formData.host_path || undefined,
        media_category: formData.media_category,
        is_default: formData.is_default || false,
        priority: formData.priority
      })
      ElMessage.success('创建成功')
    }

    emit('success')
    handleClose()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '操作失败')
  } finally {
    saving.value = false
  }
}

function handleClose() {
  resetForm()
  visible.value = false
}
</script>

<style scoped>
.form-tips {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 4px;
  line-height: 1.5;
}

:deep(.el-input-number) {
  width: 200px;
}
</style>
