/**
 * 资源识别相关 API
 */

import request from '../request'
import {
  ResourceMapping,
  ResourceMappingWithDetails,
  BatchIdentifyRequest,
  BatchIdentifyResult
} from '@/types'
import { ApiResponse } from '@/types'

// 识别单个PT资源（自动判断媒体类型）
export function identifyResource(ptResourceId: number, force: boolean = false) {
  return request.post<ApiResponse<ResourceMapping>>(
    `/resource-identification/${ptResourceId}/identify`,
    null,
    {
      params: { force }
    }
  )
}

// 批量识别PT资源（支持指定媒体类型）
export function batchIdentifyResources(data: BatchIdentifyRequest) {
  return request.post<ApiResponse<BatchIdentifyResult>>(
    '/resource-identification/batch-identify',
    data.ptResourceIds, // 请求体：JSON数组
    {
      params: {
        media_type: data.mediaType ?? 'auto',  // 媒体类型，默认 auto
        skip_errors: data.skipErrors ?? true    // 是否跳过错误
      }
    }
  )
}

// 查询PT资源的映射关系
export function getResourceMapping(ptResourceId: number) {
  return request.get<ApiResponse<ResourceMappingWithDetails>>(
    `/resource-identification/pt-resources/${ptResourceId}/mapping`
  )
}

// 删除映射关系（支持重新识别）
export function deleteMapping(mappingId: number) {
  return request.delete<ApiResponse<void>>(`/resource-identification/mappings/${mappingId}`)
}

// 删除PT资源的映射关系
export function deleteResourceMapping(ptResourceId: number) {
  return request.delete<ApiResponse<void>>(
    `/resource-identification/pt-resources/${ptResourceId}/mapping`
  )
}
