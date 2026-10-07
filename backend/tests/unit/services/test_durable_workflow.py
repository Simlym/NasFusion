"""使用临时 SQLite 文件模拟关闭连接、重启、事务回滚和重复投递。"""
import asyncio
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.constants.durable_event import EVENT_DELIVERED, EVENT_PENDING
from app.constants.task import (
    EXECUTION_STATUS_CANCELLED, EXECUTION_STATUS_COMPLETED, EXECUTION_STATUS_FAILED,
    EXECUTION_STATUS_PENDING, EXECUTION_STATUS_RUNNING,
    TASK_TYPE_DOWNLOAD_CREATE, TASK_TYPE_MEDIA_FILE_AUTO_ORGANIZE,
    TASK_TYPE_MEDIA_SERVER_LIBRARY_REFRESH, TASK_TYPE_PT_RESOURCE_IDENTIFY,
    TASK_TYPE_SUBSCRIPTION_CHECK,
)
from app.core.init import cleanup_stuck_tasks
from app.models import Base, DownloadTask, TaskExecution, WorkflowEvent
from app.services.task.task_execution_service import TaskExecutionService
from app.services.task.workflow_event_service import WorkflowEventService
from app.services.mediafile.media_organizer_service import MediaOrganizerService
from app.utils.timezone import now


@pytest_asyncio.fixture
async def sessions(tmp_path):
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{(tmp_path / 'restart.db').as_posix()}", poolclass=NullPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    await engine.dispose()


async def download(db, **overrides):
    values = dict(
        task_hash="test-torrent", pt_resource_id=1, downloader_config_id=1,
        media_type="movie", client_type="qbittorrent", torrent_name="test.mkv",
        save_path="/downloads", total_size=100, progress=100, status="completed",
        auto_organize=True, completed_at=now(),
    )
    values.update(overrides)
    task = DownloadTask(**values)
    db.add(task)
    await db.flush()
    return task


def execution(**overrides):
    values = dict(
        task_type=TASK_TYPE_MEDIA_FILE_AUTO_ORGANIZE,
        task_name="test organize", handler=TASK_TYPE_MEDIA_FILE_AUTO_ORGANIZE,
        handler_params={"download_task_id": 1}, status=EXECUTION_STATUS_PENDING,
    )
    values.update(overrides)
    return TaskExecution(**values)


@pytest.mark.asyncio
async def test_download_and_outbox_rollback_together(sessions):
    async with sessions() as db:
        task = await download(db, completed_at=None, progress=50, status="downloading")
        await db.commit()
        task.completed_at = now()
        task.progress = 100
        await WorkflowEventService.enqueue_download(db, task)
        await db.rollback()  # 在事务提交前断电
    async with sessions() as db:
        assert (await db.get(DownloadTask, 1)).completed_at is None
        assert await db.scalar(select(func.count()).select_from(WorkflowEvent)) == 0


@pytest.mark.asyncio
async def test_restart_replays_once_and_keeps_dedup_after_history_cleanup(sessions):
    async with sessions() as db:
        task = await download(db)
        await WorkflowEventService.enqueue_download(db, task)
        await WorkflowEventService.enqueue_download(db, task)
        await db.commit()  # 模拟进程在内存事件发布前退出
    await WorkflowEventService.deliver_pending(sessions)
    await WorkflowEventService.deliver_pending(sessions)
    async with sessions() as db:
        await db.execute(text("PRAGMA foreign_keys = ON"))
        assert await db.scalar(select(func.count()).select_from(TaskExecution)) == 1
        event = await db.scalar(select(WorkflowEvent))
        assert event.status == EVENT_DELIVERED
        assert event.execution_id is not None
        # 模拟任务历史被清理，outbox 的业务凭据依然存在。
        await db.execute(delete(TaskExecution))
        await db.commit()
        await db.refresh(event)
        assert event.execution_id is None
        assert await WorkflowEventService.backfill_completed(db) == 0
    await WorkflowEventService.deliver_pending(sessions)
    async with sessions() as db:
        assert await db.scalar(select(func.count()).select_from(TaskExecution)) == 0


