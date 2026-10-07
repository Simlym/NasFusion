"""主视频失败不能落库为已整理；附属文件失败允许保留主视频成功。"""
import errno
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.mediafile.media_organizer_service import MediaOrganizerService
from app.services.mediafile.nfo_generator_service import NFOGeneratorService
from app.services.storage.storage_mount_service import StorageMountService
from app.utils import file_operations


@pytest.mark.asyncio
@pytest.mark.parametrize("category,table", [
    ("movie", "unified_movies"),
    ("tv", "unified_tv_series"),
    ("adult", "unified_adult"),
])
@pytest.mark.parametrize("error_number", [errno.EXDEV, errno.EACCES])
async def test_main_video_failure_never_marks_organized(
    tmp_path, monkeypatch, category, table, error_number,
):
    source = tmp_path / "download" / "source.mkv"
    source.parent.mkdir()
    source.write_bytes(b"media contents")
    library = tmp_path / "library"
    media = SimpleNamespace(
        id=1, organized=False, organized_path=None, file_path=str(source),
        file_name=source.name, extension=".mkv", media_type=category,
        unified_resource_id=1, unified_table_name=table, resolution="2160p",
        season_number=1, episode_number=120, episode_title=None,
    )
    config = SimpleNamespace(
        id=1, is_enabled=True, media_type=category, organize_mode="hardlink",
        dir_template="{title}", filename_template="{title}", skip_existed=True,
        organize_subtitles=True, total_organized_count=0,
        generate_nfo=False, download_poster=False, download_backdrop=False,
    )
    metadata = SimpleNamespace(
        title="Test", original_title="Test", year=2023, product_number="TEST-001",
        maker=None, actresses=[],
    )
    db = AsyncMock()
    db.get.return_value = metadata
    monkeypatch.setattr(StorageMountService, "get_mount_by_id", AsyncMock(
        return_value=SimpleNamespace(name="library", container_path=str(library)),
    ))
    monkeypatch.setattr(NFOGeneratorService, "_find_subscription_for_media_file",
                        AsyncMock(return_value=None))

    def failed_link(*args, **kwargs):
        raise OSError(error_number, "simulated file operation failure")

    monkeypatch.setattr(file_operations.os, "link", failed_link)
    result = await MediaOrganizerService.organize_media_file(
        db, media, config, storage_mount_id=1,
    )

    assert result["status"] == "error"
    assert "视频整理失败" in result["message"]
    if error_number == errno.EXDEV:
        assert "跨文件系统" in result["message"]
    assert media.organized is False
    assert media.organized_path is None
    assert config.total_organized_count == 0
    assert source.read_bytes() == b"media contents"
    assert not list(library.rglob("*.mkv"))


def test_subtitle_failure_keeps_successful_video(tmp_path, monkeypatch):
    source = tmp_path / "source.mkv"
    source.write_bytes(b"media contents")
    source.with_suffix(".srt").write_text("subtitle", encoding="utf-8")
    original = file_operations.organize_file

    def organize(source_path, *args, **kwargs):
        if source_path.suffix == ".srt":
            raise file_operations.FileOperationError("subtitle permission denied")
        return original(source_path, *args, **kwargs)

    monkeypatch.setattr(file_operations, "organize_file", organize)
    result = file_operations.organize_with_associated_files(
        source, tmp_path / "library", "renamed", mode="copy",
    )
    assert (tmp_path / "library" / "renamed.mkv").read_bytes() == b"media contents"
    assert result["video"]
    assert len(result["errors"]) == 1
    assert "subtitle permission denied" in result["errors"][0]
