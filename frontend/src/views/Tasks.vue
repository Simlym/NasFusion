<template>
  <div class="page-container">
    <!-- Tab 内容显示区域 -->
    <div v-if="activeTab === 'live-queue'" v-loading="queueLoading" class="tab-content">
      <!-- 实时队列区块 -->
      <div class="unified-queue-section">
        <!-- 状态过滤器 -->
        <div class="status-filter-bar">
          <div class="filter-tabs">
            <div
              class="filter-tab"
              :class="{ active: queueStatusFilter === 'running' }"
              @click="queueStatusFilter = 'running'"
            >
              <span class="tab-dot running"></span>
              <span class="tab-label">运行中</span>
              <span class="tab-count" v-if="queueStatus.running.length > 0">{{ queueStatus.running.length }}</span>
            </div>
            <div
              class="filter-tab"
              :class="{ active: queueStatusFilter === 'pending' }"
              @click="queueStatusFilter = 'pending'"
            >
              <span class="tab-dot pending"></span>
              <span class="tab-label">等待中</span>
              <span class="tab-count" v-if="queueStatus.pending.length > 0">{{ queueStatus.pending.length }}</span>
            </div>
            <div
              class="filter-tab"
              :class="{ active: queueStatusFilter === 'recent_completed' }"
              @click="queueStatusFilter = 'recent_completed'"
            >
              <span class="tab-dot completed"></span>
              <span class="tab-label">最近完成</span>
              <span class="tab-count" v-if="queueStatus.recent_completed.length > 0">{{ queueStatus.recent_completed.length }}</span>
            </div>
          </div>
          <div class="filter-live-indicator">
            <span class="live-dot"></span>
            实时更新
          </div>
        </div>

        <!-- 队列表格 -->
        <div class="modern-table-container">
          <div class="table-header">
            <div class="header-title">
              <h3>任务列表</h3>
              <div class="header-badge">{{ displayQueueTasks.length }} 个任务</div>
            </div>
            <div class="header-actions">
              <el-button
                type="primary"
                :icon="Refresh"
                :loading="queueLoading"
                size="small"
                @click="loadQueueStatus"
              >
                刷新
              </el-button>
            </div>
          </div>

          <!-- 移动端卡片视图 -->
          <div v-if="displayQueueTasks.length > 0 && isMobile" class="queue-cards-mobile">
            <div v-for="row in displayQueueTasks" :key="row.id" class="queue-card-mobile">
              <div class="queue-card-header">
                <div class="status-cell">
                  <div
                    class="status-indicator"
                    :class="{
                      'status-running': row.status === 'running',
                      'status-pending': row.status === 'pending',
                      'status-completed': row.status === 'completed',
                      'status-failed': row.status === 'failed',
                      'status-cancelled': row.status === 'cancelled'
                    }"
                  >
                    <el-icon v-if="row.status === 'running'" class="rotate-icon"><Loading /></el-icon>
                    <el-icon v-else-if="row.status === 'completed'"><CircleCheck /></el-icon>
                    <el-icon v-else-if="row.status === 'failed'"><Close /></el-icon>
                    <el-icon v-else><Clock /></el-icon>
                  </div>
                  <span class="status-text">{{ getStatusName(row.status) }}</span>
                </div>
                <el-tag :type="getTaskTypeColor(row.task_type)" size="small" effect="light">{{ getTaskTypeName(row.task_type) }}</el-tag>
              </div>
              <div class="queue-card-title">{{ row.task_name }}</div>
              <!-- 进度 -->
              <div v-if="row.status === 'running'" class="queue-card-progress">
                <div v-if="row.progress_detail?.steps" class="step-progress">
                  <el-icon class="step-icon-running"><Loading /></el-icon>
                  <span class="step-text">{{ getCurrentStepName(row) }}</span>
                </div>
                <div v-else-if="row.progress_detail?.processed !== undefined" class="batch-progress-text">
                  已处理: {{ row.progress_detail.processed }}/{{ row.progress_detail.total }}
                </div>
                <el-progress :percentage="row.progress" :stroke-width="4" :color="getProgressColor(row.progress)" />
              </div>
              <div v-if="row.error_message" class="queue-card-error">
                <el-icon class="error-icon"><Warning /></el-icon>
                <span class="error-text">{{ row.error_message }}</span>
              </div>
              <div class="queue-card-footer">
                <span class="time-value">{{ formatDate(row.created_at) }}</span>
                <div class="actions-cell">
                  <el-button v-if="['running', 'pending'].includes(row.status)" link type="warning" size="small" @click="handleCancelExecution(row.id)">取消</el-button>
                  <el-button link type="primary" size="small" @click="handleViewDetail(row.id)">详情</el-button>
                </div>
              </div>
            </div>
          </div>

          <el-table
            v-if="displayQueueTasks.length > 0 && !isMobile"
            :data="displayQueueTasks"
            class="queue-table modern-table"
            :style="{ width: '100%' }"
            :row-style="{
              transition: 'all 0.2s ease'
            }"
          >
            <el-table-column prop="status" label="状态" width="120">
              <template #default="{ row }">
                <div class="status-cell">
                  <div
                    class="status-indicator"
                    :class="{
                      'status-running': row.status === 'running',
                      'status-pending': row.status === 'pending',
                      'status-completed': row.status === 'completed',
                      'status-failed': row.status === 'failed',
                      'status-cancelled': row.status === 'cancelled'
                    }"
                  >
                    <el-icon v-if="row.status === 'running'" class="rotate-icon">
                      <Loading />
                    </el-icon>
                    <el-icon v-else-if="row.status === 'completed'">
                      <CircleCheck />
                    </el-icon>
                    <el-icon v-else-if="row.status === 'failed'">
                      <Close />
                    </el-icon>
                    <el-icon v-else>
                      <Clock />
                    </el-icon>
                  </div>
                  <span class="status-text">{{ getStatusName(row.status) }}</span>
                </div>
              </template>
            </el-table-column>

            <el-table-column prop="task_name" label="任务名称" min-width="200" show-overflow-tooltip>
              <template #default="{ row }">
                <div class="task-name-cell">
                  <div class="task-title">{{ row.task_name }}</div>
                  <div class="task-id">ID: {{ row.id }}</div>
                </div>
              </template>
            </el-table-column>

            <el-table-column prop="task_type" label="类型" width="140">
              <template #default="{ row }">
                <el-tag
                  :type="getTaskTypeColor(row.task_type)"
                  size="small"
                  effect="light"
                  class="task-type-tag"
                >
                  {{ getTaskTypeName(row.task_type) }}
                </el-tag>
              </template>
            </el-table-column>

            <el-table-column label="进度" width="250">
              <template #default="{ row }">
                <!-- 步骤式进度（如 create_download） -->
                <div v-if="row.status === 'running' && row.progress_detail?.steps" class="progress-cell">
                  <div class="step-progress">
                    <el-icon v-if="getCurrentStepStatus(row) === 'running'" class="step-icon-running">
                      <Loading />
                    </el-icon>
                    <el-icon v-else-if="getCurrentStepStatus(row) === 'completed'" class="step-icon-success">
                      <CircleCheck />
                    </el-icon>
                    <el-icon v-else class="step-icon-pending">
                      <Clock />
                    </el-icon>
                    <span class="step-text">{{ getCurrentStepName(row) }}</span>
                  </div>
                  <div class="mini-progress">
                    <el-progress
                      :percentage="row.progress"
                      :stroke-width="4"
                      :show-text="false"
                      :color="getProgressColor(row.progress)"
                    />
                  </div>
                </div>

                <!-- 批量处理进度（如 batch_identify） -->
                <div v-else-if="row.status === 'running' && row.progress_detail?.processed !== undefined" class="progress-cell">
                  <div class="batch-progress-text">
                    已处理: {{ row.progress_detail.processed }}/{{ row.progress_detail.total }}
                  </div>
                  <div class="mini-progress">
                    <el-progress
                      :percentage="row.progress"
                      :stroke-width="4"
                      :show-text="false"
                      :color="getProgressColor(row.progress)"
                    />
                  </div>
                </div>

                <!-- 普通进度条 -->
                <div v-else-if="row.status === 'running'" class="progress-cell">
                  <div class="progress-wrapper">
                    <el-progress
                      :percentage="row.progress"
                      :stroke-width="8"
                      :color="getProgressColor(row.progress)"
                      striped
                      striped-flow
                      class="modern-progress"
                    />
                    <div class="progress-text">{{ row.progress }}%</div>
                  </div>
                </div>

                <!-- 非运行状态 -->
                <div v-else class="progress-cell">
                  <span class="no-progress">-</span>
                </div>
              </template>
            </el-table-column>

            <el-table-column label="创建时间" width="160">
              <template #default="{ row }">
                <div class="time-cell">
                  <div class="time-value">{{ formatDate(row.created_at) }}</div>
                </div>
              </template>
            </el-table-column>

            <el-table-column label="耗时" width="100">
              <template #default="{ row }">
                <div class="duration-cell">
                  <span v-if="['completed', 'failed', 'cancelled'].includes(row.status)" class="duration-value">
                    {{ formatDuration(row.duration) }}
                  </span>
                  <span v-else class="duration-value">-</span>
                </div>
              </template>
            </el-table-column>

            <el-table-column label="错误信息" min-width="180" show-overflow-tooltip>
              <template #default="{ row }">
                <div v-if="row.error_message" class="error-cell">
                  <el-tooltip :content="row.error_message" placement="top">
                    <div class="error-content">
                      <el-icon class="error-icon"><Warning /></el-icon>
                      <span class="error-text">{{ row.error_message }}</span>
                    </div>
                  </el-tooltip>
                </div>
                <span v-else class="no-error">-</span>
              </template>
            </el-table-column>

            <el-table-column label="操作" width="120" fixed="right">
              <template #default="{ row }">
                <div class="actions-cell">
                  <el-button
                    v-if="['running', 'pending'].includes(row.status)"
                    link
                    type="warning"
                    size="small"
                    @click="handleCancelExecution(row.id)"
                  >
                    取消
                  </el-button>

                  <el-button
                    link
                    type="primary"
                    size="small"
                    @click="handleViewDetail(row.id)"
                  >
                    详情
                  </el-button>
                </div>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <!-- 空状态 -->
        <el-empty
          v-if="displayQueueTasks.length === 0"
          description="暂无任务"
          :image-size="80"
        >
          <template #description>
            <p style="font-size: 16px; color: #6b7280">暂无任务</p>
            <p style="font-size: 14px; color: #9ca3af; margin-top: 8px">
              {{ queueStatusFilter === 'running' ? '当前没有运行中的任务' :
                 queueStatusFilter === 'pending' ? '当前没有等待中的任务' :
                 '最近24小时内没有完成的任务' }}
            </p>
          </template>
        </el-empty>
      </div>
    </div>

    <div v-else-if="activeTab === 'history'" v-loading="historyLoading" class="tab-content">
      <div class="history-section">
        <div class="toolbar">
          <div class="toolbar-left">
            <el-form inline>
              <el-form-item>
                <el-select v-model="historyFilters.status" placeholder="全部状态" clearable style="width: 140px">
                  <el-option label="已完成" value="completed" />
                  <el-option label="失败" value="failed" />
                  <el-option label="已取消" value="cancelled" />
                  <el-option label="运行中" value="running" />
                  <el-option label="等待中" value="pending" />
                </el-select>
              </el-form-item>

              <el-form-item label="任务类型">
                <el-select v-model="historyFilters.task_type" placeholder="全部类型" clearable style="width: 160px">
                  <el-option label="PT资源同步" value="pt_resource_sync" />
                  <el-option label="PT资源识别" value="pt_resource_identify" />
                  <el-option label="订阅检查" value="subscription_check" />
                  <el-option label="媒体扫描" value="media_file_scan" />
                  <el-option label="资源下载" value="download_create" />
                  <el-option label="下载状态同步" value="download_status_sync" />
                  <el-option label="观看历史同步" value="media_server_watch_history_sync" />
                  <el-option label="库统计更新" value="media_server_library_stats_update" />
                  <el-option label="演职员关系回填" value="credits_backfill" />
                  <el-option label="重复人物合并" value="person_merge" />
                </el-select>
              </el-form-item>

              <el-form-item label="关键字">
                <el-input
                  v-model="historyFilters.keyword"
                  placeholder="任务名称"
                  clearable
                  style="width: 160px"
                />
              </el-form-item>

              <el-form-item label="日期范围">
                <el-date-picker
                  v-model="historyFilters.dateRange"
                  type="daterange"
                  range-separator="至"
                  start-placeholder="开始日期"
                  end-placeholder="结束日期"
                  style="width: 250px"
                  clearable
                />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :icon="Search" @click="loadHistory">查询</el-button>
                <el-button @click="resetHistoryFilters">重置</el-button>
              </el-form-item>
            </el-form>
          </div>
          
          <div class="toolbar-right">
          </div>
        </div>
          
        <!-- 特定任务筛选提示 -->
        <div v-if="historyFilters.scheduledTaskId" style="margin-bottom: 15px;">
           <el-tag closable @close="() => { historyFilters.scheduledTaskId = null; loadHistory() }">
             筛选特定任务 ID: {{ historyFilters.scheduledTaskId }}
           </el-tag>
        </div>

        <!-- 历史记录表格 -->
        <el-table
          v-if="historyList.length > 0"
          :data="historyList"
          :style="{ width: '100%' }"
        >
          <el-table-column prop="status" label="状态" width="120">
            <template #default="{ row }">
              <el-tag :type="getStatusTagType(row.status)">
                {{ getStatusName(row.status) }}
              </el-tag>
            </template>
          </el-table-column>

          <el-table-column prop="task_name" label="任务名称" min-width="200" show-overflow-tooltip />

          <el-table-column prop="task_type" label="类型" width="200">
            <template #default="{ row }">
              <el-tag
                :type="getTaskTypeColor(row.task_type)"
                size="small"
                effect="light"
              >
                {{ getTaskTypeName(row.task_type) }}
              </el-tag>
            </template>
          </el-table-column>

          <el-table-column label="创建时间" width="160">
            <template #default="{ row }">
              {{ formatDate(row.created_at) }}
            </template>
          </el-table-column>

          <el-table-column label="完成时间" width="160">
            <template #default="{ row }">
              <span v-if="['completed', 'failed', 'cancelled'].includes(row.status)">
                {{ formatDate(row.completed_at || row.updated_at) }}
              </span>
              <span v-else>-</span>
            </template>
          </el-table-column>

          <el-table-column label="耗时" width="100">
            <template #default="{ row }">
              <span v-if="['completed', 'failed', 'cancelled'].includes(row.status)">
                {{ formatDuration(row.duration) }}
              </span>
              <span v-else>-</span>
            </template>
          </el-table-column>

          <el-table-column label="操作" width="120" fixed="right">
            <template #default="{ row }">
              <el-button
                type="primary"
                text
                size="small"
                @click="handleViewDetail(row.id)"
              >
                详情
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <!-- 空状态 -->
        <el-empty
          v-else
          description="暂无历史记录"
          :image-size="100"
        />

        <!-- 分页 -->
        <div v-if="historyPagination.total > 0" class="pagination-container">
          <el-pagination
            v-model:current-page="historyPagination.page"
            v-model:page-size="historyPagination.page_size"
            :total="historyPagination.total"
            :page-sizes="[10, 20, 50, 100]"
            layout="total, sizes, prev, pager, next, jumper"
            @size-change="loadHistory"
            @current-change="loadHistory"
          />
        </div>
      </div>
    </div>

    <div v-else-if="activeTab === 'scheduled'" v-loading="tasksLoading" class="tab-content">
      <!-- 工具栏 -->
      <div class="toolbar">
        <!-- 左侧：筛选器 -->
        <div class="toolbar-left">
          <el-form inline :model="scheduledTasksFilters">
            <el-form-item>
              <el-select
                v-model="scheduledTasksFilters.task_type"
                placeholder="任务类型"
                clearable
                style="width: 160px"
                @change="loadScheduledTasks"
              >
                <el-option label="PT资源同步" value="pt_resource_sync" />
                <el-option label="PT资源识别" value="pt_resource_identify" />
                <el-option label="订阅检查" value="subscription_check" />
                <el-option label="媒体扫描" value="media_file_scan" />
                <el-option label="资源下载" value="download_create" />
                <el-option label="下载状态同步" value="download_status_sync" />
                <el-option label="观看历史同步" value="media_server_watch_history_sync" />
                <el-option label="库统计更新" value="media_server_library_stats_update" />
                <el-option label="演职员关系回填" value="credits_backfill" />
                <el-option label="重复人物合并" value="person_merge" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-input
                v-model="scheduledTasksFilters.keyword"
                placeholder="任务名称"
                clearable
                style="width: 200px"
                @clear="loadScheduledTasks"
                @keyup.enter="loadScheduledTasks"
              >
                <template #append>
                  <el-button :icon="Search" @click="loadScheduledTasks" />
                </template>
              </el-input>
            </el-form-item>
          </el-form>
        </div>

        <!-- 右侧：创建与批量操作 -->
        <div class="toolbar-right">
          <template v-if="selectedTasks.length > 0">
            <el-tag type="info" style="margin-right: 12px">已选择 {{ selectedTasks.length }} 个任务</el-tag>
            <el-button size="small" :icon="VideoPlay" @click="batchEnable">启用</el-button>
            <el-button size="small" :icon="VideoPause" @click="batchDisable">禁用</el-button>
            <el-button size="small" type="danger" :icon="Delete" @click="batchDelete">删除</el-button>
            <el-divider direction="vertical" />
          </template>
          
          <el-button type="primary" :icon="Plus" @click="handleCreate">创建任务</el-button>
        </div>
      </div>

      <!-- 移动端定时任务卡片视图 -->
      <div v-if="scheduledTasks.length > 0 && isMobile" class="scheduled-cards-mobile">
        <div v-for="task in scheduledTasks" :key="task.id" class="task-card-mobile">
          <div class="task-card-header">
            <div class="task-card-title">{{ task.task_name }}</div>
            <el-switch v-model="task.enabled" :loading="togglingId === task.id" @change="handleToggleTask(task)" />
          </div>
          <div class="task-card-body">
            <div class="task-card-info">
              <span class="info-label">类型</span>
              <el-tag size="small" :type="getTaskTypeColor(task.task_type)" effect="light">{{ getTaskTypeName(task.task_type) }}</el-tag>
            </div>
            <div class="task-card-info">
              <span class="info-label">调度</span>
              <span class="info-value">{{ getScheduleDescription(task) }}</span>
            </div>
            <div class="task-card-info">
              <span class="info-label">上次状态</span>
              <el-tag v-if="task.last_run_status" size="small" :type="getStatusTagType(task.last_run_status)" effect="plain">{{ getStatusName(task.last_run_status) }}</el-tag>
              <span v-else class="info-value">-</span>
            </div>
            <div class="task-card-info">
              <span class="info-label">上次执行</span>
              <span class="info-value">{{ task.last_run_at ? formatDate(task.last_run_at) : '-' }}</span>
            </div>
            <div class="task-card-info">
              <span class="info-label">下次运行</span>
              <span class="info-value">{{ task.next_run_at ? formatDate(task.next_run_at) : '-' }}</span>
            </div>
          </div>
          <div class="task-card-actions">
            <el-button size="small" type="primary" :icon="VideoPlay" :loading="runningId === task.id" @click="handleRunNow(task)" class="action-btn-primary">立即执行</el-button>
            <div class="action-btn-group">
              <el-button size="small" :icon="Clock" @click="handleViewHistory(task)">历史</el-button>
              <el-button size="small" :icon="Edit" @click="handleEdit(task)">编辑</el-button>
              <el-button size="small" type="danger" plain :icon="Delete" @click="handleDelete(task)">删除</el-button>
            </div>
          </div>
        </div>
      </div>

      <!-- 定时任务表格 -->
      <el-table
        v-if="scheduledTasks.length > 0 && !isMobile"
        :data="scheduledTasks"
        :style="{ width: '100%' }"
        class="scheduled-tasks-table"
        :default-sort="{ prop: 'task_type', order: 'ascending' }"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column prop="task_name" label="任务名称" min-width="150" show-overflow-tooltip sortable />
        <el-table-column prop="task_type" label="类型" width="180" sortable :sort-method="(a, b) => getTaskTypeName(a.task_type).localeCompare(getTaskTypeName(b.task_type), 'zh')">
          <template #default="{ row }">
            {{ getTaskTypeName(row.task_type) }}
          </template>
        </el-table-column>
        <el-table-column label="调度" width="180" align="left">
          <template #default="{ row }">
            <div style="text-align: left;">
              <el-text size="small">{{ getScheduleDescription(row) }}</el-text>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="last_run_at" label="上次执行" width="160" align="left" sortable>
          <template #default="{ row }">
            <div style="text-align: left;">
              <el-text v-if="row.last_run_at" size="small">{{ formatDate(row.last_run_at) }}</el-text>
              <span v-else>-</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="上次状态" width="90">
          <template #default="{ row }">
            <el-tag v-if="row.last_run_status" size="small" :type="getStatusTagType(row.last_run_status)" effect="plain">
              {{ getStatusName(row.last_run_status) }}
            </el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="next_run_at" label="下次运行" width="180" align="left" sortable>
          <template #default="{ row }">
            <div style="text-align: left;">
              <el-text v-if="row.next_run_at" size="small">{{ formatDate(row.next_run_at) }}</el-text>
              <span v-else>-</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-switch
              v-model="row.enabled"
              :loading="togglingId === row.id"
              @change="handleToggleTask(row)"
            />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="260" fixed="right">
          <template #default="{ row }">
            <div style="display: flex; align-items: center; justify-content: flex-start; gap: 4px;">
              <el-button
                type="primary"
                link
                size="small"
                :icon="VideoPlay"
                :loading="runningId === row.id"
                @click="handleRunNow(row)"
              >
                执行
              </el-button>
              <el-button
                type="primary"
                link
                size="small"
                :icon="Clock"
                @click="handleViewHistory(row)"
              >
                历史
              </el-button>
              <el-dropdown trigger="click">
                <el-button link type="primary" size="small">
                  更多<el-icon class="el-icon--right"><More /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item :icon="Edit" @click="handleEdit(row)">编辑</el-dropdown-item>
                    <el-dropdown-item :icon="Delete" style="color: #f56c6c" @click="handleDelete(row)">删除</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="scheduledTasks.length === 0" description="暂无定时任务" :image-size="100">
        <el-button type="primary" :icon="Plus" @click="handleCreate">创建第一个任务</el-button>
      </el-empty>
    </div>

    <!-- 创建/编辑任务对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="getDialogTitle()"
      :width="isMobile ? '95%' : '600px'"
      @close="handleDialogClose"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="120px">
        <el-form-item label="任务类型" prop="task_type">
          <el-select
            v-model="form.task_type"
            placeholder="请选择任务类型"
            style="width: 100%"
            @change="handleTaskTypeChange"
          >
            <el-option label="PT站点同步" value="pt_resource_sync" />
            <el-option label="订阅检查" value="subscription_check" />
            <el-option label="批量识别PT资源" value="pt_resource_identify" />
            <el-option label="媒体服务器库同步" value="media_server_library_sync" />
          </el-select>
        </el-form-item>

        <el-form-item label="任务名称" prop="task_name">
          <el-input v-model="form.task_name" placeholder="请输入任务名称" />
        </el-form-item>

        <!-- 调度配置（通用字段） -->
        <el-form-item label="调度类型" prop="schedule_type">
          <el-select v-model="form.schedule_type" placeholder="请选择调度类型" style="width: 100%">
            <el-option label="固定间隔" value="interval" />
            <el-option label="Cron表达式" value="cron" />
            <el-option label="手动触发" value="manual" />
          </el-select>
        </el-form-item>

        <el-form-item v-if="form.schedule_type === 'interval'" label="执行间隔">
          <el-input-number v-model="intervalValue" :min="1" :max="9999" />
          <el-select v-model="intervalUnit" style="width: 120px; margin-left: 10px">
            <el-option label="分钟" value="minutes" />
            <el-option label="小时" value="hours" />
            <el-option label="天" value="days" />
          </el-select>
        </el-form-item>

        <el-form-item v-if="form.schedule_type === 'cron'" label="Cron表达式">
          <el-input v-model="cronExpression" placeholder="例如: 0 2 * * * (每天凌晨2点)" />
          <el-text type="info" size="small">格式: 分 时 日 月 周</el-text>
        </el-form-item>

        <el-form-item label="描述">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="2"
            placeholder="任务描述(可选)"
          />
        </el-form-item>

        <el-form-item label="启用">
          <el-switch v-model="form.enabled" />
        </el-form-item>

        <!-- PT同步任务字段 -->
        <template v-if="form.task_type === 'pt_resource_sync'">
          <el-divider content-position="left">同步参数</el-divider>

          <el-form-item label="站点" prop="site_id">
            <el-select v-model="form.site_id" placeholder="请选择站点" style="width: 100%" @change="handleSiteChange">
              <el-option v-for="site in sites" :key="site.id" :label="site.name" :value="site.id" />
            </el-select>
          </el-form-item>

          <el-form-item label="同步类型" prop="sync_type">
            <el-select v-model="form.sync_type" placeholder="请选择同步类型" style="width: 100%">
              <el-option label="增量同步" value="incremental" />
              <el-option label="全量同步" value="full" />
            </el-select>
          </el-form-item>

          <el-form-item label="最大页数">
            <el-input-number v-model="form.max_pages" :min="1" :max="1000" placeholder="不限制" />
            <el-text type="info" size="small" style="margin-left: 10px">留空则不限制</el-text>
          </el-form-item>

          <el-form-item label="请求间隔">
            <el-input-number v-model="form.request_interval" :min="1" :max="60" placeholder="使用站点默认" />
            <el-text type="info" size="small" style="margin-left: 10px">秒，留空使用站点默认配置，实际会有 ±20% 随机变化</el-text>
          </el-form-item>

          <!-- 过滤参数 -->
          <el-divider content-position="left">过滤参数（可选）</el-divider>

          <!-- 资源模式：仅 MTeam 支持 -->
          <el-form-item v-if="selectedSiteSchema === 'mteam'" label="资源模式">
            <el-select v-model="form.mode" placeholder="请选择资源模式" style="width: 100%">
              <el-option label="所有资源(非成人)" value="normal" />
              <el-option label="仅电影资源" value="movie" />
              <el-option label="仅电视资源" value="tvshow" />
              <el-option label="仅成人资源" value="adult" />
            </el-select>
            <el-text type="info" size="small" style="margin-left: 10px">默认为普通资源</el-text>
          </el-form-item>

          <el-form-item label="分类">
            <el-select
              v-model="form.categories"
              placeholder="请选择分类"
              style="width: 100%"
              multiple
              collapse-tags
              collapse-tags-tooltip
              clearable
              filterable
            >
              <el-option
                v-for="cat in siteCategories"
                :key="cat.category_id"
                :label="cat.parent_id ? `  ├─ ${cat.name_chs || cat.name_eng || cat.name} (${cat.category_id})` : `${cat.name_chs || cat.name_eng || cat.name} (${cat.category_id})`"
                :value="cat.category_id"
              />
            </el-select>
            <el-text v-if="loadingCategories" type="info" size="small" style="margin-left: 10px">
              <el-icon class="is-loading"><Loading /></el-icon> 加载中...
            </el-text>
            <el-text v-else-if="siteCategories.length > 0" type="success" size="small" style="margin-left: 10px">
              已加载 {{ siteCategories.length }} 个分类
            </el-text>
            <el-text v-else-if="form.site_id" type="warning" size="small" style="margin-left: 10px">
              暂无分类数据，请先同步分类
            </el-text>
            <el-text v-else type="info" size="small" style="margin-left: 10px">
              请先选择站点
            </el-text>
            <div style="margin-top: 4px;">
              <el-text type="info" size="small">留空则同步所有分类</el-text>
            </div>
          </el-form-item>

          <!-- 时间范围：仅 MTeam 支持 -->
          <el-form-item v-if="selectedSiteSchema === 'mteam'" label="上传时间范围">
            <el-date-picker
              v-model="uploadDateRange"
              type="datetimerange"
              range-separator="至"
              start-placeholder="开始时间"
              end-placeholder="结束时间"
              format="YYYY-MM-DD HH:mm:ss"
              value-format="YYYY-MM-DD HH:mm:ss"
              style="width: 100%"
              clearable
            />
            <el-text type="info" size="small" style="margin-left: 10px">留空则不限制时间</el-text>
          </el-form-item>

          <el-form-item label="关键字">
            <el-input v-model="form.keyword" placeholder="请输入搜索关键字" clearable />
            <el-text type="info" size="small" style="margin-left: 10px">支持标题、副标题搜索</el-text>
          </el-form-item>

          <!-- 排序选项：根据站点类型显示 -->
          <el-form-item label="排序字段">
            <el-select v-model="form.sortField" placeholder="默认排序" clearable style="width: 100%">
              <!-- MTeam 排序选项 -->
              <template v-if="selectedSiteSchema === 'mteam'">
                <el-option label="发布时间" value="TIME" />
                <el-option label="做种数" value="SEEDERS" />
                <el-option label="下载数" value="LEECHERS" />
                <el-option label="文件大小" value="SIZE" />
              </template>
              <!-- NexusPHP 排序选项 -->
              <template v-else-if="selectedSiteSchema === 'nexusphp'">
                <el-option label="标题" value="1" />
                <el-option label="评论数" value="2" />
                <el-option label="存活时间" value="3" />
                <el-option label="大小" value="4" />
                <el-option label="种子数" value="5" />
                <el-option label="下载数" value="6" />
                <el-option label="完成数" value="7" />
              </template>
            </el-select>
          </el-form-item>

          <el-form-item label="排序方向">
            <el-select v-model="form.sortDirection" placeholder="选择方向" clearable style="width: 100%">
              <el-option label="降序" value="DESC" />
              <el-option label="升序" value="ASC" />
            </el-select>
          </el-form-item>
        </template>

        <!-- 订阅检查任务字段 -->
        <template v-else-if="form.task_type === 'subscription_check'">
          <el-form-item label="检查范围" prop="check_all">
            <el-radio v-model="form.check_all" :label="true">检查所有订阅</el-radio>
            <el-radio v-model="form.check_all" :label="false">检查指定订阅</el-radio>
          </el-form-item>

          <el-form-item v-if="!form.check_all" label="选择订阅" prop="subscription_ids">
            <el-select
              v-model="form.subscription_ids"
              placeholder="请选择要检查的订阅"
              style="width: 100%"
              multiple
              collapse-tags
              collapse-tags-tooltip
            >
              <el-option
                v-for="subscription in subscriptions"
                :key="subscription.id"
                :label="subscription.title"
                :value="subscription.id"
              />
            </el-select>
            <el-text type="info" size="small" style="margin-left: 10px">可选择多个订阅</el-text>
          </el-form-item>

          <el-divider content-position="left">资源同步设置</el-divider>

          <el-form-item label="同步PT资源">
            <el-switch v-model="form.sync_resources" />
            <el-text type="info" size="small" style="margin-left: 10px">
              检查前用订阅标题搜索PT站点同步新资源
            </el-text>
          </el-form-item>

          <el-form-item v-if="form.sync_resources" label="同步页数">
            <el-input-number
              v-model="form.sync_max_pages"
              :min="1"
              :max="10"
              style="width: 200px"
            />
            <el-text type="info" size="small" style="margin-left: 10px">
              每个关键字搜索的最大页数（1-10）
            </el-text>
          </el-form-item>

          <el-form-item label="自动识别">
            <el-switch v-model="form.auto_identify" />
            <el-text type="info" size="small" style="margin-left: 10px">
              同步后自动识别标题匹配的未识别资源
            </el-text>
          </el-form-item>
        </template>

        <!-- 批量识别任务字段 -->
        <template v-else-if="form.task_type === 'pt_resource_identify'">
          <el-form-item label="识别数量" prop="identify_limit">
            <el-input-number
              v-model="form.identify_limit"
              :min="1"
              :max="1000"
              placeholder="请输入识别数量"
              style="width: 100%"
            />
            <el-text type="info" size="small" style="margin-left: 10px">
              一次识别的最大资源数量（1-1000）
            </el-text>
          </el-form-item>

          <el-form-item label="资源分类">
            <el-select
              v-model="form.identify_category"
              placeholder="全部分类"
              clearable
              style="width: 100%"
            >
              <el-option label="电影" value="movie" />
              <el-option label="电视剧" value="tv" />
              <el-option label="音乐" value="music" />
              <el-option label="动漫" value="anime" />
              <el-option label="书籍" value="book" />
              <el-option label="游戏" value="game" />
              <el-option label="成人" value="adult" />
              <el-option label="其他" value="other" />
            </el-select>
            <el-text type="info" size="small" style="margin-left: 10px">
              可选，留空则识别所有分类
            </el-text>
          </el-form-item>

          <el-form-item label="PT站点">
            <el-select
              v-model="form.site_id"
              placeholder="全部站点"
              clearable
              style="width: 100%"
            >
              <el-option
                v-for="site in sites"
                :key="site.id"
                :label="site.name"
                :value="site.id"
              />
            </el-select>
            <el-text type="info" size="small" style="margin-left: 10px">
              可选，留空则识别所有站点
            </el-text>
          </el-form-item>
        </template>

        <!-- 媒体服务器库同步参数 -->
        <template v-else-if="form.task_type === 'media_server_library_sync'">
           <el-form-item label="同步模式">
            <el-radio-group v-model="form.media_sync_mode">
              <el-radio value="incremental">增量同步</el-radio>
              <el-radio value="full">全量同步</el-radio>
            </el-radio-group>
            <div style="font-size: 12px; color: #909399; margin-top: 4px;">
              {{ form.media_sync_mode === 'incremental' ? '仅同步最近修改的媒体项' : '扫描所有媒体项，确保数据完整' }}
            </div>
          </el-form-item>

          <el-form-item v-if="form.media_sync_mode === 'incremental'" label="时间范围">
            <el-select v-model="form.media_incremental_hours" style="width: 100%">
              <el-option label="最近 1 小时" :value="1" />
              <el-option label="最近 6 小时" :value="6" />
              <el-option label="最近 12 小时" :value="12" />
              <el-option label="最近 24 小时" :value="24" />
              <el-option label="最近 48 小时" :value="48" />
              <el-option label="最近 7 天" :value="168" />
            </el-select>
          </el-form-item>

          <el-form-item label="匹配文件">
            <el-switch v-model="form.media_match_files" />
            <el-text type="info" size="small" style="margin-left: 10px">同步时自动尝试匹配本地媒体文件</el-text>
          </el-form-item>
        </template>

        <!-- 演职员关系回填参数 -->
        <template v-else-if="form.task_type === 'credits_backfill'">
          <el-form-item label="处理数量">
            <el-input-number
              v-model="form.credits_limit"
              :min="1"
              :max="1000"
              style="width: 200px"
            />
            <el-text type="info" size="small" style="margin-left: 10px">
              电影和电视剧各自的处理上限
            </el-text>
          </el-form-item>

          <el-form-item label="元数据来源">
            <el-select
              v-model="form.credits_source"
              placeholder="全部来源"
              clearable
              style="width: 200px"
            >
              <el-option label="TMDB" value="tmdb" />
              <el-option label="豆瓣" value="douban" />
            </el-select>
            <el-text type="info" size="small" style="margin-left: 10px">
              留空则回填所有来源
            </el-text>
          </el-form-item>
        </template>

        <!-- 重复人物合并参数 -->
        <template v-else-if="form.task_type === 'person_merge'">
          <el-form-item label="分组数量">
            <el-input-number
              v-model="form.merge_limit"
              :min="1"
              :max="1000"
              style="width: 200px"
            />
            <el-text type="info" size="small" style="margin-left: 10px">
              每次最多处理的重复分组数
            </el-text>
          </el-form-item>

          <el-form-item label="预览模式">
            <el-switch v-model="form.merge_dry_run" />
            <el-text type="info" size="small" style="margin-left: 10px">
              开启后仅预览不实际合并
            </el-text>
          </el-form-item>
        </template>

      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>

    <!-- 任务详情抽屉 -->
    <el-drawer
      v-model="detailDrawerVisible"
      title="任务执行详情"
      :size="isMobile ? '95%' : 600"
      direction="rtl"
    >
      <div v-loading="detailLoading" class="detail-content">
        <template v-if="currentDetail">
          <!-- 基本信息 -->
          <el-descriptions title="基本信息" :column="1" border>
            <el-descriptions-item label="任务名称">{{ currentDetail.task_name }}</el-descriptions-item>
            <el-descriptions-item label="任务类型">{{ getTaskTypeName(currentDetail.task_type) }}</el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="getStatusTagType(currentDetail.status)">
                {{ getStatusName(currentDetail.status) }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="进度">
              <el-progress :percentage="currentDetail.progress" />
            </el-descriptions-item>
          </el-descriptions>

          <!-- 时间信息 -->
          <el-descriptions title="时间信息" :column="1" border style="margin-top: 20px">
            <el-descriptions-item label="创建时间">{{ formatDate(currentDetail.created_at) }}</el-descriptions-item>
            <el-descriptions-item label="计划时间">{{ formatDate(currentDetail.scheduled_at) }}</el-descriptions-item>
            <el-descriptions-item label="开始时间">{{ formatDate(currentDetail.started_at) }}</el-descriptions-item>
            <el-descriptions-item label="完成时间">{{ formatDate(currentDetail.completed_at) }}</el-descriptions-item>
            <el-descriptions-item label="耗时">{{ formatDuration(currentDetail.duration) }}</el-descriptions-item>
          </el-descriptions>

          <!-- 执行信息 -->
          <el-descriptions title="执行信息" :column="1" border style="margin-top: 20px">
            <el-descriptions-item label="优先级">{{ currentDetail.priority }}</el-descriptions-item>
            <el-descriptions-item label="重试次数">{{ currentDetail.retry_count }} / {{ currentDetail.max_retries }}</el-descriptions-item>
            <el-descriptions-item label="工作节点">{{ currentDetail.worker_id || '-' }}</el-descriptions-item>
          </el-descriptions>

          <!-- 参数 -->
          <div v-if="currentDetail.handler_params" style="margin-top: 20px">
            <h3 style="margin: 0 0 12px 0; font-size: 14px">执行参数</h3>
            <pre class="code-block">{{ JSON.stringify(currentDetail.handler_params, null, 2) }}</pre>
          </div>

          <!-- 进度详情 -->
          <div v-if="currentDetail.progress_detail" style="margin-top: 20px">
            <h3 style="margin: 0 0 12px 0; font-size: 14px">进度详情</h3>

            <!-- 步骤式进度（如果有steps） -->
            <div v-if="currentDetail.progress_detail.steps" class="steps-container">
              <el-steps
                :active="currentDetail.progress_detail.current_step"
                direction="vertical"
                finish-status="success"
                process-status="process"
              >
                <el-step
                  v-for="(step, index) in currentDetail.progress_detail.steps"
                  :key="index"
                  :title="step.name"
                  :description="step.message"
                  :status="getStepStatus(step)"
                >
                  <template #icon>
                    <el-icon v-if="step.status === 'completed'" class="step-icon-success">
                      <CircleCheck />
                    </el-icon>
                    <el-icon v-else-if="step.status === 'running'" class="step-icon-running">
                      <Loading />
                    </el-icon>
                    <el-icon v-else-if="step.status === 'failed'" class="step-icon-failed">
                      <CircleClose />
                    </el-icon>
                    <el-icon v-else class="step-icon-pending">
                      <Clock />
                    </el-icon>
                  </template>
                </el-step>
              </el-steps>
            </div>

            <!-- 批量处理进度（兼容旧格式） -->
            <div v-else-if="currentDetail.progress_detail.processed !== undefined" class="batch-progress">
              <el-descriptions :column="2" border>
                <el-descriptions-item label="总数">{{ currentDetail.progress_detail.total }}</el-descriptions-item>
                <el-descriptions-item label="已处理">{{ currentDetail.progress_detail.processed }}</el-descriptions-item>
                <el-descriptions-item label="成功">
                  <el-tag type="success">{{ currentDetail.progress_detail.success }}</el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="失败">
                  <el-tag type="danger">{{ currentDetail.progress_detail.failed }}</el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="跳过">
                  <el-tag type="info">{{ currentDetail.progress_detail.skipped }}</el-tag>
                </el-descriptions-item>
              </el-descriptions>
            </div>

            <!-- 其他格式显示为JSON（后备方案） -->
            <pre v-else class="code-block">{{ JSON.stringify(currentDetail.progress_detail, null, 2) }}</pre>
          </div>

          <!-- 执行结果 -->
          <div v-if="currentDetail.result" style="margin-top: 20px">
            <h3 style="margin: 0 0 12px 0; font-size: 14px">执行结果</h3>
            <pre class="code-block">{{ JSON.stringify(currentDetail.result, null, 2) }}</pre>
          </div>

          <!-- 错误信息 -->
          <div v-if="currentDetail.error_message" style="margin-top: 20px">
            <h3 style="margin: 0 0 12px 0; font-size: 14px; color: #f56c6c">错误信息</h3>
            <el-alert type="error" :closable="false" show-icon>
              <template #title>
                <div style="font-size: 13px">{{ currentDetail.error_message }}</div>
              </template>
              <pre v-if="currentDetail.error_detail" style="margin-top: 8px; font-size: 12px">{{ JSON.stringify(currentDetail.error_detail, null, 2) }}</pre>
            </el-alert>
          </div>

          <!-- 执行日志 -->
          <div v-if="currentDetail.logs" style="margin-top: 20px">
            <h3 style="margin: 0 0 12px 0; font-size: 14px">执行日志</h3>
            <pre class="code-block log-block">{{ currentDetail.logs }}</pre>
          </div>

          <!-- 元数据 -->
          <div v-if="currentDetail.task_metadata" style="margin-top: 20px">
            <h3 style="margin: 0 0 12px 0; font-size: 14px">任务元数据</h3>
            <pre class="code-block">{{ JSON.stringify(currentDetail.task_metadata, null, 2) }}</pre>
          </div>
        </template>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed, onUnmounted, watch, h } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, FormInstance, FormRules } from 'element-plus'
