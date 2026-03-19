<template>
  <div class="directory-tree">
    <el-tree
      ref="treeRef"
      :data="treeData"
      :props="treeProps"
      :load="loadNode"
      :expand-on-click-node="false"
      lazy
      node-key="id"
      highlight-current
      @node-click="handleNodeClick"
      @node-contextmenu="handleContextMenu"
    >
      <template #default="{ node, data }">
        <span class="tree-node">
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
import { Folder, FolderOpened, Warning, Refresh, Search } from '@element-plus/icons-vue'
import { getDirectoryTree, type DirectoryTreeNode } from '@/api/mediaDirectory'

interface Props {
  mediaType?: string | null
  issues?: string[]
}

interface Emits {
  (e: 'node-click', node: DirectoryTreeNode): void
}

const props = withDefaults(defineProps<Props>(), {
  mediaType: null,
  issues: () => []
})

const emit = defineEmits<Emits>()

const treeRef = ref()
const contextMenuRef = ref()
const treeData = ref<DirectoryTreeNode[]>([])
const currentNode = ref<DirectoryTreeNode | null>(null)

const treeProps = {
  label: 'directory_name',
  children: 'children',
  // 判断叶子节点：
  // 1. 季度目录（有 season_number）是叶子节点
  // 2. 剧集/动画的父目录（有 series_name 但无 season_number）不是叶子节点
  // 3. 其他类型（电影、音乐等）默认为叶子节点
  isLeaf: (data: DirectoryTreeNode) => {
    // 根目录绝不是叶子节点
    if (data.parent_id === null) return false

    // 如果后端明确返回了子目录数量，且为0，则是叶子节点
    if (data.subdir_count !== undefined && data.subdir_count === 0) {
      return true
    }

    // 季度目录通常是叶子节点（内容是文件）
    if (data.season_number !== null) return true

    // 默认不作为叶子节点
    return false
  }
}

/**
 * 获取节点显示名称
 * - 直接使用目录名
 */
const getNodeDisplayName = (data: DirectoryTreeNode): string => {
  return data.directory_name
}

/**
 * 懒加载子节点
 */
const loadNode = async (node: any, resolve: any) => {
  if (node.level === 0) {
    // 加载根节点
    await loadRootNodes(resolve)
  } else {
    // 加载子节点
    await loadChildren(node.data.id, resolve)
  }
}

/**
 * 加载根节点
 */
const loadRootNodes = async (resolve: any) => {
  try {
    const res = await getDirectoryTree({
      media_type: props.mediaType || undefined,
      parent_id: null,
      issues: props.issues && props.issues.length > 0 ? props.issues : undefined
    })

    if (res.data) {
      treeData.value = res.data
      resolve(res.data)
    } else {
      resolve([])
    }
  } catch (error) {
    console.error('加载目录树失败:', error)
    ElMessage.error('加载目录树失败')
    resolve([])
  }
}

/**
 * 加载子节点
 */
const loadChildren = async (parentId: number, resolve: any) => {
  try {
    const res = await getDirectoryTree({
      media_type: props.mediaType || undefined,
      parent_id: parentId
    })

    if (res.data) {
      resolve(res.data)
    } else {
      resolve([])
    }
  } catch (error) {
    console.error('加载子节点失败:', error)
    resolve([])
  }
}

/**
 * 节点点击
 */
const handleNodeClick = (data: DirectoryTreeNode) => {
  currentNode.value = data
  emit('node-click', data)
}

/**
 * 右键菜单
 */
const handleContextMenu = (event: MouseEvent, data: DirectoryTreeNode, node: any) => {
  event.preventDefault()
  currentNode.value = data
  // 显示右键菜单逻辑可以进一步完善
}

/**
 * 菜单命令
 */
const handleCommand = async (command: string) => {
  if (!currentNode.value) return

  switch (command) {
    case 'refresh':
      refreshNode()
      break
    case 'scan':
      // TODO: 触发重新扫描
      ElMessage.info('扫描功能待实现')
      break
    case 'detect':
      // TODO: 触发问题检测
      ElMessage.info('问题检测功能待实现')
      break
  }
}

/**
 * 刷新当前节点
 */
const refreshNode = () => {
  if (treeRef.value) {
    // 重新加载当前节点
    const node = treeRef.value.getNode(currentNode.value?.id)
    if (node) {
      node.loaded = false
      node.expand()
    }
  }
}

/**
 * 刷新整棵树（重新加载根节点）
 */
const refreshTree = () => {
  if (treeRef.value) {
    // 清空数据
    treeData.value = []
    // 获取根节点并标记为未加载
    const root = treeRef.value.root
    if (root) {
      root.childNodes = []
      root.loaded = false
      // 让 el-tree 的 lazy 机制自动触发加载，不再手动调用 loadRootNodes
      // 这样可以避免重复请求
      root.loadData()
    }
  }
}

/**
 * 监听媒体类型变化
 */
watch(
  () => props.mediaType,
  () => {
    // 媒体类型变化时，重新加载整棵树
    refreshTree()
  }
)

/**
 * 监听问题筛选变化
 */
watch(
  () => props.issues,
  (newVal) => {
    // 问题筛选变化时，重新加载整棵树
    refreshTree()
  },
  { deep: true }
)

/**
 * 暴露方法
 */
defineExpose({
  refresh: refreshTree,
  refreshNode
})
</script>

<style scoped lang="scss">
.directory-tree {
  height: 100%;
  overflow-y: auto;

  .tree-node {
    display: flex;
    align-items: center;
    flex: 1;
    padding-right: 8px;

    .node-label {
      flex: 1;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .episode-count {
      margin-left: 6px;
      font-size: 12px;
      color: var(--el-text-color-secondary);
    }
  }
}

:deep(.el-tree-node__content) {
  height: 32px;
}
</style>
