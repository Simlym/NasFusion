# NasFusion 前端

基于 Vue 3 + TypeScript + Vite + Element Plus 的现代化前端应用。

## 技术栈

- **框架**: Vue 3.4+
- **语言**: TypeScript 5.3+
- **构建工具**: Vite 5.0+
- **UI库**: Element Plus 2.5+
- **状态管理**: Pinia 2.1+
- **路由**: Vue Router 4.2+
- **HTTP客户端**: Axios 1.6+
- **图表**: ECharts 5.4+

## 项目结构

```
frontend/
├── src/
│   ├── api/              # API接口定义
│   │   ├── modules/      # 各模块的API
│   │   ├── request.ts    # Axios配置
│   │   └── index.ts      # API统一导出
│   ├── assets/           # 静态资源
│   ├── components/       # 组件
│   │   ├── common/       # 通用组件
│   │   └── layout/       # 布局组件
│   ├── composables/      # 组合式函数
│   ├── router/           # 路由配置
│   ├── stores/           # Pinia状态管理
│   ├── styles/           # 全局样式
│   ├── types/            # TypeScript类型定义
│   ├── utils/            # 工具函数
│   ├── views/            # 页面组件
│   ├── App.vue           # 根组件
│   └── main.ts           # 应用入口
├── .env                  # 环境变量
├── .env.development      # 开发环境变量
├── .env.production       # 生产环境变量
├── index.html            # HTML模板
├── package.json          # 项目配置
├── tsconfig.json         # TypeScript配置
├── vite.config.ts        # Vite配置
└── README.md             # 项目说明
```

## 快速开始

### 安装依赖

```bash
npm install
```

### 开发模式

```bash
npm run dev
```

应用将运行在 `http://localhost:5173`

### 构建生产版本

```bash
npm run build
```

### 预览生产构建

```bash
npm run preview
```

## 主要功能模块

### 仪表盘 (Dashboard)
- 系统概览
- 关键指标展示
- 最近活动

### PT站点管理 (Sites)
- 站点配置
- 连接测试
- 同步管理

### 资源浏览 (Resources)
- 资源搜索
- 媒体分类
- 详情查看

### 下载管理 (Downloads)
- 任务列表
- 进度跟踪
- 状态控制

### 媒体文件 (Media)
- 文件管理
- 媒体库集成
- 元数据刮削

### 订阅管理 (Subscriptions)
- 自动订阅
- 匹配规则
- 状态跟踪

### 任务管理 (Tasks)
- 后台任务
- 执行日志
- 任务调度

### 通知中心 (Notifications)
- 消息列表
- 通知渠道
- 推送设置

### 系统设置 (Settings)
- 基础配置
- 下载器设置
- 媒体库配置
- 通知设置
- AI推荐配置

## 开发规范

### 代码风格

项目使用 ESLint 和 Prettier 进行代码格式化：

```bash
# 代码检查
npm run lint

# 代码格式化
npm run format
```

### 组件命名

- 页面组件：使用 PascalCase，如 `Dashboard.vue`
- 通用组件：使用 PascalCase，如 `PageHeader.vue`
- 布局组件：使用 PascalCase，如 `MainLayout.vue`

### 类型定义

- 所有类型定义放在 `src/types/` 目录下
- 使用 TypeScript 的类型系统
- 避免使用 `any` 类型

### API调用

- 所有API接口定义在 `src/api/modules/` 目录下
- 使用统一的请求拦截器处理认证和错误
- API响应使用类型定义

### 状态管理

- 使用 Pinia 进行状态管理
- 每个模块使用独立的 store
- 避免在组件中直接修改 store 状态

## 环境变量

在项目根目录创建 `.env.local` 文件来覆盖默认配置：

```bash
# API地址
VITE_API_BASE_URL=http://your-api-server.com/api

# 其他配置
VITE_APP_TITLE=My NasFusion
```

## 构建优化

- 使用 Vite 的代码分割功能
- 按需加载路由组件
- Element Plus 组件自动导入
- 图片资源优化

## 浏览器支持

- Chrome >= 87
- Firefox >= 78
- Safari >= 14
- Edge >= 88

## 许可证

[项目许可证]
