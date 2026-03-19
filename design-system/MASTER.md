# NasFusion Design System

> **Version:** 1.0.0
> **Last Updated:** 2025-01-20
> **Tech Stack:** Vue3 + TypeScript + Element Plus

---

## 1. 设计理念

### 1.1 核心原则

| 原则 | 描述 |
|------|------|
| **功能优先** | 聚焦核心需求，简化功能和设置 |
| **数据密集** | 高效展示大量资源信息，支持快速浏览和筛选 |
| **响应式** | 适配桌面、平板、移动设备 |
| **一致性** | 统一的视觉语言和交互模式 |

### 1.2 主题风格

| 主题 | 名称 | 风格描述 |
|------|------|---------|
| `light` | **科技浅色** | VS Code Light风格，冷灰调，专业现代 |
| `dark` | **深邃暗夜** | OLED友好，减少眼睛疲劳 |
| `auto` | **跟随系统** | 自动根据系统偏好切换 |

- **Pattern:** Data-Dense Dashboard + Dimensional Layering
- **Keywords:** media management, streaming, PT tracker, high contrast, eye-friendly
- **Best For:** 媒体管理、资源浏览、任务监控、数据展示

---

## 2. 色彩系统

### 2.1 主色板 (共享)

```scss
// 品牌色
$primary:           #409EFF;  // Element Plus 主色 - 信任、专业
$primary-light:     #79BBFF;  // 悬停状态
$primary-dark:      #337ECC;  // 按下状态

// 功能色
$success:           #67C23A;  // 成功、完成、做种中
$warning:           #E6A23C;  // 警告、处理中
$danger:            #F56C6C;  // 错误、危险
$info:              #909399;  // 信息、提示
```

### 2.2 浅色主题 - 科技现代 (Light Theme)

```scss
// 背景层级 (VS Code Light Style)
$bg-base:           #F3F3F3;  // 最底层背景
$bg-page:           #FFFFFF;  // 页面背景
$bg-container:      #F8F8F8;  // 容器背景
$bg-elevated:       #FFFFFF;  // 卡片/弹窗背景
$bg-overlay:        #EAEAEA;  // 悬浮层背景

// 边框色
$border-base:       #E0E0E0;  // 默认边框
$border-light:      #EBEBEB;  // 浅边框
$border-dark:       #D0D0D0;  // 深边框

// 文字色
$text-primary:      #1F1F1F;  // 主要文字
$text-regular:      #424242;  // 常规文字
$text-secondary:    #717171;  // 次要文字
$text-placeholder:  #A0A0A0;  // 占位符
```

### 2.3 深色主题 - 深邃暗夜 (Dark Theme)

```scss
// 背景层级 (由深到浅)
$bg-base:           #0a0a0a;  // 最底层背景
$bg-page:           #121212;  // 页面背景
$bg-container:      #1a1a1a;  // 容器背景
$bg-elevated:       #242424;  // 卡片/弹窗背景
$bg-overlay:        #2a2a2a;  // 悬浮层背景

// 边框色
$border-base:       #333333;  // 默认边框
$border-light:      #404040;  // 浅边框
$border-dark:       #262626;  // 深边框

// 文字色
$text-primary:      #E5EAF3;  // 主要文字
$text-regular:      #CFD3DC;  // 常规文字
$text-secondary:    #A3A6AD;  // 次要文字
$text-placeholder:  #6C6E72;  // 占位符
```

### 2.4 状态色

```scss
// 资源状态
$status-seeding:    #67C23A;  // 做种中 (绿色)
$status-downloading:#409EFF;  // 下载中 (蓝色)
$status-paused:     #E6A23C;  // 暂停 (橙色)
$status-error:      #F56C6C;  // 错误 (红色)
$status-completed:  #67C23A;  // 完成 (绿色)
$status-pending:    #909399;  // 待处理 (灰色)

// 促销标签
$promo-free:        #67C23A;  // 免费 (绿色)
$promo-2x:          #E6A23C;  // 2x上传 (橙色)
$promo-50:          #409EFF;  // 50%下载 (蓝色)
$promo-vip:         #F56C6C;  // VIP (红色)
```

### 2.5 媒体评分色

```scss
// 评分渐变 (0-10分)
$rating-excellent:  #67C23A;  // 8.0+ 优秀
$rating-good:       #85CE61;  // 7.0-7.9 良好
$rating-average:    #E6A23C;  // 6.0-6.9 中等
$rating-poor:       #F56C6C;  // 6.0以下 较差
$rating-none:       #909399;  // 无评分
```

