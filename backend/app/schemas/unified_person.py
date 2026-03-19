# -*- coding: utf-8 -*-
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from pydantic import BaseModel, ConfigDict


def to_camel(string: str) -> str:
    """将 snake_case 转换为 camelCase"""
    components = string.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


# 引用 UnifiedMovie 和 UnifiedTVSeries 的简单 schema 避免循环引用
# 或者只定义我们需要返回的最少字段
class UnifiedMovieSimple(BaseModel):
    id: int
    title: str
    original_title: Optional[str] = None
    year: Optional[int] = None
    poster_url: Optional[str] = None
    rating_douban: Optional[float] = None
    rating_tmdb: Optional[float] = None

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
    )

class UnifiedTVSeriesSimple(BaseModel):
    id: int
    title: str
    original_title: Optional[str] = None
    year: Optional[int] = None
    poster_url: Optional[str] = None
    rating_douban: Optional[float] = None
    rating_tmdb: Optional[float] = None

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
    )


class UnifiedPersonBase(BaseModel):
    name: str
    other_names: Optional[List[str]] = None
    tmdb_id: Optional[int] = None
    imdb_id: Optional[str] = None
    douban_id: Optional[str] = None
    profile_url: Optional[str] = None
    gender: Optional[int] = None
    biography: Optional[str] = None
    birthday: Optional[date] = None
    deathday: Optional[date] = None
    place_of_birth: Optional[str] = None
    homepage: Optional[str] = None
    known_for_department: Optional[str] = None
    popularity: Optional[float] = None
    family_info: Optional[str] = None
    metadata_source: Optional[str] = None


class UnifiedPerson(UnifiedPersonBase):
    id: int
    detail_loaded: bool
    detail_loaded_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
    )

class UnifiedPersonUpdate(BaseModel):
    name: Optional[str] = None
    other_names: Optional[List[str]] = None
    gender: Optional[int] = None
    biography: Optional[str] = None
    birthday: Optional[date] = None
    deathday: Optional[date] = None
    place_of_birth: Optional[str] = None
    homepage: Optional[str] = None
    known_for_department: Optional[str] = None
    popularity: Optional[float] = None
    family_info: Optional[str] = None
    profile_url: Optional[str] = None
    tmdb_id: Optional[int] = None
    imdb_id: Optional[str] = None
    douban_id: Optional[str] = None

    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
    )

class UnifiedPersonListItem(BaseModel):
    """人员列表项 - 精简版"""
    id: int
    name: str
    other_names: Optional[List[str]] = None
    profile_url: Optional[str] = None
    gender: Optional[int] = None
    known_for_department: Optional[str] = None
    popularity: Optional[float] = None
    birthday: Optional[date] = None
    place_of_birth: Optional[str] = None
    metadata_source: Optional[str] = None
    detail_loaded: bool = False
    movie_count: int = 0
    tv_count: int = 0

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
    )


class MovieCredit(BaseModel):
    job: str
    character: Optional[str] = None
    order: Optional[int] = 0
    movie: UnifiedMovieSimple

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
    )

class TVSeriesCredit(BaseModel):
    job: str
    character: Optional[str] = None
    order: Optional[int] = 0
    tv_series: UnifiedTVSeriesSimple

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
    )

class PersonCredits(BaseModel):
    cast_movies: List[MovieCredit] = []
    crew_movies: List[MovieCredit] = []
    cast_tv: List[TVSeriesCredit] = []
    crew_tv: List[TVSeriesCredit] = []

    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
    )
