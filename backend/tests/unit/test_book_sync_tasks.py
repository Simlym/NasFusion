from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.task.scheduled_task_service import ScheduledTaskService
from app.tasks.handlers.pt_resource_sync_handler import PTResourceSyncHandler


@pytest.mark.asyncio
async def test_book_sync_creates_full_manual_task(monkeypatch):
    db = SimpleNamespace(get=AsyncMock(return_value=SimpleNamespace(type="mteam", name="MTeam")))
    monkeypatch.setattr(ScheduledTaskService, "get_by_name", AsyncMock(return_value=None))
    create = AsyncMock(return_value=SimpleNamespace(id=42))
    monkeypatch.setattr(ScheduledTaskService, "create_pt_sync_task", create)
    task = await ScheduledTaskService.ensure_book_sync_task(db, 1)
    params = create.call_args.args[1]
    assert task.id == 42
    assert params.schedule_type == "manual"
    assert params.sync_type == "full"
    assert params.categories == ["427"]
    assert params.mode == "normal"
    assert params.keyword is None
    assert params.max_pages is None


@pytest.mark.asyncio
async def test_book_sync_reuses_schedule_without_overwriting(monkeypatch):
    task = SimpleNamespace(id=42, handler="pt_resource_sync", handler_params={"site_id": 1, "categories": ["427"], "mode": "normal"}, schedule_type="cron")
    db = SimpleNamespace(get=AsyncMock(return_value=SimpleNamespace(type="mteam")))
    monkeypatch.setattr(ScheduledTaskService, "get_by_name", AsyncMock(return_value=task))
    create = AsyncMock()
    monkeypatch.setattr(ScheduledTaskService, "create_pt_sync_task", create)
    assert await ScheduledTaskService.ensure_book_sync_task(db, 1) is task
    create.assert_not_awaited()
    assert task.schedule_type == "cron"


@pytest.mark.asyncio
async def test_book_sync_rejects_other_site(monkeypatch):
    db = SimpleNamespace(get=AsyncMock(return_value=SimpleNamespace(type="nexusphp")))
    with pytest.raises(ValueError, match="MTeam"):
        await ScheduledTaskService.ensure_book_sync_task(db, 1)


@pytest.mark.asyncio
async def test_failed_pt_sync_fails_execution(monkeypatch):
    from app.services.pt.pt_resource_service import PTResourceService
    from app.services.task.task_execution_service import TaskExecutionService
    monkeypatch.setattr(TaskExecutionService, "append_log", AsyncMock())
    monkeypatch.setattr(PTResourceService, "sync_site_resources", AsyncMock(return_value=SimpleNamespace(status="failed", error_message="站点连接失败")))
    with pytest.raises(ValueError, match="站点连接失败"):
        await PTResourceSyncHandler.execute(None, {"site_id": 1, "mode": "normal", "categories": ["427"]}, 42)
