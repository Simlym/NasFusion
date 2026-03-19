# GitHub Actions 自动构建配置指南

本文档说明如何配置 GitHub Actions 自动构建和发布 Docker 镜像到 Docker Hub。

---

## 前置准备

### 1. 创建 Docker Hub 账号

访问 https://hub.docker.com/ 注册账号（如已有则跳过）。

### 2. 创建 Docker Hub Access Token

1. 登录 Docker Hub
2. 点击右上角头像 → **Account Settings**
3. 左侧菜单选择 **Security** → **New Access Token**
4. 填写 Token 信息：
   - **Description**: `GitHub Actions`
   - **Access permissions**: `Read, Write, Delete`
5. 点击 **Generate** 并**复制生成的 Token**（只显示一次，请妥善保存）

---

## 配置 GitHub Secrets

### 步骤 1：进入 GitHub 仓库设置

1. 访问你的 GitHub 仓库
2. 点击 **Settings** 标签
3. 左侧菜单选择 **Secrets and variables** → **Actions**

### 步骤 2：添加 Secrets

点击 **New repository secret** 添加以下两个 Secret：

#### Secret 1: DOCKERHUB_USERNAME

- **Name**: `DOCKERHUB_USERNAME`
- **Value**: 你的 Docker Hub 用户名（例如：`johndoe`）

#### Secret 2: DOCKERHUB_TOKEN

- **Name**: `DOCKERHUB_TOKEN`
- **Value**: 粘贴在步骤 2 中生成的 Access Token

---

## 更新配置文件

### 1. 修改 `docker-compose.release.yml`

将文件中的 `your-dockerhub-username` 替换为你的实际 Docker Hub 用户名：

```yaml
backend:
  image: johndoe/nasfusion-backend:latest  # ← 替换为你的用户名

frontend:
  image: johndoe/nasfusion-frontend:latest  # ← 替换为你的用户名
```

### 2. 修改 `README.docker.md`

将所有 `your-username` 替换为你的 Docker Hub 用户名。

---

## 触发自动构建

### 方式 1：推送到 main 分支

```bash
git add .
git commit -m "feat: initial Docker setup"
git push origin main
```

GitHub Actions 会自动：
1. 构建 `backend` 和 `frontend` 镜像
2. 为两个镜像打上 `latest` 标签
3. 推送到 Docker Hub

### 方式 2：创建版本标签

```bash
# 创建版本标签
git tag v1.0.0
git push origin v1.0.0
```

GitHub Actions 会自动：
1. 构建镜像
2. 打上多个标签：`v1.0.0`、`1.0`、`1`、`latest`
3. 创建 GitHub Release
4. 推送到 Docker Hub

### 方式 3：手动触发

1. 访问 GitHub 仓库的 **Actions** 标签
2. 选择 **Build and Publish Docker Images** 工作流
3. 点击 **Run workflow** → 选择分支 → **Run workflow**

---

## 查看构建状态

### 在 GitHub 上查看

1. 访问仓库的 **Actions** 标签
2. 点击最新的工作流运行
3. 查看详细日志

### 在 Docker Hub 上查看

1. 访问 https://hub.docker.com/
2. 进入你的仓库页面
3. 查看 **Tags** 标签，确认镜像已上传

---

## 镜像标签策略

### 自动生成的标签

| 触发方式 | 生成的标签 | 示例 |
|---------|-----------|------|
| 推送到 `main` 分支 | `latest`, `main` | `johndoe/nasfusion-backend:latest` |
| 推送到 `develop` 分支 | `dev`, `develop` | `johndoe/nasfusion-backend:dev` |
| 推送标签 `v1.2.3` | `v1.2.3`, `1.2`, `1`, `latest` | `johndoe/nasfusion-backend:v1.2.3` |
| Pull Request | `pr-42` | `johndoe/nasfusion-backend:pr-42` |

### 标签优先级

终端用户推荐使用顺序：
1. **指定版本号**：`v1.2.3`（最稳定）
2. **主版本号**：`1`（自动获取最新补丁版本）
3. **latest**：最新稳定版（可能有兼容性变更）
4. **dev**：开发版（可能不稳定）

---

## 支持的架构