@pytest.mark.asyncio
async def test_delivery_rolls_back_execution_and_ack_on_crash(sessions, monkeypatch):
    async with sessions() as db:
        task = await download(db)
        await WorkflowEventService.enqueue_download(db, task)
        await db.commit()
    async with sessions() as db:
        monkeypatch.setattr(db, "commit", AsyncMock(side_effect=RuntimeError("power loss")))
        with pytest.raises(RuntimeError):
            await WorkflowEventService.deliver(db, 1)
    async with sessions() as db:
        assert (await db.get(WorkflowEvent, 1)).status == EVENT_PENDING
        assert await db.scalar(select(func.count()).select_from(TaskExecution)) == 0
    await WorkflowEventService.deliver_pending(sessions)
    async with sessions() as db:
        assert await db.scalar(select(func.count()).select_from(TaskExecution)) == 1


@pytest.mark.asyncio
async def test_two_consumers_cannot_deliver_same_event(sessions):
    async with sessions() as db:
        await WorkflowEventService.enqueue_download(db, await download(db))
        await db.commit()

    async def consume():
        async with sessions() as db:
            await WorkflowEventService.deliver(db, 1)

    await asyncio.gather(consume(), consume())
    async with sessions() as db:
        assert await db.scalar(select(func.count()).select_from(TaskExecution)) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [EXECUTION_STATUS_COMPLETED, EXECUTION_STATUS_CANCELLED])
async def test_backfill_adopts_existing_history_without_redo(sessions, status):
    async with sessions() as db:
        await download(db)
        old = execution(status=status)
        db.add(old)
        await db.commit()
        assert await WorkflowEventService.backfill_completed(db) == 1
    await WorkflowEventService.deliver_pending(sessions)
    async with sessions() as db:
        event = await db.get(WorkflowEvent, 1)
        assert event.execution_id == old.id
        assert (await db.get(TaskExecution, old.id)).status == status
        assert await db.scalar(select(func.count()).select_from(TaskExecution)) == 1


@pytest.mark.asyncio
async def test_startup_preserves_pending_and_only_resumes_safe_work(sessions):
    async with sessions() as db:
        pending = execution(task_type=TASK_TYPE_DOWNLOAD_CREATE, retry_count=2,
                            next_retry_at=now() + timedelta(minutes=2))
        running = execution(status=EXECUTION_STATUS_RUNNING, retry_count=1)
        legacy = execution(status=EXECUTION_STATUS_FAILED, error_message="系统重启，任务被中断")
        unsafe = execution(task_type=TASK_TYPE_DOWNLOAD_CREATE, status=EXECUTION_STATUS_RUNNING)
        cancelled = execution(status=EXECUTION_STATUS_CANCELLED)
        db.add_all([pending, running, legacy, unsafe, cancelled])
        await db.commit()
        ids = [item.id for item in [pending, running, legacy, unsafe, cancelled]]
        await cleanup_stuck_tasks(db)
    async with sessions() as db:
        items = [await db.get(TaskExecution, item_id) for item_id in ids]
        assert [item.status for item in items] == [
            EXECUTION_STATUS_PENDING, EXECUTION_STATUS_PENDING, EXECUTION_STATUS_PENDING,
            EXECUTION_STATUS_FAILED, EXECUTION_STATUS_CANCELLED,
        ]
        assert items[0].retry_count == 2 and items[0].next_retry_at is not None
        assert items[1].retry_count == 1


@pytest.mark.asyncio
async def test_atomic_claim_and_retry_deadline(sessions):
    async with sessions() as db:
        item = execution()
        db.add(item)
        await db.commit()

    async def claim():
        async with sessions() as db:
            return await TaskExecutionService.start_execution(db, item.id) is not None

    assert sorted(await asyncio.gather(claim(), claim())) == [False, True]
    async with sessions() as db:
        await TaskExecutionService.fail_execution(db, item.id, "storage offline")
        assert await TaskExecutionService.start_execution(db, item.id) is None
        item = await db.get(TaskExecution, item.id)
        item.next_retry_at = now() - timedelta(seconds=1)
        await db.commit()
        assert await TaskExecutionService.start_execution(db, item.id) is not None


@pytest.mark.asyncio
async def test_outbox_failure_is_recorded_and_retried(sessions, monkeypatch):
    async with sessions() as db:
        await WorkflowEventService.enqueue_download(db, await download(db))
        await db.commit()
    with monkeypatch.context() as patch:
        patch.setattr(WorkflowEventService, "deliver", AsyncMock(side_effect=RuntimeError("unavailable")))
        await WorkflowEventService.deliver_pending(sessions)
    async with sessions() as db:
        event = await db.get(WorkflowEvent, 1)
        assert event.status == EVENT_PENDING and event.attempts == 1
        assert event.last_error == "unavailable"
        event.next_attempt_at = now() - timedelta(seconds=1)
        await db.commit()
    await WorkflowEventService.deliver_pending(sessions)
    async with sessions() as db:
        assert (await db.get(WorkflowEvent, 1)).status == EVENT_DELIVERED


