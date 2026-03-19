# 演员模型与关联功能实现总结

本文档总结了本次关于演员模型（Actor Models）及其与电影、电视剧关联功能的实现细节。

## 1. 后端实现 (Backend)

### 1.1 数据模型 (Models)
在 `app/models/` 目录下新增了以下 SQLAlchemy 模型：
- **UnifiedPerson**: 存储演员/导演/主创的基本信息（姓名、性别、简介、出生日期、TMDB ID、IMDB ID 等）。
- **MovieCredit**: 关联 `UnifiedPerson` 和 `UnifiedMovie`，存储角色名称（`character`）、职位（`job`）等信息。
- **TVSeriesCredit**: 关联 `UnifiedPerson` 和 `UnifiedTVSeries`，存储角色名称、职位等信息。

### 1.2 数据库迁移 (Alembic)
- 创建了新的迁移脚本 `versions/xxxx_add_unified_person_and_credits.py`。
- 该脚本负责创建 `unified_persons`、`movie_credits` 和 `tv_series_credits` 表。
- 包含了升级 (`upgrade`) 和降级 (`downgrade`)逻辑。

### 1.3 服务层 (Services)
- **PersonService** (`app/services/person_service.py`):
    - 实现了 `sync_movie_credits` 方法：根据 TMDB 的 Cast/Crew 数据，同步更新 `UnifiedPerson` 和 `MovieCredit` 记录。
    - 实现了 `sync_tv_show_credits` 方法：根据 TMDB 的 Cast/Crew 数据，同步更新 `UnifiedPerson` 和 `TVSeriesCredit` 记录。
    - 实现了 `get_person_detail` 方法：获取单个人员的详细信息。
    - 实现了 `get_person_credits` 方法：获取单个人员的参演作品列表（电影和电视剧）。
    - 实现了数据合并策略：优先使用拥有更多信息的数据源更新人员记录，避免覆盖已有详细数据。

- **UnifiedMovieService** (`app/services/identification/unified_movie_service.py`):
    - 在 `refresh_metadata` 方法中集成 `PersonService.sync_movie_credits`，确保电影元数据刷新时自动同步演职人员信息。

- **UnifiedTVSeriesService** (`app/services/identification/unified_tv_series_service.py`):
    - 在 `refresh_metadata` 方法中集成 `PersonService.sync_tv_show_credits`，确保剧集元数据刷新时自动同步演职人员信息。

### 1.4 API 接口 (API Endpoints)
在 `app/api/endpoints/` 下新增了 `persons.py` 或相应路由：
- `GET /persons/{id}`: 获取指定 ID 的人员详情。
- `GET /persons/{id}/credits`: 获取指定 ID 的人员参演作品（包含电影和剧集）。

### 1.5 验证脚本
- 创建了 `verify_actors.py` 脚本，用于模拟创建电影并验证是否正确生成了 `UnifiedPerson` 和 `MovieCredit` 记录。

## 2. 前端实现 (Frontend)

### 2.1 API 模块
- 创建 `src/api/modules/person.ts`，封装了 `getPersonDetail` 和 `getPersonCredits` 请求。
- 在 `src/api/index.ts` 中注册了 `person` 模块。

### 2.2 类型定义 (Types)
- 更新 `src/types/resource.ts`：
    - `UnifiedMovie` 和 `UnifiedTV` 接口中，`directors`、`actors`、`writers`、`creators` 等数组项增加了 `id` 字段。
    - 新增 `UnifiedPerson` 接口定义。
    - 新增 `PersonCredits` 接口定义，包含 `castMovies`、`crewMovies`、`castTv`、`crewTv`。

### 2.3 视图组件 (Views)
- **PersonDetail.vue** (`src/views/PersonDetail.vue`):
    - 新增页面，用于展示人员详情。
    - 左侧显示头像，右侧显示姓名、性别、生日、出生地、部门、别名、简介及外部链接（TMDB/IMDB）。
    - 底部展示参演作品（电影/剧集）和幕后制作（电影/剧集），支持点击跳转到对应的媒体详情页。

- **MovieDetail.vue** (`src/views/MovieDetail.vue`):
    - 更新了导演和主演列表的展示方式。
    - 将纯文本列表改为可点击的链接 (`el-link`)，点击后跳转到 `PersonDetail` 页面。

- **TVSeriesDetail.vue** (`src/views/TVSeriesDetail.vue`):
    - 更新了主创、导演和主演列表的展示方式。
    - 将纯文本列表改为可点击的链接 (`el-link`)，点击后跳转到 `PersonDetail` 页面。

### 2.4 路由 (Router)
- 在 `src/router/index.ts` 中添加了 `/person/:id` 路由，指向 `PersonDetail` 组件。

## 3. 总结
本次更新完成了从数据库底层到前端展示的全链路开发，实现了媒体资源与演职人员的深度关联。用户现在可以在浏览电影或剧集时，点击演员或导演的名字查看其详细资料及其他作品，提升了媒体库的浏览体验。
