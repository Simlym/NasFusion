/**
 * 订阅相关类型定义
 */

// ==================== 订阅状态枚举 ====================
export enum SubscriptionStatus {
  ACTIVE = 'active',
  PAUSED = 'paused',
  COMPLETED = 'completed',
  CANCELLED = 'cancelled'
}







// ==================== 集数类型偏好 ====================
export enum EpisodeTypePreference {
  SINGLE_PREFERRED = 'single_preferred', // 单集优先（1-3集合集）
  SEASON_PREFERRED = 'season_preferred', // 季包优先（完整季度）
  BOTH = 'both' // 都可以
}

// ==================== 订阅规则 ====================
export interface SubscriptionRules {
  qualityPriority?: string[] // 质量优先级列表 ['2160p', '1080p', '720p']
  sitePriority?: number[] // 站点优先级列表（站点ID）
  promotionRequired?: string[] // 必须满足的促销类型 ['free', '2xfree', '2x', '50%', '30%']
  minSeeders?: number // 最小做种数
  minFileSize?: number // 最小文件大小（MB）
  episodeTypePreference?: EpisodeTypePreference // 集数类型偏好
}

// ==================== 订阅 ====================
export interface Subscription {
  id: number
  userId: number

  // 基础信息
  mediaType: 'movie' | 'tv'
  unifiedMovieId?: number
  unifiedTvId?: number
  title: string
  originalTitle?: string
  year?: number
  posterUrl?: string

  // 外部ID
  doubanId?: string
  imdbId?: string
  tmdbId?: number

  // 订阅来源和类型
  source?: string // from_tmdb/from_pt_resource/manual
  subscriptionType?: string // movie_release/tv_season

  // 电视剧订阅字段
  currentSeason?: number // 订阅的季度
  startEpisode?: number // 起始集数
  currentEpisode?: number // 当前已匹配到的集数
  totalEpisodes?: number // 本季总集数

  // 多资源关联（解决长篇动画跨年番匹配问题）
  relatedTvIds?: number[] // 关联的TV资源ID列表
  absoluteEpisodeStart?: number // 绝对集数起始
  absoluteEpisodeEnd?: number // 绝对集数结束

  // 展示信息覆写（用于NFO生成和文件整理）
  overrideTitle?: string // 覆写标题
  overrideYear?: number // 覆写年份
  overrideFolder?: string // 覆写存储目录名
  useOverrideForSync?: boolean // 是否使用覆写标题进行PT资源同步

  // 订阅规则
  rules?: SubscriptionRules

  // 订阅状态
  status: SubscriptionStatus
  isActive: boolean

  // 检查策略
  lastCheckAt?: string

  // 资源状态
  hasResources: boolean
  firstResourceFoundAt?: string
  resourceCount: number
  bestResourceQuality?: string

  // 通知设置


  // 下载设置
  autoDownload: boolean

  // 整理设置
  autoOrganize: boolean
  organizeConfigId?: number
  storageMountId?: number

  // 用户设置
  userTags?: string[]
  userPriority: number
  userNotes?: string
  isFavorite: boolean

  // 统计信息
  totalChecks: number
  totalMatches: number
  totalDownloads: number

  // 时间戳
  createdAt: string
  updatedAt: string
  completedAt?: string
}

// ==================== 订阅创建表单 ====================
export interface SubscriptionCreateForm {
  // 基础信息（必填）
  mediaType: 'movie' | 'tv'
  unifiedMovieId?: number
  unifiedTvId?: number
  title: string

  // 可选基础信息
  originalTitle?: string
  year?: number
  posterUrl?: string

  // 外部ID
  doubanId?: string
  imdbId?: string
  tmdbId?: number

  // 订阅来源和类型
  source?: string
  subscriptionType?: string

  // 电视剧订阅字段
  currentSeason?: number
  startEpisode?: number
  totalEpisodes?: number

  // 多资源关联
  relatedTvIds?: number[]
  absoluteEpisodeStart?: number
  absoluteEpisodeEnd?: number

  // 展示信息覆写
  overrideTitle?: string
  overrideYear?: number
  overrideFolder?: string
  useOverrideForSync?: boolean

  // 订阅规则
  rules?: SubscriptionRules


  // 下载设置
  autoDownload?: boolean

  // 整理设置
  autoOrganize?: boolean
  organizeConfigId?: number | null
  storageMountId?: number | null

  // 用户设置
  userTags?: string[]
  userPriority?: number
  userNotes?: string
  isFavorite?: boolean
}

// ==================== 订阅更新表单 ====================
export interface SubscriptionUpdateForm {
  // 基础信息
  title?: string
  originalTitle?: string
  year?: number
  posterUrl?: string

  // 电视剧订阅字段
  currentSeason?: number
  startEpisode?: number
  currentEpisode?: number
  totalEpisodes?: number

  // 多资源关联
  relatedTvIds?: number[]
  absoluteEpisodeStart?: number
  absoluteEpisodeEnd?: number

  // 展示信息覆写
  overrideTitle?: string
  overrideYear?: number
  overrideFolder?: string
  useOverrideForSync?: boolean

  // 订阅规则
  rules?: SubscriptionRules

  // 订阅状态
  status?: SubscriptionStatus
  isActive?: boolean



  // 下载设置
  autoDownload?: boolean

  // 整理设置
  autoOrganize?: boolean
  organizeConfigId?: number | null
  storageMountId?: number | null

  // 用户设置
  userTags?: string[]
  userPriority?: number
  userNotes?: string
  isFavorite?: boolean
}

// ==================== 订阅检查日志 ====================
export interface SubscriptionCheckLog {
  id: number
  subscriptionId: number
  checkAt: string
  checkType?: string

  // TMDB状态
  tmdbStatus?: string
  tmdbReleaseDate?: string
  tmdbUpdated?: boolean
  tmdbDetails?: Record<string, any>

  // PT搜索结果
  sitesSearched?: number
  resourcesFound?: number
  matchCount?: number
  bestMatch?: Record<string, any>
  searchResults?: Record<string, any>

  // 匹配分析
  matchingAnalysis?: Record<string, any>

  // 触发的动作
  actionTriggered?: string
  actionDetail?: Record<string, any>

  // 执行状态
  executionTime?: number
  success?: boolean
  errorMessage?: string
  errorCategory?: string
  errorSeverity: string

  // 批量检查
  batchId?: string
  batchTotal?: number
  batchPosition?: number

  // 时间戳
  createdAt: string
}

// ==================== 匹配的PT资源 ====================
export interface MatchedPTResource {
  id: number
  ptResourceId: number
  title: string
  subtitle?: string
  siteName: string
  siteId: number
  quality?: string
  size: number
  seeders: number
  leechers: number
  promotionType?: string
  publishedAt: string
  downloadUrl?: string
}
