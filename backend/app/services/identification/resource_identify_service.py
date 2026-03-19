# -*- coding: utf-8 -*-
"""
资源识别服务
"""
import logging
import re
from typing import Optional, Union

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.metadata import DoubanAdapter, TMDBAdapter
from app.adapters.pt_sites.mteam import MTeamAdapter
from app.models.pt_resource import PTResource
from app.models.resource_mapping import ResourceMapping
from app.models.unified_movie import UnifiedMovie
from app.models.unified_tv_series import UnifiedTVSeries
from app.schemas.resource_mapping import ResourceMappingCreate
from app.services.pt.pt_resource_service import PTResourceService
from app.services.identification.resource_mapping_service import ResourceMappingService
from app.services.identification.unified_movie_service import UnifiedMovieService
from app.services.identification.unified_tv_series_service import UnifiedTVSeriesService
from app.services.identification.identify_priority_service import IdentificationPriorityService
from app.services.identification.adult_identify_service import AdultIdentifyService
from app.models.pt_site import PTSite
from app.constants import MEDIA_TYPE_ADULT, UNIFIED_TABLE_ADULT
from app.constants.resource_identification import (
    IDENTIFICATION_SOURCE_LOCAL_CACHE,
    IDENTIFICATION_SOURCE_MTEAM_DOUBAN,
    IDENTIFICATION_SOURCE_DOUBAN_API,
    IDENTIFICATION_SOURCE_DOUBAN_SEARCH,
    IDENTIFICATION_SOURCE_TMDB_BY_IMDB,
    IDENTIFICATION_SOURCE_TMDB_SEARCH,
    IDENTIFICATION_STATUS_IDENTIFIED,
    IDENTIFICATION_STATUS_FAILED,
)

logger = logging.getLogger(__name__)