GitHub Actions 会自动构建以下架构的镜像：

- `linux/amd64` - x86_64（Intel/AMD 处理器）
- `linux/arm64` - ARM64（Apple Silicon、树莓派 4+、ARM NAS）

Docker 会根据运行平台自动拉取对应架构的镜像。

---

## 故障排查

### 1. 构建失败：认证错误

**错误信息**:
```
Error: Cannot perform an interactive login from a non TTY device
```

**解决方案**:
- 检查 `DOCKERHUB_USERNAME` 和 `DOCKERHUB_TOKEN` 是否正确设置
- 确保 Token 有 `Read, Write, Delete` 权限
- 重新生成 Token 并更新 Secret

### 2. 构建失败：磁盘空间不足

**错误信息**:
```
no space left on device
```

**解决方案**:
在 `.github/workflows/docker-publish.yml` 中添加清理步骤：

```yaml
- name: Free disk space
  run: |
    docker system prune -af
    df -h
```

### 3. 镜像推送失败

**错误信息**:
```
denied: requested access to the resource is denied
```

**解决方案**:
- 确保 Docker Hub 仓库已创建（自动创建需要权限）
- 或手动在 Docker Hub 创建仓库：
  - `nasfusion-backend`
  - `nasfusion-frontend`

### 4. 多架构构建超时

**错误信息**:
```
Error: buildx call failed with exit code 1: executor failed running
```

**解决方案**:
- 减少并行构建的架构数量
- 或使用 GitHub 自托管 Runner（更高性能）

---

## 高级配置

### 1. 仅在标签时推送镜像

修改 `.github/workflows/docker-publish.yml`：

```yaml
on:
  push:
    tags:
      - 'v*.*.*'
```

### 2. 添加更多架构

```yaml
platforms: linux/amd64,linux/arm64,linux/arm/v7
```

### 3. 推送到多个镜像仓库

同时推送到 Docker Hub 和 GitHub Container Registry：

```yaml
- name: Log in to GitHub Container Registry
  uses: docker/login-action@v3
  with:
    registry: ghcr.io
    username: ${{ github.actor }}
    password: ${{ secrets.GITHUB_TOKEN }}

- name: Build and push
  uses: docker/build-push-action@v5
  with:
    tags: |
      ${{ secrets.DOCKERHUB_USERNAME }}/nasfusion-backend:latest
      ghcr.io/${{ github.repository_owner }}/nasfusion-backend:latest
```

---

## 本地测试构建

在推送到 GitHub 之前，可以本地测试构建：

```bash
# 构建后端镜像
docker build -t nasfusion-backend:test ./backend

# 构建前端镜像
docker build -t nasfusion-frontend:test ./frontend

# 测试运行
docker run --rm nasfusion-backend:test
```

---

## 最佳实践

1. **语义化版本**：使用 `v1.0.0` 格式的标签
2. **变更日志**：每次发布时更新 `CHANGELOG.md`
3. **安全扫描**：添加镜像安全扫描步骤（如 Trivy）
4. **通知**：配置构建失败时的通知（Slack、Email）
5. **缓存优化**：使用 GitHub Actions 缓存加速构建

---

## 相关链接

- **Docker Hub**: https://hub.docker.com/
- **GitHub Actions 文档**: https://docs.github.com/en/actions
- **Docker Buildx**: https://docs.docker.com/buildx/working-with-buildx/

---

## 常见问题

### Q: 为什么需要 Access Token 而不是密码？

A: Access Token 更安全：
- 可以限制权限范围
- 可以随时撤销
- 不暴露主账号密码

### Q: 构建需要多长时间？

A: 通常情况：
- 后端镜像：5-10 分钟
- 前端镜像：3-5 分钟
- 总计：10-15 分钟（首次构建）

使用缓存后，后续构建可减少到 2-5 分钟。

### Q: 如何删除旧的镜像标签？

A:
1. 登录 Docker Hub
2. 进入仓库 → Tags
3. 选择要删除的标签 → Delete

或使用 API 自动清理旧标签。

---

**配置完成后**，每次推送代码或创建标签，GitHub Actions 会自动构建并发布镜像到 Docker Hub！
