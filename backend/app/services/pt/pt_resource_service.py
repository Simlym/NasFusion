"""
PT资源服务
"""
import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from app.utils.timezone import now, to_system_tz

from sqlalchemy import and_, func, or_, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.adapters.pt_sites import get_adapter
from app.constants import (
    AUTH_TYPE_COOKIE,
    AUTH_TYPE_PASSKEY,
    AUTH_TYPE_USER_PASS,
    IDENTIFICATION_STATUS_FAILED,
    IDENTIFICATION_STATUS_UNIDENTIFIED,
)
from app.models.sync_log import SyncLog
from app.models.pt_resource import PTResource
from app.models.pt_site import PTSite
from app.schemas.pt_resource import PTResourceCreate, PTResourceFilter, PTResourceUpdate
from app.utils.encryption import encryption_util

logger = logging.getLogger(__name__)


class PTResourceService:
    """PT资源服务"""

    @staticmethod
    async def get_by_id(db: AsyncSession, resource_id: int) -> Optional[PTResource]:
        """根据ID获取资源"""
        result = await db.execute(select(PTResource).where(PTResource.id == resource_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_site_and_torrent_id(
        db: AsyncSession, site_id: int, torrent_id: str
    ) -> Optional[PTResource]:
        """根据站点ID和种子ID获取资源"""
        result = await db.execute(
            select(PTResource).where(
                and_(PTResource.site_id == site_id, PTResource.torrent_id == torrent_id)
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_list(
        db: AsyncSession, filter_params: PTResourceFilter
    ) -> Tuple[List[PTResource], int]:
        """
        获取资源列表

        Args:
            db: 数据库会话
            filter_params: 过滤参数

        Returns:
            Tuple[List[PTResource], int]: 资源列表和总数
        """
        # 基础查询（预加载站点关系）
        query = select(PTResource).options(
            selectinload(PTResource.site)
        )

        # 构建过滤条件
        conditions = [PTResource.is_active == True]  # 默认只显示活跃资源

        if filter_params.site_id:
            conditions.append(PTResource.site_id == filter_params.site_id)

        if filter_params.category:
            conditions.append(PTResource.category == filter_params.category)

        if filter_params.original_category_id:
            conditions.append(PTResource.original_category_id == filter_params.original_category_id)

        if filter_params.is_free is not None:
            conditions.append(PTResource.is_free == filter_params.is_free)

        if filter_params.is_promotional:
            conditions.append(
                or_(
                    PTResource.is_free == True,
                    PTResource.is_discount == True,
                    PTResource.is_double_upload == True,
                )
            )

        if filter_params.min_seeders is not None:
            conditions.append(PTResource.seeders >= filter_params.min_seeders)

        if filter_params.resolution:
            conditions.append(PTResource.resolution == filter_params.resolution)

        if filter_params.source:
            conditions.append(PTResource.source == filter_params.source)

        if filter_params.codec:
            conditions.append(PTResource.codec == filter_params.codec)

        if filter_params.search:
            # 模糊搜索标题和副标题
            search_pattern = f"%{filter_params.search}%"
            conditions.append(
                or_(
                    PTResource.title.ilike(search_pattern),
                    PTResource.subtitle.ilike(search_pattern),
                )
            )

        if filter_params.has_mapping is not None:
            # 通过映射关系进行筛选
            from app.models.resource_mapping import ResourceMapping
            if filter_params.has_mapping:
                # 只显示已识别的资源（存在映射关系）
                query = query.join(ResourceMapping, PTResource.id == ResourceMapping.pt_resource_id)
            else:
                # 只显示未识别的资源（不存在映射关系）
                query = query.outerjoin(ResourceMapping, PTResource.id == ResourceMapping.pt_resource_id)
                conditions.append(ResourceMapping.id.is_(None))

        if filter_params.identification_status:
            # 按识别状态筛选
            if filter_params.identification_status == "unidentified":
                # NULL 或 'unidentified' 都算未识别
                conditions.append(
                    or_(
                        PTResource.identification_status == None,
                        PTResource.identification_status == IDENTIFICATION_STATUS_UNIDENTIFIED,
                    )
                )
            else:
                # identified 或 failed
                conditions.append(PTResource.identification_status == filter_params.identification_status)

        # 按订阅ID过滤（复用订阅匹配逻辑）
        if filter_params.subscription_id:
            from app.services.subscription.subscription_service import SubscriptionService

            # 获取订阅匹配的资源ID列表
            matched_resources = await SubscriptionService.find_matched_resources(
                db, filter_params.subscription_id
            )
            matched_ids = [r.id for r in matched_resources]

            if matched_ids:
                conditions.append(PTResource.id.in_(matched_ids))
            else:
                # 如果没有匹配资源，返回空列表
                conditions.append(PTResource.id == -1)

        query = query.where(and_(*conditions))

        # 计算总数
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar_one()

        # 排序和分页
        query = query.order_by(PTResource.published_at.desc(), PTResource.created_at.desc())
        query = query.offset((filter_params.page - 1) * filter_params.page_size).limit(
            filter_params.page_size
        )

        # 执行查询
        result = await db.execute(query)
        resources = list(result.scalars().all())

        # 如果是订阅过滤，按集数排序
        if filter_params.subscription_id:
            from app.services.subscription.subscription_service import SubscriptionService

            subscription = await SubscriptionService.get_by_id(db, filter_params.subscription_id)
            if subscription and subscription.is_tv_subscription:
                def get_episode_sort_key(resource):
                    """提取集数用于排序"""
                    if not resource.tv_info:
                        return (999999, 999999)

                    episodes_dict = resource.tv_info.get("episodes", {})
                    season_key = str(subscription.current_season)

                    if season_key in episodes_dict:
                        episode_range = episodes_dict[season_key]
                        start = episode_range.get("start", 999999)
                        end = episode_range.get("end", 999999)
                        return (start, end)

                    return (999999, 999999)

                resources.sort(key=get_episode_sort_key)

        return resources, total

    @staticmethod
    async def create_resource(db: AsyncSession, resource_data: PTResourceCreate) -> PTResource:
        """
        创建资源

        Args:
            db: 数据库会话
            resource_data: 资源创建数据

        Returns:
            PTResource: 创建的资源

        Raises:
            ValueError: 资源已存在
        """
        # 检查是否已存在
        existing = await PTResourceService.get_by_site_and_torrent_id(
            db, resource_data.site_id, resource_data.torrent_id
        )
        if existing:
            raise ValueError(
                f"资源已存在: site_id={resource_data.site_id}, torrent_id={resource_data.torrent_id}"
            )

        # 创建资源
        resource = PTResource(**resource_data.model_dump())
        db.add(resource)
        await db.commit()
        await db.refresh(resource)

        return resource

    @staticmethod
    async def update_resource(
        db: AsyncSession, resource_id: int, resource_data: PTResourceUpdate
    ) -> Optional[PTResource]:
        """更新资源"""
        resource = await PTResourceService.get_by_id(db, resource_id)
        if not resource:
            return None

        # 更新字段
        update_data = resource_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(resource, field, value)

        await db.commit()
        await db.refresh(resource)

        return resource

    @staticmethod
    async def delete_resource(db: AsyncSession, resource_id: int) -> bool:
        """删除资源（软删除）"""
        resource = await PTResourceService.get_by_id(db, resource_id)
        if not resource:
            return False

        resource.is_active = False
        await db.commit()

        return True

    @staticmethod
    async def upsert_resource(db: AsyncSession, resource_data: dict) -> Tuple[PTResource, str]:
        """
        创建或更新资源

        Args:
            db: 数据库会话
            resource_data: 资源数据字典

        Returns:
            Tuple[PTResource, str]: (资源对象, 操作类型: "created"/"updated")
        """
        site_id = resource_data.get("site_id")
        torrent_id = resource_data.get("torrent_id")

        # 检查是否已存在
        existing = await PTResourceService.get_by_site_and_torrent_id(db, site_id, torrent_id)

        if existing:
            # 更新资源
            update_fields = [
                "title",
                "subtitle",
                "seeders",
                "leechers",
                "completions",
                "promotion_type",
                "promotion_expire_at",
                "is_free",
                "is_discount",
                "is_double_upload",
                "size_bytes",
                "douban_id",
                "douban_rating",
                "imdb_id",
                "imdb_rating",
                "download_url",  # 下载链接也需要更新
                "detail_url",    # 详情页链接也需要更新
                "original_category_id",  # 原始分类ID
                "subcategory",  # 子分类
            ]

            for field in update_fields:
                if field in resource_data and resource_data[field] is not None:
                    # 对于豆瓣/IMDB信息，只在原值为空时更新，避免覆盖已有数据
                    if field in ("douban_id", "douban_rating", "imdb_id", "imdb_rating"):
                        current_value = getattr(existing, field)
                        if current_value is None or current_value == 0:
                            setattr(existing, field, resource_data[field])
                    else:
                        setattr(existing, field, resource_data[field])

            existing.last_check_at = now()

            await db.commit()
            await db.refresh(existing)

            return existing, "updated"
        else:
            # 创建新资源
            resource = PTResource(**resource_data)
            db.add(resource)
            await db.commit()
            await db.refresh(resource)

            return resource, "created"

    @staticmethod
    async def batch_upsert_resources(
        db: AsyncSession, resources_data: List[dict]
    ) -> Tuple[int, int]:
        """
        批量创建或更新资源（高性能版本，单次 SELECT + 单次 COMMIT）

        Args:
            db: 数据库会话
            resources_data: 资源数据字典列表

        Returns:
            Tuple[int, int]: (新建数量, 更新数量)
        """
        if not resources_data:
            return 0, 0

        # 更新字段列表（与 upsert_resource 保持一致）
        update_fields = [
            "title", "subtitle", "seeders", "leechers", "completions",
            "promotion_type", "promotion_expire_at", "is_free", "is_discount",
            "is_double_upload", "size_bytes", "download_url", "detail_url",
            "original_category_id", "subcategory",
        ]
        preserve_if_set_fields = {"douban_id", "douban_rating", "imdb_id", "imdb_rating"}

        # 1. 提取所有 (site_id, torrent_id) 对
        keys = [(d["site_id"], d["torrent_id"]) for d in resources_data]

        # 2. 批量查询已存在记录（分块处理，兼容 SQLite 的变量限制）
        CHUNK_SIZE = 450
        existing_map: Dict[Tuple[int, str], PTResource] = {}

        for i in range(0, len(keys), CHUNK_SIZE):
            chunk = keys[i:i + CHUNK_SIZE]
            result = await db.execute(
                select(PTResource).where(
                    tuple_(PTResource.site_id, PTResource.torrent_id).in_(chunk)
                )
            )
            for row in result.scalars().all():
                existing_map[(row.site_id, row.torrent_id)] = row

        # 3. 区分新建和更新
        new_resources: List[PTResource] = []
        new_count = 0
        updated_count = 0

        for resource_data in resources_data:
            key = (resource_data["site_id"], resource_data["torrent_id"])
            existing = existing_map.get(key)

            if existing:
                # 更新
                for field in update_fields:
                    if field in resource_data and resource_data[field] is not None:
                        setattr(existing, field, resource_data[field])

                # 豆瓣/IMDB信息只在原值为空时更新
                for field in preserve_if_set_fields:
                    if field in resource_data and resource_data[field] is not None:
                        current_value = getattr(existing, field)
                        if current_value is None or current_value == 0:
                            setattr(existing, field, resource_data[field])

                existing.last_check_at = now()
                updated_count += 1
            else:
                # 新建
                resource = PTResource(**resource_data)
                new_resources.append(resource)
                new_count += 1

        # 4. 批量添加新建记录
        if new_resources:
            db.add_all(new_resources)

        # 5. 单次提交
        await db.commit()

        return new_count, updated_count

    @staticmethod
    def _validate_and_filter_params(
        site: PTSite,
        filters: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        根据站点能力验证和过滤同步参数

        Args:
            site: 站点对象
            filters: 原始过滤参数

        Returns:
            验证后的过滤参数

        Raises:
            ValueError: 参数不支持
        """
        from app.constants import (
            CAPABILITY_TIME_FILTER,
            CAPABILITY_ADULT_MODE,
            CAPABILITY_CATEGORY_FILTER,
            CAPABILITY_KEYWORD_SEARCH,
            CAPABILITY_SORTING,
            SYNC_MODE_ADULT,
        )

        if not filters:
            return {}

        validated_filters = {}
        capabilities = site.capabilities or {}

        # 检查时间过滤
        if filters.get("upload_date_start") or filters.get("upload_date_end"):
            if not capabilities.get(CAPABILITY_TIME_FILTER, False):
                raise ValueError(f"站点 {site.name} 不支持时间范围过滤")
            validated_filters["upload_date_start"] = filters.get("upload_date_start")
            validated_filters["upload_date_end"] = filters.get("upload_date_end")

        # 检查成人模式
        if filters.get("mode") == SYNC_MODE_ADULT:
            if not capabilities.get(CAPABILITY_ADULT_MODE, False):
                raise ValueError(f"站点 {site.name} 不支持成人模式")
            validated_filters["mode"] = filters["mode"]
        elif filters.get("mode"):
            validated_filters["mode"] = filters["mode"]

        # 检查分类过滤
        if filters.get("categories"):
            if not capabilities.get(CAPABILITY_CATEGORY_FILTER, False):
                raise ValueError(f"站点 {site.name} 不支持分类过滤")
            validated_filters["categories"] = filters["categories"]

        # 检查关键字搜索
        if filters.get("keyword"):
            if not capabilities.get(CAPABILITY_KEYWORD_SEARCH, False):
                raise ValueError(f"站点 {site.name} 不支持关键字搜索")
            validated_filters["keyword"] = filters["keyword"]

        # 检查排序参数
        if filters.get("sortField"):
            if not capabilities.get(CAPABILITY_SORTING, False):
                # 如果站点不支持排序但只请求默认排序(TIME+DESC)，可以忽略警告直接放行（因为大多数站点默认如此），
                # 但为了严谨，凡是显式指定排序的都检查能力
                # 不过考虑到现有任务可能没有迁移能力配置，对于默认情况可以宽容处理吗？
                # 暂时严格检查，因为 MTeam 已经默认添加了该能力
                logger.warning(f"站点 {site.name} 不支持排序功能，忽略排序参数")
            else:
                validated_filters["sortField"] = filters["sortField"]
                
        if filters.get("sortDirection"):
            # 只有设置了 sortField 才处理 sortDirection，或者允许单独设置方向？
            # 通常成对出现，这里简单处理
            if capabilities.get(CAPABILITY_SORTING, False):
                validated_filters["sortDirection"] = filters["sortDirection"]

        logger.info(f"验证后的过滤参数: {validated_filters}")
        return validated_filters

    @staticmethod
    async def sync_site_resources(
        db: AsyncSession,
        site_id: int,
        sync_type: str = "manual",
        max_pages: Optional[int] = None,
        start_page: int = 1,
        task_execution_id: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
        request_interval: Optional[int] = None,
    ) -> SyncLog:
        """
        同步站点资源

        Args:
            db: 数据库会话
            site_id: 站点ID
            sync_type: 同步类型 (full/incremental/manual)
            max_pages: 最大页数
            start_page: 起始页
            task_execution_id: 任务执行ID（用于进度更新）
            filters: 同步过滤参数
                - mode: 资源模式（normal/adult）
                - categories: 分类列表
                - upload_date_start: 上传开始时间
                - upload_date_end: 上传结束时间
                - keyword: 关键字搜索
            request_interval: 请求间隔秒数（可选，默认使用站点配置）

        Returns:
            SyncLog: 同步日志

        Raises:
            ValueError: 站点不存在或参数不支持
        """
        from app.services.task.task_execution_service import TaskExecutionService

        # 获取站点信息
        site = await db.get(PTSite, site_id)
        if not site:
            raise ValueError(f"站点不存在: {site_id}")

        # 验证过滤参数
        validated_filters = PTResourceService._validate_and_filter_params(site, filters)

        # 创建同步日志
        sync_log = SyncLog(
            site_id=site_id,
            sync_type=sync_type,
            status="running",
            started_at=now(),
            sync_strategy=site.sync_strategy,
        )
        db.add(sync_log)
        await db.commit()
        await db.refresh(sync_log)

        # 初始化进度
        if task_execution_id:
            await TaskExecutionService.update_progress(
                db, task_execution_id, 5,
                progress_detail={
                    "pages_processed": 0,
                    "resources_found": 0,
                    "resources_new": 0,
                    "resources_updated": 0,
                    "errors": 0,
                    "filters": validated_filters,
                }
            )

        try:
            # 获取站点适配器（传入db以加载元数据映射）
            adapter = await PTResourceService._get_site_adapter(site, db)

            # 确定实际使用的请求间隔（任务级 > 站点级）
            effective_interval = request_interval if request_interval is not None else site.request_interval

            # 执行同步
            stats = await PTResourceService._perform_sync(
                db=db,
                site=site,
                adapter=adapter,
                sync_log=sync_log,
                max_pages=max_pages,
                start_page=start_page,
                task_execution_id=task_execution_id,
                filters=validated_filters,
                request_interval=effective_interval,
            )

            # 更新同步日志 - 成功
            sync_log.status = "success"
            sync_log.completed_at = now()
            # 确保 started_at 是时区感知的 datetime，避免与 completed_at 相减时报错
            started_at_aware = to_system_tz(sync_log.started_at)
            sync_log.duration = int((sync_log.completed_at - started_at_aware).total_seconds())
            sync_log.resources_found = stats["found"]
            sync_log.resources_new = stats["new"]
            sync_log.resources_updated = stats["updated"]
            sync_log.resources_error = stats["error"]
            sync_log.resources_skipped = stats["skipped"]
            sync_log.total_pages = stats["total_pages"]
            sync_log.pages_processed = stats["pages_processed"]  # 添加此行
            sync_log.requests_count = stats["requests_count"]

            # 更新站点状态
            site.last_sync_at = sync_log.completed_at
            site.last_sync_status = "success"
            site.last_sync_error = None
            site.total_synced = await PTResourceService._count_site_resources(db, site_id)

            await db.commit()
            await db.refresh(sync_log)

            logger.info(
                f"Sync completed for site {site.name}: "
                f"{stats['new']} new, {stats['updated']} updated, {stats['error']} errors"
            )

        except Exception as e:
            logger.error(f"Sync failed for site {site.name}: {str(e)}")

            # 更新同步日志 - 失败
            sync_log.status = "failed"
            sync_log.completed_at = now()
            # 确保 started_at 是时区感知的 datetime，避免与 completed_at 相减时报错
            started_at_aware = to_system_tz(sync_log.started_at)
            sync_log.duration = int((sync_log.completed_at - started_at_aware).total_seconds())
            sync_log.error_message = str(e)

            # 更新站点状态
            site.last_sync_at = sync_log.completed_at
            site.last_sync_status = "failed"
            site.last_sync_error = str(e)

            await db.commit()
            await db.refresh(sync_log)

        return sync_log

    @staticmethod
    async def _get_site_adapter(site: PTSite, db: AsyncSession = None):
        """
        获取站点适配器

        Args:
            site: 站点对象
            db: 数据库会话（可选，用于加载元数据映射）

        Returns:
            站点适配器实例
        """
        # 准备配置信息
        config = {
            "name": site.name,
            "base_url": site.base_url,
            "domain": site.domain,
            "proxy_config": site.proxy_config,
            "request_interval": site.request_interval or 2,
        }

        # 添加认证信息（需要解密）
        if site.auth_type == AUTH_TYPE_PASSKEY and site.auth_passkey:
            config["auth_passkey"] = encryption_util.decrypt(site.auth_passkey)
        elif site.auth_type == AUTH_TYPE_COOKIE and site.auth_cookie:
            config["auth_cookie"] = encryption_util.decrypt(site.auth_cookie)
        elif site.auth_type == AUTH_TYPE_USER_PASS:
            if site.auth_username:
                config["auth_username"] = encryption_util.decrypt(site.auth_username)
            if site.auth_password:
                config["auth_password"] = encryption_util.decrypt(site.auth_password)

        # 加载元数据映射（如果提供了db会话）
        metadata_mappings = None
        if db:
            try:
                from app.services.pt.pt_metadata_service import PTMetadataService
                mappings_obj = await PTMetadataService.get_metadata_mappings(db, site.id)
                # 转换为字典格式
                metadata_mappings = {
                    "video_codecs": mappings_obj.video_codecs,
                    "audio_codecs": mappings_obj.audio_codecs,
                    "standards": mappings_obj.standards,
                    "sources": mappings_obj.sources,
                    "languages": mappings_obj.languages,
                    "countries": mappings_obj.countries,
                }
                logger.debug(f"Loaded metadata mappings for site {site.name}")
            except Exception as e:
                logger.warning(f"Failed to load metadata mappings for site {site.name}: {str(e)}")
                # 继续使用fallback映射

        adapter = get_adapter(site.type, config, metadata_mappings=metadata_mappings)

        # 设置site_id（用于分类映射加载）
        if hasattr(adapter, 'site_id'):
            adapter.site_id = site.id

        # 加载分类映射（如果是MTeam适配器且提供了db会话）
        if db and hasattr(adapter, 'load_category_mappings'):
            try:
                await adapter.load_category_mappings(db)
                logger.debug(f"Loaded category mappings for site {site.name}")
            except Exception as e:
                logger.warning(f"Failed to load category mappings for site {site.name}: {str(e)}")

        return adapter

    @staticmethod
    async def _perform_sync(
        db: AsyncSession,
        site: PTSite,
        adapter,
        sync_log: SyncLog,
        max_pages: Optional[int] = None,
        start_page: int = 1,
        task_execution_id: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
        request_interval: Optional[int] = None,
    ) -> dict:
        """执行同步操作"""
        import random
        from app.services.task.task_execution_service import TaskExecutionService

        stats = {
            "found": 0,
            "new": 0,
            "updated": 0,
            "error": 0,
            "skipped": 0,
            "total_pages": 0,
            "requests_count": 0,
            "pages_processed": 0,
        }

        page = start_page
        limit = 100  # 每页数量
        api_total_pages = None  # 从API获取的总页数

        while True:
            try:
                logger.info(f"Fetching page {page} from {site.name} with filters: {filters}")

                # 获取资源列表（返回包含分页信息的字典）
                result = await adapter.fetch_resources(
                    page=page,
                    limit=limit,
                    **(filters or {})
                )
                stats["requests_count"] += 1

                # 兼容两种返回格式：字典（新）或列表（旧）
                if isinstance(result, dict):
                    resources = result.get("resources", [])
                    # 从第一页获取总页数
                    if api_total_pages is None:
                        api_total_pages = result.get("total_pages", 0)
                        logger.info(f"API returned total_pages: {api_total_pages}")
                else:
                    # 兼容旧的返回格式（直接返回列表）
                    resources = result

                stats["total_pages"] = page

                if not resources:
                    logger.info(f"No more resources found on page {page}, stopping sync")
                    break

                stats["found"] += len(resources)

                # 批量处理资源（单次 SELECT + 单次 COMMIT）
                for resource_data in resources:
                    resource_data["site_id"] = site.id

                try:
                    page_new, page_updated = await PTResourceService.batch_upsert_resources(
                        db, resources
                    )
                    stats["new"] += page_new
                    stats["updated"] += page_updated
                except Exception as e:
                    logger.error(f"Error batch processing resources: {str(e)}")
                    page_new = 0
                    page_updated = 0
                    stats["error"] += len(resources)

                # 页面处理完成，更新进度
                stats["pages_processed"] = page - start_page + 1

                # 更新任务进度（如果有task_execution_id）
                if task_execution_id:
                    # 计算进度百分比：优先使用用户指定的max_pages，其次使用API返回的总页数
                    effective_total_pages = max_pages or api_total_pages
                    if effective_total_pages and effective_total_pages > 0:
                        # 计算从start_page到effective_total_pages的进度
                        pages_to_process = effective_total_pages - start_page + 1
                        progress = int((stats["pages_processed"] / pages_to_process) * 90)  # 最多到90%，留10%给最终统计
                    else:
                        # 不知道总页数时，使用对数增长（进度不会到100%）
                        progress = min(int(40 + stats["pages_processed"] * 2), 85)

                    await TaskExecutionService.update_progress(
                        db, task_execution_id, progress,
                        progress_detail={
                            "pages_processed": stats["pages_processed"],
                            "total_pages": effective_total_pages or 0,
                            "resources_found": stats["found"],
                            "resources_new": stats["new"],
                            "resources_updated": stats["updated"],
                            "errors": stats["error"],
                            "filters": filters,
                        }
                    )
                    # 日志显示本页的增量值，而非累计值
                    await TaskExecutionService.append_log(
                        db, task_execution_id,
                        f"第 {page} 页: 发现 {len(resources)} 个资源 (本页新增: {page_new}, 本页更新: {page_updated})"
                    )

                # 如果返回的资源数量小于limit，说明已经到最后一页
                if len(resources) < limit:
                    logger.info(f"Reached last page (page {page}, only {len(resources)} resources), stopping sync")
                    break

                # 检查是否达到最大页数（优先于API返回的total_pages）
                if max_pages and page >= max_pages:
                    logger.info(f"Reached user-specified max pages ({max_pages}), stopping sync")
                    break

                # 检查是否达到API返回的总页数（仅当未指定max_pages时使用）
                if api_total_pages and not max_pages and page >= api_total_pages:
                    logger.info(f"Reached API total pages ({api_total_pages}), stopping sync")
                    break

                # 请求间隔延迟（带随机变化，防止被检测为爬虫）
                if request_interval and request_interval > 0:
                    # 在基础间隔上增加 -20% ~ +30% 的随机变化
                    jitter = random.uniform(-0.2, 0.3)
                    actual_delay = request_interval * (1 + jitter)
                    actual_delay = max(0.5, actual_delay)  # 最小 0.5 秒
                    logger.info(f"等待 {actual_delay:.1f} 秒后请求下一页...")
                    await asyncio.sleep(actual_delay)

                page += 1

            except Exception as e:
                logger.error(f"Error fetching page {page}: {str(e)}")
                stats["error"] += 1
                break

        return stats

    @staticmethod
    async def _count_site_resources(db: AsyncSession, site_id: int) -> int:
        """统计站点资源数量"""
        result = await db.execute(
            select(func.count()).where(
                and_(PTResource.site_id == site_id, PTResource.is_active == True)
            )
        )
        return result.scalar_one()

    @staticmethod
    async def fetch_resource_detail(
        db: AsyncSession, resource_id: int
    ) -> Optional[PTResource]:
        """
        按需获取资源详情

        Args:
            db: 数据库会话
            resource_id: 资源ID

        Returns:
            更新后的资源对象
        """
        # 获取资源
        resource = await PTResourceService.get_by_id(db, resource_id)
        if not resource:
            raise ValueError(f"资源不存在: {resource_id}")

        # 检查是否已获取详情
        if resource.detail_fetched:
            logger.info(f"Resource {resource_id} detail already fetched")
            return resource

        # 获取站点
        site = await db.get(PTSite, resource.site_id)
        if not site:
            raise ValueError(f"站点不存在: {resource.site_id}")

        try:
            # 获取适配器（传入db以加载元数据映射）
            adapter = await PTResourceService._get_site_adapter(site, db)

            # 检查适配器是否支持详情获取
            if not hasattr(adapter, "get_resource_detail"):
                raise ValueError(f"站点 {site.type} 不支持详情获取")

            # 调用详情接口
            detail_data = await adapter.get_resource_detail(resource.torrent_id)

            # 更新资源字段
            update_fields = [
                "imdb_rating",
                "douban_rating",
                "description",
                "mediainfo",
                "origin_file_name",
                "image_list",
                "detail_fetched",
                "detail_fetched_at",
                "raw_detail_json",
            ]

            for field in update_fields:
                if field in detail_data:
                    setattr(resource, field, detail_data[field])

            await db.commit()
            await db.refresh(resource)

            logger.info(f"Successfully fetched detail for resource {resource_id}")
            return resource

        except Exception as e:
            logger.error(f"Failed to fetch detail for resource {resource_id}: {str(e)}")
            raise

    @staticmethod
    async def fetch_douban_info(
        db: AsyncSession, resource_id: int
    ) -> Optional[PTResource]:
        """
        按需获取豆瓣详细信息

        Args:
            db: 数据库会话
            resource_id: 资源ID

        Returns:
            更新后的资源对象
        """
        from datetime import datetime

        # 获取资源
        resource = await PTResourceService.get_by_id(db, resource_id)
        if not resource:
            raise ValueError(f"资源不存在: {resource_id}")

        # 检查是否已获取豆瓣信息
        if resource.douban_fetched:
            logger.info(f"Resource {resource_id} douban info already fetched")
            return resource

        # 检查是否有豆瓣URL
        if not resource.douban_id:
            raise ValueError(f"资源 {resource_id} 没有豆瓣ID")

        # 构建豆瓣URL
        douban_url = f"https://movie.douban.com/subject/{resource.douban_id}/"

        # 获取站点
        site = await db.get(PTSite, resource.site_id)
        if not site:
            raise ValueError(f"站点不存在: {resource.site_id}")

        try:
            # 获取适配器（传入db以加载元数据映射）
            adapter = await PTResourceService._get_site_adapter(site, db)

            # 检查适配器是否支持豆瓣信息获取
            if not hasattr(adapter, "fetch_douban_info"):
                raise ValueError(f"站点 {site.type} 不支持豆瓣信息获取")

            # 调用豆瓣信息接口
            douban_info = await adapter.fetch_douban_info(douban_url)

            # 更新资源字段
            resource.douban_info = douban_info
            resource.douban_fetched = True
            resource.douban_fetched_at = now()

            # 如果豆瓣返回了IMDB ID，也更新到资源
            if douban_info.get("imdb_id") and not resource.imdb_id:
                resource.imdb_id = douban_info["imdb_id"]

            await db.commit()
            await db.refresh(resource)

            logger.info(f"Successfully fetched douban info for resource {resource_id}")
            return resource

        except Exception as e:
            logger.error(f"Failed to fetch douban info for resource {resource_id}: {str(e)}")
            raise

    @staticmethod
    async def refresh_resource(
        db: AsyncSession, resource_id: int
    ) -> Optional[PTResource]:
        """
        刷新单个PT资源的实时信息（做种数、促销信息等）

        Args:
            db: 数据库会话
            resource_id: 资源ID

        Returns:
            更新后的资源对象

        Raises:
            ValueError: 资源不存在或站点不支持
        """
        # 获取资源
        resource = await PTResourceService.get_by_id(db, resource_id)
        if not resource:
            raise ValueError(f"资源不存在: {resource_id}")

        # 获取站点
        site = await db.get(PTSite, resource.site_id)
        if not site:
            raise ValueError(f"站点不存在: {resource.site_id}")

        try:
            # 获取适配器
            adapter = await PTResourceService._get_site_adapter(site, db)

            # 检查适配器是否支持详情获取
            if not hasattr(adapter, "get_resource_detail"):
                raise ValueError(f"站点 {site.type} 不支持资源详情获取")

            # 调用详情接口获取最新数据
            detail_data = await adapter.get_resource_detail(resource.torrent_id)

            # 更新实时变化的字段
            real_time_fields = [
                "seeders",
                "leechers",
                "completions",
                "promotion_type",
                "promotion_expire_at",
                "is_free",
                "is_discount",
                "is_double_upload",
                "has_hr",
                "hr_days",
                "hr_seed_time",
                "hr_ratio",
            ]

            for field in real_time_fields:
                if field in detail_data:
                    setattr(resource, field, detail_data[field])

            # 更新最后检查时间
            resource.last_check_at = now()
            resource.last_seeder_update_at = now()

            await db.commit()
            await db.refresh(resource)

            logger.info(f"Successfully refreshed resource {resource_id} from {site.name}")
            return resource

        except Exception as e:
            logger.error(f"Failed to refresh resource {resource_id}: {str(e)}")
            raise

    @staticmethod
    async def batch_refresh_resources(
        db: AsyncSession, resource_ids: List[int]
    ) -> dict:
        """
        批量刷新PT资源的实时信息

        Args:
            db: 数据库会话
            resource_ids: 资源ID列表

        Returns:
            dict: 刷新统计结果
                {
                    "total": 总数,
                    "success": 成功数,
                    "failed": 失败数,
                    "errors": 错误列表
                }
        """
        result = {
            "total": len(resource_ids),
            "success": 0,
            "failed": 0,
            "errors": []
        }

        for resource_id in resource_ids:
            try:
                await PTResourceService.refresh_resource(db, resource_id)
                result["success"] += 1
            except Exception as e:
                result["failed"] += 1
                result["errors"].append({
                    "resource_id": resource_id,
                    "error": str(e)
                })
                logger.warning(f"Failed to refresh resource {resource_id}: {str(e)}")

        logger.info(
            f"Batch refresh completed: {result['success']}/{result['total']} succeeded, "
            f"{result['failed']} failed"
        )

        return result

    @staticmethod
    async def get_unidentified_resources(
        db: AsyncSession,
        site_id: Optional[int] = None,
        category: Optional[str] = None,
        limit: int = 100
    ) -> List[PTResource]:
        """
        获取未识别的PT资源（未映射到统一资源表的资源）

        Args:
            db: 数据库会话
            site_id: 站点ID（可选，为空则查询所有站点）
            category: 资源分类（可选，如 movie, tv, music, anime, book, game, adult, other）
            limit: 返回数量限制

        Returns:
            未识别的PT资源列表
        """
        from app.models.resource_mapping import ResourceMapping

        # 查询未映射的资源
        query = (
            select(PTResource)
            .outerjoin(ResourceMapping, ResourceMapping.pt_resource_id == PTResource.id)
            .where(
                and_(
                    PTResource.is_active == True,  # 只查询活跃资源
                    ResourceMapping.id == None,  # 未映射
                    or_(
                        PTResource.identification_status == None,  # NULL（历史数据）
                        PTResource.identification_status == IDENTIFICATION_STATUS_UNIDENTIFIED,  # 未识别
                    ),
                )
            )
        )

        # 按站点过滤
        if site_id:
            query = query.where(PTResource.site_id == site_id)

        # 按分类过滤
        if category:
            query = query.where(PTResource.category == category)

        # 排序和限制
        query = query.order_by(PTResource.published_at.desc()).limit(limit)

        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def search_unidentified_by_title(
        db: AsyncSession,
        keyword: str,
        limit: int = 500
    ) -> List[PTResource]:
        """
        根据标题关键字搜索未识别的PT资源

        Args:
            db: 数据库会话
            keyword: 搜索关键字
            limit: 返回数量限制

        Returns:
            匹配的未识别PT资源列表
        """
        from app.models.resource_mapping import ResourceMapping

        if not keyword or not keyword.strip():
            return []

        search_pattern = f"%{keyword.strip()}%"

        # 查询标题匹配且未映射的资源
        query = (
            select(PTResource)
            .outerjoin(ResourceMapping, ResourceMapping.pt_resource_id == PTResource.id)
            .where(
                and_(
                    PTResource.is_active == True,
                    ResourceMapping.id == None,  # 未映射
                    or_(
                        PTResource.identification_status == None,
                        PTResource.identification_status == IDENTIFICATION_STATUS_UNIDENTIFIED,
                    ),
                    or_(
                        PTResource.title.ilike(search_pattern),
                        PTResource.subtitle.ilike(search_pattern),
                    ),
                )
            )
            .order_by(PTResource.published_at.desc())
            .limit(limit)
        )

        result = await db.execute(query)
        return list(result.scalars().all())