import {
  Refresh,
  Plus,
  Edit,
  Delete,
  More,
  VideoPlay,
  VideoPause,
  Close,
  Loading,
  Clock,
  CircleCheck,
  CircleClose,
  Search,
  Warning
} from '@element-plus/icons-vue'
import api from '@/api'
import {
  ScheduledTask,
  TaskQueueStatus,
  TaskTypeNames,
  ExecutionStatusNames,
  ExecutionStatus,
  PTSite,
  Subscription,
  TaskExecution
} from '@/types'

const route = useRoute()
const router = useRouter()



// ==================== 类型定义 ====================
interface ProgressStep {
  name: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  message?: string
}

interface ProgressDetail {
  steps?: ProgressStep[]
  current_step?: number
  total_steps?: number
  [key: string]: unknown
}

interface TaskExecutionWithProgress extends TaskExecution {
  progress_detail?: ProgressDetail
}

interface HistoryParams {
  page: number
  page_size: number
  sort_by: string
  sort_order: string
  status?: string
  task_type?: string
  scheduled_task_id?: number
  keyword?: string
  start_date?: string
  end_date?: string
}

interface SubscriptionCheckHandlerParams {
  check_all: boolean
  subscription_ids?: number[]
  sync_resources?: boolean
  sync_max_pages?: number
  auto_identify?: boolean
}

