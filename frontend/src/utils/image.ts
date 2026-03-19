/**
 * 图片相关工具函数
 */

/**
 * 将外部图片URL转换为本地代理URL
 *
 * @param url 原始图片URL
 * @returns 代理URL，如果是本地URL则直接返回
 */
export function getProxiedImageUrl(url: string | undefined | null): string {
  if (!url) {
    return ''
  }

  // 如果已经是本地URL，直接返回
  if (url.startsWith('/') || url.startsWith('data:')) {
    return url
  }

  // 如果是外部URL，使用代理
  if (url.startsWith('http://') || url.startsWith('https://')) {
    const baseUrl = import.meta.env.VITE_API_BASE_URL || '/api/v1'
    const encodedUrl = encodeURIComponent(url)
    return `${baseUrl}/image-cache/fetch?url=${encodedUrl}`
  }

  return url
}

/**
 * 批量转换图片URL
 *
 * @param urls 原始图片URL数组
 * @returns 代理URL数组
 */
export function getProxiedImageUrls(urls: (string | undefined | null)[]): string[] {
  return urls.map((url) => getProxiedImageUrl(url))
}

/**
 * 获取媒体服务器图片URL（智能路由）
 * 
 * @param imagePath 图片路径（可能是完整URL或相对路径）
 * @param configId 媒体服务器配置ID
 * @returns 处理后的图片URL
 */
export function getMediaServerImageUrl(imagePath: string | undefined, configId?: number): string {
  if (!imagePath) return ''

  // 1. 外部URL (http/https)，使用通用缓存代理
  if (imagePath.startsWith('http://') || imagePath.startsWith('https://')) {
    return getProxiedImageUrl(imagePath)
  }

  // 2. 内部媒体服务器图片（相对路径），使用专用代理
  // 必须提供 configId 才能构造正确代理链接
  if (configId && imagePath.startsWith('/')) {
    const baseUrl = import.meta.env.VITE_API_BASE_URL || '/api/v1'
    return `${baseUrl}/media-servers/${configId}/image?path=${encodeURIComponent(imagePath)}`
  }

  // 3. 其他情况（如本地静态资源或Data URI），回退到通用逻辑
  return getProxiedImageUrl(imagePath)
}
