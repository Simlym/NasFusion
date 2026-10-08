/**
 * PT资源详情 API（通用接口，支持成人/音乐/电子书等媒体类型）
 */
import request from '../request'

export interface PTResourceDetailItem {
  id: number
  title: string
  subtitle?: string
  doubanId?: string
  doubanRating?: number
  posterUrl?: string
  imageList: string[]
  publishedAt?: string
  sizeBytes: number
  seeders: number
  leechers: number
  isFree: boolean
  promotionType?: string
  detailUrl?: string
  downloadUrl?: string
}

export interface PTResourceDetailItemResponse extends PTResourceDetailItem {
  detailLoaded: boolean
  description?: string
  mediainfo?: string
  dmmInfo?: {
    productNumber?: string
    actressList?: string[]
    keywordList?: string[]
    director?: string
    series?: string
    maker?: string
    label?: string
  }
}

export interface PTResourceDetailListResponse {
  items: PTResourceDetailItem[]
  total: number
  page: number
  page_size: number
}

export interface PTResourceDetailQuery {
  category?: string  // 媒体分类：adult/music/ebook 等
  siteId?: number    // PT站点ID
  originalCategoryId?: string  // 原始分类ID
  page?: number
  pageSize?: number
  keyword?: string
  isFree?: boolean
}

export interface FetchDetailResponse {
  detail_id: number
  message: string
}

/**
 * 获取 PT 资源列表（通用接口）
 */
export function getPTResourceDetailList(params: PTResourceDetailQuery) {
  return request.get<PTResourceDetailListResponse>('/pt-resource-details', {
    params: {
      category: params.category,
      site_id: params.siteId,
      original_category_id: params.originalCategoryId,
      page: params.page,
      page_size: params.pageSize,
      keyword: params.keyword,
      is_free: params.isFree
    }
  })
}

/**
 * 获取 PT 资源详情
 */
export function getPTResourceDetail(resourceId: number) {
  return request.get<PTResourceDetailItemResponse>(`/pt-resource-details/${resourceId}`)
}

/**
 * 获取资源详情（调用 MTeam API）
 */
export function fetchPTResourceDetail(resourceId: number) {
  return request.post<FetchDetailResponse>(`/pt-resource-details/${resourceId}/fetch-detail`)
}
