<template>
  <el-table :data="mounts" stripe style="width: 100%">
    <el-table-column label="名称" prop="name" width="140" />

    <el-table-column label="容器路径" prop="container_path" min-width="200" show-overflow-tooltip />

    <el-table-column label="宿主机路径" min-width="200" show-overflow-tooltip>
      <template #default="{ row }">
        <div class="host-path-cell">
          <span v-if="row.host_path" class="path-text">{{ row.host_path }}</span>
          <span v-else class="no-path">未配置</span>
        </div>
      </template>
    </el-table-column>

    <el-table-column label="类型" width="90">
      <template #default="{ row }">
        <el-tag :type="row.mount_type === 'download' ? 'primary' : 'success'" size="small" effect="plain">
          {{ row.mount_type === 'download' ? '下载' : '媒体库' }}
        </el-tag>
      </template>
    </el-table-column>

    <el-table-column label="媒体分类" width="120">
      <template #default="{ row }">
        <el-select
          v-if="row.mount_type === 'library'"
          v-model="row.media_category"
          placeholder="分类"
          size="small"
          clearable
          @change="handleCategoryChange(row)"
        >
          <el-option
            v-for="cat in categoryOptions"
            :key="cat.value"
            :label="cat.label"
            :value="cat.value"
          />
        </el-select>
        <span v-else class="no-value">-</span>
      </template>
    </el-table-column>

    <el-table-column label="优先级" width="110">
      <template #default="{ row }">
        <el-input-number
          v-if="row.mount_type === 'library'"
          v-model="row.priority"
          :min="0"
          :max="1000"
          size="small"
          controls-position="right"
          style="width: 80px"
          @change="handlePriorityChange(row)"
        />
        <span v-else class="no-value">-</span>
      </template>
    </el-table-column>

    <el-table-column label="默认" width="60" align="center">
      <template #default="{ row }">
        <el-switch
          v-if="row.mount_type === 'library' && row.media_category"
          v-model="row.is_default"
          size="small"
          @change="handleDefaultChange(row)"
        />
        <span v-else class="no-value">-</span>
      </template>
    </el-table-column>

    <el-table-column label="状态" width="80" align="center">
      <template #default="{ row }">
        <el-tag :type="row.is_accessible ? 'success' : 'danger'" size="small">
          {{ row.is_accessible ? '正常' : '异常' }}
        </el-tag>
      </template>
    </el-table-column>

    <el-table-column label="启用" width="70" align="center">
      <template #default="{ row }">
        <el-switch
          v-model="row.is_enabled"
          size="small"
          @change="handleEnableChange(row)"
        />
      </template>
    </el-table-column>

    <el-table-column label="操作" width="140" fixed="right">
      <template #default="{ row }">
        <el-button type="primary" link size="small" @click="handleRefresh(row.id)">
          刷新
        </el-button>
        <el-button type="primary" link size="small" @click="handleEdit(row)">
          编辑
        </el-button>
        <el-button type="danger" link size="small" @click="handleDelete(row)">
          删除
        </el-button>
      </template>
    </el-table-column>
  </el-table>
</template>

<script setup lang="ts">
import { type StorageMount, type StorageMountUpdate } from '@/api/modules/storage'

interface Props {
  mounts: StorageMount[]
}

defineProps<Props>()

const emit = defineEmits<{
  (e: 'update', mountId: number, data: StorageMountUpdate): void
  (e: 'refresh', mountId: number): void
  (e: 'edit', mount: StorageMount): void
  (e: 'delete', mountId: number): void
}>()

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

function handleCategoryChange(row: StorageMount) {
  emit('update', row.id, { media_category: row.media_category })
}

function handlePriorityChange(row: StorageMount) {
  emit('update', row.id, { priority: row.priority })
}

function handleDefaultChange(row: StorageMount) {
  emit('update', row.id, { is_default: row.is_default })
}

function handleEnableChange(row: StorageMount) {
  emit('update', row.id, { is_enabled: row.is_enabled })
}

function handleRefresh(mountId: number) {
  emit('refresh', mountId)
}

function handleEdit(mount: StorageMount) {
  emit('edit', mount)
}

function handleDelete(mount: StorageMount) {
  emit('delete', mount.id)
}
</script>

<style scoped>
.mount-name {
  display: flex;
  align-items: center;
  gap: 6px;
}

.same-disk-tag {
  font-size: 10px;
}

.host-path-cell {
  display: flex;
  align-items: center;
}

.path-text {
  color: var(--el-text-color-regular);
}

.no-path {
  color: var(--el-text-color-placeholder);
  font-style: italic;
}

.no-value {
  color: var(--el-text-color-placeholder);
}

</style>
