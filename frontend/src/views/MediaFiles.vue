<template>
  <div class="page-container">
    <!-- 顶部工具栏 -->
    <div class="toolbar">
      <!-- 媒体类型切换 -->
      <el-radio-group v-model="libraryMediaType" size="default" @change="handleLibraryMediaTypeChange">
        <el-radio-button value="movie">电影</el-radio-button>
        <el-radio-button value="tv">剧集</el-radio-button>
        <el-radio-button value="anime">动画</el-radio-button>
        <el-radio-button value="music">音乐</el-radio-button>
        <el-radio-button value="book">电子书</el-radio-button>
      </el-radio-group>

      <!-- 问题筛选器 -->
      <ProblemFilter v-model="selectedIssues" :counts="issueCounts" />

      <!-- 操作按钮 -->
      <div class="toolbar-actions">
        <el-button type="primary" :icon="Search" @click="handleOpenLibraryScanDialog">扫描</el-button>
        <el-button :icon="Warning" @click="handleDetectIssues">检测问题</el-button>
      </div>
    </div>

    <!-- 双栏布局 -->
    <el-container class="main-content">
      <!-- 左侧目录树 -->
      <el-aside width="320px" class="tree-aside">
        <el-card shadow="never" class="tree-card">
          <template #header>
            <div class="card-header-simple">
              <el-icon><FolderOpened /></el-icon>
              <span>目录结构</span>
            </div>
          </template>

          <DirectoryTree
            ref="treeRef"
            :media-type="libraryMediaType"
            :issues="selectedIssues"
            @node-click="handleNodeClick"
          />
        </el-card>
      </el-aside>

      <!-- 右侧详情面板 -->
      <el-main class="detail-main">
        <DirectoryDetail ref="detailRef" :directory-id="currentDirectoryId" />
      </el-main>
    </el-container>

    <!-- 媒体库扫描对话框 -->
    <el-dialog v-model="libraryScanDialog.visible" title="扫描媒体库" width="500px">
      <el-form label-width="100px">
        <el-form-item label="媒体类型">
          <el-select v-model="libraryScanDialog.mediaType" clearable placeholder="全部">
            <el-option label="电影" value="movie" />
            <el-option label="剧集" value="tv" />
            <el-option label="动画" value="anime" />
            <el-option label="音乐" value="music" />
            <el-option label="电子书" value="book" />
          </el-select>
        </el-form-item>
        <el-form-item label="扫描模式">
          <el-radio-group v-model="libraryScanDialog.scanMode">
            <el-radio value="full">
              <span>全量扫描</span>
              <el-text size="small" type="info" style="margin-left: 8px">重建完整目录树</el-text>
            </el-radio>
            <el-radio value="incremental">
              <span>增量扫描</span>
              <el-text size="small" type="info" style="margin-left: 8px">仅同步变化，自动清理已删除</el-text>
            </el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="libraryScanDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="scanning" @click="confirmLibraryScan">
          开始扫描
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Search,
  FolderOpened,
  Warning
} from '@element-plus/icons-vue'
import DirectoryTree from '@/components/MediaLibrary/DirectoryTree.vue'
import DirectoryDetail from '@/components/MediaLibrary/DirectoryDetail.vue'
import ProblemFilter from '@/components/MediaLibrary/ProblemFilter.vue'
import { detectIssues } from '@/api/mediaDirectory'
import type { DirectoryTreeNode } from '@/api/mediaDirectory'
import { scanDirectory } from '@/api/modules/media'
// 组件引用
const treeRef = ref()
const detailRef = ref()
const scanning = ref(false)

// 状态
const libraryMediaType = ref<string>('movie')
const selectedIssues = ref<string[]>([])
const issueCounts = ref<Record<string, number>>({})
const currentDirectoryId = ref<number | null>(null)

const libraryScanDialog = reactive({
  visible: false,
  mediaType: '',
  scanMode: 'incremental'
})

onMounted(() => {
  document.title = '文件管理 (媒体库) - NasFusion'
  // 不再自动触发问题检测，用户可以通过"检测问题"按钮手动触发
})


// ========== library Tab 专用函数 ==========

/**
 * 处理节点点击
 */
const handleNodeClick = (node: DirectoryTreeNode) => {
  currentDirectoryId.value = node.id
}

/**
 * 刷新 library 视图
 */
const handleLibraryRefresh = () => {
  if (treeRef.value) {
    treeRef.value.refresh()
  }
  if (detailRef.value) {
    detailRef.value.refresh()
  }
  ElMessage.success('已刷新')
}

/**
 * 媒体类型切换
 */
const handleLibraryMediaTypeChange = () => {
  // 重置选中的目录
  currentDirectoryId.value = null
  // 重置问题筛选
  selectedIssues.value = []
  // 注意：不需要手动调用 refresh()，因为 DirectoryTree 组件内部已经 watch 了 mediaType
  // 不再自动重新检测问题，用户可以通过"检测问题"按钮手动触发
}

