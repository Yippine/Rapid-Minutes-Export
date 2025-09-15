"""
Temporary Storage Manager (E4 - Data Storage Layer)
Manages temporary files during processing with automatic cleanup
Implements SESE principle - Simple, Effective, Systematic, Exhaustive temp file management
"""

import asyncio
import logging
import os
import shutil
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
import aiofiles

from ..config import settings

logger = logging.getLogger(__name__)


@dataclass
class TempFileInfo:
    """Temporary file information"""
    file_id: str
    file_path: str
    original_name: str
    created_at: datetime
    last_accessed: datetime
    file_size: int
    purpose: str  # processing, upload, conversion, etc.
    ttl: timedelta  # time to live
    cleanup_scheduled: bool = False


class TempStorage:
    """
    Temporary storage manager with automatic cleanup
    Handles temporary files during processing workflow
    """
    
    def __init__(self, base_temp_dir: Optional[str] = None, default_ttl_hours: int = 6):
        """Initialize temporary storage manager"""
        self.base_temp_dir = Path(base_temp_dir or settings.temp_dir)
        self.default_ttl = timedelta(hours=default_ttl_hours)
        
        # Active temp files registry
        self._temp_files: Dict[str, TempFileInfo] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        self._cleanup_interval = 300  # 5 minutes
        
        # Ensure temp directory exists
        self.base_temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Start cleanup task
        self._start_cleanup_task()
        
        logger.info(f"🗂️ Temp Storage initialized - dir: {self.base_temp_dir}, TTL: {default_ttl_hours}h")
    
    async def store_file(
        self, 
        file_id: str, 
        file_data: bytes, 
        original_name: str,
        purpose: str = "processing",
        ttl: Optional[timedelta] = None
    ) -> str:
        """
        Store temporary file
        
        Args:
            file_id: Unique file identifier
            file_data: File content bytes
            original_name: Original filename
            purpose: Purpose of temporary file
            ttl: Time to live (auto-cleanup after this time)
            
        Returns:
            Path to stored temporary file
        """
        ttl = ttl or self.default_ttl
        
        # Generate temp file path
        temp_path = await self._generate_temp_path(file_id, original_name)
        
        logger.info(f"💾 Storing temp file: {file_id} ({len(file_data)} bytes) - {purpose}")
        
        try:
            # Write file
            async with aiofiles.open(temp_path, 'wb') as f:
                await f.write(file_data)
            
            # Register temp file
            temp_info = TempFileInfo(
                file_id=file_id,
                file_path=str(temp_path),
                original_name=original_name,
                created_at=datetime.utcnow(),
                last_accessed=datetime.utcnow(),
                file_size=len(file_data),
                purpose=purpose,
                ttl=ttl
            )
            
            self._temp_files[file_id] = temp_info
            
            logger.debug(f"✅ Temp file stored: {file_id} -> {temp_path}")
            return str(temp_path)
            
        except Exception as e:
            logger.error(f"❌ Error storing temp file {file_id}: {e}")
            # Cleanup on error
            if temp_path.exists():
                temp_path.unlink()
            raise
    
    async def get_file(self, file_id: str) -> Optional[bytes]:
        """Get temporary file content"""
        if file_id not in self._temp_files:
            return None
        
        temp_info = self._temp_files[file_id]
        
        try:
            async with aiofiles.open(temp_info.file_path, 'rb') as f:
                content = await f.read()
            
            # Update last accessed
            temp_info.last_accessed = datetime.utcnow()
            
            return content
            
        except FileNotFoundError:
            logger.warning(f"⚠️ Temp file not found: {file_id}")
            # Remove from registry
            del self._temp_files[file_id]
            return None
    
    async def get_file_path(self, file_id: str) -> Optional[str]:
        """Get temporary file path"""
        if file_id not in self._temp_files:
            return None
        
        temp_info = self._temp_files[file_id]
        
        if Path(temp_info.file_path).exists():
            temp_info.last_accessed = datetime.utcnow()
            return temp_info.file_path
        else:
            # Remove from registry if file doesn't exist
            del self._temp_files[file_id]
            return None
    
    async def extend_ttl(self, file_id: str, additional_hours: int = 2) -> bool:
        """Extend time-to-live for temporary file"""
        if file_id not in self._temp_files:
            return False
        
        temp_info = self._temp_files[file_id]
        temp_info.ttl += timedelta(hours=additional_hours)
        
        logger.debug(f"⏰ Extended TTL for temp file {file_id} by {additional_hours}h")
        return True
    
    async def delete_file(self, file_id: str) -> bool:
        """Delete temporary file immediately"""
        if file_id not in self._temp_files:
            return False
        
        temp_info = self._temp_files[file_id]
        
        try:
            # Remove file from disk
            if Path(temp_info.file_path).exists():
                os.remove(temp_info.file_path)
            
            # Remove from registry
            del self._temp_files[file_id]
            
            logger.debug(f"🗑️ Temp file deleted: {file_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error deleting temp file {file_id}: {e}")
            return False
    
    async def list_temp_files(self, purpose: Optional[str] = None) -> List[TempFileInfo]:
        """List temporary files, optionally filtered by purpose"""
        files = list(self._temp_files.values())
        
        if purpose:
            files = [f for f in files if f.purpose == purpose]
        
        return files
    
    async def cleanup_expired_files(self) -> int:
        """Clean up expired temporary files"""
        current_time = datetime.utcnow()
        expired_files = []
        
        for file_id, temp_info in self._temp_files.items():
            if current_time - temp_info.created_at > temp_info.ttl:
                expired_files.append(file_id)
        
        cleanup_count = 0
        for file_id in expired_files:
            if await self.delete_file(file_id):
                cleanup_count += 1
        
        if cleanup_count > 0:
            logger.info(f"🧹 Cleaned up {cleanup_count} expired temp files")
        
        return cleanup_count
    
    async def cleanup_orphaned_files(self) -> int:
        """Clean up orphaned files in temp directory"""
        cleanup_count = 0
        registered_paths = {info.file_path for info in self._temp_files.values()}
        
        # Check all files in temp directory
        for file_path in self.base_temp_dir.rglob('*'):
            if file_path.is_file():
                if str(file_path) not in registered_paths:
                    try:
                        file_path.unlink()
                        cleanup_count += 1
                        logger.debug(f"🗑️ Removed orphaned temp file: {file_path}")
                    except Exception as e:
                        logger.warning(f"⚠️ Could not remove orphaned file {file_path}: {e}")
        
        if cleanup_count > 0:
            logger.info(f"🧹 Cleaned up {cleanup_count} orphaned temp files")
        
        return cleanup_count
    
    async def emergency_cleanup(self) -> int:
        """Emergency cleanup - remove all temporary files"""
        cleanup_count = len(self._temp_files)
        
        # Delete all registered files
        for file_id in list(self._temp_files.keys()):
            await self.delete_file(file_id)
        
        # Clean up orphaned files
        orphaned_count = await self.cleanup_orphaned_files()
        
        logger.warning(f"🚨 Emergency cleanup completed: {cleanup_count + orphaned_count} files removed")
        return cleanup_count + orphaned_count
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get temporary storage statistics"""
        total_files = len(self._temp_files)
        total_size = sum(info.file_size for info in self._temp_files.values())
        
        # Group by purpose
        purpose_stats = {}
        for info in self._temp_files.values():
            if info.purpose not in purpose_stats:
                purpose_stats[info.purpose] = {'count': 0, 'size': 0}
            purpose_stats[info.purpose]['count'] += 1
            purpose_stats[info.purpose]['size'] += info.file_size
        
        # Calculate disk usage
        disk_usage = self._get_directory_size()
        
        return {
            'total_temp_files': total_files,
            'total_registered_size': total_size,
            'actual_disk_usage': disk_usage,
            'purpose_breakdown': purpose_stats,
            'cleanup_task_active': self._cleanup_task and not self._cleanup_task.done(),
            'base_temp_dir': str(self.base_temp_dir)
        }
    
    async def create_temp_directory(self, prefix: str = "processing") -> str:
        """Create a temporary directory for batch processing"""
        temp_dir = self.base_temp_dir / f"{prefix}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        logger.debug(f"📁 Created temp directory: {temp_dir}")
        return str(temp_dir)
    
    async def copy_to_temp(self, source_path: str, file_id: str, purpose: str = "copy") -> str:
        """Copy existing file to temporary storage"""
        if not Path(source_path).exists():
            raise FileNotFoundError(f"Source file not found: {source_path}")
        
        # Read source file
        async with aiofiles.open(source_path, 'rb') as f:
            file_data = await f.read()
        
        # Store as temporary file
        original_name = Path(source_path).name
        return await self.store_file(file_id, file_data, original_name, purpose)
    
    async def move_to_permanent(self, file_id: str, destination_path: str) -> bool:
        """Move temporary file to permanent location"""
        if file_id not in self._temp_files:
            return False
        
        temp_info = self._temp_files[file_id]
        source_path = Path(temp_info.file_path)
        dest_path = Path(destination_path)
        
        if not source_path.exists():
            return False
        
        try:
            # Ensure destination directory exists
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Move file
            shutil.move(str(source_path), str(dest_path))
            
            # Remove from temp registry
            del self._temp_files[file_id]
            
            logger.info(f"📦 Moved temp file to permanent: {file_id} -> {dest_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error moving temp file {file_id}: {e}")
            return False
    
    # Private methods
    
    async def _generate_temp_path(self, file_id: str, original_name: str) -> Path:
        """Generate temporary file path"""
        # Create subdirectory by date for organization
        date_subdir = datetime.utcnow().strftime('%Y%m%d')
        temp_subdir = self.base_temp_dir / date_subdir
        temp_subdir.mkdir(parents=True, exist_ok=True)
        
        # Use file_id as base name to avoid conflicts
        file_extension = Path(original_name).suffix
        return temp_subdir / f"temp_{file_id}{file_extension}"
    
    def _start_cleanup_task(self):
        """Start background cleanup task"""
        async def cleanup_loop():
            while True:
                try:
                    await asyncio.sleep(self._cleanup_interval)
                    await self.cleanup_expired_files()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"❌ Error in cleanup task: {e}")
        
        self._cleanup_task = asyncio.create_task(cleanup_loop())
        logger.debug("🧹 Cleanup task started")
    
    def _get_directory_size(self) -> int:
        """Calculate total size of temp directory"""
        total_size = 0
        
        if self.base_temp_dir.exists():
            for file_path in self.base_temp_dir.rglob('*'):
                if file_path.is_file():
                    try:
                        total_size += file_path.stat().st_size
                    except (OSError, IOError):
                        pass
        
        return total_size
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - cleanup"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Optional: cleanup all temp files on exit
        # await self.emergency_cleanup()
    
    def schedule_file_cleanup(self, file_id: str, delay_seconds: int):
        """Schedule a file for delayed cleanup"""
        if file_id not in self._temp_files:
            return
        
        temp_info = self._temp_files[file_id]
        temp_info.cleanup_scheduled = True
        
        async def delayed_cleanup():
            await asyncio.sleep(delay_seconds)
            await self.delete_file(file_id)
        
        asyncio.create_task(delayed_cleanup())
        logger.debug(f"⏰ Scheduled cleanup for temp file {file_id} in {delay_seconds}s")
    
    async def get_temp_file_info(self, file_id: str) -> Optional[TempFileInfo]:
        """Get temporary file information"""
        return self._temp_files.get(file_id)
    
    async def batch_store_files(
        self, 
        files: List[Dict[str, Any]], 
        purpose: str = "batch_processing"
    ) -> List[str]:
        """Store multiple files in batch"""
        stored_paths = []
        
        for file_info in files:
            file_id = file_info['file_id']
            file_data = file_info['data']
            original_name = file_info['name']
            
            try:
                path = await self.store_file(file_id, file_data, original_name, purpose)
                stored_paths.append(path)
            except Exception as e:
                logger.error(f"❌ Failed to store file {file_id} in batch: {e}")
                stored_paths.append(None)
        
        logger.info(f"📦 Batch stored {len([p for p in stored_paths if p])} of {len(files)} files")
        return stored_paths