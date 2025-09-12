"""
Output Management Controller (B4 - Business Logic Layer)
Comprehensive output file management and download coordination
Implements SESE principle - Simple, Effective, Systematic, Exhaustive output handling
"""

import logging
import os
import shutil
import zipfile
from typing import Dict, List, Optional, Union, Any, BinaryIO
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
import json
import mimetypes

from ..config import settings
from ..storage.output_manager import OutputManager as StorageOutputManager
from ..storage.temp_storage import TempStorage

logger = logging.getLogger(__name__)


class OutputFormat(Enum):
    """Supported output formats"""
    DOCX = "docx"
    PDF = "pdf"
    JSON = "json"
    TXT = "txt"
    ZIP = "zip"


class OutputStatus(Enum):
    """Output file status"""
    GENERATING = "generating"
    READY = "ready"
    DOWNLOADING = "downloading"
    EXPIRED = "expired"
    ERROR = "error"


@dataclass
class OutputFile:
    """Output file information"""
    file_id: str
    original_job_id: str
    filename: str
    file_path: str
    format: OutputFormat
    file_size: int
    status: OutputStatus = OutputStatus.GENERATING
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    download_count: int = 0
    last_downloaded: Optional[datetime] = None
    mime_type: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    checksum: Optional[str] = None


@dataclass
class DownloadSession:
    """Download session tracking"""
    session_id: str
    file_id: str
    user_id: Optional[str] = None
    started_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime = field(default_factory=lambda: datetime.utcnow() + timedelta(hours=1))
    download_url: Optional[str] = None
    is_active: bool = True


@dataclass
class BatchDownload:
    """Batch download package"""
    batch_id: str
    file_ids: List[str]
    package_path: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    status: OutputStatus = OutputStatus.GENERATING
    file_count: int = 0
    total_size: int = 0


