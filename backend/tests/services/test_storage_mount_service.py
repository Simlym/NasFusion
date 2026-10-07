import os
from unittest.mock import AsyncMock, MagicMock

import pytest


os.environ.setdefault(
    "SECRET_KEY", "test_secret_key_must_be_at_least_32_bytes_long_for_security"
)

from app.models.storage_mount import StorageMount
from app.services.storage.storage_mount_service import StorageMountService


@pytest.mark.asyncio
async def test_delete_mount_clears_references_before_delete():
    db = AsyncMock()
    mount = StorageMount(id=6, name="downloads", mount_type="download")
    result = MagicMock()
    result.scalar_one_or_none.return_value = mount
    db.execute.return_value = result

    deleted = await StorageMountService.delete_mount(db, mount.id)

    assert deleted is True
    statements = [call.args[0] for call in db.execute.await_args_list]
    assert len(statements) == 3
    assert statements[1].table.name == "download_tasks"
    assert statements[2].table.name == "subscriptions"
    assert statements[1].compile().params["storage_mount_id"] is None
    assert statements[2].compile().params["storage_mount_id"] is None
    db.delete.assert_awaited_once_with(mount)
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_mount_returns_false_when_missing():
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db.execute.return_value = result

    deleted = await StorageMountService.delete_mount(db, 999)

    assert deleted is False
    db.delete.assert_not_awaited()
    db.commit.assert_not_awaited()
