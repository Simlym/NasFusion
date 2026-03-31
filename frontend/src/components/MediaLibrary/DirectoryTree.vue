<template>
  <div class="directory-tree">
    <el-tree
      ref="treeRef"
      :data="treeData"
      :props="treeProps"
      :load="loadNode"
      :expand-on-click-node="false"
      lazy
      node-key="_treeKey"
      highlight-current
      @node-click="handleNodeClick"
      @node-contextmenu="handleContextMenu"
    >
      <template #default="{ node, data }">
        <!-- 剧集节点 -->
        <span v-if="data._node_type === 'episode'" class="tree-node episode-node">
          <span class="ep-badge">
            {{ data.episode_number != null ? `E${String(data.episode_number).padStart(2, '0')}` : 'EP' }}
          </span>
          <span class="node-label ep-label" :title="data.episode_title || data.file_name">
            {{ data.episode_title || data.file_name }}
          </span>
          <el-tooltip :content="data.has_nfo ? 'NFO ✓' : '缺少NFO'" placement="top">
            <el-icon :color="data.has_nfo ? '#67c23a' : '#f56c6c'" :size="12" style="flex-shrink:0">
              <CircleCheck v-if="data.has_nfo" />
              <CircleClose v-else />
            </el-icon>
          </el-tooltip>
          <el-tooltip :content="data.has_poster ? '图片 ✓' : '缺少图片'" placement="top">
            <el-icon :color="data.has_poster ? '#67c23a' : '#e6a23c'" :size="12" style="flex-shrink:0;margin-left:2px">
              <Picture v-if="data.has_poster" />
              <PictureFilled v-else />
            </el-icon>
          </el-tooltip>
        </span>

        <!-- 目录节点 -->
        <span v-else class="tree-node">
          <el-icon :size="16" style="margin-right: 4px">
            <FolderOpened v-if="node.expanded" />
            <Folder v-else />
          </el-icon>
          <span class="node-label">{{ getNodeDisplayName(data) }}</span>

          <!-- 季度标记 -->
          <el-tag v-if="data.season_number" size="small" type="info" style="margin-left: 6px">
            S{{ String(data.season_number).padStart(2, '0') }}
          </el-tag>

          <!-- 集数统计 -->
          <span v-if="data.episode_count > 0" class="episode-count">
            ({{ data.episode_count }}集)
          </span>

          <!-- 问题标记 -->
          <el-icon
            v-if="data.has_issues"
            :size="14"
            color="#f56c6c"
            style="margin-left: 6px"
            title="存在问题"
          >
            <Warning />
          </el-icon>
        </span>
      </template>
    </el-tree>

    <!-- 右键菜单 -->
    <el-dropdown
      ref="contextMenuRef"
      trigger="contextmenu"
      :teleported="false"
      @command="handleCommand"
    >
      <span></span>
      <template #dropdown>
        <el-dropdown-menu>
          <el-dropdown-item command="refresh" :icon="Refresh">
            刷新
          </el-dropdown-item>
          <el-dropdown-item command="scan" :icon="Search">
            重新扫描
          </el-dropdown-item>
          <el-dropdown-item command="detect" :icon="Warning" divided>
            检测问题
          </el-dropdown-item>
        </el-dropdown-menu>
      </template>
    </el-dropdown>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Folder, FolderOpened, Warning, Refresh, Search,
  CircleCheck, CircleClose, Picture, PictureFilled
} from '@element-plus/icons-vue'
import { getDirectoryTree, getDirectoryDetail, type DirectoryTreeNode } from '@/api/mediaDirectory'

// 视频文件扩展名集合
const VIDEO_EXTS = new Set(['mkv', 'mp4', 'avi', 'mov', 'wmv', 'ts', 'flv', 'm2ts', 'rmvb', 'iso', 'bdmv'])

export interface EpisodeTreeNode {
  _treeKey: string
  _node_type: 'episode'
  id: number
  file_name: string
  extension: string
  episode_number: number | null
  episode_title: string | null
  has_nfo: boolean
  has_poster: boolean
  has_subtitle: boolean
  resolution: string | null
  file_size: number
  parent_dir_id: number   // 所属季度目录ID，用于刮削后刷新
}

export type AnyTreeNode = (DirectoryTreeNode & { _treeKey: string; _node_type: 'directory' }) | EpisodeTreeNode

interface Props {
  mediaType?: string | null
  issues?: string[]
}

interface Emits {
  (e: 'node-click', node: AnyTreeNode): void
}

const props = withDefaults(defineProps<Props>(), {
  mediaType: null,
  issues: () => []
})

const emit = defineEmits<Emits>()

const treeRef = ref()
const contextMenuRef = ref()
const treeData = ref<any[]>([])
const currentNode = ref<AnyTreeNode | null>(null)

const treeProps = {
  label: 'directory_name',
  children: 'children',
  isLeaf: (data: any) => {
    // 剧集节点始终是叶子
    if (data._node_type === 'episode') return true
    // 根目录不是叶子
    if (data.parent_id === null) return false
    // 季度目录有剧集子节点（不是叶子）
    if (data.season_number != null) return false
    // 其他目录根据子目录数判断
    if (data.subdir_count !== undefined && data.subdir_count === 0) return true
    return false
  }
}

/** 给目录节点添加 _treeKey 和 _node_type */
function transformDirNodes(dirs: DirectoryTreeNode[]): any[] {
  return dirs.map(d => ({
    ...d,
    _treeKey: `d_${d.id}`,
    _node_type: 'directory'
  }))
}

