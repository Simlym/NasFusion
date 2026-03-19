# PostgreSQL 外部访问配置指南

## 快速配置

### 1. 修改 `.env` 文件

```bash
# 如果宿主机没有运行 PostgreSQL，使用默认端口
DB_EXTERNAL_PORT=5432

# 如果宿主机已有 PostgreSQL，建议使用其他端口避免冲突
DB_EXTERNAL_PORT=5433
```

### 2. 重启容器

```bash
docker-compose down
docker-compose up -d
```

### 3. 测试连接

**从宿主机连接：**
```bash
# 方法1：使用 psql 命令
psql -h localhost -p 5432 -U nasfusion -d nasfusion

# 方法2：使用 Docker 进入容器
docker exec -it nasfusion-postgres psql -U nasfusion -d nasfusion
```

**从其他机器连接：**
```bash
psql -h <NAS_IP> -p 5432 -U nasfusion -d nasfusion
```

**使用图形化工具（如 DBeaver、pgAdmin、DataGrip）：**
- **主机**：`<NAS_IP>` 或 `localhost`（本机）
- **端口**：`5432`（或你配置的 `DB_EXTERNAL_PORT`）
- **数据库**：`nasfusion`
- **用户名**：`nasfusion`（或你配置的 `DB_POSTGRES_USER`）
- **密码**：`.env` 中设置的 `DB_POSTGRES_PASSWORD`

---

## 安全建议

### ⚠️ 生产环境注意事项

1. **强密码**：确保 `DB_POSTGRES_PASSWORD` 使用强密码
   ```bash
   # 生成强密码
   openssl rand -base64 32
   ```

2. **防火墙规则**：限制数据库访问IP
   ```bash
   # 群晖防火墙设置
   # 控制面板 → 安全性 → 防火墙 → 编辑规则
   # 仅允许特定 IP 访问 5432 端口

   # Linux iptables 示例
   iptables -A INPUT -p tcp --dport 5432 -s 192.168.1.100 -j ACCEPT
   iptables -A INPUT -p tcp --dport 5432 -j DROP
   ```

3. **不暴露端口**：如果不需要外部访问，注释掉 `docker-compose.yml` 中的 `ports` 配置
   ```yaml
   postgres:
     # ports:
     #   - "${DB_EXTERNAL_PORT:-5432}:5432"  # 注释掉这一行
   ```

4. **使用 SSL 连接**：配置 PostgreSQL SSL（可选）
   ```bash
   # 在容器内启用 SSL
   docker exec -it nasfusion-postgres bash

   # 生成自签名证书
   openssl req -new -x509 -days 365 -nodes -text -out server.crt \
     -keyout server.key -subj "/CN=nasfusion-postgres"

   # 修改 postgresql.conf
   # ssl = on
   # ssl_cert_file = 'server.crt'
   # ssl_key_file = 'server.key'
   ```

---

## 常见问题

### Q1: 连接被拒绝（Connection refused）

**检查项**：
1. 确认容器正在运行：`docker ps | grep postgres`
2. 确认端口映射正确：`docker port nasfusion-postgres`
3. 检查防火墙：`sudo ufw status`（Ubuntu）或群晖控制面板

### Q2: 密码认证失败

**解决方案**：
1. 检查 `.env` 中的密码是否正确
2. 首次修改密码后需要重新创建容器：
   ```bash
   docker-compose down -v  # ⚠️ 会删除数据！
   docker-compose up -d
   ```

### Q3: 如何备份数据库？

```bash
# 备份数据库
docker exec nasfusion-postgres pg_dump -U nasfusion nasfusion > backup.sql

# 或使用 pg_dumpall 备份所有数据库
docker exec nasfusion-postgres pg_dumpall -U nasfusion > backup_all.sql

# 恢复数据库
docker exec -i nasfusion-postgres psql -U nasfusion nasfusion < backup.sql
```

### Q4: 如何查看数据库日志？

```bash
# 查看 PostgreSQL 容器日志
docker logs nasfusion-postgres

# 实时查看日志
docker logs -f nasfusion-postgres
```

---

## 高级配置

### 1. 修改 PostgreSQL 最大连接数

编辑 `docker-compose.yml`，添加环境变量：
```yaml
postgres:
  environment:
    POSTGRES_MAX_CONNECTIONS: 200  # 默认 100
```

### 2. 配置共享内存（提升性能）

```yaml
postgres:
  shm_size: 256mb  # 默认 64mb
```

### 3. 持久化配置文件

```yaml
postgres:
  volumes:
    - ./config/postgresql.conf:/etc/postgresql/postgresql.conf:ro
  command: postgres -c config_file=/etc/postgresql/postgresql.conf
```

---

## 端口冲突解决方案

如果宿主机已有服务占用端口：

| 服务 | 默认端口 | 替代端口建议 |
|-----|---------|------------|
| PostgreSQL | 5432 | 5433, 15432 |
| Nginx | 80 | 8080, 8888 |
| Backend | 8000 | 8001, 9000 |

修改 `.env` 文件：
```bash
DB_EXTERNAL_PORT=5433  # 避免与系统 PostgreSQL 冲突
HTTP_PORT=8080         # 避免与 NAS Web 服务冲突
```

---

**文档版本**: v1.0
**最后更新**: 2025-12-28
**维护者**: Claude Code
