"""
File Manager (E1 - Data Storage Layer)  
Advanced file storage and management system
Implements MECE principle - independent file operations with complete coverage
"""

import asyncio
import logging
import os
import shutil
from typing import Dict, List, Optional, Union, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
import aiofiles
import hashlib
import json

from ..config import settings

logger = logging.getLogger(__name__)


@dataclass
class FileMetadata:
    """File metadata container"""
    file_id: str
    original_name: str
    stored_path: str
    file_size: int
    mime_type: str
    created_at: datetime
    last_accessed: datetime
    checksum: str
    tags: List[str]
    custom_metadata: Dict[str, Any]


class FileManager:
    """
    Advanced file storage and management system
    Provides secure, organized file storage with metadata tracking
    """
    
    def __init__(self, base_path: Optional[str] = None):
        """Initialize file manager"""
        self.base_path = Path(base_path or settings.data_dir)
        self.upload_dir = self.base_path / "uploads"
        self.temp_dir = self.base_path / "temp"
        self.output_dir = self.base_path / "output"
        
        # File registry
        self._file_registry: Dict[str, FileMetadata] = {}
        self._registry_file = self.base_path / "file_registry.json"
        
        # Ensure directories exist
        asyncio.create_task(self._initialize_directories())
        
        logger.info(f"📁 File Manager initialized - base path: {self.base_path}")
    
    async def _initialize_directories(self):
        """Create necessary directories"""
        directories = [self.base_path, self.upload_dir, self.temp_dir, self.output_dir]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Load existing registry
        await self._load_registry()
    
    async def store_file(
        self, 
        file_data: bytes, 
        filename: str,
        file_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
        tags: Optional[List[str]] = None
    ) -> FileMetadata:
        """
        Store file with metadata
        
        Args:
            file_data: File content bytes
            filename: Original filename
            file_id: Optional custom file ID
            metadata: Custom metadata
            tags: File tags for organization
            
        Returns:
            FileMetadata object
        """
        if not file_id:
            file_id = self._generate_file_id(file_data, filename)
        
        metadata = metadata or {}
        tags = tags or []
        
        logger.info(f"💾 Storing file: {filename} ({len(file_data)} bytes)")
        
        # Generate storage path
        storage_path = self._get_storage_path(file_id, filename)
        
        # Calculate checksum
        checksum = hashlib.sha256(file_data).hexdigest()
        
        # Store file
        async with aiofiles.open(storage_path, 'wb') as f:
            await f.write(file_data)
        
        # Create metadata
        file_metadata = FileMetadata(
            file_id=file_id,
            original_name=filename,
            stored_path=str(storage_path),
            file_size=len(file_data),
            mime_type=self._detect_mime_type(filename),
            created_at=datetime.utcnow(),
            last_accessed=datetime.utcnow(),
            checksum=checksum,
            tags=tags,
            custom_metadata=metadata
        )
        
        # Register file
        self._file_registry[file_id] = file_metadata
        await self._save_registry()
        
        logger.info(f"✅ File stored successfully: {file_id}")
        return file_metadata
    
    async def get_file(self, file_id: str) -> Optional[bytes]:
        """Get file content by ID"""
        if file_id not in self._file_registry:
            return None
        
        file_metadata = self._file_registry[file_id]
        
        try:
            async with aiofiles.open(file_metadata.stored_path, 'rb') as f:
                content = await f.read()
            
            # Update last accessed
            file_metadata.last_accessed = datetime.utcnow()
            await self._save_registry()
            
            logger.debug(f"📖 File retrieved: {file_id}")
            return content
            
        except FileNotFoundError:
            logger.error(f"❌ File not found on disk: {file_id}")
            # Remove from registry if file doesn't exist
            del self._file_registry[file_id]
            await self._save_registry()
            return None
    
    async def get_file_path(self, file_id: str) -> Optional[str]:
        """Get file path by ID"""
        if file_id not in self._file_registry:
            return None
        
        file_metadata = self._file_registry[file_id]
        
        if os.path.exists(file_metadata.stored_path):
            file_metadata.last_accessed = datetime.utcnow()
            await self._save_registry()
            return file_metadata.stored_path
        
        return None
    
    async def get_file_metadata(self, file_id: str) -> Optional[FileMetadata]:
        """Get file metadata by ID"""
        return self._file_registry.get(file_id)
    
    async def update_file_metadata(
        self, 
        file_id: str, 
        metadata: Optional[Dict] = None,
        tags: Optional[List[str]] = None
    ) -> bool:
        """Update file metadata"""
        if file_id not in self._file_registry:
            return False
        
        file_metadata = self._file_registry[file_id]
        
        if metadata:
            file_metadata.custom_metadata.update(metadata)
        
        if tags is not None:
            file_metadata.tags = tags
        
        await self._save_registry()
        logger.debug(f"📝 File metadata updated: {file_id}")
        return True
    
    async def delete_file(self, file_id: str) -> bool:
        """Delete file and metadata"""
        if file_id not in self._file_registry:
            return False
        
        file_metadata = self._file_registry[file_id]
        
        try:
            # Remove file from disk
            if os.path.exists(file_metadata.stored_path):
                os.remove(file_metadata.stored_path)
            
            # Remove from registry
            del self._file_registry[file_id]
            await self._save_registry()
            
            logger.info(f"🗑️ File deleted: {file_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error deleting file {file_id}: {e}")
            return False
    
    async def list_files(
        self, 
        tags: Optional[List[str]] = None,
        metadata_filter: Optional[Dict] = None,
        limit: Optional[int] = None
    ) -> List[FileMetadata]:
        """List files with optional filtering"""
        files = list(self._file_registry.values())
        
        # Filter by tags
        if tags:
            files = [f for f in files if any(tag in f.tags for tag in tags)]
        
        # Filter by metadata
        if metadata_filter:
            filtered_files = []
            for file_meta in files:
                match = True
                for key, value in metadata_filter.items():
                    if key not in file_meta.custom_metadata or file_meta.custom_metadata[key] != value:
                        match = False
                        break
                if match:
                    filtered_files.append(file_meta)
            files = filtered_files
        
        # Sort by creation date (newest first)
        files.sort(key=lambda f: f.created_at, reverse=True)
        
        # Apply limit
        if limit:
            files = files[:limit]
        
        return files
    
    async def cleanup_old_files(self, max_age_days: int = 30) -> int:
        """Clean up files older than specified days"""
        cutoff_date = datetime.utcnow() - timedelta(days=max_age_days)
        cleanup_count = 0
        
        files_to_delete = []
        for file_id, file_metadata in self._file_registry.items():
            if file_metadata.created_at < cutoff_date:
                files_to_delete.append(file_id)
        
        for file_id in files_to_delete:
            if await self.delete_file(file_id):
                cleanup_count += 1
        
        if cleanup_count > 0:
            logger.info(f"🧹 Cleaned up {cleanup_count} old files")
        
        return cleanup_count
    
    async def cleanup_orphaned_files(self) -> int:
        """Clean up files that exist on disk but not in registry"""
        cleanup_count = 0
        
        # Check upload directory
        if self.upload_dir.exists():
            for file_path in self.upload_dir.rglob('*'):
                if file_path.is_file():
                    # Check if file is registered
                    registered = any(
                        Path(meta.stored_path) == file_path 
                        for meta in self._file_registry.values()
                    )
                    
                    if not registered:
                        try:
                            file_path.unlink()
                            cleanup_count += 1
                            logger.debug(f"🗑️ Removed orphaned file: {file_path}")
                        except Exception as e:
                            logger.warning(f"⚠️ Could not remove orphaned file {file_path}: {e}")
        
        if cleanup_count > 0:
            logger.info(f"🧹 Cleaned up {cleanup_count} orphaned files")
        
        return cleanup_count
    
    async def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        total_files = len(self._file_registry)
        total_size = sum(meta.file_size for meta in self._file_registry.values())
        
        # Get disk usage
        upload_size = self._get_directory_size(self.upload_dir)
        temp_size = self._get_directory_size(self.temp_dir)
        output_size = self._get_directory_size(self.output_dir)
        
        return {
            'registered_files': total_files,
            'total_registered_size': total_size,
            'upload_directory_size': upload_size,
            'temp_directory_size': temp_size,
            'output_directory_size': output_size,
            'total_disk_usage': upload_size + temp_size + output_size
        }
    
    async def verify_file_integrity(self, file_id: str) -> bool:
        """Verify file integrity using checksum"""
        if file_id not in self._file_registry:
            return False
        
        file_metadata = self._file_registry[file_id]
        
        try:
            async with aiofiles.open(file_metadata.stored_path, 'rb') as f:
                content = await f.read()
            
            current_checksum = hashlib.sha256(content).hexdigest()
            return current_checksum == file_metadata.checksum
            
        except Exception as e:
            logger.error(f"❌ Error verifying file integrity {file_id}: {e}")
            return False
    
    # Private methods
    
    def _generate_file_id(self, file_data: bytes, filename: str) -> str:
        """Generate unique file ID"""
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')[:-3]
        content_hash = hashlib.md5(file_data).hexdigest()[:8]
        return f"{timestamp}_{content_hash}"
    
    def _get_storage_path(self, file_id: str, filename: str) -> Path:
        """Get storage path for file"""
        # Organize by date for better file organization
        date_dir = datetime.utcnow().strftime('%Y/%m/%d')
        storage_dir = self.upload_dir / date_dir
        storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Use file_id as filename to avoid conflicts
        file_extension = Path(filename).suffix
        return storage_dir / f"{file_id}{file_extension}"
    
    def _detect_mime_type(self, filename: str) -> str:
        """Detect MIME type from filename"""
        import mimetypes
        mime_type, _ = mimetypes.guess_type(filename)
        return mime_type or 'application/octet-stream'
    
    def _get_directory_size(self, directory: Path) -> int:
        """Get total size of directory"""
        if not directory.exists():
            return 0
        
        total_size = 0
        for file_path in directory.rglob('*'):
            if file_path.is_file():
                try:
                    total_size += file_path.stat().st_size
                except (OSError, IOError):
                    pass
        
        return total_size
    
    async def _load_registry(self):
        """Load file registry from disk"""
        if not self._registry_file.exists():
            return
        
        try:
            async with aiofiles.open(self._registry_file, 'r') as f:
                data = await f.read()
                registry_data = json.loads(data)
            
            # Reconstruct FileMetadata objects
            for file_id, meta_dict in registry_data.items():
                self._file_registry[file_id] = FileMetadata(
                    file_id=meta_dict['file_id'],
                    original_name=meta_dict['original_name'],
                    stored_path=meta_dict['stored_path'],
                    file_size=meta_dict['file_size'],
                    mime_type=meta_dict['mime_type'],
                    created_at=datetime.fromisoformat(meta_dict['created_at']),
                    last_accessed=datetime.fromisoformat(meta_dict['last_accessed']),
                    checksum=meta_dict['checksum'],
                    tags=meta_dict['tags'],
                    custom_metadata=meta_dict['custom_metadata']
                )
            
            logger.info(f"📋 Loaded {len(self._file_registry)} files from registry")
            
        except Exception as e:
            logger.error(f"❌ Error loading file registry: {e}")
            self._file_registry = {}
    
    async def _save_registry(self):
        """Save file registry to disk"""
        try:
            registry_data = {}
            for file_id, metadata in self._file_registry.items():
                registry_data[file_id] = {
                    'file_id': metadata.file_id,
                    'original_name': metadata.original_name,
                    'stored_path': metadata.stored_path,
                    'file_size': metadata.file_size,
                    'mime_type': metadata.mime_type,
                    'created_at': metadata.created_at.isoformat(),
                    'last_accessed': metadata.last_accessed.isoformat(),
                    'checksum': metadata.checksum,
                    'tags': metadata.tags,
                    'custom_metadata': metadata.custom_metadata
                }
            
            async with aiofiles.open(self._registry_file, 'w') as f:
                await f.write(json.dumps(registry_data, indent=2))
            
        except Exception as e:
            logger.error(f"❌ Error saving file registry: {e}")
    
    async def move_file(self, file_id: str, destination_dir: str) -> bool:
        """Move file to different directory"""
        if file_id not in self._file_registry:
            return False
        
        file_metadata = self._file_registry[file_id]
        current_path = Path(file_metadata.stored_path)
        
        if not current_path.exists():
            return False
        
        # Create destination directory
        dest_dir = Path(destination_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        # New path
        new_path = dest_dir / current_path.name
        
        try:
            shutil.move(str(current_path), str(new_path))
            file_metadata.stored_path = str(new_path)
            await self._save_registry()
            
            logger.info(f"📦 File moved: {file_id} -> {new_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error moving file {file_id}: {e}")
            return False