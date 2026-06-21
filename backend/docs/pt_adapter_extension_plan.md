# PT 站点适配器扩展 —— 修订实施方案

> **进度**（截至当前）：Phase 0 ✅ / Phase 1 ✅ / Phase 2 ✅ / Phase 3 ✅。
> 单测：`tests/unit/adapters/` 25 passed（工厂路由 / Unit3D 解析 / Generic JSON-API + json_path）。
> 待办：Phase 5 的真站点集成/端到端测试；按需为 Yema 等异形站点写 hook 子类。
> 已落地实现细节与验证中发现的修正：
> - `_http_mixin.py` 的 `_parse_size` 已支持 IEC 单位（GiB/TiB），UNIT3D/JSON 站点使用 IEC。
> - UNIT3D 下载链接统一回退到 `/torrents/download/{id}`（页面 download_check 链接缺前缀时不直接拼接）。
> - `GenericJSONAPIAdapter._parse_timestamp`：Unix 时间戳走 `to_system_tz`（**不可** 走 `parse_pt_site_time`，否则会把 UTC 字符串当本地时间，偏移 8h）。
> - 新增 `utils/json_path.py`（get_by_path / render_template / render_template_obj / safe_int / safe_float）。
> - 已注册 4 个框架：`mteam` / `nexusphp` / `unit3d` / `generic_json_api`。
> - 示例 preset：`blutopia`（unit3d）、`tnode`（generic_json_api）。
>
> **Generic JSON-API hook 边界（已实现）**：规整站点（如 TNode）纯 preset 零代码；
> 异形站点（如 Yema 促销枚举 / 二次请求下载链）= 子类 override
> `_parse_promotion` / `_get_download_url` / `_build_search_request` / `_map_row` 之一。


> 目标：在不破坏现有 MTeam / NexusPHP 站点的前提下，让"新增同框架站点"尽量零代码，
> "新增异形站点"只需写一个薄 hook 子类。覆盖 Unit3D（国际）与 JSON-API（TNode/Yema/Rousi/海胆）两类。

本方案修订自初版评审。核心修订点：

1. **删除"改 `site.type` 语义 + 双工厂 + 迁移 13 个调用点"的大重构**，改为"工厂内部加一层 schema 查表"。
   因为底层数据已经支持：`PTSite.preset_id` 字段已存在并已写入；每个 preset 已带 `schema` 字段。
2. **新增 Phase 0**：把现在只存在于 `NexusPHPAdapter` 的 HTTP 基础设施（重试 / requests fallback /
   Cloudflare 检测 / 限速 / 代理）抽到共享 mixin，两个新 Adapter 都要用。同时固化 `fetch_resources` 的标准返回结构。
3. **重新定位"零代码"承诺**：同框架站点零代码；异形 JSON-API 站点 = preset 配置 + ≤30 行 hook 子类。
   不再承诺 TNode/Yema 纯 JSON——两个参考项目（MoviePilot spider/、PT-depiler definitions）都证明这些站点需要自定义请求 / 下载链 / 标签解析逻辑。

---

## 关键事实（实施前必读）

| 事实 | 位置 | 影响 |
|---|---|---|
| `site.type` 当前 = `preset_id`（如 `hdsky`） | `pt_site_service.py:186` | 不要改它的语义；工厂改为先查 preset.schema |
| `PTSite.preset_id` 字段已存在并已写入 | `models/pt_site.py:16`，`pt_site_service.py:213` | 框架路由信息已齐备，无需迁移 |
| 每个 preset 已带 `schema` 字段 | `site_presets.py:20-30, 各 preset` | 直接作为框架路由 key |
| `fetch_resources` 实际返回 `dict`（非 base 声明的 `list`） | `nexusphp.py:565`，消费方 `pt_resource_service.py:739-755` | 新 Adapter 必须返回 dict 结构 |
| 重试/fallback/CF/限速只在 NexusPHPAdapter | `nexusphp.py:263-494` | 需抽取为共享 mixin（Phase 0） |
| `HDSkyAdapter` 等 4 个空壳类只设 `preset_id` | `nexusphp.py:1692-1731` | schema 查表后可删除 |

### 标准 `fetch_resources` 返回结构（消费方契约）

```python
{
    "resources": [resource_dict, ...],  # 每个 dict 见下方字段
    "total_pages": int,
    "total": int,
    "page_number": int,
    "page_size": int,
}
```

每个 `resource_dict` 必须包含（与 NexusPHP `_parse_torrent_row` 对齐，缺失字段补默认值）：

