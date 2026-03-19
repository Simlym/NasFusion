# -*- coding: utf-8 -*-
"""
修复 unified_movies 和 unified_tv_series 表中的元数据编码问题

主要问题:
1. genres/languages/countries 字段包含双重转义的 Unicode 字符
2. languages 和 countries 需要使用 MetadataNormalizer 进行标准化

使用方法:
    python scripts/fix_metadata_encoding.py
"""
import asyncio
import json
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import select, update
from app.core.database import async_session_local
from app.models.unified_movie import UnifiedMovie
from app.models.unified_tv_series import UnifiedTVSeries
from app.utils.metadata_normalization import MetadataNormalizer


class MetadataFixer:
    """元数据修复工具"""

    def __init__(self):
        self.fixed_movies = 0
        self.fixed_tv_series = 0
        self.error_count = 0

    @staticmethod
    def fix_json_field(value):
        """
        修复 JSON 字段的编码问题

        Args:
            value: 原始值(可能是字符串或列表)

        Returns:
            修复后的列表,如果输入为空则返回 None
        """
        if not value:
            return None

        # 如果已经是列表,检查列表内容是否需要修复
        if isinstance(value, list):
            # 检查列表中是否包含已经正确的中文字符串
            # 如果所有元素都是字符串且不为空,直接返回
            if all(isinstance(item, str) for item in value):
                return value
            return value

        # 如果是字符串,尝试解析
        if isinstance(value, str):
            try:
                # 尝试 JSON 解析
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return parsed
                return None
            except (json.JSONDecodeError, TypeError):
                return None

        return None

    @staticmethod
    def normalize_languages(languages):
        """
        标准化语言列表

        Args:
            languages: 语言列表

        Returns:
            标准化后的语言列表
        """
        if not languages or not isinstance(languages, list):
            return None

        normalized = []
        for lang in languages:
            if not lang:
                continue
            normalized_lang = MetadataNormalizer.normalize_language(lang)
            if normalized_lang and normalized_lang not in normalized:
                normalized.append(normalized_lang)

        return normalized if normalized else None

    @staticmethod
    def normalize_countries(countries):
        """
        标准化国家/地区列表

        Args:
            countries: 国家/地区列表

        Returns:
            标准化后的国家/地区列表
        """
        if not countries or not isinstance(countries, list):
            return None

        normalized = []
        for country in countries:
            if not country:
                continue
            normalized_country = MetadataNormalizer.normalize_country(country)
            if normalized_country and normalized_country not in normalized:
                normalized.append(normalized_country)

        return normalized if normalized else None

    async def fix_movie(self, db, movie):
        """
        修复单个电影记录

        Args:
            db: 数据库会话
            movie: UnifiedMovie 实例

        Returns:
            是否修复成功
        """
        try:
            updated = False
            changes = []

            # 修复 genres
            if movie.genres:
                fixed_genres = self.fix_json_field(movie.genres)
                if fixed_genres != movie.genres:
                    movie.genres = fixed_genres
                    updated = True
                    changes.append("genres")

            # 修复并标准化 languages
            if movie.languages:
                fixed_languages = self.fix_json_field(movie.languages)
                if fixed_languages:
                    normalized_languages = self.normalize_languages(fixed_languages)
                    if normalized_languages != movie.languages:
                        old_langs = movie.languages
                        movie.languages = normalized_languages
                        updated = True
                        changes.append(f"languages: {old_langs} → {normalized_languages}")

            # 修复并标准化 countries
            if movie.countries:
                fixed_countries = self.fix_json_field(movie.countries)
                if fixed_countries:
                    normalized_countries = self.normalize_countries(fixed_countries)
                    if normalized_countries != movie.countries:
                        old_countries = movie.countries
                        movie.countries = normalized_countries
                        updated = True
                        changes.append(f"countries: {old_countries} → {normalized_countries}")

            if updated:
                await db.commit()
                print(f"✓ 修复电影 {movie.id} ({movie.title}): {', '.join(changes)}")
                return True
            return False

        except Exception as e:
            print(f"✗ 修复电影 {movie.id} ({movie.title}) 失败: {e}")
            await db.rollback()
            self.error_count += 1
            return False

    async def fix_tv_series(self, db, tv):
        """
        修复单个电视剧记录

        Args:
            db: 数据库会话
            tv: UnifiedTVSeries 实例

        Returns:
            是否修复成功
        """
        try:
            updated = False
            changes = []

            # 修复 genres
            if tv.genres:
                fixed_genres = self.fix_json_field(tv.genres)
                if fixed_genres != tv.genres:
                    tv.genres = fixed_genres
                    updated = True
                    changes.append("genres")

            # 修复并标准化 languages
            if tv.languages:
                fixed_languages = self.fix_json_field(tv.languages)
                if fixed_languages:
                    normalized_languages = self.normalize_languages(fixed_languages)
                    if normalized_languages != tv.languages:
                        old_langs = tv.languages
                        tv.languages = normalized_languages
                        updated = True
                        changes.append(f"languages: {old_langs} → {normalized_languages}")

            # 修复并标准化 countries
            if tv.countries:
                fixed_countries = self.fix_json_field(tv.countries)
                if fixed_countries:
                    normalized_countries = self.normalize_countries(fixed_countries)
                    if normalized_countries != tv.countries:
                        old_countries = tv.countries
                        tv.countries = normalized_countries
                        updated = True
                        changes.append(f"countries: {old_countries} → {normalized_countries}")

            if updated:
                await db.commit()
                print(f"✓ 修复电视剧 {tv.id} ({tv.title}): {', '.join(changes)}")
                return True
            return False

        except Exception as e:
            print(f"✗ 修复电视剧 {tv.id} ({tv.title}) 失败: {e}")
            await db.rollback()
            self.error_count += 1
            return False

    async def fix_all_movies(self):
        """修复所有电影记录"""
        print("开始修复电影数据...")

        async with async_session_local() as db:
            # 查询所有电影(分批处理以避免内存问题)
            batch_size = 100
            offset = 0

            while True:
                query = select(UnifiedMovie).limit(batch_size).offset(offset)
                result = await db.execute(query)
                movies = result.scalars().all()

                if not movies:
                    break

                for movie in movies:
                    if await self.fix_movie(db, movie):
                        self.fixed_movies += 1

                offset += batch_size

        print(f"电影修复完成! 共修复 {self.fixed_movies} 条记录")

    async def fix_all_tv_series(self):
        """修复所有电视剧记录"""
        print("\n开始修复电视剧数据...")

        async with async_session_local() as db:
            # 查询所有电视剧(分批处理)
            batch_size = 100
            offset = 0

            while True:
                query = select(UnifiedTVSeries).limit(batch_size).offset(offset)
                result = await db.execute(query)
                tv_series_list = result.scalars().all()

                if not tv_series_list:
                    break

                for tv in tv_series_list:
                    if await self.fix_tv_series(db, tv):
                        self.fixed_tv_series += 1

                offset += batch_size

        print(f"电视剧修复完成! 共修复 {self.fixed_tv_series} 条记录")

    async def run(self):
        """执行修复任务"""
        print("="*60)
        print("元数据修复工具")
        print("="*60)

        await self.fix_all_movies()
        await self.fix_all_tv_series()

        print("\n"+"="*60)
        print("修复汇总:")
        print(f"  - 电影: {self.fixed_movies} 条")
        print(f"  - 电视剧: {self.fixed_tv_series} 条")
        print(f"  - 错误: {self.error_count} 条")
        print("="*60)


async def main():
    """主函数"""
    fixer = MetadataFixer()
    await fixer.run()


if __name__ == "__main__":
    asyncio.run(main())
