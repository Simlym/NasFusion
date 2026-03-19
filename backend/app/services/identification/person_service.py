# -*- coding: utf-8 -*-
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.unified_person import UnifiedPerson, MovieCredit, TVSeriesCredit
from app.models.unified_movie import UnifiedMovie
from app.models.unified_tv_series import UnifiedTVSeries
from app.adapters.metadata.tmdb_adapter import TMDBAdapter
from app.core.config import settings
from app.utils.timezone import now
from app.utils.metadata_normalization import MetadataNormalizer

logger = logging.getLogger(__name__)


def _parse_date(value) -> date:
    """将日期字符串(ISO格式)或date对象安全地转换为date对象"""
    if value is None:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return None
    return None


class PersonService:
    @staticmethod
    async def get_or_create_person(db: Session, person_data: Dict[str, Any]) -> UnifiedPerson:
        """
        查找或创建人员
        优先使用 TMDB ID 查找
        """
        tmdb_id = person_data.get("tmdb_id")
        imdb_id = person_data.get("imdb_id")
        douban_id = person_data.get("douban_id")
        name = person_data.get("name")

        if not name:
            return None

        person = None

        # 1. 优先通过 TMDB ID 查找
        if tmdb_id:
            stmt = select(UnifiedPerson).where(UnifiedPerson.tmdb_id == tmdb_id)
            result = await db.execute(stmt)
            person = result.scalars().first()

        # 2. 如果没找到，且有 IMDB ID，尝试通过 IMDB ID 查找
        if not person and imdb_id:
             stmt = select(UnifiedPerson).where(UnifiedPerson.imdb_id == imdb_id)
             result = await db.execute(stmt)
             person = result.scalars().first()

        # 3. 如果没找到，且有豆瓣 ID，尝试通过豆瓣 ID 查找
        if not person and douban_id:
            stmt = select(UnifiedPerson).where(UnifiedPerson.douban_id == str(douban_id))
            result = await db.execute(stmt)
            person = result.scalars().first()

        # 4. 兜底：通过名称精确匹配（仅当唯一匹配时使用，避免同名不同人）
        if not person and name:
            stmt = select(UnifiedPerson).where(UnifiedPerson.name == name)
            result = await db.execute(stmt)
            candidates = result.scalars().all()
            if len(candidates) == 1:
                person = candidates[0]

        # 5. 创建新人员
        if not person:
            person = UnifiedPerson(
                tmdb_id=tmdb_id,
                imdb_id=imdb_id,
                douban_id=str(douban_id) if douban_id else None,
                name=name,
                profile_url=person_data.get("thumb_url"),
                detail_loaded=False
            )
            db.add(person)
            await db.flush()
            await db.refresh(person)
        else:
            # 简单的属性更新（如果需要）
            updated = False
            if tmdb_id and not person.tmdb_id:
                person.tmdb_id = tmdb_id
                updated = True
            if imdb_id and not person.imdb_id:
                person.imdb_id = imdb_id
                updated = True
            if douban_id and not person.douban_id:
                person.douban_id = str(douban_id)
                updated = True

            # 如果新数据有头像且旧数据没有，更新头像
            new_profile = person_data.get("thumb_url")
            if new_profile and not person.profile_url:
                person.profile_url = new_profile
                updated = True

            if updated:
                person.updated_at = now()
                db.add(person)
        
        return person

    @staticmethod
    async def sync_movie_credits(db: Session, movie: UnifiedMovie, credits_data: Dict[str, List[Dict]]) -> None:
        """
        同步电影演职员表
        credits_data 结构: {"actors": [...], "directors": [...], "writers": [...]}
        """
        if not movie or not credits_data:
            return

        # 1. 删除该电影的所有关联
        from sqlalchemy import delete
        await db.execute(delete(MovieCredit).where(MovieCredit.movie_id == movie.id))
        
        # 2. 处理导演
        for director in credits_data.get("directors", []):
            person = await PersonService.get_or_create_person(db, director)
            if person:
                credit = MovieCredit(
                    movie_id=movie.id,
                    person_id=person.id,
                    job="Director",
                    order=0 # 导演一般不排序或排在最前
                )
                db.add(credit)

        # 3. 处理演员
        for actor in credits_data.get("actors", []):
            person = await PersonService.get_or_create_person(db, actor)
            if person:
                credit = MovieCredit(
                    movie_id=movie.id,
                    person_id=person.id,
                    job="Actor",
                    character=actor.get("character"),
                    order=actor.get("order", 0)
                )
                db.add(credit)
        
        # 4. grid writers if any (UnifiedMovie struct might not have writers explicitly separated usually)
        # 此时只处理了 actors 和 directors，因为 UnifiedMovie 目前主要存这两个。
        # 如果 credits_data 传来了 writers，也可以处理。
        
        await db.commit()

    @staticmethod
    async def sync_tv_credits(db: Session, tv: UnifiedTVSeries, credits_data: Dict[str, List[Dict]]) -> None:
        """
        同步电视剧演职员表
        """
        if not tv or not credits_data:
            return

        from sqlalchemy import delete
        await db.execute(delete(TVSeriesCredit).where(TVSeriesCredit.tv_series_id == tv.id))

        # 创作者/导演/编剧
        # UnifiedTVSeries 里通常叫 creators 或 directos
        creators = credits_data.get("creators", []) # TMDB TV 叫 created_by
        for creator in creators:
            person = await PersonService.get_or_create_person(db, creator)
            if person:
                 credit = TVSeriesCredit(
                    tv_series_id=tv.id,
                    person_id=person.id,
                    job="Creator",
                    order=0
                )
                 db.add(credit)

        # 导演
        directors = credits_data.get("directors", [])
        for director in directors:
            person = await PersonService.get_or_create_person(db, director)
            if person:
                credit = TVSeriesCredit(
                    tv_series_id=tv.id,
                    person_id=person.id,
                    job="Director",
                    order=0
                )
                db.add(credit)

        # 演员
        actors = credits_data.get("actors", [])
        for actor in actors:
            person = await PersonService.get_or_create_person(db, actor)
            if person:
                credit = TVSeriesCredit(
                    tv_series_id=tv.id,
                    person_id=person.id,
                    job="Actor",
                    character=actor.get("character"),
                    order=actor.get("order", 0)
                )
                db.add(credit)

        await db.commit()

    @staticmethod
    async def _get_tmdb_adapter(db: AsyncSession) -> TMDBAdapter:
        """获取TMDB适配器实例（从数据库读取配置）"""
        from app.models.system_setting import SystemSetting

        query = select(SystemSetting).where(
            SystemSetting.category == "metadata_scraping",
            SystemSetting.key == "tmdb_api_key",
        )
        result = await db.execute(query)
        setting = result.scalar_one_or_none()

        if not setting or not setting.value:
            raise ValueError("TMDB API Key未配置")

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

        tmdb_config = {
            "api_key": setting.value,
            "proxy_config": proxy_config,
            "language": "zh-CN",
        }

        return TMDBAdapter(tmdb_config)

    @staticmethod
    async def _get_douban_adapter(db: AsyncSession):
        """获取豆瓣适配器实例"""
        from app.models.system_setting import SystemSetting
        from app.adapters.metadata.douban_adapter import DoubanAdapter

        proxy_query = select(SystemSetting).where(
            SystemSetting.category == "metadata_scraping",
            SystemSetting.key == "douban_proxy",
        )
        proxy_result = await db.execute(proxy_query)
        proxy_setting = proxy_result.scalar_one_or_none()

        proxy_config = {}
        if proxy_setting and proxy_setting.value:
            proxy_config = {
                "enabled": True,
                "url": proxy_setting.value,
            }
        
        # 豆瓣不需要API Key，但需要配置代理和Cookie (DoubanAdapter会自动处理)
        return DoubanAdapter({"proxy_config": proxy_config})

    @staticmethod
    async def ensure_person_details(db: AsyncSession, person_id: int) -> UnifiedPerson:
        """
        确保人员详情已加载（Lazy Load）
        """
        stmt = select(UnifiedPerson).where(UnifiedPerson.id == person_id)
        result = await db.execute(stmt)
        person = result.scalars().first()

        if not person:
            return None

        # 如果未加载详情
        if not person.detail_loaded:
            details = None
            try:
                # 决策使用哪个源
                # 1. 明确指定了 douban 来源
                # 2. 或者只有 douban_id 没有 tmdb_id
                use_douban = (person.metadata_source == "douban") or (person.douban_id and not person.tmdb_id)
                
                if use_douban and person.douban_id:
                    # 使用豆瓣
                    try:
                        adapter = await PersonService._get_douban_adapter(db)
                        details = await adapter.get_person_details(person.douban_id)
                    except Exception as e:
                        logger.error(f"Failed to fetch person details from Douban for {person.id}: {e}")
                
                # 如果没有用豆瓣或者豆瓣失败了，且有TMDB ID，尝试TMDB
                if not details and person.tmdb_id:
                    try:
                        adapter = await PersonService._get_tmdb_adapter(db)
                        details = await adapter.get_person_details(person.tmdb_id)
                    except Exception as e:
                        logger.error(f"Failed to fetch person details from TMDB for {person.id}: {e}")

                if details:
                    person.biography = details.get("biography")
                    person.birthday = _parse_date(details.get("birthday"))
                    person.deathday = _parse_date(details.get("deathday"))
                    person.place_of_birth = details.get("place_of_birth")
                    person.gender = details.get("gender")
                    person.homepage = details.get("homepage")
                    person.known_for_department = MetadataNormalizer.normalize_department(details.get("known_for_department"))
                    person.popularity = details.get("popularity")
                    person.family_info = details.get("family_info")
                    person.raw_data = details

                    
                    # 合并别名
                    existing_aka = person.other_names or []
                    new_aka = details.get("other_names") or []
                    all_aka = list(set(existing_aka + new_aka))
                    person.other_names = all_aka
                    
                    # 如果之前没有URL，更新URL
                    if not person.profile_url and details.get("profile_url"):
                         person.profile_url = details.get("profile_url")

                    person.detail_loaded = True
                    person.detail_loaded_at = now()
                    
                    db.add(person)
                    await db.commit()
                    await db.refresh(person)
            except Exception as e:
                logger.error(f"Failed to process person details for {person.id}: {e}")

        return person

    @staticmethod
    async def batch_sync_details(db: AsyncSession, limit: int = 50) -> Dict[str, Any]:
        """
        批量同步人员详情（从 TMDB 获取 biography/birthday 等字段）
        查询 detail_loaded=False 且 tmdb_id 不为空的人员记录
        """
        stmt = (
            select(UnifiedPerson)
            .where(
                UnifiedPerson.detail_loaded == False,
            )
            .order_by(UnifiedPerson.id.asc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        persons = result.scalars().all()

        total = len(persons)
        if total == 0:
            return {"total": 0, "success": 0, "failed": 0, "errors": []}

        # 缓存适配器
        tmdb_adapter = None
        douban_adapter = None
        
        try:
             tmdb_adapter = await PersonService._get_tmdb_adapter(db)
        except:
             pass
             
        try:
             douban_adapter = await PersonService._get_douban_adapter(db)
        except:
             pass

        success = 0
        failed = 0
        errors = []

        for person in persons:
            details = None
            try:
                use_douban = (person.metadata_source == "douban") or (person.douban_id and not person.tmdb_id)
                
                if use_douban and person.douban_id and douban_adapter:
                     try:
                        details = await douban_adapter.get_person_details(person.douban_id)
                     except Exception as e:
                        errors.append(f"Person {person.id} Douban error: {e}")

                if not details and person.tmdb_id and tmdb_adapter:
                    try:
                        details = await tmdb_adapter.get_person_details(person.tmdb_id)
                    except Exception as e:
                        errors.append(f"Person {person.id} TMDB error: {e}")

                if details:
                    person.biography = details.get("biography")
                    person.birthday = _parse_date(details.get("birthday"))
                    person.deathday = _parse_date(details.get("deathday"))
                    person.place_of_birth = details.get("place_of_birth")
                    person.gender = details.get("gender")
                    person.homepage = details.get("homepage")
                    person.known_for_department = MetadataNormalizer.normalize_department(details.get("known_for_department"))
                    person.popularity = details.get("popularity")
                    person.family_info = details.get("family_info")
                    person.raw_data = details

                    
                    existing_aka = person.other_names or []
                    new_aka = details.get("other_names") or []
                    person.other_names = list(set(existing_aka + new_aka))

                    person.detail_loaded = True
                    person.detail_loaded_at = now()
                    db.add(person)
                    await db.commit()
                    success += 1
                else:
                    failed += 1
                    msg = "No details found from any source"
                    errors.append(f"Person {person.id} ({person.name}): {msg}")
                    
                    # 标记为已处理，避免重复同步
                    person.detail_loaded = True
                    person.detail_loaded_at = now()
                    person.raw_data = {"error": msg, "failed_at": now().isoformat()}
                    db.add(person)
                    await db.commit()
            except Exception as e:
                failed += 1
                msg = str(e)
                errors.append(f"Person {person.id} ({person.name}): {msg}")
                logger.error(f"batch_sync_details: person {person.id} failed: {e}")
                
                # 发生错误也标记为已处理，避免卡死在某几条数据上
                try:
                    person.detail_loaded = True
                    person.detail_loaded_at = now()
                    person.raw_data = {"error": msg, "failed_at": now().isoformat()}
                    db.add(person)
                    await db.commit()
                except Exception as db_e:
                    logger.error(f"Failed to update error status for person {person.id}: {db_e}")

            # 避免限流
            await asyncio.sleep(0.3)

        return {
            "total": total,
            "success": success,
            "failed": failed,
            "errors": errors[:20],
        }
