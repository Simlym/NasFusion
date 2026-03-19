# Scripts 目录说明

本目录包含 NasFusion 项目的各类运维脚本，按功能分类组织。

## 目录结构

```
scripts/
├── init/          # 初始化脚本
├── migration/     # 数据迁移脚本
├── tools/         # 运维工具脚本
├── debug/         # 调试和测试脚本
└── README.md      # 本文档
```

---

## 📁 init/ - 初始化脚本

用于系统初始化配置的脚本，通常在首次部署或新增功能时运行。

### init_tmdb_settings.py
初始化 TMDB 配置到系统设置表。

**用途**：
- 配置 TMDB API Key
- 配置可选的代理地址

**使用方法**：
```bash
# 添加 TMDB API Key
python scripts/init/init_tmdb_settings.py --api-key YOUR_TMDB_API_KEY

# 添加 TMDB API Key + 代理
python scripts/init/init_tmdb_settings.py --api-key YOUR_API_KEY --proxy http://127.0.0.1:7890

# 查看当前配置
python scripts/init/init_tmdb_settings.py --show
```

**获取 TMDB API Key**：
1. 访问 https://www.themoviedb.org/
2. 注册账号并登录
3. 访问 https://www.themoviedb.org/settings/api
4. 申请 API 密钥（免费）

---

### init_notification_settings.py
初始化通知系统默认配置到 system_settings 表。

**用途**：
- 初始化通知系统基础配置（语言、保留期、消息长度等）
- 初始化各渠道默认配置（Telegram、Email、Webhook）

**使用方法**：
```bash
# 初始化通知配置
python scripts/init/init_notification_settings.py

# 查看当前配置
python scripts/init/init_notification_settings.py --show
```

**配置项**：
- 消息保留天数
- 消息去重窗口
- 最大重试次数
- Telegram/Email/Webhook 渠道配置

---

## 📁 migration/ - 数据迁移脚本

用于数据库结构变更或数据迁移的脚本，通常在版本升级时运行。

### migrate_metadata.py
PT 站点元数据迁移脚本。

**用途**：
- 从旧的 `metadata_cache` 字段迁移到新的独立元数据表
- 对所有现有 PT 站点重新同步元数据
- 清理旧字段

**使用方法**：
```bash
# 执行元数据迁移
python scripts/migration/migrate_metadata.py

# 仅检查是否有旧字段
python scripts/migration/migrate_metadata.py --check-only

# 删除旧字段（PostgreSQL）
python scripts/migration/migrate_metadata.py --drop-old-fields
```

**注意事项**：
- SQLite 不支持直接删除列，需要手动处理
- 建议在迁移前备份数据库

---

## 📁 tools/ - 运维工具脚本

日常运维和管理工具脚本。

### reset_password.py
重置用户密码工具。

**用途**：
- 重置管理员或其他用户的登录密码
- 当忘记密码时快速恢复访问

**使用方法**：
```bash
python scripts/tools/reset_password.py
```

**交互流程**：
1. 输入要重置密码的用户名（默认：admin）
2. 输入新密码（默认：admin）
3. 脚本自动更新数据库

---

### update_tv_episodes.py
批量更新电视剧集数信息。

**用途**：
- 从豆瓣 API 重新获取电视剧元数据
- 更新 `unified_tv_series` 表的 `number_of_episodes` 字段
- 修复缺失的集数信息

**使用方法**：
```bash
python scripts/tools/update_tv_episodes.py
```

**功能**：
- 自动查询有豆瓣 ID 但缺少集数的电视剧
- 批量调用豆瓣 API 获取最新数据
- 显示详细的更新进度和统计

---

## 📁 debug/ - 调试和测试脚本

用于开发调试、问题诊断和功能测试的脚本。

### debug_mteam_auth.py
MTeam API 认证调试工具。

**用途**：
- 检查数据库中的 MTeam 站点配置
- 测试 API Key 解密
- 测试 API 请求（分类列表、健康检查）
- 输出详细的调试信息

**使用方法**：
```bash
python scripts/debug/debug_mteam_auth.py
```

**诊断内容**：
- ✅ 站点配置信息（名称、类型、域名、基础 URL）
- ✅ 认证信息检查（API Key 加密/解密）
- ✅ API 请求测试（分类列表、健康检查）
- ✅ 错误诊断建议

**适用场景**：
- 403 Forbidden 错误排查
- API Key 配置问题诊断
- 代理配置验证

---

### test_identification.py
资源识别功能测试脚本。

**用途**：
- 测试豆瓣 API 适配器
- 测试数据库表创建
- 测试完整资源识别流程
- 验证元数据获取和映射

**使用方法**：
```bash
python scripts/debug/test_identification.py
```

**测试内容**：
1. **豆瓣 API 适配器**：测试元数据获取
2. **数据库表创建**：验证 `unified_movies`、`resource_mappings` 表
3. **完整识别流程**：测试 PT 资源到统一资源的映射

**输出**：
- ✓/✗ 各测试项通过状态
- 详细的元数据信息
- 测试结果汇总

---

## 📝 使用建议

### 首次部署
```bash
# 1. 初始化 TMDB 配置（用于电影识别）
python scripts/init/init_tmdb_settings.py --api-key YOUR_KEY

# 2. 初始化通知系统配置
python scripts/init/init_notification_settings.py
```

### 版本升级
```bash
# 检查是否需要数据迁移
python scripts/migration/migrate_metadata.py --check-only

# 执行迁移（如有需要）
python scripts/migration/migrate_metadata.py
```

### 日常运维
```bash
# 重置管理员密码
python scripts/tools/reset_password.py

# 更新电视剧集数
python scripts/tools/update_tv_episodes.py
```

### 问题诊断
```bash
# 调试 MTeam 认证问题
python scripts/debug/debug_mteam_auth.py

# 测试资源识别功能
python scripts/debug/test_identification.py
```

---

## 💡 开发规范

### 脚本编写规范
1. **编码**：所有脚本使用 UTF-8 编码，添加 `# -*- coding: utf-8 -*-`
2. **文档**：脚本开头添加 docstring 说明用途和使用方法
3. **路径**：使用 `Path(__file__).parent.parent` 添加项目根目录到 Python 路径
4. **错误处理**：使用 try-except 捕获异常，输出友好的错误信息
5. **交互**：提供清晰的输出格式（使用分隔线、状态图标）

### 新增脚本分类规则
- **init/**：初始化配置、首次运行脚本
- **migration/**：数据迁移、结构变更脚本
- **tools/**：日常运维、管理工具
- **debug/**：调试、测试、诊断脚本

### 命名规范
- 使用小写下划线命名：`init_xxx.py`、`migrate_xxx.py`
- 清晰表达脚本用途：`reset_password.py`、`update_tv_episodes.py`
- 避免缩写：使用 `notification` 而非 `notif`

---

## 📚 相关文档

- [项目指导文档](../../CLAUDE.md)
- [数据库设计](../docs/database/README.md)
- [开发规范](../docs/development/README.md)

---

**文档维护者**：NasFusion Team
**最后更新**：2025-12-02
**版本**：v1.0