### 2.6 Element Plus 深色主题覆盖

```scss
// CSS Variables 覆盖
:root {
  // 主色
  --el-color-primary: #409EFF;
  --el-color-success: #67C23A;
  --el-color-warning: #E6A23C;
  --el-color-danger: #F56C6C;
  --el-color-info: #909399;

  // 背景色
  --el-bg-color: #121212;
  --el-bg-color-page: #0a0a0a;
  --el-bg-color-overlay: #1a1a1a;

  // 文字色
  --el-text-color-primary: #E5EAF3;
  --el-text-color-regular: #CFD3DC;
  --el-text-color-secondary: #A3A6AD;
  --el-text-color-placeholder: #6C6E72;
  --el-text-color-disabled: #4C4D4F;

  // 边框色
  --el-border-color: #333333;
  --el-border-color-light: #404040;
  --el-border-color-lighter: #4a4a4a;
  --el-border-color-dark: #262626;

  // 填充色
  --el-fill-color: #242424;
  --el-fill-color-light: #2a2a2a;
  --el-fill-color-lighter: #303030;
  --el-fill-color-dark: #1a1a1a;
  --el-fill-color-blank: #121212;
}
```

---

## 3. 字体系统

### 3.1 字体家族

```scss
// 主字体栈
$font-family-base:
  -apple-system,
  BlinkMacSystemFont,
  "Segoe UI",
  Roboto,
  "PingFang SC",      // macOS 中文
  "Microsoft YaHei",   // Windows 中文
  "Hiragino Sans GB",
  "Helvetica Neue",
  Arial,
  sans-serif;

// 等宽字体 (代码、数据)
$font-family-mono:
  "Fira Code",
  "JetBrains Mono",
  "Source Code Pro",
  Menlo,
  Monaco,
  Consolas,
  "Courier New",
  monospace;
```

### 3.2 字号规范

```scss
// 标题字号
$font-size-h1:      28px;   // 页面标题
$font-size-h2:      24px;   // 区块标题
$font-size-h3:      20px;   // 卡片标题
$font-size-h4:      18px;   // 小标题
$font-size-h5:      16px;   // 强调文字

// 正文字号
$font-size-base:    14px;   // 默认正文
$font-size-small:   13px;   // 辅助文字
$font-size-mini:    12px;   // 标签、提示

// 数据展示
$font-size-data:    14px;   // 表格数据
$font-size-stat:    32px;   // 统计数字
```

### 3.3 字重规范

```scss
$font-weight-light:     300;  // 轻量
$font-weight-regular:   400;  // 常规正文
$font-weight-medium:    500;  // 中等强调
$font-weight-semibold:  600;  // 半粗
$font-weight-bold:      700;  // 粗体标题
```

### 3.4 行高规范

```scss
$line-height-tight:     1.3;  // 紧凑 - 标题
$line-height-base:      1.5;  // 默认 - 正文
$line-height-loose:     1.75; // 宽松 - 长文本
$line-height-data:      1.4;  // 数据 - 表格
```

### 3.5 Google Fonts 导入

```css
@import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600&family=Noto+Sans+SC:wght@300;400;500;600;700&display=swap');
```

---

## 4. 间距系统

### 4.1 基础间距单位

```scss
// 基于 4px 的间距系统
$spacing-unit:      4px;

$spacing-xs:        4px;    // 0.25rem - 紧凑间距
$spacing-sm:        8px;    // 0.5rem  - 小间距
$spacing-md:        12px;   // 0.75rem - 中等间距
$spacing-base:      16px;   // 1rem    - 默认间距
$spacing-lg:        20px;   // 1.25rem - 大间距
$spacing-xl:        24px;   // 1.5rem  - 超大间距
$spacing-2xl:       32px;   // 2rem    - 区块间距
$spacing-3xl:       48px;   // 3rem    - 页面间距
```

### 4.2 组件内边距

```scss
// 按钮内边距
$padding-button-mini:     4px 8px;
$padding-button-small:    6px 12px;
$padding-button-default:  8px 16px;
$padding-button-large:    12px 20px;

// 输入框内边距
$padding-input:           8px 12px;

// 卡片内边距
$padding-card-small:      12px;
$padding-card-default:    16px;
$padding-card-large:      20px;

// 表格单元格内边距
$padding-table-cell:      8px 12px;
```

