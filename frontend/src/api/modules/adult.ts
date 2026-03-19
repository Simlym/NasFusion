/**
 * 成人资源 API
 */
import {
  getPTResourceDetailList,
  getPTResourceDetail,
  fetchPTResourceDetail,
  type PTResourceDetailItem,
  type PTResourceDetailItemResponse,
  type PTResourceDetailListResponse,
  type FetchDetailResponse
} from './ptResourceDetails'

// 重新导出类型（语义化命名）
export type AdultResource = PTResourceDetailItem
export type AdultResourceDetail = PTResourceDetailItemResponse
export type AdultResourceListResponse = PTResourceDetailListResponse
export { type FetchDetailResponse }

/**
 * 获取成人资源列表
 */
export function getAdultResources(params: {
  page?: number
  pageSize?: number
  siteId?: number
  originalCategoryId?: string
}) {
  return getPTResourceDetailList({
    category: 'adult',
    ...params
  })
}

/**
 * 获取成人资源详情
 */
export function getAdultResourceDetail(resourceId: number) {
  return getPTResourceDetail(resourceId)
}

/**
 * 获取资源详情（调用 MTeam API）
 */
export function fetchAdultResourceDetail(resourceId: number) {
  return fetchPTResourceDetail(resourceId)
}
