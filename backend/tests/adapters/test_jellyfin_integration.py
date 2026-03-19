import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from app.adapters.media_servers.jellyfin import JellyfinAdapter
import httpx

@pytest.fixture
def adapter():
    config = {
        "name": "TestServer",
        "host": "localhost",
        "port": 8096,
        "api_key": "test_key",
        "use_ssl": False
    }
    return JellyfinAdapter(config)

@pytest.mark.asyncio
async def test_get_system_info(adapter):
    mock_response = {
        "ServerName": "Test Jellyfin",
        "Version": "10.8.10",
        "Id": "server_id_123"
    }
    
    # Mock the response object
    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.json.return_value = mock_response
    mock_res.raise_for_status.return_value = None

    # Mock the client instance
    mock_client_instance = AsyncMock()
    mock_client_instance.get.return_value = mock_res
    
    # Mock the AsyncClient context manager
    with patch("app.adapters.media_servers.jellyfin.httpx.AsyncClient") as mock_client_cls:
        mock_client_cls.return_value.__aenter__.return_value = mock_client_instance
        
        result = await adapter.get_system_info()
        
        assert result["ServerName"] == "Test Jellyfin"
        assert result["Version"] == "10.8.10"
        
        # Verify get was called correctly
        args, kwargs = mock_client_instance.get.call_args
        assert str(args[0]).endswith("/System/Info")
        assert kwargs["headers"]["X-Emby-Token"] == "test_key"

@pytest.mark.asyncio
async def test_get_sessions(adapter):
    mock_response = [{"Id": "session1", "UserName": "User1"}]
    
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
        assert result[0]["UserName"] == "User1"
        assert str(mock_client_instance.get.call_args[0][0]).endswith("/Sessions")

@pytest.mark.asyncio
async def test_get_latest_media(adapter):
    # Mock get_users
    mock_users = [{"id": "user1", "name": "Admin"}]
    mock_latest = [{"Name": "Latest Movie", "Id": "movie1"}]
    
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
            assert "/Users/user1/Items/Latest" in str(mock_client_instance.get.call_args[0][0])

@pytest.mark.asyncio
async def test_search(adapter):
    mock_users = [{"id": "user1", "name": "Admin"}]
    mock_search_result = {"Items": [{"Name": "Found Movie", "Id": "movie2"}]}
    
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
            assert result[0]["Name"] == "Found Movie"
            
            args, kwargs = mock_client_instance.get.call_args
            assert kwargs["params"]["SearchTerm"] == "Found"