### 4.3 布局间距

```scss
// 页面容器
$padding-page:            24px;
$padding-page-mobile:     16px;

// 侧边栏
$width-sidebar:           220px;
$width-sidebar-collapsed: 64px;

// 内容区域
$max-width-content:       1400px;
$gap-grid:                16px;
```

---

## 5. 组件样式规范

### 5.1 卡片 (Card)

```scss
// 基础卡片
.nf-card {
  background: $bg-elevated;
  border: 1px solid $border-base;
  border-radius: 8px;
  padding: $padding-card-default;

  // 悬停效果
  &:hover {
    border-color: $border-light;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  }

  // 可点击卡片
  &--clickable {
    cursor: pointer;
    transition: all 0.2s ease;

    &:hover {
      transform: translateY(-2px);
    }
  }
}

// 媒体卡片 (海报展示)
.nf-media-card {
  border-radius: 8px;
  overflow: hidden;
  background: $bg-elevated;

  .poster {
    aspect-ratio: 2/3;
    object-fit: cover;
  }

  .info {
    padding: 12px;
  }

  .rating {
    position: absolute;
    top: 8px;
    right: 8px;
    background: rgba(0, 0, 0, 0.75);
    border-radius: 4px;
    padding: 4px 8px;
    font-weight: 600;
  }
}
```

### 5.2 表格 (Table)

```scss
// Element Plus 表格深色覆盖
.el-table {
  --el-table-bg-color: #{$bg-container};
  --el-table-tr-bg-color: #{$bg-container};
  --el-table-header-bg-color: #{$bg-elevated};
  --el-table-row-hover-bg-color: #{$bg-overlay};
  --el-table-border-color: #{$border-base};
  --el-table-text-color: #{$text-regular};
  --el-table-header-text-color: #{$text-primary};
}

// 资源表格特殊样式
.nf-resource-table {
  .resource-name {
    font-weight: 500;
    color: $text-primary;

    &:hover {
      color: $primary;
    }
  }

  .resource-size {
    font-family: $font-family-mono;
    color: $text-secondary;
  }

  .promo-tag {
    display: inline-flex;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: $font-size-mini;
    font-weight: 500;

    &--free { background: rgba($promo-free, 0.2); color: $promo-free; }
    &--2x { background: rgba($promo-2x, 0.2); color: $promo-2x; }
    &--50 { background: rgba($promo-50, 0.2); color: $promo-50; }
  }
}
```

### 5.3 按钮 (Button)

```scss
// 按钮基础样式
.nf-btn {
  border-radius: 6px;
  font-weight: 500;
  transition: all 0.2s ease;

  // 尺寸
  &--mini { padding: $padding-button-mini; font-size: $font-size-mini; }
  &--small { padding: $padding-button-small; font-size: $font-size-small; }
  &--default { padding: $padding-button-default; font-size: $font-size-base; }
  &--large { padding: $padding-button-large; font-size: $font-size-h5; }
}

// 主要按钮
.el-button--primary {
  --el-button-bg-color: #{$primary};
  --el-button-border-color: #{$primary};
  --el-button-hover-bg-color: #{$primary-light};
  --el-button-hover-border-color: #{$primary-light};
  --el-button-active-bg-color: #{$primary-dark};
}

// 图标按钮
.nf-icon-btn {
  width: 32px;
  height: 32px;
  padding: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  background: transparent;
  border: none;
  color: $text-secondary;
  cursor: pointer;

  &:hover {
    background: $bg-overlay;
    color: $text-primary;
  }
}
```

### 5.4 标签 (Tag)

```scss
// 状态标签
.nf-status-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: $font-size-mini;
  font-weight: 500;

  &--seeding {
    background: rgba($status-seeding, 0.15);
    color: $status-seeding;
  }

  &--downloading {
    background: rgba($status-downloading, 0.15);
    color: $status-downloading;
  }

  &--completed {
    background: rgba($status-completed, 0.15);
    color: $status-completed;
  }

  &--error {
    background: rgba($status-error, 0.15);
    color: $status-error;
  }

  &--pending {
    background: rgba($status-pending, 0.15);
    color: $status-pending;
  }
}

// 媒体类型标签
.nf-media-type-tag {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: $font-size-mini;
  text-transform: uppercase;
  font-weight: 600;
  letter-spacing: 0.5px;

  &--movie { background: #7C3AED; color: white; }
  &--tv { background: #2563EB; color: white; }
  &--anime { background: #EC4899; color: white; }
  &--music { background: #10B981; color: white; }
}
```

