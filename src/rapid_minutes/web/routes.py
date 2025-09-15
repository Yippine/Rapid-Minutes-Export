import logging
from fastapi import APIRouter, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse

from rapid_minutes.storage.file_manager import FileManager
from rapid_minutes.ai.ollama_client import OllamaClient
from rapid_minutes.ai.text_processor import TextProcessor
from rapid_minutes.document.word_generator import WordGenerator

logger = logging.getLogger(__name__)
router = APIRouter()

file_manager = FileManager()
ollama_client = OllamaClient()
text_processor = TextProcessor()


@router.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload a text file for processing"""
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")

        # Sanitize filename
        import re
        if not re.match(r'^[a-zA-Z0-9._-]+$', file.filename) or '..' in file.filename:
            raise HTTPException(status_code=400, detail="Invalid filename")

        # Check file type
        allowed_extensions = ['.txt', '.doc', '.docx']
        file_ext = '.' + file.filename.split('.')[-1].lower()
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type. Allowed: {allowed_extensions}"
            )

        # Check file size
        if file.size and file.size > 10 * 1024 * 1024:  # 10MB limit
            raise HTTPException(status_code=413, detail="File too large (max 10MB)")

        # Read file content
        file_content = await file.read()

        # Validate content size
        if len(file_content) == 0:
            raise HTTPException(status_code=400, detail="Empty file not allowed")

        if len(file_content) > 10 * 1024 * 1024:  # 10MB limit
            raise HTTPException(status_code=413, detail="File content too large")
        
        # Save file
        file_info = file_manager.save_uploaded_file(file_content, file.filename)
        
        return {
            "success": True,
            "file_id": file_info["file_id"],
            "filename": file_info["original_name"],
            "size": file_info["file_size"],
            "message": "File uploaded successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload file")


def validate_file_id(file_id: str) -> str:
    """Validate file_id to prevent path traversal"""
    import re
    if not re.match(r'^[a-zA-Z0-9-]+$', file_id) or '..' in file_id or len(file_id) != 36:
        raise HTTPException(status_code=400, detail="Invalid file ID format")
    return file_id


@router.post("/api/generate/{file_id}")
async def generate_minutes(file_id: str, background_tasks: BackgroundTasks):
    """Generate meeting minutes from uploaded file"""
    try:
        # Validate file_id
        file_id = validate_file_id(file_id)

        # Check if file exists
        file_info = file_manager.get_file_info(file_id)
        if not file_info:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Start background processing
        background_tasks.add_task(process_file_background, file_id)
        
        return {
            "success": True,
            "file_id": file_id,
            "message": "Processing started",
            "status": "processing"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Generation error: {e}")
        raise HTTPException(status_code=500, detail="Failed to start processing")


@router.get("/api/status/{file_id}")
async def get_processing_status(file_id: str):
    """Get processing status of a file"""
    try:
        # Validate file_id
        file_id = validate_file_id(file_id)

        file_info = file_manager.get_file_info(file_id)
        if not file_info:
            raise HTTPException(status_code=404, detail="File not found")
        
        return {
            "file_id": file_id,
            "status": file_info.get("status", "unknown"),
            "progress": file_info.get("progress", 0),
            "error": file_info.get("error"),
            "last_updated": file_info.get("last_updated")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Status check error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get status")


@router.get("/api/download/{file_type}/{file_id}")
async def download_file(file_type: str, file_id: str):
    """Download generated Word or PDF file"""
    try:
        # Validate file_id
        file_id = validate_file_id(file_id)

        if file_type not in ['word', 'pdf']:
            raise HTTPException(status_code=400, detail="Invalid file type. Use 'word' or 'pdf'")

        file_path = file_manager.get_output_file_path(file_id, file_type)
        if not file_path:
            raise HTTPException(status_code=404, detail=f"Generated {file_type} file not found")
        
        # Determine media type and filename
        if file_type == 'word':
            media_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            filename = f"meeting_minutes_{file_id}.docx"
        else:
            media_type = 'application/pdf'
            filename = f"meeting_minutes_{file_id}.pdf"
        
        return FileResponse(
            path=file_path,
            media_type=media_type,
            filename=filename
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Download error: {e}")
        raise HTTPException(status_code=500, detail="Failed to download file")


@router.delete("/api/file/{file_id}")
async def delete_file(file_id: str):
    """Delete uploaded file and generated outputs"""
    try:
        # Validate file_id
        file_id = validate_file_id(file_id)

        file_info = file_manager.get_file_info(file_id)
        if not file_info:
            raise HTTPException(status_code=404, detail="File not found")
        
        # TODO: Implement file deletion
        # For now, just return success
        return {
            "success": True,
            "message": "File deletion scheduled"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete error: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete file")


@router.get("/api/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check Ollama connectivity
        ollama_healthy = ollama_client.health_check()
        
        return {
            "status": "healthy" if ollama_healthy else "degraded",
            "ollama": "connected" if ollama_healthy else "disconnected",
            "timestamp": file_manager.temp_dir
        }
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


async def process_file_background(file_id: str):
    """Background task to process uploaded file"""
    try:
        logger.info(f"Starting background processing for {file_id}")
        
        # Update status
        file_manager.update_processing_status(file_id, "processing", 10)
        
        # Read file content
        raw_content = file_manager.read_file_content(file_id)
        file_manager.update_processing_status(file_id, "processing", 20)
        
        # Clean and preprocess text
        cleaned_content = text_processor.clean_text(raw_content)
        preprocessed_content = text_processor.preprocess_for_ai(cleaned_content)
        file_manager.update_processing_status(file_id, "processing", 40)
        
        # Extract meeting data using AI
        meeting_data = ollama_client.extract_meeting_data(preprocessed_content)
        file_manager.update_processing_status(file_id, "processing", 70)
        
        # Generate Word document
        word_generator = WordGenerator()
        word_content = word_generator.generate_document(meeting_data)
        
        # Save Word file
        file_manager.save_output_file(file_id, word_content, 'word')
        file_manager.update_processing_status(file_id, "processing", 90)
        
        # Generate PDF (placeholder for now)
        # TODO: Implement PDF generation
        file_manager.update_processing_status(file_id, "completed", 100)
        
        logger.info(f"Background processing completed for {file_id}")
        
    except Exception as e:
        logger.error(f"Background processing failed for {file_id}: {e}")
        file_manager.update_processing_status(file_id, "failed", 0, str(e))