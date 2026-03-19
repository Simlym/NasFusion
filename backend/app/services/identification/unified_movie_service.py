# -*- coding: utf-8 -*-
"""
统一电影资源服务
"""
import logging
from typing import List, Optional, Tuple
from datetime import datetime
from app.utils.timezone import now

from sqlalchemy import String, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.unified_movie import UnifiedMovie
from app.models.trending_collection import TrendingCollection
from app.schemas.unified_movie import UnifiedMovieCreate, UnifiedMovieUpdate

logger = logging.getLogger(__name__)


class UnifiedMovieService:
    """统一电影资源服务"""

    @staticmethod
    async def get_by_id(db: AsyncSession, movie_id: int) -> Optional[UnifiedMovie]:
        """根据ID获取电影"""
        result = await db.execute(select(UnifiedMovie).where(UnifiedMovie.id == movie_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_douban_id(db: AsyncSession, douban_id: str) -> Optional[UnifiedMovie]:
        """根据豆瓣ID获取电影"""
        result = await db.execute(
            select(UnifiedMovie).where(UnifiedMovie.douban_id == douban_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_imdb_id(db: AsyncSession, imdb_id: str) -> Optional[UnifiedMovie]:
        """根据IMDB ID获取电影"""
        result = await db.execute(
            select(UnifiedMovie).where(UnifiedMovie.imdb_id == imdb_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_tmdb_id(db: AsyncSession, tmdb_id: int) -> Optional[UnifiedMovie]:
        """根据TMDB ID获取电影"""
        result = await db.execute(
            select(UnifiedMovie).where(UnifiedMovie.tmdb_id == tmdb_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def find_by_external_ids(
        db: AsyncSession,
        douban_id: Optional[str] = None,
        imdb_id: Optional[str] = None,
        tmdb_id: Optional[int] = None,
    ) -> Optional[UnifiedMovie]:
        """
        通过外部ID查找已存在的统一电影资源

        Args:
            db: 数据库会话
            douban_id: 豆瓣ID
            imdb_id: IMDB ID
            tmdb_id: TMDB ID

        Returns:
            UnifiedMovie: 找到的电影对象，未找到返回None

        优先级：douban_id > imdb_id > tmdb_id
        """
        # 1. 优先使用豆瓣ID查找
        if douban_id:
            movie = await UnifiedMovieService.get_by_douban_id(db, douban_id)
            if movie:
                logger.info(f"Found existing movie in local cache by douban_id: {douban_id}")
                return movie

        # 2. 使用IMDB ID查找
        if imdb_id:
            movie = await UnifiedMovieService.get_by_imdb_id(db, imdb_id)
            if movie:
                logger.info(f"Found existing movie in local cache by imdb_id: {imdb_id}")
                return movie

        # 3. 使用TMDB ID查找
        if tmdb_id:
            movie = await UnifiedMovieService.get_by_tmdb_id(db, tmdb_id)
            if movie:
                logger.info(f"Found existing movie in local cache by tmdb_id: {tmdb_id}")
                return movie

        return None

    @staticmethod
    async def find_or_create(
        db: AsyncSession,
        douban_id: Optional[str] = None,
        imdb_id: Optional[str] = None,
        tmdb_id: Optional[int] = None,
        metadata: Optional[dict] = None,
    ) -> Tuple[UnifiedMovie, bool]:
        """
        查找或创建统一电影资源（去重逻辑）

        Args:
            db: 数据库会话
            douban_id: 豆瓣ID
            imdb_id: IMDB ID
            tmdb_id: TMDB ID
            metadata: 元数据字典（用于创建新记录）

        Returns:
            Tuple[UnifiedMovie, bool]: (电影对象, 是否新建)

        优先级：douban_id > imdb_id > tmdb_id
        """
        # 1. 优先使用豆瓣ID查找
        if douban_id:
            movie = await UnifiedMovieService.get_by_douban_id(db, douban_id)
            if movie:
                logger.info(f"Found existing movie by douban_id: {douban_id}")
                # 如果找到了，但其他ID为空，更新它们
                updated = False
                if imdb_id and not movie.imdb_id:
                    movie.imdb_id = imdb_id
                    updated = True
                if tmdb_id and not movie.tmdb_id:
                    movie.tmdb_id = tmdb_id
                    updated = True
                if updated:
                    movie.updated_at = now()
                    await db.commit()
                    await db.refresh(movie)
                return movie, False

        # 2. 使用IMDB ID查找
        if imdb_id:
            movie = await UnifiedMovieService.get_by_imdb_id(db, imdb_id)
            if movie:
                logger.info(f"Found existing movie by imdb_id: {imdb_id}")
                updated = False
                if douban_id and not movie.douban_id:
                    movie.douban_id = douban_id
                    updated = True
                if tmdb_id and not movie.tmdb_id:
                    movie.tmdb_id = tmdb_id
                    updated = True
                if updated:
                    movie.updated_at = now()
                    await db.commit()
                    await db.refresh(movie)
                return movie, False

        # 3. 使用TMDB ID查找
        if tmdb_id:
            movie = await UnifiedMovieService.get_by_tmdb_id(db, tmdb_id)
            if movie:
                logger.info(f"Found existing movie by tmdb_id: {tmdb_id}")
                updated = False
                if douban_id and not movie.douban_id:
                    movie.douban_id = douban_id
                    updated = True
                if imdb_id and not movie.imdb_id:
                    movie.imdb_id = imdb_id
                    updated = True
                if updated:
                    movie.updated_at = now()
                    await db.commit()
                    await db.refresh(movie)
                return movie, False

        # 4. 未找到，创建新记录
        if not metadata:
            raise ValueError("创建新电影资源时需要提供metadata")

        # ⚠️ 验证必填字段
        title = metadata.get('title')
        if not title or (isinstance(title, str) and not title.strip()):
            raise ValueError(
                f"无法创建电影资源：title字段为空。"
                f"douban_id={douban_id}, imdb_id={imdb_id}, tmdb_id={tmdb_id}"
            )

        logger.info(f"Creating new movie: {title}")

        # 过滤掉 UnifiedMovie 模型不支持的字段
        valid_fields = {
            "tmdb_id", "imdb_id", "douban_id",
            "title", "original_title", "aka",
            "year", "release_date",
            "runtime",
            "rating_tmdb", "votes_tmdb", "rating_douban", "votes_douban", "rating_imdb", "votes_imdb",
            "genres", "tags", "languages", "countries",
            "directors", "actors", "writers",
            "overview", "tagline",
            "certification",
            "production_companies", "production_countries",
            "poster_url", "backdrop_url", "logo_url", "clearart_url",
            "pt_resource_count", "has_free_resource", "best_quality", "best_seeder_count",
            "last_resource_updated_at",
            "local_file_count", "has_local", "local_images_dir",
            "detail_loaded", "detail_loaded_at", "metadata_source",
            "budget", "revenue", "status", "homepage",
            "belongs_to_collection",
        }

        # 只保留有效字段
        filtered_metadata = {k: v for k, v in metadata.items() if k in valid_fields}

        # 转换日期字符串为 date 对象（针对 SQLite）
        if "release_date" in filtered_metadata:
            val = filtered_metadata["release_date"]
            if isinstance(val, str):
                try:
                    # 尝试解析 ISO 格式日期 (YYYY-MM-DD)
                    filtered_metadata["release_date"] = datetime.strptime(val, "%Y-%m-%d").date()
                except (ValueError, TypeError):
                    # 解析失败则设为 None
                    logger.warning(f"Failed to parse date for release_date: {val}. Setting to None.")
                    filtered_metadata["release_date"] = None

        # 确保图片 URL 字段是字符串
        for url_field in ["poster_url", "backdrop_url", "logo_url", "clearart_url"]:
            if url_field in filtered_metadata:
                val = filtered_metadata[url_field]
                if isinstance(val, dict):
                    filtered_metadata[url_field] = val.get("url")

        movie = UnifiedMovie(**filtered_metadata)
        movie.detail_loaded = True
        db.add(movie)
        await db.commit()
        await db.refresh(movie)

        # 同步演职员表
        try:
            from app.services.identification.person_service import PersonService
            # 构建credits_data
            credits_data = {
                "actors": filtered_metadata.get("actors", []),
                "directors": filtered_metadata.get("directors", []),
                "writers": filtered_metadata.get("writers", []),
            }
            await PersonService.sync_movie_credits(db, movie, credits_data)
        except Exception as e:
            logger.error(f"Failed to sync credits for movie {movie.id}: {e}")

        return movie, True

    @staticmethod
    async def get_list(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 20,
        has_free_resource: Optional[bool] = None,
        year: Optional[int] = None,
        genre: Optional[str] = None,
        country: Optional[str] = None,
        search: Optional[str] = None,
        sort_by: str = "created_at",
        order: str = "desc",
        min_rating: Optional[float] = None,
        trending_collection: Optional[str] = None,
        exclude_genre: Optional[str] = None,
    ) -> Tuple[List[UnifiedMovie], int]:
        """
        获取电影列表

        Args:
            db: 数据库会话
            skip: 跳过数量
            limit: 限制数量
            has_free_resource: 是否有免费资源
            year: 年份
            genre: 类型
            country: 国家/地区
            search: 搜索关键词（标题）
            sort_by: 排序字段 (created_at, rating, year, title)
            order: 排序方向 (asc, desc)
            min_rating: 最低评分
            order: 排序方向 (asc, desc)
            min_rating: 最低评分
            trending_collection: 榜单类型（如 'douban_top250'）

        Returns:
            Tuple[List[UnifiedMovie], int]: (电影列表, 总数)
        """
        # 基础查询
        query = select(UnifiedMovie)
        conditions = []

        # 关联榜单筛选
        if trending_collection:
            query = query.join(
                TrendingCollection,
                and_(
                    TrendingCollection.unified_resource_id == UnifiedMovie.id,
                    TrendingCollection.collection_type == trending_collection,
                    TrendingCollection.media_type == "movie",  # 确保只关联电影类型
                )
            )

        if has_free_resource is not None:
            conditions.append(UnifiedMovie.has_free_resource == has_free_resource)

        if year:
            conditions.append(UnifiedMovie.year == year)

        if genre:
            # JSON 数组存储格式为 ["类型1", "类型2"]
            from app.core.config import settings
            if settings.database.DB_TYPE.lower() == "postgresql":
                # PostgreSQL: 使用 @> 操作符检查 JSONB 数组是否包含元素
                # 这种方式不依赖存储格式（无论是 \uXXXX 还是明文都能匹配）
                from sqlalchemy import literal
                from sqlalchemy.dialects.postgresql import JSONB
                conditions.append(
                    UnifiedMovie.genres.cast(JSONB).contains(literal([genre], JSONB))
                )
            else:
                # SQLite: 只能用 LIKE 匹配
                conditions.append(UnifiedMovie.genres.cast(String).like(f'%"{genre}"%'))

        if exclude_genre:
            # 排除包含指定类型的资源
            from app.core.config import settings
            if settings.database.DB_TYPE.lower() == "postgresql":
                from sqlalchemy import literal, not_
                from sqlalchemy.dialects.postgresql import JSONB
                conditions.append(
                    not_(UnifiedMovie.genres.cast(JSONB).contains(literal([exclude_genre], JSONB)))
                )
            else:
                conditions.append(
                    ~UnifiedMovie.genres.cast(String).like(f'%"{exclude_genre}"%')
                )

        if country:
            # JSON 数组存储格式为 ["国家1", "国家2"]
            from app.core.config import settings
            if settings.database.DB_TYPE.lower() == "postgresql":
                # PostgreSQL: 使用 @> 操作符检查 JSONB 数组是否包含元素
                from sqlalchemy import literal
                from sqlalchemy.dialects.postgresql import JSONB
                conditions.append(
                    UnifiedMovie.countries.cast(JSONB).contains(literal([country], JSONB))
                )
            else:
                # SQLite: 只能用 LIKE 匹配
                conditions.append(UnifiedMovie.countries.cast(String).like(f'%"{country}"%'))

        if search:
            # 搜索标题或原始标题
            search_pattern = f"%{search}%"
            conditions.append(
                or_(
                    UnifiedMovie.title.ilike(search_pattern),
                    UnifiedMovie.original_title.ilike(search_pattern),
                )
            )

        if min_rating is not None:
            conditions.append(
                or_(
                    UnifiedMovie.rating_douban >= min_rating,
                    UnifiedMovie.rating_tmdb >= min_rating,
                    UnifiedMovie.rating_imdb >= min_rating,
                )
            )

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
            sort_column = UnifiedMovie.created_at
            if sort_by == 'rating':
                sort_column = UnifiedMovie.rating_douban
            elif sort_by == 'year':
                sort_column = UnifiedMovie.year
            elif sort_by == 'title':
                sort_column = UnifiedMovie.title

            if order == 'asc':
                query = query.order_by(sort_column.asc())
            else:
                query = query.order_by(sort_column.desc())

        # 始终添加第二排序键以保证分页稳定
        if sort_by != 'created_at' or trending_collection:
             query = query.order_by(UnifiedMovie.created_at.desc())
        query = query.offset(skip).limit(limit)

        # 执行查询
        result = await db.execute(query)
        movies = result.scalars().all()

        return list(movies), total

    @staticmethod
    async def update_movie(
        db: AsyncSession,
        movie_id: int,
        movie_data: UnifiedMovieUpdate,
    ) -> Optional[UnifiedMovie]:
        """更新电影信息"""
        movie = await UnifiedMovieService.get_by_id(db, movie_id)
        if not movie:
            return None

        # 更新字段
        update_data = movie_data.model_dump(exclude_unset=True)
        
        # 同步演职员表 (如果更新数据中包含)
        credits_data = {}
        if "actors" in update_data:
             credits_data["actors"] = update_data["actors"]
        if "directors" in update_data:
             credits_data["directors"] = update_data["directors"]
        if "writers" in update_data:
             credits_data["writers"] = update_data["writers"]
        
        if credits_data:
            try:
                from app.services.identification.person_service import PersonService
                await PersonService.sync_movie_credits(db, movie, credits_data)
            except Exception as e:
                logger.error(f"Failed to update credits for movie {movie.id}: {e}")

        for field, value in update_data.items():
            setattr(movie, field, value)

        movie.updated_at = now()
        await db.commit()
        await db.refresh(movie)

        return movie
