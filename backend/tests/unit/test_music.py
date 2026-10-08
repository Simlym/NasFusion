from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.adapters.pt_sites.mteam import MTeamAdapter
from app.schemas.pt_resource import SyncRequest
from app.schemas.scheduled_task import PTSyncTaskCreate
from app.tasks.handlers.pt_resource_sync_handler import PTResourceSyncHandler


def music_item(category="406"):
    return {
        "id": "1267054", "name": "Andy Lau Proud of You Concert Live 2002 DVDRip",
        "smallDescr": "刘德华2002你是我的骄傲演唱会", "category": category,
        "douban": "https://music.douban.com/subject/3593089/", "doubanRating": "8.6",
        "size": "2717992480", "numfiles": "1", "createdDate": "2026-10-08 21:14:25",
        "imageList": ["https://example.org/album.jpg"],
        "status": {"seeders": "14", "leechers": "0", "timesCompleted": "0", "discount": "PERCENT_50"},
    }


@pytest.mark.parametrize("category", ["406", "434"])
@pytest.mark.parametrize("mapping", [None, {}, {"401": "movie"}])
def test_music_category_without_site_mapping(category, mapping):
    adapter = MTeamAdapter({"base_url": "https://api.m-team.io"})
    adapter.category_map = mapping
    result = adapter._parse_resource_item(music_item(category))
    assert result["category"] == "music"
    assert result["douban_id"] == "3593089"
    assert result["douban_rating"] == 8.6
    assert result["seeders"] == 14
    assert result["is_discount"] is True
    assert result["size_bytes"] == 2717992480


def test_music_mode_accepted_in_manual_and_scheduled_sync():
    assert SyncRequest(mode="music", categories=[]).mode == "music"
    task = PTSyncTaskCreate(site_id=1, task_name="音乐同步", mode="music", categories=[])
    assert task.mode == "music"
    assert task.categories == []


@pytest.mark.asyncio
async def test_music_request_and_unknown_category_from_music_mode(monkeypatch):
    adapter = MTeamAdapter({"base_url": "https://api.m-team.io"})
    async def request(endpoint, method, json_data):
        assert endpoint == "/api/torrent/search"
        assert method == "POST"
        assert json_data == {"mode": "music", "visible": 1, "categories": [], "pageNumber": 1, "pageSize": 100}
        return {"data": {"pageNumber": "1", "pageSize": "100", "total": "10000", "totalPages": "100", "data": [music_item("999")]}}
    monkeypatch.setattr(adapter, "_make_request", request)
    result = await adapter.fetch_resources(mode="music", limit=100)
    assert result["resources"][0]["category"] == "music"
    assert result["total_pages"] == 100


@pytest.mark.asyncio
async def test_music_mode_reaches_existing_sync_handler(monkeypatch):
    from app.services.pt.pt_resource_service import PTResourceService
    from app.services.task.task_execution_service import TaskExecutionService
    monkeypatch.setattr(TaskExecutionService, "append_log", AsyncMock())
    monkeypatch.setattr(TaskExecutionService, "update_progress", AsyncMock())
    sync = AsyncMock(return_value=SimpleNamespace(status="success", pages_processed=1, resources_found=2, resources_new=2, resources_updated=0, resources_error=0, id=12))
    monkeypatch.setattr(PTResourceService, "sync_site_resources", sync)
    result = await PTResourceSyncHandler.execute(SimpleNamespace(get=AsyncMock(return_value=None)), {"site_id": 1, "mode": "music", "categories": []}, 42)
    assert sync.call_args.kwargs["filters"] == {"mode": "music"}
    assert result["resources_new"] == 2
