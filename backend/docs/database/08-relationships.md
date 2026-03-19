# 数据关系和约束

## 1. 外键关系图

```
users (1) → (∞) user_profiles
users (1) → (∞) notification_channels
users (1) → (∞) subscriptions

pt_sites (1) → (∞) pt_resources
pt_resources (1) → (1) resource_mappings
unified_resources (1) → (∞) resource_mappings
unified_resources (1) → (∞) download_tasks
download_tasks (1) → (∞) media_files
subscriptions (1) → (∞) subscription_check_logs

notification_channels (1) → (∞) notification_logs

scheduled_tasks (1) → (∞) task_queue
```

---

## 2. 业务规则约束

### 2.1 数据完整性
- 每个PT资源只能关联一个统一资源
- 每个统一资源可以有多个推荐资源，但只能有一个主推荐
- 订阅状态转换必须遵循业务规则
- 下载任务状态机管理

### 2.2 数据一致性
- 级联删除策略
- 触发器维护统计字段
- 事务保证数据一致性

### 2.3 业务逻辑约束
- 用户评分范围限制
- 文件大小合理性检查
- 时间戳逻辑验证
