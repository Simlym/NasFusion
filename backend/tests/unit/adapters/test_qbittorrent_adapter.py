import httpx
import pytest

from app.adapters.downloaders.qbittorrent import QBittorrentAdapter


def _create_adapter(handler):
    adapter = QBittorrentAdapter(
        {
            "host": "qbittorrent",
            "port": 8080,
            "username": "admin",
            "password": "secret",
            "use_ssl": False,
        }
    )
    adapter._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return adapter


@pytest.mark.asyncio
async def test_login_accepts_qbittorrent_5_2_response():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v2/auth/login"
        return httpx.Response(
            204,
            headers={"set-cookie": "QBT_SID_8080=new-session; HttpOnly; path=/"},
        )

    adapter = _create_adapter(handler)

    try:
        assert await adapter._login() is True
        assert adapter._cookies == {"QBT_SID_8080": "new-session"}
    finally:
        await adapter.close()


@pytest.mark.asyncio
async def test_login_accepts_legacy_response():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text="Ok.",
            headers={"set-cookie": "SID=legacy-session; HttpOnly; path=/"},
        )

    adapter = _create_adapter(handler)

    try:
        assert await adapter._login() is True
        assert adapter._cookies == {"SID": "legacy-session"}
    finally:
        await adapter.close()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status_code", "body", "headers"),
    [
        (200, "Fails.", {}),
        (204, "", {}),
        (403, "Forbidden", {}),
    ],
)
async def test_login_rejects_failed_or_cookie_less_response(
    status_code: int,
    body: str,
    headers: dict[str, str],
):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, text=body, headers=headers)

    adapter = _create_adapter(handler)

    try:
        assert await adapter._login() is False
        assert adapter._cookies is None
    finally:
        await adapter.close()


@pytest.mark.asyncio
async def test_add_torrent_file_accepts_qbittorrent_5_2_response():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v2/torrents/add"
        return httpx.Response(
            200,
            json={
                "added_torrent_ids": ["torrent-hash"],
                "failure_count": 0,
                "pending_count": 0,
                "success_count": 1,
            },
        )

    adapter = _create_adapter(handler)
    adapter._cookies = {"QBT_SID_8080": "session"}

    try:
        result = await adapter.add_torrent_file(b"torrent-data", "/downloads")
        assert result["success"] is True
    finally:
        await adapter.close()


@pytest.mark.asyncio
async def test_add_torrent_magnet_accepts_pending_response():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v2/torrents/add"
        return httpx.Response(
            202,
            json={
                "added_torrent_ids": ["magnet-hash"],
                "failure_count": 0,
                "pending_count": 1,
                "success_count": 0,
            },
        )

    adapter = _create_adapter(handler)
    adapter._cookies = {"QBT_SID_8080": "session"}

    try:
        result = await adapter.add_torrent_magnet(
            "magnet:?xt=urn:btih:magnet-hash",
            "/downloads",
        )
        assert result["success"] is True
    finally:
        await adapter.close()


@pytest.mark.asyncio
async def test_add_torrent_rejects_qbittorrent_5_2_failure_response():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            409,
            json={
                "added_torrent_ids": [],
                "failure_count": 1,
                "pending_count": 0,
                "success_count": 0,
            },
        )

    adapter = _create_adapter(handler)
    adapter._cookies = {"QBT_SID_8080": "session"}

    try:
        with pytest.raises(Exception, match="Failed to add torrent"):
            await adapter.add_torrent_file(b"torrent-data", "/downloads")
    finally:
        await adapter.close()
