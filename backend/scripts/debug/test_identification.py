# -*- coding: utf-8 -*-
"""
测试资源识别功能
"""
import asyncio
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.models import Base, UnifiedMovie, ResourceMapping, PTResource
from app.adapters.metadata import DoubanAdapter
from app.services.identification.resource_identify_service import ResourceIdentificationService

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 数据库URL（使用测试数据库）
DATABASE_URL = "sqlite+aiosqlite:///./data/nasfusion.db"


async def test_douban_adapter():
    """测试豆瓣API适配器"""
    logger.info("=" * 50)
    logger.info("测试豆瓣API适配器")
    logger.info("=" * 50)

    # 从数据库获取第一个PT站点的API Key
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session_local = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session_local() as db:
        from app.models.pt_site import PTSite
        from app.utils.encryption import encryption_util
        from sqlalchemy import select

        # 获取第一个站点
        query = select(PTSite).limit(1)
        result = await db.execute(query)
        site = result.scalar_one_or_none()

        if not site:
            logger.warning("未找到PT站点配置，跳过豆瓣API测试")
            logger.info("提示：请先配置PT站点（MTeam），并填写x-api-key")
            await engine.dispose()
            return False

        if not site.auth_passkey:
            logger.warning(f"站点 {site.name} 未配置auth_passkey（x-api-key），跳过测试")
            await engine.dispose()
            return False

        # 解密API Key
        try:
            api_key = encryption_util.decrypt(site.auth_passkey)
        except Exception:
            # 可能是未加密的
            api_key = site.auth_passkey

        logger.info(f"使用站点: {site.name}")
        logger.info(f"API Base URL: {site.base_url}")

    await engine.dispose()

    # 创建适配器（使用站点配置）
    adapter = DoubanAdapter({
        "api_key": api_key,
        "api_base_url": site.base_url or "https://api.m-team.cc",
        "proxy_config": site.proxy_config,
    })

    # 测试URL
    test_url = "https://movie.douban.com/subject/25954475/"  # 聚焦

    try:
        metadata = await adapter.get_by_url(test_url)
        logger.info(f"成功获取元数据:")
        logger.info(f"  标题: {metadata.get('title')}")
        logger.info(f"  原始标题: {metadata.get('original_title')}")
        logger.info(f"  豆瓣ID: {metadata.get('douban_id')}")
        logger.info(f"  IMDB ID: {metadata.get('imdb_id')}")
        logger.info(f"  年份: {metadata.get('year')}")
        logger.info(f"  评分: {metadata.get('rating_douban')}")
        logger.info(f"  类型: {metadata.get('genres')}")
        logger.info(f"  导演: {len(metadata.get('directors', []))} 位")
        logger.info(f"  演员: {len(metadata.get('actors', []))} 位")
        return True
    except Exception as e:
        logger.error(f"豆瓣API测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_database_tables():
    """测试数据库表创建"""
    logger.info("=" * 50)
    logger.info("测试数据库表创建")
    logger.info("=" * 50)

    engine = create_async_engine(DATABASE_URL, echo=False)

    try:
        # 创建表
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all, checkfirst=True)

        logger.info("数据库表创建成功")

        # 检查表是否存在
        async with engine.connect() as conn:
            from sqlalchemy import text

            # 检查unified_movies表
            result = await conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='unified_movies'"
            ))
            if result.fetchone():
                logger.info("✓ unified_movies 表已创建")
            else:
                logger.error("✗ unified_movies 表不存在")

            # 检查resource_mappings表
            result = await conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='resource_mappings'"
            ))
            if result.fetchone():
                logger.info("✓ resource_mappings 表已创建")
            else:
                logger.error("✗ resource_mappings 表不存在")

        await engine.dispose()
        return True

    except Exception as e:
        logger.error(f"数据库表创建失败: {str(e)}")
        await engine.dispose()
        return False


async def test_identification_flow():
    """测试完整识别流程"""
    logger.info("=" * 50)
    logger.info("测试完整识别流程")
    logger.info("=" * 50)

    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session_local = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session_local() as db:
        try:
            # 查找一个有douban_id的PT资源
            from sqlalchemy import select

            query = select(PTResource).where(PTResource.douban_id.isnot(None)).limit(1)
            result = await db.execute(query)
            pt_resource = result.scalar_one_or_none()

            if not pt_resource:
                logger.warning("未找到有豆瓣ID的PT资源，跳过识别测试")
                logger.info("提示：请先同步PT资源，并确保资源包含douban_id")
                return False

            logger.info(f"找到测试资源: {pt_resource.title} (ID: {pt_resource.id})")
            logger.info(f"豆瓣ID: {pt_resource.douban_id}")

            # 执行识别
            mapping = await ResourceIdentificationService.identify_movie(
                db=db,
                pt_resource_id=pt_resource.id,
                force=True,  # 强制重新识别
            )

            logger.info("识别成功！")
            logger.info(f"  映射ID: {mapping.id}")
            logger.info(f"  PT资源ID: {mapping.pt_resource_id}")
            logger.info(f"  电影ID: {mapping.unified_movie_id}")
            logger.info(f"  匹配方式: {mapping.match_method}")
            logger.info(f"  匹配置信度: {mapping.match_confidence}")

            # 查询统一电影资源
            from app.services.identification.unified_movie_service import UnifiedMovieService

            movie = await UnifiedMovieService.get_by_id(db, mapping.unified_movie_id)
            if movie:
                logger.info(f"\n统一电影资源:")
                logger.info(f"  标题: {movie.title}")
                logger.info(f"  原始标题: {movie.original_title}")
                logger.info(f"  年份: {movie.year}")
                logger.info(f"  评分: {movie.rating_douban}")
                logger.info(f"  PT资源数量: {movie.pt_resource_count}")
                logger.info(f"  有免费资源: {movie.has_free_resource}")

            return True

        except Exception as e:
            logger.error(f"识别流程测试失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    await engine.dispose()


async def main():
    """主测试函数"""
    print("\n" + "=" * 70)
    print("PT资源识别功能测试")
    print("=" * 70 + "\n")

    results = {
        "豆瓣API适配器": False,
        "数据库表创建": False,
        "完整识别流程": False,
    }

    # 1. 测试豆瓣API
    results["豆瓣API适配器"] = await test_douban_adapter()
    print()

    # 2. 测试数据库表创建
    results["数据库表创建"] = await test_database_tables()
    print()

    # 3. 测试完整识别流程
    results["完整识别流程"] = await test_identification_flow()
    print()

    # 打印测试结果
    print("\n" + "=" * 70)
    print("测试结果汇总")
    print("=" * 70)

    for test_name, passed in results.items():
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"{test_name}: {status}")

    all_passed = all(results.values())
    print()
    if all_passed:
        print("✓ 所有测试通过！")
    else:
        print("✗ 部分测试失败，请查看上方日志")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
