# -*- coding: utf-8 -*-
"""
修复 douban 类型资源的导演和演员数据

问题描述:
1. 通过 mteam_douban 来源识别的资源，directors/actors 可能是纯字符串数组（如 ["张三", "李四"]），
   缺少 douban_id、thumb_url 等完整信息
2. 通过 douban_api 来源识别但 celebrities 接口失败的资源，directors/actors 缺少正确的 douban_id
3. 部分资源的 directors/actors 为空或不完整

修复方式:
- 对所有有 douban_id 的 unified_movies 和 unified_tv_series，重新调用豆瓣 celebrities API
- 用完整的演职员数据（含 douban_id、latin_name、thumb_url、character 等）更新 JSON 字段
- 同步更新 unified_persons + movie_credits / tv_series_credits 关联表

使用方法:
    cd backend
    python scripts/fix_douban_celebrities.py [--dry-run] [--limit N] [--delay SECONDS]

参数:
    --dry-run     仅检查，不写入数据库
    --limit N     只处理前 N 条记录（调试用）
    --delay S     每次 API 请求之间的延迟秒数（默认 1.0，避免限流）
"""
import argparse
import asyncio
import logging
import sys
from pathlib import Path
import json
import os

# 添加项目根目录到 Python 路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# 加载 .env 文件（必须在导入 app 模块之前）
from dotenv import load_dotenv
load_dotenv(backend_dir / ".env")

from sqlalchemy import select, func
from app.core.database import async_session_local
from app.models.unified_movie import UnifiedMovie
from app.models.unified_tv_series import UnifiedTVSeries

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def _is_incomplete_celebrities(directors, actors) -> bool:
    """
    判断导演/演员数据是否不完整，需要修复

    不完整的情况：
    1. directors 或 actors 为 None/空
    2. 列表中包含纯字符串（如 "张三"）
    3. 列表中的 dict 缺少 douban_id 或 thumb_url
    """
    for person_list in [directors, actors]:
        if not person_list:
            return True
        for item in person_list:
            if isinstance(item, str):
                # 纯字符串，需要修复
                return True
            if isinstance(item, dict):
                # 缺少 douban_id 表示数据不完整
                if not item.get("douban_id"):
                    return True
    return False