@pytest.mark.asyncio
async def test_site_sync_without_new_resources_queues_subscription_check(sessions):
    async with sessions() as db:
        await WorkflowEventService.enqueue_site_sync(db, {
            "site_id": 7, "site_name": "M-Team", "sync_log_id": 11,
            "resources_new": 0,
        })
        await db.commit()
    await WorkflowEventService.deliver_pending(sessions)
    async with sessions() as db:
        item = await db.scalar(select(TaskExecution))
        assert item.task_type == TASK_TYPE_SUBSCRIPTION_CHECK
        assert item.task_metadata["workflow_step"] == "subscription_check"
        assert item.handler_params["workflow_run_ids"] == ["site_sync:workflow:11"]


@pytest.mark.asyncio
async def test_site_sync_identifies_before_subscription_check(sessions, monkeypatch):
    from app.services.pt.pt_resource_service import PTResourceService

    monkeypatch.setattr(
        PTResourceService, "get_unidentified_resources",
        AsyncMock(return_value=[SimpleNamespace(id=101), SimpleNamespace(id=102)]),
    )
    async with sessions() as db:
        await WorkflowEventService.enqueue_site_sync(db, {
            "site_id": 7, "site_name": "M-Team", "sync_log_id": 12,
            "resources_new": 2,
        })
        await db.commit()
    await WorkflowEventService.deliver_pending(sessions)
    async with sessions() as db:
        identify = await db.scalar(select(TaskExecution))
        assert identify.task_type == TASK_TYPE_PT_RESOURCE_IDENTIFY
        assert identify.handler_params["pt_resource_ids"] == [101, 102]
        assert await db.scalar(
            select(func.count()).select_from(TaskExecution).where(
                TaskExecution.task_type == TASK_TYPE_SUBSCRIPTION_CHECK
            )
        ) == 0
        await WorkflowEventService.enqueue_resource_identified(db, {
            "source_execution_id": identify.id,
            "workflow_run_ids": identify.handler_params["workflow_run_ids"],
        })
        await db.commit()
    await WorkflowEventService.deliver_pending(sessions)
    async with sessions() as db:
        types = (await db.execute(select(TaskExecution.task_type).order_by(TaskExecution.id))).scalars().all()
        assert types == [TASK_TYPE_PT_RESOURCE_IDENTIFY, TASK_TYPE_SUBSCRIPTION_CHECK]


@pytest.mark.asyncio
async def test_media_refresh_events_are_debounced_and_retryable(sessions):
    async with sessions() as db:
        payload = {"user_id": 1, "organized_count": 2}
        await WorkflowEventService.enqueue_media_organized(db, payload)
        await WorkflowEventService.enqueue_media_organized(db, payload)
        await db.commit()
        assert await db.scalar(select(func.count()).select_from(WorkflowEvent)) == 1
    await WorkflowEventService.deliver_pending(sessions)
    async with sessions() as db:
        item = await db.scalar(select(TaskExecution))
        assert item.task_type == TASK_TYPE_MEDIA_SERVER_LIBRARY_REFRESH
        assert item.scheduled_at > now()
        assert item.max_retries == 3


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["hardlink", "copy", "move"])
async def test_file_operation_completed_before_db_commit_is_recovered(tmp_path, mode):
    import os
    import shutil
    source, target = tmp_path / "source.mkv", tmp_path / "target.mkv"
    source.write_bytes(b"complete media contents")
    media = SimpleNamespace(file_path=str(source), sub_status=None)
    config = SimpleNamespace(organize_mode=mode)
    planned = AsyncMock(return_value={"status": "success", "organized_path": str(target)})
    db = AsyncMock()
    assert await MediaOrganizerService._resume_checkpoint(db, media, config, planned, 1) is None
    db.commit.assert_awaited_once()
    if mode == "hardlink":
        os.link(source, target)
    elif mode == "copy":
        shutil.copyfile(source, target)
    else:
        source.rename(target)
    # 模拟物理操作完成，但 organized=True 尚未提交时断电。
    result = await MediaOrganizerService._resume_checkpoint(db, media, config, planned, 1)
    assert result["status"] == "success"
    assert target.read_bytes() == b"complete media contents"