### 5.5 输入框 (Input)

```scss
// Element Plus 输入框深色覆盖
.el-input {
  --el-input-bg-color: #{$bg-container};
  --el-input-border-color: #{$border-base};
  --el-input-hover-border-color: #{$border-light};
  --el-input-focus-border-color: #{$primary};
  --el-input-text-color: #{$text-primary};
  --el-input-placeholder-color: #{$text-placeholder};
}

// 搜索框
.nf-search-input {
  .el-input__wrapper {
    background: $bg-elevated;
    border-radius: 8px;

    &:hover {
      box-shadow: 0 0 0 1px $border-light;
    }
  }

  .el-input__prefix {
    color: $text-secondary;
  }
}
```

### 5.6 对话框 (Dialog)

```scss
// Element Plus 对话框深色覆盖
.el-dialog {
  --el-dialog-bg-color: #{$bg-elevated};
  --el-dialog-border-radius: 12px;

  .el-dialog__header {
    border-bottom: 1px solid $border-base;
    padding: 16px 20px;
  }

  .el-dialog__body {
    padding: 20px;
  }

  .el-dialog__footer {
    border-top: 1px solid $border-base;
    padding: 12px 20px;
  }
}

// 遮罩层
.el-overlay {
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
}
```

### 5.7 导航 (Navigation)

```scss
// 侧边栏
.nf-sidebar {
  width: $width-sidebar;
  background: $bg-container;
  border-right: 1px solid $border-base;

  &--collapsed {
    width: $width-sidebar-collapsed;
  }
}

// 菜单项
.nf-menu-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 8px;
  margin: 4px 8px;
  color: $text-secondary;
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    background: $bg-overlay;
    color: $text-primary;
  }

  &--active {
    background: rgba($primary, 0.15);
    color: $primary;

    .nf-menu-icon {
      color: $primary;
    }
  }
}

// 顶部导航
.nf-header {
  height: 60px;
  background: $bg-container;
  border-bottom: 1px solid $border-base;
  padding: 0 $padding-page;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
```

### 5.8 进度条 (Progress)

```scss
// 下载进度条
.nf-download-progress {
  .el-progress-bar__outer {
    background: $bg-overlay;
    border-radius: 4px;
  }

  .el-progress-bar__inner {
    border-radius: 4px;
    background: linear-gradient(90deg, $primary, $primary-light);
  }
}

// 任务进度
.nf-task-progress {
  display: flex;
  align-items: center;
  gap: 8px;

  .progress-bar {
    flex: 1;
    height: 6px;
    background: $bg-overlay;
    border-radius: 3px;
    overflow: hidden;

    .progress-fill {
      height: 100%;
      background: $primary;
      transition: width 0.3s ease;
    }
  }

  .progress-text {
    font-family: $font-family-mono;
    font-size: $font-size-small;
    color: $text-secondary;
    min-width: 40px;
    text-align: right;
  }
}
```

---

## 6. 图标规范

### 6.1 图标库选择

**推荐图标库 (按优先级)：**

1. **Element Plus Icons** - 与 Element Plus 组件一致性
   ```bash
   npm install @element-plus/icons-vue
   ```

2. **Heroicons** - 高质量、一致的图标集
   ```bash
   npm install @heroicons/vue
   ```

3. **Lucide Icons** - 简洁、可定制
   ```bash
   npm install lucide-vue-next
   ```

### 6.2 图标尺寸规范

```scss
// 图标尺寸
$icon-size-xs:      14px;   // 标签内图标
$icon-size-sm:      16px;   // 按钮内图标
$icon-size-base:    20px;   // 默认图标
$icon-size-lg:      24px;   // 菜单图标
$icon-size-xl:      32px;   // 功能图标
$icon-size-2xl:     48px;   // 空状态图标
```

### 6.3 图标使用规范

```vue
<!-- 推荐：使用组件方式 -->
<template>
  <el-icon :size="20">
    <Download />
  </el-icon>
</template>

<!-- 不推荐：使用 emoji 作为图标 -->
<!-- 错误示例 -->
<span>📥</span>
```

### 6.4 常用功能图标映射