class OutputController:
    """
    Output management controller
    Handles file generation, storage, download, and cleanup operations
    """
    
    def __init__(
        self,
        storage_manager: Optional[StorageOutputManager] = None,
        temp_storage: Optional[TempStorage] = None,
        default_expiry_hours: int = 24
    ):
        """Initialize output controller"""
        self.storage_manager = storage_manager or StorageOutputManager()
        self.temp_storage = temp_storage or TempStorage()
        self.default_expiry_hours = default_expiry_hours
        
        # File registry
        self._output_files: Dict[str, OutputFile] = {}
        self._download_sessions: Dict[str, DownloadSession] = {}
        self._batch_downloads: Dict[str, BatchDownload] = {}
        
        # Ensure output directories exist
        self._ensure_directories()
        
        logger.info("📤 Output Controller initialized")
    
    async def register_output_file(
        self,
        job_id: str,
        file_path: str,
        format: OutputFormat,
        original_filename: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> OutputFile:
        """
        Register a generated output file
        
        Args:
            job_id: Original processing job ID
            file_path: Path to generated file
            format: Output format
            original_filename: Original filename if different
            metadata: Additional file metadata
            
        Returns:
            OutputFile object
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Output file not found: {file_path}")
        
        # Generate unique file ID
        file_id = self._generate_file_id(job_id, format)
        
        # Get file information
        file_size = os.path.getsize(file_path)
        filename = original_filename or os.path.basename(file_path)
        mime_type = mimetypes.guess_type(file_path)[0] or self._get_mime_type_by_format(format)
        
        # Calculate expiry time
        expires_at = datetime.utcnow() + timedelta(hours=self.default_expiry_hours)
        
        # Generate checksum
        checksum = await self._calculate_checksum(file_path)
        
        # Create output file record
        output_file = OutputFile(
            file_id=file_id,
            original_job_id=job_id,
            filename=filename,
            file_path=file_path,
            format=format,
            file_size=file_size,
            status=OutputStatus.READY,
            expires_at=expires_at,
            mime_type=mime_type,
            checksum=checksum,
            metadata=metadata or {}
        )
        
        # Store in registry
        self._output_files[file_id] = output_file
        
        logger.info(f"📄 Output file registered: {file_id} ({format.value}, {file_size} bytes)")
        return output_file
    
    async def get_file_info(self, file_id: str) -> Optional[OutputFile]:
        """Get output file information"""
        return self._output_files.get(file_id)
    
    async def create_download_session(
        self,
        file_id: str,
        user_id: Optional[str] = None
    ) -> Optional[DownloadSession]:
        """
        Create a download session for a file
        
        Args:
            file_id: Output file ID
            user_id: User requesting download
            
        Returns:
            DownloadSession or None if file not found/expired
        """
        if file_id not in self._output_files:
            return None
        
        output_file = self._output_files[file_id]
        
        # Check if file is still available
        if output_file.status != OutputStatus.READY:
            return None
        
        if output_file.expires_at and datetime.utcnow() > output_file.expires_at:
            output_file.status = OutputStatus.EXPIRED
            return None
        
        # Generate session ID
        session_id = self._generate_session_id()
        
        # Create download session
        session = DownloadSession(
            session_id=session_id,
            file_id=file_id,
            user_id=user_id,
            download_url=f"/api/download/{session_id}"
        )
        
        self._download_sessions[session_id] = session
        
        logger.info(f"🔗 Download session created: {session_id} for file: {file_id}")
        return session
    
    async def download_file(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Download file using session ID
        
        Returns:
            Dictionary with file info and binary data
        """
        if session_id not in self._download_sessions:
            return None
        
        session = self._download_sessions[session_id]
        
        # Check session validity
        if not session.is_active or datetime.utcnow() > session.expires_at:
            session.is_active = False
            return None
        
        if session.file_id not in self._output_files:
            return None
        
        output_file = self._output_files[session.file_id]
        
        # Check file status
        if output_file.status != OutputStatus.READY:
            return None
        
        if not os.path.exists(output_file.file_path):
            output_file.status = OutputStatus.ERROR
            return None
        
        try:
            # Read file content
            with open(output_file.file_path, 'rb') as f:
                file_content = f.read()
            
            # Update download statistics
            output_file.download_count += 1
            output_file.last_downloaded = datetime.utcnow()
            output_file.status = OutputStatus.DOWNLOADING
            
            logger.info(f"📥 File downloaded: {session.file_id} (session: {session_id})")
            
            return {
                'filename': output_file.filename,
                'content': file_content,
                'mime_type': output_file.mime_type,
                'file_size': output_file.file_size,
                'format': output_file.format.value
            }
            
        except Exception as e:
            logger.error(f"❌ Download failed for session {session_id}: {e}")
            output_file.status = OutputStatus.ERROR
            return None
        finally:
            # Mark file as ready again after download
            if output_file.status == OutputStatus.DOWNLOADING:
                output_file.status = OutputStatus.READY
    
    async def create_batch_download(
        self,
        file_ids: List[str],
        batch_name: Optional[str] = None
    ) -> Optional[BatchDownload]:
        """
        Create batch download package
        
        Args:
            file_ids: List of file IDs to include
            batch_name: Custom batch name
            
        Returns:
            BatchDownload object
        """
        # Validate file IDs
        valid_files = []
        total_size = 0
        
        for file_id in file_ids:
            if file_id in self._output_files:
                output_file = self._output_files[file_id]
                if output_file.status == OutputStatus.READY:
                    valid_files.append(output_file)
                    total_size += output_file.file_size
        
        if not valid_files:
            return None
        
        # Generate batch ID
        batch_id = self._generate_batch_id()
        
        # Create batch download
        batch = BatchDownload(
            batch_id=batch_id,
            file_ids=file_ids,
            file_count=len(valid_files),
            total_size=total_size
        )
        
        try:
            # Create ZIP package
            zip_filename = batch_name or f"batch_download_{batch_id}.zip"
            zip_path = os.path.join(settings.output_dir, zip_filename)
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for output_file in valid_files:
                    if os.path.exists(output_file.file_path):
                        zipf.write(output_file.file_path, output_file.filename)
            
            batch.package_path = zip_path
            batch.status = OutputStatus.READY
            
            # Register batch
            self._batch_downloads[batch_id] = batch
            
            logger.info(f"📦 Batch download created: {batch_id} ({len(valid_files)} files, {total_size} bytes)")
            return batch
            
        except Exception as e:
            batch.status = OutputStatus.ERROR
            logger.error(f"❌ Batch download creation failed: {e}")
            return batch
    
    async def convert_format(
        self,
        file_id: str,
        target_format: OutputFormat
    ) -> Optional[OutputFile]:
        """
        Convert output file to different format
        
        Args:
            file_id: Source file ID
            target_format: Target output format
            
        Returns:
            New OutputFile for converted format
        """
        if file_id not in self._output_files:
            return None
        
        source_file = self._output_files[file_id]
        
        # Check if conversion is supported
        if not self._is_conversion_supported(source_file.format, target_format):
            logger.warning(f"⚠️ Conversion not supported: {source_file.format.value} -> {target_format.value}")
            return None
        
        try:
            # Perform conversion based on format
            if target_format == OutputFormat.PDF and source_file.format == OutputFormat.DOCX:
                converted_path = await self._convert_docx_to_pdf(source_file.file_path)
            elif target_format == OutputFormat.TXT:
                converted_path = await self._extract_text_content(source_file.file_path)
            elif target_format == OutputFormat.JSON:
                converted_path = await self._export_to_json(source_file)
            else:
                return None
            
            if not converted_path:
                return None
            
            # Register converted file
            converted_filename = self._change_file_extension(source_file.filename, target_format)
            converted_file = await self.register_output_file(
                source_file.original_job_id,
                converted_path,
                target_format,
                converted_filename,
                {
                    'converted_from': source_file.file_id,
                    'original_format': source_file.format.value
                }
            )
            
            logger.info(f"🔄 File converted: {file_id} -> {converted_file.file_id} ({target_format.value})")
            return converted_file
            
        except Exception as e:
            logger.error(f"❌ Format conversion failed: {file_id} -> {target_format.value}: {e}")
            return None
    
    async def cleanup_expired_files(self) -> int:
        """Clean up expired output files"""
        cleanup_count = 0
        current_time = datetime.utcnow()
        
        expired_files = []
        for file_id, output_file in self._output_files.items():
            if output_file.expires_at and current_time > output_file.expires_at:
                expired_files.append(file_id)
        
        for file_id in expired_files:
            await self.remove_file(file_id)
            cleanup_count += 1
        
        # Cleanup expired download sessions
        expired_sessions = []
        for session_id, session in self._download_sessions.items():
            if current_time > session.expires_at:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del self._download_sessions[session_id]
        
        if cleanup_count > 0:
            logger.info(f"🧹 Cleaned up {cleanup_count} expired files and {len(expired_sessions)} sessions")
        
        return cleanup_count
    
    async def remove_file(self, file_id: str) -> bool:
        """Remove output file and cleanup resources"""
        if file_id not in self._output_files:
            return False
        
        output_file = self._output_files[file_id]
        
        try:
            # Remove physical file
            if os.path.exists(output_file.file_path):
                os.remove(output_file.file_path)
            
            # Remove from registry
            del self._output_files[file_id]
            
            # Clean up related download sessions
            expired_sessions = [
                session_id for session_id, session in self._download_sessions.items()
                if session.file_id == file_id
            ]
            for session_id in expired_sessions:
                del self._download_sessions[session_id]
            
            logger.info(f"🗑️ Output file removed: {file_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error removing file {file_id}: {e}")
            return False
    
    def get_output_statistics(self) -> Dict[str, Any]:
        """Get output management statistics"""
        total_files = len(self._output_files)
        
        # Status distribution
        status_counts = {}
        for status in OutputStatus:
            status_counts[status.value] = sum(
                1 for f in self._output_files.values() if f.status == status
            )
        
        # Format distribution
        format_counts = {}
        for format in OutputFormat:
            format_counts[format.value] = sum(
                1 for f in self._output_files.values() if f.format == format
            )
        
        # Storage usage
        total_size = sum(f.file_size for f in self._output_files.values())
        
        # Download statistics
        total_downloads = sum(f.download_count for f in self._output_files.values())
        
        return {
            'total_files': total_files,
            'status_distribution': status_counts,
            'format_distribution': format_counts,
            'total_storage_bytes': total_size,
            'total_downloads': total_downloads,
            'active_download_sessions': len(self._download_sessions),
            'batch_downloads': len(self._batch_downloads)
        }
    
    # Private methods
    
    def _generate_file_id(self, job_id: str, format: OutputFormat) -> str:
        """Generate unique file ID"""
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        import uuid
        return f"out_{timestamp}_{job_id[:8]}_{format.value}_{str(uuid.uuid4())[:8]}"
    
    def _generate_session_id(self) -> str:
        """Generate download session ID"""
        import uuid
        return f"dl_{str(uuid.uuid4())[:16]}"
    
    def _generate_batch_id(self) -> str:
        """Generate batch download ID"""
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        import uuid
        return f"batch_{timestamp}_{str(uuid.uuid4())[:8]}"
    
    async def _calculate_checksum(self, file_path: str) -> str:
        """Calculate file checksum"""
        import hashlib
        try:
            with open(file_path, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception:
            return ""
    
    def _get_mime_type_by_format(self, format: OutputFormat) -> str:
        """Get MIME type by format"""
        mime_types = {
            OutputFormat.DOCX: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            OutputFormat.PDF: 'application/pdf',
            OutputFormat.JSON: 'application/json',
            OutputFormat.TXT: 'text/plain',
            OutputFormat.ZIP: 'application/zip'
        }
        return mime_types.get(format, 'application/octet-stream')
    
    def _is_conversion_supported(self, source: OutputFormat, target: OutputFormat) -> bool:
        """Check if format conversion is supported"""
        supported_conversions = {
            OutputFormat.DOCX: [OutputFormat.PDF, OutputFormat.TXT],
            OutputFormat.JSON: [OutputFormat.TXT],
        }
        return target in supported_conversions.get(source, [])
    
    def _change_file_extension(self, filename: str, target_format: OutputFormat) -> str:
        """Change file extension based on target format"""
        name, _ = os.path.splitext(filename)
        return f"{name}.{target_format.value}"
    
    def _ensure_directories(self):
        """Ensure required directories exist"""
        directories = [
            settings.output_dir,
            settings.temp_dir,
            os.path.join(settings.output_dir, 'batches')
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    # Conversion methods (placeholder implementations)
    
    async def _convert_docx_to_pdf(self, docx_path: str) -> Optional[str]:
        """Convert DOCX to PDF"""
        # Placeholder - would integrate with PDF conversion library
        logger.info(f"🔄 Converting DOCX to PDF: {docx_path}")
        # Implementation would go here
        return None
    
    async def _extract_text_content(self, file_path: str) -> Optional[str]:
        """Extract text content from document"""
        # Placeholder - would extract text content
        logger.info(f"📝 Extracting text content: {file_path}")
        # Implementation would go here
        return None
    
    async def _export_to_json(self, output_file: OutputFile) -> Optional[str]:
        """Export metadata to JSON"""
        try:
            json_data = {
                'file_info': {
                    'filename': output_file.filename,
                    'format': output_file.format.value,
                    'file_size': output_file.file_size,
                    'created_at': output_file.created_at.isoformat(),
                    'checksum': output_file.checksum
                },
                'metadata': output_file.metadata
            }
            
            json_path = output_file.file_path.replace('.docx', '.json').replace('.pdf', '.json')
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            
            return json_path
            
        except Exception as e:
            logger.error(f"❌ JSON export failed: {e}")
            return None