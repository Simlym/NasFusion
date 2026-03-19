import request from '../request'
import type { UnifiedPerson, PersonCredits } from '@/types'

export const getPersonList = (params?: {
    page?: number
    pageSize?: number
    search?: string
    gender?: number
    department?: string
    country?: string
    metadataSource?: string
    detailLoaded?: boolean
    sortBy?: string
    sortOrder?: string
}) => {
    return request.get('/persons', {
        params: {
            page: params?.page || 1,
            page_size: params?.pageSize || 20,
            search: params?.search || undefined,
            gender: params?.gender ?? undefined,
            department: params?.department || undefined,
            country: params?.country || undefined,
            metadata_source: params?.metadataSource || undefined,
            detail_loaded: params?.detailLoaded ?? undefined,
            sort_by: params?.sortBy || undefined,
            sort_order: params?.sortOrder || undefined,
        }
    })
}

export const getPersonDetail = (id: number) => {
    return request.get<UnifiedPerson>(`/persons/${id}`)
}

export const getPersonCredits = (id: number) => {
    return request.get<PersonCredits>(`/persons/${id}/credits`)
}

export const getPersonDepartments = () => {
    return request.get<string[]>('/persons/departments')
}

export const updatePerson = (id: number, data: Partial<UnifiedPerson>) => {
    return request.put<UnifiedPerson>(`/persons/${id}`, data)
}

export default {
    getPersonList,
    getPersonDetail,
    getPersonCredits,
    getPersonDepartments,
    updatePerson,
}