| 功能 | Element Plus Icon | Heroicons | Lucide |
|------|-------------------|-----------|--------|
| 下载 | Download | ArrowDownTrayIcon | Download |
| 搜索 | Search | MagnifyingGlassIcon | Search |
| 设置 | Setting | Cog6ToothIcon | Settings |
| 用户 | User | UserIcon | User |
| 刷新 | Refresh | ArrowPathIcon | RefreshCw |
| 删除 | Delete | TrashIcon | Trash2 |
| 编辑 | Edit | PencilIcon | Edit |
| 更多 | MoreFilled | EllipsisVerticalIcon | MoreVertical |
| 电影 | Film | FilmIcon | Film |
| 电视 | Monitor | TvIcon | Tv |
| 音乐 | Headset | MusicalNoteIcon | Music |
| 文件夹 | Folder | FolderIcon | Folder |
| 订阅 | Bell | BellIcon | Bell |
| 任务 | Clock | ClockIcon | Clock |

---

## 7. 布局规范

### 7.1 页面布局结构

```
┌─────────────────────────────────────────────────────────┐
│                      Header (60px)                       │
├──────────┬──────────────────────────────────────────────┤
│          │                                               │
│ Sidebar  │                  Main Content                 │
│ (220px)  │                                               │
│          │  ┌────────────────────────────────────────┐  │
│          │  │            Page Header                  │  │
│          │  ├────────────────────────────────────────┤  │
│          │  │                                        │  │
│          │  │            Content Area                │  │
│          │  │                                        │  │
│          │  └────────────────────────────────────────┘  │
│          │                                               │
└──────────┴──────────────────────────────────────────────┘
```

### 7.2 响应式断点

```scss
// 断点定义
$breakpoint-xs:     0;       // 手机竖屏
$breakpoint-sm:     576px;   // 手机横屏
$breakpoint-md:     768px;   // 平板竖屏
$breakpoint-lg:     992px;   // 平板横屏/小桌面
$breakpoint-xl:     1200px;  // 桌面
$breakpoint-2xl:    1400px;  // 大桌面

// 媒体查询混入
@mixin respond-to($breakpoint) {
  @if $breakpoint == 'sm' {
    @media (min-width: $breakpoint-sm) { @content; }
  } @else if $breakpoint == 'md' {
    @media (min-width: $breakpoint-md) { @content; }
  } @else if $breakpoint == 'lg' {
    @media (min-width: $breakpoint-lg) { @content; }
  } @else if $breakpoint == 'xl' {
    @media (min-width: $breakpoint-xl) { @content; }
  } @else if $breakpoint == '2xl' {
    @media (min-width: $breakpoint-2xl) { @content; }
  }
}
```

### 7.3 网格系统

```scss
// 媒体卡片网格
.nf-media-grid {
  display: grid;
  gap: $gap-grid;
  grid-template-columns: repeat(2, 1fr);  // 移动端 2 列

  @include respond-to('sm') {
    grid-template-columns: repeat(3, 1fr);
  }

  @include respond-to('md') {
    grid-template-columns: repeat(4, 1fr);
  }

  @include respond-to('lg') {
    grid-template-columns: repeat(5, 1fr);
  }

  @include respond-to('xl') {
    grid-template-columns: repeat(6, 1fr);
  }
}

// 资源列表网格
.nf-resource-grid {
  display: grid;
  gap: $gap-grid;
  grid-template-columns: 1fr;

  @include respond-to('lg') {
    grid-template-columns: repeat(2, 1fr);
  }

  @include respond-to('2xl') {
    grid-template-columns: repeat(3, 1fr);
  }
}
```

### 7.4 Z-Index 层级

```scss
// Z-Index 管理
$z-index-dropdown:    100;   // 下拉菜单
$z-index-sticky:      200;   // 固定元素
$z-index-fixed:       300;   // 固定定位
$z-index-sidebar:     400;   // 侧边栏
$z-index-header:      500;   // 顶部导航
$z-index-overlay:     600;   // 遮罩层
$z-index-modal:       700;   // 弹窗
$z-index-popover:     800;   // 气泡
$z-index-tooltip:     900;   // 提示
$z-index-message:     1000;  // 消息通知
```

---

## 8. 动效规范

### 8.1 过渡时间

```scss
// 过渡持续时间
$transition-fast:     150ms;  // 快速 - 小元素状态变化
$transition-base:     200ms;  // 默认 - 按钮、输入框
$transition-slow:     300ms;  // 慢速 - 卡片、面板
$transition-slower:   500ms;  // 更慢 - 页面切换

// 缓动函数
$ease-default:        ease;
$ease-in-out:         cubic-bezier(0.4, 0, 0.2, 1);
$ease-out:            cubic-bezier(0, 0, 0.2, 1);
$ease-in:             cubic-bezier(0.4, 0, 1, 1);
```

