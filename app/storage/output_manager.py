"""
Output File Management Mechanism (E3 - Data Storage Layer)
Comprehensive output file storage, organization, and lifecycle management
Implements SESE principle - Simple, Effective, Systematic, Exhaustive output handling
"""

import logging
import os
import shutil
import json
import mimetypes
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
import hashlib

from ..config import settings

logger = logging.getLogger(__name__)


class OutputFileType(Enum):
    """Output file types"""
    DOCX = "docx"
    PDF = "pdf"
    JSON = "json"
    TXT = "txt"
    ZIP = "zip"
    TEMP = "temp"


class OutputFileStatus(Enum):
    """Output file status"""
    PROCESSING = "processing"
    READY = "ready"
    DOWNLOADED = "downloaded"
    EXPIRED = "expired"
    ARCHIVED = "archived"
    ERROR = "error"


@dataclass
class OutputFileRecord:
    """Output file record"""
    file_id: str
    original_job_id: str
    file_type: OutputFileType
    filename: str
    file_path: str
    file_size: int
    status: OutputFileStatus = OutputFileStatus.PROCESSING
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    mime_type: str = ""
    checksum: str = ""
    download_count: int = 0
    last_downloaded: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)


@dataclass
class StorageQuota:
    """Storage quota information"""
    total_limit_bytes: int = 5 * 1024 * 1024 * 1024  # 5GB default
    used_bytes: int = 0
    file_count: int = 0
    warning_threshold: float = 0.8  # 80%
    critical_threshold: float = 0.95  # 95%


