import request from '../request'

export interface VersionInfo {
  /** 当前运行版本（镜像构建时由 Git tag 注入；本地源码为 dev） */
  current: string
  /** GitHub 最新发布版本；外网不可达时为 null */
  latest: string | null
  /** 是否有可用更新 */
  has_update: boolean
  /** 最新版本发布页地址 */
  release_url: string
}

/** 获取版本信息（后端带 6 小时缓存，公开接口） */
export const getVersionInfo = () => {
  return request.get<VersionInfo>('/system/version')
}

/** 主动检查更新（需登录）。force=true 跳过缓存立即查询 GitHub */
export const checkVersionUpdate = (force = false) => {
  return request.post<VersionInfo>('/system/version/check', null, {
    params: { force },
  })
}
