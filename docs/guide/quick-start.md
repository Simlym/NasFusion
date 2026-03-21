# 快速开始

推荐使用 Docker Compose 一键部署，通常 **5 分钟内**即可完成。

## 前置要求

| 组件 | 最低版本 | 说明 |
|------|----------|------|
| Docker | 20.10+ | 容器运行环境 |
| Docker Compose | 2.0+ | 编排工具 |
| 内存 | 2GB+ | 建议 4GB 以上 |
| 硬盘 | 10GB+ | 数据库 + 日志 |

## 第一步：获取代码

```bash
git clone https://github.com/Simlym/NasFusion.git
cd NasFusion
```

## 第二步：配置环境变量

```bash
cp backend/.env.example backend/.env
```

用编辑器打开 `backend/.env`，修改以下关键配置：

```ini
# ✅ 必填：JWT 签名密钥（务必修改，可用以下命令生成）
# openssl rand -hex 32
SECRET_KEY=请替换为随机字符串

# ✅ 必填：TMDB API Key（用于元数据刮削）
# 在 https://www.themoviedb.org/settings/api 申请
TMDB_API_KEY=你的TMDB_API_Key

# 数据库（默认 SQLite，无需改动）
DATABASE_URL=sqlite+aiosqlite:///./data/nasfusion.db
```

::: tip 获取 TMDB API Key
1. 注册 [TMDB 账号](https://www.themoviedb.org/)
2. 进入 **设置 → API → 申请开发者密钥**
3. 填写应用信息（个人使用选"个人"类型即可）
4. 复制 **API 密钥（v3 auth）**
:::

## 第三步：启动服务

```bash
docker compose up -d
```

首次启动会拉取镜像，大约需要 2-5 分钟。

```bash
# 查看启动日志，确认服务正常
docker compose logs -f backend
```

看到以下输出说明启动成功：

```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

## 第四步：访问系统

| 服务 | 地址 |
|------|------|
| **前端界面** | http://localhost:3000 |
| **API 文档** | http://localhost:8000/docs |

<!-- 图：系统登录页截图 -->
<!-- ![登录页](/images/quickstart/login.png) -->

::: tip 图片预留位置
*登录页面截图：显示 NasFusion Logo、用户名密码输入框*
:::

**默认账户**：

- 用户名：`admin`
- 密码：`admin123`

::: warning 安全提示
请在首次登录后**立即前往「设置 → 账户」修改默认密码**，避免安全风险。
:::

## 第五步：初始化配置

登录后，建议按以下顺序完成初始化：

### 5.1 添加 PT 站点

进入 **设置 → PT 站点 → 添加站点**：

<!-- 图：PT 站点配置页截图 -->
<!-- ![PT 站点配置](/images/quickstart/pt-site-config.png) -->

::: tip 图片预留位置
*PT 站点配置页截图：填写站点名称、类型、API Key 的表单*
:::

填写完成后点击 **测试连接**，验证配置是否正确。

### 5.2 触发首次同步

进入 **资源管理 → 同步**，点击 **立即同步**：

<!-- 图：资源同步页截图 -->
<!-- ![资源同步](/images/quickstart/sync-page.png) -->

::: tip 图片预留位置
*资源同步页截图：显示同步进度条、已同步资源数量*
:::

首次同步根据站点资源量，可能需要 5-30 分钟。同步完成后即可在 **资源搜索** 页面检索资源。

### 5.3 连接媒体服务器（可选）

进入 **设置 → 媒体服务器**，填写 Jellyfin/Emby/Plex 的地址和 API Key。

### 5.4 连接下载器

进入 **设置 → 下载器**，填写 qBittorrent 的地址、用户名、密码。

<!-- 图：下载器配置截图 -->
<!-- ![下载器配置](/images/quickstart/downloader-config.png) -->

::: tip 图片预留位置
*下载器配置页截图：qBittorrent 连接设置表单*
:::

## 验证一切正常

完成配置后，可以做一个端到端测试：

1. 在 **资源搜索** 中搜索一部电影
2. 点击 **下载** 触发下载任务
3. 在 **下载管理** 中确认任务已推送到 qBittorrent
4. 收到 Telegram/邮件通知（如果配置了通知）

<!-- 图：资源搜索页截图 -->
<!-- ![资源搜索](/images/quickstart/resource-search.png) -->

::: tip 图片预留位置
*资源搜索页截图：搜索结果列表，展示资源名称、大小、做种数、促销标签*
:::

## 下一步

- [配置说明 →](./configuration) — 完整的配置项参考
- [PT 站点管理 →](../features/pt-sites) — 深入了解站点配置
- [订阅追剧 →](../features/subscription) — 设置自动追更
