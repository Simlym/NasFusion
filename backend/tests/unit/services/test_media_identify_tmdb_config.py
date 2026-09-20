from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.services.identification.media_identify_service import MediaIdentifyService


@pytest.mark.asyncio
async def test_tmdb_adapter_uses_proxy_and_interactive_timeouts():
    settings = {
        "tmdb_api_key": SimpleNamespace(value="test-key"),
        "tmdb_language": SimpleNamespace(value="zh-CN"),
        "tmdb_proxy": SimpleNamespace(value="http://proxy:7890"),
    }

    async def get_setting(_db, _category, key):
        return settings.get(key)

    service = MediaIdentifyService()
    with (
        patch(
            "app.services.identification.media_identify_service.SystemSettingService.get_by_key",
            new=AsyncMock(side_effect=get_setting),
        ),
        patch("app.services.identification.media_identify_service.TMDBAdapter") as adapter_cls,
    ):
        await service._get_tmdb_adapter(AsyncMock())

    adapter_cls.assert_called_once_with({
        "api_key": "test-key",
        "language": "zh-CN",
        "proxy_config": {
            "enabled": True,
            "url": "http://proxy:7890",
        },
        "timeout": 20,
        "max_retries": 2,
    })


@pytest.mark.asyncio
async def test_tmdb_adapter_reloads_changed_proxy_configuration():
    proxy_setting = SimpleNamespace(value="http://proxy-one:7890")
    settings = {
        "tmdb_api_key": SimpleNamespace(value="test-key"),
        "tmdb_language": None,
        "tmdb_proxy": proxy_setting,
    }

    async def get_setting(_db, _category, key):
        return settings.get(key)

    service = MediaIdentifyService()
    with (
        patch(
            "app.services.identification.media_identify_service.SystemSettingService.get_by_key",
            new=AsyncMock(side_effect=get_setting),
        ),
        patch("app.services.identification.media_identify_service.TMDBAdapter") as adapter_cls,
    ):
        await service._get_tmdb_adapter(AsyncMock())
        proxy_setting.value = "http://proxy-two:7890"
        await service._get_tmdb_adapter(AsyncMock())

    assert adapter_cls.call_count == 2
    assert adapter_cls.call_args_list[1].args[0]["proxy_config"]["url"] == (
        "http://proxy-two:7890"
    )


@pytest.mark.asyncio
async def test_identify_from_download_task_uses_explicit_async_lookup_and_repairs_file():
    service = MediaIdentifyService()
    task = SimpleNamespace(
        unified_table_name="unified_tv_series",
        unified_resource_id=456,
    )
    media_file = SimpleNamespace(
        download_task_id=232,
        unified_table_name=None,
        unified_resource_id=None,
        match_method="none",
        match_confidence=None,
        status="discovered",
    )
    db = AsyncMock()
    db.get.return_value = task

    result = await service._identify_from_download_task(db, media_file)

    db.get.assert_awaited_once()
    db.commit.assert_awaited_once()
    assert result["success"] is True
    assert result["match_source"] == "download_task"
    assert media_file.unified_table_name == "unified_tv_series"
    assert media_file.unified_resource_id == 456
    assert media_file.status == "identified"
    assert media_file.match_confidence == 95
