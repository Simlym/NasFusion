# -*- coding: utf-8 -*-
"""
通用 JSON API 站点适配器（配置驱动）

覆盖规整的国内 JSON-API 站点（TNode / 海胆 等）。差异通过预设的 api_config 表达：
认证、请求体模板、响应路径、字段映射、促销规则、下载链接模板。

异形站点（如 Yema 的促销枚举编码、二次请求下载链）= 写一个薄子类，
override 下列 hook 之一即可，无需复制通用流程：
    _build_search_request / _get_download_url / _parse_promotion / _map_row

api_config 结构示例见 backend/docs/pt_adapter_extension_plan.md 与 TNode 预设。
"""
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin

import httpx

from app.adapters.base import BasePTSiteAdapter
from app.adapters.pt_sites._http_mixin import HttpClientMixin
from app.adapters.pt_sites._resource_schema import normalize_resource, make_page_result
from app.utils.json_path import get_by_path, render_template, render_template_obj, safe_int, safe_float
from app.utils.timezone import to_system_tz
from app.utils.tv_parser import extract_tv_info
from app.constants import (
    MEDIA_TYPE_ANIME,
    MEDIA_TYPE_MOVIE,
    MEDIA_TYPE_MUSIC,
    MEDIA_TYPE_OTHER,
    MEDIA_TYPE_TV,
)
from app.constants.site_presets import get_site_preset

logger = logging.getLogger(__name__)