class DoubanCelebritiesFixer:
    """豆瓣演职员数据修复工具"""

    def __init__(self, dry_run: bool = False, limit: int = 0, delay: float = 1.0):
        self.dry_run = dry_run
        self.limit = limit
        self.delay = delay

        self.state_file = Path(__file__).parent / "processed_douban_celebrities.json"
        self.processed_data = self._load_state()
        self.processed_movies = set(self.processed_data.get("movies", []))
        self.processed_tv = set(self.processed_data.get("tv_series", []))
        self.invalid_ids = set(self.processed_data.get("invalid_ids", []))

        # 统计
        self.total_movies = 0
        self.total_tv = 0
        self.fixed_movies = 0
        self.fixed_tv = 0
        self.skipped_movies = 0
        self.skipped_tv = 0
        self.error_movies = 0
        self.error_tv = 0

    def _load_state(self):
        """加载处理记录"""
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"加载状态文件失败: {e}")
        return {"movies": [], "tv_series": [], "invalid_ids": []}

    def _save_state(self):
        """保存处理记录"""
        data = {
            "movies": list(self.processed_movies),
            "tv_series": list(self.processed_tv),
            "invalid_ids": list(self.invalid_ids)
        }
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存状态文件失败: {e}")

    async def _get_douban_adapter(self, db):
        """获取豆瓣适配器实例（从数据库读取代理配置）"""
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

        return DoubanAdapter({"proxy_config": proxy_config, "timeout": 30, "max_retries": 3})

    async def _fetch_celebrities(self, adapter, douban_id: str, media_type: str) -> dict:
        """
        获取演职员数据
        
        Raises:
            Exception: 如果是 404 等严重错误, 抛出异常以便上层处理
        """
        try:
            if media_type == "movie":
                return await adapter.get_movie_celebrities(douban_id)
            else:
                return await adapter.get_tv_celebrities(douban_id)
        except Exception as e:
            # 如果是 404，重新抛出，以便上层标记为无效 ID
            if "404" in str(e):
                raise e
            logger.warning(f"获取演职员失败 (douban_id={douban_id}, type={media_type}): {e}")
            return None

    async def _process_single_movie(self, db, adapter, movie: UnifiedMovie) -> bool:
        """处理单个电影: 修复数据并同步 Credits"""
        douban_id = movie.douban_id
        api_called = False

        # 检查是否需要修复
        if _is_incomplete_celebrities(movie.directors, movie.actors):
            try:
                # 调用豆瓣 API
                celebrities = await self._fetch_celebrities(adapter, douban_id, "movie")
                if not celebrities:
                    logger.warning(f"  电影 {movie.id} ({movie.title}) - API返回空")
                    return False
                
                api_called = True
                new_directors = celebrities.get("directors", [])
                new_actors = celebrities.get("actors", [])

                if new_directors or new_actors:
                     # 日志对比
                    old_d_names = self._extract_names(movie.directors)
                    new_d_names = self._extract_names(new_directors)
                    logger.info(f"  修复电影 {movie.id} ({movie.title}): 导演 {old_d_names} -> {new_d_names}")

                    if not self.dry_run:
                        movie.directors = new_directors if new_directors else movie.directors
                        movie.actors = new_actors if new_actors else movie.actors
            except Exception as e:
                if "404" in str(e):
                    logger.error(f"  电影 {movie.id} ({movie.title}) ID失效 (404) - 标记为无效")
                    self.invalid_ids.add(douban_id)
                    self._save_state()
                    # 404 算作错误
                    self.error_movies += 1 
                    return False
                raise e # 其他错误继续抛出
        
        # 如果是 Dry Run，到这里就结束
        if self.dry_run:
            return True

        # 无论数据是否刚修复，只要现在有数据，就执行同步
        # 这满足了用户 "数据修复时，可以执行识别逻辑" 的需求，
        # 即使数据本来就是好的，也会刷新一下 Credits 关联
        try:
            from app.services.identification.person_service import PersonService
            credits_data = {
                "directors": movie.directors or [],
                "actors": movie.actors or [],
            }
            await PersonService.sync_movie_credits(db, movie, credits_data)
            
            if not api_called:
                # 只有当没有调用 API (仅仅同步) 时打印这条，否则上面会有 "修复电影..." 的日志
                logger.info(f"  [仅同步] 电影 {movie.id} ({movie.title}) - 关联已更新")
                
        except Exception as e:
            logger.error(f"  同步 credits 失败 (movie={movie.id}): {e}")
            # 如果是 API 修复成功但 sync 失败，仍然算作处理成功吗？
            # 这里的逻辑是尽力同步，不阻断
        
        await db.commit()
        
        # 如果调用了 API，延迟一下
        if api_called:
            await asyncio.sleep(self.delay)
            
        return True

    async def _process_single_tv(self, db, adapter, tv: UnifiedTVSeries) -> bool:
        """处理单个剧集: 修复数据并同步 Credits"""
        douban_id = tv.douban_id
        api_called = False

        if _is_incomplete_celebrities(tv.directors, tv.actors):
            try:
                celebrities = await self._fetch_celebrities(adapter, douban_id, "tv")
                if not celebrities:
                    logger.warning(f"  剧集 {tv.id} ({tv.title}) - API返回空")
                    return False
                
                api_called = True
                new_directors = celebrities.get("directors", [])
                new_actors = celebrities.get("actors", [])

                if new_directors or new_actors:
                    old_d_names = self._extract_names(tv.directors)
                    new_d_names = self._extract_names(new_directors)
                    logger.info(f"  修复剧集 {tv.id} ({tv.title}): 导演 {old_d_names} -> {new_d_names}")

                    if not self.dry_run:
                        tv.directors = new_directors if new_directors else tv.directors
                        tv.actors = new_actors if new_actors else tv.actors
            except Exception as e:
                if "404" in str(e):
                    logger.error(f"  剧集 {tv.id} ({tv.title}) ID失效 (404) - 标记为无效")
                    self.invalid_ids.add(douban_id)
                    self._save_state()
                    self.error_tv += 1
                    return False
                raise e

        if self.dry_run:
            return True

        # 同步 Credits
        try:
            from app.services.identification.person_service import PersonService
            credits_data = {
                "directors": tv.directors or [],
                "actors": tv.actors or [],
                "creators": tv.creators or [],
            }
            await PersonService.sync_tv_credits(db, tv, credits_data)
            
            if not api_called:
                logger.info(f"  [仅同步] 剧集 {tv.id} ({tv.title}) - 关联已更新")
                
        except Exception as e:
            logger.error(f"  同步 credits 失败 (tv={tv.id}): {e}")

        await db.commit()
        
        if api_called:
            await asyncio.sleep(self.delay)

        return True

    @staticmethod
    def _extract_names(person_list) -> list:
        """从人员列表中提取名字用于日志展示"""
        if not person_list:
            return []
        names = []
        for item in person_list:
            if isinstance(item, str):
                names.append(item)
            elif isinstance(item, dict):
                names.append(item.get("name", "?"))
        return names

    async def fix_movies(self):
        """修复所有电影"""
        logger.info("=" * 60)
        logger.info("开始修复电影演职员数据...")
        logger.info("=" * 60)

        # 1. 获取所有需要处理的 ID
        movie_ids = []
        async with async_session_local() as db:
            query = (
                select(UnifiedMovie.id)
                .where(UnifiedMovie.douban_id.isnot(None))
            )
            # 排除已处理的 ID
            if self.processed_movies:
                query = query.where(UnifiedMovie.id.notin_(self.processed_movies))
            
            query = query.order_by(UnifiedMovie.id)

            if self.limit > 0:
                query = query.limit(self.limit)

            result = await db.execute(query)
            movie_ids = result.scalars().all()
        
        self.total_movies = len(movie_ids)
        logger.info(f"共找到 {self.total_movies} 部有豆瓣ID的电影")

        for i, m_id in enumerate(movie_ids, 1):
            if m_id in self.processed_movies:
                self.skipped_movies += 1
                continue

            # 每个任务使用独立的 Session
            async with async_session_local() as db:
                adapter = await self._get_douban_adapter(db)
                try:
                    movie = await db.get(UnifiedMovie, m_id)
                    if not movie:
                        continue

                    if movie.douban_id in self.invalid_ids:
                        self.skipped_movies += 1
                        if i % 20 == 0:
                             logger.info(f"  进度: {i}/{self.total_movies} (处理: {self.fixed_movies}, 跳过: {self.skipped_movies}, 错误: {self.error_movies})")
                        continue

                    # 处理电影
                    processed = await self._process_single_movie(db, adapter, movie)
                    
                    if processed:
                        self.fixed_movies += 1
                        self.processed_movies.add(movie.id)
                        self._save_state()
                    else:
                        self.skipped_movies += 1

                except Exception as e:
                    logger.error(f"  电影 {m_id} 处理异常: {e}")
                    self.error_movies += 1
                
                # 进度日志
                if i % 20 == 0:
                    logger.info(f"  进度: {i}/{self.total_movies} (处理: {self.fixed_movies}, 跳过: {self.skipped_movies}, 错误: {self.error_movies})")

        logger.info(f"电影修复完成: 总计 {self.total_movies}, 修复 {self.fixed_movies}, 跳过 {self.skipped_movies}, 错误 {self.error_movies}")

    async def fix_tv_series(self):
        """修复所有电视剧"""
        logger.info("")
        logger.info("=" * 60)
        logger.info("开始修复电视剧演职员数据...")
        logger.info("=" * 60)

        # 1. 获取所有需要处理的 ID
        tv_ids = []
        async with async_session_local() as db:
            query = (
                select(UnifiedTVSeries.id)
                .where(UnifiedTVSeries.douban_id.isnot(None))
            )
            # 排除已处理的 ID
            if self.processed_tv:
                query = query.where(UnifiedTVSeries.id.notin_(self.processed_tv))
                
            query = query.order_by(UnifiedTVSeries.id)

            if self.limit > 0:
                query = query.limit(self.limit)

            result = await db.execute(query)
            tv_ids = result.scalars().all()
        
        self.total_tv = len(tv_ids)
        logger.info(f"共找到 {self.total_tv} 部有豆瓣ID的电视剧")

        for i, t_id in enumerate(tv_ids, 1):
            if t_id in self.processed_tv:
                self.skipped_tv += 1
                continue

            # 每个任务使用独立的 Session
            async with async_session_local() as db:
                adapter = await self._get_douban_adapter(db)
                try:
                    tv = await db.get(UnifiedTVSeries, t_id)
                    if not tv:
                        continue

                    if tv.douban_id in self.invalid_ids:
                        self.skipped_tv += 1
                        if i % 20 == 0:
                            logger.info(f"  进度: {i}/{self.total_tv} (处理: {self.fixed_tv}, 跳过: {self.skipped_tv}, 错误: {self.error_tv})")
                        continue

                    # 处理剧集
                    processed = await self._process_single_tv(db, adapter, tv)
                    
                    if processed:
                        self.fixed_tv += 1
                        self.processed_tv.add(tv.id)
                        self._save_state()
                    else:
                        self.skipped_tv += 1

                except Exception as e:
                    logger.error(f"  剧集 {t_id} 处理异常: {e}")
                    self.error_tv += 1
                
                if i % 20 == 0:
                    logger.info(f"  进度: {i}/{self.total_tv} (处理: {self.fixed_tv}, 跳过: {self.skipped_tv}, 错误: {self.error_tv})")

        logger.info(f"电视剧修复完成: 总计 {self.total_tv}, 修复 {self.fixed_tv}, 跳过 {self.skipped_tv}, 错误 {self.error_tv}")

    async def run(self):
        """执行修复"""
        mode = "DRY-RUN (仅检查)" if self.dry_run else "实际修复"
        logger.info(f"豆瓣演职员数据修复工具 - 模式: {mode}")
        if self.limit > 0:
            logger.info(f"限制处理数量: {self.limit}")
        logger.info(f"API 请求延迟: {self.delay}s")
        logger.info("")

        await self.fix_movies()
        await self.fix_tv_series()

        # 汇总
        logger.info("")
        logger.info("=" * 60)
        logger.info("修复汇总:")
        logger.info(f"  电影: 总计 {self.total_movies}, 修复 {self.fixed_movies}, 跳过 {self.skipped_movies}, 错误 {self.error_movies}")
        logger.info(f"  电视剧: 总计 {self.total_tv}, 修复 {self.fixed_tv}, 跳过 {self.skipped_tv}, 错误 {self.error_tv}")
        logger.info("=" * 60)


def parse_args():
    parser = argparse.ArgumentParser(description="修复豆瓣演职员数据")
    parser.add_argument("--dry-run", action="store_true", help="仅检查，不写入数据库")
    parser.add_argument("--limit", type=int, default=0, help="只处理前 N 条记录（0=全部）")
    parser.add_argument("--delay", type=float, default=1.0, help="API 请求延迟秒数（默认 1.0）")
    return parser.parse_args()


async def main():
    args = parse_args()
    fixer = DoubanCelebritiesFixer(
        dry_run=args.dry_run,
        limit=args.limit,
        delay=args.delay,
    )
    await fixer.run()


if __name__ == "__main__":
    asyncio.run(main())
