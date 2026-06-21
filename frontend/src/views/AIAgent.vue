<template>
  <div class="ai-agent-container" :class="{ 'sidebar-open': sidebarVisible }">
    <!-- 移动端侧边栏遮罩 -->
    <div class="sidebar-overlay" @click="sidebarVisible = false"></div>
    
    <!-- 侧边栏：对话列表 -->
    <div class="sidebar">
      <div class="sidebar-header">
        <el-button class="new-chat-btn" type="primary" @click="handleNewConversation" :icon="Plus">
          新对话
        </el-button>
        <el-button :icon="Tools" @click="openToolsDrawer" title="工具与调用日志" />
        <el-button :icon="Setting" @click="showConfigDialog = true" title="设置" />
      </div>

      <div class="conversation-list">
        <div
          v-for="conv in conversations"
          :key="conv.id"
          class="conversation-item"
          :class="{ active: currentConversationId === conv.id }"
          @click="handleSelectConversation(conv.id)"
        >
          <el-icon class="conv-icon"><ChatLineRound /></el-icon>
          <div class="conv-info">
            <div class="conv-title">{{ conv.title || '新对话' }}</div>
            <div class="conv-time">{{ formatTime(conv.updated_at) }}</div>
          </div>
          <el-button
            class="conv-delete"
            :icon="Delete"
            link
            @click.stop="deleteConversation(conv.id)"
          />
        </div>

        <div v-if="conversations.length === 0" class="empty-tip">
          暂无对话，点击上方按钮开始
        </div>
      </div>
    </div>

    <!-- 主内容：聊天区域 -->
    <div class="main-content">
      <!-- 移动端顶部栏 -->
      <div class="mobile-header">
        <el-button class="menu-btn" :icon="Menu" @click="sidebarVisible = true" />
        <span class="mobile-title">AI 助手</span>
        <el-button :icon="Tools" @click="openToolsDrawer" />
        <el-button :icon="Setting" @click="showConfigDialog = true" />
      </div>

      <!-- 未配置提示 -->
      <div v-if="!config?.is_enabled" class="config-tip">
        <el-empty description="AI Agent 未配置">
          <el-button type="primary" @click="showConfigDialog = true">
            立即配置
          </el-button>
        </el-empty>
      </div>

      <!-- 聊天界面 -->
      <template v-else>
        <!-- 消息列表 -->
        <div class="message-list" ref="messageListRef">
          <div
            v-for="msg in visibleMessages"
            :key="msg.id"
            class="message-item"
            :class="msg.role"
          >
            <div class="message-avatar">
              <el-avatar v-if="msg.role === 'user'" :icon="User" />
              <el-avatar v-else class="ai-avatar"><AppIcon name="lucide:bot" :size="18" /></el-avatar>
            </div>
            <div class="message-content">
              <div class="message-text" v-html="renderMarkdown(msg.content || '')"></div>
              <div v-if="msg.tool_calls" class="message-tools">
                <el-tag
                  v-for="(tc, idx) in msg.tool_calls"
                  :key="idx"
                  type="info"
                  size="small"
                >
                  {{ getToolDisplayName(tc.name) }}
                </el-tag>
              </div>
            </div>
          </div>

          <!-- 流式输出 -->
          <div v-if="isStreaming" class="message-item assistant">
            <div class="message-avatar">
              <el-avatar class="ai-avatar"><AppIcon name="lucide:bot" :size="18" /></el-avatar>
            </div>
            <div class="message-content">
              <div v-if="streamingContent" class="message-text" v-html="renderMarkdown(streamingContent)"></div>
              <!-- 工具调用状态 -->
              <div v-if="streamingToolCalls.length" class="message-tools streaming-tools">
                <el-tag
                  v-for="(tc, idx) in streamingToolCalls"
                  :key="idx"
                  :type="tc.status === 'running' ? 'warning' : tc.status === 'done' ? 'success' : 'info'"
                  size="small"
                >
                  <el-icon v-if="tc.status === 'running'" class="is-loading"><Loading /></el-icon>
                  {{ getToolDisplayName(tc.name) }}
                </el-tag>
              </div>
              <div v-if="!streamingContent && !streamingToolCalls.length" class="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>

          <!-- 加载中（非流式） -->
          <div v-else-if="loading && !isStreaming" class="message-item assistant">
            <div class="message-avatar">
              <el-avatar class="ai-avatar"><AppIcon name="lucide:bot" :size="18" /></el-avatar>
            </div>
            <div class="message-content">
              <div class="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        </div>

        <!-- 输入框 -->
        <div class="input-area">
          <div class="input-wrapper">
            <el-input
              v-model="inputMessage"
              type="textarea"
              :autosize="{ minRows: 1, maxRows: 5 }"
              placeholder="输入消息，Enter 发送，Shift+Enter 换行"
              @keydown.enter.exact.prevent="sendMessage"
              :disabled="loading"
            />
            <el-button
              class="send-btn"
              circle
              :icon="Promotion"
              :loading="loading"
              @click="sendMessage"
              :disabled="!inputMessage.trim()"
            />
          </div>
        </div>
      </template>
    </div>

    <!-- 配置对话框 -->
    <el-dialog
      v-model="showConfigDialog"
      title="AI Agent 配置"
      width="min(600px, 95vw)"
    >
      <el-form :model="configForm" label-width="120px">
        <el-form-item label="LLM 配置">
          <el-select
            v-model="configForm.llm_config_id"
            placeholder="选择已配置的 LLM"
            clearable
            style="width: 100%"
          >
            <el-option
              v-for="opt in llmOptions"
              :key="opt.id"
              :label="`${opt.name} (${opt.model})`"
              :value="opt.id"
            />
          </el-select>
          <div v-if="llmOptions.length === 0" class="form-tip" style="margin-top: 8px;">
            暂无可用的 LLM 配置，请前往
            <router-link to="/settings?tab=llm" style="color: var(--el-color-primary);">系统设置 &gt; LLM 配置</router-link>
            添加供应商
          </div>
        </el-form-item>

        <el-form-item label="启用">
          <el-switch v-model="configForm.is_enabled" />
        </el-form-item>

        <el-form-item label="启用工具">
          <el-switch v-model="configForm.enable_tools" />
          <span class="form-tip">启用后 AI 可以调用系统功能</span>
        </el-form-item>

        <el-form-item label="流式输出">
          <el-switch v-model="configForm.enable_streaming" />
          <span class="form-tip">逐字显示回复内容，体验更流畅</span>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showConfigDialog = false">取消</el-button>
        <el-button type="primary" @click="saveConfig" :loading="saveLoading">
          保存
        </el-button>
      </template>
    </el-dialog>

    <!-- 工具与调用日志抽屉 -->
    <el-drawer
      v-model="showToolsDrawer"
      title="工具与调用日志"
      size="520px"
      :destroy-on-close="false"
    >
      <el-tabs v-model="toolsTab">
        <!-- 工具/Skill 列表 -->
        <el-tab-pane name="tools">
          <template #label>
            <span>可用工具 <el-tag size="small" round>{{ toolsMeta.total }}</el-tag></span>
          </template>
          <div v-loading="toolsLoading" class="tools-pane">
            <div class="tools-summary">
              <el-tag type="primary" size="small">工具 {{ toolsMeta.tool_count }}</el-tag>
              <el-tag type="success" size="small">Skill {{ toolsMeta.skill_count }}</el-tag>
            </div>
            <div v-for="t in toolList" :key="t.name" class="tool-card">
              <div class="tool-card-head">
                <span class="tool-name">{{ t.display_name }}</span>
                <el-tag :type="t.type === 'skill' ? 'success' : 'info'" size="small">
                  {{ t.type === 'skill' ? 'Skill' : '工具' }}
                </el-tag>
                <code class="tool-id">{{ t.name }}</code>
              </div>
              <div class="tool-desc">{{ t.description }}</div>
            </div>
            <el-empty v-if="!toolsLoading && toolList.length === 0" description="暂无工具" />
          </div>
        </el-tab-pane>

        <!-- 调用日志 -->
        <el-tab-pane name="logs" label="调用日志">
          <div v-loading="execLoading" class="logs-pane">
            <div class="logs-toolbar">
              <el-select
                v-model="execStatusFilter"
                placeholder="全部状态"
                clearable
                size="small"
                style="width: 120px"
                @change="loadExecutions"
              >
                <el-option label="成功" value="completed" />
                <el-option label="失败" value="failed" />
              </el-select>
              <el-button size="small" :icon="Refresh" @click="loadExecutions">刷新</el-button>
            </div>

            <el-collapse v-if="executions.length" accordion>
              <el-collapse-item v-for="e in executions" :key="e.id" :name="e.id">
                <template #title>
                  <div class="log-title">
                    <el-icon v-if="e.status === 'completed'" color="#67c23a"><CircleCheck /></el-icon>
                    <el-icon v-else color="#f56c6c"><CircleClose /></el-icon>
                    <span class="log-tool">{{ toolDisplayNames[e.tool_name] || e.tool_name }}</span>
                    <span v-if="e.execution_time_ms != null" class="log-time">{{ e.execution_time_ms }}ms</span>
                    <span class="log-date">{{ formatTime(e.created_at) }}</span>
                  </div>
                </template>
                <div class="log-body">
                  <div v-if="e.error_message" class="log-error">错误：{{ e.error_message }}</div>
                  <div class="log-section">参数</div>
                  <pre class="log-json">{{ prettyJson(e.arguments) }}</pre>
                  <div class="log-section">结果</div>
                  <pre class="log-json">{{ prettyJson(e.result) }}</pre>
                </div>
              </el-collapse-item>
            </el-collapse>
            <el-empty v-if="!execLoading && executions.length === 0" description="暂无调用记录" />

            <div v-if="execTotal > execPageSize" class="logs-pager">
              <el-pagination
                small
                layout="prev, pager, next"
                :total="execTotal"
                :page-size="execPageSize"
                :current-page="execPage"
                @current-change="onExecPageChange"
              />
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Plus,
  Delete,
  ChatLineRound,
  User,
  Promotion,
  Setting,
  Menu,
  Loading,
  Tools,
  Refresh,
  CircleCheck,
  CircleClose,
} from '@element-plus/icons-vue'
import AppIcon from '@/components/common/AppIcon.vue'
import { marked } from 'marked'
import api from '@/api'
import type {
  AIAgentConfig,
  AIConversation,
  AIMessage,
  LLMConfigOption,
  AITool,
  AIToolExecution,
} from '@/api/modules/aiAgent'