/**
 * 检测问题（静默执行，不显示提示）
 */
const detectIssuesSilently = async (skipRefresh = false) => {
  try {
    const res = await detectIssues({
      directory_id: null,
      media_type: libraryMediaType.value || null
    })
    if (res.data) {
      issueCounts.value = res.data.issues
      // 只在需要时刷新
      if (!skipRefresh) {
        handleLibraryRefresh()
      }
    }
  } catch (error) {
    console.error('检测问题失败:', error)
  }
}

/**
 * 检测问题（显示提示）
 */
const handleDetectIssues = async () => {
  try {
    // 传递当前选择的媒体类型
    const res = await detectIssues({
      directory_id: null,
      media_type: libraryMediaType.value || null
    })
    if (res.data) {
      issueCounts.value = res.data.issues
      ElMessage.success(`检测完成，发现 ${res.data.total_issues} 个问题`)
      handleLibraryRefresh()
    }
  } catch (error) {
    console.error('检测问题失败:', error)
    ElMessage.error('检测问题失败')
  }
}

// ========== 扫描相关函数 ==========

/**
 * 打开媒体库扫描对话框
 */
function handleOpenLibraryScanDialog() {
  libraryScanDialog.mediaType = libraryMediaType.value
  libraryScanDialog.scanMode = 'incremental'
  libraryScanDialog.visible = true
}

/**
 * 确认媒体库扫描
 */
async function confirmLibraryScan() {
  await startScanTask({
    mount_type: 'library',
    label: '媒体库',
    scanMode: libraryScanDialog.scanMode,
    mediaType: libraryScanDialog.mediaType || undefined
  })
  libraryScanDialog.visible = false
}

async function startScanTask(params: {
  directory?: string
  mount_type?: string
  label: string
  scanMode?: string
  mediaType?: string
}) {
  const { label, directory, mount_type, mediaType, scanMode } = params
  scanning.value = true
  try {
    // 创建扫描任务
    const res = await scanDirectory({
      directory: directory,
      mount_type: mount_type,
      recursive: true,
      media_type: mediaType,
      scan_mode: scanMode as any || 'incremental'
    })

    const executionId = res.data.execution_id

    ElMessage.success(`${label}扫描任务已创建，正在后台执行...`)

    // 轮询任务状态
    await pollTaskStatus(executionId, label)
  } catch (error: any) {
    ElMessage.error(error.message || `扫描${label}失败`)
    scanning.value = false
  }
}

async function pollTaskStatus(executionId: number, label: string) {
  const { getTaskExecution } = await import('@/api/modules/task')

  const poll = async () => {
    try {
      const taskRes = await getTaskExecution(executionId)
      const task = taskRes.data

      // 检查任务状态
      if (task.status === 'completed') {
        scanning.value = false
        const filesCreated = task.result?.files_created || 0
        ElMessage.success(`${label}扫描完成！创建了 ${filesCreated} 个媒体文件记录`)

        handleLibraryRefresh()
      } else if (task.status === 'failed') {
        scanning.value = false
        ElMessage.error(`${label}扫描失败: ${task.error_message || '未知错误'}`)
      } else if (task.status === 'running' || task.status === 'pending') {
        // 继续轮询
        setTimeout(poll, 2000) // 每2秒轮询一次
      } else {
        // 其他状态（cancelled, timeout）
        scanning.value = false
        ElMessage.warning(`${label}扫描${task.status === 'cancelled' ? '已取消' : '超时'}`)
      }
    } catch (error: any) {
      scanning.value = false
      ElMessage.error(`查询任务状态失败: ${error.message}`)
    }
  }

  // 开始轮询
  await poll()
}
</script>

<style scoped lang="scss">
.page-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: var(--el-bg-color-page);
}

// library Tab 样式
.toolbar {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
  background-color: var(--el-bg-color);
  border-bottom: 1px solid var(--el-border-color-light);

  .toolbar-actions {
    margin-left: auto;
    display: flex;
    gap: 8px;
  }
}

.main-content {
  flex: 1;
  overflow: hidden;
  padding: 16px;
  gap: 16px;

  .tree-aside {
    width: 320px;
    height: 100%;
    overflow: hidden;

    .tree-card {
      height: 100%;
      display: flex;
      flex-direction: column;

      .card-header-simple {
        display: flex;
        align-items: center;
        gap: 8px;
        font-weight: 500;
      }

      :deep(.el-card__body) {
        flex: 1;
        overflow: hidden;
        padding: 0;
      }
    }
  }

  .detail-main {
    flex: 1;
    overflow: hidden;
    padding: 0;
  }
}
</style>
