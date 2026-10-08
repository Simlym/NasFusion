"""批次历史必须关联同步日志而非执行 ID，并保留共享任务和稳定顺序。"""
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.services.task.task_execution_service import TaskExecutionService
from app.utils.timezone import now


def execution(execution_id, offset=0, **overrides):
    values = dict(id=execution_id, created_at=now() + timedelta(seconds=offset),
                  task_type="subscription_check", task_metadata={}, handler_params={}, result={})
    values.update(overrides)
    return SimpleNamespace(**values)


def test_groups_include_sync_root_and_shared_execution_in_creation_order():
    root = execution(100, task_type="pt_resource_sync", result={"sync_log_id": 12})
    identify = execution(101, 1, handler_params={"workflow_run_ids": ["site_sync:workflow:12"]})
    shared = execution(102, 2, task_metadata={"workflow_run_ids": ["site_sync:workflow:12", "site_sync:workflow:13"]})
    independent = execution(103, 3)
    groups = TaskExecutionService.group_workflow_executions([shared, identify, independent, root])
    by_id = {group["batch_id"]: group for group in groups}
    assert [item.id for item in by_id["site_sync:workflow:12"]["items"]] == [100, 101, 102]
    assert [item.id for item in by_id["site_sync:workflow:13"]["items"]] == [102]
    assert not by_id["execution:103"]["is_workflow"]
    assert "site_sync:workflow:100" not in by_id


@pytest.mark.asyncio
async def test_filter_keeps_whole_batch_and_paginates_batches():
    root = execution(1, task_type="pt_resource_sync", result={"sync_log_id": 12})
    child = execution(2, 1, task_metadata={"workflow_run_ids": ["site_sync:workflow:12"]})
    other = execution(3, 2)
    with patch.object(TaskExecutionService, "get_all", new=AsyncMock(
        side_effect=[([child], 1), ([root, child, other], 3)])):
        groups, total = await TaskExecutionService.get_workflow_history(None, 1, 1, status="failed")
    assert total == 1
    assert [item.id for item in groups[0]["items"]] == [1, 2]