// ==================== 状态 ====================

const loading = ref(false)
const saveLoading = ref(false)
const showConfigDialog = ref(false)
const messageListRef = ref<HTMLElement>()

// 流式输出状态
const streamingContent = ref('')
const isStreaming = ref(false)
const streamingToolCalls = ref<Array<{ name: string; status: string; result?: any }>>([])


const config = ref<AIAgentConfig | null>(null)
const llmOptions = ref<LLMConfigOption[]>([])
const conversations = ref<AIConversation[]>([])
const messages = ref<AIMessage[]>([])
const currentConversationId = ref<number | null>(null)
const inputMessage = ref('')
const sidebarVisible = ref(false)

const configForm = ref({
  llm_config_id: null as number | null,
  is_enabled: true,
  enable_tools: true,
  enable_streaming: true,
})

// ==================== 工具与调用日志抽屉 ====================
const showToolsDrawer = ref(false)
const toolsTab = ref('tools')

const toolList = ref<AITool[]>([])
const toolsMeta = ref({ total: 0, tool_count: 0, skill_count: 0 })
const toolsLoading = ref(false)

const executions = ref<AIToolExecution[]>([])
const execLoading = ref(false)
const execTotal = ref(0)
const execPage = ref(1)
const execPageSize = ref(20)
const execStatusFilter = ref<string>('')

