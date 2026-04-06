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
        <el-button class="mobile-tree-btn" :icon="FolderOpened" @click="mobileTreeVisible = true">目录</el-button>
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
        <EpisodeDetail
          v-if="currentEpisode"
          :episode="currentEpisode"
          @scrape-done="handleEpisodeScrapeDone"
        />
        <DirectoryDetail
          v-else
          ref="detailRef"
          :directory-id="currentDirectoryId"
        />
      </el-main>
    </el-container>

    <!-- 移动端：目录树抽屉 -->
    <el-drawer
      v-model="mobileTreeVisible"
      direction="ltr"
      size="85%"
      title="目录结构"
      class="mobile-tree-drawer"
    >
      <DirectoryTree
        ref="mobileTreeRef"
        :media-type="libraryMediaType"
        :issues="selectedIssues"
        @node-click="handleMobileNodeClick"
      />
    </el-drawer>

    <!-- 媒体库扫描对话框 -->
    <el-dialog v-model="libraryScanDialog.visible" title="扫描媒体库" width="500px" class="scan-dialog">
      <el-form label-width="100px">
        <el-form-item label="扫描范围">
          <div v-if="libraryScanDialog.directory" class="scan-directory-info">
            <el-tag type="primary" closable @close="clearScanDirectory" class="scan-directory-tag">
              <el-icon style="margin-right: 4px"><FolderOpened /></el-icon>
              <span class="scan-directory-name">{{ libraryScanDialog.directoryName }}</span>
            </el-tag>
            <el-text size="small" type="info">仅扫描选中目录</el-text>
          </div>
          <el-text v-else type="info">全部媒体库目录</el-text>
        </el-form-item>
        <el-form-item label="媒体类型">
          <el-select v-model="libraryScanDialog.mediaType" clearable placeholder="全部">
            <el-option label="电影" value="movie" />
            <el-option label="剧集" value="tv" />
            <el-option label="动画" value="anime" />
            <el-option label="音乐" value="music" />
            <el-option label="电子书" value="book" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="!libraryScanDialog.directory" label="扫描模式">
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
import EpisodeDetail from '@/components/MediaLibrary/EpisodeDetail.vue'
import ProblemFilter from '@/components/MediaLibrary/ProblemFilter.vue'
import { detectIssues } from '@/api/mediaDirectory'
import type { AnyTreeNode, EpisodeTreeNode } from '@/components/MediaLibrary/DirectoryTree.vue'
import { scanDirectory } from '@/api/modules/media'
// 组件引用
const treeRef = ref()
const mobileTreeRef = ref()
const detailRef = ref()
const scanning = ref(false)
const mobileTreeVisible = ref(false)

// 状态
const libraryMediaType = ref<string>('movie')
const selectedIssues = ref<string[]>([])
const issueCounts = ref<Record<string, number>>({})
const currentDirectoryId = ref<number | null>(null)
const currentNodeData = ref<{ directory_path: string; directory_name: string } | null>(null)
const currentEpisode = ref<EpisodeTreeNode | null>(null)

const libraryScanDialog = reactive({
  visible: false,
  mediaType: '',
  scanMode: 'incremental',
  directory: '' as string,       // 选中目录的物理路径
  directoryName: '' as string    // 选中目录的显示名称
})

onMounted(() => {
  document.title = '文件管理 (媒体库) - NasFusion'
  // 不再自动触发问题检测，用户可以通过"检测问题"按钮手动触发
})


// ========== library Tab 专用函数 ==========

/**
 * 处理节点点击（目录或剧集文件）
 */
const handleNodeClick = (node: AnyTreeNode) => {
  if (node._node_type === 'episode') {
    currentDirectoryId.value = null
    currentNodeData.value = null
    currentEpisode.value = node as EpisodeTreeNode
  } else {
    currentEpisode.value = null
    currentDirectoryId.value = node.id
    currentNodeData.value = {
      directory_path: (node as any).directory_path,
      directory_name: (node as any).directory_name
    }
  }
}

/**
 * 移动端节点点击（关闭抽屉后跳转）
 */
const handleMobileNodeClick = (node: AnyTreeNode) => {
  handleNodeClick(node)
  mobileTreeVisible.value = false
}

/**
 * 剧集刮削完成后，刷新父季度节点的子列表，更新树中的NFO/图片状态图标
 */
const handleEpisodeScrapeDone = () => {
  if (currentEpisode.value && treeRef.value) {
    treeRef.value.refreshNodeByKey(`d_${currentEpisode.value.parent_dir_id}`)
  }
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
  currentNodeData.value = null
  currentEpisode.value = null
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
  // 如果当前选中了目录，默认扫描该目录（全量）
  if (currentDirectoryId.value && currentNodeData.value) {
    libraryScanDialog.directory = currentNodeData.value.directory_path
    libraryScanDialog.directoryName = currentNodeData.value.directory_name
    libraryScanDialog.scanMode = 'full'
  } else {
    libraryScanDialog.directory = ''
    libraryScanDialog.directoryName = ''
    libraryScanDialog.scanMode = 'incremental'
  }
  libraryScanDialog.visible = true
}

/**
 * 清除扫描对话框中的目录选择
 */
function clearScanDirectory() {
  libraryScanDialog.directory = ''
  libraryScanDialog.directoryName = ''
  libraryScanDialog.scanMode = 'incremental'
}

/**
 * 确认媒体库扫描
 */
async function confirmLibraryScan() {
  if (libraryScanDialog.directory) {
    // 单目录扫描，固定全量模式
    await startScanTask({
      directory: libraryScanDialog.directory,
      label: libraryScanDialog.directoryName,
      scanMode: 'full',
      mediaType: libraryScanDialog.mediaType || undefined
    })
  } else {
    await startScanTask({
      mount_type: 'library',
      label: '媒体库',
      scanMode: libraryScanDialog.scanMode,
      mediaType: libraryScanDialog.mediaType || undefined
    })
  }
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

// 移动端目录按钮，桌面端隐藏
.mobile-tree-btn {
  display: none;
}

@media (max-width: 768px) {
  .toolbar {
    flex-wrap: wrap;
    gap: 10px;
    padding: 12px;

    // 媒体类型切换缩小
    :deep(.el-radio-group) {
      .el-radio-button__inner {
        padding: 6px 10px;
        font-size: 13px;
      }
    }

    .toolbar-actions {
      width: 100%;
      justify-content: flex-end;
    }
  }

  .mobile-tree-btn {
    display: inline-flex;
  }

  .main-content {
    padding: 10px;

    .tree-aside {
      display: none;
    }

    .detail-main {
      width: 100%;
    }
  }
}

.scan-directory-info {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  width: 100%;

  .scan-directory-tag {
    max-width: 280px;
    display: inline-flex;
    align-items: center;

    .scan-directory-name {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  .el-text {
    flex-shrink: 0;
    line-height: 24px;
  }
}

// 移动端抽屉内树组件样式
.mobile-tree-drawer {
  :deep(.el-drawer__body) {
    padding: 0;
    overflow-y: auto;
  }
}
</style>

<style lang="scss">
@media (max-width: 768px) {
  .scan-dialog {
    --el-dialog-width: 92% !important;
    width: 92% !important;
  }
}
</style>
