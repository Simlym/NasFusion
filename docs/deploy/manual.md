# 手动部署

适用于不使用 Docker 的场景。

## 环境要求

| 组件 | 版本要求 |
|------|----------|
| Python | 3.11+ |
| Node.js | 18+ |
| PostgreSQL | 14+（可选，默认 SQLite） |

## 后端部署

### 1. 安装依赖

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 填写必要配置
```

### 3. 初始化数据库

```bash
alembic upgrade head
```

### 4. 启动后端

**开发模式**：
```bash
python -m app.main
```

**生产模式**（使用 Gunicorn）：
```bash
pip install gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

## 前端部署

### 开发模式

```bash
cd frontend
npm install
npm run dev
```

### 生产构建

```bash
npm run build
# 产物在 dist/ 目录，用 Nginx 托管
```

## Nginx 配置参考

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 前端静态文件
    location / {
        root /path/to/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # 后端 API 代理
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 进程管理（Systemd）

```ini
# /etc/systemd/system/nasfusion.service
[Unit]
Description=NasFusion Backend
After=network.target

[Service]
User=nasfusion
WorkingDirectory=/opt/nasfusion/backend
ExecStart=/opt/nasfusion/backend/venv/bin/python -m app.main
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
systemctl enable nasfusion
systemctl start nasfusion
```
