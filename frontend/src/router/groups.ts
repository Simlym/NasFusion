/**
 * 菜单分组定义
 */
export interface MenuGroup {
  key: string
  label: string
  order: number
}

export const menuGroups: MenuGroup[] = [
  {
    key: 'overview',
    label: '概览',
    order: 1
  },
  {
    key: 'discover',
    label: '发现',
    order: 2
  },
  {
    key: 'media',
    label: '媒体',
    order: 3
  },
  {
    key: 'tools',
    label: '工具',
    order: 4
  },
  {
    key: 'system',
    label: '系统',
    order: 5
  }
]
