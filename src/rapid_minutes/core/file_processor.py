"""
File Processing Controller (B1 - Business Logic Layer)
Advanced file handling and processing coordination
Implements SESE principle - Simple, Effective, Systematic, Exhaustive file processing
"""

import asyncio
import logging
import os
import hashlib
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import aiofiles
import magic

from ..config import settings
from ..storage.file_manager import FileManager
from ..storage.temp_storage import TempStorage
from ..utils.validators import FileValidator
from ..ai.text_preprocessor import TextPreprocessor

logger = logging.getLogger(__name__)


class FileStatus(Enum):
    """File processing status"""
    UPLOADED = "uploaded"
    VALIDATING = "validating"
    VALID = "valid"
    INVALID = "invalid"
    PROCESSING = "processing"
    PROCESSED = "processed"
    ERROR = "error"
    EXPIRED = "expired"


class FileType(Enum):
    """Supported file types"""
    TEXT = "text/plain"
    TXT = "text/plain"
    DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    PDF = "application/pdf"
    UNKNOWN = "unknown"


@dataclass
class ProcessedFile:
    """Container for processed file information"""
    file_id: str
    original_name: str
    file_path: str
    file_type: FileType
    file_size: int
    mime_type: str
    encoding: Optional[str] = None
    status: FileStatus = FileStatus.UPLOADED
    upload_timestamp: datetime = field(default_factory=datetime.utcnow)
    processing_timestamp: Optional[datetime] = None
    content_hash: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    validation_results: Dict[str, bool] = field(default_factory=dict)
    processing_results: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None


@dataclass
class FileProcessingOptions:
    """File processing configuration options"""
    validate_content: bool = True
    extract_text: bool = True
    preprocess_text: bool = True
    detect_encoding: bool = True
    virus_scan: bool = False
    max_file_size: int = field(default_factory=lambda: settings.max_file_size_bytes)
    allowed_types: List[str] = field(default_factory=lambda: ['text/plain', 'application/pdf'])
    preserve_original: bool = True
    cleanup_after: timedelta = field(default_factory=lambda: timedelta(hours=24))