```
torrent_id, title, subtitle, category, original_category_id, subcategory,
size_bytes, seeders, leechers, completions, published_at,
is_free, is_double_upload, is_discount, promotion_type, promotion_expire_at,
download_url, detail_url, tv_info, detail_fetched,
douban_id, douban_rating, imdb_id, imdb_rating
```

---

## Phase 0：共享基础设施抽取（前置，~0.5 天）

### 0.1 抽取 HTTP mixin

新建 `backend/app/adapters/pt_sites/_http_mixin.py`，把 `NexusPHPAdapter` 中以下方法搬过来（保持行为不变）：

- `_build_proxy_url` / `_mask_proxy_url`
- `_wait_for_rate_limit`
- `_make_request` / `_make_request_with_httpx` / `_make_request_with_requests`
- `_convert_requests_response` / `_is_cloudflare_challenge`
- `_parse_size` / `_parse_size_text` / `_parse_int` / `_parse_time`（纯工具）

```python
class HttpClientMixin:
    """共享 HTTP 请求基础设施：重试、requests fallback、CF 检测、限速、代理。

    依赖宿主类提供的属性（在 __init__ 里设置）：
        self.site_name, self.base_url, self.proxy_url, self.client_config,
        self.user_agent, self.cookie, self.verify_ssl,
        self.request_interval, self.max_retries, self.retry_delay, self.prefer_requests
    子类可 override _get_headers() 定制鉴权头（Cookie / x-api-key / Bearer）。
    """
    def _init_http(self, config: dict) -> None:
        """供宿主 __init__ 调用，集中初始化 HTTP 相关属性。"""
        ...

    def _get_headers(self) -> dict: ...
    async def _make_request(self, url, method="GET", **kwargs): ...
    # ...（从 nexusphp.py 平移）
```

让 `NexusPHPAdapter(HttpClientMixin, BasePTSiteAdapter)`，删掉其内部重复方法，**回归测试现有 NexusPHP 站点不变**。这一步是纯重构，独立可验证。

> 注意：`_get_headers` 在 NexusPHP 注入 `Cookie`；JSON-API/Unit3D 子类 override 它注入 `x-api-key` / `Authorization` / CSRF。

### 0.2 标准化返回结构

在 `_http_mixin.py` 或新 `_resource_schema.py` 提供：

```python
RESOURCE_DEFAULTS = {  # 所有字段的默认值
    "subtitle": "", "subcategory": None, "size_bytes": 0,
    "seeders": 0, "leechers": 0, "completions": 0, "published_at": None,
    "is_free": False, "is_double_upload": False, "is_discount": False,
    "promotion_type": "none", "promotion_expire_at": None,
    "download_url": "", "detail_url": "", "tv_info": None, "detail_fetched": False,
    "douban_id": None, "douban_rating": None, "imdb_id": None, "imdb_rating": None,
}

def normalize_resource(raw: dict) -> dict:
    """补全默认值；要求 raw 至少含 torrent_id/title/category。"""
    return {**RESOURCE_DEFAULTS, **raw}

def make_page_result(resources, page, total_pages=1, total=None) -> dict:
    return {
        "resources": resources,
        "total_pages": total_pages,
        "total": total if total is not None else len(resources),
        "page_number": page,
        "page_size": len(resources),
    }
```

---

## Phase 1：工厂改为 schema 查表（~0.5 天，替代初版整个 Phase 1）

只改 `backend/app/adapters/pt_sites/__init__.py`。**不改 `pt_site_service.py`，不改任何调用点。**