@pytest.mark.asyncio
async def test_partial_copy_is_not_overwritten_or_reported_success(tmp_path):
    source, target = tmp_path / "source.mkv", tmp_path / "target.mkv"
    source.write_bytes(b"complete media contents")
    media = SimpleNamespace(file_path=str(source), sub_status=None)
    config = SimpleNamespace(organize_mode="copy")
    planned = AsyncMock(return_value={"status": "success", "organized_path": str(target)})
    await MediaOrganizerService._resume_checkpoint(AsyncMock(), media, config, planned, 1)
    target.write_bytes(b"partial")
    with pytest.raises(ValueError, match="完整性"):
        await MediaOrganizerService._resume_checkpoint(AsyncMock(), media, config, planned, 1)
    assert target.read_bytes() == b"partial"
    assert source.read_bytes() == b"complete media contents"


@pytest.mark.asyncio
async def test_scheduler_restarts_interrupted_execution_without_duplicate(sessions, monkeypatch):
    import app.services.task.scheduler_manager as scheduler_module
    manager = scheduler_module.scheduler_manager
    monkeypatch.setattr(scheduler_module, "async_session_local", sessions)
    async with sessions() as db:
        await WorkflowEventService.enqueue_download(db, await download(db))
        await db.commit()
    await WorkflowEventService.deliver_pending(sessions)
    interrupted = AsyncMock(side_effect=asyncio.CancelledError())
    monkeypatch.setattr(manager, "_run_task_handler", interrupted)
    with pytest.raises(asyncio.CancelledError):
        await manager._execute_task_by_execution(1)
    async with sessions() as db:
        assert (await db.get(TaskExecution, 1)).status == EXECUTION_STATUS_RUNNING
        await cleanup_stuck_tasks(db)
    handler = AsyncMock(return_value={"status": "success"})
    monkeypatch.setattr(manager, "_run_task_handler", handler)
    await manager._recover_pending_work()
    await asyncio.gather(*list(manager._recovery_tasks))
    async with sessions() as db:
        assert (await db.get(TaskExecution, 1)).status == EXECUTION_STATUS_COMPLETED
        assert await db.scalar(select(func.count()).select_from(TaskExecution)) == 1
    handler.assert_awaited_once()


@pytest.mark.asyncio
async def test_scheduler_failure_enters_retry_queue(sessions, monkeypatch):
    import app.services.task.scheduler_manager as scheduler_module
    manager = scheduler_module.scheduler_manager
    monkeypatch.setattr(scheduler_module, "async_session_local", sessions)
    monkeypatch.setattr(manager, "_run_task_handler", AsyncMock(side_effect=RuntimeError("storage offline")))
    async with sessions() as db:
        db.add(execution())
        await db.commit()
    await manager._execute_task_by_execution(1)
    async with sessions() as db:
        item = await db.get(TaskExecution, 1)
        assert item.status == EXECUTION_STATUS_PENDING
        assert item.retry_count == 1 and item.next_retry_at > now()
        assert item.error_message == "storage offline"


@pytest.mark.asyncio
async def test_auto_organize_resumes_remaining_files_and_reports_failure(sessions, tmp_path, monkeypatch):
    from app.models import MediaFile, OrganizeConfig, StorageMount
    from app.services.mediafile.media_file_service import MediaFileService
    from app.tasks.handlers.media_file_auto_organize_handler import MediaFileAutoOrganizeHandler
    completed = tmp_path / "done.mkv"
    completed.write_bytes(b"done")
    async with sessions() as db:
        config = OrganizeConfig(name="test", media_type="movie", library_root=str(tmp_path),
                                dir_template="{title}", filename_template="{title}", skip_existed=False)
        mount = StorageMount(name="test", mount_type="library", container_path=str(tmp_path))
        db.add_all([config, mount])
        await db.flush()
        task = await download(db, save_path=str(tmp_path), organize_config_id=config.id, storage_mount_id=mount.id)
        db.add(execution())
        for index, organized in enumerate([True, False]):
            db.add(MediaFile(
                file_path=str(tmp_path / f"source-{index}.mkv"), file_name=f"source-{index}.mkv",
                directory=str(tmp_path), file_size=4, file_type="video", extension=".mkv",
                modified_at=now(), media_type="movie", unified_table_name="unified_movies",
                unified_resource_id=1, download_task_id=task.id, organized=organized,
                organized_path=str(completed) if organized else None,
            ))
        await db.commit()
    monkeypatch.setattr(MediaFileService, "create_from_download_task", AsyncMock())
    organize = AsyncMock(return_value={"status": "error", "message": "offline"})
    monkeypatch.setattr(MediaOrganizerService, "organize_media_file", organize)
    async with sessions() as db:
        with pytest.raises(RuntimeError, match="1 个文件未完成"):
            await MediaFileAutoOrganizeHandler.execute(db, {"download_task_id": 1}, 1)
    assert organize.await_count == 1
    assert organize.call_args.kwargs["media_file"].organized is False
    assert organize.call_args.kwargs["resume_safe"] is True
    assert organize.call_args.kwargs["storage_mount_id"] == 1
    async with sessions() as db:
        mount = await db.get(StorageMount, 1)
        mount.container_path = str(tmp_path / "offline-library")
        await db.commit()
        with pytest.raises(FileNotFoundError, match="目标存储路径不可用"):
            await MediaFileAutoOrganizeHandler.execute(db, {"download_task_id": 1}, 1)
    assert organize.await_count == 1  # 存储未就绪时不发起文件操作


