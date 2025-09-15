"""
Download API Endpoint (P03 - API Layer)
Secure file download with session management and format conversion
Implements ICE principle - Intuitive download interface with comprehensive file handling
"""

import logging
from typing import Dict, List, Optional, Any, TYPE_CHECKING
from fastapi import APIRouter, HTTPException, Depends, Query, Response
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
import os
import io
from datetime import datetime

from ..core.output_manager import OutputController, OutputFormat
from ..document.pdf_generator import PDFGenerator, PDFGenerationOptions
from ..storage.output_manager import OutputManager
from ..config import settings

# 延遲導入避免循環依賴
if TYPE_CHECKING:
    from ..core.template_controller import TemplateController, TemplateType

logger = logging.getLogger(__name__)

# API Router
router = APIRouter(prefix="/api/download", tags=["download"])

# Pydantic models
class DownloadResponse(BaseModel):
    """Download response model"""
    success: bool
    download_url: Optional[str] = None
    session_id: Optional[str] = None
    file_info: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class BatchDownloadRequest(BaseModel):
    """Batch download request model"""
    file_ids: List[str] = Field(..., description="List of file IDs to download")
    package_name: Optional[str] = Field(None, description="Custom package name")
    format: str = Field(default="zip", description="Package format")


class BatchDownloadResponse(BaseModel):
    """Batch download response model"""
    success: bool
    batch_id: Optional[str] = None
    download_url: Optional[str] = None
    file_count: int = 0
    total_size: int = 0
    error: Optional[str] = None


class ConversionRequest(BaseModel):
    """Format conversion request model"""
    source_file_id: str = Field(..., description="Source file ID")
    target_format: OutputFormat = Field(..., description="Target format")
    conversion_options: Dict[str, Any] = Field(default_factory=dict, description="Conversion options")


class ConversionResponse(BaseModel):
    """Format conversion response model"""
    success: bool
    converted_file_id: Optional[str] = None
    download_url: Optional[str] = None
    conversion_info: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# Dependency injection
def get_output_controller() -> OutputController:
    """Get output controller instance"""
    return OutputController()


def get_output_manager() -> OutputManager:
    """Get output manager instance"""
    return OutputManager()


def get_pdf_generator() -> PDFGenerator:
    """Get PDF generator instance"""
    return PDFGenerator()


