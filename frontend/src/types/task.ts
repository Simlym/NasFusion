/**
 * 任务调度相关类型定义
 */

// 任务类型
export enum TaskType {
  PT_RESOURCE_SYNC = 'pt_resource_sync',
  PT_RESOURCE_IDENTIFY = 'pt_resource_identify',
  SUBSCRIPTION_CHECK = 'subscription_check',
  AI_RECOMMENDATION = 'ai_recommendation',
  NOTIFICATION_SEND = 'notification_send',
  MEDIA_FILE_SCAN = 'media_file_scan',
  TASK_EXECUTION_CLEANUP = 'task_execution_cleanup',
  DOWNLOAD_CREATE = 'download_create',
  DOWNLOAD_STATUS_SYNC = 'download_status_sync',
  MEDIA_SERVER_WATCH_HISTORY_SYNC = 'media_server_watch_history_sync',
  MEDIA_SERVER_LIBRARY_STATS_UPDATE = 'media_server_library_stats_update',
  CREDITS_BACKFILL = 'credits_backfill',
  PERSON_MERGE = 'person_merge'
}

// 调度类型
export enum ScheduleType {
  CRON = 'cron',
  INTERVAL = 'interval',
  ONE_TIME = 'one_time',
  MANUAL = 'manual'
}

// 执行状态
export enum ExecutionStatus {
  PENDING = 'pending',
  RUNNING = 'running',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled',
  TIMEOUT = 'timeout'
}

// 任务类型显示名称（支持新旧两种格式）
export const TaskTypeNames: Record<string, string> = {
  // 新格式
  [TaskType.PT_RESOURCE_SYNC]: 'PT资源同步',
  [TaskType.PT_RESOURCE_IDENTIFY]: 'PT资源识别',
  [TaskType.SUBSCRIPTION_CHECK]: '订阅检查',
  [TaskType.AI_RECOMMENDATION]: 'AI推荐',
  [TaskType.NOTIFICATION_SEND]: '通知发送',
  [TaskType.MEDIA_FILE_SCAN]: '媒体文件扫描',
  [TaskType.TASK_EXECUTION_CLEANUP]: '任务执行记录清理',
  [TaskType.DOWNLOAD_CREATE]: '创建下载任务',
  [TaskType.DOWNLOAD_STATUS_SYNC]: '同步下载状态',
  [TaskType.MEDIA_SERVER_WATCH_HISTORY_SYNC]: '媒体服务器观看历史同步',
  [TaskType.MEDIA_SERVER_LIBRARY_STATS_UPDATE]: '媒体服务器库统计更新',
  // 媒体服务器同步类型
  'media_server_library_sync': '媒体服务器媒体库同步',
  'trending_sync': '流行趋势同步',
  'trending_detail_sync': '流行详情同步',
  [TaskType.CREDITS_BACKFILL]: '演职员关系回填',
  [TaskType.PERSON_MERGE]: '重复人物合并',
  // 旧格式兼容（用于历史数据）
  'pt_sync': 'PT资源同步',
  'batch_identify': 'PT资源识别',
  'scan_media': '媒体文件扫描',
  'cleanup': '任务执行记录清理',
  'create_download': '创建下载任务',
  'sync_download_status': '同步下载状态'
}

// 调度类型显示名称
export const ScheduleTypeNames: Record<ScheduleType, string> = {
  [ScheduleType.CRON]: 'Cron表达式',
  [ScheduleType.INTERVAL]: '固定间隔',
  [ScheduleType.ONE_TIME]: '一次性',
  [ScheduleType.MANUAL]: '手动触发'
}

// 执行状态显示名称
export const ExecutionStatusNames: Record<ExecutionStatus, string> = {
  [ExecutionStatus.PENDING]: '等待中',
  [ExecutionStatus.RUNNING]: '执行中',
  [ExecutionStatus.COMPLETED]: '已完成',
  [ExecutionStatus.FAILED]: '失败',
  [ExecutionStatus.CANCELLED]: '已取消',
  [ExecutionStatus.TIMEOUT]: '超时'
}

// 调度任务
export interface ScheduledTask {
  id: number
  task_name: string
  task_type: string
  description?: string
  enabled: boolean
  schedule_type: string
  schedule_config?: Record<string, any>
  handler: string
  handler_params?: Record<string, any>
  priority: number
  timeout?: number
  max_retries: number
  retry_delay: number
  next_run_at?: string
  last_run_at?: string
  last_run_status?: string
  last_run_duration?: number
  total_runs: number
  success_runs: number
  failed_runs: number
  created_at: string
  updated_at: string
}

// 创建调度任务表单
export interface ScheduledTaskCreate {
  task_name: string
  task_type: string
  description?: string
  enabled?: boolean
  schedule_type: string
  schedule_config?: Record<string, any>
  handler: string
  handler_params?: Record<string, any>
  priority?: number
  timeout?: number
  max_retries?: number
  retry_delay?: number
}

// PT同步任务快速创建表单
export interface PTSyncTaskCreate {
  site_id: number
  task_name: string
  schedule_type?: string
  schedule_config?: Record<string, any>
  sync_type?: string
  max_pages?: number
  request_interval?: number  // 请求间隔（秒）
  enabled?: boolean
  description?: string
  // 过滤参数
  mode?: string
  categories?: string[]
  upload_date_start?: string
  upload_date_end?: string
  keyword?: string
  sortField?: string
  sortDirection?: string
}

// 任务执行记录
export interface TaskExecution {
  id: number
  scheduled_task_id?: number
  task_type: string
  task_name: string
  related_type?: string
  related_id?: number
  status: string
  priority: number
  handler: string
  handler_params?: Record<string, any>
  scheduled_at?: string
  started_at?: string
  completed_at?: string
  duration?: number
  retry_count: number
  max_retries: number
  next_retry_at?: string
  worker_id?: string
  result?: Record<string, any>
  error_message?: string
  error_detail?: Record<string, any>
  progress: number
  progress_detail?: Record<string, any>
  logs?: string
  task_metadata?: Record<string, any>
  created_at: string
  updated_at: string
}

// 任务执行摘要
export interface TaskExecutionSummary {
  id: number
  task_name: string
  task_type: string
  status: string
  progress: number
  started_at?: string
  error_message?: string
}

// 任务队列状态
export interface TaskQueueStatus {
  running: TaskExecutionSummary[]
  pending: TaskExecutionSummary[]
  recent_completed: TaskExecutionSummary[]
}

// 调度任务列表响应
export interface ScheduledTaskListResponse {
  total: number
  items: ScheduledTask[]
}

// 任务执行列表响应
export interface TaskExecutionListResponse {
  total: number
  items: TaskExecution[]
}
