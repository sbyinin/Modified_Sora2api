"""File caching service"""
import os
import asyncio
import hashlib
import time
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta
from curl_cffi.requests import AsyncSession
from ..core.config import config
from ..core.logger import debug_logger


class FileCache:
    """File caching service for images and videos"""

    def __init__(self, cache_dir: str = "tmp", default_timeout: int = 7200, proxy_manager=None):
        """
        Initialize file cache

        Args:
            cache_dir: Cache directory path
            default_timeout: Default cache timeout in seconds (default: 2 hours)
            proxy_manager: ProxyManager instance for downloading files
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.default_timeout = default_timeout
        self.proxy_manager = proxy_manager
        self._cleanup_task = None
        self._session = None
        self._session_lock = asyncio.Lock()
        self._download_semaphore = asyncio.Semaphore(self._normalize_int(config.cache_max_concurrency, 3))

    def _normalize_int(self, value: Optional[int], default: int, minimum: int = 1) -> int:
        try:
            normalized = int(value)
        except (TypeError, ValueError):
            return default
        return normalized if normalized >= minimum else default

    async def _get_session(self) -> AsyncSession:
        if self._session is not None:
            return self._session
        async with self._session_lock:
            if self._session is None:
                self._session = AsyncSession()
        return self._session

    async def close(self):
        """Close shared HTTP session"""
        if self._session is None:
            return
        async with self._session_lock:
            if self._session is not None:
                self._session.close()
                self._session = None
        
    async def start_cleanup_task(self):
        """Start background cleanup task"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def stop_cleanup_task(self):
        """Stop background cleanup task"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
    
    async def _cleanup_loop(self):
        """Background task to clean up expired files"""
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                await self._cleanup_expired_files()
            except asyncio.CancelledError:
                break
            except Exception as e:
                debug_logger.log_error(
                    error_message=f"Cleanup task error: {str(e)}",
                    status_code=0,
                    response_text=""
                )
    
    async def _cleanup_expired_files(self):
        """Remove expired cache files"""
        try:
            current_time = time.time()
            removed_count = 0
            
            for file_path in self.cache_dir.iterdir():
                if file_path.is_file():
                    # Check file age
                    file_age = current_time - file_path.stat().st_mtime
                    if file_age > self.default_timeout:
                        try:
                            file_path.unlink()
                            removed_count += 1
                            debug_logger.log_info(f"Removed expired cache file: {file_path.name}")
                        except Exception as e:
                            debug_logger.log_error(
                                error_message=f"Failed to remove file {file_path.name}: {str(e)}",
                                status_code=0,
                                response_text=""
                            )
            
            if removed_count > 0:
                debug_logger.log_info(f"Cleanup completed: removed {removed_count} expired files")
                
        except Exception as e:
            debug_logger.log_error(
                error_message=f"Cleanup error: {str(e)}",
                status_code=0,
                response_text=""
            )
    
    def _generate_cache_filename(self, url: str, media_type: str) -> str:
        """
        Generate cache filename from URL
        
        Args:
            url: Original URL
            media_type: 'image' or 'video'
            
        Returns:
            Cache filename
        """
        # Use URL hash as filename
        url_hash = hashlib.md5(url.encode()).hexdigest()
        
        # Determine extension
        if media_type == "video":
            ext = ".mp4"
        else:
            ext = ".png"
        
        return f"{url_hash}{ext}"
    
    async def download_and_cache(self, url: str, media_type: str) -> str:
        """
        Download file from URL and cache it locally
        
        Args:
            url: File URL to download
            media_type: 'image' or 'video'
            
        Returns:
            Local cache filename
        """
        filename = self._generate_cache_filename(url, media_type)
        file_path = self.cache_dir / filename
        
        # Check if already cached and not expired
        if file_path.exists():
            file_age = time.time() - file_path.stat().st_mtime
            if file_age < self.default_timeout:
                debug_logger.log_info(f"Cache hit: {filename}")
                return filename
            else:
                # Remove expired file
                try:
                    file_path.unlink()
                except Exception:
                    pass
        
        # Download file
        debug_logger.log_info(f"Downloading file from: {url}")

        try:
            session = await self._get_session()
            async with self._download_semaphore:
                response = await session.get(url, timeout=60)

                if response.status_code != 200:
                    raise Exception(f"Download failed: HTTP {response.status_code}")
                
                # Save to cache
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                
                debug_logger.log_info(f"File cached: {filename} ({len(response.content)} bytes)")
                return filename
                
        except Exception as e:
            debug_logger.log_error(
                error_message=f"Failed to download file: {str(e)}",
                status_code=0,
                response_text=str(e)
            )
            raise Exception(f"Failed to cache file: {str(e)}")
    
    def get_cache_path(self, filename: str) -> Path:
        """Get full path to cached file"""
        return self.cache_dir / filename
    
    def set_timeout(self, timeout: int):
        """Set cache timeout in seconds"""
        self.default_timeout = timeout
        debug_logger.log_info(f"Cache timeout updated to {timeout} seconds")
    
    def get_timeout(self) -> int:
        """Get current cache timeout"""
        return self.default_timeout
    
    async def clear_all(self):
        """Clear all cached files"""
        try:
            removed_count = 0
            for file_path in self.cache_dir.iterdir():
                if file_path.is_file():
                    try:
                        file_path.unlink()
                        removed_count += 1
                    except Exception:
                        pass
            
            debug_logger.log_info(f"Cache cleared: removed {removed_count} files")
            return removed_count
            
        except Exception as e:
            debug_logger.log_error(
                error_message=f"Failed to clear cache: {str(e)}",
                status_code=0,
                response_text=""
            )
            raise

