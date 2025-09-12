"""
File Upload API Endpoint (P01 - API Layer)
Advanced file upload handling with validation and processing coordination
Implements ICE principle - Intuitive upload interface with comprehensive error handling
"""

import logging
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import os
from datetime import datetime

from ..core.file_processor import FileProcessor, ProcessedFile, FileStatus, FileProcessingOptions
from ..core.meeting_processor import MeetingProcessor, ProcessingJob, ProcessingPriority
from ..core.template_controller import TemplateController, TemplateType
from ..config import settings

logger = logging.getLogger(__name__)

# API Router
router = APIRouter(prefix="/api/upload", tags=["upload"])

# Pydantic models for request/response
class FileUploadResponse(BaseModel):
    success: bool
    file_id: Optional[str] = None
    job_id: Optional[str] = None
    message: str
    file_info: Optional[Dict[str, Any]] = None
    processing_info: Optional[Dict[str, Any]] = None


class ProcessingOptions(BaseModel):
    """Processing options for uploaded file"""
    auto_process: bool = Field(default=True, description="Start processing automatically")
    template_type: TemplateType = Field(default=TemplateType.STANDARD, description="Template type to use")
    priority: ProcessingPriority = Field(default=ProcessingPriority.NORMAL, description="Processing priority")
    generate_pdf: bool = Field(default=True, description="Generate PDF output")
    extraction_options: Dict[str, Any] = Field(default_factory=dict, description="AI extraction options")
    template_options: Dict[str, Any] = Field(default_factory=dict, description="Template processing options")


class BatchUploadRequest(BaseModel):
    """Batch upload request"""
    processing_options: ProcessingOptions = Field(default_factory=ProcessingOptions)
    user_id: Optional[str] = None


class BatchUploadResponse(BaseModel):
    success: bool
    uploaded_count: int
    failed_count: int
    results: List[FileUploadResponse]
    batch_id: Optional[str] = None


# Dependency injection
def get_file_processor() -> FileProcessor:
    """Get file processor instance"""
    return FileProcessor()


def get_meeting_processor() -> MeetingProcessor:
    """Get meeting processor instance"""
    return MeetingProcessor()


def get_template_controller() -> TemplateController:
    """Get template controller instance"""
    return TemplateController()


