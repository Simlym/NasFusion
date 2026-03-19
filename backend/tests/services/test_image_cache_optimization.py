
import os
# Set env var before importing app settings to avoid validation error
os.environ["SECRET_KEY"] = "test_secret_key_must_be_at_least_32_bytes_long_for_security"

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timedelta
from app.services.common.image_cache_service import ImageCacheService
from app.models.image_cache import ImageCache

@pytest.fixture
def mock_db():
    session = AsyncMock()
    # Mock execute result for scalar_one_or_none
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    session.execute.return_value = mock_result
    return session

@pytest.mark.asyncio
async def test_access_throttling_daily(mock_db):
    """Verify that access stats are only updated once per day (24h)"""
    url = "http://example.com/test.jpg"
    
    # Setup cache entry with recent access (1 hour ago)
    cache_entry = ImageCache(
        original_url=url,
        last_accessed_at=datetime.now() - timedelta(hours=1),
        access_count=10
    )
    
    # Mock DB returning this entry
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = cache_entry
    mock_db.execute.return_value = mock_result
    
    # 1. Call get_cached_image - should NOT trigger commit
    await ImageCacheService.get_cached_image(mock_db, url)
    mock_db.commit.assert_not_called()
    
    # Setup cache entry with OLD access (25 hours ago)
    cache_entry.last_accessed_at = datetime.now() - timedelta(hours=25)
    
    # 2. Call get_cached_image - SHOULD trigger commit
    await ImageCacheService.get_cached_image(mock_db, url)
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_concurrent_download_locking(mock_db):
    """Verify that concurrent requests for the same URL are locked and sequential"""
    url = "http://example.com/concurrent.jpg"
    
    # Mock DB to return None initially (not cached)
    mock_files_result = MagicMock()
    mock_files_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_files_result

    # Mock settings path
    with patch('app.services.common.image_cache_service.settings') as mock_settings, \
         patch('app.services.common.image_cache_service.httpx.AsyncClient') as mock_client_cls, \
         patch('app.services.common.image_cache_service.aiofiles.open') as mock_aio_open, \
         patch.object(ImageCacheService, 'get_cached_image', side_effect=[None, ImageCache(local_path="foo"), ImageCache(local_path="foo")]) as mock_get_cache:
        
        mock_settings.IMAGE_CACHE_PATH = "/tmp/cache"
        
        # Setup Mock HTTP Client
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        
        # Simulate slow download
        async def slow_get(*args, **kwargs):
            await asyncio.sleep(0.1)
            response = MagicMock()
            response.raise_for_status = MagicMock()
            response.headers = {"content-type": "image/jpeg"}
            response.content = b"fake_image_data"
            return response
            
        mock_client.get.side_effect = slow_get

        # Mock aiofiles
        mock_file = AsyncMock()
        mock_aio_open.return_value.__aenter__.return_value = mock_file
        
        # Mock file existence check (path.exists)
        # We need Path object returned by _get_cache_root / existing.local_path to have .exists() return True
        # Since we are mocking get_cached_image returning an object with local_path="foo"
        # And get_file_path joins root + local_path.
        # We need to mock Path.exists. 
        # But get_cached_image is patched, so we just need to ensure when it returns an object, the code:
        # full_path = ... / existing.local_path
        # if full_path.exists(): return existing
        # works.
        
        with patch('pathlib.Path.exists', return_value=True):
            # Run 3 concurrent downloads
            tasks = [
                ImageCacheService.download_and_cache(mock_db, url),
                ImageCacheService.download_and_cache(mock_db, url),
                ImageCacheService.download_and_cache(mock_db, url)
            ]
            
            results = await asyncio.gather(*tasks)
        
        # Verification:
        assert mock_client.get.call_count == 1
        mock_file.write.assert_called_once_with(b"fake_image_data")

