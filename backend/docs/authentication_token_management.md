# 认证与 Token 管理机制

## 概述

NasFusion 使用基于 JWT (JSON Web Token) 的双令牌认证机制，提供安全且用户友好的身份验证体验。

## 双令牌机制

### 令牌类型

系统使用两种类型的 JWT 令牌：

| 令牌类型 | 用途 | 有效期 | 存储位置 |
|---------|------|--------|---------|
| **Access Token** (访问令牌) | 访问受保护的 API 资源 | 30 分钟 | localStorage (`token`) |
| **Refresh Token** (刷新令牌) | 获取新的访问令牌 | 7 天 | localStorage (`refresh_token`) |

### 设计原则

1. **安全性优先**：访问令牌有效期短（30分钟），减少令牌泄露风险
2. **用户体验**：刷新令牌有效期长（7天），减少重复登录
3. **无感知刷新**：自动在后台刷新令牌，用户无需感知

## 认证流程

### 1. 用户登录

```
用户提交用户名密码
       ↓
后端验证用户身份
       ↓
生成 Access Token (30分钟) + Refresh Token (7天)
       ↓
前端保存到 localStorage
       ↓
前端保存用户信息到 localStorage
       ↓
跳转到首页
```

**登录接口**: `POST /api/v1/auth/login`

**请求体**:
```json
{
  "username": "admin",
  "password": "password"
}
```

**响应体**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800,
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### 2. 访问受保护资源

```
前端发起 API 请求
       ↓
请求拦截器检查 Token 是否即将过期（剩余 < 5分钟）
       ↓
   是：主动刷新 Token → 使用新 Token 发起请求
   否：直接使用当前 Token 发起请求
       ↓
后端验证 Token 有效性
       ↓
   有效：返回资源数据
   无效：返回 401 错误
       ↓
前端响应拦截器捕获 401
       ↓
尝试使用 Refresh Token 刷新
       ↓
   成功：重试原请求
   失败：清除所有令牌，跳转登录页
```

### 3. Token 刷新机制

#### 主动刷新（推荐）

前端在请求拦截器中检测到 Token 即将过期时，**主动刷新**：

```typescript
// frontend/src/api/request.ts
if (isTokenExpiringSoon() && !isRefreshing) {
  // 提前 5 分钟主动刷新
  await refreshAccessToken()
}
```

**优点**：
- ✅ 无感知刷新，用户体验好
- ✅ 避免请求失败
- ✅ 减少 401 错误重试

#### 被动刷新（兜底）

当访问令牌已过期，后端返回 401 错误时，前端**被动刷新**：

```typescript
// 响应拦截器捕获 401
if (error.response.status === 401 && !isRefreshing) {
  await refreshAccessToken()
  // 重试原请求
  return request(error.config)
}
```

**刷新接口**: `POST /api/v1/auth/refresh`

**请求体**:
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**响应体**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800,
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**注意**：刷新成功后会返回新的 Access Token 和 Refresh Token（推荐做法，防止 Refresh Token 被滥用）

### 4. 路由守卫验证

前端路由跳转时自动验证登录状态：

```typescript
// frontend/src/router/index.ts
router.beforeEach(async (to, from, next) => {
  if (requiresAuth) {
    // 检查是否有 Token
    if (!token) {
      return next({ name: 'Login' })
    }

    // 检查是否有用户信息（从 localStorage 恢复或从后端获取）
    if (!userStore.user) {
      try {
        await userStore.fetchCurrentUser()
      } catch (error) {
        // Token 无效，跳转登录
        await userStore.logout()
        return next({ name: 'Login' })
      }
    }
  }

  next()
})
```

### 5. 用户登出

```
用户点击登出按钮
       ↓
清除 localStorage (token, refresh_token, user_info)
       ↓
清空 Pinia Store 状态
       ↓
跳转到登录页
```

## JWT Token 结构

### Access Token Payload

```json
{
  "sub": "1",              // 用户ID
  "username": "admin",     // 用户名
  "role": "admin",         // 角色
  "type": "access",        // 令牌类型
  "iat": 1700000000,       // 签发时间
  "exp": 1700001800        // 过期时间（iat + 30分钟）
}
```

### Refresh Token Payload

```json
{
  "sub": "1",              // 用户ID
  "type": "refresh",       // 令牌类型
  "iat": 1700000000,       // 签发时间
  "exp": 1700604800        // 过期时间（iat + 7天）
}
```