# API Endpoints
@router.post("/single", response_model=FileUploadResponse)
async def upload_single_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    processing_options: str = Form(default="{}"),
    user_id: Optional[str] = Form(default=None),
    file_processor: FileProcessor = Depends(get_file_processor),
    meeting_processor: MeetingProcessor = Depends(get_meeting_processor)
):
    """
    Upload single file and optionally start processing
    
    Args:
        file: Uploaded file
        processing_options: JSON string of processing options
        user_id: User identifier
        
    Returns:
        FileUploadResponse with upload and processing status
    """
    logger.info(f"📤 Single file upload: {file.filename} ({user_id or 'anonymous'})")
    
    try:
        # Parse processing options
        import json
        try:
            options_dict = json.loads(processing_options)
            options = ProcessingOptions(**options_dict)
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"⚠️ Invalid processing options, using defaults: {e}")
            options = ProcessingOptions()
        
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="Filename is required")
        
        # Check file size
        if file.size and file.size > settings.max_file_size_bytes:
            raise HTTPException(
                status_code=413, 
                detail=f"File too large. Maximum size: {settings.max_file_size_mb}MB"
            )
        
        # Read file content
        file_content = await file.read()
        
        if len(file_content) == 0:
            raise HTTPException(status_code=400, detail="Empty file not allowed")
        
        # Process file upload
        file_processing_options = FileProcessingOptions(
            max_file_size=settings.max_file_size_bytes,
            allowed_types=settings.allowed_file_types,
            validate_content=True,
            extract_text=True,
            preprocess_text=True
        )
        
        processed_file = await file_processor.upload_file(
            file_content, 
            file.filename,
            file_processing_options
        )
        
        if processed_file.status == FileStatus.ERROR:
            raise HTTPException(
                status_code=400, 
                detail=f"File processing failed: {processed_file.error_message}"
            )
        
        # Prepare response data
        file_info = {
            'file_id': processed_file.file_id,
            'original_name': processed_file.original_name,
            'file_size': processed_file.file_size,
            'file_type': processed_file.file_type.value,
            'mime_type': processed_file.mime_type,
            'upload_timestamp': processed_file.upload_timestamp.isoformat(),
            'validation_results': processed_file.validation_results
        }
        
        response_data = FileUploadResponse(
            success=True,
            file_id=processed_file.file_id,
            message="File uploaded successfully",
            file_info=file_info
        )
        
        # Start processing if requested
        if options.auto_process:
            try:
                processing_options_dict = {
                    'template_type': options.template_type,
                    'generate_pdf': options.generate_pdf,
                    'extraction': options.extraction_options,
                    'template': options.template_options
                }
                
                job_id = await meeting_processor.submit_processing_job(
                    file_content,
                    file.filename,
                    user_id,
                    options.priority,
                    processing_options_dict
                )
                
                response_data.job_id = job_id
                response_data.processing_info = {
                    'job_id': job_id,
                    'auto_started': True,
                    'priority': options.priority.value,
                    'template_type': options.template_type.value
                }
                response_data.message += " - Processing started automatically"
                
                logger.info(f"✅ File uploaded and processing started: {processed_file.file_id} -> {job_id}")
                
            except Exception as e:
                logger.warning(f"⚠️ File uploaded but processing failed to start: {e}")
                response_data.processing_info = {
                    'auto_started': False,
                    'error': str(e)
                }
                response_data.message += " - Manual processing required"
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Single file upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.post("/batch", response_model=BatchUploadResponse)
async def upload_batch_files(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    request_data: str = Form(default="{}"),
    file_processor: FileProcessor = Depends(get_file_processor),
    meeting_processor: MeetingProcessor = Depends(get_meeting_processor)
):
    """
    Upload multiple files in batch
    
    Args:
        files: List of uploaded files
        request_data: JSON string of batch upload request
        
    Returns:
        BatchUploadResponse with batch processing results
    """
    logger.info(f"📦 Batch file upload: {len(files)} files")
    
    try:
        # Parse request data
        import json
        try:
            request_dict = json.loads(request_data)
            request = BatchUploadRequest(**request_dict)
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"⚠️ Invalid request data, using defaults: {e}")
            request = BatchUploadRequest()
        
        if len(files) > settings.max_batch_upload_files:
            raise HTTPException(
                status_code=400, 
                detail=f"Too many files. Maximum: {settings.max_batch_upload_files}"
            )
        
        # Process each file
        results = []
        uploaded_count = 0
        failed_count = 0
        
        batch_id = f"batch_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{len(files)}"
        
        for i, file in enumerate(files):
            try:
                logger.info(f"📄 Processing file {i+1}/{len(files)}: {file.filename}")
                
                # Read file content
                file_content = await file.read()
                
                # Basic validation
                if len(file_content) == 0:
                    results.append(FileUploadResponse(
                        success=False,
                        message=f"Empty file skipped: {file.filename}"
                    ))
                    failed_count += 1
                    continue
                
                if len(file_content) > settings.max_file_size_bytes:
                    results.append(FileUploadResponse(
                        success=False,
                        message=f"File too large: {file.filename}"
                    ))
                    failed_count += 1
                    continue
                
                # Process file
                processed_file = await file_processor.upload_file(
                    file_content,
                    file.filename,
                    FileProcessingOptions()
                )
                
                if processed_file.status == FileStatus.ERROR:
                    results.append(FileUploadResponse(
                        success=False,
                        message=f"Processing failed: {processed_file.error_message}"
                    ))
                    failed_count += 1
                    continue
                
                # Create success response
                file_response = FileUploadResponse(
                    success=True,
                    file_id=processed_file.file_id,
                    message=f"File uploaded successfully: {file.filename}",
                    file_info={
                        'file_id': processed_file.file_id,
                        'original_name': processed_file.original_name,
                        'file_size': processed_file.file_size,
                        'file_type': processed_file.file_type.value
                    }
                )
                
                # Start processing if requested
                if request.processing_options.auto_process:
                    try:
                        job_id = await meeting_processor.submit_processing_job(
                            file_content,
                            file.filename,
                            request.user_id,
                            request.processing_options.priority,
                            {
                                'template_type': request.processing_options.template_type,
                                'batch_id': batch_id
                            }
                        )
                        
                        file_response.job_id = job_id
                        file_response.processing_info = {
                            'job_id': job_id,
                            'batch_id': batch_id
                        }
                        
                    except Exception as e:
                        logger.warning(f"⚠️ Processing failed to start for {file.filename}: {e}")
                        file_response.processing_info = {
                            'auto_started': False,
                            'error': str(e)
                        }
                
                results.append(file_response)
                uploaded_count += 1
                
            except Exception as e:
                logger.error(f"❌ Failed to process file {file.filename}: {e}")
                results.append(FileUploadResponse(
                    success=False,
                    message=f"Upload failed: {str(e)}"
                ))
                failed_count += 1
        
        logger.info(f"✅ Batch upload completed: {uploaded_count} success, {failed_count} failed")
        
        return BatchUploadResponse(
            success=uploaded_count > 0,
            uploaded_count=uploaded_count,
            failed_count=failed_count,
            results=results,
            batch_id=batch_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Batch upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Batch upload failed: {str(e)}")


@router.get("/supported-types")
async def get_supported_file_types(
    file_processor: FileProcessor = Depends(get_file_processor)
):
    """Get list of supported file types"""
    try:
        supported_types = await file_processor.get_supported_file_types()
        
        return {
            'success': True,
            'supported_types': supported_types,
            'max_file_size_mb': settings.max_file_size_mb,
            'max_batch_files': settings.max_batch_upload_files
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get supported types: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates")
async def get_available_templates(
    template_controller: TemplateController = Depends(get_template_controller)
):
    """Get list of available templates"""
    try:
        templates = await template_controller.get_available_templates()
        
        return {
            'success': True,
            'templates': templates
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate")
async def validate_file(
    file: UploadFile = File(...),
    file_processor: FileProcessor = Depends(get_file_processor)
):
    """
    Validate uploaded file without storing it
    
    Args:
        file: File to validate
        
    Returns:
        Validation results
    """
    logger.info(f"🔍 File validation: {file.filename}")
    
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="Filename is required")
        
        # Read file content
        file_content = await file.read()
        
        # Basic validation
        validation_results = {
            'filename': file.filename,
            'file_size': len(file_content),
            'size_valid': len(file_content) <= settings.max_file_size_bytes,
            'not_empty': len(file_content) > 0,
            'type_supported': False,
            'content_readable': False
        }
        
        # Check file type
        import magic
        try:
            mime_type = magic.from_buffer(file_content, mime=True)
            validation_results['detected_mime_type'] = mime_type
            validation_results['type_supported'] = mime_type in settings.allowed_file_types
        except Exception as e:
            logger.warning(f"⚠️ MIME type detection failed: {e}")
            validation_results['mime_detection_error'] = str(e)
        
        # Try to read content for text files
        if validation_results.get('detected_mime_type', '').startswith('text/'):
            try:
                content_preview = file_content.decode('utf-8', errors='ignore')[:500]
                validation_results['content_readable'] = True
                validation_results['content_preview'] = content_preview
                validation_results['estimated_word_count'] = len(content_preview.split())
            except Exception as e:
                validation_results['content_read_error'] = str(e)
        
        # Overall validation status
        validation_results['valid'] = all([
            validation_results['size_valid'],
            validation_results['not_empty'],
            validation_results['type_supported']
        ])
        
        if validation_results['valid']:
            validation_results['message'] = "File validation passed"
        else:
            validation_results['message'] = "File validation failed"
        
        return {
            'success': True,
            'validation': validation_results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ File validation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")


@router.get("/stats")
async def get_upload_statistics(
    file_processor: FileProcessor = Depends(get_file_processor)
):
    """Get upload and processing statistics"""
    try:
        stats = file_processor.get_processing_stats()
        
        return {
            'success': True,
            'statistics': stats
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get upload statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))