# API Endpoints
@router.post("/prepare/{file_id}", response_model=DownloadResponse)
async def prepare_download(
    file_id: str,
    user_id: Optional[str] = Query(None, description="User ID for tracking"),
    output_controller: OutputController = Depends(get_output_controller)
):
    """
    Prepare file for download by creating a download session
    
    Args:
        file_id: Output file ID
        user_id: User ID for tracking
        
    Returns:
        DownloadResponse with download session information
    """
    logger.info(f"🔗 Preparing download for file: {file_id}")
    
    try:
        # Get file information
        file_info = await output_controller.get_file_info(file_id)
        if not file_info:
            raise HTTPException(status_code=404, detail=f"File not found: {file_id}")
        
        # Check file status
        if file_info.status.value != "ready":
            return DownloadResponse(
                success=False,
                error=f"File not ready for download. Status: {file_info.status.value}"
            )
        
        # Create download session
        session = await output_controller.create_download_session(file_id, user_id)
        if not session:
            return DownloadResponse(
                success=False,
                error="Failed to create download session"
            )
        
        return DownloadResponse(
            success=True,
            download_url=session.download_url,
            session_id=session.session_id,
            file_info={
                'file_id': file_info.file_id,
                'filename': file_info.filename,
                'file_size': file_info.file_size,
                'format': file_info.format.value,
                'mime_type': file_info.mime_type,
                'created_at': file_info.created_at.isoformat()
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to prepare download for {file_id}: {e}")
        return DownloadResponse(
            success=False,
            error=str(e)
        )


@router.get("/file/{session_id}")
async def download_file(
    session_id: str,
    output_controller: OutputController = Depends(get_output_controller)
):
    """
    Download file using session ID
    
    Args:
        session_id: Download session ID
        
    Returns:
        File content as streaming response
    """
    logger.info(f"⬇️ Downloading file with session: {session_id}")
    
    try:
        # Download file using session
        download_result = await output_controller.download_file(session_id)
        if not download_result:
            raise HTTPException(status_code=404, detail="Download session not found or expired")
        
        # Create streaming response
        file_content = download_result['content']
        filename = download_result['filename']
        mime_type = download_result['mime_type']
        
        def iter_file():
            yield file_content
        
        response = StreamingResponse(
            io.BytesIO(file_content),
            media_type=mime_type,
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Content-Length': str(len(file_content))
            }
        )
        
        logger.info(f"✅ File downloaded: {filename} ({len(file_content)} bytes)")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Download failed for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")


@router.post("/batch", response_model=BatchDownloadResponse)
async def create_batch_download(
    request: BatchDownloadRequest,
    output_controller: OutputController = Depends(get_output_controller)
):
    """
    Create batch download package
    
    Args:
        request: Batch download request
        
    Returns:
        BatchDownloadResponse with package information
    """
    logger.info(f"📦 Creating batch download for {len(request.file_ids)} files")
    
    try:
        if len(request.file_ids) == 0:
            raise HTTPException(status_code=400, detail="No files specified for batch download")
        
        if len(request.file_ids) > 50:  # Arbitrary limit
            raise HTTPException(status_code=400, detail="Too many files for batch download (max 50)")
        
        # Create batch download
        batch = await output_controller.create_batch_download(
            request.file_ids,
            request.package_name
        )
        
        if not batch:
            return BatchDownloadResponse(
                success=False,
                error="Failed to create batch download - no valid files found"
            )
        
        if batch.status.value != "ready":
            return BatchDownloadResponse(
                success=False,
                error=f"Batch creation failed. Status: {batch.status.value}"
            )
        
        # Create download session for batch
        batch_file_id = f"batch_{batch.batch_id}"
        session = await output_controller.create_download_session(batch_file_id)
        
        return BatchDownloadResponse(
            success=True,
            batch_id=batch.batch_id,
            download_url=session.download_url if session else None,
            file_count=batch.file_count,
            total_size=batch.total_size
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Batch download creation failed: {e}")
        return BatchDownloadResponse(
            success=False,
            error=str(e)
        )


@router.post("/convert", response_model=ConversionResponse)
async def convert_file_format(
    request: ConversionRequest,
    output_controller: OutputController = Depends(get_output_controller),
    pdf_generator: PDFGenerator = Depends(get_pdf_generator)
):
    """
    Convert file to different format
    
    Args:
        request: Conversion request
        
    Returns:
        ConversionResponse with converted file information
    """
    logger.info(f"🔄 Converting file {request.source_file_id} to {request.target_format.value}")
    
    try:
        # Get source file
        source_file = await output_controller.get_file_info(request.source_file_id)
        if not source_file:
            raise HTTPException(status_code=404, detail=f"Source file not found: {request.source_file_id}")
        
        # Perform conversion
        converted_file = await output_controller.convert_format(
            request.source_file_id,
            request.target_format
        )
        
        if not converted_file:
            return ConversionResponse(
                success=False,
                error=f"Conversion not supported: {source_file.format.value} -> {request.target_format.value}"
            )
        
        # Create download session for converted file
        session = await output_controller.create_download_session(converted_file.file_id)
        
        return ConversionResponse(
            success=True,
            converted_file_id=converted_file.file_id,
            download_url=session.download_url if session else None,
            conversion_info={
                'source_format': source_file.format.value,
                'target_format': converted_file.format.value,
                'source_size': source_file.file_size,
                'converted_size': converted_file.file_size,
                'conversion_time': converted_file.metadata.get('conversion_time')
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ File conversion failed: {e}")
        return ConversionResponse(
            success=False,
            error=str(e)
        )


@router.get("/formats")
async def get_supported_formats():
    """Get list of supported output formats and conversions"""
    try:
        return {
            'success': True,
            'supported_formats': [fmt.value for fmt in OutputFormat],
            'conversions': {
                'docx': ['pdf', 'txt'],
                'pdf': [],
                'json': ['txt'],
                'txt': [],
                'zip': []
            },
            'format_descriptions': {
                'docx': 'Microsoft Word Document',
                'pdf': 'Portable Document Format',
                'json': 'JSON Data Format',
                'txt': 'Plain Text',
                'zip': 'ZIP Archive'
            }
        }
    except Exception as e:
        logger.error(f"❌ Failed to get supported formats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/preview/{file_id}")
async def preview_file(
    file_id: str,
    format: Optional[str] = Query(default="json", description="Preview format"),
    output_controller: OutputController = Depends(get_output_controller)
):
    """
    Get file preview information
    
    Args:
        file_id: File ID
        format: Preview format (json, text, metadata)
        
    Returns:
        File preview data
    """
    logger.info(f"👁️ Previewing file: {file_id}")
    
    try:
        # Get file information
        file_info = await output_controller.get_file_info(file_id)
        if not file_info:
            raise HTTPException(status_code=404, detail=f"File not found: {file_id}")
        
        preview_data = {
            'file_id': file_info.file_id,
            'filename': file_info.filename,
            'format': file_info.format.value,
            'file_size': file_info.file_size,
            'created_at': file_info.created_at.isoformat(),
            'download_count': file_info.download_count,
            'last_downloaded': file_info.last_downloaded.isoformat() if file_info.last_downloaded else None
        }
        
        if format == "metadata":
            preview_data['metadata'] = file_info.metadata
            preview_data['checksum'] = file_info.checksum
        
        elif format == "text" and file_info.format in [OutputFormat.TXT, OutputFormat.JSON]:
            # For text files, provide content preview
            try:
                with open(file_info.file_path, 'r', encoding='utf-8') as f:
                    content = f.read(1000)  # First 1000 characters
                preview_data['content_preview'] = content
                preview_data['is_truncated'] = len(content) == 1000
            except Exception as e:
                preview_data['content_error'] = str(e)
        
        return {
            'success': True,
            'preview': preview_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to preview file {file_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_download_history(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    limit: int = Query(20, description="Maximum number of records"),
    output_manager: OutputManager = Depends(get_output_manager)
):
    """
    Get download history
    
    Args:
        user_id: Filter by user ID
        limit: Maximum number of records
        
    Returns:
        Download history data
    """
    logger.info(f"📜 Getting download history - user: {user_id}")
    
    try:
        # Get recent downloads
        files = await output_manager.list_files(
            status=None,  # All statuses
            limit=limit
        )
        
        # Filter downloaded files
        download_history = []
        for file_record in files:
            if file_record.download_count > 0:
                download_history.append({
                    'file_id': file_record.file_id,
                    'filename': file_record.filename,
                    'file_type': file_record.file_type.value,
                    'file_size': file_record.file_size,
                    'download_count': file_record.download_count,
                    'last_downloaded': file_record.last_downloaded.isoformat() if file_record.last_downloaded else None,
                    'created_at': file_record.created_at.isoformat()
                })
        
        # Sort by last downloaded
        download_history.sort(key=lambda x: x['last_downloaded'] or '', reverse=True)
        
        return {
            'success': True,
            'history': download_history[:limit],
            'total_count': len(download_history)
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get download history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_download_statistics(
    output_controller: OutputController = Depends(get_output_controller),
    output_manager: OutputManager = Depends(get_output_manager)
):
    """Get download statistics"""
    try:
        # Get output statistics
        output_stats = output_controller.get_output_statistics()
        storage_stats = output_manager.get_storage_stats()
        
        # Combine statistics
        combined_stats = {
            'downloads': {
                'total_downloads': output_stats.get('total_downloads', 0),
                'active_sessions': output_stats.get('active_download_sessions', 0),
                'batch_downloads': output_stats.get('batch_downloads', 0)
            },
            'files': {
                'total_files': storage_stats['total_files'],
                'format_distribution': storage_stats['type_distribution'],
                'total_size_bytes': storage_stats['total_size_bytes'],
                'quota_usage_percent': storage_stats['quota_usage_percent']
            },
            'conversions': {
                'supported_formats': len(OutputFormat),
                'conversion_pairs': 4  # DOCX->PDF, DOCX->TXT, JSON->TXT, etc.
            }
        }
        
        return {
            'success': True,
            'statistics': combined_stats
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get download statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))