**安全设计**：
- Refresh Token 仅包含用户 ID，减少信息泄露
- 通过 `type` 字段区分令牌类型，防止混用
- 刷新时重新验证用户状态（`is_active`、`is_locked`）

## 配置说明

### 后端配置

**配置文件**: `backend/.env`

```env
# JWT 配置
JWT_SECRET_KEY=your-secret-key-here                # JWT 签名密钥（必须配置）
JWT_ALGORITHM=HS256                                 # 加密算法
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30                  # 访问令牌过期时间（分钟）
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7                     # 刷新令牌过期时间（天）
```

**推荐配置**：

| 场景 | Access Token | Refresh Token | 说明 |
|------|-------------|--------------|------|
| **生产环境（推荐）** | 30 分钟 | 7 天 | 平衡安全性和用户体验 |
| 高安全环境 | 15 分钟 | 1 天 | 金融、医疗等敏感系统 |
| 开发环境 | 60 分钟 | 30 天 | 减少频繁登录干扰开发 |
| 内网环境 | 120 分钟 | 30 天 | 低风险环境 |

### 前端配置

**Token 存储键名**:
```typescript
// frontend/src/api/request.ts
const TOKEN_KEY = 'token'                // 访问令牌
const REFRESH_TOKEN_KEY = 'refresh_token' // 刷新令牌
const TOKEN_EXPIRES_KEY = 'token_expires_at' // 过期时间戳
const USER_INFO_KEY = 'user_info'        // 用户信息
```

**主动刷新阈值**:
```typescript
// 提前 5 分钟刷新
const fiveMinutes = 5 * 60 * 1000
return Date.now() + fiveMinutes > expiresTime
```

## 安全机制

### 1. Token 签名验证

所有 Token 使用 HMAC-SHA256 签名，确保：
- ✅ Token 未被篡改
- ✅ Token 由本系统签发

### 2. 过期时间验证

后端解码 Token 时自动验证 `exp` 字段：
```python
# backend/app/utils/security.py
payload = jwt.decode(token, secret_key, algorithms=[JWT_ALGORITHM])
# 自动验证过期时间，过期则抛出 JWTError
```

### 3. 令牌类型验证

刷新接口严格验证令牌类型：
```python
# backend/app/api/v1/auth.py
if payload.get("type") != "refresh":
    raise HTTPException(status_code=401, detail="令牌类型错误")
```

防止使用 Access Token 刷新。

### 4. 用户状态验证

刷新令牌时重新检查用户状态：
```python
user = await UserService.get_by_id(db, user_id)
if user is None or not user.is_active:
    raise HTTPException(status_code=401, detail="用户不存在或已被禁用")
```

确保被禁用的用户无法通过旧令牌继续访问。

### 5. 防重放攻击

**现有机制**：
- Token 包含签发时间 (`iat`) 和过期时间 (`exp`)
- Refresh Token 刷新后返回新令牌，旧令牌应被丢弃

**可选增强**（未实现，可扩展）：
- Token 黑名单（Redis 存储已撤销的 Token）
- Refresh Token 单次使用（数据库记录已使用的 Refresh Token）

## 常见问题

### Q1: 为什么 Token 过期时间从 5 小时改为 30 分钟？

**A**: 基于安全最佳实践：
- ✅ **减少泄露风险**：即使 Token 被窃取，30 分钟后自动失效
- ✅ **双令牌机制**：Refresh Token (7天) 保证用户体验
- ✅ **符合 OAuth 2.0 规范**：推荐短期 Access Token + 长期 Refresh Token

### Q2: 为什么需要主动刷新机制？

**A**:
- ❌ **被动刷新的问题**：用户操作时突然返回 401，体验差
- ✅ **主动刷新的好处**：提前 5 分钟刷新，用户无感知
- ✅ **减少请求失败**：避免高并发场景下多个请求同时触发刷新

### Q3: 刷新失败会怎样？

**A**:
1. **主动刷新失败**：继续使用原 Token，让后端判断是否有效
2. **被动刷新失败**：清除所有令牌，跳转登录页
3. **用户体验**：仅在 Refresh Token 也过期时才需要重新登录（7天）

### Q4: 为什么用户信息要保存到 localStorage？

**A**:
- ✅ **页面刷新恢复**：避免每次刷新页面都请求 `/auth/me`
- ✅ **路由守卫优化**：快速验证登录状态
- ✅ **减少 API 调用**：降低服务器压力

**注意**：敏感信息（如密码）不会存储，仅存储展示信息（用户名、角色等）