function openToolsDrawer() {
  showToolsDrawer.value = true
  if (toolList.value.length === 0) loadTools()
  loadExecutions()
}

async function loadTools() {
  toolsLoading.value = true
  try {
    const res = await api.aiAgent.getTools()
    toolList.value = res.data.tools
    toolsMeta.value = {
      total: res.data.total,
      tool_count: res.data.tool_count,
      skill_count: res.data.skill_count,
    }
  } catch (e) {
    ElMessage.error('加载工具列表失败')
  } finally {
    toolsLoading.value = false
  }
}

async function loadExecutions() {
  execLoading.value = true
  try {
    const res = await api.aiAgent.getToolExecutions({
      page: execPage.value,
      page_size: execPageSize.value,
      exec_status: execStatusFilter.value || undefined,
    })
    executions.value = res.data.executions
    execTotal.value = res.data.total
  } catch (e) {
    ElMessage.error('加载调用日志失败')
  } finally {
    execLoading.value = false
  }
}

function onExecPageChange(page: number) {
  execPage.value = page
  loadExecutions()
}

function prettyJson(v: any): string {
  if (v == null) return '—'
  try {
    return JSON.stringify(v, null, 2)
  } catch {
    return String(v)
  }
}

// 工具显示名映射
const toolDisplayNames: Record<string, string> = {
  movie_recommend: '电影推荐',
  tv_recommend: '剧集推荐',
  pt_sync: 'PT同步',
  resource_search: '资源搜索',
  resource_identify: '资源识别',
  download_create: '创建下载',
  download_status: '下载状态',
  subscription_create: '创建订阅',
  subscription_list: '订阅列表',
  media_query: '媒体查询',
  system_status: '系统状态',
  trending_query: '榜单查询',
}

