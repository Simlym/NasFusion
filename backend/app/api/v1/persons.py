# -*- coding: utf-8 -*-
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, or_, and_, not_, literal, String
from sqlalchemy.orm import selectinload

from app.core.dependencies import get_db
from app.models.unified_person import UnifiedPerson, MovieCredit, TVSeriesCredit
from app.models.unified_movie import UnifiedMovie
from app.models.unified_tv_series import UnifiedTVSeries
from app.schemas.unified_person import (
    UnifiedPerson as UnifiedPersonSchema,
    UnifiedPersonListItem,
    PersonCredits,
    UnifiedPersonUpdate,
)
from app.services.identification.person_service import PersonService

router = APIRouter()


@router.get("", response_model=dict)
async def get_persons(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索关键词（姓名）"),
    gender: Optional[int] = Query(None, description="性别筛选: 1=女, 2=男"),
    department: Optional[str] = Query(None, description="职能筛选: Actor, Director, Writing 等"),
    metadata_source: Optional[str] = Query(None, description="数据来源: tmdb, douban"),
    country: Optional[str] = Query(None, description="国家/地区筛选: CN=中国大陆, HK=中国香港, TW=中国台湾, JP=日本, KR=韩国, US=美国"),
    detail_loaded: Optional[bool] = Query(None, description="是否已加载详情"),
    sort_by: Optional[str] = Query("popularity", description="排序字段: popularity, name, birthday, created_at"),
    sort_order: Optional[str] = Query("desc", description="排序方向: asc, desc"),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    获取人员列表（分页 + 搜索 + 筛选）
    """
    # 子查询：每个 person 的电影数量（按 movie_id 去重）
    movie_count_subq = (
        select(
            MovieCredit.person_id,
            func.count(func.distinct(MovieCredit.movie_id)).label("movie_count")
        )
        .group_by(MovieCredit.person_id)
        .subquery()
    )

    # 子查询：每个 person 的电视剧数量（按 tv_series_id 去重）
    tv_count_subq = (
        select(
            TVSeriesCredit.person_id,
            func.count(func.distinct(TVSeriesCredit.tv_series_id)).label("tv_count")
        )
        .group_by(TVSeriesCredit.person_id)
        .subquery()
    )

    # 构建基础查询
    base_query = (
        select(
            UnifiedPerson,
            func.coalesce(movie_count_subq.c.movie_count, literal(0)).label("movie_count"),
            func.coalesce(tv_count_subq.c.tv_count, literal(0)).label("tv_count"),
        )
        .outerjoin(movie_count_subq, UnifiedPerson.id == movie_count_subq.c.person_id)
        .outerjoin(tv_count_subq, UnifiedPerson.id == tv_count_subq.c.person_id)
    )
    count_query = select(func.count()).select_from(UnifiedPerson)

    filters = []

    # 搜索过滤（姓名 + 别名）
    if search:
        search_filter = or_(
            UnifiedPerson.name.ilike(f"%{search}%"),
            UnifiedPerson.other_names.cast(String).ilike(f"%{search}%"),
        )
        filters.append(search_filter)

    # 性别筛选
    if gender is not None:
        filters.append(UnifiedPerson.gender == gender)

    # 职能筛选
    if department:
        filters.append(UnifiedPerson.known_for_department == department)

    # 国家/地区筛选
    if country:
        country_filter_map = {
            "CN": {
                "include": ["%中国%", "%China%", "%Beijing%", "%Shanghai%", "%Guangdong%", "%北京%", "%上海%", "%广东%"],
                "exclude": ["%香港%", "%Hong Kong%", "%台湾%", "%Taiwan%", "%澳门%", "%Macau%"],
            },
            "HK": {"include": ["%香港%", "%Hong Kong%"]},
            "TW": {"include": ["%台湾%", "%Taiwan%"]},
            "JP": {"include": ["%日本%", "%Japan%", "%Tokyo%", "%Osaka%", "%東京%", "%大阪%"]},
            "KR": {"include": ["%韩国%", "%Korea%", "%Seoul%", "%首尔%"]},
            "US": {"include": ["%美国%", "%United States%", "%, U.S.%", "%USA%", "%America%"]},
            "GB": {"include": ["%英国%", "%United Kingdom%", "%England%", "%UK%", "%London%", "%Scotland%", "%Wales%", "%伦敦%"]},
            "FR": {"include": ["%法国%", "%France%", "%Paris%", "%巴黎%"]},
            "DE": {"include": ["%德国%", "%Germany%", "%Berlin%", "%柏林%"]},
            "IN": {"include": ["%印度%", "%India%", "%Mumbai%", "%孟买%"]},
            "TH": {"include": ["%泰国%", "%Thailand%", "%Bangkok%", "%曼谷%"]},
            "CA": {"include": ["%加拿大%", "%Canada%"]},
            "AU": {"include": ["%澳大利亚%", "%Australia%", "%澳洲%"]},
        }
        if country == "OTHER":
            # "其他"：排除所有已定义国家的匹配模式
            all_patterns = []
            for cfg in country_filter_map.values():
                all_patterns.extend(cfg["include"])
            exclude_all = and_(
                UnifiedPerson.place_of_birth.isnot(None),
                *[not_(UnifiedPerson.place_of_birth.ilike(p)) for p in all_patterns]
            )
            filters.append(exclude_all)
        else:
            country_cfg = country_filter_map.get(country)
            if country_cfg:
                include_conditions = [UnifiedPerson.place_of_birth.ilike(p) for p in country_cfg["include"]]
                country_condition = or_(*include_conditions)
                exclude_patterns = country_cfg.get("exclude", [])
                if exclude_patterns:
                    exclude_conditions = [not_(UnifiedPerson.place_of_birth.ilike(p)) for p in exclude_patterns]
                    country_condition = and_(country_condition, *exclude_conditions)
                filters.append(country_condition)

    # 数据来源筛选
    if metadata_source:
        filters.append(UnifiedPerson.metadata_source == metadata_source)

    # 详情加载状态筛选
    if detail_loaded is not None:
        filters.append(UnifiedPerson.detail_loaded == detail_loaded)

    # 应用所有过滤条件
    if filters:
        for f in filters:
            base_query = base_query.where(f)
            count_query = count_query.where(f)

    # 总数
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # 排序
    # 排序
    if sort_by == "movie_count":
        sort_expression = func.coalesce(movie_count_subq.c.movie_count, literal(0))
    elif sort_by == "tv_count":
        sort_expression = func.coalesce(tv_count_subq.c.tv_count, literal(0))
    elif sort_by == "total_credits":
        sort_expression = func.coalesce(movie_count_subq.c.movie_count, literal(0)) + \
                          func.coalesce(tv_count_subq.c.tv_count, literal(0))
    else:
        sort_column_map = {
            "popularity": UnifiedPerson.popularity,
            "name": UnifiedPerson.name,
            "birthday": UnifiedPerson.birthday,
            "created_at": UnifiedPerson.created_at,
        }
        sort_expression = sort_column_map.get(sort_by, UnifiedPerson.popularity)

    if sort_order == "asc":
        order = sort_expression.asc().nullslast()
    else:
        order = sort_expression.desc().nullslast()

    # 分页查询
    skip = (page - 1) * page_size
    query = (
        base_query
        .order_by(order, UnifiedPerson.id.desc())
        .offset(skip)
        .limit(page_size)
    )
    result = await db.execute(query)
    rows = result.all()

    items = []
    for row in rows:
        person = row[0]
        movie_count = row[1]
        tv_count = row[2]
        item = UnifiedPersonListItem.model_validate(person).model_dump(by_alias=True)
        item["movieCount"] = movie_count
        item["tvCount"] = tv_count
        items.append(item)

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.get("/departments", response_model=List[str])
async def get_person_departments(
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    获取所有职能类型（用于筛选下拉）
    """
    query = (
        select(UnifiedPerson.known_for_department)
        .where(UnifiedPerson.known_for_department.isnot(None))
        .distinct()
        .order_by(UnifiedPerson.known_for_department)
    )
    result = await db.execute(query)
    departments = [row[0] for row in result.all() if row[0]]
    return departments


@router.get("/{person_id}", response_model=UnifiedPersonSchema)
async def get_person_details(
    person_id: int,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    获取人员详情
    如果详情未加载，尝试从TMDB获取
    """
    # 使用 Service 确保详情已加载
    person = await PersonService.ensure_person_details(db, person_id)
    
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")
    
    return person


@router.get("/{person_id}/credits", response_model=PersonCredits)
async def get_person_credits(
    person_id: int,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    获取人员参与的作品（电影 + 电视剧）
    """
    # 检查人员是否存在
    person = await db.get(UnifiedPerson, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    # 查询电影关联
    movie_query = (
        select(MovieCredit)
        .options(selectinload(MovieCredit.movie))
        .where(MovieCredit.person_id == person_id)
        .order_by(MovieCredit.movie_id.desc())
    )
    movie_credits_result = await db.execute(movie_query)
    movie_credits = movie_credits_result.scalars().all()

    # 查询电视剧关联
    tv_query = (
        select(TVSeriesCredit)
        .options(selectinload(TVSeriesCredit.tv_series))
        .where(TVSeriesCredit.person_id == person_id)
        .order_by(TVSeriesCredit.tv_series_id.desc())
    )
    tv_credits_result = await db.execute(tv_query)
    tv_credits = tv_credits_result.scalars().all()

    # 分类整理
    cast_movies = []
    crew_movies = []
    cast_tv = []
    crew_tv = []

    for credit in movie_credits:
        if credit.job == "Actor":
            cast_movies.append(credit)
        else:
            crew_movies.append(credit)

    for credit in tv_credits:
        if credit.job == "Actor":
            cast_tv.append(credit)
        else:
            crew_tv.append(credit)

    return {
        "cast_movies": cast_movies,
        "crew_movies": crew_movies,
        "cast_tv": cast_tv,
        "crew_tv": crew_tv,
    }


@router.put("/{person_id}", response_model=UnifiedPersonSchema)
async def update_person(
    person_id: int,
    person_in: UnifiedPersonUpdate,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    更新人员信息
    """
    person = await db.get(UnifiedPerson, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")
    
    update_data = person_in.model_dump(exclude_unset=True)
    
    # 特殊处理 other_names (如果前端传来的是逗号分隔的字符串，可以转列表，但这里假设前端传列表)
    # 如果有特殊逻辑可以在这里加
    
    for field, value in update_data.items():
        setattr(person, field, value)
    
    from app.utils.timezone import now
    person.updated_at = now()
    
    db.add(person)
    await db.commit()
    await db.refresh(person)
    
    return person
