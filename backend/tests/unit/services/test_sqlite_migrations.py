"""从实际报错的旧版本开始执行完整迁移链，不通过 stamp head 跳过步骤。"""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
import sys

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

from app.core.config import settings
from app.models.llm_config import LLMConfig


BACKEND = Path(__file__).resolve().parents[3]
OLD_REVISION = "a9b8c7d6e5f4"


def build_old_database(tmp_path, monkeypatch, llm_state="absent", named_fk=False, duplicates=False):
    path = tmp_path / "old.db"
    monkeypatch.setattr(settings.database, "DB_TYPE", "sqlite")
    monkeypatch.setattr(settings.database, "SQLITE_PATH", path.as_posix())
    engine = sa.create_engine(f"sqlite:///{path.as_posix()}")
    metadata = sa.MetaData()
    mounts = sa.Table("storage_mounts", metadata, sa.Column("id", sa.Integer, primary_key=True))
    users = sa.Table("users", metadata, sa.Column("id", sa.Integer, primary_key=True))
    downloads = sa.Table(
        "download_tasks", metadata, sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("storage_mount_id", sa.Integer, sa.ForeignKey(
            "storage_mounts.id", name="fk_download_tasks_storage_mount" if named_fk else None,
        )),
        sa.Column("note", sa.Text), sa.CheckConstraint("id > 0", name="check_download_id"),
    )
    sa.Index("ix_test_download_note", downloads.c.note)
    columns = [sa.Column("id", sa.Integer, primary_key=True),
               sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"))]
    if llm_state != "absent":
        LLMConfig.__table__.to_metadata(metadata)
    if llm_state == "complete":
        columns.append(sa.Column("llm_config_id", sa.Integer, sa.ForeignKey("llm_configs.id", ondelete="SET NULL")))
    agents = sa.Table("ai_agent_configs", metadata, *columns)
    resources = sa.Table(
        "pt_resources", metadata, sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("site_id", sa.Integer), sa.Column("torrent_id", sa.String(50)),
    )
    files = sa.Table(
        "media_files", metadata, sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("download_task_id", sa.Integer, sa.ForeignKey("download_tasks.id")),
        sa.Column("match_method", sa.String(30)),
        sa.CheckConstraint("match_method IN ('none', 'from_download')", name="ck_media_file_match_method"),
    )
    organize = sa.Table("organize_configs", metadata, sa.Column("id", sa.Integer, primary_key=True),
                        sa.Column("dir_template", sa.Text))
    sa.Table("task_executions", metadata, sa.Column("id", sa.Integer, primary_key=True))
    with engine.begin() as conn:
        metadata.create_all(conn)
        conn.execute(mounts.insert().values(id=1))
        conn.execute(users.insert().values(id=1))
        conn.execute(downloads.insert().values(id=10, storage_mount_id=1, note="keep this value"))
        conn.execute(agents.insert().values(id=1, user_id=1))
        conn.execute(resources.insert().values(id=1, site_id=1, torrent_id="torrent"))
        if duplicates:
            conn.execute(resources.insert().values(id=2, site_id=1, torrent_id="torrent"))
        conn.execute(files.insert().values(id=1, download_task_id=10, match_method="from_download"))
        conn.execute(organize.insert().values(id=1, dir_template="Show/Season {season}"))
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    command.stamp(cfg, OLD_REVISION)
    return engine, cfg


@pytest.mark.parametrize("llm_state,named_fk", [
    ("absent", False), ("partial", False), ("complete", False), ("complete", True),
])
def test_old_sqlite_schema_upgrades_to_head_without_losing_rows(tmp_path, monkeypatch, llm_state, named_fk):
    engine, cfg = build_old_database(tmp_path, monkeypatch, llm_state, named_fk)
    try:
        command.upgrade(cfg, "head")
        command.upgrade(cfg, "head")  # 重跑不重新建表或添加字段
        with engine.connect() as conn:
            inspector = sa.inspect(conn)
            assert conn.exec_driver_sql("select version_num from alembic_version").scalar() == ScriptDirectory.from_config(cfg).get_current_head()
            assert conn.exec_driver_sql("select id, storage_mount_id, note from download_tasks").all() == [(10, 1, "keep this value")]
            assert conn.exec_driver_sql("select download_task_id from media_files").scalar() == 10
            assert conn.exec_driver_sql("select dir_template from organize_configs").scalar() == "Show/Season {season:02d}"
            assert "workflow_token" in {col["name"] for col in inspector.get_columns("download_tasks")}
            assert "workflow_events" in inspector.get_table_names()
            assert "ix_test_download_note" in {idx["name"] for idx in inspector.get_indexes("download_tasks")}
            assert "check_download_id" in {item["name"] for item in inspector.get_check_constraints("download_tasks")}
            assert inspector.get_foreign_keys("download_tasks")[0]["options"]["ondelete"] == "SET NULL"
            llm_fk = next(fk for fk in inspector.get_foreign_keys("ai_agent_configs") if fk["constrained_columns"] == ["llm_config_id"])
            assert llm_fk["options"]["ondelete"] == "SET NULL"
            assert conn.exec_driver_sql("pragma integrity_check").scalar() == "ok"
            assert conn.exec_driver_sql("pragma foreign_key_check").all() == []
            conn.exec_driver_sql("pragma foreign_keys=ON")
            conn.exec_driver_sql("delete from storage_mounts where id=1")
            assert conn.exec_driver_sql("select storage_mount_id from download_tasks").scalar() is None
            conn.rollback()
    finally:
        engine.dispose()


def test_later_failure_rolls_back_schema_data_and_version(tmp_path, monkeypatch):
    engine, cfg = build_old_database(tmp_path, monkeypatch, duplicates=True)
    try:
        with pytest.raises(sa.exc.IntegrityError):
            command.upgrade(cfg, "head")
        with engine.connect() as conn:
            inspector = sa.inspect(conn)
            assert conn.exec_driver_sql("select version_num from alembic_version").scalar() == OLD_REVISION
            assert not inspector.has_table("llm_configs")
            assert not any(name.startswith("_alembic_tmp_") for name in inspector.get_table_names())
            assert "llm_config_id" not in {col["name"] for col in inspector.get_columns("ai_agent_configs")}
            assert inspector.get_foreign_keys("download_tasks")[0].get("options", {}).get("ondelete") is None
            assert conn.exec_driver_sql("select count(*) from pt_resources").scalar() == 2
            assert conn.exec_driver_sql("select note from download_tasks").scalar() == "keep this value"
    finally:
        engine.dispose()


def test_incompatible_existing_table_is_not_silently_skipped(tmp_path, monkeypatch):
    engine, cfg = build_old_database(tmp_path, monkeypatch, llm_state="partial")
    try:
        with engine.begin() as conn:
            conn.exec_driver_sql("alter table llm_configs drop column model")
        with pytest.raises(RuntimeError, match="llm_configs.model"):
            command.upgrade(cfg, "head")
        with engine.connect() as conn:
            assert conn.exec_driver_sql("select version_num from alembic_version").scalar() == OLD_REVISION
    finally:
        engine.dispose()


@pytest.mark.parametrize("revision", ['193dbdf95aa1', 'c7d8e9f0a1b2'])
def test_foreign_key_migrations_can_emit_postgresql_sql(revision):
    from io import StringIO
    from alembic.runtime.migration import MigrationContext
    from alembic.operations import Operations
    cfg = Config(str(BACKEND / 'alembic.ini'))
    cfg.set_main_option('script_location', str(BACKEND / 'alembic'))
    module = ScriptDirectory.from_config(cfg).get_revision(revision).module
    output = StringIO()
    migration_context = MigrationContext.configure(
        dialect_name='postgresql', opts={'as_sql': True, 'output_buffer': output},
    )
    with Operations.context(migration_context):
        module.upgrade()
        module.downgrade()
    assert 'ON DELETE SET NULL' in output.getvalue()
    assert 'DROP CONSTRAINT' in output.getvalue()


@pytest.mark.asyncio
async def test_startup_stops_on_migration_failure(monkeypatch):
    import app.core.init as initialization
    monkeypatch.setattr(initialization, "_is_fresh_database", AsyncMock(return_value=False))
    run = Mock(return_value=SimpleNamespace(returncode=1, stderr="migration failed"))
    monkeypatch.setattr(initialization.subprocess, "run", run)
    with pytest.raises(RuntimeError, match="停止启动"):
        await initialization.run_alembic_migrations()
    assert run.call_args.args[0] == [sys.executable, "-m", "alembic", "upgrade", "head"]