```python
from app.constants.site_presets import get_site_preset
from app.constants.site_presets import (
    SITE_SCHEMA_NEXUSPHP, SITE_SCHEMA_MTEAM, SITE_SCHEMA_UNIT3D,
)
# 新增（Phase 4 在 site_presets 里定义）：SITE_SCHEMA_GENERIC_JSON_API

# 框架 → Adapter（新路由表）
SCHEMA_REGISTRY: Dict[str, Type[BasePTSiteAdapter]] = {
    SITE_SCHEMA_MTEAM: MTeamAdapter,
    SITE_SCHEMA_NEXUSPHP: NexusPHPAdapter,
    SITE_SCHEMA_UNIT3D: Unit3dAdapter,
    "generic_json_api": GenericJSONAPIAdapter,
}

# 旧：站点专属 Adapter（仅向后兼容，逐步清空）
ADAPTER_REGISTRY: Dict[str, Type[BasePTSiteAdapter]] = {
    "mteam": MTeamAdapter,
    "nexusphp": NexusPHPAdapter,
    # hdsky/chdbits/pthome/ourbits 删除——由 schema=nexusphp + preset_id 还原
}


def _resolve_adapter_class(site_type: str, config: Dict[str, Any]) -> Type[BasePTSiteAdapter]:
    # 1) 优先用 preset 的 schema 路由
    preset_id = config.get("preset_id") or site_type
    preset = get_site_preset(preset_id) if preset_id else None
    if preset:
        schema = preset.get("schema")
        if schema in SCHEMA_REGISTRY:
            return SCHEMA_REGISTRY[schema]
    # 2) fallback：旧的 site_type 直查（兼容存量/无 preset 站点）
    cls = ADAPTER_REGISTRY.get(site_type.lower())
    if cls:
        return cls
    raise ValueError(
        f"Unsupported site: type={site_type}, "
        f"schema={preset.get('schema') if preset else None}"
    )


def get_adapter(site_type: str, config: Dict[str, Any], metadata_mappings: Dict = None) -> BasePTSiteAdapter:
    # 关键：确保 config 带上 preset_id，让 Adapter 内部能 get_site_preset
    if "preset_id" not in config:
        config["preset_id"] = site_type  # 现状 site.type 即 preset_id
    adapter_class = _resolve_adapter_class(site_type, config)
    return adapter_class(config, metadata_mappings=metadata_mappings)
```

**回归点**：现有调用 `get_adapter(site.type, config)` 中 `site.type` = `hdsky`：
`config["preset_id"]="hdsky"` → preset.schema=`nexusphp` → `NexusPHPAdapter` → 内部按 `preset_id="hdsky"` 加载选择器/分类。行为与今日一致。删掉 4 个空壳类后无影响。

> 同步 `pt_resource_service._get_adapter` 已经把 `config["preset_id"]` 透传了吗？
> 当前 **没有**——它只塞了 name/base_url/... 没塞 preset_id。
> 所以上面 `get_adapter` 里"若缺则用 site_type 兜底"这一行是必需的安全网；
> 但更干净的做法是顺手在各 `_get_adapter`/调用点补 `config["preset_id"] = site.preset_id or site.type`。
> 两者保留其一即可，建议两者都做（工厂兜底 + 调用点显式）。

---

## Phase 2：Unit3dAdapter（先做，复用度最高，~1–1.5 天）

先做 Unit3D 而非 Generic JSON：它走网页解析，最接近现有 NexusPHP 逻辑，能最大复用 Phase 0 的 mixin，端到端跑通快、风险低。

`backend/app/adapters/pt_sites/unit3d.py`：

```python
class Unit3dAdapter(HttpClientMixin, BasePTSiteAdapter):
    """UNIT3D 框架适配器（BLU/Aither/...）。默认网页解析 /torrents，
    可选 API 模式 /api/torrents（站点开放 token 时）。"""

    def __init__(self, config, metadata_mappings=None):
        super().__init__(config)
        self._init_http(config)
        self.preset = get_site_preset(config.get("preset_id"))
        u3d = (self.preset or {}).get("unit3d_config", {})
        self.torrents_page = u3d.get("torrents_page", "/torrents")
        self.api_path = u3d.get("api_path")          # 有则走 API 模式
        self.api_token = config.get("auth_passkey")  # UNIT3D 个人 API token
        self.selectors = u3d.get("selectors", DEFAULT_UNIT3D_SELECTORS)
        self.category_map = self._build_category_map()  # 同 NexusPHP

    async def fetch_resources(self, page=1, limit=50, **filters) -> dict:
        if self.api_path and self.api_token:
            return await self._fetch_via_api(page, limit, **filters)
        return await self._fetch_via_html(page, limit, **filters)
    # _fetch_via_html / _fetch_via_api / get_resource_detail /
    # download_torrent / authenticate / health_check / fetch_user_profile
```

异形 UNIT3D 站点（如 Aither 资料页改版的特殊选择器）= 写一个子类 override `_parse_torrent_row` 或换 selectors preset，不动通用逻辑。

---

## Phase 3：GenericJSONAPIAdapter（~1.5–2 天）

`backend/app/adapters/pt_sites/generic_json_api.py`：