class ResourceIdentificationService:
    """资源识别服务"""

    @staticmethod
    async def identify_movie(
        db: AsyncSession,
        pt_resource_id: int,
        force: bool = False,
    ) -> ResourceMapping:
        """
        识别PT资源为电影并建立映射

        Args:
            db: 数据库会话
            pt_resource_id: PT资源ID
            force: 是否强制重新识别（删除旧映射）

        Returns:
            ResourceMapping: 映射关系对象

        Raises:
            ValueError: 参数错误、资源不存在、识别失败等
        """
        # 1. 获取PT资源
        pt_resource = await PTResourceService.get_by_id(db, pt_resource_id)
        if not pt_resource:
            raise ValueError(f"PT资源不存在: {pt_resource_id}")

        logger.info(f"Identifying PT resource: id={pt_resource_id}, title={pt_resource.title}")

        try:
            # 2. 检查是否已映射
            existing_mapping = await ResourceMappingService.get_by_pt_resource(db, pt_resource_id)
            if existing_mapping:
                if not force:
                    raise ValueError(
                        f"PT资源 {pt_resource_id} 已映射到 {existing_mapping.unified_table_name}:{existing_mapping.unified_resource_id}，"
                        "如需重新识别，请先删除旧映射或使用force=True"
                    )
                else:
                    # 删除旧映射
                    await ResourceMappingService.delete_mapping(db, existing_mapping.id)
                    logger.info(f"Deleted old mapping for force re-identification: {existing_mapping.id}")

            # 3. 优先从本地缓存查找（优化1：减少外部API调用）
            movie = await ResourceIdentificationService._find_in_local_cache(
                pt_resource=pt_resource,
                media_type="movie",
                db=db
            )

            # 如果本地缓存命中，直接创建映射
            if movie:
                logger.info(f"Found movie in local cache, skipping external API calls")
                is_new = False
                match_method = IDENTIFICATION_SOURCE_LOCAL_CACHE
                match_confidence = 100
            else:
                # 4. 本地缓存未命中，获取元数据（支持豆瓣和TMDB多个来源）
                metadata = await ResourceIdentificationService._fetch_metadata(pt_resource, db)

                # 保存识别来源信息（稍后使用）
                match_method = metadata.get("metadata_source", "unknown")
                match_confidence = 100 if (pt_resource.douban_id or pt_resource.imdb_id) else 80

                # 移除非模型字段（避免传入UnifiedMovie构造函数时报错）
                # 注意：metadata_source 是模型字段，不需要移除
                metadata_clean = {k: v for k, v in metadata.items() if k not in ["media_type"]}

                # 5. 查找或创建统一电影资源（去重）
                movie, is_new = await UnifiedMovieService.find_or_create(
                    db=db,
                    douban_id=metadata.get("douban_id"),
                    imdb_id=metadata.get("imdb_id"),
                    tmdb_id=metadata.get("tmdb_id"),
                    metadata=metadata_clean,
                )

            if is_new:
                logger.info(f"Created new unified movie: id={movie.id}, title={movie.title}")
            else:
                logger.info(f"Found existing unified movie: id={movie.id}, title={movie.title}")

            # 6. 创建映射关系
            mapping_data = ResourceMappingCreate(
                pt_resource_id=pt_resource_id,
                media_type="movie",
                unified_table_name="unified_movies",
                unified_resource_id=movie.id,
                match_method=match_method,  # douban, tmdb, tmdb_search
                match_confidence=match_confidence,
                is_primary=True,
            )

            mapping = await ResourceMappingService.create_mapping(db, mapping_data)

            # 7. 更新统一资源的统计信息
            await movie.update_statistics(db)
            logger.info(
                f"Updated movie statistics: pt_resource_count={movie.pt_resource_count}, "
                f"has_free_resource={movie.has_free_resource}"
            )

            # 8. 更新识别状态为已识别
            pt_resource.identification_status = IDENTIFICATION_STATUS_IDENTIFIED
            await db.commit()
            logger.info(f"Updated identification_status to 'identified' for PT resource {pt_resource_id}")

            return mapping

        except Exception as e:
            # 识别失败，更新状态为failed
            pt_resource.identification_status = IDENTIFICATION_STATUS_FAILED
            await db.commit()
            logger.error(f"Identification failed for PT resource {pt_resource_id}, status updated to 'failed': {str(e)}")
            raise

    @staticmethod
    async def identify_tv(
        db: AsyncSession,
        pt_resource_id: int,
        force: bool = False,
    ) -> ResourceMapping:
        """
        识别PT资源为电视剧并建立映射

        Args:
            db: 数据库会话
            pt_resource_id: PT资源ID
            force: 是否强制重新识别（删除旧映射）

        Returns:
            ResourceMapping: 映射关系对象

        Raises:
            ValueError: 参数错误、资源不存在、识别失败等
        """
        # 1. 获取PT资源
        pt_resource = await PTResourceService.get_by_id(db, pt_resource_id)
        if not pt_resource:
            raise ValueError(f"PT资源不存在: {pt_resource_id}")

        logger.info(f"Identifying PT resource as TV: id={pt_resource_id}, title={pt_resource.title}")

        try:
            # 2. 检查是否已映射
            existing_mapping = await ResourceMappingService.get_by_pt_resource(db, pt_resource_id)
            if existing_mapping:
                if not force:
                    raise ValueError(
                        f"PT资源 {pt_resource_id} 已映射到 {existing_mapping.unified_table_name}:{existing_mapping.unified_resource_id}，"
                        "如需重新识别，请先删除旧映射或使用force=True"
                    )
                else:
                    # 删除旧映射
                    await ResourceMappingService.delete_mapping(db, existing_mapping.id)
                    logger.info(f"Deleted old mapping for force re-identification: {existing_mapping.id}")

            # 3. 优先从本地缓存查找（优化1：减少外部API调用）
            tv_series = await ResourceIdentificationService._find_in_local_cache(
                pt_resource=pt_resource,
                media_type="tv",
                db=db
            )

            # 如果本地缓存命中，直接创建映射
            if tv_series:
                logger.info(f"Found TV series in local cache, skipping external API calls")
                is_new = False
                match_method = IDENTIFICATION_SOURCE_LOCAL_CACHE
                match_confidence = 100
            else:
                # 4. 本地缓存未命中，获取元数据（支持豆瓣和TMDB多个来源）
                metadata = await ResourceIdentificationService._fetch_metadata(pt_resource, db)

                # 保存识别来源信息（稍后使用）
                match_method = metadata.get("metadata_source", "unknown")
                match_confidence = 100 if (pt_resource.douban_id or pt_resource.imdb_id) else 80

                # 移除非模型字段（避免传入UnifiedTVSeries构造函数时报错）
                # 注意：metadata_source 是模型字段，不需要移除
                metadata_clean = {k: v for k, v in metadata.items() if k not in ["media_type"]}

                # 5. 查找或创建统一电视剧资源（去重）
                tv_series, is_new = await UnifiedTVSeriesService.find_or_create(
                    db=db,
                    douban_id=metadata.get("douban_id"),
                    imdb_id=metadata.get("imdb_id"),
                    tmdb_id=metadata.get("tmdb_id"),
                    tvdb_id=metadata.get("tvdb_id"),
                    metadata=metadata_clean,
                )

            if is_new:
                logger.info(f"Created new unified TV series: id={tv_series.id}, title={tv_series.title}")
            else:
                logger.info(f"Found existing unified TV series: id={tv_series.id}, title={tv_series.title}")

            # 6. 创建映射关系
            mapping_data = ResourceMappingCreate(
                pt_resource_id=pt_resource_id,
                media_type="tv",
                unified_table_name="unified_tv_series",
                unified_resource_id=tv_series.id,
                match_method=match_method,  # douban, tmdb, tmdb_search
                match_confidence=match_confidence,
                is_primary=True,
            )

            mapping = await ResourceMappingService.create_mapping(db, mapping_data)

            # 7. 更新统一资源的统计信息（如果模型支持）
            if hasattr(tv_series, 'update_statistics'):
                await tv_series.update_statistics(db)
                logger.info(
                    f"Updated TV series statistics: pt_resource_count={tv_series.pt_resource_count}, "
                    f"has_free_resource={tv_series.has_free_resource}"
                )

            # 8. 更新识别状态为已识别
            pt_resource.identification_status = IDENTIFICATION_STATUS_IDENTIFIED
            await db.commit()
            logger.info(f"Updated identification_status to 'identified' for PT resource {pt_resource_id}")

            return mapping

        except Exception as e:
            # 识别失败，更新状态为failed
            pt_resource.identification_status = IDENTIFICATION_STATUS_FAILED
            await db.commit()
            logger.error(f"Identification failed for PT resource {pt_resource_id}, status updated to 'failed': {str(e)}")
            raise

    @staticmethod
    async def identify_adult(
        db: AsyncSession,
        pt_resource_id: int,
        force: bool = False,
    ) -> ResourceMapping:
        """
        识别PT资源为成人资源并建立映射

        Args:
            db: 数据库会话
            pt_resource_id: PT资源ID
            force: 是否强制重新识别（删除旧映射）

        Returns:
            ResourceMapping: 映射关系对象

        Raises:
            ValueError: 参数错误、资源不存在、识别失败等
        """
        # 1. 获取PT资源
        pt_resource = await PTResourceService.get_by_id(db, pt_resource_id)
        if not pt_resource:
            raise ValueError(f"PT资源不存在: {pt_resource_id}")

        logger.info(f"Identifying PT resource as adult: id={pt_resource_id}, title={pt_resource.title}")

        try:
            # 2. 检查是否已映射
            existing_mapping = await ResourceMappingService.get_by_pt_resource(db, pt_resource_id)
            if existing_mapping:
                if not force:
                    raise ValueError(
                        f"PT资源 {pt_resource_id} 已映射到 {existing_mapping.unified_table_name}:{existing_mapping.unified_resource_id}，"
                        "如需重新识别，请先删除旧映射或使用force=True"
                    )
                else:
                    await ResourceMappingService.delete_mapping(db, existing_mapping.id)
                    logger.info(f"Deleted old mapping for force re-identification: {existing_mapping.id}")

            # 3. 获取MTeam适配器（用于DMM API调用）
            site = await db.get(PTSite, pt_resource.site_id)
            mteam_adapter = None
            if site:
                try:
                    adapter = await PTResourceService._get_site_adapter(site, db)
                    if isinstance(adapter, MTeamAdapter):
                        mteam_adapter = adapter
                except Exception as e:
                    logger.warning(f"获取MTeam适配器失败，将使用简化模式: {e}")

            # 4. 尝试从raw_page_json获取dmmCode
            dmm_code = None
            if pt_resource.raw_page_json and isinstance(pt_resource.raw_page_json, dict):
                dmm_code = pt_resource.raw_page_json.get("dmmCode")

            # 5. 识别成人资源
            unified_adult = None

            if dmm_code and mteam_adapter:
                # 有dmmCode且有适配器，直接通过DMM API识别
                logger.info(f"使用dmmCode进行DMM识别: {dmm_code}")
                try:
                    dmm_info = await mteam_adapter.fetch_dmm_info(dmm_code)
                    if dmm_info:
                        from app.models.unified_adult import UnifiedAdult
                        from sqlalchemy import select

                        # 提取番号用于去重
                        product_number = dmm_info.get("product_number") or AdultIdentifyService.extract_product_number(
                            pt_resource.title, pt_resource.subtitle or ""
                        )

                        # 检查是否已存在
                        if product_number:
                            # 1. 精确匹配
                            stmt = select(UnifiedAdult).where(UnifiedAdult.product_number == product_number)
                            result = await db.execute(stmt)
                            unified_adult = result.scalar_one_or_none()
                            
                            # 2. 如果精确匹配失败，尝试查找简化版记录
                            if not unified_adult:
                                stmt = select(UnifiedAdult).where(UnifiedAdult.product_number.like(f"{product_number}_SIM_%"))
                                result = await db.execute(stmt)
                                unified_adult = result.scalars().first()

                        if not unified_adult:
                            from app.utils.timezone import now
                            unified_adult = UnifiedAdult(
                                product_number=product_number,
                                dmm_url=dmm_info.get("url"),
                                title=dmm_info.get("title") or pt_resource.title,
                                original_title=dmm_info.get("original_title"),
                                release_date=dmm_info.get("release_date"),
                                duration=dmm_info.get("duration"),
                                year=dmm_info.get("year"),
                                maker=dmm_info.get("maker"),
                                label=dmm_info.get("label"),
                                series=dmm_info.get("series"),
                                director=dmm_info.get("director"),
                                actresses=dmm_info.get("actresses"),
                                genres=dmm_info.get("genres"),
                                overview=dmm_info.get("overview"),
                                rating=dmm_info.get("rating"),
                                poster_url=dmm_info.get("poster_url"),
                                backdrop_url=dmm_info.get("backdrop_url"),
                                image_list=dmm_info.get("image_list"),
                                detail_loaded=True,
                                detail_loaded_at=now(),
                                metadata_source="dmm",
                                raw_dmm_data=dmm_info.get("raw_data"),
                            )
                            db.add(unified_adult)
                            await db.flush()
                            logger.info(f"创建统一成人资源(DMM via dmmCode): {product_number} - {unified_adult.title}")
                        else:
                             logger.info(f"找到现有统一成人资源: {unified_adult.product_number}")
                except Exception as e:
                    logger.warning(f"通过dmmCode进行DMM识别失败: {e}")

            if not unified_adult:
                # 尝试先从已有数据库中查找（避免重复创建简化记录）
                # 提取番号
                product_number_extracted = AdultIdentifyService.extract_product_number(
                    pt_resource.title, pt_resource.subtitle or ""
                )
                
                if product_number_extracted:
                     # 1. 精确匹配
                    stmt = select(UnifiedAdult).where(UnifiedAdult.product_number == product_number_extracted)
                    result = await db.execute(stmt)
                    unified_adult = result.scalar_one_or_none()
                    
                    # 2. 如果精确匹配失败，尝试查找简化版记录
                    if not unified_adult:
                        stmt = select(UnifiedAdult).where(UnifiedAdult.product_number.like(f"{product_number_extracted}_SIM_%"))
                        result = await db.execute(stmt)
                        unified_adult = result.scalars().first()
                    
                    if unified_adult:
                        logger.info(f"从现有库中找到匹配资源: {unified_adult.product_number}")

                # 如果还没找到，降级到AdultIdentifyService的标准流程（DMM→简化）
                if not unified_adult:
                    unified_adult = await AdultIdentifyService.identify_adult_resource(
                        db, pt_resource, mteam_adapter
                    )

            if not unified_adult:
                raise ValueError(f"PT资源 {pt_resource_id} 成人资源识别失败")

            # 6. 创建映射关系
            match_method = "dmm" if unified_adult.metadata_source == "dmm" else "simplified"
            match_confidence = 100 if unified_adult.metadata_source == "dmm" else 80

            mapping_data = ResourceMappingCreate(
                pt_resource_id=pt_resource_id,
                media_type=MEDIA_TYPE_ADULT,
                unified_table_name=UNIFIED_TABLE_ADULT,
                unified_resource_id=unified_adult.id,
                match_method=match_method,
                match_confidence=match_confidence,
                is_primary=True,
            )

            mapping = await ResourceMappingService.create_mapping(db, mapping_data)

            # 7. 更新统一资源的统计信息
            if hasattr(unified_adult, 'update_statistics'):
                await unified_adult.update_statistics(db)
                logger.info(
                    f"Updated adult statistics: pt_resource_count={unified_adult.pt_resource_count}"
                )

            # 8. 更新识别状态为已识别
            pt_resource.identification_status = IDENTIFICATION_STATUS_IDENTIFIED
            await db.commit()
            logger.info(f"Updated identification_status to 'identified' for PT resource {pt_resource_id}")

            return mapping

        except Exception as e:
            # 识别失败，更新状态为failed
            pt_resource.identification_status = IDENTIFICATION_STATUS_FAILED
            await db.commit()
            logger.error(f"Adult identification failed for PT resource {pt_resource_id}, status updated to 'failed': {str(e)}")
            raise

    @staticmethod
    async def _find_in_local_cache(
        pt_resource: PTResource,
        media_type: str,
        db: AsyncSession
    ) -> Optional[Union[UnifiedMovie, UnifiedTVSeries]]:
        """
        从本地缓存查找已存在的统一资源（基于 douban_id 或 imdb_id）

        Args:
            pt_resource: PT资源对象
            media_type: 媒体类型 ("movie" 或 "tv")
            db: 数据库会话

        Returns:
            UnifiedMovie或UnifiedTVSeries: 找到的统一资源对象，未找到返回None
        """
        if media_type == "movie":
            return await UnifiedMovieService.find_by_external_ids(
                db=db,
                douban_id=pt_resource.douban_id,
                imdb_id=pt_resource.imdb_id,
                tmdb_id=None,  # PT资源通常没有tmdb_id
            )
        elif media_type == "tv":
            return await UnifiedTVSeriesService.find_by_external_ids(
                db=db,
                douban_id=pt_resource.douban_id,
                imdb_id=pt_resource.imdb_id,
                tmdb_id=None,
                tvdb_id=None,
            )
        else:
            logger.warning(f"Unsupported media type for local cache lookup: {media_type}")
            return None

    @staticmethod
    async def _fetch_metadata(pt_resource: PTResource, db: AsyncSession) -> dict:
        """
        获取PT资源的元数据（基于配置的动态优先级）

        Args:
            pt_resource: PT资源对象
            db: 数据库会话（用于获取站点配置和系统配置）

        Returns:
            dict: 元数据字典

        Raises:
            ValueError: 无法获取元数据
        """
        # 1. 获取PT资源所属站点
        site = await db.get(PTSite, pt_resource.site_id)
        if not site:
            raise ValueError(f"PT资源 {pt_resource.id} 所属站点不存在: {pt_resource.site_id}")

        # 2. 获取识别优先级配置
        priority_config = await IdentificationPriorityService.get_priority_config(db)
        enabled_sources = priority_config.get("enabled_sources", [])

        logger.info(f"Using identification priority: {enabled_sources}")

        errors = []  # 记录所有尝试的错误

        # 3. 按配置的优先级依次尝试各识别源
        for source in enabled_sources:
            # 跳过本地缓存（已在 identify_movie/tv 中处理）
            if source == IDENTIFICATION_SOURCE_LOCAL_CACHE:
                continue

            try:
                # 尝试当前识别源
                metadata = await ResourceIdentificationService._try_identification_source(
                    source=source,
                    pt_resource=pt_resource,
                    site=site,
                    db=db,
                )

                if metadata:
                    logger.info(f"✓ 识别成功（来源: {source}）: {metadata.get('title')}")
                    
                    # 4. 合并 PT 资源本身已有的 ID（关键：避免丢失已有的外部 ID）
                    # 这样可以确保：
                    # - 使用 TMDB 识别时，如果 PT 资源有 douban_id，也会保存到 unified 表
                    # - 使用豆瓣识别时，如果 PT 资源有 tmdb_id，也会保存到 unified 表
                    # - 避免因为只使用单一来源 ID 而导致的资源重复问题
                    if pt_resource.douban_id and not metadata.get("douban_id"):
                        metadata["douban_id"] = pt_resource.douban_id
                        logger.info(f"  └── 补充 douban_id={pt_resource.douban_id} (来自 PT 资源)")
                    
                    if pt_resource.imdb_id and not metadata.get("imdb_id"):
                        metadata["imdb_id"] = pt_resource.imdb_id
                        logger.info(f"  └── 补充 imdb_id={pt_resource.imdb_id} (来自 PT 资源)")
                    
                    # tmdb_id 为 int 类型
                    if pt_resource.tmdb_id and not metadata.get("tmdb_id"):
                        metadata["tmdb_id"] = pt_resource.tmdb_id
                        logger.info(f"  └── 补充 tmdb_id={pt_resource.tmdb_id} (来自 PT 资源)")
                    
                    # 补充豆瓣评分（PT 资源字段: douban_rating, unified 表字段: rating_douban）
                    if pt_resource.douban_rating and not metadata.get("rating_douban"):
                        metadata["rating_douban"] = float(pt_resource.douban_rating)
                        logger.info(f"  └── 补充 rating_douban={pt_resource.douban_rating} (来自 PT 资源)")
                    
                    return metadata

            except Exception as e:
                error_msg = f"{source} 失败: {str(e)}"
                logger.warning(error_msg)
                errors.append(error_msg)

        # 4. 所有方法都失败，抛出详细错误
        error_summary = "\n".join([f"  - {err}" for err in errors])
        raise ValueError(
            f"PT资源 {pt_resource.id} 识别失败，已尝试所有方法：\n{error_summary}\n"
            f"建议：\n"
            f"  1. 获取PT资源详情以补充豆瓣ID或IMDB ID\n"
            f"  2. 检查网络连接和API配置\n"
            f"  3. 手动添加豆瓣ID或IMDB ID\n"
            f"  4. 在设置中调整识别优先级"
        )

    @staticmethod
    async def _try_identification_source(
        source: str,
        pt_resource: PTResource,
        site: PTSite,
        db: AsyncSession,
    ) -> Optional[dict]:
        """
        尝试使用指定的识别源获取元数据

        Args:
            source: 识别源类型
            pt_resource: PT资源对象
            site: PT站点对象
            db: 数据库会话

        Returns:
            dict: 元数据字典，失败返回None
        """
        # MTeam 豆瓣接口
        if source == IDENTIFICATION_SOURCE_MTEAM_DOUBAN:
            if not pt_resource.douban_id:
                logger.info(f"跳过 {source}: 无 douban_id")
                return None

            # 从豆瓣ID构建URL
            douban_url = f"https://movie.douban.com/subject/{pt_resource.douban_id}/"
            logger.info(f"尝试 {source}: douban_url={douban_url}")

            # 使用统一的适配器初始化方法（加载完整配置和映射）
            adapter = await PTResourceService._get_site_adapter(site, db)

            # 校验适配器类型（确保是MTeam适配器）
            if not isinstance(adapter, MTeamAdapter):
                raise ValueError(
                    f"站点 {site.name} (类型: {site.type}) 不是MTeam类型，无法使用MTeam豆瓣接口。"
                    f"请检查识别优先级配置。"
                )

            # 调用豆瓣信息获取方法
            douban_info = await adapter.fetch_douban_info(douban_url)

            # 转换为标准元数据格式
            # 从 rating 对象中提取投票数
            rating_obj = douban_info.get("rating")
            votes_douban = None
            if rating_obj and isinstance(rating_obj, dict):
                count_str = rating_obj.get("count")
                if count_str:
                    try:
                        votes_douban = int(count_str)
                    except (ValueError, TypeError):
                        pass

            metadata = {
                "douban_id": douban_info.get("subject_id"),
                "imdb_id": douban_info.get("imdb_id"),
                "title": douban_info.get("title"),
                "original_title": douban_info.get("original_title"),
                "year": douban_info.get("year"),
                "release_date": douban_info.get("release_date"),  # 已从 pubdate 转换
                "runtime": douban_info.get("runtime"),  # 已从 durations 转换
                "overview": douban_info.get("intro"),  # 简介
                "rating_douban": douban_info.get("score"),
                "votes_douban": votes_douban,  # 豆瓣投票数（从 rating.count）
                "genres": douban_info.get("genres", []),
                "directors": douban_info.get("directors", []),
                "actors": douban_info.get("actors", []),
                "countries": douban_info.get("countries", []),
                "languages": douban_info.get("languages", []),
                "aka": douban_info.get("aka", []),
                "poster_url": douban_info.get("cover_url"),
                "metadata_source": IDENTIFICATION_SOURCE_MTEAM_DOUBAN,
            }
            return metadata

        # 豆瓣 API（通过豆瓣ID）
        elif source == IDENTIFICATION_SOURCE_DOUBAN_API:
            if not pt_resource.douban_id:
                logger.info(f"跳过 {source}: 无 douban_id")
                return None

            logger.info(f"尝试 {source}: douban_id={pt_resource.douban_id}")

            douban_config = {
                "proxy_config": site.proxy_config if site else {},
                "timeout": 30,
                "max_retries": 3,
            }
            douban_adapter = DoubanAdapter(douban_config)

            # 判断媒体类型
            media_type = ResourceIdentificationService._detect_media_type(pt_resource)

            # 先尝试指定类型，失败则尝试另一种
            try:
                metadata = await douban_adapter.get_by_douban_id(
                    str(pt_resource.douban_id), media_type
                )
                return metadata
            except Exception:
                # 尝试备用类型
                alt_type = "tv" if media_type == "movie" else "movie"
                logger.info(f"尝试备用类型: {alt_type}")
                metadata = await douban_adapter.get_by_douban_id(
                    str(pt_resource.douban_id), alt_type
                )
                return metadata

        # 豆瓣搜索（通过标题+年份）
        elif source == IDENTIFICATION_SOURCE_DOUBAN_SEARCH:
            # 清理标题用于搜索
            cleaned_title = ResourceIdentificationService._clean_title_for_search(pt_resource.title)
            logger.info(f"尝试 {source}: title={cleaned_title}")

            douban_config = {
                "proxy_config": site.proxy_config if site else {},
                "timeout": 30,
                "max_retries": 3,
            }
            douban_adapter = DoubanAdapter(douban_config)

            year = ResourceIdentificationService._extract_year_from_title(pt_resource.title)
            media_type = ResourceIdentificationService._detect_media_type(pt_resource)

            search_results = await douban_adapter.search_by_title(
                title=cleaned_title,
                year=year,
                media_type=media_type,
            )

            if search_results:
                metadata = search_results[0]
                metadata["metadata_source"] = IDENTIFICATION_SOURCE_DOUBAN_SEARCH
                return metadata
            return None

        # TMDB精确匹配（通过IMDB ID）
        elif source == IDENTIFICATION_SOURCE_TMDB_BY_IMDB:
            if not pt_resource.imdb_id:
                logger.info(f"跳过 {source}: 无 imdb_id")
                return None

            logger.info(f"尝试 {source}: imdb_id={pt_resource.imdb_id}")

            # 检测媒体类型
            media_type = ResourceIdentificationService._detect_media_type(pt_resource)
            tmdb_adapter = await ResourceIdentificationService._get_tmdb_adapter(db)

            # 根据媒体类型调用不同的方法
            if media_type == "tv":
                metadata = await tmdb_adapter.find_tv_by_imdb_id(pt_resource.imdb_id)
            else:
                metadata = await tmdb_adapter.find_by_imdb_id(pt_resource.imdb_id)

            if metadata:
                return metadata
            return None

        # TMDB搜索（通过标题+年份）
        elif source == IDENTIFICATION_SOURCE_TMDB_SEARCH:
            # 清理标题用于搜索
            cleaned_title = ResourceIdentificationService._clean_title_for_search(pt_resource.title)
            logger.info(f"尝试 {source}: title={cleaned_title}")

            # 检测媒体类型
            media_type = ResourceIdentificationService._detect_media_type(pt_resource)
            year = ResourceIdentificationService._extract_year_from_title(pt_resource.title)
            tmdb_adapter = await ResourceIdentificationService._get_tmdb_adapter(db)

            # 根据媒体类型调用不同的搜索方法
            if media_type == "tv":
                search_results = await tmdb_adapter.search_tv_by_title(
                    title=cleaned_title,
                    first_air_date_year=year,
                )
            else:
                search_results = await tmdb_adapter.search_by_title(
                    title=cleaned_title,
                    year=year,
                )

            if search_results:
                metadata = search_results[0]
                metadata["metadata_source"] = IDENTIFICATION_SOURCE_TMDB_SEARCH
                return metadata
            return None

        else:
            logger.warning(f"Unknown identification source: {source}")
            return None

    @staticmethod
    def _detect_media_type(pt_resource: PTResource) -> str:
        """检测媒体类型"""
        if pt_resource.category == "tv":
            return "tv"
        elif "S0" in pt_resource.title or " S1" in pt_resource.title or " Season" in pt_resource.title:
            return "tv"
        return "movie"

    @staticmethod
    async def _get_tmdb_adapter(db: AsyncSession) -> TMDBAdapter:
        """
        获取TMDB适配器实例

        从系统设置中读取TMDB API Key和代理配置

        Args:
            db: 数据库会话

        Returns:
            TMDBAdapter: TMDB适配器实例

        Raises:
            ValueError: TMDB未配置或配置无效
        """
        from app.models.system_setting import SystemSetting
        from sqlalchemy import select

        # 查询TMDB配置
        query = select(SystemSetting).where(
            SystemSetting.category == "metadata_scraping",
            SystemSetting.key == "tmdb_api_key",
        )
        result = await db.execute(query)
        setting = result.scalar_one_or_none()

        if not setting or not setting.value:
            raise ValueError(
                "TMDB API Key未配置，无法使用TMDB识别。\n"
                "请在系统设置中添加TMDB API Key：\n"
                "  category='metadata_scraping', key='tmdb_api_key', value='your_api_key'"
            )

        # 查询代理配置（可选）
        proxy_query = select(SystemSetting).where(
            SystemSetting.category == "metadata_scraping",
            SystemSetting.key == "tmdb_proxy",
        )
        proxy_result = await db.execute(proxy_query)
        proxy_setting = proxy_result.scalar_one_or_none()

        proxy_config = {}
        if proxy_setting and proxy_setting.value:
            proxy_config = {
                "enabled": True,
                "url": proxy_setting.value,
            }

        # 创建TMDB适配器
        tmdb_config = {
            "api_key": setting.value,
            "proxy_config": proxy_config,
            "language": "zh-CN",  # 默认使用中文
        }

        return TMDBAdapter(tmdb_config)

    @staticmethod
    async def _get_douban_adapter(db: AsyncSession) -> DoubanAdapter:
        """
        获取豆瓣适配器实例

        Args:
            db: 数据库会话

        Returns:
            DoubanAdapter: 豆瓣适配器实例
        """
        # 豆瓣适配器不需要额外配置，直接创建
        douban_config = {
            "timeout": 30,
            "max_retries": 3,
        }
        return DoubanAdapter(douban_config)

    @staticmethod
    async def _get_tvdb_adapter(db: AsyncSession):
        """
        获取TVDB适配器实例

        从系统设置中读取TVDB API Key配置

        Args:
            db: 数据库会话

        Returns:
            TVDBAdapter: TVDB适配器实例，如果未配置返回None
        """
        from app.models.system_setting import SystemSetting
        from sqlalchemy import select

        # 查询TVDB配置
        query = select(SystemSetting).where(
            SystemSetting.category == "metadata_scraping",
            SystemSetting.key == "tvdb_api_key",
        )
        result = await db.execute(query)
        setting = result.scalar_one_or_none()

        if not setting or not setting.value:
            logger.debug("TVDB API Key未配置，跳过TVDB识别")
            return None

        # 查询代理配置（可选）
        proxy_query = select(SystemSetting).where(
            SystemSetting.category == "metadata_scraping",
            SystemSetting.key == "tvdb_proxy",
        )
        proxy_result = await db.execute(proxy_query)
        proxy_setting = proxy_result.scalar_one_or_none()

        proxy_config = {}
        if proxy_setting and proxy_setting.value:
            proxy_config = {
                "enabled": True,
                "url": proxy_setting.value,
            }

        # 查询TVDB PIN（可选）
        pin_query = select(SystemSetting).where(
            SystemSetting.category == "metadata_scraping",
            SystemSetting.key == "tvdb_pin",
        )
        pin_result = await db.execute(pin_query)
        pin_setting = pin_result.scalar_one_or_none()

        # 创建TVDB适配器
        from app.adapters.metadata.tvdb_adapter import TVDBAdapter
        tvdb_config = {
            "api_key": setting.value,
            "pin": pin_setting.value if pin_setting else "",
            "proxy_config": proxy_config,
            "language": "zho",  # 默认使用中文
        }

        return TVDBAdapter(tvdb_config)

    @staticmethod
    def _clean_title_for_search(title: str) -> str:
        """
        清理标题用于搜索（去除发布组、编码、分辨率等信息）

        Args:
            title: 原始标题

        Returns:
            清理后的标题
        """
        # 去除常见的技术标签
        technical_patterns = [
            r'\d{3,4}[pi]',  # 分辨率: 1080p, 1080i, 720p, 2160p
            r'\d{1}K',  # 4K, 8K
            
            # 日期格式 (YYYYMMDD, YYYY MM DD)
            r'\b(?:19|20)\d{2}[.\s]?\d{2}[.\s]?\d{2}\b',
            
            # 剧集信息 S01, S01E01, Ep01
            r'\bS\d{1,2}(?:E\d{1,3})?\b',
            r'\bEp?\d{1,4}\b',
            
            # 来源/平台
            r'\biQIYI\b|\bNF\b|\bNETFLIX\b|\bAMZN\b|\bBILI\b|\bBRTV\b|\bCCTV\b',

            r'BluRay|Blu-ray|BDRip|BRRip|REMUX|ISO',  # 蓝光相关
            r'WEB-DL|WEBRip|WEB',  # WEB发布
            r'HDRip|DVDRip|HDTV',  # 其他来源
            r'H\.?264|H\.?265|x264|x265|HEVC|AVC',  # 视频编码
            r'AAC|AC3|DDP|DTS|TrueHD|FLAC|Atmos',  # 音频编码
            r'\bDD\b|\bDD\+', # Dolby Digital
            
            r'5\.1|7\.1|2\.0',  # 声道数
            r'10bit|8bit',  # 位深
            r'HDR|SDR|Dolby ?Vision|DoVi',  # 色彩
            r'\bHFR\b', # 高帧率
            
            r'MA\s',  # Master Audio
            r'\d+Audio',  # 多音轨标记
            r'PROPER|REPACK|iNTERNAL',  # 发布标记
            r'\baka\b', # aka标记
        ]

        cleaned = title
        for pattern in technical_patterns:
            cleaned = re.sub(pattern, ' ', cleaned, flags=re.IGNORECASE)

        # 去除发布组（通常在 @ 或 - 之后）
        cleaned = re.sub(r'[@-][A-Za-z0-9]+(?:@[A-Za-z0-9]+)?\s*$', '', cleaned)

        # 去除多余的空格和点号
        cleaned = re.sub(r'[._]+', ' ', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()

        logger.info(f"标题清理: '{title}' → '{cleaned}'")
        return cleaned

    @staticmethod
    def _extract_year_from_title(title: str) -> Optional[int]:
        """
        从标题中提取年份

        支持多种格式：
        - Movie Name (2023)
        - Movie Name 2023
        - Movie Name.2023

        Args:
            title: 资源标题

        Returns:
            int: 年份，如果未找到返回None
        """
        # 匹配括号中的年份或末尾的年份
        patterns = [
            r'\((\d{4})\)',  # (2023)
            r'\.(\d{4})\.',  # .2023.
            r'\s(\d{4})\s',  # 空格2023空格
            r'\.(\d{4})$',   # .2023结尾
            r'\s(\d{4})$',   # 空格2023结尾
        ]

        for pattern in patterns:
            match = re.search(pattern, title)
            if match:
                year = int(match.group(1))
                # 验证年份合理性（1900-2100）
                if 1900 <= year <= 2100:
                    return year

        return None

    @staticmethod
    async def batch_identify_movies(
        db: AsyncSession,
        pt_resource_ids: list[int],
        skip_errors: bool = True,
        task_execution_id: Optional[int] = None,
    ) -> dict:
        """
        批量识别PT资源

        Args:
            db: 数据库会话
            pt_resource_ids: PT资源ID列表
            skip_errors: 是否跳过错误（True则继续处理下一个，False则遇错即停）
            task_execution_id: 任务执行ID（用于更新进度）

        Returns:
            dict: 识别结果统计
                {
                    "total": int,
                    "success": int,
                    "failed": int,
                    "skipped": int,
                    "errors": List[dict],
                }
        """
        from app.services.task.task_execution_service import TaskExecutionService

        result = {
            "total": len(pt_resource_ids),
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "errors": [],
        }

        for index, pt_resource_id in enumerate(pt_resource_ids):
            try:
                # 检查是否已经有映射关系
                existing_mapping = await ResourceMappingService.get_by_pt_resource_id(
                    db, pt_resource_id
                )
                if existing_mapping:
                    # 已有映射，但需要确保状态已更新
                    pt_resource = await PTResourceService.get_by_id(db, pt_resource_id)
                    if pt_resource and pt_resource.identification_status != IDENTIFICATION_STATUS_IDENTIFIED:
                        pt_resource.identification_status = IDENTIFICATION_STATUS_IDENTIFIED
                        await db.commit()
                        logger.info(f"Updated identification_status to 'identified' for already mapped PT resource {pt_resource_id}")
                    result["skipped"] += 1
                    logger.info(f"PT resource {pt_resource_id} already identified, skipping")
                else:
                    await ResourceIdentificationService.identify_movie(db, pt_resource_id)
                    result["success"] += 1

            except Exception as e:
                logger.error(f"Failed to identify PT resource {pt_resource_id}: {str(e)}")
                result["failed"] += 1
                result["errors"].append({
                    "pt_resource_id": pt_resource_id,
                    "error": str(e),
                })

                if not skip_errors:
                    raise

            # 更新任务进度
            if task_execution_id:
                progress = int((index + 1) / len(pt_resource_ids) * 100)
                await TaskExecutionService.update_progress(
                    db=db,
                    execution_id=task_execution_id,
                    progress=progress,
                    progress_detail={
                        "processed": index + 1,
                        "total": len(pt_resource_ids),
                        "success": result["success"],
                        "failed": result["failed"],
                        "skipped": result["skipped"],
                    }
                )

        logger.info(
            f"Batch identification completed: {result['success']} success, "
            f"{result['failed']} failed, {result['skipped']} skipped"
        )
        return result

    @staticmethod
    async def batch_identify_tv(
        db: AsyncSession,
        pt_resource_ids: list[int],
        skip_errors: bool = True,
        task_execution_id: Optional[int] = None,
    ) -> dict:
        """
        批量识别PT资源为电视剧

        Args:
            db: 数据库会话
            pt_resource_ids: PT资源ID列表
            skip_errors: 是否跳过错误（True则继续处理下一个，False则遇错即停）
            task_execution_id: 任务执行ID（用于更新进度）

        Returns:
            dict: 识别结果统计
                {
                    "total": int,
                    "success": int,
                    "failed": int,
                    "skipped": int,
                    "errors": List[dict],
                }
        """
        from app.services.task.task_execution_service import TaskExecutionService

        result = {
            "total": len(pt_resource_ids),
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "errors": [],
        }

        for index, pt_resource_id in enumerate(pt_resource_ids):
            try:
                # 检查是否已经有映射关系
                existing_mapping = await ResourceMappingService.get_by_pt_resource_id(
                    db, pt_resource_id
                )
                if existing_mapping:
                    # 已有映射，但需要确保状态已更新
                    pt_resource = await PTResourceService.get_by_id(db, pt_resource_id)
                    if pt_resource and pt_resource.identification_status != IDENTIFICATION_STATUS_IDENTIFIED:
                        pt_resource.identification_status = IDENTIFICATION_STATUS_IDENTIFIED
                        await db.commit()
                        logger.info(f"Updated identification_status to 'identified' for already mapped PT resource {pt_resource_id}")
                    result["skipped"] += 1
                    logger.info(f"PT resource {pt_resource_id} already identified, skipping")
                else:
                    await ResourceIdentificationService.identify_tv(db, pt_resource_id)
                    result["success"] += 1

            except Exception as e:
                logger.error(f"Failed to identify PT resource as TV {pt_resource_id}: {str(e)}")
                result["failed"] += 1
                result["errors"].append({
                    "pt_resource_id": pt_resource_id,
                    "error": str(e),
                })

                if not skip_errors:
                    raise

            # 更新任务进度
            if task_execution_id:
                progress = int((index + 1) / len(pt_resource_ids) * 100)
                await TaskExecutionService.update_progress(
                    db=db,
                    execution_id=task_execution_id,
                    progress=progress,
                    progress_detail={
                        "processed": index + 1,
                        "total": len(pt_resource_ids),
                        "success": result["success"],
                        "failed": result["failed"],
                        "skipped": result["skipped"],
                    }
                )

        logger.info(
            f"Batch TV identification completed: {result['success']} success, "
            f"{result['failed']} failed, {result['skipped']} skipped"
        )
        return result

    @staticmethod
    async def batch_identify_adult(
        db: AsyncSession,
        pt_resource_ids: list[int],
        skip_errors: bool = True,
        task_execution_id: Optional[int] = None,
    ) -> dict:
        """
        批量识别PT资源为成人资源

        Args:
            db: 数据库会话
            pt_resource_ids: PT资源ID列表
            skip_errors: 是否跳过错误（True则继续处理下一个，False则遇错即停）
            task_execution_id: 任务执行ID（用于更新进度）

        Returns:
            dict: 识别结果统计
        """
        from app.services.task.task_execution_service import TaskExecutionService

        result = {
            "total": len(pt_resource_ids),
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "errors": [],
        }

        for index, pt_resource_id in enumerate(pt_resource_ids):
            try:
                # 检查是否已经有映射关系
                existing_mapping = await ResourceMappingService.get_by_pt_resource_id(
                    db, pt_resource_id
                )
                if existing_mapping:
                    # 已有映射，但需要确保状态已更新
                    pt_resource = await PTResourceService.get_by_id(db, pt_resource_id)
                    if pt_resource and pt_resource.identification_status != IDENTIFICATION_STATUS_IDENTIFIED:
                        pt_resource.identification_status = IDENTIFICATION_STATUS_IDENTIFIED
                        await db.commit()
                        logger.info(f"Updated identification_status to 'identified' for already mapped PT resource {pt_resource_id}")
                    result["skipped"] += 1
                    logger.info(f"PT resource {pt_resource_id} already identified, skipping")
                else:
                    await ResourceIdentificationService.identify_adult(db, pt_resource_id)
                    result["success"] += 1

            except Exception as e:
                logger.error(f"Failed to identify PT resource as adult {pt_resource_id}: {str(e)}")
                result["failed"] += 1
                result["errors"].append({
                    "pt_resource_id": pt_resource_id,
                    "error": str(e),
                })

                if not skip_errors:
                    raise

            # 更新任务进度
            if task_execution_id:
                progress = int((index + 1) / len(pt_resource_ids) * 100)
                await TaskExecutionService.update_progress(
                    db=db,
                    execution_id=task_execution_id,
                    progress=progress,
                    progress_detail={
                        "processed": index + 1,
                        "total": len(pt_resource_ids),
                        "success": result["success"],
                        "failed": result["failed"],
                        "skipped": result["skipped"],
                    }
                )

        logger.info(
            f"Batch adult identification completed: {result['success']} success, "
            f"{result['failed']} failed, {result['skipped']} skipped"
        )
        return result

    @staticmethod
    async def identify_auto(
        db: AsyncSession,
        pt_resource_id: int,
        force: bool = False,
    ) -> ResourceMapping:
        """
        自动识别PT资源（根据category自动选择电影或电视剧）

        Args:
            db: 数据库会话
            pt_resource_id: PT资源ID
            force: 是否强制重新识别

        Returns:
            ResourceMapping: 映射关系对象
        """
        # 获取PT资源
        pt_resource = await PTResourceService.get_by_id(db, pt_resource_id)
        if not pt_resource:
            raise ValueError(f"PT资源不存在: {pt_resource_id}")

        # 根据category判断媒体类型
        if pt_resource.category == "tv":
            return await ResourceIdentificationService.identify_tv(db, pt_resource_id, force)
        elif "S0" in pt_resource.title or " S1" in pt_resource.title or " Season" in pt_resource.title:
            # 从标题中检测是否为剧集
            return await ResourceIdentificationService.identify_tv(db, pt_resource_id, force)
        elif pt_resource.category == "movie":
            # 默认识别为电影
            return await ResourceIdentificationService.identify_movie(db, pt_resource_id, force)
        elif pt_resource.category == "anime":
            # 默认识别为电影
            return await ResourceIdentificationService.identify_movie(db, pt_resource_id, force)
        elif pt_resource.category == MEDIA_TYPE_ADULT:
            return await ResourceIdentificationService.identify_adult(db, pt_resource_id, force)

    @staticmethod
    async def batch_identify_auto(
        db: AsyncSession,
        pt_resource_ids: list[int],
        skip_errors: bool = True,
        task_execution_id: Optional[int] = None,
    ) -> dict:
        """
        批量自动识别PT资源（根据category自动选择电影或电视剧）

        Args:
            db: 数据库会话
            pt_resource_ids: PT资源ID列表
            skip_errors: 是否跳过错误
            task_execution_id: 任务执行ID（用于更新进度）

        Returns:
            dict: 识别结果统计
        """
        from app.services.task.task_execution_service import TaskExecutionService

        result = {
            "total": len(pt_resource_ids),
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "errors": [],
        }

        for index, pt_resource_id in enumerate(pt_resource_ids):
            try:
                # 检查是否已经有映射关系
                existing_mapping = await ResourceMappingService.get_by_pt_resource_id(
                    db, pt_resource_id
                )
                if existing_mapping:
                    # 已有映射，但需要确保状态已更新
                    pt_resource = await PTResourceService.get_by_id(db, pt_resource_id)
                    if pt_resource and pt_resource.identification_status != IDENTIFICATION_STATUS_IDENTIFIED:
                        pt_resource.identification_status = IDENTIFICATION_STATUS_IDENTIFIED
                        await db.commit()
                        logger.info(f"Updated identification_status to 'identified' for already mapped PT resource {pt_resource_id}")
                    result["skipped"] += 1
                    logger.info(f"PT resource {pt_resource_id} already identified, skipping")
                else:
                    await ResourceIdentificationService.identify_auto(db, pt_resource_id)
                    result["success"] += 1

            except Exception as e:
                logger.error(f"Failed to auto-identify PT resource {pt_resource_id}: {str(e)}")
                result["failed"] += 1
                result["errors"].append({
                    "pt_resource_id": pt_resource_id,
                    "error": str(e),
                })

                if not skip_errors:
                    raise

            # 更新任务进度
            if task_execution_id:
                progress = int((index + 1) / len(pt_resource_ids) * 100)
                await TaskExecutionService.update_progress(
                    db=db,
                    execution_id=task_execution_id,
                    progress=progress,
                    progress_detail={
                        "processed": index + 1,
                        "total": len(pt_resource_ids),
                        "success": result["success"],
                        "failed": result["failed"],
                        "skipped": result["skipped"],
                    }
                )

        logger.info(
            f"Batch auto identification completed: {result['success']} success, "
            f"{result['failed']} failed, {result['skipped']} skipped"
        )
        return result

    # ==================== 统一识别入口 ====================

    @staticmethod
    async def identify_resource(
        db: AsyncSession,
        pt_resource_id: int,
        media_type: str = "auto",
        force: bool = False,
    ) -> ResourceMapping:
        """
        统一资源识别入口

        Args:
            db: 数据库会话
            pt_resource_id: PT资源ID
            media_type: 媒体类型（auto | movie | tv | music | book | adult | other）
            force: 是否强制重新识别

        Returns:
            ResourceMapping: 映射关系对象

        Raises:
            ValueError: 不支持的媒体类型
        """
        # 自动识别模式
        if media_type == "auto":
            return await ResourceIdentificationService.identify_auto(db, pt_resource_id, force)

        # 根据媒体类型路由到对应识别器
        if media_type == "movie":
            return await ResourceIdentificationService.identify_movie(db, pt_resource_id, force)
        elif media_type == "tv":
            return await ResourceIdentificationService.identify_tv(db, pt_resource_id, force)
        elif media_type == "music":
            # TODO: 实现音乐识别
            raise ValueError(f"音乐识别功能尚未实现")
        elif media_type == "book":
            # TODO: 实现电子书识别
            raise ValueError(f"电子书识别功能尚未实现")
        elif media_type == "adult":
            return await ResourceIdentificationService.identify_adult(db, pt_resource_id, force)
        else:
            raise ValueError(f"不支持的媒体类型: {media_type}")

    @staticmethod
    async def batch_identify_resources(
        db: AsyncSession,
        pt_resource_ids: list[int],
        media_type: str = "auto",
        skip_errors: bool = True,
        task_execution_id: Optional[int] = None,
    ) -> dict:
        """
        批量统一资源识别

        Args:
            db: 数据库会话
            pt_resource_ids: PT资源ID列表
            media_type: 媒体类型（auto | movie | tv | music | book | adult）
            skip_errors: 是否跳过错误
            task_execution_id: 任务执行ID（用于更新进度）

        Returns:
            dict: 识别结果统计
                {
                    "total": int,
                    "success": int,
                    "failed": int,
                    "skipped": int,
                    "errors": List[dict],
                }
        """
        # 根据媒体类型路由到对应批量识别方法
        if media_type == "auto":
            return await ResourceIdentificationService.batch_identify_auto(
                db, pt_resource_ids, skip_errors, task_execution_id
            )
        elif media_type == "movie":
            return await ResourceIdentificationService.batch_identify_movies(
                db, pt_resource_ids, skip_errors, task_execution_id
            )
        elif media_type == "tv":
            return await ResourceIdentificationService.batch_identify_tv(
                db, pt_resource_ids, skip_errors, task_execution_id
            )
        elif media_type == "adult":
            return await ResourceIdentificationService.batch_identify_adult(
                db, pt_resource_ids, skip_errors, task_execution_id
            )
        elif media_type in ["music", "book"]:
            raise ValueError(f"{media_type}批量识别功能尚未实现")
        else:
            raise ValueError(f"不支持的媒体类型: {media_type}")
