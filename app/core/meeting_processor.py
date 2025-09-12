"""
Meeting Processing Coordinator (B2 - Business Logic Layer)
Central coordinator for meeting minutes processing workflow
Implements SESE and 82 Rule principles - orchestrates 20% core functionality for 80% effectiveness
"""

import asyncio
import logging
from typing import Dict, List, Optional, Union, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
import uuid

from ..ai.text_preprocessor import TextPreprocessor
from ..ai.ollama_client import OllamaClient
from ..ai.extractor import StructuredDataExtractor, MeetingMinutes, ExtractionResult, ExtractionStatus
from .file_processor import FileProcessor, ProcessedFile, FileStatus
from ..config import settings

logger = logging.getLogger(__name__)


class ProcessingStage(Enum):
    """Processing workflow stages"""
    QUEUED = "queued"
    FILE_VALIDATION = "file_validation"
    TEXT_PREPROCESSING = "text_preprocessing"
    AI_EXTRACTION = "ai_extraction"
    DATA_VALIDATION = "data_validation"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProcessingPriority(Enum):
    """Processing priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class ProcessingJob:
    """Meeting processing job container"""
    job_id: str
    file_id: str
    user_id: Optional[str] = None
    stage: ProcessingStage = ProcessingStage.QUEUED
    priority: ProcessingPriority = ProcessingPriority.NORMAL
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: float = 0.0
    status_message: str = "Job queued for processing"
    extraction_result: Optional[ExtractionResult] = None
    processing_options: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class ProcessingStats:
    """Processing statistics"""
    total_jobs: int = 0
    completed_jobs: int = 0
    failed_jobs: int = 0
    active_jobs: int = 0
    average_processing_time: float = 0.0
    success_rate: float = 0.0
    total_processing_time: float = 0.0


class MeetingProcessor:
    """
    Central coordinator for meeting minutes processing
    Orchestrates the complete workflow from file upload to structured minutes extraction
    """
    
    def __init__(
        self,
        file_processor: Optional[FileProcessor] = None,
        data_extractor: Optional[StructuredDataExtractor] = None,
        ollama_client: Optional[OllamaClient] = None,
        max_concurrent_jobs: int = 5
    ):
        """Initialize meeting processor with dependencies"""
        self.file_processor = file_processor or FileProcessor()
        self.data_extractor = data_extractor or StructuredDataExtractor(ollama_client)
        self.max_concurrent_jobs = max_concurrent_jobs
        
        # Job management
        self._active_jobs: Dict[str, ProcessingJob] = {}
        self._completed_jobs: Dict[str, ProcessingJob] = {}
        self._processing_queue: List[ProcessingJob] = []
        self._job_semaphore = asyncio.Semaphore(max_concurrent_jobs)
        
        # Processing callbacks and hooks
        self._stage_callbacks: Dict[ProcessingStage, List[Callable]] = {
            stage: [] for stage in ProcessingStage
        }
        
        # Statistics tracking
        self._stats = ProcessingStats()
        
        logger.info(f"🤖 Meeting Processor initialized - max concurrent jobs: {max_concurrent_jobs}")
    
    async def submit_processing_job(
        self, 
        file_data: bytes,
        filename: str,
        user_id: Optional[str] = None,
        priority: ProcessingPriority = ProcessingPriority.NORMAL,
        processing_options: Optional[Dict] = None
    ) -> str:
        """
        Submit a new meeting processing job
        
        Args:
            file_data: Raw file data
            filename: Original filename
            user_id: User identifier
            priority: Processing priority
            processing_options: Custom processing options
            
        Returns:
            Job ID for tracking
        """
        job_id = str(uuid.uuid4())
        processing_options = processing_options or {}
        
        logger.info(f"📋 Submitting processing job: {job_id} for file: {filename}")
        
        # Create processing job
        job = ProcessingJob(
            job_id=job_id,
            file_id="",  # Will be set after file upload
            user_id=user_id,
            priority=priority,
            processing_options=processing_options,
            metadata={
                'original_filename': filename,
                'file_size': len(file_data),
                'submitted_by': user_id
            }
        )
        
        # Add to processing queue
        self._processing_queue.append(job)
        self._stats.total_jobs += 1
        
        # Start processing (async)
        asyncio.create_task(self._process_job(job, file_data, filename))
        
        return job_id
    
    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job processing status"""
        # Check active jobs
        if job_id in self._active_jobs:
            job = self._active_jobs[job_id]
            return self._serialize_job_status(job)
        
        # Check completed jobs
        if job_id in self._completed_jobs:
            job = self._completed_jobs[job_id]
            return self._serialize_job_status(job)
        
        # Check queue
        for job in self._processing_queue:
            if job.job_id == job_id:
                return self._serialize_job_status(job)
        
        return None
    
    async def get_job_result(self, job_id: str) -> Optional[MeetingMinutes]:
        """Get processing job result"""
        job = self._completed_jobs.get(job_id)
        if not job or job.stage != ProcessingStage.COMPLETED:
            return None
        
        return job.extraction_result.minutes if job.extraction_result else None
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a processing job"""
        # Remove from queue
        self._processing_queue = [job for job in self._processing_queue if job.job_id != job_id]
        
        # Cancel active job
        if job_id in self._active_jobs:
            job = self._active_jobs[job_id]
            job.stage = ProcessingStage.CANCELLED
            job.status_message = "Job cancelled by user"
            job.completed_at = datetime.utcnow()
            
            # Move to completed
            self._completed_jobs[job_id] = job
            del self._active_jobs[job_id]
            
            logger.info(f"❌ Job cancelled: {job_id}")
            return True
        
        return False
    
    async def retry_failed_job(self, job_id: str) -> bool:
        """Retry a failed processing job"""
        if job_id not in self._completed_jobs:
            return False
        
        job = self._completed_jobs[job_id]
        
        if job.stage != ProcessingStage.FAILED or job.retry_count >= job.max_retries:
            return False
        
        # Reset job state
        job.stage = ProcessingStage.QUEUED
        job.progress = 0.0
        job.retry_count += 1
        job.status_message = f"Retrying job (attempt {job.retry_count + 1})"
        job.error_message = None
        job.started_at = None
        job.completed_at = None
        
        # Move back to queue
        self._processing_queue.append(job)
        del self._completed_jobs[job_id]
        
        logger.info(f"🔄 Retrying job: {job_id} (attempt {job.retry_count + 1})")
        return True
    
    def get_processing_statistics(self) -> ProcessingStats:
        """Get processing statistics"""
        # Update stats
        self._stats.active_jobs = len(self._active_jobs)
        
        if self._stats.total_jobs > 0:
            self._stats.success_rate = self._stats.completed_jobs / self._stats.total_jobs
        
        return self._stats
    
    def register_stage_callback(self, stage: ProcessingStage, callback: Callable):
        """Register callback for processing stage"""
        self._stage_callbacks[stage].append(callback)
    
    async def cleanup_completed_jobs(self, max_age_hours: int = 24) -> int:
        """Clean up old completed jobs"""
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        cleanup_count = 0
        
        jobs_to_remove = []
        for job_id, job in self._completed_jobs.items():
            if job.completed_at and job.completed_at < cutoff_time:
                jobs_to_remove.append(job_id)
        
        for job_id in jobs_to_remove:
            del self._completed_jobs[job_id]
            cleanup_count += 1
        
        if cleanup_count > 0:
            logger.info(f"🧹 Cleaned up {cleanup_count} old completed jobs")
        
        return cleanup_count
    
    # Private processing methods
    
    async def _process_job(self, job: ProcessingJob, file_data: bytes, filename: str):
        """Main job processing workflow"""
        async with self._job_semaphore:
            try:
                # Move to active jobs
                self._active_jobs[job.job_id] = job
                job.started_at = datetime.utcnow()
                job.stage = ProcessingStage.FILE_VALIDATION
                
                await self._update_job_progress(job, 0.1, "Validating file...")
                
                # Stage 1: File Processing and Validation
                processed_file = await self._process_file(job, file_data, filename)
                job.file_id = processed_file.file_id
                
                await self._update_job_progress(job, 0.3, "Preprocessing text content...")
                
                # Stage 2: Text Preprocessing
                await self._preprocess_text(job, processed_file)
                
                await self._update_job_progress(job, 0.6, "Extracting meeting information with AI...")
                
                # Stage 3: AI Extraction
                await self._extract_meeting_data(job, processed_file)
                
                await self._update_job_progress(job, 0.9, "Validating extracted data...")
                
                # Stage 4: Data Validation
                await self._validate_extracted_data(job)
                
                await self._update_job_progress(job, 1.0, "Processing completed successfully!")
                
                # Mark as completed
                job.stage = ProcessingStage.COMPLETED
                job.completed_at = datetime.utcnow()
                
                # Update statistics
                self._stats.completed_jobs += 1
                processing_time = (job.completed_at - job.started_at).total_seconds()
                self._stats.total_processing_time += processing_time
                self._stats.average_processing_time = self._stats.total_processing_time / self._stats.completed_jobs
                
                # Move to completed jobs
                self._completed_jobs[job.job_id] = job
                if job.job_id in self._active_jobs:
                    del self._active_jobs[job.job_id]
                
                logger.info(f"✅ Job completed successfully: {job.job_id} in {processing_time:.2f}s")
                
                # Execute stage callback
                await self._execute_stage_callbacks(ProcessingStage.COMPLETED, job)
                
            except Exception as e:
                await self._handle_job_error(job, str(e))
    
    async def _process_file(self, job: ProcessingJob, file_data: bytes, filename: str) -> ProcessedFile:
        """Process and validate file"""
        job.stage = ProcessingStage.FILE_VALIDATION
        await self._execute_stage_callbacks(ProcessingStage.FILE_VALIDATION, job)
        
        try:
            processed_file = await self.file_processor.upload_file(file_data, filename)
            
            if processed_file.status != FileStatus.VALID:
                raise ValueError(f"File validation failed: {processed_file.error_message}")
            
            job.metadata['file_info'] = {
                'file_type': processed_file.file_type.value,
                'file_size': processed_file.file_size,
                'mime_type': processed_file.mime_type,
                'encoding': processed_file.encoding
            }
            
            return processed_file
            
        except Exception as e:
            raise ValueError(f"File processing failed: {str(e)}")
    
    async def _preprocess_text(self, job: ProcessingJob, processed_file: ProcessedFile):
        """Preprocess text content"""
        job.stage = ProcessingStage.TEXT_PREPROCESSING
        await self._execute_stage_callbacks(ProcessingStage.TEXT_PREPROCESSING, job)
        
        try:
            processing_results = await self.file_processor.process_file_content(
                processed_file.file_id, 
                job.processing_options
            )
            
            job.metadata['preprocessing_stats'] = processing_results.get('preprocessing_stats', {})
            
        except Exception as e:
            raise ValueError(f"Text preprocessing failed: {str(e)}")
    
    async def _extract_meeting_data(self, job: ProcessingJob, processed_file: ProcessedFile):
        """Extract structured meeting data using AI"""
        job.stage = ProcessingStage.AI_EXTRACTION
        await self._execute_stage_callbacks(ProcessingStage.AI_EXTRACTION, job)
        
        try:
            # Get preprocessed content
            content = await self.file_processor.get_file_content(processed_file.file_id)
            
            if not content:
                raise ValueError("No content available for extraction")
            
            # Extract meeting minutes
            extraction_result = await self.data_extractor.extract_meeting_minutes(
                content,
                preprocessing_options=job.processing_options.get('preprocessing', {}),
                extraction_options=job.processing_options.get('extraction', {})
            )
            
            job.extraction_result = extraction_result
            
            # Store extraction metadata
            job.metadata['extraction_metadata'] = extraction_result.extraction_metadata
            job.metadata['confidence_score'] = extraction_result.confidence_score
            
            if extraction_result.status != ExtractionStatus.COMPLETED:
                logger.warning(f"⚠️ Extraction completed with warnings: {extraction_result.status}")
            
        except Exception as e:
            raise ValueError(f"AI extraction failed: {str(e)}")
    
    async def _validate_extracted_data(self, job: ProcessingJob):
        """Validate extracted meeting data"""
        job.stage = ProcessingStage.DATA_VALIDATION
        await self._execute_stage_callbacks(ProcessingStage.DATA_VALIDATION, job)
        
        if not job.extraction_result or not job.extraction_result.minutes:
            raise ValueError("No extraction results to validate")
        
        # Basic validation checks
        minutes = job.extraction_result.minutes
        validation_issues = []
        
        # Check basic info
        if not minutes.basic_info or not (minutes.basic_info.title or minutes.basic_info.meeting_type):
            validation_issues.append("Missing meeting title or type")
        
        # Check attendees
        if not minutes.attendees:
            validation_issues.append("No attendees identified")
        
        # Check content richness
        total_content = len(minutes.agenda) + len(minutes.action_items) + len(minutes.decisions)
        if total_content == 0:
            validation_issues.append("No structured content extracted (agenda, actions, or decisions)")
        
        # Store validation results
        job.metadata['validation_issues'] = validation_issues
        job.metadata['data_quality'] = {
            'basic_info_complete': bool(minutes.basic_info.title),
            'has_attendees': len(minutes.attendees) > 0,
            'has_agenda': len(minutes.agenda) > 0,
            'has_action_items': len(minutes.action_items) > 0,
            'has_decisions': len(minutes.decisions) > 0,
            'content_richness': total_content
        }
        
        if validation_issues:
            logger.warning(f"⚠️ Data validation issues for job {job.job_id}: {validation_issues}")
    
    async def _handle_job_error(self, job: ProcessingJob, error_message: str):
        """Handle job processing error"""
        job.stage = ProcessingStage.FAILED
        job.error_message = error_message
        job.status_message = f"Processing failed: {error_message}"
        job.completed_at = datetime.utcnow()
        
        # Update statistics
        self._stats.failed_jobs += 1
        
        # Move to completed jobs
        self._completed_jobs[job.job_id] = job
        if job.job_id in self._active_jobs:
            del self._active_jobs[job.job_id]
        
        logger.error(f"❌ Job failed: {job.job_id} - {error_message}")
        
        # Execute stage callback
        await self._execute_stage_callbacks(ProcessingStage.FAILED, job)
    
    async def _update_job_progress(self, job: ProcessingJob, progress: float, message: str):
        """Update job progress and status"""
        job.progress = progress
        job.status_message = message
        logger.debug(f"📈 Job {job.job_id}: {progress*100:.1f}% - {message}")
    
    async def _execute_stage_callbacks(self, stage: ProcessingStage, job: ProcessingJob):
        """Execute callbacks for processing stage"""
        callbacks = self._stage_callbacks.get(stage, [])
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(job)
                else:
                    callback(job)
            except Exception as e:
                logger.warning(f"⚠️ Stage callback error for {stage}: {e}")
    
    def _serialize_job_status(self, job: ProcessingJob) -> Dict[str, Any]:
        """Serialize job status for API response"""
        return {
            'job_id': job.job_id,
            'file_id': job.file_id,
            'stage': job.stage.value,
            'priority': job.priority.value,
            'progress': job.progress,
            'status_message': job.status_message,
            'created_at': job.created_at.isoformat(),
            'started_at': job.started_at.isoformat() if job.started_at else None,
            'completed_at': job.completed_at.isoformat() if job.completed_at else None,
            'confidence_score': job.extraction_result.confidence_score if job.extraction_result else 0.0,
            'retry_count': job.retry_count,
            'error_message': job.error_message,
            'metadata': job.metadata
        }