class OutputManager:
    """
    Output file management system
    Handles output file storage, organization, lifecycle, and cleanup
    """
    
    def __init__(self, output_dir: Optional[str] = None):
        """Initialize output manager"""
        self.output_dir = output_dir or settings.output_dir
        self.metadata_dir = os.path.join(self.output_dir, '.metadata')
        self.archive_dir = os.path.join(self.output_dir, '.archive')
        
        # File organization subdirectories
        self.subdirs = {
            OutputFileType.DOCX: 'documents',
            OutputFileType.PDF: 'pdfs',
            OutputFileType.JSON: 'data',
            OutputFileType.TXT: 'text',
            OutputFileType.ZIP: 'packages',
            OutputFileType.TEMP: 'temp'
        }
        
        # Ensure directories exist
        self._ensure_directories()
        
        # File registry
        self._output_files: Dict[str, OutputFileRecord] = {}
        
        # Storage quota tracking
        self.quota = StorageQuota()
        
        # Load existing files
        self._load_existing_files()
        
        # Update quota usage
        self._update_quota_usage()
        
        logger.info(f"📁 Output Manager initialized - {len(self._output_files)} files loaded")
    
    async def store_file(
        self,
        file_path: str,
        job_id: str,
        file_type: OutputFileType,
        filename: Optional[str] = None,
        metadata: Optional[Dict] = None,
        expires_in_hours: Optional[int] = None
    ) -> Optional[OutputFileRecord]:
        """
        Store output file with proper organization
        
        Args:
            file_path: Source file path
            job_id: Associated job ID
            file_type: Output file type
            filename: Custom filename (optional)
            metadata: Additional metadata
            expires_in_hours: Expiration time in hours
            
        Returns:
            OutputFileRecord if successful
        """
        if not os.path.exists(file_path):
            logger.error(f"❌ Source file not found: {file_path}")
            return None
        
        # Check storage quota
        file_size = os.path.getsize(file_path)
        if not self._check_storage_quota(file_size):
            logger.error("❌ Storage quota exceeded")
            return None
        
        try:
            # Generate file ID and determine storage path
            file_id = self._generate_file_id(job_id, file_type)
            
            if not filename:
                filename = os.path.basename(file_path)
            
            # Determine storage directory
            storage_dir = os.path.join(self.output_dir, self.subdirs[file_type])
            storage_path = os.path.join(storage_dir, f"{file_id}_{filename}")
            
            # Copy file to storage
            shutil.copy2(file_path, storage_path)
            
            # Calculate file metadata
            checksum = await self._calculate_checksum(storage_path)
            mime_type = mimetypes.guess_type(storage_path)[0] or 'application/octet-stream'
            
            # Set expiration
            expires_at = None
            if expires_in_hours:
                expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)
            
            # Create file record
            file_record = OutputFileRecord(
                file_id=file_id,
                original_job_id=job_id,
                file_type=file_type,
                filename=filename,
                file_path=storage_path,
                file_size=file_size,
                status=OutputFileStatus.READY,
                expires_at=expires_at,
                mime_type=mime_type,
                checksum=checksum,
                metadata=metadata or {}
            )
            
            # Save metadata
            await self._save_file_metadata(file_record)
            
            # Add to registry
            self._output_files[file_id] = file_record
            
            # Update quota
            self.quota.used_bytes += file_size
            self.quota.file_count += 1
            
            logger.info(f"💾 File stored: {file_id} ({file_type.value}, {file_size} bytes)")
            return file_record
            
        except Exception as e:
            logger.error(f"❌ Failed to store file: {e}")
            return None
    
    async def get_file(self, file_id: str) -> Optional[OutputFileRecord]:
        """Get file record by ID"""
        return self._output_files.get(file_id)
    
    async def get_file_path(self, file_id: str) -> Optional[str]:
        """Get file path by ID"""
        file_record = self._output_files.get(file_id)
        if file_record and os.path.exists(file_record.file_path):
            return file_record.file_path
        return None
    
    async def delete_file(self, file_id: str, permanent: bool = False) -> bool:
        """
        Delete output file
        
        Args:
            file_id: File ID
            permanent: If True, permanently delete; otherwise archive
            
        Returns:
            Success status
        """
        if file_id not in self._output_files:
            logger.error(f"❌ File not found: {file_id}")
            return False
        
        try:
            file_record = self._output_files[file_id]
            
            if permanent:
                # Remove physical file
                if os.path.exists(file_record.file_path):
                    os.remove(file_record.file_path)
                
                # Remove metadata
                await self._remove_file_metadata(file_id)
                
                # Update quota
                self.quota.used_bytes -= file_record.file_size
                self.quota.file_count -= 1
                
                # Remove from registry
                del self._output_files[file_id]
                
                logger.info(f"🗑️ File permanently deleted: {file_id}")
            else:
                # Archive file
                archive_success = await self._archive_file(file_record)
                if archive_success:
                    file_record.status = OutputFileStatus.ARCHIVED
                    await self._save_file_metadata(file_record)
                    logger.info(f"📦 File archived: {file_id}")
                else:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to delete file {file_id}: {e}")
            return False
    
    async def list_files(
        self,
        job_id: Optional[str] = None,
        file_type: Optional[OutputFileType] = None,
        status: Optional[OutputFileStatus] = None,
        limit: Optional[int] = None
    ) -> List[OutputFileRecord]:
        """
        List files with optional filtering
        
        Args:
            job_id: Filter by job ID
            file_type: Filter by file type
            status: Filter by status
            limit: Maximum number of results
            
        Returns:
            List of file records
        """
        files = list(self._output_files.values())
        
        # Apply filters
        if job_id:
            files = [f for f in files if f.original_job_id == job_id]
        
        if file_type:
            files = [f for f in files if f.file_type == file_type]
        
        if status:
            files = [f for f in files if f.status == status]
        
        # Sort by creation time (newest first)
        files.sort(key=lambda f: f.created_at, reverse=True)
        
        # Apply limit
        if limit:
            files = files[:limit]
        
        return files
    
    async def cleanup_expired_files(self) -> int:
        """Clean up expired files"""
        cleanup_count = 0
        current_time = datetime.utcnow()
        
        expired_files = []
        for file_id, file_record in self._output_files.items():
            if file_record.expires_at and current_time > file_record.expires_at:
                expired_files.append(file_id)
        
        for file_id in expired_files:
            success = await self.delete_file(file_id, permanent=False)
            if success:
                cleanup_count += 1
        
        if cleanup_count > 0:
            logger.info(f"🧹 Cleaned up {cleanup_count} expired files")
        
        return cleanup_count
    
    async def mark_downloaded(self, file_id: str) -> bool:
        """Mark file as downloaded"""
        if file_id not in self._output_files:
            return False
        
        try:
            file_record = self._output_files[file_id]
            file_record.download_count += 1
            file_record.last_downloaded = datetime.utcnow()
            file_record.status = OutputFileStatus.DOWNLOADED
            file_record.updated_at = datetime.utcnow()
            
            await self._save_file_metadata(file_record)
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to mark file as downloaded {file_id}: {e}")
            return False
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        # File type distribution
        type_counts = {}
        type_sizes = {}
        for file_type in OutputFileType:
            files = [f for f in self._output_files.values() if f.file_type == file_type]
            type_counts[file_type.value] = len(files)
            type_sizes[file_type.value] = sum(f.file_size for f in files)
        
        # Status distribution
        status_counts = {}
        for status in OutputFileStatus:
            status_counts[status.value] = sum(
                1 for f in self._output_files.values() if f.status == status
            )
        
        # Download statistics
        total_downloads = sum(f.download_count for f in self._output_files.values())
        
        # Storage quota
        quota_usage = self.quota.used_bytes / self.quota.total_limit_bytes if self.quota.total_limit_bytes > 0 else 0
        
        return {
            'total_files': len(self._output_files),
            'total_size_bytes': self.quota.used_bytes,
            'quota_usage_percent': quota_usage * 100,
            'quota_limit_bytes': self.quota.total_limit_bytes,
            'type_distribution': type_counts,
            'type_sizes': type_sizes,
            'status_distribution': status_counts,
            'total_downloads': total_downloads,
            'warning_threshold_reached': quota_usage >= self.quota.warning_threshold,
            'critical_threshold_reached': quota_usage >= self.quota.critical_threshold
        }
    
    # Private methods
    
    def _ensure_directories(self):
        """Ensure all required directories exist"""
        directories = [
            self.output_dir,
            self.metadata_dir,
            self.archive_dir
        ]
        
        # Add subdirectories
        for subdir in self.subdirs.values():
            directories.append(os.path.join(self.output_dir, subdir))
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    def _generate_file_id(self, job_id: str, file_type: OutputFileType) -> str:
        """Generate unique file ID"""
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        import uuid
        return f"{file_type.value}_{timestamp}_{job_id[:8]}_{str(uuid.uuid4())[:8]}"
    
    async def _calculate_checksum(self, file_path: str) -> str:
        """Calculate file SHA256 checksum"""
        hash_sha256 = hashlib.sha256()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            logger.error(f"❌ Failed to calculate checksum for {file_path}: {e}")
            return ""
    
    async def _save_file_metadata(self, file_record: OutputFileRecord):
        """Save file metadata to JSON"""
        metadata_file = os.path.join(self.metadata_dir, f"{file_record.file_id}.json")
        
        try:
            # Convert to serializable format
            metadata_dict = asdict(file_record)
            
            # Handle datetime objects
            for key, value in metadata_dict.items():
                if isinstance(value, datetime):
                    metadata_dict[key] = value.isoformat()
            
            # Handle enums
            metadata_dict['file_type'] = file_record.file_type.value
            metadata_dict['status'] = file_record.status.value
            
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata_dict, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"❌ Failed to save metadata for {file_record.file_id}: {e}")
    
    async def _remove_file_metadata(self, file_id: str):
        """Remove file metadata"""
        metadata_file = os.path.join(self.metadata_dir, f"{file_id}.json")
        if os.path.exists(metadata_file):
            os.remove(metadata_file)
    
    def _load_existing_files(self):
        """Load existing files from metadata"""
        if not os.path.exists(self.metadata_dir):
            return
        
        for metadata_file in os.listdir(self.metadata_dir):
            if metadata_file.endswith('.json'):
                try:
                    file_path = os.path.join(self.metadata_dir, metadata_file)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        metadata_dict = json.load(f)
                    
                    # Convert datetime strings back to datetime objects
                    datetime_fields = ['created_at', 'updated_at', 'expires_at', 'last_downloaded']
                    for field in datetime_fields:
                        if metadata_dict.get(field):
                            metadata_dict[field] = datetime.fromisoformat(metadata_dict[field])
                    
                    # Convert enum strings back to enums
                    metadata_dict['file_type'] = OutputFileType(metadata_dict['file_type'])
                    metadata_dict['status'] = OutputFileStatus(metadata_dict['status'])
                    
                    # Create file record
                    file_record = OutputFileRecord(**metadata_dict)
                    
                    # Verify file still exists
                    if os.path.exists(file_record.file_path):
                        self._output_files[file_record.file_id] = file_record
                    else:
                        # File missing, remove metadata
                        logger.warning(f"⚠️ File missing, removing metadata: {file_record.file_id}")
                        os.remove(file_path)
                        
                except Exception as e:
                    logger.warning(f"⚠️ Failed to load file metadata {metadata_file}: {e}")
    
    def _update_quota_usage(self):
        """Update storage quota usage"""
        total_size = sum(f.file_size for f in self._output_files.values())
        self.quota.used_bytes = total_size
        self.quota.file_count = len(self._output_files)
    
    def _check_storage_quota(self, additional_size: int) -> bool:
        """Check if additional file fits within storage quota"""
        projected_usage = self.quota.used_bytes + additional_size
        return projected_usage <= self.quota.total_limit_bytes
    
    async def _archive_file(self, file_record: OutputFileRecord) -> bool:
        """Archive file to archive directory"""
        try:
            # Create archive subdirectory if needed
            archive_subdir = os.path.join(self.archive_dir, file_record.file_type.value)
            os.makedirs(archive_subdir, exist_ok=True)
            
            # Generate archive filename with timestamp
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            archive_filename = f"{file_record.file_id}_{timestamp}_{file_record.filename}"
            archive_path = os.path.join(archive_subdir, archive_filename)
            
            # Move file to archive
            shutil.move(file_record.file_path, archive_path)
            
            # Update file record
            file_record.file_path = archive_path
            file_record.updated_at = datetime.utcnow()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to archive file {file_record.file_id}: {e}")
            return False