### Q5: Token 存储在 localStorage 安全吗？

**A**:
- ⚠️ **风险**：XSS 攻击可窃取 localStorage
- ✅ **缓解措施**：
  - 前端使用 Vue 3 自动转义防止 XSS
  - 后端设置 CSP (Content Security Policy) 头
  - Token 有效期短（30分钟）
  - 定期刷新 Token（旧 Token 失效）
- 🔄 **替代方案**：HttpOnly Cookie（需要修改架构，前后端同域名）

### Q6: 如何强制用户重新登录？

**A**: 管理员可通过以下方式：
1. **禁用用户**：设置 `user.is_active = False`，刷新 Token 时会拦截
2. **锁定账户**：设置 `user.is_locked = True`
3. **修改密码**：建议同时记录 `password_changed_at`，Token 中可包含此时间戳验证

### Q7: 如何在多设备间管理登录？

**A**: 当前实现支持多设备同时登录（每次登录生成新 Token）。

**可选扩展**（未实现）：
- 单点登录：数据库记录当前有效的 Refresh Token，登录时撤销旧 Token
- 设备管理：记录登录设备信息，允许用户远程登出

## 代码示例

### 后端：验证 Token

```python
# backend/app/core/dependencies.py
from fastapi import Depends, HTTPException
from app.utils.security import decode_access_token

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    token = credentials.credentials

    # 解码并验证 Token
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="无效的认证凭据")

    # 获取用户
    user_id = int(payload.get("sub"))
    user = await UserService.get_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="用户不存在")

    return user
```

### 前端：自动刷新 Token

```typescript
// frontend/src/api/request.ts
request.interceptors.request.use(async (config) => {
  const token = getToken()

  if (token && isTokenExpiringSoon()) {
    const refreshToken = getRefreshToken()

    if (refreshToken && !isRefreshing) {
      isRefreshing = true

      try {
        const response = await axios.post('/api/v1/auth/refresh', {
          refresh_token: refreshToken
        })

        setToken(response.data.access_token, response.data.expires_in)
        setRefreshToken(response.data.refresh_token)

        config.headers.Authorization = `Bearer ${response.data.access_token}`
      } catch (error) {
        // 刷新失败，使用原 Token（让后端判断）
        config.headers.Authorization = `Bearer ${token}`
      } finally {
        isRefreshing = false
      }
    }
  } else if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }

  return config
})
```

## 最佳实践

### 开发建议

1. ✅ **使用强密钥**：`JWT_SECRET_KEY` 至少 32 字符，生产环境使用随机生成
2. ✅ **HTTPS 传输**：生产环境必须使用 HTTPS，防止 Token 被窃听
3. ✅ **短期 Access Token**：建议 15-60 分钟
4. ✅ **适度 Refresh Token**：建议 7-30 天
5. ✅ **日志记录**：记录登录、刷新、登出操作（审计跟踪）
6. ✅ **监控告警**：监控异常刷新频率（可能的攻击行为）

### 生产环境检查清单

- [ ] `JWT_SECRET_KEY` 已设置为强随机密钥
- [ ] HTTPS 已启用
- [ ] CORS 配置正确（限制允许的域名）
- [ ] CSP 头已配置（防止 XSS）
- [ ] Token 过期时间符合安全策略
- [ ] 日志记录敏感操作
- [ ] 监控系统已部署

## 相关文件

### 后端

- `backend/app/api/v1/auth.py` - 认证接口（登录、刷新、获取当前用户）
- `backend/app/utils/security.py` - Token 生成和验证
- `backend/app/core/dependencies.py` - Token 依赖注入
- `backend/app/core/config.py` - JWT 配置
- `backend/app/schemas/user.py` - Token 响应模型

### 前端

- `frontend/src/api/request.ts` - Axios 拦截器（自动刷新）
- `frontend/src/stores/user.ts` - 用户状态管理（持久化）
- `frontend/src/router/index.ts` - 路由守卫（验证登录）
- `frontend/src/api/modules/user.ts` - 用户 API 封装

## 更新日志

| 日期 | 版本 | 变更内容 |
|------|------|---------|
| 2024-01-XX | v1.1 | 添加双令牌机制，优化主动刷新 |
| 2024-01-XX | v1.0 | 初始版本，单 Token 机制 |

## 参考资料

- [RFC 7519: JSON Web Token (JWT)](https://tools.ietf.org/html/rfc7519)
- [OAuth 2.0 RFC 6749](https://tools.ietf.org/html/rfc6749)
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