interface PTSyncHandlerParams {
  site_id: number
  sync_type?: string
  max_pages?: number
  request_interval?: number  // 请求间隔（秒）
  // 过滤参数
  mode?: string
  categories?: string[]
  upload_date_start?: string
  upload_date_end?: string
  keyword?: string
  sortField?: string
  sortDirection?: string
}

interface PTResourceIdentifyHandlerParams {
  limit: number
  category?: string
  site_id?: number
  skip_errors?: boolean
}

interface MediaServerLibrarySyncHandlerParams {
  sync_mode?: 'full' | 'incremental'
  incremental_hours?: number
  match_files?: boolean
}

interface TaskUpdateData {
  task_name: string
  schedule_type: string
  schedule_config?: Record<string, unknown>
  description?: string
  enabled: boolean
  handler_params?: SubscriptionCheckHandlerParams | PTSyncHandlerParams | PTResourceIdentifyHandlerParams | MediaServerLibrarySyncHandlerParams
}

// ==================== 辅助函数 ====================
const getErrorMessage = (error: unknown): string => {
  if (error instanceof Error) {
    return error.message
  }
  if (typeof error === 'string') {
    return error
  }
  return '未知错误'
}

// ==================== 状态管理 ====================
// 从路由查询参数初始化标签页，默认为 live-queue
const activeTab = ref((route.query.tab as string) || 'live-queue')

