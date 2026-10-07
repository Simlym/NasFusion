from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.v1.downloaders import router as downloader_router
from app.api.v1.media_directories import _validated_image_path
from app.core.dependencies import get_current_admin_user


@pytest.mark.asyncio
async def test_anonymous_user_is_rejected() -> None:
    from app.core.dependencies import get_current_user

    with pytest.raises(HTTPException) as exc:
        await get_current_user(None, None)
    assert exc.value.status_code == 401


def test_all_downloader_routes_require_admin() -> None:
    assert downloader_router.routes
    for route in downloader_router.routes:
        dependencies = [item.dependency for item in route.dependencies]
        assert get_current_admin_user in dependencies


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("user", "expected_detail"),
    [
        (SimpleNamespace(is_active=True, is_locked=False, is_admin=False), "需要管理员权限"),
        (SimpleNamespace(is_active=False, is_locked=False, is_admin=True), "用户已被禁用"),
    ],
)
async def test_admin_dependency_rejects_non_admin_and_disabled_users(user, expected_detail) -> None:
    from app.core.dependencies import get_current_active_user

    if not user.is_active:
        with pytest.raises(HTTPException) as exc:
            await get_current_active_user(user)
    else:
        with pytest.raises(HTTPException) as exc:
            await get_current_admin_user(user)
    assert exc.value.status_code == 403
    assert exc.value.detail == expected_detail


def test_media_image_must_stay_inside_directory(tmp_path: Path) -> None:
    media_dir = tmp_path / "library"
    media_dir.mkdir()
    outside = tmp_path / "secret.jpg"
    outside.write_bytes(b"\xff\xd8\xffnot-really-important")
    directory = SimpleNamespace(directory_path=str(media_dir), poster_path=str(outside), backdrop_path=None)

    with pytest.raises(HTTPException) as exc:
        _validated_image_path(directory, "poster")
    assert exc.value.status_code == 403


def test_media_image_rejects_non_image_content(tmp_path: Path) -> None:
    media_dir = tmp_path / "library"
    media_dir.mkdir()
    fake_image = media_dir / "poster.jpg"
    fake_image.write_text("private text", encoding="utf-8")
    directory = SimpleNamespace(directory_path=str(media_dir), poster_path=str(fake_image), backdrop_path=None)

    with pytest.raises(HTTPException) as exc:
        _validated_image_path(directory, "poster")
    assert exc.value.status_code == 415
