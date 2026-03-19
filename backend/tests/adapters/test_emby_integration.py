import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from app.adapters.media_servers.emby import EmbyAdapter
import httpx

@pytest.fixture
def adapter():
    config = {
        "name": "TestEmby",
        "host": "localhost",
        "port": 8096,
        "api_key": "test_emby_key",
        "use_ssl": False
    }
    return EmbyAdapter(config)

@pytest.mark.asyncio
async def test_get_system_info(adapter):
    mock_response = {
        "ServerName": "Test Emby",
        "Version": "4.7.11",
        "Id": "emby_server_id"
    }
    
    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.json.return_value = mock_response
    mock_res.raise_for_status.return_value = None

    mock_client_instance = AsyncMock()
    mock_client_instance.get.return_value = mock_res
    
    # Emby inherits from Jellyfin but might be mocked slightly differently if needed, 
    # but since it uses the same base class logic for system info, this should work.
    # Note: EmbyAdapter is in `app.adapters.media_servers.emby` but imports JellyfinAdapter from `jellyfin`.
    # The actual implementation calls `super().get_system_info()`? No, it inherits it.
    # So we patch where `httpx.AsyncClient` is used. Since it inherits, it uses `JellyfinAdapter`'s methods.
    # So we should patch inside `app.adapters.media_servers.jellyfin` or wherever `httpx` is used.
    # Since `EmbyAdapter` imports `JellyfinAdapter`, the code runs in `jellyfin.py`.
    
    with patch("app.adapters.media_servers.jellyfin.httpx.AsyncClient") as mock_client_cls:
        mock_client_cls.return_value.__aenter__.return_value = mock_client_instance
        
        result = await adapter.get_system_info()
        
        assert result["ServerName"] == "Test Emby"
        assert result["Version"] == "4.7.11"
        
        args, kwargs = mock_client_instance.get.call_args
        assert str(args[0]).endswith("/System/Info")
        # Emby uses X-Emby-Token as well
        assert kwargs["headers"]["X-Emby-Token"] == "test_emby_key"

@pytest.mark.asyncio
async def test_get_sessions(adapter):
    mock_response = [{"Id": "session_emby", "UserName": "UserEmby"}]
    
    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.json.return_value = mock_response
    mock_res.raise_for_status.return_value = None

    mock_client_instance = AsyncMock()
    mock_client_instance.get.return_value = mock_res
    
    with patch("app.adapters.media_servers.jellyfin.httpx.AsyncClient") as mock_client_cls:
        mock_client_cls.return_value.__aenter__.return_value = mock_client_instance
        
        result = await adapter.get_sessions()
        
        assert len(result) == 1
        assert result[0]["UserName"] == "UserEmby"
        assert str(mock_client_instance.get.call_args[0][0]).endswith("/Sessions")

@pytest.mark.asyncio
async def test_get_latest_media(adapter):
    mock_users = [{"id": "user_emby", "name": "Admin"}]
    mock_latest = [{"Name": "Latest Movie", "Id": "movie_emby"}]
    
    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.json.return_value = mock_latest
    
    mock_client_instance = AsyncMock()
    mock_client_instance.get.return_value = mock_res
    
    with patch.object(adapter, 'get_users', new_callable=AsyncMock) as mock_get_users:
        mock_get_users.return_value = mock_users
        
        with patch("app.adapters.media_servers.jellyfin.httpx.AsyncClient") as mock_client_cls:
            mock_client_cls.return_value.__aenter__.return_value = mock_client_instance
            
            result = await adapter.get_latest_media(limit=5)
            
            assert len(result) == 1
            assert result[0]["Name"] == "Latest Movie"
            # Since mock_users return user_emby, the path should contain it
            path_arg = str(mock_client_instance.get.call_args[0][0])
            assert "/Users/user_emby/Items/Latest" in path_arg

@pytest.mark.asyncio
async def test_search(adapter):
    mock_users = [{"id": "user_emby", "name": "Admin"}]
    mock_search_result = {"Items": [{"Name": "Found Emby Movie", "Id": "movie2"}]}
    
    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.json.return_value = mock_search_result
    
    mock_client_instance = AsyncMock()
    mock_client_instance.get.return_value = mock_res
    
    with patch.object(adapter, 'get_users', new_callable=AsyncMock) as mock_get_users:
        mock_get_users.return_value = mock_users
        
        with patch("app.adapters.media_servers.jellyfin.httpx.AsyncClient") as mock_client_cls:
            mock_client_cls.return_value.__aenter__.return_value = mock_client_instance
            
            result = await adapter.search("Found")
            
            assert len(result) == 1
            assert result[0]["Name"] == "Found Emby Movie"
            
            args, kwargs = mock_client_instance.get.call_args
            assert kwargs["params"]["SearchTerm"] == "Found"