const getNodeDisplayName = (data: any): string => data.directory_name

/** 懒加载节点 */
const loadNode = async (node: any, resolve: any) => {
  if (node.level === 0) {
    await loadRootNodes(resolve)
  } else if (node.data._node_type === 'episode') {
    resolve([])
  } else if (node.data.season_number != null) {
    await loadEpisodeNodes(node.data.id, resolve)
  } else {
    await loadChildren(node.data.id, resolve)
  }
}

/** 加载根节点 */
const loadRootNodes = async (resolve: any) => {
  try {
    const res = await getDirectoryTree({
      media_type: props.mediaType || undefined,
      parent_id: null,
      issues: props.issues?.length ? props.issues : undefined
    })
    const nodes = transformDirNodes(res.data || [])
    treeData.value = nodes
    resolve(nodes)
  } catch (error) {
    console.error('加载目录树失败:', error)
    ElMessage.error('加载目录树失败')
    resolve([])
  }
}

/** 加载子目录节点 */
const loadChildren = async (parentId: number, resolve: any) => {
  try {
    const res = await getDirectoryTree({
      media_type: props.mediaType || undefined,
      parent_id: parentId
    })
    resolve(transformDirNodes(res.data || []))
  } catch (error) {
    console.error('加载子节点失败:', error)
    resolve([])
  }
}

/** 加载季度下的剧集文件节点 */
const loadEpisodeNodes = async (directoryId: number, resolve: any) => {
  try {
    const res = await getDirectoryDetail(directoryId)
    const files = res.data?.files || []
    const episodes: EpisodeTreeNode[] = files
      .filter((f: any) => VIDEO_EXTS.has((f.extension || '').toLowerCase()))
      .sort((a: any, b: any) => (a.episode_number ?? 9999) - (b.episode_number ?? 9999))
      .map((f: any): EpisodeTreeNode => ({
        _treeKey: `e_${f.id}`,
        _node_type: 'episode',
        id: f.id,
        file_name: f.file_name,
        extension: f.extension || '',
        episode_number: f.episode_number ?? null,
        episode_title: f.episode_title ?? null,
        has_nfo: f.has_nfo ?? false,
        has_poster: f.has_poster ?? false,
        has_subtitle: f.has_subtitle ?? false,
        resolution: f.resolution ?? null,
        file_size: f.file_size ?? 0,
        parent_dir_id: directoryId,
      }))
    resolve(episodes)
  } catch (error) {
    console.error('加载剧集节点失败:', error)
    resolve([])
  }
}

/** 节点点击 */
const handleNodeClick = (data: AnyTreeNode) => {
  currentNode.value = data
  emit('node-click', data)
}

/** 右键菜单 */
const handleContextMenu = (event: MouseEvent, data: AnyTreeNode) => {
  event.preventDefault()
  currentNode.value = data
}

/** 菜单命令 */
const handleCommand = async (command: string) => {
  if (!currentNode.value) return
  switch (command) {
    case 'refresh':
      refreshCurrentNode()
      break
    case 'scan':
      ElMessage.info('扫描功能待实现')
      break
    case 'detect':
      ElMessage.info('问题检测功能待实现')
      break
  }
}

/** 刷新当前节点 */
const refreshCurrentNode = () => {
  if (!treeRef.value || !currentNode.value) return
  const node = treeRef.value.getNode(currentNode.value._treeKey)
  if (node) {
    node.loaded = false
    node.expand()
  }
}

/** 刷新整棵树 */
const refreshTree = () => {
  if (!treeRef.value) return
  treeData.value = []
  const root = treeRef.value.root
  if (root) {
    root.childNodes = []
    root.loaded = false
    root.loadData()
  }
}

/**
 * 刷新指定 treeKey 的节点子列表（供外部调用）
 * 剧集刮削后传入 `d_${parent_dir_id}` 来重新加载季度下的剧集节点。
 */
const refreshNodeByKey = (treeKey: string) => {
  if (!treeRef.value) return
  const node = treeRef.value.getNode(treeKey)
  if (node) {
    node.loaded = false
    if (node.expanded) {
      // 已展开：强制重新加载子节点
      node.loadData()
    }
  }
}

watch(() => props.mediaType, refreshTree)

watch(
  () => props.issues,
  refreshTree,
  { deep: true }
)

defineExpose({ refresh: refreshTree, refreshCurrentNode, refreshNodeByKey })
</script>

<style scoped lang="scss">
.directory-tree {
  height: 100%;
  overflow-y: auto;

  .tree-node {
    display: flex;
    align-items: center;
    flex: 1;
    min-width: 0;
    padding-right: 8px;

    .node-label {
      flex: 1;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      min-width: 0;
    }

    .episode-count {
      margin-left: 6px;
      font-size: 12px;
      color: var(--el-text-color-secondary);
      flex-shrink: 0;
    }
  }
}

/* 剧集节点样式 */
.episode-node {
  gap: 4px;

  .ep-badge {
    flex-shrink: 0;
    font-family: monospace;
    font-weight: 700;
    font-size: 11px;
    color: var(--el-color-primary);
    background: var(--el-color-primary-light-9);
    border-radius: 3px;
    padding: 0 4px;
    line-height: 18px;
    min-width: 30px;
    text-align: center;
  }

  .ep-label {
    font-size: 12px;
    color: var(--el-text-color-regular);
  }
}

:deep(.el-tree-node__content) {
  height: 32px;
}

/* 剧集节点行高略小，看起来更紧凑 */
:deep(.el-tree-node__content:has(.episode-node)) {
  height: 28px;
}
</style>