### 8.2 常用过渡

```scss
// 颜色过渡
.transition-colors {
  transition: color $transition-base $ease-default,
              background-color $transition-base $ease-default,
              border-color $transition-base $ease-default;
}

// 变换过渡
.transition-transform {
  transition: transform $transition-base $ease-out;
}

// 透明度过渡
.transition-opacity {
  transition: opacity $transition-base $ease-default;
}

// 全属性过渡
.transition-all {
  transition: all $transition-base $ease-in-out;
}
```

### 8.3 动画效果

```scss
// 淡入动画
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

// 滑入动画
@keyframes slideInUp {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

// 加载旋转
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

// 脉冲效果 (状态指示)
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
```

### 8.4 减少动效支持

```scss
// 尊重用户偏好
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

## 9. 无障碍规范

### 9.1 颜色对比度

| 文本类型 | 最小对比度 | 推荐对比度 |
|---------|-----------|-----------|
| 正文文本 | 4.5:1 | 7:1 |
| 大文本 (18px+) | 3:1 | 4.5:1 |
| 图标/图形 | 3:1 | 4.5:1 |

### 9.2 焦点状态

```scss
// 键盘焦点样式
:focus-visible {
  outline: 2px solid $primary;
  outline-offset: 2px;
}

// 移除鼠标焦点
:focus:not(:focus-visible) {
  outline: none;
}
```

### 9.3 ARIA 标签

```vue
<!-- 图标按钮必须有 aria-label -->
<el-button
  :icon="Download"
  circle
  aria-label="下载资源"
/>

<!-- 状态指示器需要 aria-live -->
<div aria-live="polite" aria-atomic="true">
  {{ statusMessage }}
</div>

<!-- 表单控件需要 label -->
<el-form-item label="搜索关键词">
  <el-input v-model="keyword" placeholder="输入关键词..." />
</el-form-item>
```

---

## 10. 预交付检查清单

### 10.1 视觉质量

- [ ] 不使用 emoji 作为图标 (使用 SVG/Icon 组件)
- [ ] 所有图标来自统一图标库 (Element Plus Icons / Heroicons)
- [ ] 悬停状态不会导致布局偏移
- [ ] 使用主题变量而非硬编码颜色值

### 10.2 交互体验

- [ ] 所有可点击元素有 `cursor: pointer`
- [ ] 悬停状态提供清晰视觉反馈
- [ ] 过渡动画平滑 (150-300ms)
- [ ] 焦点状态对键盘导航可见

### 10.3 深色主题

- [ ] 文本对比度符合 WCAG AA (4.5:1)
- [ ] 边框在深色背景上可见
- [ ] 禁用状态清晰可辨

### 10.4 布局响应

- [ ] 在 375px 宽度下正常显示
- [ ] 在 768px/1024px/1440px 下布局正确
- [ ] 无水平滚动条
- [ ] 侧边栏折叠正常工作

### 10.5 性能优化

- [ ] 图片使用懒加载
- [ ] 尊重 `prefers-reduced-motion`
- [ ] 骨架屏/加载状态完善

---

## 11. 文件结构

```
frontend/src/
├── styles/
│   ├── variables/
│   │   ├── _colors.scss       # 颜色变量
│   │   ├── _typography.scss   # 字体变量
│   │   ├── _spacing.scss      # 间距变量
│   │   ├── _z-index.scss      # 层级变量
│   │   └── _index.scss        # 变量导出
│   ├── base/
│   │   ├── _reset.scss        # 重置样式
│   │   ├── _typography.scss   # 基础排版
│   │   └── _index.scss        # 基础导出
│   ├── components/
│   │   ├── _card.scss         # 卡片样式
│   │   ├── _table.scss        # 表格样式
│   │   ├── _button.scss       # 按钮样式
│   │   ├── _tag.scss          # 标签样式
│   │   └── _index.scss        # 组件导出
│   ├── element-plus/
│   │   └── _dark-theme.scss   # EP 深色主题覆盖
│   └── main.scss              # 主入口文件
```

---

**Document Maintainer:** Claude Code
**Design Reference:**  Element Plus Dark Theme
**Generated with:** UI/UX Pro Max Skill
