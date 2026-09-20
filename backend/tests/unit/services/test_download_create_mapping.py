from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.tasks.handlers.download_create_handler import DownloadCreateHandler
from app.services.download.download_task_service import DownloadTaskService


@pytest.mark.asyncio
async def test_resolve_unified_mapping_keeps_explicit_values():
    db = AsyncMock()

    result = await DownloadCreateHandler._resolve_unified_mapping(
        db,
        pt_resource_id=244007,
        unified_table_name="unified_tv_series",
        unified_resource_id=123,
    )

    assert result == ("unified_tv_series", 123)
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_resolve_unified_mapping_uses_pt_resource_mapping():
    mapping = SimpleNamespace(
        unified_table_name="unified_tv_series",
        unified_resource_id=456,
    )
    query_result = Mock()
    query_result.scalar_one_or_none.return_value = mapping
    db = AsyncMock()
    db.execute.return_value = query_result

    result = await DownloadCreateHandler._resolve_unified_mapping(
        db,
        pt_resource_id=244007,
        unified_table_name=None,
        unified_resource_id=None,
    )

    assert result == ("unified_tv_series", 456)
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_resolve_unified_mapping_leaves_unidentified_resource_empty():
    query_result = Mock()
    query_result.scalar_one_or_none.return_value = None
    db = AsyncMock()
    db.execute.return_value = query_result

    result = await DownloadCreateHandler._resolve_unified_mapping(
        db,
        pt_resource_id=244007,
        unified_table_name=None,
        unified_resource_id=None,
    )

    assert result == (None, None)


@pytest.mark.asyncio
async def test_backfill_unified_mapping_repairs_existing_media_files():
    mapping = SimpleNamespace(
        unified_table_name="unified_tv_series",
        unified_resource_id=456,
    )
    media_file = SimpleNamespace(
        unified_table_name=None,
        unified_resource_id=None,
        match_method="from_download",
        match_confidence=None,
        status="discovered",
    )
    mapping_result = Mock()
    mapping_result.scalar_one_or_none.return_value = mapping
    files_result = Mock()
    files_result.scalars.return_value.all.return_value = [media_file]
    db = AsyncMock()
    db.execute.side_effect = [mapping_result, files_result]
    task = SimpleNamespace(
        id=232,
        pt_resource_id=244007,
        unified_table_name=None,
        unified_resource_id=None,
    )

    repaired = await DownloadTaskService._backfill_unified_mapping(db, task)

    assert repaired is True
    assert (task.unified_table_name, task.unified_resource_id) == (
        "unified_tv_series",
        456,
    )
    assert (media_file.unified_table_name, media_file.unified_resource_id) == (
        "unified_tv_series",
        456,
    )
    assert media_file.status == "identified"
    assert media_file.match_confidence == 95