// 监听路由参数变化，同步 activeTab
watch(
  () => route.query.tab,
  (tab) => {
    if (tab && typeof tab === 'string' && activeTab.value !== tab) {
      activeTab.value = tab
    }
  }
)

// 监听 activeTab 变化，同步路由参数
watch(activeTab, (tab) => {
  if (route.query.tab !== tab) {
    router.replace({ query: { ...route.query, tab } })
  }
})
const queueLoading = ref(false)
const historyLoading = ref(false)
const tasksLoading = ref(false)
const submitting = ref(false)
const togglingId = ref<number | null>(null)
const runningId = ref<number | null>(null)
const countdown = ref(30)
const isMobile = ref(window.innerWidth <= 768)
const detailDrawerVisible = ref(false)
const detailLoading = ref(false)
const currentDetail = ref<TaskExecution | null>(null)

// 实时队列状态过滤器
const queueStatusFilter = ref('running')

// ==================== 数据 ====================
const queueStatus = reactive<TaskQueueStatus>({
  running: [],
  pending: [],
  recent_completed: []
})
const scheduledTasks = ref<ScheduledTask[]>([])
const sites = ref<PTSite[]>([])
const subscriptions = ref<Subscription[]>([])
const selectedTasks = ref<ScheduledTask[]>([])
const scheduledTasksFilters = reactive({
  task_type: '',
  keyword: ''
})

// 历史记录
const historyList = ref<TaskExecution[]>([])
const historyPagination = reactive({
  page: 1,
  page_size: 20,
  total: 0
})

// 历史记录筛选器
const historyFilters = reactive({
  status: '',
  task_type: '',
  scheduledTaskId: null as number | null,
  keyword: '',
  dateRange: null as Date[] | null
})

// ==================== 对话框 ====================
const dialogVisible = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const formRef = ref<FormInstance>()
const currentEditTask = ref<ScheduledTask | null>(null)

const form = reactive({
  task_type: 'pt_resource_sync' as 'pt_resource_sync' | 'subscription_check' | 'pt_resource_identify' | 'media_server_library_sync',
  task_name: '',
  site_id: null as number | null,
  sync_type: 'incremental',
  max_pages: null as number | null,
  request_interval: null as number | null,  // 请求间隔（秒）
  // PT同步过滤参数
  mode: 'normal',
  categories: [] as string[],
  upload_date_start: null as string | null,
  upload_date_end: null as string | null,
  keyword: '',
  sortField: '',
  sortDirection: '',
  check_all: true as boolean,
  subscription_ids: [] as number[],
  // 订阅检查任务参数
  sync_resources: false as boolean,
  sync_max_pages: 1 as number,
  auto_identify: false as boolean,
  // 批量识别任务参数
  identify_limit: 100,
  identify_category: '' as string,
  // 媒体服务器同步参数
  media_sync_mode: 'incremental' as 'full' | 'incremental',
  media_incremental_hours: 24,
  media_match_files: true,
  // 演职员关系回填参数
  credits_limit: 100,
  credits_source: '' as string,
  // 重复人物合并参数
  merge_limit: 100,
  merge_dry_run: false,
  schedule_type: 'interval',
  description: '',
  enabled: true
})

const intervalValue = ref(6)
const intervalUnit = ref('hours')
const cronExpression = ref('0 2 * * *')
const uploadDateRange = ref<[string, string] | null>(null)

// 动态表单验证规则
const rules = computed<FormRules>(() => {
  const baseRules = {
    task_type: [{ required: true, message: '请选择任务类型', trigger: 'change' }],
    task_name: [{ required: true, message: '请输入任务名称', trigger: 'blur' }],
    schedule_type: [{ required: true, message: '请选择调度类型', trigger: 'change' }],
  }

  if (form.task_type === 'pt_resource_sync') {
    return {
      ...baseRules,
      site_id: [{ required: true, message: '请选择站点', trigger: 'change' }],
      sync_type: [{ required: true, message: '请选择同步类型', trigger: 'change' }],
    }
  } else if (form.task_type === 'subscription_check') {
    return {
      ...baseRules,
      check_all: [{ required: true, message: '请选择检查范围', trigger: 'change' }],
      subscription_ids: [
        {
          required: !form.check_all,
          message: '请选择至少一个订阅',
          trigger: 'change',
          type: 'array',
          min: 1,
        },
      ],
    }
  }

  return baseRules
})

// ==================== 计算属性 ====================

// 选中站点的 schema 类型（用于动态显示过滤参数）
// mteam = MTeam 站点（支持模式、时间范围、排序）
// 其他 = NexusPHP 站点（支持排序）
const selectedSiteSchema = computed(() => {
  if (!form.site_id) return null
  const site = sites.value.find(s => s.id === form.site_id)
  if (!site) return null
  // type 就是 preset_id（如 mteam, hdsky, chdbits 等）
  const siteType = site.type?.toLowerCase() || ''
  if (siteType === 'mteam') {
    return 'mteam'
  }
  // 其他所有站点都是 NexusPHP
  return 'nexusphp'
})

// 实时队列：根据过滤器显示的任务
const displayQueueTasks = computed(() => {
  if (queueStatusFilter.value === 'running') {
    return queueStatus.running
  } else if (queueStatusFilter.value === 'pending') {
    return queueStatus.pending
  } else if (queueStatusFilter.value === 'recent_completed') {
    return queueStatus.recent_completed
  }
  return []
})

// ==================== 辅助函数 ====================
const getTaskTypeName = (type: string) => TaskTypeNames[type as keyof typeof TaskTypeNames] || type
const getStatusName = (status: string) => {
  if (status === 'success') return '已完成'
  return ExecutionStatusNames[status as keyof typeof ExecutionStatusNames] || status
}

const getStepStatus = (step: ProgressStep) => {
  if (step.status === 'completed') return 'success'
  if (step.status === 'running') return 'process'
  if (step.status === 'failed') return 'error'
  return 'wait'
}

// 获取当前执行的步骤名称
const getCurrentStepName = (row: TaskExecutionWithProgress) => {
  if (!row.progress_detail?.steps) return ''

  const steps = row.progress_detail.steps
  const currentStepIndex = row.progress_detail.current_step || 0

  // 优先返回当前运行中的步骤
  const runningStep = steps.find((s) => s.status === 'running')
  if (runningStep) return runningStep.name

  // 否则返回 current_step 索引对应的步骤
  if (currentStepIndex < steps.length) {
    return steps[currentStepIndex].name
  }

  // 最后返回最后一个完成的步骤
  const lastCompletedStep = steps.filter((s) => s.status === 'completed').pop()
  return lastCompletedStep?.name || steps[0]?.name || ''
}

// 获取当前步骤的状态
const getCurrentStepStatus = (row: TaskExecutionWithProgress) => {
  if (!row.progress_detail?.steps) return 'pending'

  const steps = row.progress_detail.steps
  const runningStep = steps.find((s) => s.status === 'running')
  if (runningStep) return 'running'

  const currentStepIndex = row.progress_detail.current_step || 0
  if (currentStepIndex < steps.length) {
    return steps[currentStepIndex].status
  }

  return 'pending'
}

const getDialogTitle = () => {
  if (dialogMode.value === 'create') {
    const taskTypeName = {
      'pt_resource_sync': 'PT同步',
      'subscription_check': '订阅检查',
      'pt_resource_identify': 'PT识别',
      'media_server_library_sync': '媒体库同步'
    }[form.task_type] || '通用'
    return `创建${taskTypeName}任务`
  } else {
    return '编辑任务'
  }
}



const getStatusTagType = (status: string): 'success' | 'danger' | 'warning' | 'primary' | 'info' => {
  switch (status) {
    case ExecutionStatus.COMPLETED:
    case 'success':
      return 'success'
    case ExecutionStatus.FAILED:
    case 'failed':
      return 'danger'
    case ExecutionStatus.CANCELLED:
    case 'cancelled':
      return 'warning'
    case ExecutionStatus.RUNNING:
    case 'running':
      return 'primary'
    default:
      return 'info'
  }
}

const getProgressColor = (percentage: number) => {
  if (percentage < 30) return '#f56c6c'
  if (percentage < 70) return '#e6a23c'
  return '#67c23a'
}

const getTaskTypeColor = (type: string): 'primary' | 'success' | 'warning' | 'info' | 'danger' => {
  const colorMap: Record<string, 'primary' | 'success' | 'warning' | 'info' | 'danger'> = {
    'pt_resource_sync': 'primary',
    'pt_resource_identify': 'success',
    'subscription_check': 'warning',
    'media_file_scan': 'info',
    'download_create': 'danger',
    'media_server_watch_history_sync': 'primary',
    'media_server_library_stats_update': 'success',
    'media_server_library_sync': 'warning',
    'trending_sync': 'info',
    'trending_detail_sync': 'info',
    'credits_backfill': 'warning',
    'person_merge': 'success',
    // 旧格式兼容
    'pt_sync': 'primary',
    'batch_identify': 'success',
    'scan_media': 'info'
  }
  return colorMap[type] || 'info'
}

const getScheduleDescription = (task: ScheduledTask) => {
  if (task.schedule_type === 'manual') {
    return '手动触发'
  }
  if (task.schedule_type === 'interval' && task.schedule_config) {
    const interval = task.schedule_config.interval
    const unit = task.schedule_config.unit || 'seconds'
    if (unit === 'hours' || (unit === 'seconds' && interval >= 3600)) {
      const hours = unit === 'hours' ? interval : interval / 3600
      return `每 ${hours} 小时`
    } else if (unit === 'minutes' || (unit === 'seconds' && interval >= 60)) {
      const minutes = unit === 'minutes' ? interval : interval / 60
      return `每 ${minutes} 分钟`
    } else if (unit === 'days') {
      return `每 ${interval} 天`
    }
    return `每 ${interval} 秒`
  }
  if (task.schedule_type === 'cron' && task.schedule_config) {
    return `Cron: ${task.schedule_config.cron}`
  }
  return '未配置'
}

const siteCategories = ref<any[]>([])
const loadingCategories = ref(false)

// 按父分类排序分类列表
const sortCategoriesByParent = (categories: any[]) => {
  if (!categories || categories.length === 0) return []

  // 分离父分类和子分类
  const parentCategories = categories.filter(cat => !cat.parent_id)
  const childCategories = categories.filter(cat => cat.parent_id)

  // 按 order 字段排序父分类
  parentCategories.sort((a, b) => (a.order || 0) - (b.order || 0))

  // 构建排序后的数组
  const sorted: any[] = []
  parentCategories.forEach(parent => {
    // 添加父分类
    sorted.push(parent)

    // 找出该父分类下的所有子分类
    const children = childCategories
      .filter(child => child.parent_id === parent.category_id)
      .sort((a, b) => (a.order || 0) - (b.order || 0))

    // 添加子分类
    sorted.push(...children)
  })

  // 添加没有父分类的孤立子分类（如果有的话）
  const orphanChildren = childCategories.filter(
    child => !parentCategories.find(p => p.category_id === child.parent_id)
  )
  sorted.push(...orphanChildren)

  return sorted
}

// 站点预设缓存（避免重复请求）
const sitePresetsCache = ref<Map<string, any>>(new Map())

// 分类列表缓存（存储转换后的数组）
const categoryListCache = ref<Map<string, any[]>>(new Map())

// 从预设配置加载 NexusPHP 分类
const loadCategoriesFromPreset = async (site: PTSite) => {
  const presetId = site.type // type 就是 preset_id
  if (!presetId) return []

  // 检查分类列表缓存（存储的是转换后的数组）
  if (categoryListCache.value.has(presetId)) {
    return categoryListCache.value.get(presetId) || []
  }

  try {
    // 获取站点预设详情（包含 categories）
    const res = await api.site.getSitePresetDetail(presetId)
    const preset = res.data as any

    // 缓存预设数据（用于其他用途）
    sitePresetsCache.value.set(presetId, preset)

    // 将 preset.categories 转换为分类列表格式
    const categories = preset.categories || {}
    const categoryList: any[] = []

    for (const [catId, mediaType] of Object.entries(categories)) {
      // 根据媒体类型获取中文名称
      const mediaTypeNames: Record<string, string> = {
        movie: '电影',
        tv: '剧集',
        anime: '动漫',
        music: '音乐',
        other: '其他',
        game: '游戏',
        book: '书籍'
      }

      categoryList.push({
        category_id: catId,
        name_chs: mediaTypeNames[mediaType as string] || mediaType,
        name_eng: mediaType,
        name: mediaType,
        parent_id: null,
        order: 0
      })
    }

    // 按中文名称排序
    categoryList.sort((a, b) => a.name_chs.localeCompare(b.name_chs, 'zh-CN'))

    // 缓存转换后的分类列表
    categoryListCache.value.set(presetId, categoryList)

    return categoryList
  } catch (e) {
    console.error('Failed to fetch preset categories:', e)
    return []
  }
}