@pytest.mark.asyncio
async def test_history_cleanup_does_not_delete_pending_retry(sessions):
    from app.tasks.handlers.task_execution_cleanup_handler import TaskExecutionCleanupHandler
    async with sessions() as db:
        db.add_all([
            execution(completed_at=now() - timedelta(days=30), retry_count=1),
            execution(status=EXECUTION_STATUS_COMPLETED, completed_at=now() - timedelta(days=30)),
            execution(status=EXECUTION_STATUS_RUNNING, task_name="cleanup"),
        ])
        await db.commit()
        db.add(WorkflowEvent(
            business_key="cleanup-test", event_type="download_completed", payload={},
            status=EVENT_DELIVERED, execution_id=2,
        ))
        await db.commit()
        await TaskExecutionCleanupHandler.execute(db, {"keep_failed": False}, 3)
    async with sessions() as db:
        assert await db.get(TaskExecution, 1) is not None
        assert await db.get(TaskExecution, 2) is None
        assert (await db.get(WorkflowEvent, 1)).execution_id is None


@pytest.mark.asyncio
async def test_real_download_update_enqueues_before_nested_service_commit(sessions, monkeypatch):
    from app.services.download.download_task_service import DownloadTaskService
    from app.services.mediafile.media_file_service import MediaFileService
    monkeypatch.setattr(DownloadTaskService, "_backfill_unified_mapping", AsyncMock(return_value=False))
    monkeypatch.setattr(DownloadTaskService, "_send_completion_notification", AsyncMock())

    async def discover(db, task):
        # 文件发现服务本身会提交：此时完成状态与 outbox 必须已经同时存在。
        assert await db.scalar(select(func.count()).select_from(WorkflowEvent)) == 1
        await db.commit()
        return []

    monkeypatch.setattr(MediaFileService, "create_from_download_task", discover)
    info = dict(state="seeding", progress=1, download_speed=0, upload_speed=0,
                downloaded=100, uploaded=0, ratio=0, eta=0)
    async with sessions() as db:
        task = await download(db, progress=50, completed_at=None)
        await db.commit()
        await DownloadTaskService._update_task_record(db, task, info)
        await DownloadTaskService._update_task_record(db, task, info)
        await db.commit()
    async with sessions() as db:
        assert (await db.get(DownloadTask, 1)).completed_at is not None
        assert await db.scalar(select(func.count()).select_from(WorkflowEvent)) == 1


@pytest.mark.asyncio
async def test_backfill_skips_disabled_and_deleted_downloads(sessions):
    async with sessions() as db:
        await download(db, auto_organize=False)
        await download(db, task_hash="deleted-torrent", status="deleted")
        await db.commit()
        assert await WorkflowEventService.backfill_completed(db) == 0
        assert await db.scalar(select(func.count()).select_from(WorkflowEvent)) == 0