class GenericJSONAPIAdapter(HttpClientMixin, BasePTSiteAdapter):
    """配置驱动的 JSON-API 适配器。"""

    def __init__(self, config: Dict[str, Any], metadata_mappings: Optional[Dict] = None):
        super().__init__(config)
        self._init_http(config)

        self.preset_id = config.get("preset_id")
        self.preset = get_site_preset(self.preset_id) if self.preset_id else None

        self.passkey = config.get("auth_passkey", "")
        self.api_key = config.get("auth_passkey", "")  # 某些站用 passkey 字段存 api key
        self.domain = config.get("domain", "")
        self.metadata_mappings = metadata_mappings or {}
        self.site_id = None

        # api_config（预设与 config 合并）
        api = config.get("api_config") or {}
        if self.preset and "api_config" in self.preset:
            api = {**self.preset["api_config"], **api}
        self.api = api

        self.category_map = self._build_category_map()

        # CSRF token 缓存
        self._csrf_token: Optional[str] = None

    def _build_category_map(self) -> Dict[str, str]:
        if not self.preset:
            return {}
        if "category_details" in self.preset:
            return {
                str(cat_id): details["mapped_category"]
                for cat_id, details in self.preset["category_details"].items()
            }
        if "categories" in self.preset:
            return {str(k): v for k, v in self.preset["categories"].items()}
        return {}

    # ==================== 鉴权头 ====================

    def _get_headers(self) -> Dict[str, str]:
        """JSON-API 请求头：JSON Accept + 可选 api_key / CSRF / Cookie。"""
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json; charset=utf-8",
        }
        if self.cookie:
            headers["Cookie"] = self.cookie

        auth = self.api.get("auth") or {}
        # API key header（如 x-api-key）
        key_header = auth.get("api_key_header")
        if key_header and self.api_key:
            headers[key_header] = self.api_key
        # Bearer
        if auth.get("bearer") and self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        # CSRF
        csrf = self.api.get("csrf") or {}
        if csrf.get("enabled") and self._csrf_token:
            headers[csrf.get("header", "X-CSRF-TOKEN")] = self._csrf_token

        if self.base_url:
            headers["Referer"] = self.base_url
        return headers

    # ==================== CSRF token（hook） ====================

    async def _ensure_csrf_token(self) -> None:
        """若配置需要 CSRF，确保已获取 token。子类可 override。"""
        csrf = self.api.get("csrf") or {}
        if not csrf.get("enabled") or self._csrf_token:
            return
        token_url = urljoin(self.base_url, csrf.get("token_url", "/"))
        pattern = csrf.get("regex", r'<meta name="x-csrf-token" content="(.+?)">')
        try:
            resp = await self._make_request(token_url)
            m = re.search(pattern, resp.text)
            if m:
                self._csrf_token = m.group(1)
                logger.info(f"[{self.site_name}] 获取 CSRF token 成功")
            else:
                logger.warning(f"[{self.site_name}] 未在页面匹配到 CSRF token")
        except Exception as e:
            logger.error(f"[{self.site_name}] 获取 CSRF token 失败: {e}")

    # ==================== 请求构建（hook） ====================

    async def _build_search_request(
        self, page: int, limit: int, **filters
    ) -> Tuple[str, str, Dict[str, Any]]:
        """
        构建搜索请求，返回 (method, url, request_kwargs)。

        默认按 api_config.search 渲染模板。请求体/查询参数中可用占位符：
            {{keyword}} {{page}} {{size}}
        子类可 override 处理特殊编码（如 Yema 的嵌套 pageParam）。
        """
        search = self.api.get("search") or {}
        method = (search.get("method") or "POST").upper()
        url = urljoin(self.base_url, search.get("url", ""))

        page_base = search.get("page_base", 1)
        context = {
            "keyword": filters.get("keyword") or "",
            "page": page - 1 + page_base,
            "size": limit,
            "category": filters.get("category") or filters.get("categories") or "",
        }

        kwargs: Dict[str, Any] = {}
        if "body" in search:
            kwargs["json"] = render_template_obj(search["body"], context)
        if "params" in search:
            kwargs["params"] = render_template_obj(search["params"], context)

        return method, url, kwargs

    # ==================== 列表获取 ====================

    async def fetch_resources(
        self, page: int = 1, limit: int = 50, **filters
    ) -> Dict[str, Any]:
        try:
            await self._ensure_csrf_token()

            method, url, kwargs = await self._build_search_request(page, limit, **filters)
            logger.info(f"[{self.site_name}] 请求 {method} {url} (filters: {filters})")

            response = await self._make_request(url, method=method, **kwargs)
            data = self._response_json(response)

            resp_cfg = self.api.get("response") or {}
            rows = get_by_path(data, resp_cfg.get("list_path", ""), default=[]) or []

            resources = [self._map_row(r) for r in rows]
            resources = [r for r in resources if r]  # 过滤掉无效行

            total_pages = self._extract_total_pages(data, page)
            total = get_by_path(data, resp_cfg.get("total_path", ""))
            return make_page_result(
                resources, page, total_pages=total_pages,
                total=safe_int(total) if total is not None else None,
            )
        except Exception as e:
            logger.error(f"[{self.site_name}] 获取资源列表失败: {e}")
            raise

    @staticmethod
    def _response_json(response) -> Any:
        if hasattr(response, "json"):
            return response.json()
        import json
        return json.loads(response.text)

    def _extract_total_pages(self, data: Any, current_page: int) -> int:
        resp_cfg = self.api.get("response") or {}
        tp_path = resp_cfg.get("total_pages_path")
        if tp_path:
            tp = safe_int(get_by_path(data, tp_path), default=0)
            if tp:
                return tp
        # 由 total + page_size 推算
        total = get_by_path(data, resp_cfg.get("total_path", ""))
        page_size = resp_cfg.get("page_size")
        if total is not None and page_size:
            total = safe_int(total)
            return max(1, -(-total // int(page_size)))  # 向上取整
        return current_page

    # ==================== 单行映射（hook） ====================

    def _map_row(self, raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """把单条原始 JSON 映射为标准资源字典。"""
        fm = self.api.get("field_mapping") or {}
        mapped: Dict[str, Any] = {}
        for std_key, path in fm.items():
            mapped[std_key] = get_by_path(raw, path)

        torrent_id = mapped.get("torrent_id")
        title = mapped.get("title")
        if torrent_id is None or not title:
            return None
        mapped["torrent_id"] = str(torrent_id)

        # 数值字段规整
        for k in ("size_bytes", "seeders", "leechers", "completions"):
            if k in mapped:
                mapped[k] = safe_int(mapped[k])

        # 评分
        for k in ("douban_rating", "imdb_rating"):
            if k in mapped and mapped[k] is not None:
                mapped[k] = safe_float(mapped[k])

        # 时间字段
        mapped.update(self._parse_time_fields(raw))

        # 分类
        mapped["category"] = self._parse_category(raw, mapped.get("original_category_id"))

        # 促销
        mapped.update(self._parse_promotion(raw))

        # 下载链接
        mapped["download_url"] = self._get_download_url(mapped["torrent_id"], raw)

        # 电视剧信息
        if mapped["category"] in (MEDIA_TYPE_TV, MEDIA_TYPE_ANIME):
            mapped["tv_info"] = extract_tv_info(title, mapped.get("subtitle") or "")

        return normalize_resource(mapped)

    def _parse_time_fields(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """按 api_config.time_fields 解析时间（timestamp / datetime 字符串）。"""
        result: Dict[str, Any] = {}
        time_fields = self.api.get("time_fields") or {}
        for std_key, cfg in time_fields.items():
            value = get_by_path(raw, cfg.get("field", ""))
            if value in (None, "", 0):
                continue
            fmt = cfg.get("format", "datetime")
            if fmt == "timestamp":
                result[std_key] = self._parse_timestamp(value)
            else:
                result[std_key] = self._parse_time(str(value))
        return result

    @staticmethod
    def _parse_timestamp(value: Any) -> Optional[datetime]:
        try:
            ts = float(value)
            # 毫秒时间戳
            if ts > 1e11:
                ts /= 1000.0
            # Unix 时间戳是 UTC 绝对时刻，直接转系统时区（不要走 parse_pt_site_time，
            # 那会把字符串当作系统时区本地时间，导致偏移）
            utc_dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            return to_system_tz(utc_dt)
        except Exception:
            return None

    def _parse_category(self, raw: Dict[str, Any], category_id: Any) -> str:
        """按分类ID映射；支持 raw 中嵌套的分类字段。"""
        cat_field = (self.api.get("category") or {}).get("field")
        if category_id is None and cat_field:
            category_id = get_by_path(raw, cat_field)
        if category_id is not None and self.category_map:
            return self.category_map.get(str(category_id), MEDIA_TYPE_OTHER)
        return MEDIA_TYPE_OTHER

    # ==================== 促销解析（hook） ====================

    def _parse_promotion(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析促销信息。默认支持 factor 模式（下载/上传系数）。
        Yema 等枚举编码站点应 override 此方法。
        """
        promo = self.api.get("promotion") or {}
        ptype = promo.get("type")

        is_free = False
        is_double_up = False
        is_half_down = False

        if ptype == "factor":
            dl_factor = safe_float(
                get_by_path(raw, promo.get("download_factor_field", "")), default=1.0
            )
            up_factor = safe_float(
                get_by_path(raw, promo.get("upload_factor_field", "")), default=1.0
            )
            if dl_factor is not None:
                if dl_factor == 0:
                    is_free = True
                elif dl_factor == 0.5:
                    is_half_down = True
            if up_factor is not None and up_factor >= 2:
                is_double_up = True

        if is_free and is_double_up:
            promotion_type = "free_2x"
        elif is_free:
            promotion_type = "free"
        elif is_double_up:
            promotion_type = "2x"
        elif is_half_down:
            promotion_type = "50%"
        else:
            promotion_type = "none"

        return {
            "is_free": is_free,
            "is_double_upload": is_double_up,
            "is_discount": is_half_down,
            "promotion_type": promotion_type,
        }

    # ==================== 下载链接（hook） ====================

    def _get_download_url(self, torrent_id: str, raw: Dict[str, Any]) -> str:
        """按 download_url 模板构造下载链接。二次请求型站点应 override。"""
        template = self.api.get("download_url", "")
        if not template:
            return ""
        context = {
            "torrent_id": torrent_id,
            "passkey": self.passkey,
            "api_key": self.api_key,
        }
        path = render_template(template, context)
        return urljoin(self.base_url, path)

    async def download_torrent(self, resource_id: str, download_url: str = None) -> bytes:
        try:
            await self._ensure_csrf_token()
            url = download_url or self._get_download_url(resource_id, {})
            if not url:
                raise ValueError("无法构造下载链接（缺少 api_config.download_url）")
            logger.info(f"[{self.site_name}] 下载种子: {self._mask_proxy_url(url)}")

            response = await self._make_request(url)
            content = response.content
            if not content.startswith(b"d"):
                if b"<html" in content.lower() or b"<!doctype" in content.lower():
                    raise ValueError("下载返回HTML页面，可能未登录或无权限")
                raise ValueError("下载的内容不是有效的种子文件")
            logger.info(f"[{self.site_name}] 种子下载成功: {len(content)} bytes")
            return content
        except Exception as e:
            logger.error(f"[{self.site_name}] 下载种子失败: {e}")
            raise

    # ==================== 详情 / 健康检查 ====================

    async def get_resource_detail(self, resource_id: str) -> Dict[str, Any]:
        """详情默认仅回包基础信息；需要详情的站点可在 preset 配置或子类扩展。"""
        return {"torrent_id": resource_id, "detail_fetched": True}

    async def authenticate(self) -> bool:
        try:
            result = await self.fetch_resources(page=1, limit=1)
            return isinstance(result, dict)
        except Exception as e:
            logger.error(f"[{self.site_name}] 认证失败: {e}")
            return False

    async def health_check(self) -> bool:
        try:
            result = await self.fetch_resources(page=1, limit=1)
            return len(result.get("resources", [])) > 0
        except Exception as e:
            logger.error(f"[{self.site_name}] 健康检查失败: {e}")
            return False

    async def fetch_categories(self) -> List[Dict[str, Any]]:
        categories: List[Dict[str, Any]] = []
        if not self.preset:
            return categories
        order = 0
        for cat_id, details in self.preset.get("category_details", {}).items():
            categories.append({
                "id": cat_id,
                "nameChs": details.get("name_chs", ""),
                "nameEng": details.get("name_eng", ""),
                "nameCht": details.get("name_cht"),
                "parent": None,
                "order": order,
                "image": None,
                "_mapped_category": details.get("mapped_category"),
            })
            order += 1
        return categories

    async def load_category_mappings(self, db) -> None:
        return None


__all__ = ["GenericJSONAPIAdapter"]