```python
class GenericJSONAPIAdapter(HttpClientMixin, BasePTSiteAdapter):
    """配置驱动的 JSON-API 适配器，覆盖规整的国内 JSON 站点。
    异形站点（TNode/Yema/Rousi/海胆）通过薄子类 override hook 方法。"""

    def __init__(self, config, metadata_mappings=None):
        super().__init__(config)
        self._init_http(config)
        self.preset = get_site_preset(config.get("preset_id"))
        self.api = (self.preset or {}).get("api_config", {})
        self._csrf_token = None

    # —— hook 方法：异形站点子类 override 这几个就够 ——
    async def _build_search_request(self, page, limit, **filters) -> tuple[str, str, dict]:
        """返回 (method, url, request_kwargs)。默认按 api_config 模板渲染。"""
    async def _get_download_url(self, torrent_id, raw) -> str:
        """默认按 download_url 模板拼接；二次请求型站点子类 override。"""
    def _parse_promotion(self, raw) -> dict:
        """默认按 promotion_rules 匹配；编码特殊的子类 override。"""

    # —— 通用流程：一般不需要 override ——
    async def fetch_resources(self, page=1, limit=50, **filters) -> dict:
        method, url, kw = await self._build_search_request(page, limit, **filters)
        resp = await self._make_request(url, method=method, **kw)
        data = resp.json() if hasattr(resp, "json") else json.loads(resp.text)
        rows = _get_by_path(data, self.api.get("response_path", ""))
        resources = [self._map_row(r) for r in rows]
        return make_page_result(resources, page, self._extract_total_pages(data))

    def _map_row(self, raw) -> dict:
        fm = self.api.get("field_mapping", {})
        mapped = {k: _get_by_path(raw, path) for k, path in fm.items()}
        mapped.update(self._parse_promotion(raw))
        mapped["category"] = self.category_map.get(str(mapped.get("original_category_id")), MEDIA_TYPE_OTHER)
        return normalize_resource(mapped)
```

新工具 `backend/app/utils/json_path.py`：`_get_by_path(obj, "data.data")`、`_render_template(text, ctx)`、`_safe_int`。

**承诺边界（务必写进文档与验收）**：
- ✅ 规整 JSON 站点：仅 preset `api_config`，零代码。
- ✅ TNode/Yema/Rousi/海胆：preset `api_config` + ≤30 行子类（override 上述 1–2 个 hook）。
- ❌ 不承诺这四个站点纯 JSON 零代码——参考 MoviePilot `spider/{tnode,yema,rousi}.py`（180–300 行）与
  PT-depiler `definitions/{yemapt,aither}.ts`（含 `request`/`getTorrentDownloadLink`/`parseTorrentRowForTags` override）。

---

## Phase 4：preset 扩展（~0.5 天）

`site_presets.py`：
- 新增 `SITE_SCHEMA_GENERIC_JSON_API = "generic_json_api"` 并加入 `SITE_SCHEMAS`。
- 新增 1 个 Unit3D 示例 preset（含 `unit3d_config`：selectors + category_map）。
- 新增 1 个 generic_json_api 示例 preset（含 `api_config`：search_url/method/auth/response_path/field_mapping/promotion_rules/download_url 模板）。

---

## Phase 5：测试（~1 天，贯穿各 Phase）

- `tests/adapters/test_factory.py`：`get_adapter` schema 路由 + 兼容 fallback（含 `hdsky`→NexusPHP 回归）。
- `tests/adapters/test_unit3d_adapter.py`：本地 HTML fixture 解析（fixture 从参考项目脱敏抽取，CI 拿不到真实登录态）。
- `tests/adapters/test_generic_json_api_adapter.py`：mock JSON 响应测 field_mapping / response_path / promotion / 分页。
- 回归：现有 NexusPHP / MTeam 站点（Phase 0 重构后必跑）。

---

## 工时重估

| Phase | 内容 | 估时 |
|---|---|---|
| 0 | HTTP mixin 抽取 + 返回结构标准化 + 回归 | 0.5 天 |
| 1 | 工厂 schema 查表 + 删空壳类 | 0.5 天 |
| 2 | Unit3dAdapter（网页模式优先）+ 1 站点端到端 | 1–1.5 天 |
| 3 | GenericJSONAPIAdapter + 1 站点（建议先做规整站点，异形站点 hook 子类增量） | 1.5–2 天 |
| 4 | preset 扩展 | 0.5 天 |
| 5 | 测试（贯穿） | 1 天 |
| **合计** | | **~5–6 天** |

## 落地顺序建议

Phase 0 → Phase 1（合并验证，纯重构不改外部行为）→ Phase 2（Unit3D 端到端，证明新框架链路通）→
Phase 4 的 generic preset → Phase 3（Generic，先规整站点跑通，再按需加异形 hook）→ Phase 5 收尾。

每个 Phase 完成即跑对应测试，Phase 0/1 完成必须先确认现有站点零回归再继续。