const fetchSiteCategories = async (siteId: number) => {
  if (!siteId) {
    siteCategories.value = []
    return
  }

  const site = sites.value.find(s => s.id === siteId)
  if (!site) {
    siteCategories.value = []
    return
  }

  loadingCategories.value = true
  try {
    let categories: any[] = []

    // 统一从数据库加载分类（MTeam 和 NexusPHP 都在创建站点时自动同步分类）
    const res = await api.site.getSiteCategories(siteId)
    const data = res.data as any

    if (data && Array.isArray(data.categories)) {
      categories = data.categories
    } else if (Array.isArray(data)) {
      categories = data
    }

    // 按父分类排序
    siteCategories.value = sortCategoriesByParent(categories)

    console.log('Loaded categories:', siteCategories.value.length)
  } catch (e) {
    console.error('Failed to fetch categories', e)
    siteCategories.value = []
  } finally {
    loadingCategories.value = false
  }
}

// 监听站点变化加载分类
watch(() => form.site_id, (newId, oldId) => {
  console.log('Site ID changed:', oldId, '->', newId)
  if (newId) {
    fetchSiteCategories(newId)
  } else {
    siteCategories.value = []
  }
})

// 编辑模式下初始化（对话框打开时如果已有站点ID则加载分类）
watch(() => dialogVisible.value, (val) => {
  if (val) {
    console.log('Dialog opened, site_id:', form.site_id)
    if (form.site_id) {
      fetchSiteCategories(form.site_id)
    } else {
      // 清空分类列表
      siteCategories.value = []
    }
  }
})

// 站点变化处理函数（watch 已处理分类加载，这里主要用于显式触发）
const handleSiteChange = () => {
  // watch 已经处理了站点变化和分类加载
  // 这里可以添加额外的站点变化处理逻辑
  console.log('Site changed, schema:', selectedSiteSchema.value)
}

// 监听排序字段变化，自动设置排序方向
watch(() => form.sortField, (newField, oldField) => {
  // 当选择了排序字段且排序方向为空时，自动设置为降序
  if (newField && !form.sortDirection) {
    form.sortDirection = 'DESC'
  }
  // 当清空排序字段时，也清空排序方向
  if (!newField) {
    form.sortDirection = ''
  }
})

const formatDate = (dateStr: string | undefined) => {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    timeZone: 'Asia/Shanghai'
  })
}

const formatDuration = (duration: number | null | undefined) => {
  if (!duration || duration <= 0) return '-'
  if (duration < 60) return `${duration}秒`
  if (duration < 3600) return `${Math.floor(duration / 60)}分${duration % 60}秒`
  return `${Math.floor(duration / 3600)}时${Math.floor((duration % 3600) / 60)}分`
}

// ==================== 数据加载 ====================
const loadQueueStatus = async () => {
  queueLoading.value = true
  try {
    const { data } = await api.task.getTaskQueueStatus()
    queueStatus.running = data.running
    queueStatus.pending = data.pending
    queueStatus.recent_completed = data.recent_completed
  } catch (error: unknown) {
    ElMessage.error('加载任务队列状态失败: ' + (getErrorMessage(error)))
  } finally {
    queueLoading.value = false
  }
}

const loadScheduledTasks = async () => {
  tasksLoading.value = true
  try {
    const params: any = { limit: 100 }
    if (scheduledTasksFilters.task_type) {
      params.task_type = scheduledTasksFilters.task_type
    }
    if (scheduledTasksFilters.keyword) {
      params.keyword = scheduledTasksFilters.keyword
    }
    const { data } = await api.task.getScheduledTasks(params)
    scheduledTasks.value = data.items.map((task) => ({
      ...task,
      success_rate:
        task.total_runs > 0 ? Math.round((task.success_runs / task.total_runs) * 100) : 0
    }))
  } catch (error: unknown) {
    ElMessage.error('加载调度任务失败: ' + (getErrorMessage(error)))
  } finally {
    tasksLoading.value = false
  }
}

const loadSites = async () => {
  try {
    const { data } = await api.site.getSiteList({ page: 1, page_size: 100, sync_enabled: true })
    sites.value = data.items
  } catch (error: unknown) {
    console.error('加载站点列表失败:', error)
  }
}

const loadSubscriptions = async () => {
  try {
    const res = await api.subscription.getSubscriptionList({ page: 1, pageSize: 100, is_active: true })
    subscriptions.value = res.data.items || []
  } catch (error: unknown) {
    console.error('加载订阅列表失败:', error)
  }
}

const handleTaskTypeChange = (taskType: 'pt_resource_sync' | 'subscription_check' | 'pt_resource_identify' | 'media_server_library_sync') => {
  // 切换任务类型时,清除相关字段的验证状态
  formRef.value?.clearValidate()

  // 重置任务特定字段
  if (taskType === 'pt_resource_sync') {
    form.check_all = true
    form.subscription_ids = []
    // 清空批量识别字段
    form.identify_limit = 100
    form.identify_category = ''
  } else if (taskType === 'subscription_check') {
    form.site_id = null
    form.sync_type = 'incremental'
    form.max_pages = null
    form.mode = 'normal'
    form.categories = []
    form.keyword = ''
    uploadDateRange.value = null
    siteCategories.value = []
    // 清空批量识别字段
    form.identify_limit = 100
    form.identify_category = ''
  } else if (taskType === 'pt_resource_identify') {
    form.sync_type = 'incremental'
    form.max_pages = null
    form.mode = 'normal'
    form.categories = []
    form.keyword = ''
    uploadDateRange.value = null
    form.check_all = true
    form.subscription_ids = []
  } else if (taskType === 'media_server_library_sync') {
    // 默认任务名称
    if (!form.task_name || form.task_name.includes('同步') || form.task_name.includes('识别') || form.task_name.includes('订阅')) {
      form.task_name = '自动媒体库同步'
    }
    // 重置其他字段
    form.check_all = true
    form.subscription_ids = []
    form.identify_limit = 100
    form.identify_category = ''
    form.site_id = null
  }
}

const loadHistory = async () => {
  historyLoading.value = true
  try {
    const params: HistoryParams = {
      page: historyPagination.page,
      page_size: historyPagination.page_size,
      sort_by: 'created_at',
      sort_order: 'desc'
    }

    // 应用筛选器
    if (historyFilters.status) {
      params.status = historyFilters.status
    }
    if (historyFilters.task_type) {
      params.task_type = historyFilters.task_type
    }
    if (historyFilters.scheduledTaskId) {
      params.scheduled_task_id = historyFilters.scheduledTaskId
    }
    if (historyFilters.keyword) {
      params.keyword = historyFilters.keyword
    }
    if (historyFilters.dateRange && historyFilters.dateRange.length === 2) {
      params.start_date = historyFilters.dateRange[0].toISOString()
      params.end_date = historyFilters.dateRange[1].toISOString()
    }

    const { data } = await api.task.getTaskExecutionsList(params)
    historyList.value = data.items
    historyPagination.total = data.total
  } catch (error: unknown) {
    ElMessage.error('加载历史记录失败: ' + (getErrorMessage(error)))
  } finally {
    historyLoading.value = false
  }
}

const resetHistoryFilters = () => {
  historyFilters.status = ''
  historyFilters.task_type = ''
  historyFilters.scheduledTaskId = null
  historyFilters.keyword = ''
  historyFilters.dateRange = null
  historyPagination.page = 1
  loadHistory()
}

// ==================== 事件处理 ====================
const handleSelectionChange = (selection: ScheduledTask[]) => {
  selectedTasks.value = selection
}

const handleCreate = () => {
  dialogMode.value = 'create'
  currentEditTask.value = null
  resetForm()
  dialogVisible.value = true
}

const handleEdit = (task: ScheduledTask) => {
  dialogMode.value = 'edit'
  currentEditTask.value = task

  // 填充表单
  form.task_type = task.task_type as 'pt_resource_sync' | 'subscription_check' | 'pt_resource_identify' | 'media_server_library_sync'
  form.task_name = task.task_name
  form.schedule_type = task.schedule_type
  form.description = task.description || ''
  form.enabled = task.enabled

  // 根据任务类型填充特定字段(支持新旧两种格式)
  if (task.task_type === 'pt_resource_sync' || task.task_type === 'pt_sync') {
    form.task_type = 'pt_resource_sync'  // 统一为新格式
    form.site_id = task.handler_params?.site_id || null
    form.sync_type = task.handler_params?.sync_type || 'incremental'
    form.max_pages = task.handler_params?.max_pages || null
    form.request_interval = task.handler_params?.request_interval || null
    form.check_all = true
    form.subscription_ids = []

    // 填充过滤参数
    form.mode = task.handler_params?.mode || 'normal'
    form.categories = task.handler_params?.categories || []
    form.keyword = task.handler_params?.keyword || ''
    form.sortField = task.handler_params?.sortField || ''
    form.sortDirection = task.handler_params?.sortDirection || ''

    // 填充上传时间范围
    if (task.handler_params?.upload_date_start && task.handler_params?.upload_date_end) {
      uploadDateRange.value = [
        task.handler_params.upload_date_start,
        task.handler_params.upload_date_end
      ]
    } else {
      uploadDateRange.value = null
    }
  } else if (task.task_type === 'subscription_check') {
    form.site_id = null
    form.sync_type = 'incremental'
    form.max_pages = null
    form.request_interval = null
    form.check_all = task.handler_params?.check_all ?? true
    form.subscription_ids = task.handler_params?.subscription_ids || []
    // 填充新增的订阅检查参数
    form.sync_resources = task.handler_params?.sync_resources ?? false
    form.sync_max_pages = task.handler_params?.sync_max_pages ?? 1
    form.auto_identify = task.handler_params?.auto_identify ?? false

    // 清空PT同步专用字段
    form.mode = 'normal'
    form.categories = []
    form.keyword = ''
    uploadDateRange.value = null
  } else if (task.task_type === 'pt_resource_identify') {
    // 填充批量识别任务参数
    form.identify_limit = task.handler_params?.limit || 100
    form.identify_category = task.handler_params?.category || ''
    form.site_id = task.handler_params?.site_id || null

    // 清空其他任务专用字段
    form.sync_type = 'incremental'
    form.max_pages = null
    form.request_interval = null
    form.check_all = true
    form.subscription_ids = []
    form.categories = []
    form.keyword = ''
    uploadDateRange.value = null
  } else if (task.task_type === 'media_server_library_sync') {
    // 填充媒体服务器同步参数
    form.media_sync_mode = task.handler_params?.sync_mode || 'incremental'
    form.media_incremental_hours = task.handler_params?.incremental_hours || 24
    form.media_match_files = task.handler_params?.match_files ?? true

    // 清空其他任务专用字段
    form.site_id = null
    form.sync_type = 'incremental'
    form.max_pages = null
    form.request_interval = null
    form.check_all = true
    form.subscription_ids = []
    form.mode = 'normal'
    form.categories = []
    form.keyword = ''
    uploadDateRange.value = null
  } else if (task.task_type === 'credits_backfill') {
    form.credits_limit = task.handler_params?.limit || 100
    form.credits_source = task.handler_params?.source || ''
  } else if (task.task_type === 'person_merge') {
    form.merge_limit = task.handler_params?.limit || 100
    form.merge_dry_run = task.handler_params?.dry_run ?? false
  }

  // 解析调度配置
  if (task.schedule_type === 'interval' && task.schedule_config) {
    intervalUnit.value = task.schedule_config.unit || 'seconds'
    intervalValue.value = task.schedule_config.interval || 6
    if (intervalUnit.value === 'seconds') {
      if (intervalValue.value >= 86400 && intervalValue.value % 86400 === 0) {
        intervalUnit.value = 'days'
        intervalValue.value = intervalValue.value / 86400
      } else if (intervalValue.value >= 3600 && intervalValue.value % 3600 === 0) {
        intervalUnit.value = 'hours'
        intervalValue.value = intervalValue.value / 3600
      } else if (intervalValue.value >= 60 && intervalValue.value % 60 === 0) {
        intervalUnit.value = 'minutes'
        intervalValue.value = intervalValue.value / 60
      }
    }
  }
  if (task.schedule_type === 'cron' && task.schedule_config) {
    cronExpression.value = task.schedule_config.cron || '0 2 * * *'
  }

  dialogVisible.value = true
}

const handleDelete = async (task: ScheduledTask) => {
  try {
    await ElMessageBox.confirm('', '删除确认', {
      confirmButtonText: '确定删除',
      cancelButtonText: '取消',
      type: 'warning',
      message: h('div', null, [
        h('p', { style: 'margin-bottom: 8px; font-weight: 500;' }, `确定要删除任务 "${task.task_name}" 吗？`),
        h('p', { style: 'font-size: 13px; color: #909399;' }, `任务名称: ${task.task_name}`),
        h(
          'p',
          { style: 'font-size: 13px; color: #909399;' },
          `任务类型: ${getTaskTypeName(task.task_type)}`
        ),
        h(
          'p',
          { style: 'color: #f56c6c; margin-top: 12px; font-size: 13px;' },
          '⚠️ 删除后无法恢复，但执行历史会保留'
        )
      ])
    })

    await api.task.deleteScheduledTask(task.id)
    ElMessage.success('删除成功')
    await loadScheduledTasks()
  } catch (error: unknown) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败: ' + (getErrorMessage(error)))
    }
  }
}

const handleToggleTask = async (task: ScheduledTask) => {
  togglingId.value = task.id
  try {
    await api.task.toggleScheduledTask(task.id)
    ElMessage.success(task.enabled ? '任务已启用' : '任务已禁用')
    await loadScheduledTasks()
  } catch (error: unknown) {
    ElMessage.error('切换状态失败: ' + (getErrorMessage(error)))
    task.enabled = !task.enabled
  } finally {
    togglingId.value = null
  }
}

const handleRunNow = async (task: ScheduledTask) => {
  runningId.value = task.id
  try {
    const { data } = await api.task.runScheduledTaskNow(task.id)
    ElMessage.success(data.message || '任务已提交执行')
    setTimeout(() => loadQueueStatus(), 1000)
  } catch (error: unknown) {
    ElMessage.error('执行失败: ' + (getErrorMessage(error)))
  } finally {
    runningId.value = null
  }
}

