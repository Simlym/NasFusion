# NasFusion 快速入门指南

> 5 分钟快速部署 NasFusion 媒体管理系统

## 📋 前置要求

- Docker 20.10+ 和 Docker Compose 2.0+
- 2GB+ 可用内存
- TMDB API Key（免费申请：https://www.themoviedb.org/settings/api）

## 🚀 三步部署

### 步骤 1：下载项目

```bash
# 从 GitHub 下载最新发布版本
git clone https://github.com/your-repo/NasFusion.git
cd NasFusion

# 或下载指定版本
wget https://github.com/your-repo/NasFusion/archive/refs/tags/v1.0.0.tar.gz
tar -xzf v1.0.0.tar.gz
cd NasFusion-1.0.0
```

### 步骤 2：配置环境

```bash
# 复制配置模板
cp backend/.env.production backend/.env

# 编辑配置文件
nano backend/.env
```

**必须修改的配置**：

```bash
# 1. 生成随机密钥（在终端执行）
openssl rand -hex 32

# 2. 修改以下配置
SECRET_KEY=粘贴上面生成的密钥
JWT_SECRET_KEY=再生成一个密钥并粘贴
DB_POSTGRES_PASSWORD=设置一个强密码
TMDB_API_KEY=你的_TMDB_API_Key
```

### 步骤 3：启动服务

```bash
# 使用发布版本（推荐，无需构建）
docker-compose -f docker-compose.release.yml up -d

# 或使用本地构建版本
docker-compose up -d
```

等待 30 秒后，访问 **http://localhost** 即可开始使用！

---

## 🎯 首次登录

- **地址**: http://localhost
- **用户名**: admin
- **密码**: admin123

⚠️ **重要**：登录后请立即修改密码！

---

## 📦 NAS 用户特别说明

### 群晖 Synology

1. **查看用户 ID**：
```bash
ssh admin@your-nas-ip
id admin
# 输出：uid=1026(admin) gid=100(users)
```

2. **修改配置**：
```bash
# 编辑 backend/.env
PUID=1026
PGID=100

# 修改数据路径
MEDIA_PATH=/volume1/media/NasFusion
DOWNLOAD_PATH=/volume1/downloads/NasFusion
```

3. **使用 NAS 优化配置**：
```bash
docker-compose -f docker-compose.nas.yml up -d
```

### 威联通 QNAP

```bash
# backend/.env
MEDIA_PATH=/share/Multimedia/NasFusion
DOWNLOAD_PATH=/share/Download/NasFusion
```

---

## 🔧 常用命令

```bash
# 查看运行状态
docker-compose -f docker-compose.release.yml ps

# 查看日志
docker-compose -f docker-compose.release.yml logs -f

# 重启服务
docker-compose -f docker-compose.release.yml restart

# 停止服务
docker-compose -f docker-compose.release.yml down

# 升级到最新版本
docker-compose -f docker-compose.release.yml pull
docker-compose -f docker-compose.release.yml up -d
```

---

## 📚 下一步

1. **添加 PT 站点** - 在"站点管理"中添加 MTeam、CHDBits 等站点
2. **同步资源** - 执行首次资源同步，导入 PT 站点种子
3. **创建订阅** - 订阅你喜欢的电视剧，自动下载更新
4. **配置下载器** - 连接 qBittorrent 或 Transmission
5. **整理媒体库** - 自动整理下载的媒体文件

---

## ❓ 常见问题

### 1. 端口 80 被占用？

修改 `docker-compose.release.yml`：

```yaml
nginx:
  ports:
    - "8080:80"  # 改为 8080 端口
```

或设置环境变量：

```bash
export HTTP_PORT=8080
docker-compose -f docker-compose.release.yml up -d
```

访问地址改为：http://localhost:8080

### 2. 数据库连接失败？

检查 `backend/.env` 中的 `DB_POSTGRES_PASSWORD` 是否设置正确。

### 3. TMDB API 配额用完？

免费账号每天有 1000 次请求限制。可以：
- 等待次日重置
- 升级到付费账号
- 暂时禁用元数据刮削功能

### 4. 文件权限错误（NAS）？

确保设置了正确的 `PUID` 和 `PGID`：

```bash
# 查看你的用户 ID
id your-username

# 在 backend/.env 中设置
PUID=实际的用户ID
PGID=实际的用户组ID
```

---

## 🆘 获取帮助

- **完整文档**: https://github.com/your-repo/NasFusion/tree/main/docs
- **问题反馈**: https://github.com/your-repo/NasFusion/issues
- **社区讨论**: https://github.com/your-repo/NasFusion/discussions

---

## 📊 系统状态检查

```bash
# 检查所有服务是否健康
docker-compose -f docker-compose.release.yml ps

# 应该看到类似输出：
# NAME                  STATUS          PORTS
# nasfusion-backend     Up (healthy)    8000/tcp
# nasfusion-frontend    Up (healthy)    80/tcp
# nasfusion-nginx       Up (healthy)    0.0.0.0:80->80/tcp
# nasfusion-postgres    Up (healthy)    5432/tcp
# nasfusion-redis       Up (healthy)    6379/tcp
```

如果有服务显示 `unhealthy`，查看日志：

```bash
docker-compose -f docker-compose.release.yml logs <服务名>
```

---

**祝你使用愉快！** 🎉

如有问题，欢迎在 GitHub 提 Issue 或参与讨论。
