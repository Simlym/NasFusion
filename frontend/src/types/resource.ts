/**
 * 资源相关类型定义
 */

import { MediaType, UnifiedTableName } from './common'

// PT资源
export interface PTResource {
  id: number
  siteId: number
  siteName?: string
  torrentId: string
  torrentHash?: string
  title: string
  subtitle?: string
  category: string
  sizeBytes: number
  fileCount: number
  seeders: number
  leechers: number
  completions: number
  lastSeederUpdateAt?: string
  promotionType?: string
  promotionExpireAt?: string
  isFree: boolean
  isDiscount: boolean
  isDoubleUpload: boolean
  hasHr: boolean
  hrDays?: number
  hrSeedTime?: number
  hrRatio?: number
  resolution?: string
  source?: string
  codec?: string
  audio?: string[]
  subtitleInfo?: string[]
  qualityTags?: string[]
  tvInfo?: {
    seasons?: number[]
    episodes?: Record<string, { start: number; end: number }>
    isCompleteSeason?: boolean
  }
  imdbId?: string
  imdbRating?: number
  doubanId?: string
  doubanRating?: number
  tmdbId?: number
  detailUrl?: string
  downloadUrl: string
  magnetLink?: string
  isActive: boolean
  lastCheckAt?: string
  publishedAt?: string
  createdAt: string
  updatedAt: string
  sizeGb: number
  sizeHumanReadable: string
  isPromotional: boolean
  hasMapping: boolean
  mappingId?: number
  unifiedResourceId?: number
  mediaType?: string
  description?: string
  mediainfo?: string
  detailFetched?: boolean
  detailFetchedAt?: string
  identificationStatus?: string
  isDownloaded?: boolean
  downloadStatus?: string
}

// 统一电影资源
export interface UnifiedMovie {
  id: number
  tmdbId?: number
  imdbId?: string
  doubanId?: string
  title: string
  originalTitle?: string
  aka?: string[]
  year?: number
  releaseDate?: string
  runtime?: number
  ratingTmdb?: number
  votesTmdb?: number
  ratingDouban?: number
  votesDouban?: number
  ratingImdb?: number
  votesImdb?: number
  genres?: string[]
  tags?: string[]
  languages?: string[]
  countries?: string[]
  directors?: Array<{
    id: number
    douban_id?: string
    imdb_id?: string
    name: string
    latin_name?: string
    thumb_url?: string
  }>
  actors?: Array<{
    id: number
    douban_id?: string
    imdb_id?: string
    name: string
    latin_name?: string
    character?: string
    thumb_url?: string
    order?: number
  }>
  writers?: Array<{
    id: number
    douban_id?: string
    imdb_id?: string
    name: string
    latin_name?: string
    thumb_url?: string
  }>
  overview?: string
  tagline?: string
  certification?: string
  collectionId?: number
  collectionName?: string
  budget?: number
  revenue?: number
  productionCompanies?: string[]
  status?: string
  posterUrl?: string
  backdropUrl?: string
  logoUrl?: string
  clearartUrl?: string
  bannerUrl?: string
  ptResourceCount: number
  hasFreeResource: boolean
  bestQuality?: string
  bestSeederCount: number
  lastResourceUpdatedAt?: string
  localFileCount: number
  hasLocal: boolean
  localImagesDir?: string
  detailLoaded: boolean
  detailLoadedAt?: string
  metadataSource?: string
  createdAt: string
  updatedAt: string
}

// 统一资源基础接口（保留用于其他资源类型）
export interface UnifiedResourceBase {
  id: number
  unifiedTableName?: UnifiedTableName
  mediaType?: MediaType
  title: string
  originalTitle?: string
  year?: number
  posterUrl?: string
  backdropUrl?: string
  overview?: string
  imdbId?: string
  tmdbId?: number
  doubanId?: string
  rating?: number
  voteCount?: number
  ptResourceCount: number
  bestQualitySize?: number
  bestQualitySeeders?: number
  hasFreeResource?: boolean
  firstAvailableAt?: string
  lastUpdatedAt?: string
  createdAt: string
}