const handleCancelExecution = async (executionId: number) => {
  try {
    await ElMessageBox.confirm('确定要取消该任务吗？', '取消确认', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    await api.task.cancelTaskExecution(executionId)
    ElMessage.success('任务已取消')

    // 刷新队列状态
    await loadQueueStatus()
  } catch (error: unknown) {
    if (error !== 'cancel') {
      ElMessage.error('取消失败: ' + (getErrorMessage(error)))
    }
  }
}

const handleViewHistory = (task: ScheduledTask) => {
  // 重置历史筛选器
  resetHistoryFilters()
  // 设置特定任务筛选
  historyFilters.scheduledTaskId = task.id
  // 切换 activeTab 会触发 watch，从而更新 URL
  activeTab.value = 'history'
  // 加载数据
  loadHistory()
}

const handleViewDetail = async (executionId: number) => {
  detailDrawerVisible.value = true
  detailLoading.value = true
  try {
    const { data } = await api.task.getTaskExecution(executionId)
    currentDetail.value = data
  } catch (error: unknown) {
    ElMessage.error('加载任务详情失败: ' + (getErrorMessage(error)))
    detailDrawerVisible.value = false
  } finally {
    detailLoading.value = false
  }
}

const handleSubmit = async () => {
  if (!formRef.value) return
  await formRef.value.validate()

  submitting.value = true
  try {
    let schedule_config: Record<string, unknown> | undefined
    if (form.schedule_type === 'interval') {
      schedule_config = {
        interval: intervalValue.value,
        unit: intervalUnit.value
      }
    } else if (form.schedule_type === 'cron') {
      schedule_config = {
        cron: cronExpression.value,
        timezone: 'Asia/Shanghai'
      }
    }

    if (dialogMode.value === 'create') {
      // 根据任务类型创建不同的任务
      if (form.task_type === 'pt_resource_sync') {
        await api.task.createPTSyncTask({
          task_name: form.task_name,
          site_id: form.site_id!,
          schedule_type: form.schedule_type,
          schedule_config,
          sync_type: form.sync_type,
          max_pages: form.max_pages || undefined,
          request_interval: form.request_interval || undefined,
          description: form.description || undefined,
          enabled: form.enabled,
          // 过滤参数
          mode: form.mode || undefined,
          categories: form.categories.length > 0 ? form.categories : undefined,
          upload_date_start: uploadDateRange.value?.[0] || undefined,
          upload_date_end: uploadDateRange.value?.[1] || undefined,
          keyword: form.keyword || undefined,
          sortField: form.sortField || undefined,
          sortDirection: form.sortDirection || undefined
        })
      } else if (form.task_type === 'subscription_check') {
        // 构建订阅检查任务参数
        const handler_params: SubscriptionCheckHandlerParams = {
          check_all: form.check_all,
          sync_resources: form.sync_resources,
          sync_max_pages: form.sync_max_pages,
          auto_identify: form.auto_identify
        }
        if (!form.check_all && form.subscription_ids.length > 0) {
          handler_params.subscription_ids = form.subscription_ids
        }

        await api.task.createScheduledTask({
          task_type: form.task_type,
          task_name: form.task_name,
          schedule_type: form.schedule_type,
          schedule_config,
          handler: 'subscription_check',
          handler_params,
          description: form.description || undefined,
          enabled: form.enabled
        })
      } else if (form.task_type === 'pt_resource_identify') {
        // 构建批量识别任务参数
        const handler_params: PTResourceIdentifyHandlerParams = {
          limit: form.identify_limit,
          skip_errors: true
        }
        if (form.identify_category) {
          handler_params.category = form.identify_category
        }
        if (form.site_id) {
          handler_params.site_id = form.site_id
        }

        await api.task.createScheduledTask({
          task_type: form.task_type,
          task_name: form.task_name,
          schedule_type: form.schedule_type,
          schedule_config,
          handler: 'pt_resource_identify',
          handler_params,
          description: form.description || undefined,
          enabled: form.enabled
        })
      } else if (form.task_type === 'media_server_library_sync') {
        // 构建媒体服务器同步参数
        const handler_params: MediaServerLibrarySyncHandlerParams = {
          sync_mode: form.media_sync_mode,
          incremental_hours: form.media_sync_mode === 'incremental' ? form.media_incremental_hours : undefined,
          match_files: form.media_match_files
        }

        await api.task.createScheduledTask({
          task_type: form.task_type,
          task_name: form.task_name,
          schedule_type: form.schedule_type,
          schedule_config,
          handler: 'media_server_library_sync',
          handler_params,
          description: form.description || undefined,
          enabled: form.enabled
        })
      }
      ElMessage.success('创建成功')
    } else {
      // 更新任务
      const updateData: TaskUpdateData = {
        task_name: form.task_name,
        schedule_type: form.schedule_type,
        schedule_config,
        description: form.description,
        enabled: form.enabled,
      }

      // 根据任务类型设置不同的handler_params
      if (form.task_type === 'pt_resource_sync') {
        const ptParams: PTSyncHandlerParams = {
          site_id: form.site_id!,
          sync_type: form.sync_type
        }
        if (form.max_pages) {
          ptParams.max_pages = form.max_pages
        }
        if (form.request_interval) {
          ptParams.request_interval = form.request_interval
        }
        // 过滤参数
        if (form.mode) {
          ptParams.mode = form.mode
        }
        if (form.categories.length > 0) {
          ptParams.categories = form.categories
        }
        if (uploadDateRange.value?.[0]) {
          ptParams.upload_date_start = uploadDateRange.value[0]
        }
        if (uploadDateRange.value?.[1]) {
          ptParams.upload_date_end = uploadDateRange.value[1]
        }
        if (form.keyword) {
          ptParams.keyword = form.keyword
        }
        if (form.sortField) {
          ptParams.sortField = form.sortField
        }
        if (form.sortDirection) {
          ptParams.sortDirection = form.sortDirection
        }
        updateData.handler_params = ptParams
      } else if (form.task_type === 'subscription_check') {
        const subParams: SubscriptionCheckHandlerParams = {
          check_all: form.check_all,
          sync_resources: form.sync_resources,
          sync_max_pages: form.sync_max_pages,
          auto_identify: form.auto_identify
        }
        if (!form.check_all && form.subscription_ids.length > 0) {
          subParams.subscription_ids = form.subscription_ids
        }
        updateData.handler_params = subParams
      } else if (form.task_type === 'pt_resource_identify') {
        const identifyParams: PTResourceIdentifyHandlerParams = {
          limit: form.identify_limit,
          skip_errors: true
        }
        if (form.identify_category) {
          identifyParams.category = form.identify_category
        }
        if (form.site_id) {
          identifyParams.site_id = form.site_id
        }
        updateData.handler_params = identifyParams
      } else if (form.task_type === 'media_server_library_sync') {
        const mediaParams: MediaServerLibrarySyncHandlerParams = {
          sync_mode: form.media_sync_mode,
          incremental_hours: form.media_sync_mode === 'incremental' ? form.media_incremental_hours : undefined,
          match_files: form.media_match_files
        }
        updateData.handler_params = mediaParams
      } else if (form.task_type === 'credits_backfill') {
        const creditsParams: Record<string, any> = {
          limit: form.credits_limit
        }
        if (form.credits_source) {
          creditsParams.source = form.credits_source
        }
        updateData.handler_params = creditsParams
      } else if (form.task_type === 'person_merge') {
        updateData.handler_params = {
          limit: form.merge_limit,
          dry_run: form.merge_dry_run
        }
      }

      await api.task.updateScheduledTask(currentEditTask.value!.id, updateData)
      ElMessage.success('更新成功')
    }

    dialogVisible.value = false
    await loadScheduledTasks()
  } catch (error: unknown) {
    ElMessage.error(
      (dialogMode.value === 'create' ? '创建' : '更新') + '失败: ' + (getErrorMessage(error))
    )
  } finally {
    submitting.value = false
  }
}

const handleDialogClose = () => {
  resetForm()
}

const resetForm = () => {
  form.task_type = 'pt_resource_sync'
  form.task_name = ''
  form.site_id = null
  form.sync_type = 'incremental'
  form.max_pages = null
  form.request_interval = null
  // 重置过滤参数
  form.mode = 'normal'
  form.categories = []
  form.keyword = ''
  form.sortField = ''
  form.sortDirection = ''
  uploadDateRange.value = null
  form.check_all = true
  form.subscription_ids = []
  // 重置订阅检查任务参数
  form.sync_resources = false
  form.sync_max_pages = 1
  form.auto_identify = false
  // 重置批量识别参数
  form.identify_limit = 100
  form.identify_category = ''
  // 重置媒体服务器同步参数
  form.media_sync_mode = 'incremental'
  form.media_incremental_hours = 24
  form.media_match_files = true
  form.schedule_type = 'interval'
  form.description = ''
  form.enabled = true
  intervalValue.value = 6
  intervalUnit.value = 'hours'
  cronExpression.value = '0 2 * * *'
  formRef.value?.resetFields()
}

// ==================== 批量操作 ====================
const batchEnable = async () => {
  try {
    await ElMessageBox.confirm(
      `确定要启用选中的 ${selectedTasks.value.length} 个任务吗？`,
      '批量启用',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'info'
      }
    )

    for (const task of selectedTasks.value) {
      if (!task.enabled) {
        await api.task.toggleScheduledTask(task.id)
      }
    }
    ElMessage.success('批量启用成功')
    await loadScheduledTasks()
    selectedTasks.value = []
  } catch (error: unknown) {
    if (error !== 'cancel') {
      ElMessage.error('批量启用失败: ' + (getErrorMessage(error)))
    }
  }
}