class FileProcessor:
    """
    Advanced file processing controller
    Handles file upload, validation, processing, and coordination with other system components
    """
    
    def __init__(
        self,
        file_manager: Optional[FileManager] = None,
        temp_storage: Optional[TempStorage] = None,
        text_preprocessor: Optional[TextPreprocessor] = None
    ):
        """Initialize file processor with dependencies"""
        self.file_manager = file_manager or FileManager()
        self.temp_storage = temp_storage or TempStorage()
        self.text_preprocessor = text_preprocessor or TextPreprocessor()
        self.file_validator = FileValidator()
        
        # Active processing tasks
        self._processing_tasks: Dict[str, asyncio.Task] = {}
        self._processed_files: Dict[str, ProcessedFile] = {}
        
        logger.info("📁 File Processor initialized")
    
    async def upload_file(
        self, 
        file_data: bytes, 
        filename: str,
        options: Optional[FileProcessingOptions] = None
    ) -> ProcessedFile:
        """
        Upload and process a file
        
        Args:
            file_data: Raw file data bytes
            filename: Original filename
            options: Processing options
            
        Returns:
            ProcessedFile object with processing results
        """
        options = options or FileProcessingOptions()
        
        logger.info(f"📤 Starting file upload: {filename} ({len(file_data)} bytes)")
        
        # Generate unique file ID
        file_id = self._generate_file_id(file_data, filename)
        
        # Create processed file object
        processed_file = ProcessedFile(
            file_id=file_id,
            original_name=filename,
            file_path="",  # Will be set after storage
            file_type=FileType.UNKNOWN,
            file_size=len(file_data),
            mime_type="unknown",
            status=FileStatus.UPLOADED
        )
        
        try:
            # Step 1: Initial validation
            processed_file.status = FileStatus.VALIDATING
            await self._validate_file_basic(processed_file, file_data, options)
            
            # Step 2: Store file temporarily
            temp_path = await self.temp_storage.store_file(file_id, file_data, filename)
            processed_file.file_path = temp_path
            
            # Step 3: Detailed validation and analysis
            await self._analyze_file(processed_file, options)
            
            # Step 4: Extract and preprocess content if text file
            if processed_file.file_type in [FileType.TEXT, FileType.TXT]:
                await self._process_text_file(processed_file, options)
            
            processed_file.status = FileStatus.VALID
            processed_file.processing_timestamp = datetime.utcnow()
            
            # Store in processed files registry
            self._processed_files[file_id] = processed_file
            
            logger.info(f"✅ File upload completed: {file_id}")
            return processed_file
            
        except Exception as e:
            processed_file.status = FileStatus.ERROR
            processed_file.error_message = str(e)
            logger.error(f"❌ File upload failed for {filename}: {e}")
            
            # Cleanup on error
            if processed_file.file_path:
                await self._cleanup_file(processed_file.file_path)
            
            return processed_file
    
    async def process_file_content(
        self, 
        file_id: str,
        processing_options: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Process file content for meeting minutes extraction
        
        Args:
            file_id: Unique file identifier
            processing_options: Additional processing options
            
        Returns:
            Processing results dictionary
        """
        if file_id not in self._processed_files:
            raise ValueError(f"File {file_id} not found or not uploaded")
        
        processed_file = self._processed_files[file_id]
        
        if processed_file.status != FileStatus.VALID:
            raise ValueError(f"File {file_id} is not in valid state for processing")
        
        logger.info(f"🔄 Processing file content: {file_id}")
        
        try:
            processed_file.status = FileStatus.PROCESSING
            
            # Read file content
            content = await self._read_file_content(processed_file)
            
            # Preprocess text content
            if processed_file.file_type in [FileType.TEXT, FileType.TXT]:
                preprocessing_result = await self.text_preprocessor.preprocess(
                    content, processing_options
                )
                
                processing_results = {
                    'original_content': content,
                    'preprocessed_content': preprocessing_result.cleaned_text,
                    'segments': preprocessing_result.segments,
                    'preprocessing_metadata': preprocessing_result.metadata,
                    'preprocessing_stats': preprocessing_result.preprocessing_stats
                }
            else:
                # For non-text files, return raw content
                processing_results = {
                    'original_content': content,
                    'content_type': 'binary',
                    'message': 'Binary content - preprocessing not applicable'
                }
            
            processed_file.processing_results = processing_results
            processed_file.status = FileStatus.PROCESSED
            
            logger.info(f"✅ File processing completed: {file_id}")
            return processing_results
            
        except Exception as e:
            processed_file.status = FileStatus.ERROR
            processed_file.error_message = str(e)
            logger.error(f"❌ File processing failed for {file_id}: {e}")
            raise
    
    async def get_file_status(self, file_id: str) -> Optional[ProcessedFile]:
        """Get file processing status"""
        return self._processed_files.get(file_id)
    
    async def get_file_content(self, file_id: str) -> Optional[str]:
        """Get processed file content"""
        if file_id not in self._processed_files:
            return None
        
        processed_file = self._processed_files[file_id]
        
        if processed_file.status == FileStatus.PROCESSED:
            return processed_file.processing_results.get('preprocessed_content')
        
        # If not processed, read raw content
        return await self._read_file_content(processed_file)
    
    async def cleanup_expired_files(self) -> int:
        """Clean up expired files based on retention policy"""
        cleanup_count = 0
        current_time = datetime.utcnow()
        
        expired_files = []
        for file_id, processed_file in self._processed_files.items():
            age = current_time - processed_file.upload_timestamp
            
            # Default cleanup after 24 hours
            if age > timedelta(hours=24):
                expired_files.append(file_id)
        
        for file_id in expired_files:
            await self.remove_file(file_id)
            cleanup_count += 1
        
        if cleanup_count > 0:
            logger.info(f"🧹 Cleaned up {cleanup_count} expired files")
        
        return cleanup_count
    
    async def remove_file(self, file_id: str) -> bool:
        """Remove file and cleanup resources"""
        if file_id not in self._processed_files:
            return False
        
        processed_file = self._processed_files[file_id]
        
        try:
            # Cleanup file storage
            if processed_file.file_path:
                await self._cleanup_file(processed_file.file_path)
            
            # Cancel any ongoing processing task
            if file_id in self._processing_tasks:
                self._processing_tasks[file_id].cancel()
                del self._processing_tasks[file_id]
            
            # Remove from registry
            del self._processed_files[file_id]
            
            logger.info(f"🗑️ File removed: {file_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error removing file {file_id}: {e}")
            return False
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get file processing statistics"""
        total_files = len(self._processed_files)
        
        status_counts = {}
        for status in FileStatus:
            status_counts[status.value] = sum(
                1 for f in self._processed_files.values() if f.status == status
            )
        
        total_size = sum(f.file_size for f in self._processed_files.values())
        
        return {
            'total_files': total_files,
            'status_distribution': status_counts,
            'total_size_bytes': total_size,
            'active_processing_tasks': len(self._processing_tasks),
            'memory_usage_estimate': total_size * 1.5  # Rough estimate
        }
    
    # Private methods
    
    def _generate_file_id(self, file_data: bytes, filename: str) -> str:
        """Generate unique file ID"""
        content_hash = hashlib.sha256(file_data).hexdigest()
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        return f"{timestamp}_{content_hash[:8]}"
    
    async def _validate_file_basic(
        self, 
        processed_file: ProcessedFile, 
        file_data: bytes, 
        options: FileProcessingOptions
    ):
        """Basic file validation"""
        # Check file size
        if len(file_data) > options.max_file_size:
            raise ValueError(f"File too large: {len(file_data)} bytes > {options.max_file_size}")
        
        if len(file_data) == 0:
            raise ValueError("Empty file not allowed")
        
        # Detect MIME type
        mime_type = magic.from_buffer(file_data, mime=True)
        processed_file.mime_type = mime_type
        
        # Map to file type
        processed_file.file_type = self._map_mime_to_file_type(mime_type)
        
        # Check allowed types
        if mime_type not in options.allowed_types:
            raise ValueError(f"File type not allowed: {mime_type}")
        
        # Generate content hash
        processed_file.content_hash = hashlib.sha256(file_data).hexdigest()
        
        processed_file.validation_results['basic_validation'] = True
    
    def _map_mime_to_file_type(self, mime_type: str) -> FileType:
        """Map MIME type to FileType enum"""
        mime_to_type = {
            'text/plain': FileType.TEXT,
            'application/pdf': FileType.PDF,
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': FileType.DOCX
        }
        
        return mime_to_type.get(mime_type, FileType.UNKNOWN)
    
    async def _analyze_file(self, processed_file: ProcessedFile, options: FileProcessingOptions):
        """Detailed file analysis"""
        try:
            # Detect encoding for text files
            if processed_file.file_type in [FileType.TEXT, FileType.TXT] and options.detect_encoding:
                encoding = await self._detect_encoding(processed_file.file_path)
                processed_file.encoding = encoding
            
            # Additional metadata
            file_stat = os.stat(processed_file.file_path)
            processed_file.metadata.update({
                'file_size': file_stat.st_size,
                'created_time': datetime.fromtimestamp(file_stat.st_ctime).isoformat(),
                'modified_time': datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                'mime_type_detected': processed_file.mime_type,
                'encoding': processed_file.encoding
            })
            
            processed_file.validation_results['detailed_analysis'] = True
            
        except Exception as e:
            logger.warning(f"⚠️ File analysis warning: {e}")
            processed_file.validation_results['detailed_analysis'] = False
    
    async def _process_text_file(self, processed_file: ProcessedFile, options: FileProcessingOptions):
        """Process text file content"""
        if not options.extract_text:
            return
        
        try:
            # Read content
            content = await self._read_file_content(processed_file)
            
            # Basic content validation
            if not content or len(content.strip()) == 0:
                raise ValueError("File contains no readable text content")
            
            # Store basic content info
            processed_file.metadata.update({
                'content_length': len(content),
                'line_count': len(content.splitlines()),
                'word_count': len(content.split()),
                'char_count': len(content)
            })
            
            processed_file.validation_results['text_processing'] = True
            
        except Exception as e:
            logger.warning(f"⚠️ Text processing warning: {e}")
            processed_file.validation_results['text_processing'] = False
    
    async def _read_file_content(self, processed_file: ProcessedFile) -> str:
        """Read file content with proper encoding"""
        encoding = processed_file.encoding or 'utf-8'
        
        try:
            async with aiofiles.open(processed_file.file_path, 'r', encoding=encoding) as f:
                return await f.read()
        except UnicodeDecodeError:
            # Try alternative encodings
            for alt_encoding in ['latin1', 'cp1252', 'iso-8859-1']:
                try:
                    async with aiofiles.open(processed_file.file_path, 'r', encoding=alt_encoding) as f:
                        content = await f.read()
                        processed_file.encoding = alt_encoding
                        logger.info(f"📄 Successfully read file with {alt_encoding} encoding")
                        return content
                except UnicodeDecodeError:
                    continue
            
            raise ValueError("Unable to decode file with any supported encoding")
    
    async def _detect_encoding(self, file_path: str) -> Optional[str]:
        """Detect file encoding"""
        import chardet
        
        try:
            async with aiofiles.open(file_path, 'rb') as f:
                raw_data = await f.read(10000)  # Read first 10KB
                result = chardet.detect(raw_data)
                return result.get('encoding')
        except Exception as e:
            logger.warning(f"⚠️ Encoding detection failed: {e}")
            return None
    
    async def _cleanup_file(self, file_path: str):
        """Clean up file from storage"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.debug(f"🗑️ Cleaned up file: {file_path}")
        except Exception as e:
            logger.warning(f"⚠️ Cleanup warning: {e}")
    
    async def get_supported_file_types(self) -> List[Dict[str, str]]:
        """Get list of supported file types"""
        return [
            {
                'mime_type': 'text/plain',
                'extension': '.txt',
                'description': 'Plain text files',
                'max_size': f"{settings.max_file_size_mb}MB"
            },
            {
                'mime_type': 'application/pdf',
                'extension': '.pdf', 
                'description': 'PDF documents (text extraction)',
                'max_size': f"{settings.max_file_size_mb}MB"
            }
        ]