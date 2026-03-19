/**
 * NasFusion 图标注册表
 * 使用 Lucide 图标集（通过 Iconify）
 * 格式：lucide:<icon-name>
 *
 * 使用方法：
 *   import { icons } from '@/utils/icons'
 *   <AppIcon :name="icons.dashboard" />
 *   或直接用字符串：<AppIcon name="lucide:layout-dashboard" />
 */
export const icons = {
  // ────── 导航 ──────
  dashboard:      'lucide:home',
  overview:       'lucide:bar-chart-2',

  // ────── 发现 ──────
  search:         'lucide:search',
  resources:      'lucide:compass',
  persons:        'lucide:users',

  // ────── 媒体库 ──────
  mediaLibrary:   'lucide:clapperboard',
  movie:          'lucide:film',
  tv:             'lucide:tv-2',
  anime:          'lucide:sparkles',
  music:          'lucide:music',
  book:           'lucide:book-open',
  adult:          'lucide:eye-off',

  // ────── 媒体管理 ──────
  subscription:   'lucide:rss',
  download:       'lucide:download',
  downloadQueue:  'lucide:clock-3',
  downloadPause:  'lucide:pause-circle',
  downloadDone:   'lucide:check-circle-2',
  downloadActive: 'lucide:loader',
  files:          'lucide:folder-open',
  fileManager:    'lucide:folder-open',
  mediaServer:    'lucide:server',

  // ────── 工具 ──────
  aiAgent:        'lucide:bot',
  tasks:          'lucide:list-checks',
  taskQueue:      'lucide:activity',
  taskHistory:    'lucide:history',
  taskScheduled:  'lucide:alarm-clock',
  notifications:  'lucide:bell',
  notificationRule: 'lucide:bell-ring',

  // ────── 系统 ──────
  systemLog:      'lucide:file-text',
  settings:       'lucide:settings',
  storage:        'lucide:hard-drive',
  ptSites:        'lucide:globe',
  downloader:     'lucide:download-cloud',
  organizeRule:   'lucide:folder-sync',
  scraping:       'lucide:scan-search',
  notifSettings:  'lucide:bell-ring',
  security:       'lucide:shield-check',

  // ────── 动作 ──────
  add:            'lucide:plus',
  edit:           'lucide:pencil',
  delete:         'lucide:trash-2',
  refresh:        'lucide:refresh-cw',
  filter:         'lucide:filter',
  sort:           'lucide:arrow-up-down',
  upload:         'lucide:upload',
  link:           'lucide:link',
  copy:           'lucide:copy',
  check:          'lucide:check',
  close:          'lucide:x',
  more:           'lucide:more-horizontal',
  expand:         'lucide:chevron-right',
  collapse:       'lucide:chevron-left',

  // ────── 状态 ──────
  success:        'lucide:check-circle-2',
  warning:        'lucide:alert-triangle',
  error:          'lucide:x-circle',
  info:           'lucide:info',
  loading:        'lucide:loader',
  empty:          'lucide:inbox',

  // ────── 界面 ──────
  fold:           'lucide:menu',
  unfold:         'lucide:menu',
  sun:            'lucide:sun',
  moon:           'lucide:moon',
  cloud:          'lucide:cloud',
  user:           'lucide:user',
  logout:         'lucide:log-out',
  lock:           'lucide:lock',
  eye:            'lucide:eye',
  eyeOff:         'lucide:eye-off',
  star:           'lucide:star',
  heart:          'lucide:heart',
  tag:            'lucide:tag',
  calendar:       'lucide:calendar',
  timer:          'lucide:timer',
  histogram:      'lucide:bar-chart-2',
  collection:     'lucide:library',
  picture:        'lucide:image',
  video:          'lucide:video',
  watchHistory:   'lucide:clock',

  // ────── PT站点 ──────
  ptSearch:       'lucide:search',
  ptSubscribe:    'lucide:bookmark',
  ptRss:          'lucide:rss',
  ptConnect:      'lucide:plug',
  ptHealth:       'lucide:heart-pulse',
} as const

export type IconName = keyof typeof icons
export type IconId = (typeof icons)[IconName]
