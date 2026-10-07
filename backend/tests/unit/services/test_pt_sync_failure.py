"""同步中断时保留已提交页面，并把原始错误传递给任务调度器。"""
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy import event, func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models import Base
from app.models.pt_resource import PTResource
from app.models.pt_site import PTSite
from app.models.sync_log import SyncLog
from app.services.pt.pt_resource_service import PTResourceService
from app.services.task.task_execution_service import TaskExecutionService
from app.tasks.handlers.pt_resource_sync_handler import PTResourceSyncHandler
from app.events.bus import event_bus


def resource(torrent_id, **overrides):
    return {
        "torrent_id": torrent_id, "title": torrent_id, "size_bytes": 1,
        "download_url": f"https://test.invalid/download/{torrent_id}", **overrides,
    }


@pytest_asyncio.fixture
async def sync_db(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{(tmp_path / 'sync.db').as_posix()}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    async with sessions() as db:
        site = PTSite(
            name="test site", type="mteam", domain="test.invalid",
            base_url="https://test.invalid", auth_type="cookie", request_interval=0,
        )
        db.add(site)
        await db.flush()
        site_id = site.id
        db.add(PTResource(
            site_id=site_id, **resource("existing", seeders=1),
        ))
        await db.commit()
    yield engine, sessions, site_id
    await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["flush", "fetch"])
@pytest.mark.parametrize("logging_failure", [False, True])
async def test_failed_page_propagates_original_error_and_keeps_committed_page(
    sync_db, monkeypatch, failure, logging_failure,
):
    engine, sessions, site_id = sync_db
    original_error = RuntimeError("index corrupted" if failure == "flush" else "site unavailable")
    first_page = {
        "resources": [
            resource(str(i))
            for i in range(100)
        ],
        "total_pages": 5,
    }
    second_page = {"resources": [
        resource("existing", seeders=2),
    ]}
    adapter = AsyncMock()
    adapter.fetch_resources.side_effect = [
        first_page, original_error if failure == "fetch" else second_page,
    ]
    monkeypatch.setattr(PTResourceService, "_get_site_adapter", AsyncMock(return_value=adapter))
    progress = AsyncMock()
    monkeypatch.setattr(TaskExecutionService, "update_progress", progress)
    monkeypatch.setattr(TaskExecutionService, "append_log", AsyncMock())
    publish = AsyncMock()
    monkeypatch.setattr(event_bus, "publish", publish)

    def fail_sql(conn, cursor, statement, parameters, context, executemany):
        if failure == "flush" and statement.startswith("UPDATE pt_resources SET"):
            # 在真实 ORM flush 中抛错，让 Session 进入待回滚状态。
            raise original_error
        if logging_failure and statement.startswith("UPDATE sync_logs SET"):
            raise RuntimeError("failure log unavailable")

    event.listen(engine.sync_engine, "before_cursor_execute", fail_sql)
    try:
        async with sessions() as db:
            with pytest.raises(RuntimeError) as caught:
                await PTResourceSyncHandler.execute(
                    db, {"site_id": site_id, "max_pages": 5}, execution_id=123,
                )
            assert caught.value is original_error
            assert db.is_active
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", fail_sql)

    assert adapter.fetch_resources.await_count == 2
    publish.assert_not_awaited()
    assert [call.args[2] for call in progress.await_args_list] == [5, 18]
    assert progress.await_args_list[-1].kwargs["progress_detail"]["pages_processed"] == 1
    async with sessions() as db:
        assert await db.scalar(select(func.count()).select_from(PTResource)) == 101
        existing = await db.scalar(select(PTResource).where(PTResource.torrent_id == "existing"))
        assert existing.seeders == 1
        sync_log = await db.scalar(select(SyncLog))
        site = await db.get(PTSite, site_id)
        if logging_failure:
            assert sync_log.status == "running"
        else:
            assert sync_log.status == "failed"
            assert sync_log.error_message == str(original_error)
            assert sync_log.completed_at is not None
            assert site.last_sync_status == "failed"
            assert site.last_sync_error == str(original_error)


@pytest.mark.asyncio
async def test_successful_sync_still_commits_resources_and_statistics(sync_db, monkeypatch):
    _, sessions, site_id = sync_db
    adapter = AsyncMock()
    adapter.fetch_resources.return_value = {"resources": [
        resource("existing", seeders=2),
        resource("new"),
    ]}
    monkeypatch.setattr(PTResourceService, "_get_site_adapter", AsyncMock(return_value=adapter))
    async with sessions() as db:
        sync_log = await PTResourceService.sync_site_resources(db, site_id, max_pages=5)
        assert sync_log.status == "success"
        assert sync_log.resources_new == 1
        assert sync_log.resources_updated == 1
        assert sync_log.pages_processed == 1
        assert (await db.get(PTSite, site_id)).total_synced == 2
