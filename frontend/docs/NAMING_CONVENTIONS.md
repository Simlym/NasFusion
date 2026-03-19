# 前端命名规范

本文档定义了 NasFusion 前端项目的命名规范，以确保代码一致性和可维护性。

## 基本规则

### 1. TypeScript/JavaScript 代码

| 类型 | 命名规范 | 示例 |
|------|---------|------|
| **变量** | camelCase | `userName`, `isLoading`, `currentPage` |
| **常量** | UPPER_SNAKE_CASE | `API_BASE_URL`, `MAX_FILE_SIZE` |
| **函数** | camelCase | `fetchUserData()`, `handleSubmit()` |
| **类** | PascalCase | `UserService`, `DownloadManager` |
| **接口/类型** | PascalCase | `UserProfile`, `PTResource` |
| **枚举** | PascalCase | `MediaType`, `UserRole` |
| **枚举值** | UPPER_SNAKE_CASE | `MediaType.TV_SERIES` |

### 2. Vue 组件

| 类型 | 命名规范 | 示例 |
|------|---------|------|
| **文件名** | PascalCase | `UserProfile.vue`, `SiteList.vue` |
| **组件名** | PascalCase | `PageHeader`, `StatCard` |
| **Props** | camelCase | `userName`, `isDisabled` |
| **Events** | kebab-case | `@update:model-value`, `@item-click` |
| **Slots** | kebab-case | `#header-slot`, `#default` |

### 3. 文件和目录

| 类型 | 命名规范 | 示例 |
|------|---------|------|
| **Vue 组件** | PascalCase | `UserProfile.vue` |
| **TS/JS 文件** | camelCase | `userService.ts`, `formatUtils.ts` |
| **目录** | kebab-case | `api-modules/`, `error-handling/` |
| **类型定义** | camelCase | `user.ts`, `download.ts` |
| **Composables** | camelCase (use 前缀) | `usePagination.ts`, `useLoading.ts` |

## API 数据转换

### 后端响应 (snake_case) → 前端类型 (camelCase)

由于后端 API 使用 snake_case，而前端使用 camelCase，需要进行数据转换。

#### 方案 1：API 层转换（推荐）

```typescript
// src/api/modules/user.ts
import { keysToCamel } from '@/utils/caseConverter'

export async function getUserProfile(): Promise<UserProfile> {
  const response = await request.get('/users/profile')
  return keysToCamel<UserProfile>(response.data)
}
```

#### 方案 2：类型定义兼容

对于简单场景，类型定义可以直接使用 snake_case 以匹配 API：

```typescript
// 直接匹配后端响应结构
export interface User {
  id: number
  user_name: string  // snake_case 匹配后端
  is_active: boolean
  created_at: string
}
```

#### 方案 3：双类型定义（复杂场景）

```typescript
// 后端响应类型（snake_case）
export interface UserApiResponse {
  user_id: number
  user_name: string
  is_active: boolean
  created_at: string
}

// 前端使用类型（camelCase）
export interface User {
  userId: number
  userName: string
  isActive: boolean
  createdAt: string
}

// 转换函数
export function convertUser(apiResponse: UserApiResponse): User {
  return keysToCamel<User>(apiResponse)
}
```

### 发送请求时的转换

```typescript
import { keysToSnake } from '@/utils/caseConverter'

export async function updateUser(data: UserUpdate): Promise<User> {
  // 转换为 snake_case 发送给后端
  const snakeCaseData = keysToSnake(data)
  const response = await request.put('/users', snakeCaseData)
  // 转换响应为 camelCase
  return keysToCamel<User>(response.data)
}
```

## 当前项目状态

### 已使用 camelCase 的类型

- `PTResource` - PT 资源
- `PTSiteStats` - 站点统计
- `UserStats` - 用户统计
- 所有 `Unified*` 资源类型

### 仍使用 snake_case 的类型（待迁移）

- `User` - 用户信息
- `UserProfile` - 用户配置
- `PTSite` - PT 站点配置
- `DownloaderConfig` - 下载器配置
- `DownloadTask` - 下载任务

### 迁移计划

1. **短期**：保持现有 snake_case 类型与后端兼容
2. **中期**：在 API 层添加自动转换
3. **长期**：统一所有类型为 camelCase，使用转换工具处理后端响应

## 最佳实践

### 1. 新类型定义

所有新创建的类型应使用 camelCase：

```typescript
// ✅ 推荐
export interface NewFeature {
  featureId: number
  featureName: string
  isEnabled: boolean
  createdAt: string
}

// ❌ 避免
export interface NewFeature {
  feature_id: number
  feature_name: string
  is_enabled: boolean
  created_at: string
}
```

### 2. API 响应处理

```typescript
// 在 Store 或 API 模块中转换数据
async function fetchData() {
  const response = await api.getData()
  // 转换 snake_case 到 camelCase
  return keysToCamel(response.data)
}
```

### 3. 表单提交

```typescript
// 提交表单时转换为 snake_case
async function submitForm(formData: FormType) {
  const apiData = keysToSnake(formData)
  await api.submit(apiData)
}
```

### 4. 避免混合使用

在同一个模块或组件中，保持命名风格一致：

```typescript
// ✅ 一致的 camelCase
const userData = {
  userId: 1,
  userName: 'admin',
  isActive: true
}

// ❌ 混合使用
const userData = {
  user_id: 1,
  userName: 'admin',
  is_active: true
}
```

## 工具函数

项目提供了以下转换工具（位于 `src/utils/caseConverter.ts`）：

- `snakeToCamel(str)` - 转换字符串
- `camelToSnake(str)` - 转换字符串
- `keysToCamel(obj)` - 递归转换对象键
- `keysToSnake(obj)` - 递归转换对象键
- `convertPaginatedResponse(response)` - 转换分页响应

## 结论

遵循这些命名规范将：
- 提高代码一致性
- 减少团队沟通成本
- 使代码更易于维护
- 符合 Vue/TypeScript 社区标准
