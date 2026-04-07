# -*- coding: utf-8 -*-
"""
统一电视剧资源服务
"""
import logging
from datetime import datetime
from app.utils.timezone import now
from typing import List, Optional, Tuple

from sqlalchemy import String, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.unified_tv_series import UnifiedTVSeries
from app.models.trending_collection import TrendingCollection

logger = logging.getLogger(__name__)


class UnifiedTVSeriesService:
    """统一电视剧资源服务"""

    @staticmethod
    async def get_by_id(db: AsyncSession, tv_id: int) -> Optional[UnifiedTVSeries]:
        """根据ID获取电视剧"""
        result = await db.execute(select(UnifiedTVSeries).where(UnifiedTVSeries.id == tv_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_douban_id(db: AsyncSession, douban_id: str) -> Optional[UnifiedTVSeries]:
        """根据豆瓣ID获取电视剧"""
        result = await db.execute(
            select(UnifiedTVSeries).where(UnifiedTVSeries.douban_id == douban_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_imdb_id(db: AsyncSession, imdb_id: str) -> Optional[UnifiedTVSeries]:
        """根据IMDB ID获取电视剧"""
        result = await db.execute(
            select(UnifiedTVSeries).where(UnifiedTVSeries.imdb_id == imdb_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_tmdb_id(db: AsyncSession, tmdb_id: int) -> Optional[UnifiedTVSeries]:
        """根据TMDB ID获取电视剧"""
        result = await db.execute(
            select(UnifiedTVSeries).where(UnifiedTVSeries.tmdb_id == tmdb_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_tvdb_id(db: AsyncSession, tvdb_id: int) -> Optional[UnifiedTVSeries]:
        """根据TVDB ID获取电视剧"""
        result = await db.execute(
            select(UnifiedTVSeries).where(UnifiedTVSeries.tvdb_id == tvdb_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def find_by_external_ids(
        db: AsyncSession,
        douban_id: Optional[str] = None,
        imdb_id: Optional[str] = None,
        tmdb_id: Optional[int] = None,
        tvdb_id: Optional[int] = None,
    ) -> Optional[UnifiedTVSeries]:
        """
        通过外部ID查找已存在的统一电视剧资源

        Args:
            db: 数据库会话
            douban_id: 豆瓣ID
            imdb_id: IMDB ID
            tmdb_id: TMDB ID
            tvdb_id: TVDB ID

        Returns:
            UnifiedTVSeries: 找到的电视剧对象，未找到返回None

        优先级：douban_id > imdb_id > tmdb_id > tvdb_id
        """
        # 1. 优先使用豆瓣ID查找
        if douban_id:
            tv = await UnifiedTVSeriesService.get_by_douban_id(db, douban_id)
            if tv:
                logger.info(f"Found existing TV series in local cache by douban_id: {douban_id}")
                return tv

        # 2. 使用IMDB ID查找
        if imdb_id:
            tv = await UnifiedTVSeriesService.get_by_imdb_id(db, imdb_id)
            if tv:
                logger.info(f"Found existing TV series in local cache by imdb_id: {imdb_id}")
                return tv

        # 3. 使用TMDB ID查找
        if tmdb_id:
            tv = await UnifiedTVSeriesService.get_by_tmdb_id(db, tmdb_id)
            if tv:
                logger.info(f"Found existing TV series in local cache by tmdb_id: {tmdb_id}")
                return tv

        # 4. 使用TVDB ID查找
        if tvdb_id:
            tv = await UnifiedTVSeriesService.get_by_tvdb_id(db, tvdb_id)
            if tv:
                logger.info(f"Found existing TV series in local cache by tvdb_id: {tvdb_id}")
                return tv

        return None

    @staticmethod
    async def find_or_create(
        db: AsyncSession,
        douban_id: Optional[str] = None,
        imdb_id: Optional[str] = None,
        tmdb_id: Optional[int] = None,
        tvdb_id: Optional[int] = None,
        metadata: Optional[dict] = None,
    ) -> Tuple[UnifiedTVSeries, bool]:
        """
        查找或创建统一电视剧资源（去重逻辑）

        Args:
            db: 数据库会话
            douban_id: 豆瓣ID
            imdb_id: IMDB ID
            tmdb_id: TMDB ID
            tvdb_id: TVDB ID
            metadata: 元数据字典（用于创建新记录）

        Returns:
            Tuple[UnifiedTVSeries, bool]: (电视剧对象, 是否新建)

        优先级：douban_id > imdb_id > tmdb_id > tvdb_id
        """
        # 1. 优先使用豆瓣ID查找
        if douban_id:
            tv = await UnifiedTVSeriesService.get_by_douban_id(db, douban_id)
            if tv:
                logger.info(f"Found existing TV series by douban_id: {douban_id}")
                # 如果找到了，但其他ID为空，更新它们
                updated = False
                if imdb_id and not tv.imdb_id:
                    tv.imdb_id = imdb_id
                    updated = True
                if tmdb_id and not tv.tmdb_id:
                    tv.tmdb_id = tmdb_id
                    updated = True
                if tvdb_id and not tv.tvdb_id:
                    tv.tvdb_id = tvdb_id
                    updated = True
                if updated:
                    tv.updated_at = now()
                    await db.commit()
                    await db.refresh(tv)
                return tv, False

        # 2. 使用IMDB ID查找
        if imdb_id:
            tv = await UnifiedTVSeriesService.get_by_imdb_id(db, imdb_id)
            if tv:
                logger.info(f"Found existing TV series by imdb_id: {imdb_id}")
                updated = False
                if douban_id and not tv.douban_id:
                    tv.douban_id = douban_id
                    updated = True
                if tmdb_id and not tv.tmdb_id:
                    tv.tmdb_id = tmdb_id
                    updated = True
                if tvdb_id and not tv.tvdb_id:
                    tv.tvdb_id = tvdb_id
                    updated = True
                if updated:
                    tv.updated_at = now()
                    await db.commit()
                    await db.refresh(tv)
                return tv, False

        # 3. 使用TMDB ID查找
        if tmdb_id:
            tv = await UnifiedTVSeriesService.get_by_tmdb_id(db, tmdb_id)
            if tv:
                logger.info(f"Found existing TV series by tmdb_id: {tmdb_id}")
                updated = False
                if douban_id and not tv.douban_id:
                    tv.douban_id = douban_id
                    updated = True
                if imdb_id and not tv.imdb_id:
                    tv.imdb_id = imdb_id
                    updated = True
                if tvdb_id and not tv.tvdb_id:
                    tv.tvdb_id = tvdb_id
                    updated = True
                if updated:
                    tv.updated_at = now()
                    await db.commit()
                    await db.refresh(tv)
                return tv, False

        # 4. 使用TVDB ID查找
        if tvdb_id:
            tv = await UnifiedTVSeriesService.get_by_tvdb_id(db, tvdb_id)
            if tv:
                logger.info(f"Found existing TV series by tvdb_id: {tvdb_id}")
                updated = False
                if douban_id and not tv.douban_id:
                    tv.douban_id = douban_id
                    updated = True
                if imdb_id and not tv.imdb_id:
                    tv.imdb_id = imdb_id
                    updated = True
                if tmdb_id and not tv.tmdb_id:
                    tv.tmdb_id = tmdb_id
                    updated = True
                if updated:
                    tv.updated_at = now()
                    await db.commit()
                    await db.refresh(tv)
                return tv, False

        # 5. 未找到，创建新记录
        if not metadata:
            raise ValueError("创建新电视剧资源时需要提供metadata")

        # ⚠️ 验证必填字段
        title = metadata.get('title')
        if not title or (isinstance(title, str) and not title.strip()):
            raise ValueError(
                f"无法创建电视剧资源：title字段为空。"
                f"douban_id={douban_id}, imdb_id={imdb_id}, tmdb_id={tmdb_id}, tvdb_id={tvdb_id}"
            )

        logger.info(f"Creating new TV series: {title}")

        # 过滤掉UnifiedTVSeries模型不支持的字段
        valid_fields = {
            "tmdb_id", "imdb_id", "tvdb_id", "douban_id",
            "title", "original_title", "aka",
            "year", "first_air_date", "last_air_date", "status",
            "number_of_seasons", "number_of_episodes", "episode_runtime",
            "rating_tmdb", "votes_tmdb", "rating_douban", "votes_douban", "rating_imdb", "votes_imdb",
            "genres", "tags", "languages", "countries", "networks",
            "creators", "directors", "actors", "writers",
            "overview", "tagline",
            "certification", "content_ratings",
            "production_companies", "type",
            "poster_url", "backdrop_url", "logo_url", "clearart_url", "banner_url",
            "pt_resource_count", "has_free_resource", "best_quality", "best_seeder_count",
            "last_resource_updated_at",
            "local_file_count", "has_local", "local_images_dir",
            "seasons_info",
            "detail_loaded", "detail_loaded_at", "metadata_source",
        }

        # 只保留有效字段
        filtered_metadata = {k: v for k, v in metadata.items() if k in valid_fields}

        # 处理特殊字段映射（从电影元数据格式转换）
        if "runtime" in metadata and "episode_runtime" not in filtered_metadata:
            # 将单个runtime转换为数组
            filtered_metadata["episode_runtime"] = [metadata["runtime"]]

        # 转换日期字符串为 date 对象（针对 SQLite）
        for date_field in ["first_air_date", "last_air_date"]:
            if date_field in filtered_metadata:
                val = filtered_metadata[date_field]
                if isinstance(val, str):
                    try:
                        # 尝试解析 ISO 格式日期 (YYYY-MM-DD)
                        filtered_metadata[date_field] = datetime.strptime(val, "%Y-%m-%d").date()
                    except (ValueError, TypeError):
                        # 解析失败则设为 None
                        # 日志记录警告
                        logger.warning(f"Failed to parse date for {date_field}: {val}. Setting to None.")
                        filtered_metadata[date_field] = None

        # 处理季数和集数：0 转换为 None（满足数据库约束 ck_tv_series_*_positive）
        # 数据库约束要求：number_of_seasons IS NULL OR number_of_seasons > 0
        # 数据库约束要求：number_of_episodes IS NULL OR number_of_episodes > 0
        for count_field in ["number_of_seasons", "number_of_episodes"]:
            if count_field in filtered_metadata:
                val = filtered_metadata[count_field]
                if val is not None and val == 0:
                    logger.warning(f"{count_field} is 0, converting to None to satisfy database constraint.")
                    filtered_metadata[count_field] = None

        # 确保图片 URL 字段是字符串
        for url_field in ["poster_url", "backdrop_url", "logo_url", "clearart_url", "banner_url"]:
            if url_field in filtered_metadata:
                val = filtered_metadata[url_field]
                if isinstance(val, dict):
                    filtered_metadata[url_field] = val.get("url")

        tv = UnifiedTVSeries(**filtered_metadata)
        tv.detail_loaded = True
        db.add(tv)
        await db.commit()
        await db.refresh(tv)

        # 同步演职员表
        try:
            from app.services.identification.person_service import PersonService
            # 构建credits_data
            credits_data = {
                "actors": filtered_metadata.get("actors", []),
                "creators": filtered_metadata.get("creators", []), # UnifiedTVSeries里可能没有creators字段，但metadata里有
                "directors": filtered_metadata.get("directors", []),
            }
            await PersonService.sync_tv_credits(db, tv, credits_data)
        except Exception as e:
            logger.error(f"Failed to sync credits for TV {tv.id}: {e}")

        return tv, True

    @staticmethod
    async def get_list(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 20,
        has_free_resource: Optional[bool] = None,
        year: Optional[int] = None,
        genre: Optional[str] = None,
        country: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        sort_by: str = "created_at",
        order: str = "desc",
        min_rating: Optional[float] = None,
        trending_collection: Optional[str] = None,
        exclude_genre: Optional[str] = None,
        has_local: Optional[bool] = None,
    ) -> Tuple[List[UnifiedTVSeries], int]:
        """
        获取电视剧列表

        Args:
            db: 数据库会话
            skip: 跳过数量
            limit: 限制数量
            has_free_resource: 是否有免费资源
            year: 年份
            genre: 类型
            country: 国家/地区
            status: 状态（Returning Series/Ended等）
            search: 搜索关键词（标题）
            sort_by: 排序字段 (created_at, rating, year, title)
            order: 排序方向 (asc, desc)
            min_rating: 最低评分
            trending_collection: 榜单类型（如 'douban_weekly_best'）
            has_local: 是否有本地文件

        Returns:
            Tuple[List[UnifiedTVSeries], int]: (电视剧列表, 总数)
        """
        # 基础查询
        query = select(UnifiedTVSeries)
        conditions = []

        # 关联榜单筛选
        if trending_collection:
            query = query.join(
                TrendingCollection,
                and_(
                    TrendingCollection.unified_resource_id == UnifiedTVSeries.id,
                    TrendingCollection.collection_type == trending_collection,
                    TrendingCollection.media_type == "tv",  # 确保只关联电视剧类型
                )
            )

        # 构建过滤条件
        if has_free_resource is not None:
            conditions.append(UnifiedTVSeries.has_free_resource == has_free_resource)

        if year:
            conditions.append(UnifiedTVSeries.year == year)

        if genre:
            # JSON 数组存储格式为 ["类型1", "类型2"]
            from app.core.config import settings
            if settings.database.DB_TYPE.lower() == "postgresql":
                # PostgreSQL: 使用 @> 操作符检查 JSONB 数组是否包含元素
                from sqlalchemy import literal
                from sqlalchemy.dialects.postgresql import JSONB
                conditions.append(
                    UnifiedTVSeries.genres.cast(JSONB).contains(literal([genre], JSONB))
                )
            else:
                # SQLite: 只能用 LIKE 匹配
                conditions.append(UnifiedTVSeries.genres.cast(String).like(f'%"{genre}"%'))

        if exclude_genre:
            # 排除包含指定类型的资源
            from app.core.config import settings
            if settings.database.DB_TYPE.lower() == "postgresql":
                from sqlalchemy import literal, not_
                from sqlalchemy.dialects.postgresql import JSONB
                conditions.append(
                    not_(UnifiedTVSeries.genres.cast(JSONB).contains(literal([exclude_genre], JSONB)))
                )
            else:
                conditions.append(
                    ~UnifiedTVSeries.genres.cast(String).like(f'%"{exclude_genre}"%')
                )

        if country:
            # JSON 数组存储格式为 ["国家1", "国家2"]
            from app.core.config import settings
            if settings.database.DB_TYPE.lower() == "postgresql":
                # PostgreSQL: 使用 @> 操作符检查 JSONB 数组是否包含元素
                from sqlalchemy import literal
                from sqlalchemy.dialects.postgresql import JSONB
                conditions.append(
                    UnifiedTVSeries.countries.cast(JSONB).contains(literal([country], JSONB))
                )
            else:
                # SQLite: 只能用 LIKE 匹配
                conditions.append(UnifiedTVSeries.countries.cast(String).like(f'%"{country}"%'))

        if status:
            conditions.append(UnifiedTVSeries.status == status)

        if search:
            # 搜索标题或原始标题
            search_pattern = f"%{search}%"
            conditions.append(
                or_(
                    UnifiedTVSeries.title.ilike(search_pattern),
                    UnifiedTVSeries.original_title.ilike(search_pattern),
                )
            )

        if min_rating is not None:
            conditions.append(
                or_(
                    UnifiedTVSeries.rating_douban >= min_rating,
                    UnifiedTVSeries.rating_tmdb >= min_rating,
                    UnifiedTVSeries.rating_imdb >= min_rating,
                )
            )

        if has_local is not None:
            conditions.append(UnifiedTVSeries.has_local == has_local)

        if conditions:
            query = query.where(and_(*conditions))

        # 计算总数
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar_one()

        # 排序和分页
        if trending_collection and sort_by == 'created_at':
            # 如果是按榜单筛选且未指定其他排序，优先按榜单排名排序
            query = query.order_by(TrendingCollection.rank_position.asc())
        else:
            # 常规排序
            sort_column = UnifiedTVSeries.created_at
            if sort_by == 'rating':
                sort_column = UnifiedTVSeries.rating_douban
            elif sort_by == 'year':
                sort_column = UnifiedTVSeries.year
            elif sort_by == 'title':
                sort_column = UnifiedTVSeries.title

            if order == 'asc':
                query = query.order_by(sort_column.asc())
            else:
                query = query.order_by(sort_column.desc())
        
        # 始终添加第二排序键以保证分页稳定
        if sort_by != 'created_at' or trending_collection:
             query = query.order_by(UnifiedTVSeries.created_at.desc())
        query = query.offset(skip).limit(limit)

        # 执行查询
        result = await db.execute(query)
        tv_series = result.scalars().all()

        return list(tv_series), total

    @staticmethod
    async def update_tv_series(
        db: AsyncSession,
        tv_id: int,
        tv_data: dict,
    ) -> Optional[UnifiedTVSeries]:
        """更新电视剧信息"""
        tv = await UnifiedTVSeriesService.get_by_id(db, tv_id)
        if not tv:
            return None

        # 更新字段
        update_data = tv_data if isinstance(tv_data, dict) else tv_data.model_dump(exclude_unset=True)

        # 同步演职员表 (如果更新数据中包含)
        credits_data = {}
        if "actors" in update_data:
             credits_data["actors"] = update_data["actors"]
        if "directors" in update_data:
             credits_data["directors"] = update_data["directors"]
        if "creators" in update_data:
             credits_data["creators"] = update_data["creators"]

        if credits_data:
            try:
                from app.services.identification.person_service import PersonService
                await PersonService.sync_tv_credits(db, tv, credits_data)
            except Exception as e:
                logger.error(f"Failed to update credits for TV {tv.id}: {e}")

        for field, value in update_data.items():
            if hasattr(tv, field):
                setattr(tv, field, value)

        tv.updated_at = now()
        await db.commit()
        await db.refresh(tv)

        return tv