// ==================== 计算属性 ====================

// 过滤掉 tool 角色的消息（这些是技术细节，用户不需要看到）
const visibleMessages = computed(() => {
  return messages.value.filter(msg => msg.role !== 'tool')
})

// ==================== 方法 ====================

const formatTime = (time: string) => {
  if (!time) return ''
  const date = new Date(time)
  const now = new Date()
  const diff = now.getTime() - date.getTime()

  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`
  return date.toLocaleDateString()
}

const renderMarkdown = (text: string) => {
  if (!text) return ''
  // 过滤掉伪工具调用文本（流式模式下LLM可能生成此类文本）
  const filteredText = text.replace(/\[Call Tool:\s*\w+\([^)]*\)\]/g, '')
  return marked(filteredText)
}

const getToolDisplayName = (name: string) => {
  return toolDisplayNames[name] || name
}

const scrollToBottom = () => {
  nextTick(() => {
    if (messageListRef.value) {
      messageListRef.value.scrollTop = messageListRef.value.scrollHeight
    }
  })
}

// 加载 LLM 配置选项
const loadLLMOptions = async () => {
  try {
    const res = await api.aiAgent.getLLMOptions()
    llmOptions.value = res.data || []
  } catch (error) {
    console.error('加载 LLM 选项失败:', error)
  }
}

// 加载配置
const loadConfig = async () => {
  try {
    const res = await api.aiAgent.getConfig()
    config.value = res.data
    if (res.data) {
      configForm.value = {
        llm_config_id: res.data.llm_config_id ?? null,
        is_enabled: res.data.is_enabled,
        enable_tools: res.data.enable_tools,
        enable_streaming: res.data.enable_streaming ?? true,
      }
    }
  } catch (error) {
    console.error('加载配置失败:', error)
  }
}

// 加载对话列表
const loadConversations = async () => {
  try {
    const res = await api.aiAgent.getConversations({ status: 'active' })
    conversations.value = res.data.items
  } catch (error) {
    console.error('加载对话列表失败:', error)
  }
}

// 加载对话消息
const loadMessages = async (conversationId: number) => {
  try {
    const res = await api.aiAgent.getConversation(conversationId)
    messages.value = res.data.messages
    scrollToBottom()
  } catch (error) {
    console.error('加载消息失败:', error)
  }
}

// 选择对话
const handleSelectConversation = async (conversationId: number) => {
  currentConversationId.value = conversationId
  sidebarVisible.value = false
  await loadMessages(conversationId)
}

// 创建新对话
const handleNewConversation = () => {
  currentConversationId.value = null
  messages.value = []
  sidebarVisible.value = false
}

// 删除对话
const deleteConversation = async (conversationId: number) => {
  try {
    await api.aiAgent.deleteConversation(conversationId)
    await loadConversations()
    if (currentConversationId.value === conversationId) {
      currentConversationId.value = null
      messages.value = []
    }
    ElMessage.success('对话已删除')
  } catch (error) {
    ElMessage.error('删除失败')
  }
}

// 发送消息
const sendMessage = async () => {
  const message = inputMessage.value.trim()
  if (!message || loading.value) return

  // 清空输入框并显示加载状态
  inputMessage.value = ''
  loading.value = true

  // 立即显示用户消息（乐观更新）
  const tempUserMessage: AIMessage = {
    id: Date.now(), // 临时ID
    conversation_id: currentConversationId.value || 0,
    role: 'user',
    content: message,
    created_at: new Date().toISOString(),
  }
  messages.value.push(tempUserMessage)
  scrollToBottom()

  // 检查是否启用流式输出
  const enableStreaming = config.value?.enable_streaming ?? true

  try {
    if (enableStreaming) {
      await sendMessageStream(message, tempUserMessage)
    } else {
      await sendMessageNonStream(message, tempUserMessage)
    }
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || error.message || '发送失败')
    // 发送失败时恢复输入，移除临时消息
    inputMessage.value = message
    messages.value = messages.value.filter(m => m.id !== tempUserMessage.id)
  } finally {
    loading.value = false
    isStreaming.value = false
    streamingContent.value = ''
    streamingToolCalls.value = []
  }
}

// 非流式发送
const sendMessageNonStream = async (message: string, tempUserMessage: AIMessage) => {
  const res = await api.aiAgent.chat({
    message,
    conversation_id: currentConversationId.value || undefined,
  })

  // 更新对话ID
  if (!currentConversationId.value) {
    currentConversationId.value = res.data.conversation_id
    await loadConversations()
  }

  // 重新加载完整的对话消息
  await loadMessages(res.data.conversation_id)
}

// 流式发送
const sendMessageStream = async (message: string, tempUserMessage: AIMessage) => {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || '/api/v1'
  const url = `${baseUrl}/ai-agent/chat/stream`
  const token = localStorage.getItem('token')

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({
      message,
      conversation_id: currentConversationId.value || undefined,
    }),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: '流式请求失败' }))
    throw new Error(error.detail || '流式请求失败')
  }

  isStreaming.value = true
  streamingContent.value = ''

  const reader = response.body?.getReader()
  const decoder = new TextDecoder()

  if (!reader) {
    throw new Error('无法读取响应流')
  }

  let conversationId: number | null = currentConversationId.value

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    const chunk = decoder.decode(value, { stream: true })
    const lines = chunk.split('\n')

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = line.slice(6).trim()
        if (!data || data === '[DONE]') continue

        try {
          const parsed = JSON.parse(data)

          // 根据类型处理消息
          switch (parsed.type) {
            case 'error':
              throw new Error(parsed.error || '流式输出错误')

            case 'conversation':
              // 获取对话ID
              if (parsed.conversation_id && !conversationId) {
                conversationId = parsed.conversation_id
                currentConversationId.value = conversationId
                loadConversations() // 不 await，避免阻塞流读取
              }
              break

            case 'content':
              // 累积流式内容（显示在 isStreaming 区域，不操作 messages 数组）
              if (parsed.content !== undefined) {
                streamingContent.value += parsed.content
                scrollToBottom()
              }
              break

            case 'tool_calls':
              // LLM 请求工具调用，清空之前的流式内容（将在下一轮继续）
              streamingContent.value = ''
              if (parsed.tool_calls) {
                streamingToolCalls.value.push(...parsed.tool_calls.map((tc: any) => ({
                  name: tc.name,
                  status: 'running',
                })))
                scrollToBottom()
              }
              break

            case 'tool_result':
              // 标记工具执行完成
              if (parsed.tool_name) {
                const tc = streamingToolCalls.value.find(t => t.name === parsed.tool_name && t.status === 'running')
                if (tc) {
                  tc.status = 'done'
                  tc.result = parsed.result
                }
                scrollToBottom()
              }
              break

            case 'done':
              break
          }
        } catch (e: any) {
          if (e.message?.includes('流式') || e.message?.includes('错误')) {
            throw e
          }
          // 忽略其他解析错误
        }
      }
    }
  }

  // 流式完成后，重新加载完整消息以获取正确的ID和元数据
  if (conversationId) {
    await loadMessages(conversationId)
  }
}

// 保存配置
const saveConfig = async () => {
  if (!configForm.value.llm_config_id) {
    ElMessage.warning('请选择 LLM 配置')
    return
  }

  saveLoading.value = true
  try {
    const data: any = {
      llm_config_id: configForm.value.llm_config_id,
      is_enabled: configForm.value.is_enabled,
      enable_tools: configForm.value.enable_tools,
      enable_streaming: configForm.value.enable_streaming,
    }

    if (config.value) {
      await api.aiAgent.updateConfig(data)
    } else {
      await api.aiAgent.createConfig(data)
    }

    await loadConfig()
    showConfigDialog.value = false
    ElMessage.success('配置已保存')
  } catch (error) {
    ElMessage.error('保存失败')
  } finally {
    saveLoading.value = false
  }
}

// ==================== 生命周期 ====================

onMounted(async () => {
  await loadLLMOptions()
  await loadConfig()
  await loadConversations()
})
</script>

<style lang="scss" scoped>
.ai-agent-container {
  display: flex;
  height: calc(100vh - 120px);
  background: var(--el-bg-color);
  border-radius: 8px;
  overflow: hidden;
}

.sidebar {
  width: 280px;
  border-right: 1px solid var(--el-border-color-light);
  display: flex;
  flex-direction: column;

  .sidebar-header {
    padding: 16px;
    border-bottom: 1px solid var(--el-border-color-light);
    display: flex;
    gap: 8px;

    .new-chat-btn {
      flex: 1;
    }
  }

  .conversation-list {
    flex: 1;
    overflow-y: auto;
    padding: 8px;

    .conversation-item {
      display: flex;
      align-items: center;
      padding: 12px;
      border-radius: 8px;
      cursor: pointer;
      transition: background-color 0.2s;

      &:hover {
        background: var(--el-fill-color-light);
      }

      &.active {
        background: var(--bg-color-sidebar-active);

        .conv-title {
          color: var(--primary-color);
          font-weight: 600;
        }

        .conv-info {
           .conv-time {
             color: var(--primary-color);
             opacity: 0.8;
           }
        }
      }

      .conv-icon {
        font-size: 20px;
        color: var(--el-text-color-secondary);
        margin-right: 12px;
      }

      &.active .conv-icon {
        color: var(--primary-color);
      }

      .conv-info {
        flex: 1;
        min-width: 0;

        .conv-title {
          font-size: 14px;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .conv-time {
          font-size: 12px;
          color: var(--el-text-color-secondary);
          margin-top: 4px;
        }
      }

      .conv-delete {
        opacity: 0;
        transition: opacity 0.2s;
      }

      &:hover .conv-delete {
        opacity: 1;
      }
    }

    .empty-tip {
      text-align: center;
      color: var(--el-text-color-secondary);
      padding: 40px 20px;
    }
  }
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;

  .config-tip {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .message-list {
    flex: 1;
    overflow-y: auto;
    padding: 20px;

    .message-item {
      display: flex;
      margin-bottom: 20px;

      &.user {
        flex-direction: row-reverse;

        .message-content {
          align-items: flex-end;

          .message-text {
            background: var(--el-color-primary);
            color: #fff;
          }
        }
      }

      &.assistant {
        .message-content {
          .message-text {
            background: var(--el-fill-color);
          }
        }
      }

      .message-avatar {
        flex-shrink: 0;
        margin: 0 12px;

        .ai-avatar {
          background: var(--nf-primary, #3B82F6);
          color: white;
        }
      }

      .message-content {
        display: flex;
        flex-direction: column;
        max-width: 70%;

        .message-text {
          padding: 12px 16px;
          border-radius: 12px;
          line-height: 1.6;

          :deep(p) {
            margin: 0 0 8px;

            &:last-child {
              margin-bottom: 0;
            }
          }

          :deep(ul), :deep(ol) {
            margin: 8px 0;
            padding-left: 20px;
          }

          :deep(code) {
            background: rgba(0, 0, 0, 0.1);
            padding: 2px 6px;
            border-radius: 4px;
          }

          :deep(pre) {
            background: rgba(0, 0, 0, 0.1);
            padding: 12px;
            border-radius: 8px;
            overflow-x: auto;

            code {
              background: none;
              padding: 0;
            }
          }
        }

        .message-tools {
          margin-top: 8px;

          .el-tag {
            margin-right: 4px;
          }

          &.streaming-tools .el-tag .is-loading {
            margin-right: 4px;
          }
        }
      }
    }

    .typing-indicator {
      display: flex;
      gap: 4px;
      padding: 12px 16px;

      span {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: var(--el-text-color-secondary);
        animation: typing 1.4s infinite ease-in-out;

        &:nth-child(2) {
          animation-delay: 0.2s;
        }

        &:nth-child(3) {
          animation-delay: 0.4s;
        }
      }
    }
  }

  .input-area {
    padding: 14px 20px 18px;
    background: var(--el-bg-color);

    .input-wrapper {
      display: flex;
      align-items: flex-end;
      gap: 10px;
      background: var(--el-fill-color-light);
      border: 1.5px solid var(--el-border-color);
      border-radius: 16px;
      padding: 6px 6px 6px 14px;
      transition: border-color 0.2s;

      &:focus-within {
        border-color: var(--el-color-primary);
        background: var(--el-bg-color);
      }

      :deep(.el-textarea) {
        flex: 1;
        border: none;
        background: transparent;

        .el-textarea__inner {
          border: none;
          background: transparent;
          box-shadow: none;
          padding: 5px 0;
          resize: none;
          overflow: hidden;
          line-height: 1.6;
          font-size: 14px;
          min-height: unset !important;
        }
      }

      .send-btn {
        flex-shrink: 0;
        width: 36px;
        height: 36px;
        margin-bottom: 2px;
        border: none;
        background: transparent;
        color: var(--el-color-primary);
        transition: color 0.2s, background 0.2s;

        &:hover:not(:disabled) {
          background: var(--el-color-primary-light-9);
          color: var(--el-color-primary);
        }

        &:disabled {
          background: transparent;
          color: var(--el-text-color-placeholder);
        }

        :deep(.el-icon) {
          font-size: 18px;
        }
      }
    }
  }
}

.form-tip {
  margin-left: 12px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

@keyframes typing {
  0%, 60%, 100% {
    transform: translateY(0);
  }
  30% {
    transform: translateY(-4px);
  }
}

/* Mobile Adaptation */
.mobile-header {
  display: none; /* Desktop hidden */
}

.sidebar-overlay {
  display: none;
}

@media (max-width: 768px) {
  .ai-agent-container {
    /* 减去：顶部header(60px) + 顶部内边距(16px) + 底部导航栏(56px) + safe-area */
    height: calc(100vh - 60px - 16px - 56px - env(safe-area-inset-bottom, 0px));
    border-radius: 0;
    position: relative;
    overflow: hidden;
  }

  /* Overlay */
  .sidebar-overlay {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.5);
    z-index: 99;
    display: none;
  }

  .ai-agent-container.sidebar-open .sidebar-overlay {
    display: block;
  }

  /* Sidebar Drawer */
  .sidebar {
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    width: 80%;
    max-width: 300px;
    background: var(--el-bg-color);
    z-index: 100;
    transform: translateX(-100%);
    transition: transform 0.3s ease;
    border-right: none;
    box-shadow: 2px 0 8px rgba(0,0,0,0.1);
  }

  .ai-agent-container.sidebar-open .sidebar {
    transform: translateX(0);
  }

  /* Main Content */
  .main-content {
    width: 100%;

    /* Mobile Header */
    .mobile-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      height: 50px;
      padding: 0 12px;
      border-bottom: 1px solid var(--el-border-color-light);
      background: var(--el-bg-color);
      flex-shrink: 0;

      .mobile-title {
        font-weight: 600;
        font-size: 16px;
      }

      .el-button {
        font-size: 18px;
        padding: 4px;
        height: auto;
        border: none;
        background: transparent;
      }
    }

    .message-list {
      padding: 12px;

      .message-item {
        margin-bottom: 14px;

        .message-content {
          max-width: 85%;

          .message-text {
            padding: 10px 12px;
            font-size: 14px;
          }
        }

        .message-avatar {
          margin: 0 8px;

          .el-avatar {
            width: 32px;
            height: 32px;
            font-size: 14px;
          }
        }
      }
    }

    .input-area {
      padding: 10px 12px 12px;

      .input-wrapper {
        border-radius: 14px;
        padding: 5px 5px 5px 12px;

        :deep(.el-textarea .el-textarea__inner) {
          font-size: 16px; /* 防止 iOS 自动缩放 */
        }

        .send-btn {
          width: 34px;
          height: 34px;

          :deep(.el-icon) {
            font-size: 16px;
          }
        }
      }
    }
  }

  /* 配置对话框移动端适配 */
  :global(.el-dialog) {
    margin: 8px auto;

    .el-form-item__label {
      font-size: 13px;
    }
  }
}

/* 工具与调用日志抽屉 */
.tools-pane {
  .tools-summary {
    display: flex;
    gap: 8px;
    margin-bottom: 12px;
  }

  .tool-card {
    padding: 10px 12px;
    margin-bottom: 8px;
    border: 1px solid var(--el-border-color-light);
    border-radius: 8px;
    background: var(--el-fill-color-blank);

    .tool-card-head {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 4px;

      .tool-name {
        font-weight: 600;
      }

      .tool-id {
        font-size: 12px;
        color: var(--el-text-color-secondary);
        background: var(--el-fill-color-light);
        padding: 1px 6px;
        border-radius: 4px;
      }
    }

    .tool-desc {
      font-size: 13px;
      color: var(--el-text-color-regular);
      line-height: 1.5;
    }
  }
}

.logs-pane {
  .logs-toolbar {
    display: flex;
    gap: 8px;
    align-items: center;
    margin-bottom: 12px;
  }

  .log-title {
    display: flex;
    align-items: center;
    gap: 8px;
    width: 100%;

    .log-tool {
      font-weight: 600;
    }

    .log-time {
      font-size: 12px;
      color: var(--el-color-primary);
    }

    .log-date {
      margin-left: auto;
      font-size: 12px;
      color: var(--el-text-color-secondary);
    }
  }

  .log-body {
    .log-error {
      color: var(--el-color-danger);
      font-size: 13px;
      margin-bottom: 8px;
    }

    .log-section {
      font-size: 12px;
      font-weight: 600;
      color: var(--el-text-color-secondary);
      margin: 6px 0 2px;
    }

    .log-json {
      margin: 0;
      padding: 8px;
      font-size: 12px;
      background: var(--el-fill-color-light);
      border-radius: 6px;
      white-space: pre-wrap;
      word-break: break-all;
      max-height: 240px;
      overflow: auto;
    }
  }

  .logs-pager {
    display: flex;
    justify-content: center;
    margin-top: 12px;
  }
}
</style>
