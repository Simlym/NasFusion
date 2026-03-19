import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from app.adapters.media_servers.plex import PlexAdapter

@pytest.fixture
def adapter():
    config = {
        "name": "TestPlex",
        "host": "localhost",
        "port": 32400,
        "token": "test_token",
        "use_ssl": False
    }
    return PlexAdapter(config)

@pytest.mark.asyncio
async def test_get_system_info(adapter):
    mock_response = {
        "MediaContainer": {
            "machineIdentifier": "plex_id_123",
            "version": "1.2.3"
        }
    }
    
    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.json.return_value = mock_response
    mock_res.raise_for_status.return_value = None

    mock_client_instance = AsyncMock()
    mock_client_instance.get.return_value = mock_res
    
    with patch("app.adapters.media_servers.plex.httpx.AsyncClient") as mock_client_cls:
        mock_client_cls.return_value.__aenter__.return_value = mock_client_instance
        
        result = await adapter.get_system_info()
        assert result["Id"] == "plex_id_123"
        assert result["Version"] == "1.2.3"
        
        # Verify AsyncClient init args
        init_kwargs = mock_client_cls.call_args[1]
        assert init_kwargs["headers"]["X-Plex-Token"] == "test_token"

@pytest.mark.asyncio
async def test_get_sessions(adapter):
    mock_response = {
        "MediaContainer": {
            "Metadata": [
                {
                    "sessionKey": "s1",
                    "User": {"title": "User1"},
                    "title": "Movie Title",
                    "type": "movie"
                }
            ]
        }
    }
    
    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.json.return_value = mock_response
    
    mock_client_instance = AsyncMock()
    mock_client_instance.get.return_value = mock_res
    
    with patch("app.adapters.media_servers.plex.httpx.AsyncClient") as mock_client_cls:
        mock_client_cls.return_value.__aenter__.return_value = mock_client_instance
        
        result = await adapter.get_sessions()
        assert len(result) == 1
        assert result[0]["UserName"] == "User1"
        assert result[0]["ItemName"] == "Movie Title"

@pytest.mark.asyncio
async def test_get_latest_media(adapter):
    mock_response = {
        "MediaContainer": {
            "Metadata": [
                {"title": "Latest Movie", "ratingKey": "100"}
            ]
        }
    }
    
    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.json.return_value = mock_response
    
    mock_client_instance = AsyncMock()
    mock_client_instance.get.return_value = mock_res
    
    with patch("app.adapters.media_servers.plex.httpx.AsyncClient") as mock_client_cls:
        mock_client_cls.return_value.__aenter__.return_value = mock_client_instance
        
        result = await adapter.get_latest_media(limit=5)
        assert len(result) == 1
        assert result[0]["title"] == "Latest Movie"
        assert "/library/recentlyAdded" in str(mock_client_instance.get.call_args[0][0])
