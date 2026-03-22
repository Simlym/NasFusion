/**
 * MCP 外部服务器管理 API
 */

import request from '../request'

// ==================== 类型定义 ====================

export interface MCPServer {
  id: number
  name: string
  description?: string
  transport_type: string
  url?: string
  command?: string
  auth_type: string
  is_enabled: boolean
  tools_count?: number
  last_sync_at?: string
  last_error?: string
  created_at: string
}

export interface MCPServerCreate {
  name: string
  description?: string
  transport_type: string
  url?: string
  command?: string
  command_args?: string[]
  env_vars?: Record<string, string>
  auth_type: string
  auth_token?: string
  is_enabled: boolean
}

export interface MCPServerUpdate {
  name?: string
  description?: string
  url?: string
  command?: string
  command_args?: string[]
  env_vars?: Record<string, string>
  auth_type?: string
  auth_token?: string
  is_enabled?: boolean
}

// ==================== API ====================

export function getMCPServerList() {
  return request.get<MCPServer[]>('/mcp/external-servers')
}

export function createMCPServer(data: MCPServerCreate) {
  return request.post<MCPServer>('/mcp/external-servers', data)
}

export function updateMCPServer(id: number, data: MCPServerUpdate) {
  return request.put<MCPServer>(`/mcp/external-servers/${id}`, data)
}

export function deleteMCPServer(id: number) {
  return request.delete(`/mcp/external-servers/${id}`)
}

export function testMCPServer(id: number) {
  return request.post<{ success: boolean; message: string; tools_count?: number }>(
    `/mcp/external-servers/${id}/test`
  )
}

export function syncMCPServerTools(id: number) {
  return request.post<{ success: boolean; tools_count: number; tools: any[] }>(
    `/mcp/external-servers/${id}/sync`
  )
}
