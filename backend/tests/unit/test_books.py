"""电子书解析、缓存修复及分页过滤回归测试。"""
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.adapters.pt_sites.mteam import MTeamAdapter
from app.api.v1.pt_resource_details import get_pt_resource_details
from app.models.pt_resource import PTResource
from app.services.pt.pt_resource_service import PTResourceService


def book_item(**overrides):
    return {
        "id": "1194301", "name": "langqiaoyimeng", "smallDescr": "廊桥遗梦",
        "category": "427", "douban": "https://book.douban.com/subject/26815762/",
        "doubanRating": "8.9", "size": "395167", "numfiles": "1",
        "createdDate": "2026-06-13 19:46:18",
        "status": {"seeders": "41", "leechers": "0", "timesCompleted": "250"},
        "imageList": ["https://example.org/book.jpg"], **overrides,
    }


@pytest.mark.parametrize("mapping", [None, {}, {"401": "movie"}])
def test_mteam_book_without_synced_categories(mapping):
    adapter = MTeamAdapter({"base_url": "https://api.m-team.io"})
    adapter.category_map = mapping
    book = adapter._parse_resource_item(book_item())
    assert book["category"] == "book"
    assert book["douban_id"] == "26815762"
    assert book["douban_rating"] == 8.9
    assert book["seeders"] == 41
    assert book["size_bytes"] == 395167
    assert book["published_at"].utcoffset().total_seconds() == 8 * 3600
    assert adapter._parse_resource_item(book_item(imageList=None))["image_list"] == []


@pytest.mark.asyncio
async def test_mteam_book_search_request(monkeypatch):
    adapter = MTeamAdapter({"base_url": "https://api.m-team.io"})
    async def fake_request(endpoint, method, json_data):
        assert endpoint == "/api/torrent/search"
        assert method == "POST"
        assert json_data["categories"] == ["427"]
        assert json_data["mode"] == "normal"
        assert json_data["pageNumber"] == 2
        return {"data": {"pageNumber": "2", "pageSize": "100", "total": "6547", "totalPages": "66", "data": [book_item()]}}
    monkeypatch.setattr(adapter, "_make_request", fake_request)
    result = await adapter.fetch_resources(page=2, limit=100, categories=["427"])
    assert result["total_pages"] == 66
    assert result["resources"][0]["category"] == "book"


@pytest.mark.asyncio
async def test_book_cache_repair_and_filtered_pagination():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        async with engine.begin() as connection:
            await connection.run_sync(PTResource.__table__.create)
        async with async_sessionmaker(engine, expire_on_commit=False)() as db:
            adapter = MTeamAdapter({})
            data = adapter._parse_resource_item(book_item()) | {"site_id": 1}
            db.add(PTResource(**(data | {"category": "other", "image_list": [], "raw_page_json": {}})))
            await db.commit()
            assert await PTResourceService.batch_upsert_resources(db, [data]) == (0, 1)
            for i in range(4):
                db.add(PTResource(**(data | {"torrent_id": str(i), "title": "100% ebook", "subtitle": "其他书籍", "is_free": True})))
            db.add(PTResource(**(data | {"torrent_id": "movie", "category": "movie", "is_free": True})))
            db.add(PTResource(**(data | {"torrent_id": "hidden", "is_active": False})))
            await db.commit()

            async def listing(**overrides):
                return await get_pt_resource_details(**({"category": "book", "site_id": 1, "original_category_id": None, "keyword": None, "is_free": None, "page": 1, "page_size": 2, "db": db} | overrides))
            result = await listing(keyword="廊桥")
            assert result.total == 1
            assert result.items[0].poster_url == "https://example.org/book.jpg"
            assert result.items[0].douban_rating == 8.9
            assert (await listing(keyword="%", is_free=True)).total == 4
            first = await listing(is_free=True)
            second = await listing(is_free=True, page=2)
            assert first.total == second.total == 4
            assert not {item.id for item in first.items} & {item.id for item in second.items}
            assert (await listing(site_id=2)).total == 0
    finally:
        await engine.dispose()