@pytest.mark.asyncio
async def test_organizer_recovers_file_side_effect_and_commits_checkpoint_once(sessions, tmp_path, monkeypatch):
    import os
    from app.models import MediaFile, OrganizeConfig
    source, target = tmp_path / "source.mkv", tmp_path / "target.mkv"
    source.write_bytes(b"media data")
    async with sessions() as db:
        config = OrganizeConfig(
            name="resume", media_type="movie", library_root=str(tmp_path),
            dir_template="{title}", filename_template="{title}", organize_mode="hardlink",
            skip_existed=False, generate_nfo=False, download_poster=False, download_backdrop=False,
        )
        media = MediaFile(
            file_path=str(source), file_name=source.name, directory=str(tmp_path),
            file_size=10, file_type="video", extension=".mkv", modified_at=now(),
            media_type="movie", unified_table_name="unified_movies", unified_resource_id=1,
        )
        db.add_all([config, media])
        await db.commit()

    async def interrupted_handler(db, media, config, dry_run, storage_mount_id):
        if not dry_run:
            os.link(source, target)
            raise asyncio.CancelledError()  # 文件操作完成，数据库状态尚未更新
        return {"status": "success", "organized_path": str(target)}

    handler = AsyncMock(side_effect=interrupted_handler)
    monkeypatch.setattr(MediaOrganizerService, "_organize_movie", handler)
    async with sessions() as db:
        with pytest.raises(asyncio.CancelledError):
            await MediaOrganizerService.organize_media_file(
                db, await db.get(MediaFile, 1), await db.get(OrganizeConfig, 1), resume_safe=True,
            )
    async with sessions() as db:
        media, config = await db.get(MediaFile, 1), await db.get(OrganizeConfig, 1)
        assert media.organized is False
        assert media.sub_status["auto_organize_checkpoint"]["target"] == str(target)
        result = await MediaOrganizerService.organize_media_file(db, media, config, resume_safe=True)
        assert result["status"] == "success"
        result = await MediaOrganizerService.organize_media_file(db, media, config, resume_safe=True)
        assert result["status"] == "skipped"
    async with sessions() as db:
        media, config = await db.get(MediaFile, 1), await db.get(OrganizeConfig, 1)
        assert media.organized is True and media.organized_path == str(target)
        assert config.total_organized_count == 1
        assert config.skip_existed is False  # 用户配置没有被自动恢复修改
    assert handler.await_count == 2  # 只有第一次执行调用了计划和实际操作


@pytest.mark.asyncio
async def test_uncommitted_completion_event_is_invisible_to_consumer(sessions):
    async with sessions() as producer:
        task = await download(producer, progress=50, completed_at=None)
        await producer.commit()
        task.progress = 100
        task.completed_at = now()
        await WorkflowEventService.enqueue_download(producer, task)
        async with sessions() as consumer:
            assert await consumer.scalar(select(func.count()).select_from(WorkflowEvent)) == 0
            assert (await consumer.get(DownloadTask, task.id)).completed_at is None
        await producer.commit()
    async with sessions() as consumer:
        assert await consumer.scalar(select(func.count()).select_from(WorkflowEvent)) == 1
        assert (await consumer.get(DownloadTask, task.id)).completed_at is not None


@pytest.mark.asyncio
async def test_deleted_download_id_reuse_has_distinct_workflow(sessions):
    async with sessions() as db:
        original = await download(db)
        await WorkflowEventService.enqueue_download(db, original)
        old_id, old_token = original.id, original.workflow_token
        old_execution = execution(status=EXECUTION_STATUS_COMPLETED)
        db.add(old_execution)
        await db.commit()
        await db.delete(original)
        await db.commit()
        replacement = await download(db)  # 同一 torrent 重新添加，SQLite 可以复用主键
        assert replacement.id == old_id
        assert replacement.workflow_token != old_token
        await WorkflowEventService.enqueue_download(db, replacement)
        await db.commit()
    await WorkflowEventService.deliver_pending(sessions)
    async with sessions() as db:
        events = (await db.execute(select(WorkflowEvent).order_by(WorkflowEvent.id))).scalars().all()
        assert len(events) == 2
        assert events[0].execution_id is None  # 旧事件不能操作新下载
        assert events[1].execution_id is not None
        assert events[1].execution_id != old_execution.id
        assert await WorkflowEventService.backfill_completed(db) == 0


@pytest.mark.asyncio
async def test_old_execution_cannot_organize_readded_download(sessions):
    from app.tasks.handlers.media_file_auto_organize_handler import MediaFileAutoOrganizeHandler
    async with sessions() as db:
        original = await download(db)
        old_token = original.workflow_token
        db.add(execution(handler_params={"download_task_id": original.id, "workflow_token": old_token}))
        await db.commit()
        await db.delete(original)
        await db.commit()
        replacement = await download(db)
        await db.commit()
        with pytest.raises(ValueError, match="原下载任务已删除"):
            await MediaFileAutoOrganizeHandler.execute(
                db, {"download_task_id": replacement.id, "workflow_token": old_token}, 1,
            )