const batchDisable = async () => {
  try {
    await ElMessageBox.confirm(
      `确定要禁用选中的 ${selectedTasks.value.length} 个任务吗？`,
      '批量禁用',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    for (const task of selectedTasks.value) {
      if (task.enabled) {
        await api.task.toggleScheduledTask(task.id)
      }
    }
    ElMessage.success('批量禁用成功')
    await loadScheduledTasks()
    selectedTasks.value = []
  } catch (error: unknown) {
    if (error !== 'cancel') {
      ElMessage.error('批量禁用失败: ' + (getErrorMessage(error)))
    }
  }
}

const batchDelete = async () => {
  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedTasks.value.length} 个任务吗？此操作不可恢复！`,
      '批量删除',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'error'
      }
    )

    for (const task of selectedTasks.value) {
      await api.task.deleteScheduledTask(task.id)
    }
    ElMessage.success('批量删除成功')
    await loadScheduledTasks()
    selectedTasks.value = []
  } catch (error: unknown) {
    if (error !== 'cancel') {
      ElMessage.error('批量删除失败: ' + (getErrorMessage(error)))
    }
  }
}

// ==================== 自动刷新和倒计时 ====================
let refreshInterval: number | null = null
let countdownInterval: number | null = null

const startCountdown = () => {
  countdown.value = 30
  countdownInterval = window.setInterval(() => {
    countdown.value--
    if (countdown.value <= 0) {
      countdown.value = 30
    }
  }, 1000)
}

// 监听路由变化，同步标签页状态
watch(
  () => route.query.tab,
  (newTab) => {
    if (newTab && typeof newTab === 'string' && newTab !== activeTab.value) {
      activeTab.value = newTab
      // 根据标签页加载对应数据
      if (newTab === 'live-queue') {
        loadQueueStatus()
      } else if (newTab === 'history') {
        loadHistory()
      } else if (newTab === 'scheduled') {
        loadScheduledTasks()
      }
    }
  }
)

// ==================== 监听标签页切换（保留原有逻辑作为后备） ====================
watch(activeTab, (newTab) => {
  // 这个watcher现在主要处理程序内部触发的tab变化
  // URL变化已经由上面的route watcher处理
  if (newTab === 'live-queue') {
    loadQueueStatus()
  } else if (newTab === 'history') {
    loadHistory()
  } else if (newTab === 'scheduled') {
    loadScheduledTasks()
  }
})

const handleMobileResize = () => {
  isMobile.value = window.innerWidth <= 768
}

onMounted(() => {
  // 设置页面标题
  document.title = '任务管理 - NasFusion'
  window.addEventListener('resize', handleMobileResize)

  // 初始加载当前标签页的数据
  if (activeTab.value === 'live-queue') {
    loadQueueStatus()
  } else if (activeTab.value === 'history') {
    loadHistory()
  } else if (activeTab.value === 'scheduled') {
    loadScheduledTasks()
  }

  // 加载站点列表（用于创建任务）
  loadSites()
  // 加载订阅列表（用于创建任务）
  loadSubscriptions()

  // 每30秒自动刷新队列状态（仅当在实时队列标签页时）
  refreshInterval = window.setInterval(() => {
    if (activeTab.value === 'live-queue') {
      loadQueueStatus()
    }
  }, 30000)

  // 启动倒计时
  startCountdown()
})

onUnmounted(() => {
  if (refreshInterval) clearInterval(refreshInterval)
  if (countdownInterval) clearInterval(countdownInterval)
  window.removeEventListener('resize', handleMobileResize)
})
</script>

<style scoped>
.page-container {
  width: 100%;
}

/* ==================== 页面头部 ==================== */
.page-header {
  margin-bottom: 20px;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.page-header h1 {
  margin: 0 0 10px 0;
  font-size: 24px;
}

.page-header p {
  margin: 0;
  color: #909399;
}

.refresh-indicator {
  display: flex;
  align-items: center;
  gap: 12px;
}

.rotate-icon {
  animation: rotate 1s linear infinite;
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

/* ==================== 状态过滤器 ==================== */

/* ==================== Tabs容器 ==================== */
.tabs-container :deep(.el-tabs__content) {
  padding: 0;
}

.tab-label {
  display: flex;
  align-items: center;
  gap: 8px;
}

.tab-content {
  padding: 24px 24px 0 24px;
}

/* ==================== 实时队列区块 ==================== */
.unified-queue-section {
  padding: 16px;
}

/* ==================== 历史记录区块 ==================== */


.filter-bar {
  margin-bottom: 16px;
  padding: 12px;
  background-color: #f5f7fa;
  border-radius: 6px;
}

.filter-bar :deep(.el-form-item) {
  margin-bottom: 0;
  margin-right: 16px;
}

.filter-bar :deep(.el-form-item:last-child) {
  margin-right: 0;
}

/* 状态过滤器 */
.status-filter {
  margin-bottom: 24px;
  display: flex;
  flex-direction: column;
}

/* 现代化过滤器样式 */
/* 状态过滤器 - 紧凑分段控件 */
.status-filter-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}

.filter-tabs {
  display: flex;
  align-items: center;
  background: var(--nf-bg-container);
  border: 1px solid var(--nf-border-base);
  border-radius: var(--nf-radius-base);
  padding: 3px;
  gap: 2px;
}

.filter-tab {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: var(--nf-radius-sm);
  cursor: pointer;
  font-size: var(--nf-font-size-small);
  font-weight: var(--nf-font-weight-medium);
  color: var(--nf-text-secondary);
  transition: all var(--nf-transition-fast) var(--nf-ease-in-out);
  white-space: nowrap;
  user-select: none;
}

.filter-tab:hover {
  color: var(--nf-text-primary);
  background: var(--nf-bg-overlay);
}

.filter-tab.active {
  color: var(--nf-primary);
  background: var(--nf-bg-elevated);
  box-shadow: var(--nf-shadow-xs);
}

.tab-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}

.tab-dot.running {
  background-color: var(--nf-warning);
  box-shadow: 0 0 0 2px rgba(230, 162, 60, 0.2);
}

.tab-dot.pending {
  background-color: var(--nf-info);
}

.tab-dot.completed {
  background-color: var(--nf-success);
}

.filter-tab.active .tab-dot.running {
  animation: dot-pulse 2s ease-in-out infinite;
}

@keyframes dot-pulse {
  0%, 100% { box-shadow: 0 0 0 2px rgba(230, 162, 60, 0.2); }
  50% { box-shadow: 0 0 0 5px rgba(230, 162, 60, 0.08); }
}

.tab-label {
  line-height: 1;
}

.tab-count {
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: var(--nf-radius-full);
  background: var(--nf-bg-overlay);
  color: var(--nf-text-secondary);
  font-size: 11px;
  font-weight: var(--nf-font-weight-semibold);
  line-height: 18px;
  text-align: center;
}

.filter-tab.active .tab-count {
  background: var(--nf-primary);
  color: #fff;
}

.filter-live-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: var(--nf-font-size-mini);
  color: var(--nf-text-placeholder);
  font-weight: var(--nf-font-weight-medium);
  white-space: nowrap;
}

.live-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background-color: var(--nf-success);
  animation: live-pulse 2s ease-in-out infinite;
}

@keyframes live-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

/* 队列表格 */
.queue-table {
  margin-top: 0;
}

.queue-table :deep(.el-table__body-wrapper) {
  min-height: auto;
}

/* 现代化表格样式 */
.modern-table-container {
  background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  border-bottom: 1px solid #e2e8f0;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-title h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
  letter-spacing: -0.025em;
}

.header-badge {
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  color: white;
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}

.modern-table :deep(.el-table__header) {
  background: transparent;
}

.modern-table :deep(.el-table__header th) {
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  color: #1f2937;
  font-weight: 600;
  font-size: 13px;
  letter-spacing: 0.025em;
  border-bottom: none;
  padding: 16px 12px;
}

.modern-table :deep(.el-table__body tr) {
  transition: all 0.2s ease;
}

.modern-table :deep(.el-table__body tr:hover) {
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
}

.modern-table :deep(.el-table__body td) {
  border-bottom: 1px solid #f1f5f9;
  padding: 16px 12px;
}

/* 单元格样式 */
.status-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-indicator {
  width: 24px;
  height: 24px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: white;
}

.status-indicator.status-running {
  background: linear-gradient(135deg, #f59e0b, #fbbf24);
  box-shadow: 0 2px 6px rgba(245, 158, 11, 0.3);
}

.status-indicator.status-pending {
  background: linear-gradient(135deg, #6b7280, #9ca3af);
  box-shadow: 0 2px 6px rgba(107, 114, 128, 0.3);
}

.status-indicator.status-completed {
  background: linear-gradient(135deg, #10b981, #34d399);
  box-shadow: 0 2px 6px rgba(16, 185, 129, 0.3);
}

.status-indicator.status-failed {
  background: linear-gradient(135deg, #ef4444, #f87171);
  box-shadow: 0 2px 6px rgba(239, 68, 68, 0.3);
}

.status-indicator.status-cancelled {
  background: linear-gradient(135deg, #8b5cf6, #a78bfa);
  box-shadow: 0 2px 6px rgba(139, 92, 246, 0.3);
}

.status-text {
  font-size: 13px;
  font-weight: 600;
  color: #374151;
}

.task-name-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.task-title {
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
  line-height: 1.4;
}

.task-id {
  font-size: 11px;
  color: #9ca3af;
  font-weight: 500;
}

.task-type-tag {
  border-radius: 8px;
  font-weight: 500;
  letter-spacing: 0.025em;
}

.progress-cell {
  display: flex;
  align-items: center;
  height: 32px;
}

.progress-wrapper {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
}

.modern-progress {
  flex: 1;
}

.progress-text {
  font-size: 12px;
  font-weight: 600;
  color: #6b7280;
  min-width: 35px;
  text-align: right;
}

.no-progress {
  color: #d1d5db;
  font-size: 14px;
}

.time-cell {
  display: flex;
  align-items: center;
}

.time-value {
  font-size: 13px;
  color: #6b7280;
  font-weight: 500;
}

.duration-cell {
  display: flex;
  align-items: center;
}

.duration-value {
  font-size: 13px;
  color: #6b7280;
  font-weight: 500;
}

.error-cell {
  display: flex;
  align-items: center;
  width: 100%;
}

.error-content {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  overflow: hidden;
}

.error-icon {
  color: #ef4444;
  font-size: 14px;
  flex-shrink: 0;
}

.error-text {
  font-size: 13px;
  color: #ef4444;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.no-error {
  color: #d1d5db;
  font-size: 14px;
}

.actions-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  justify-content: flex-end;
}

.detail-btn {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.detail-btn:hover {
  background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
  transform: translateY(-1px);
}

/* 状态标签中的旋转图标 */
.el-tag .rotate-icon {
  margin-right: 4px;
}

/* ==================== 工具栏 ==================== */
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
  gap: 12px;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

/* ==================== 定时任务表格 ==================== */
.scheduled-tasks-table {
  margin-top: 16px;
}

.scheduled-tasks-table :deep(.el-table__body td:nth-child(4)),
.scheduled-tasks-table :deep(.el-table__body td:nth-child(5)) {
  text-align: center !important;
  vertical-align: middle !important;
}

.success-rate {
  display: flex;
  justify-content: flex-start;
  align-items: center;
  height: 100%;
  min-height: 55px;
  padding: 0;
  margin: 0;
}

.success-rate .progress-wrapper {
  display: flex;
  justify-content: flex-start;
  align-items: center;
  height: 55px;
}

.execution-stats {
  display: flex;
  justify-content: flex-start;
  align-items: center;
  height: 100%;
  min-height: 55px;
}


/* ==================== 分页 ==================== */
.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}

/* ==================== 移动端卡片视图 ==================== */
.scheduled-cards-mobile {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 0 16px 16px;
}

.task-card-mobile {
  background: var(--nf-bg-elevated, #fff);
  border: 1px solid var(--nf-border-base, #e2e8f0);
  border-radius: 12px;
  padding: 14px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}

.task-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.task-card-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--nf-text-primary, #1f2937);
  flex: 1;
  margin-right: 12px;
  line-height: 1.3;
}

.task-card-body {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 12px;
}

.task-card-info {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

.info-label {
  color: var(--nf-text-placeholder, #9ca3af);
  min-width: 52px;
  flex-shrink: 0;
}

.info-value {
  color: var(--nf-text-secondary, #6b7280);
  font-size: 13px;
}

.task-card-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-top: 10px;
  border-top: 1px solid var(--nf-border-light, #f1f5f9);
}

.action-btn-primary {
  width: 100%;
}

.action-btn-group {
  display: flex;
  gap: 8px;
}

.action-btn-group .el-button {
  flex: 1;
}

/* 实时队列移动端卡片 */
.queue-cards-mobile {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 0 16px 16px;
}

.queue-card-mobile {
  background: var(--nf-bg-elevated, #fff);
  border: 1px solid var(--nf-border-base, #e2e8f0);
  border-radius: 12px;
  padding: 12px 14px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}

.queue-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.queue-card-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--nf-text-primary, #1f2937);
  margin-bottom: 8px;
  line-height: 1.3;
}

.queue-card-progress {
  margin-bottom: 8px;
}

.queue-card-error {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-bottom: 8px;
  color: #ef4444;
  font-size: 12px;
}

.queue-card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 8px;
  border-top: 1px solid var(--nf-border-light, #f1f5f9);
}

/* ==================== 响应式设计 ==================== */
@media (max-width: 768px) {

  /* 过滤器移动端优化 */
  .status-filter-bar {
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
  }

  .filter-tabs {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
  }

  .filter-tab {
    padding: 5px 10px;
    font-size: var(--nf-font-size-mini);
  }

  .filter-live-indicator {
    justify-content: flex-end;
  }

  /* 表格移动端优化 */
  .modern-table-container {
    border-radius: 12px;
    overflow: hidden;
  }

  .table-header {
    padding: 16px;
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }

  .header-title h3 {
    font-size: 14px;
  }

  .header-badge {
    font-size: 11px;
    padding: 3px 8px;
  }

  /* 页面头部移动端 */
  .page-header h1 {
    font-size: 20px;
  }

  .header-content {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .refresh-indicator {
    width: 100%;
    justify-content: space-between;
  }

  .toolbar {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
    padding: 0 16px;
  }

  .toolbar-left,
  .toolbar-right {
    width: 100%;
  }

  .toolbar-right {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px;
  }

  /* 工具栏表单在移动端自动换行 */
  .toolbar-left :deep(.el-form) {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .toolbar-left :deep(.el-form-item) {
    margin-bottom: 0;
    margin-right: 0;
  }

  .toolbar-left :deep(.el-select),
  .toolbar-left :deep(.el-input),
  .toolbar-left :deep(.el-date-editor) {
    width: 100% !important;
  }

  .filter-bar :deep(.el-form-item) {
    margin-bottom: 12px;
  }

  /* tab-content 在移动端减少内边距 */
  .tab-content {
    padding: 12px 0 0 0;
  }

  /* 历史记录区域在移动端内边距 */
  .history-section {
    padding: 0 12px;
  }

  /* 统一队列区域在移动端减少内边距 */
  .unified-queue-section {
    padding: 8px 0;
  }

  /* 现代表格容器在移动端 */
  .modern-table-container {
    margin: 0 12px;
  }

  /* 状态过滤栏移动端 */
  .status-filter-bar {
    padding: 0 12px;
  }
}

@media (max-width: 576px) {
  /* 超小屏幕优化 */

  /* 表格在超小屏幕上的优化 */
  .modern-table :deep(.el-table__header th),
  .modern-table :deep(.el-table__body td) {
    padding: 12px 8px;
  }

  .modern-table :deep(.el-table__header th) {
    font-size: 11px;
  }

  .modern-table :deep(.el-table__body td) {
    font-size: 12px;
  }

  .header-badge {
    display: none;
  }

  .table-header {
    padding: 12px;
  }

  /* 移动端表格列隐藏 */
  .modern-table :deep(.el-table__header th:nth-child(6)),
  .modern-table :deep(.el-table__body td:nth-child(6)),
  .modern-table :deep(.el-table__header th:nth-child(7)),
  .modern-table :deep(.el-table__body td:nth-child(7)) {
    display: none;
  }

  /* 状态单元格优化 */
  .status-text {
    font-size: 12px;
  }

  .status-indicator {
    width: 20px;
    height: 20px;
    font-size: 10px;
  }

  /* 任务名称优化 */
  .task-title {
    font-size: 13px;
    line-height: 1.3;
  }

  .task-id {
    font-size: 10px;
  }

  /* 进度条优化 */
  .progress-cell {
    height: 28px;
  }

  .progress-text {
    font-size: 11px;
    min-width: 30px;
  }

  /* 操作按钮优化 */
  .actions-cell {
    gap: 4px;
  }

  .cancel-btn,
  .detail-btn {
    width: 24px;
    height: 24px;
    font-size: 12px;
  }

  .cancel-btn span {
    display: none;
  }

  /* 错误信息优化 */
  .error-text {
    font-size: 11px;
  }

  .error-icon {
    font-size: 12px;
  }
}

/* ==================== 取消按钮样式 ==================== */

/* ==================== 动画和交互效果 ==================== */

/* 页面整体加载动画 */
.page-container {
  animation: fadeInUp 0.6s ease-out;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 过滤器入场动画 */
.status-filter-bar {
  animation: filterSlideIn 0.4s ease-out forwards;
  opacity: 0;
}

@keyframes filterSlideIn {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 表格容器入场动画 */
.modern-table-container {
  animation: tableSlideIn 0.7s ease-out 0.3s forwards;
  opacity: 0;
}

@keyframes tableSlideIn {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 表格行动画 */
.modern-table :deep(.el-table__body tr) {
  animation: tableRowFadeIn 0.3s ease-out forwards;
  opacity: 0;
}

.modern-table :deep(.el-table__body tr:nth-child(1)) { animation-delay: 0.05s; }
.modern-table :deep(.el-table__body tr:nth-child(2)) { animation-delay: 0.1s; }
.modern-table :deep(.el-table__body tr:nth-child(3)) { animation-delay: 0.15s; }
.modern-table :deep(.el-table__body tr:nth-child(4)) { animation-delay: 0.2s; }
.modern-table :deep(.el-table__body tr:nth-child(5)) { animation-delay: 0.25s; }
.modern-table :deep(.el-table__body tr:nth-child(6)) { animation-delay: 0.3s; }
.modern-table :deep(.el-table__body tr:nth-child(n+7)) { animation-delay: 0.35s; }

@keyframes tableRowFadeIn {
  from {
    opacity: 0;
    transform: translateX(-20px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

/* 过滤标签点击反馈 */
.filter-tab:active {
  transform: scale(0.97);
  transition: transform 0.1s ease;
}

/* 状态指示器动画 */
.status-indicator {
  transition: all 0.3s ease;
}

.status-indicator.status-running {
  animation: statusPulse 2s ease-in-out infinite;
}

@keyframes statusPulse {
  0%, 100% {
    box-shadow: 0 2px 6px rgba(245, 158, 11, 0.3);
  }
  50% {
    box-shadow: 0 2px 12px rgba(245, 158, 11, 0.6);
  }
}

/* 进度条动画增强 */
.modern-progress :deep(.el-progress-bar__outer) {
  transition: all 0.3s ease;
}

.modern-progress:hover :deep(.el-progress-bar__outer) {
  transform: scaleY(1.2);
}

/* 数据更新动画 */
.stat-value,
.text-secondary,
.duration-value,
.time-value {
  transition: all 0.3s ease;
}

/* 头部徽章动画 */
.header-badge {
  position: relative;
  overflow: hidden;
}

.header-badge::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
  animation: badgeShimmer 3s ease-in-out infinite;
}

@keyframes badgeShimmer {
  0% {
    left: -100%;
  }
  50%, 100% {
    left: 100%;
  }
}

/* 加载状态动画 */
.page-container.v-loading .modern-stat-card,
.page-container.v-loading .status-filter-bar,
.page-container.v-loading .modern-table-container {
  animation-play-state: paused;
  opacity: 0.6;
}

/* 空状态动画 */
.el-empty {
  animation: emptyStateFadeIn 0.5s ease-out 0.6s forwards;
  opacity: 0;
}

@keyframes emptyStateFadeIn {
  from {
    opacity: 0;
    transform: scale(0.9);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

/* 交互反馈增强 */
.modern-stat-card:active,
.detail-btn:active {
  transform: scale(0.98);
  transition: transform 0.1s ease;
}

/* 悬停增强效果 */
.modern-stat-card:hover .stat-value {
  transform: scale(1.05);
  transition: transform 0.3s ease;
}

/* 刷新按钮动画 */
.header-actions .el-button:hover .el-icon {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* ==================== 取消按钮样式 ==================== */
.cancel-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  font-size: 13px;
  color: #f56c6c;
  background-color: #fef0f0;
  border: 1px solid #fbc4c4;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.cancel-btn:hover {
  color: #ffffff;
  background-color: #f56c6c;
  border-color: #f56c6c;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(245, 108, 108, 0.3);
}

.cancel-btn:active {
  transform: translateY(-1px);
  box-shadow: 0 2px 6px rgba(245, 108, 108, 0.3);
}

.cancel-btn .el-icon {
  font-size: 14px;
  transition: transform 0.2s ease;
}

.cancel-btn:hover .el-icon {
  transform: rotate(10deg);
}

/* ==================== 详情抽屉 ==================== */
.detail-content {
  padding: 10px 0;
}

.code-block {
  background-color: #f5f7fa;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  padding: 12px;
  font-size: 13px;
  line-height: 1.6;
  overflow: auto;
  max-height: 300px;
  margin: 0;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
}

.log-block {
  max-height: 500px;
  white-space: pre-wrap;
  word-break: break-all;
}

/* ==================== 暗色模式 - Dracula Purple ==================== */

/* 基础暗色模式变量 */
html.dark {
  --dark-bg-primary: linear-gradient(135deg, #1a1726 0%, #221e30 100%);
  --dark-bg-secondary: linear-gradient(135deg, #221e30 0%, #2a2540 100%);
  --dark-bg-tertiary: linear-gradient(135deg, #2a2540 0%, #332d4a 100%);
  --dark-border: #3d3660;
  --dark-text-primary: #F0ECF9;
  --dark-text-secondary: #D5CEE8;
  --dark-text-tertiary: #A89DC0;
  --dark-text-quaternary: #706590;
  --dark-shadow: 0 4px 16px rgba(19, 17, 28, 0.5);
  --dark-accent-purple: linear-gradient(135deg, #BD93F9 0%, #D4B8FF 100%);
  --dark-accent-green: linear-gradient(135deg, #50FA7B 0%, #69FF94 100%);
  --dark-accent-pink: linear-gradient(135deg, #FF79C6 0%, #FF92D0 100%);
}

/* 状态过滤器暗色模式 - 使用 CSS 变量自动适配，无需额外覆盖 */

html.dark .filter-bar {
  background-color: var(--dark-bg-primary);
  border-color: var(--dark-border);
}

html.dark .stat-card:hover {
  box-shadow: 0 4px 12px 0 rgba(189, 147, 249, 0.3);
}

html.dark .code-block {
  background-color: #1a1726;
  border-color: #3d3660;
  color: #D5CEE8;
  box-shadow: inset 0 2px 4px rgba(19, 17, 28, 0.3);
}

html.dark .cancel-btn {
  color: #FF5555;
  background-color: rgba(255, 85, 85, 0.1);
  border-color: rgba(255, 85, 85, 0.3);
}

/* 表格暗色模式优化 */
html.dark .modern-table-container {
  background: var(--dark-bg-primary);
  border-color: var(--dark-border);
  box-shadow: 0 4px 16px rgba(19, 17, 28, 0.4);
}

html.dark .table-header {
  background: var(--dark-bg-secondary);
  border-bottom-color: var(--dark-border);
}

html.dark .header-title h3 {
  color: var(--dark-text-primary);
  text-shadow: 0 1px 2px rgba(19, 17, 28, 0.4);
}

html.dark .header-badge {
  background: var(--dark-accent-purple);
  box-shadow: 0 2px 8px rgba(189, 147, 249, 0.4);
}

html.dark .modern-table :deep(.el-table__header th) {
  background: transparent;
  color: var(--dark-text-secondary);
  border-bottom-color: var(--dark-border);
  font-weight: 600;
}

html.dark .modern-table :deep(.el-table__body tr:hover) {
  background: var(--dark-bg-secondary);
}

html.dark .modern-table :deep(.el-table__body tr) {
  border-bottom-color: #2e2850;
}

html.dark .modern-table :deep(.el-table__body td) {
  border-bottom-color: var(--dark-border);
}

/* 单元格暗色模式 */
html.dark .status-text {
  color: var(--dark-text-secondary);
}

html.dark .task-title {
  color: var(--dark-text-primary);
  text-shadow: 0 1px 2px rgba(19, 17, 28, 0.3);
}

html.dark .task-id {
  color: var(--dark-text-quaternary);
}

html.dark .time-value,
html.dark .duration-value,
html.dark .progress-text {
  color: var(--dark-text-tertiary);
}

html.dark .no-progress,
html.dark .no-error {
  color: #706590;
}

/* 状态指示器暗色模式 - Dracula Colors */
html.dark .status-indicator.status-running {
  background: linear-gradient(135deg, #FFB86C, #FFD0A0);
  box-shadow: 0 2px 8px rgba(255, 184, 108, 0.4);
}

html.dark .status-indicator.status-completed {
  background: linear-gradient(135deg, #50FA7B, #69FF94);
  box-shadow: 0 2px 8px rgba(80, 250, 123, 0.4);
}

html.dark .status-indicator.status-failed {
  background: linear-gradient(135deg, #FF5555, #FF7777);
  box-shadow: 0 2px 8px rgba(255, 85, 85, 0.4);
}

html.dark .status-indicator.status-pending {
  background: linear-gradient(135deg, #706590, #A89DC0);
  box-shadow: 0 2px 8px rgba(112, 101, 144, 0.4);
}

html.dark .status-indicator.status-cancelled {
  background: linear-gradient(135deg, #BD93F9, #D4B8FF);
  box-shadow: 0 2px 8px rgba(189, 147, 249, 0.4);
}

/* 按钮和交互元素暗色模式 */
html.dark .detail-btn {
  color: #D4B8FF;
  border-color: #BD93F9;
}

html.dark .detail-btn:hover {
  background: var(--dark-accent-purple);
  color: white;
  box-shadow: 0 4px 12px rgba(189, 147, 249, 0.35);
}

html.dark .cancel-btn {
  color: #FF5555;
  background-color: rgba(255, 85, 85, 0.15);
  border-color: rgba(255, 85, 85, 0.4);
}

html.dark .cancel-btn:hover {
  color: #ffffff;
  background-color: #FF5555;
  border-color: #FF5555;
  box-shadow: 0 4px 12px rgba(255, 85, 85, 0.4);
}

/* 进度条暗色模式 */
html.dark .modern-progress :deep(.el-progress-bar__outer) {
  background-color: #332d4a;
}

html.dark .error-text {
  color: #FF5555;
  text-shadow: 0 1px 2px rgba(19, 17, 28, 0.4);
}

html.dark .error-icon {
  color: #FF5555;
}

/* 响应式暗色模式调整 */
@media (max-width: 768px) {
  html.dark .modern-table-container {
    box-shadow: 0 2px 8px rgba(19, 17, 28, 0.3);
  }
}

/* 步骤式进度容器（详情抽屉） */
.steps-container {
  padding: 20px;
  background: var(--bg-color-overlay);
  border-radius: 8px;
  margin-top: 12px;
}

/* 步骤进度（表格中） */
.step-progress {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.step-text {
  font-size: 13px;
  color: var(--text-color-primary);
  font-weight: 500;
}

.mini-progress {
  margin-top: 2px;
}

.batch-progress-text {
  font-size: 13px;
  color: var(--text-color-regular);
  margin-bottom: 4px;
}

.step-icon-success {
  color: var(--success-color);
  animation: none;
  font-size: 16px;
}

.step-icon-running {
  color: var(--primary-color);
  animation: rotate 1.5s linear infinite;
  font-size: 16px;
}

.step-icon-failed {
  color: var(--danger-color);
  font-size: 16px;
}

.step-icon-pending {
  color: var(--text-color-muted);
  font-size: 16px;
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

/* 批量进度容器 */
.batch-progress {
  margin-top: 12px;
}

/* 暗色模式适配 */
html.dark .steps-container {
  background: var(--bg-color-overlay);
}

/* 暗色模式动画优化 */
html.dark .detail-btn:hover {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

/* ==================== 海洋主题 ==================== */

/* 海洋主题基础变量 */
html.ocean {
  --ocean-bg-primary: linear-gradient(135deg, #0d1f35 0%, #132742 100%);
  --ocean-bg-secondary: linear-gradient(135deg, #132742 0%, #1a3150 100%);
  --ocean-bg-tertiary: linear-gradient(135deg, #1a3150 0%, #213a5c 100%);
  --ocean-border: #2a4a6e;
  --ocean-border-light: #3a5a7e;
  --ocean-text-primary: #E8F4FC;
  --ocean-text-secondary: #C5DCF0;
  --ocean-text-tertiary: #8EAEC8;
  --ocean-text-quaternary: #5A7A94;
  --ocean-shadow: 0 4px 16px rgba(10, 22, 40, 0.6);
  --ocean-accent-blue: linear-gradient(135deg, #38BDF8 0%, #7DD3FC 100%);
  --ocean-accent-green: linear-gradient(135deg, #10B981 0%, #34D399 100%);
  --ocean-accent-purple: linear-gradient(135deg, #8B5CF6 0%, #A78BFA 100%);
}

/* 状态过滤器海洋主题 - 使用 CSS 变量自动适配，无需额外覆盖 */

/* 表格海洋主题优化 */
html.ocean .modern-table-container {
  background: var(--ocean-bg-primary);
  border-color: var(--ocean-border);
  box-shadow: 0 4px 16px rgba(10, 22, 40, 0.5);
}

html.ocean .table-header {
  background: var(--ocean-bg-secondary);
  border-bottom-color: var(--ocean-border);
}

html.ocean .header-title h3 {
  color: var(--ocean-text-primary);
  text-shadow: 0 1px 2px rgba(10, 22, 40, 0.4);
}

html.ocean .header-badge {
  background: var(--ocean-accent-blue);
  box-shadow: 0 2px 8px rgba(56, 189, 248, 0.4);
}

html.ocean .modern-table :deep(.el-table__header th) {
  background: transparent;
  color: var(--ocean-text-secondary);
  border-bottom-color: var(--ocean-border);
  font-weight: 600;
}

html.ocean .modern-table :deep(.el-table__body tr:hover) {
  background: var(--ocean-bg-secondary);
}

html.ocean .modern-table :deep(.el-table__body tr) {
  border-bottom-color: #1a3150;
}

html.ocean .modern-table :deep(.el-table__body td) {
  border-bottom-color: var(--ocean-border);
}

/* 单元格海洋主题 */
html.ocean .status-text {
  color: var(--ocean-text-secondary);
}

html.ocean .task-title {
  color: var(--ocean-text-primary);
  text-shadow: 0 1px 2px rgba(10, 22, 40, 0.3);
}

html.ocean .task-id {
  color: var(--ocean-text-quaternary);
}

html.ocean .time-value,
html.ocean .duration-value,
html.ocean .progress-text {
  color: var(--ocean-text-tertiary);
}

html.ocean .no-progress,
html.ocean .no-error {
  color: var(--ocean-text-quaternary);
}

/* 状态指示器海洋主题 */
html.ocean .status-indicator.status-running {
  background: linear-gradient(135deg, #F59E0B, #FBBF24);
  box-shadow: 0 2px 8px rgba(251, 191, 36, 0.4);
}

html.ocean .status-indicator.status-completed {
  background: linear-gradient(135deg, #10B981, #34D399);
  box-shadow: 0 2px 8px rgba(52, 211, 153, 0.4);
}

html.ocean .status-indicator.status-failed {
  background: linear-gradient(135deg, #EF4444, #F87171);
  box-shadow: 0 2px 8px rgba(248, 113, 113, 0.4);
}

html.ocean .status-indicator.status-pending {
  background: linear-gradient(135deg, #5A7A94, #8EAEC8);
  box-shadow: 0 2px 8px rgba(90, 122, 148, 0.4);
}

html.ocean .status-indicator.status-cancelled {
  background: linear-gradient(135deg, #8B5CF6, #A78BFA);
  box-shadow: 0 2px 8px rgba(167, 139, 250, 0.4);
}

/* 按钮和交互元素海洋主题 */
html.ocean .detail-btn {
  color: #7DD3FC;
  border-color: #38BDF8;
}

html.ocean .detail-btn:hover {
  background: var(--ocean-accent-blue);
  color: white;
  box-shadow: 0 4px 12px rgba(56, 189, 248, 0.35);
}

html.ocean .cancel-btn {
  color: #F87171;
  background-color: rgba(248, 113, 113, 0.15);
  border-color: rgba(248, 113, 113, 0.4);
}

html.ocean .cancel-btn:hover {
  color: #ffffff;
  background-color: #EF4444;
  border-color: #EF4444;
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.4);
}

/* 进度条海洋主题 */
html.ocean .modern-progress :deep(.el-progress-bar__outer) {
  background-color: #1a3150;
}

html.ocean .error-text {
  color: #F87171;
  text-shadow: 0 1px 2px rgba(10, 22, 40, 0.4);
}

html.ocean .error-icon {
  color: #F87171;
}

/* 其他元素海洋主题 */
html.ocean .filter-bar {
  background-color: var(--ocean-bg-primary);
  border-color: var(--ocean-border);
}

html.ocean .code-block {
  background-color: #0a1628;
  border-color: var(--ocean-border);
  color: var(--ocean-text-secondary);
  box-shadow: inset 0 2px 4px rgba(10, 22, 40, 0.3);
}

html.ocean .steps-container {
  background: var(--bg-color-overlay);
}

/* 响应式海洋主题调整 */
@media (max-width: 768px) {
  html.ocean .modern-table-container {
    box-shadow: 0 2px 8px rgba(10, 22, 40, 0.4);
  }
}

/* 海洋主题动画优化 */
html.ocean .detail-btn:hover {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
</style>