// 统一电视剧资源
export interface UnifiedTV {
  id: number
  tmdbId?: number
  imdbId?: string
  tvdbId?: number
  doubanId?: string
  title: string
  originalTitle?: string
  aka?: string[]
  year?: number
  firstAirDate?: string
  lastAirDate?: string
  status?: string  // Returning Series/Ended/Canceled/In Production
  numberOfSeasons?: number
  numberOfEpisodes?: number
  episodeRuntime?: (number | null)[]
  ratingTmdb?: number
  votesTmdb?: number
  ratingDouban?: number
  votesDouban?: number
  ratingImdb?: number
  votesImdb?: number
  genres?: string[]
  tags?: string[]
  languages?: string[]
  countries?: string[]
  networks?: string[]
  creators?: Array<{
    id: number
    douban_id?: string
    imdb_id?: string
    name: string
    latin_name?: string
    thumb_url?: string
  }>
  directors?: Array<{
    id: number
    douban_id?: string
    imdb_id?: string
    name: string
    latin_name?: string
    thumb_url?: string
  }>
  actors?: Array<{
    id: number
    douban_id?: string
    imdb_id?: string
    name: string
    latin_name?: string
    character?: string
    thumb_url?: string
    order?: number
  }>
  writers?: Array<{
    id: number
    douban_id?: string
    imdb_id?: string
    name: string
    latin_name?: string
    thumb_url?: string
  }>
  overview?: string
  tagline?: string
  certification?: string
  contentRatings?: Record<string, string>
  productionCompanies?: string[]
  type?: string  // Scripted/Reality/Documentary/News等
  posterUrl?: string
  backdropUrl?: string
  logoUrl?: string
  clearartUrl?: string
  bannerUrl?: string
  seasonsInfo?: Array<{
    season_number: number
    episode_count: number
    air_date?: string
    poster_url?: string
  }>
  ptResourceCount: number
  hasFreeResource: boolean
  bestQuality?: string
  bestSeederCount: number
  lastResourceUpdatedAt?: string
  localFileCount: number
  hasLocal: boolean
  localImagesDir?: string
  detailLoaded: boolean
  detailLoadedAt?: string
  metadataSource?: string
  createdAt: string
  updatedAt: string
}

// 为了向后兼容，保留 UnifiedTVSeries 别名
export type UnifiedTVSeries = UnifiedTV

// 统一音乐资源
export interface UnifiedMusic extends UnifiedResourceBase {
  artist?: string
  albumType?: string
  genres?: string[]
  trackCount?: number
}

// 资源过滤器
export interface ResourceFilter {
  mediaType?: MediaType
  siteId?: number
  keyword?: string
  minSize?: number
  maxSize?: number
  minSeeders?: number
  year?: number
  genres?: string[]
  sortBy?: string
  sortOrder?: 'asc' | 'desc'
}

// 资源映射
export interface ResourceMapping {
  id: number
  ptResourceId: number
  mediaType: MediaType
  unifiedTableName: UnifiedTableName
  unifiedResourceId: number
  matchMethod?: string
  matchConfidence?: number
  matchScoreDetail?: Record<string, unknown>
  isPrimary: boolean
  recommendationScore?: number
  recommendationReason?: Record<string, unknown>
  isVerified: boolean
  verifiedBy?: number
  verifiedAt?: string
  createdAt: string
  updatedAt: string
}

// 资源映射详情（含关联数据）
export interface ResourceMappingWithDetails extends ResourceMapping {
  ptResource?: PTResource
  unifiedResource?: UnifiedMovie | Record<string, unknown> // 根据 unified_table_name 动态加载
}

// 统一电影资源（含PT资源列表）
// PT资源分页信息
export interface PTResourcesPagination {
  total: number
  page: number
  pageSize: number
  totalPages: number
}

export interface UnifiedMovieWithPTResources extends UnifiedMovie {
  ptResources: PTResource[]
  ptResourcesPagination?: PTResourcesPagination
}

// 统一电视剧资源（含PT资源列表）
export interface UnifiedTVWithPTResources extends UnifiedTV {
  ptResources: PTResource[]
  ptResourcesPagination?: PTResourcesPagination
}

// 批量识别请求
export interface BatchIdentifyRequest {
  ptResourceIds: number[]
  mediaType?: 'auto' | 'movie' | 'tv' | 'music' | 'book' | 'adult'  // 媒体类型，默认 auto
  skipErrors?: boolean
}

// 批量识别结果
export interface BatchIdentifyResult {
  total: number
  success: number
  failed: number
  skipped: number
  errors: Array<{
    ptResourceId: number
    error: string
  }>
}

// 统一人员资源
export interface UnifiedPerson {
  id: number
  tmdbId?: number
  imdbId?: string
  doubanId?: string
  name: string
  otherNames?: string[]
  profileUrl?: string
  gender?: number // 1: Female, 2: Male
  biography?: string
  birthday?: string
  deathday?: string
  placeOfBirth?: string
  homepage?: string
  knownForDepartment?: string
  popularity?: number
  familyInfo?: string
  metadataSource?: string
  detailLoaded?: boolean
  detailLoadedAt?: string
  createdAt?: string
  updatedAt?: string
  movieCount?: number
  tvCount?: number
}

// 人员关联作品 简单信息
export interface PersonCreditMovie {
  id: number
  title: string
  originalTitle?: string
  year?: number
  posterUrl?: string
  ratingDouban?: number
  ratingTmdb?: number
}

export interface PersonCreditTV {
  id: number
  title: string
  originalTitle?: string
  year?: number
  posterUrl?: string
  ratingDouban?: number
  ratingTmdb?: number
}

// 人员参演作品
export interface PersonCredits {
  castMovies: Array<{
    job: string
    character?: string
    order?: number
    movie: PersonCreditMovie
  }>
  crewMovies: Array<{
    job: string
    movie: PersonCreditMovie
  }>
  castTv: Array<{
    job: string
    character?: string
    order?: number
    tvSeries: PersonCreditTV
  }>
  crewTv: Array<{
    job: string
    tvSeries: PersonCreditTV
  }>
}

