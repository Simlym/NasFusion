import request from '../request'

export interface DiskInfo {
  total: number
  used: number
  free: number
  percent: number
}

export interface PathValidation {
  exists: boolean
  is_directory: boolean
  readable: boolean
  writable: boolean
  disk_info: DiskInfo | null
  error?: string
}

export interface DirectoryItem {
  name: string
  path: string
  size: number
  modified_at: string | null
  is_accessible: boolean
}

export interface BrowseResult {
  current_path: string
  parent_path: string | null
  directories: DirectoryItem[]
}

export interface CreateDirectoryResult {
  success: boolean
  path: string
  created: boolean
  error?: string
}

// 验证路径
export function validatePath(path: string) {
  return request.post<PathValidation>('/file-system/validate-path', { path })
}

// 浏览目录
export function browseDirectory(path: string, showHidden: boolean = false) {
  return request.get<BrowseResult>('/file-system/browse-directory', {
    params: { path, show_hidden: showHidden }
  })
}

// 获取磁盘信息
export function getDiskInfo(paths: string[]) {
  return request.get<Record<string, DiskInfo | null>>('/file-system/disk-info', {
    params: { paths },
    paramsSerializer: (params) => {
      // 处理数组参数
      return params.paths.map((p: string) => `paths=${encodeURIComponent(p)}`).join('&')
    }
  })
}

// 创建目录
export function createDirectory(path: string, recursive: boolean = true) {
  return request.post<CreateDirectoryResult>('/file-system/create-directory', {
    path,
    recursive
  })
}

// 获取默认浏览路径
export function getDefaultBrowsePath() {
  return request.get<{ is_docker: boolean; default_path: string }>(
    '/file-system/default-browse-path'
  )
}

// 检查权限
export function checkPermissions(path: string) {
  return request.get<{ readable: boolean; writable: boolean; executable: boolean }>(
    '/file-system/check-permissions',
    { params: { path } }
  )
}
