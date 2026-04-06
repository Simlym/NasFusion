# -*- coding: utf-8 -*-
"""
图片缓存服务
处理外部图片的下载、缓存和管理
"""
import asyncio
import hashlib
import os
from datetime import timedelta
from pathlib import Path
from typing import Optional, Dict
from urllib.parse import urlparse

import aiofiles
import httpx
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.image_cache import ImageCache
from app.utils.timezone import now as tz_now


class ImageCacheService:
    """图片缓存服务"""
    
    # 下载锁，避免同一URL并发下载
    _download_locks: Dict[str, asyncio.Lock] = {}
    _locks_lock = asyncio.Lock()  # 保护 _download_locks 的锁

    # 支持的图片类型
    SUPPORTED_CONTENT_TYPES = {
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/png": ".png",
        "image/gif": ".gif",
        "image/webp": ".webp",
        "image/bmp": ".bmp",
    }

    @staticmethod
    def _get_cache_root() -> Path:
        """获取缓存根目录"""
        return Path(settings.IMAGE_CACHE_PATH)

    @staticmethod
    def _ensure_cache_directory() -> None:
        """确保缓存目录存在"""
        cache_root = ImageCacheService._get_cache_root()
        cache_root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _get_source_type(url: str) -> str:
        """根据URL判断来源类型"""
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        if "tmdb.org" in domain or "themoviedb.org" in domain:
            return "tmdb"
        elif "douban" in domain:
            return "douban"
        elif "mteam" in domain:
            return "mteam"
        else:
            return "other"

    @staticmethod
    def _generate_file_path(url: str, content_type: str) -> str:
        """
        生成3级目录文件路径
        格式: ab/cd/ef/abcdef1234567890.ext
        """
        # 计算URL的SHA256哈希
        url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()

        # 获取文件扩展名
        ext = ImageCacheService.SUPPORTED_CONTENT_TYPES.get(content_type, ".jpg")

        # 3级目录结构
        dir1 = url_hash[0:2]
        dir2 = url_hash[2:4]
        dir3 = url_hash[4:6]

        # 完整路径（相对于缓存根目录）
        return f"{dir1}/{dir2}/{dir3}/{url_hash}{ext}"

    @staticmethod
    async def get_cached_image(db: AsyncSession, url: str) -> Optional[ImageCache]:
        """
        获取缓存的图片记录

        Args:
            db: 数据库会话
            url: 原始图片URL

        Returns:
            图片缓存记录或None
        """
        result = await db.execute(
            select(ImageCache).where(ImageCache.original_url == url)
        )
        cache = result.scalar_one_or_none()

        if cache:
            # 优化：限制更新频率，避免每次读取都写数据库
            # 只有当上次访问时间超过24小时前，才更新访问时间和计数
            current_time = tz_now()
            should_update = False
            if not cache.last_accessed_at:
                should_update = True
            else:
                last_accessed = cache.last_accessed_at
                # 兼容旧数据：如果数据库中的时间是 naive datetime，补充时区信息
                if last_accessed.tzinfo is None:
                    from app.utils.timezone import ensure_timezone
                    last_accessed = ensure_timezone(last_accessed)
                if (current_time - last_accessed) > timedelta(days=1):
                    should_update = True

            if should_update:
                cache.access_count += 1
                cache.last_accessed_at = current_time
                # 注意：这里会产生DB写入，但在高并发读取下比每次都写要好得多
                try:
                    await db.commit()
                except Exception:
                    # 统计更新失败不应影响读取
                    await db.rollback()

        return cache

    @staticmethod
    def _extract_real_url(url: str) -> str:
        """
        从代理URL中提取真实的图片URL

        Args:
            url: 可能是代理URL的图片URL

        Returns:
            真实的图片URL
        """
        # 处理gateway996代理URL，提取真实的豆瓣图片URL
        if "gateway996.com" in url and "payload=" in url:
            try:
                from urllib.parse import parse_qs, urlparse, unquote
                parsed = urlparse(url)
                params = parse_qs(parsed.query)
                if "payload" in params:
                    payload = params["payload"][0]
                    # payload格式: uri=https://...&zone=...
                    # 需要URL解码
                    payload = unquote(payload)
                    if "uri=" in payload:
                        # 提取uri参数
                        uri_start = payload.find("uri=") + 4
                        uri_end = payload.find("&", uri_start)
                        if uri_end == -1:
                            real_url = payload[uri_start:]
                        else:
                            real_url = payload[uri_start:uri_end]
                        return real_url
            except Exception as e:
                print(f"解析gateway996 URL失败: {e}")

        return url

    @staticmethod
    def _get_request_headers(url: str) -> dict:
        """
        根据URL获取合适的请求头

        Args:
            url: 图片URL

        Returns:
            请求头字典
        """
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
        }

        # 根据URL添加特定的Referer
        if "doubanio.com" in url:
            # 豆瓣图片需要豆瓣Referer
            headers["Referer"] = "https://movie.douban.com/"
        elif "tmdb.org" in url or "themoviedb.org" in url:
            headers["Referer"] = "https://www.themoviedb.org/"
        elif "m-team" in url or "mteam" in url:
            # M-Team图片需要M-Team Referer
            headers["Referer"] = "https://kp.m-team.cc/"

        return headers

    @staticmethod
    async def _get_url_lock(url: str) -> asyncio.Lock:
        """获取URL特定的锁"""
        async with ImageCacheService._locks_lock:
            if url not in ImageCacheService._download_locks:
                ImageCacheService._download_locks[url] = asyncio.Lock()
            return ImageCacheService._download_locks[url]

    @staticmethod
    async def _release_url_lock(url: str) -> None:
        """释放URL锁（如果不再使用）"""
        async with ImageCacheService._locks_lock:
            # 只有当锁没有被锁定时才清除，这是一个简单的清理策略
            # 在高并发下可能不会立即清除，但 acceptable
            if url in ImageCacheService._download_locks:
                 # 这里我们不直接删除，因为没办法安全地知道是否有其他协程在等待这个锁
                 # 让它保留在内存中，对于有限的URL集合是可以的。
                 # 如果URL数量非常大，可能需要更复杂的引用计数机制。
                 # 考虑到图片缓存通常是热点访问，保留一些锁对象开销不大。
                 pass

    @staticmethod
    async def download_and_cache(
        db: AsyncSession, url: str, timeout: float = 60.0
    ) -> Optional[ImageCache]:
        """
        下载图片并缓存到本地
        
        优化：
        1. 使用锁防止并发下载同一URL
        2. 使用 aiofiles 进行异步文件写入
        """
        # 获取此URL的锁
        lock = await ImageCacheService._get_url_lock(url)
        
        async with lock:
            # 锁定后再次检查是否已缓存
            existing = await ImageCacheService.get_cached_image(db, url)
            if existing:
                full_path = ImageCacheService._get_cache_root() / existing.local_path
                if full_path.exists():
                    return existing
                else:
                    await db.delete(existing)
                    await db.commit()

            # 确保缓存目录存在
            ImageCacheService._ensure_cache_directory()

            try:
                # 提取真实URL（处理gateway996等代理）
                real_url = ImageCacheService._extract_real_url(url)

                # 获取请求头
                headers = ImageCacheService._get_request_headers(real_url)

                # 下载图片（增加超时时间到60秒）
                async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=headers) as client:
                    response = await client.get(real_url)
                    response.raise_for_status()

                    # 获取内容类型
                    content_type = response.headers.get("content-type", "image/jpeg").split(";")[0].strip()
                    if content_type not in ImageCacheService.SUPPORTED_CONTENT_TYPES:
                        if url.lower().endswith(".png"):
                            content_type = "image/png"
                        elif url.lower().endswith(".gif"):
                            content_type = "image/gif"
                        elif url.lower().endswith(".webp"):
                            content_type = "image/webp"
                        else:
                            content_type = "image/jpeg"

                    # 获取图片数据
                    image_data = response.content

                    # 计算文件哈希
                    file_hash = hashlib.sha256(image_data).hexdigest()

                    # 检查是否有相同哈希的文件（去重）
                    existing_by_hash = await db.execute(
                        select(ImageCache).where(ImageCache.file_hash == file_hash)
                    )
                    existing_record = existing_by_hash.scalars().first()

                    if existing_record:
                        try:
                            cache = ImageCache(
                                original_url=url,
                                local_path=existing_record.local_path,
                                file_hash=file_hash,
                                size_bytes=len(image_data),
                                content_type=content_type,
                                source_type=ImageCacheService._get_source_type(url),
                                access_count=1,
                                last_accessed_at=tz_now(),
                            )
                            db.add(cache)
                            await db.commit()
                            return cache
                        except Exception as db_err:
                            await db.rollback()
                            # 再次检查，可能在极短时间内被其他进程插入
                            re_check = await ImageCacheService.get_cached_image(db, url)
                            if re_check:
                                return re_check
                            raise db_err

                    # 生成本地文件路径
                    local_path = ImageCacheService._generate_file_path(url, content_type)
                    full_path = ImageCacheService._get_cache_root() / local_path

                    # 创建目录结构
                    full_path.parent.mkdir(parents=True, exist_ok=True)

                    # 异步保存文件
                    async with aiofiles.open(full_path, "wb") as f:
                        await f.write(image_data)

                    # 创建数据库记录
                    try:
                        cache = ImageCache(
                            original_url=url,
                            local_path=local_path,
                            file_hash=file_hash,
                            size_bytes=len(image_data),
                            content_type=content_type,
                            source_type=ImageCacheService._get_source_type(url),
                            access_count=1,
                            last_accessed_at=tz_now(),
                        )
                        db.add(cache)
                        await db.commit()
                        return cache
                    except Exception as db_err:
                        await db.rollback()
                        re_check = await ImageCacheService.get_cached_image(db, url)
                        if re_check:
                            return re_check
                        # 如果不是DB并发问题，清理文件
                        if full_path.exists():
                            try:
                                full_path.unlink()
                            except Exception:
                                pass
                        raise db_err

            except httpx.HTTPError as e:
                print(f"下载图片失败 {url}: {type(e).__name__}")
                return None
            except Exception as e:
                print(f"缓存图片失败 {url}: {type(e).__name__}: {e}")
                import traceback
                traceback.print_exc()
                return None

    @staticmethod
    def get_file_path(cache: ImageCache) -> Path:
        """
        获取缓存图片的完整文件路径

        Args:
            cache: 图片缓存记录

        Returns:
            完整文件路径
        """
        return ImageCacheService._get_cache_root() / cache.local_path

    @staticmethod
    async def get_cache_stats(db: AsyncSession) -> dict:
        """
        获取缓存统计信息

        Args:
            db: 数据库会话

        Returns:
            统计信息字典
        """
        # 总数量
        total_count_result = await db.execute(select(func.count(ImageCache.id)))
        total_count = total_count_result.scalar() or 0

        # 总大小
        total_size_result = await db.execute(select(func.sum(ImageCache.size_bytes)))
        total_size = total_size_result.scalar() or 0

        # 按来源类型统计
        source_stats_result = await db.execute(
            select(
                ImageCache.source_type,
                func.count(ImageCache.id).label("count"),
                func.sum(ImageCache.size_bytes).label("size"),
            ).group_by(ImageCache.source_type)
        )
        source_stats = {
            row.source_type or "unknown": {
                "count": row.count,
                "size_bytes": row.size or 0,
            }
            for row in source_stats_result.all()
        }

        # 磁盘实际占用（去重后）
        unique_files_result = await db.execute(
            select(
                func.count(func.distinct(ImageCache.file_hash)).label("count"),
            )
        )
        unique_file_count = unique_files_result.scalar() or 0

        return {
            "total_count": total_count,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "unique_file_count": unique_file_count,
            "source_stats": source_stats,
            "cache_directory": str(ImageCacheService._get_cache_root().absolute()),
        }

    @staticmethod
    async def clean_cache(
        db: AsyncSession,
        mode: str = "expired",
        keep_days: int = 30,
        keep_size_mb: int = 1000,
    ) -> dict:
        """
        清理缓存

        Args:
            db: 数据库会话
            mode: 清理模式
                - "expired": 清理过期缓存（根据keep_days）
                - "oldest": 保留最近访问的，删除超出keep_size_mb的
                - "unused": 清理长期未访问的（根据keep_days）
                - "all": 清理全部缓存
            keep_days: 保留最近N天的缓存
            keep_size_mb: 保留最多N MB的缓存

        Returns:
            清理结果统计
        """
        deleted_count = 0
        deleted_size = 0
        deleted_files = []

        if mode == "all":
            # 删除全部缓存
            all_caches_result = await db.execute(select(ImageCache))
            all_caches = all_caches_result.scalars().all()

            for cache in all_caches:
                file_path = ImageCacheService.get_file_path(cache)
                if file_path.exists():
                    deleted_size += cache.size_bytes
                    try:
                        file_path.unlink()
                        deleted_files.append(str(file_path))
                    except Exception:
                        pass
                deleted_count += 1

            await db.execute(delete(ImageCache))
            await db.commit()

        elif mode == "expired" or mode == "unused":
            # 清理过期或长期未访问的缓存
            from datetime import timedelta
            cutoff_date = tz_now() - timedelta(days=keep_days)

            if mode == "expired":
                query = select(ImageCache).where(ImageCache.created_at < cutoff_date)
            else:  # unused
                query = select(ImageCache).where(ImageCache.last_accessed_at < cutoff_date)

            old_caches_result = await db.execute(query)
            old_caches = old_caches_result.scalars().all()

            for cache in old_caches:
                # 检查是否有其他记录引用同一文件
                same_file_count_result = await db.execute(
                    select(func.count(ImageCache.id)).where(
                        ImageCache.local_path == cache.local_path
                    )
                )
                same_file_count = same_file_count_result.scalar() or 0

                if same_file_count <= 1:
                    # 只有这一个记录引用此文件，可以删除文件
                    file_path = ImageCacheService.get_file_path(cache)
                    if file_path.exists():
                        deleted_size += cache.size_bytes
                        try:
                            file_path.unlink()
                            deleted_files.append(str(file_path))
                        except Exception:
                            pass

                await db.delete(cache)
                deleted_count += 1

            await db.commit()

        elif mode == "oldest":
            # 保留最近访问的，删除超出大小限制的
            keep_size_bytes = keep_size_mb * 1024 * 1024

            # 按最后访问时间倒序排列
            all_caches_result = await db.execute(
                select(ImageCache).order_by(ImageCache.last_accessed_at.desc())
            )
            all_caches = all_caches_result.scalars().all()

            current_size = 0
            for cache in all_caches:
                if current_size + cache.size_bytes <= keep_size_bytes:
                    current_size += cache.size_bytes
                else:
                    # 超出大小限制，删除
                    same_file_count_result = await db.execute(
                        select(func.count(ImageCache.id)).where(
                            ImageCache.local_path == cache.local_path
                        )
                    )
                    same_file_count = same_file_count_result.scalar() or 0

                    if same_file_count <= 1:
                        file_path = ImageCacheService.get_file_path(cache)
                        if file_path.exists():
                            deleted_size += cache.size_bytes
                            try:
                                file_path.unlink()
                                deleted_files.append(str(file_path))
                            except Exception:
                                pass

                    await db.delete(cache)
                    deleted_count += 1

            await db.commit()

        # 清理空目录
        ImageCacheService._cleanup_empty_directories()

        return {
            "mode": mode,
            "deleted_count": deleted_count,
            "deleted_size_bytes": deleted_size,
            "deleted_size_mb": round(deleted_size / (1024 * 1024), 2),
            "deleted_files": len(deleted_files),
        }

    @staticmethod
    def _cleanup_empty_directories() -> None:
        """清理空目录"""
        cache_root = ImageCacheService._get_cache_root()
        if not cache_root.exists():
            return

        # 从最深层开始清理空目录
        for dirpath, dirnames, filenames in os.walk(cache_root, topdown=False):
            if dirpath != str(cache_root) and not os.listdir(dirpath):
                try:
                    os.rmdir(dirpath)
                except Exception:
                    pass

    @staticmethod
    async def delete_single_cache(db: AsyncSession, cache_id: int) -> bool:
        """
        删除单个缓存记录

        Args:
            db: 数据库会话
            cache_id: 缓存ID

        Returns:
            是否成功删除
        """
        result = await db.execute(
            select(ImageCache).where(ImageCache.id == cache_id)
        )
        cache = result.scalar_one_or_none()

        if not cache:
            return False

        # 检查是否有其他记录引用同一文件
        same_file_count_result = await db.execute(
            select(func.count(ImageCache.id)).where(
                ImageCache.local_path == cache.local_path
            )
        )
        same_file_count = same_file_count_result.scalar() or 0

        if same_file_count <= 1:
            # 只有这一个记录引用此文件，删除文件
            file_path = ImageCacheService.get_file_path(cache)
            if file_path.exists():
                try:
                    file_path.unlink()
                except Exception:
                    pass

        await db.delete(cache)
        await db.commit()

        return True

    @staticmethod
    def get_file_path(cache: ImageCache) -> Path:
        """
        获取缓存图片的完整文件路径

        Args:
            cache: 图片缓存记录

        Returns:
            完整文件路径
        """
        return ImageCacheService._get_cache_root() / cache.local_path

    @staticmethod
    async def get_cache_stats(db: AsyncSession) -> dict:
        """
        获取缓存统计信息

        Args:
            db: 数据库会话

        Returns:
            统计信息字典
        """
        # 总数量
        total_count_result = await db.execute(select(func.count(ImageCache.id)))
        total_count = total_count_result.scalar() or 0

        # 总大小
        total_size_result = await db.execute(select(func.sum(ImageCache.size_bytes)))
        total_size = total_size_result.scalar() or 0

        # 按来源类型统计
        source_stats_result = await db.execute(
            select(
                ImageCache.source_type,
                func.count(ImageCache.id).label("count"),
                func.sum(ImageCache.size_bytes).label("size"),
            ).group_by(ImageCache.source_type)
        )
        source_stats = {
            row.source_type or "unknown": {
                "count": row.count,
                "size_bytes": row.size or 0,
            }
            for row in source_stats_result.all()
        }

        # 磁盘实际占用（去重后）
        unique_files_result = await db.execute(
            select(
                func.count(func.distinct(ImageCache.file_hash)).label("count"),
            )
        )
        unique_file_count = unique_files_result.scalar() or 0

        return {
            "total_count": total_count,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "unique_file_count": unique_file_count,
            "source_stats": source_stats,
            "cache_directory": str(ImageCacheService._get_cache_root().absolute()),
        }

    @staticmethod
    async def clean_cache(
        db: AsyncSession,
        mode: str = "expired",
        keep_days: int = 30,
        keep_size_mb: int = 1000,
    ) -> dict:
        """
        清理缓存

        Args:
            db: 数据库会话
            mode: 清理模式
                - "expired": 清理过期缓存（根据keep_days）
                - "oldest": 保留最近访问的，删除超出keep_size_mb的
                - "unused": 清理长期未访问的（根据keep_days）
                - "all": 清理全部缓存
            keep_days: 保留最近N天的缓存
            keep_size_mb: 保留最多N MB的缓存

        Returns:
            清理结果统计
        """
        deleted_count = 0
        deleted_size = 0
        deleted_files = []

        if mode == "all":
            # 删除全部缓存
            all_caches_result = await db.execute(select(ImageCache))
            all_caches = all_caches_result.scalars().all()

            for cache in all_caches:
                file_path = ImageCacheService.get_file_path(cache)
                if file_path.exists():
                    deleted_size += cache.size_bytes
                    try:
                        file_path.unlink()
                        deleted_files.append(str(file_path))
                    except Exception:
                        pass
                deleted_count += 1

            await db.execute(delete(ImageCache))
            await db.commit()

        elif mode == "expired" or mode == "unused":
            # 清理过期或长期未访问的缓存
            from datetime import timedelta
            cutoff_date = tz_now() - timedelta(days=keep_days)

            if mode == "expired":
                query = select(ImageCache).where(ImageCache.created_at < cutoff_date)
            else:  # unused
                query = select(ImageCache).where(ImageCache.last_accessed_at < cutoff_date)

            old_caches_result = await db.execute(query)
            old_caches = old_caches_result.scalars().all()

            for cache in old_caches:
                # 检查是否有其他记录引用同一文件
                same_file_count_result = await db.execute(
                    select(func.count(ImageCache.id)).where(
                        ImageCache.local_path == cache.local_path
                    )
                )
                same_file_count = same_file_count_result.scalar() or 0

                if same_file_count <= 1:
                    # 只有这一个记录引用此文件，可以删除文件
                    file_path = ImageCacheService.get_file_path(cache)
                    if file_path.exists():
                        deleted_size += cache.size_bytes
                        try:
                            file_path.unlink()
                            deleted_files.append(str(file_path))
                        except Exception:
                            pass

                await db.delete(cache)
                deleted_count += 1

            await db.commit()

        elif mode == "oldest":
            # 保留最近访问的，删除超出大小限制的
            keep_size_bytes = keep_size_mb * 1024 * 1024

            # 按最后访问时间倒序排列
            all_caches_result = await db.execute(
                select(ImageCache).order_by(ImageCache.last_accessed_at.desc())
            )
            all_caches = all_caches_result.scalars().all()

            current_size = 0
            for cache in all_caches:
                if current_size + cache.size_bytes <= keep_size_bytes:
                    current_size += cache.size_bytes
                else:
                    # 超出大小限制，删除
                    same_file_count_result = await db.execute(
                        select(func.count(ImageCache.id)).where(
                            ImageCache.local_path == cache.local_path
                        )
                    )
                    same_file_count = same_file_count_result.scalar() or 0

                    if same_file_count <= 1:
                        file_path = ImageCacheService.get_file_path(cache)
                        if file_path.exists():
                            deleted_size += cache.size_bytes
                            try:
                                file_path.unlink()
                                deleted_files.append(str(file_path))
                            except Exception:
                                pass

                    await db.delete(cache)
                    deleted_count += 1

            await db.commit()

        # 清理空目录
        ImageCacheService._cleanup_empty_directories()

        return {
            "mode": mode,
            "deleted_count": deleted_count,
            "deleted_size_bytes": deleted_size,
            "deleted_size_mb": round(deleted_size / (1024 * 1024), 2),
            "deleted_files": len(deleted_files),
        }

    @staticmethod
    def _cleanup_empty_directories() -> None:
        """清理空目录"""
        cache_root = ImageCacheService._get_cache_root()
        if not cache_root.exists():
            return

        # 从最深层开始清理空目录
        for dirpath, dirnames, filenames in os.walk(cache_root, topdown=False):
            if dirpath != str(cache_root) and not os.listdir(dirpath):
                try:
                    os.rmdir(dirpath)
                except Exception:
                    pass

    @staticmethod
    async def delete_single_cache(db: AsyncSession, cache_id: int) -> bool:
        """
        删除单个缓存记录

        Args:
            db: 数据库会话
            cache_id: 缓存ID

        Returns:
            是否成功删除
        """
        result = await db.execute(
            select(ImageCache).where(ImageCache.id == cache_id)
        )
        cache = result.scalar_one_or_none()

        if not cache:
            return False

        # 检查是否有其他记录引用同一文件
        same_file_count_result = await db.execute(
            select(func.count(ImageCache.id)).where(
                ImageCache.local_path == cache.local_path
            )
        )
        same_file_count = same_file_count_result.scalar() or 0

        if same_file_count <= 1:
            # 只有这一个记录引用此文件，删除文件
            file_path = ImageCacheService.get_file_path(cache)
            if file_path.exists():
                try:
                    file_path.unlink()
                except Exception:
                    pass

        await db.delete(cache)
        await db.commit()

        return True
