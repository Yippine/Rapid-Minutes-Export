"""
Processing Status API Endpoint (P02 - API Layer)
Real-time processing status monitoring and job management
Implements SESE principle - Simple, Effective, Systematic, Exhaustive status tracking
"""

import logging
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from datetime import datetime

from ..core.meeting_processor import MeetingProcessor, ProcessingStage
from ..core.file_processor import FileProcessor

logger = logging.getLogger(__name__)

# API Router
router = APIRouter(prefix="/api/process", tags=["processing"])

# Pydantic models
class ProcessingStatusResponse(BaseModel):
    """Processing status response model"""
    success: bool
    job_id: str
    status: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class JobListResponse(BaseModel):
    """Job list response model"""
    success: bool
    jobs: List[Dict[str, Any]] = Field(default_factory=list)
    total_count: int = 0
    active_count: int = 0
    completed_count: int = 0


class ProcessingResultResponse(BaseModel):
    """Processing result response model"""
    success: bool
    job_id: str
    result: Optional[Dict[str, Any]] = None
    meeting_minutes: Optional[Dict[str, Any]] = None
    generation_info: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class JobControlResponse(BaseModel):
    """Job control response model"""
    success: bool
    job_id: str
    action: str
    message: str


class ProcessingStatsResponse(BaseModel):
    """Processing statistics response model"""
    success: bool
    statistics: Dict[str, Any]


# Dependency injection
def get_meeting_processor() -> MeetingProcessor:
    """Get meeting processor instance"""
    return MeetingProcessor()


def get_file_processor() -> FileProcessor:
    """Get file processor instance"""
    return FileProcessor()


# API Endpoints
@router.get("/status/{job_id}", response_model=ProcessingStatusResponse)
async def get_processing_status(
    job_id: str,
    meeting_processor: MeetingProcessor = Depends(get_meeting_processor)
):
    """
    Get processing status for a specific job
    
    Args:
        job_id: Processing job ID
        
    Returns:
        ProcessingStatusResponse with current status
    """
    logger.info(f"📊 Getting processing status: {job_id}")
    
    try:
        status = await meeting_processor.get_job_status(job_id)
        
        if not status:
            raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
        
        return ProcessingStatusResponse(
            success=True,
            job_id=job_id,
            status=status
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get processing status for {job_id}: {e}")
        return ProcessingStatusResponse(
            success=False,
            job_id=job_id,
            error=str(e)
        )


@router.get("/jobs", response_model=JobListResponse)
async def list_processing_jobs(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: Optional[int] = Query(50, description="Maximum number of jobs to return"),
    offset: Optional[int] = Query(0, description="Number of jobs to skip"),
    meeting_processor: MeetingProcessor = Depends(get_meeting_processor)
):
    """
    List processing jobs with optional filtering
    
    Args:
        user_id: Filter by user ID
        status: Filter by processing status
        limit: Maximum results to return
        offset: Results to skip
        
    Returns:
        JobListResponse with job list and statistics
    """
    logger.info(f"📋 Listing processing jobs - user: {user_id}, status: {status}")
    
    try:
        # Get all jobs (in a real implementation, this would support pagination)
        jobs = []
        active_count = 0
        completed_count = 0
        
        # Get processing statistics
        stats = meeting_processor.get_processing_statistics()
        
        # For demonstration, return basic statistics
        # In a real implementation, you would iterate through jobs and apply filters
        
        return JobListResponse(
            success=True,
            jobs=jobs,
            total_count=stats.total_jobs,
            active_count=stats.active_jobs,
            completed_count=stats.completed_jobs
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to list processing jobs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list jobs: {str(e)}")


@router.get("/result/{job_id}", response_model=ProcessingResultResponse)
async def get_processing_result(
    job_id: str,
    include_raw_data: bool = Query(False, description="Include raw extraction data"),
    meeting_processor: MeetingProcessor = Depends(get_meeting_processor)
):
    """
    Get processing result for a completed job
    
    Args:
        job_id: Processing job ID
        include_raw_data: Include raw extraction data in response
        
    Returns:
        ProcessingResultResponse with meeting minutes and generation info
    """
    logger.info(f"📄 Getting processing result: {job_id}")
    
    try:
        # Get job status first
        status = await meeting_processor.get_job_status(job_id)
        if not status:
            raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
        
        if status['stage'] != ProcessingStage.COMPLETED.value:
            return ProcessingResultResponse(
                success=False,
                job_id=job_id,
                error=f"Job not completed yet. Current stage: {status['stage']}"
            )
        
        # Get meeting minutes result
        meeting_minutes = await meeting_processor.get_job_result(job_id)
        if not meeting_minutes:
            return ProcessingResultResponse(
                success=False,
                job_id=job_id,
                error="No processing result available"
            )
        
        # Convert meeting minutes to dict
        minutes_dict = {
            'basic_info': {
                'title': meeting_minutes.basic_info.title,
                'date': meeting_minutes.basic_info.date,
                'time': meeting_minutes.basic_info.time,
                'location': meeting_minutes.basic_info.location,
                'duration': meeting_minutes.basic_info.duration,
                'organizer': meeting_minutes.basic_info.organizer
            } if meeting_minutes.basic_info else None,
            'attendees': [
                {
                    'name': att.name,
                    'role': att.role,
                    'organization': att.organization,
                    'present': att.present
                }
                for att in meeting_minutes.attendees
            ],
            'agenda': [
                {
                    'title': topic.title,
                    'description': topic.description,
                    'presenter': topic.presenter,
                    'key_points': topic.key_points
                }
                for topic in meeting_minutes.agenda
            ],
            'action_items': [
                {
                    'task': item.task,
                    'assignee': item.assignee,
                    'due_date': item.due_date,
                    'priority': item.priority,
                    'status': item.status
                }
                for item in meeting_minutes.action_items
            ],
            'decisions': [
                {
                    'decision': dec.decision,
                    'rationale': dec.rationale,
                    'impact': dec.impact,
                    'responsible_party': dec.responsible_party
                }
                for dec in meeting_minutes.decisions
            ],
            'key_outcomes': meeting_minutes.key_outcomes,
            'additional_notes': meeting_minutes.additional_notes,
            'next_meeting': meeting_minutes.next_meeting
        }
        
        # Prepare result
        result = {
            'extraction_status': 'completed',
            'confidence_score': status.get('confidence_score', 0.0),
            'processing_metadata': status.get('metadata', {}),
            'data_quality': {
                'has_basic_info': bool(meeting_minutes.basic_info and meeting_minutes.basic_info.title),
                'attendees_count': len(meeting_minutes.attendees),
                'agenda_items_count': len(meeting_minutes.agenda),
                'action_items_count': len(meeting_minutes.action_items),
                'decisions_count': len(meeting_minutes.decisions),
                'outcomes_count': len(meeting_minutes.key_outcomes)
            }
        }
        
        if include_raw_data:
            result['raw_extraction_data'] = status.get('metadata', {}).get('extraction_metadata', {})
        
        return ProcessingResultResponse(
            success=True,
            job_id=job_id,
            result=result,
            meeting_minutes=minutes_dict,
            generation_info={
                'processing_time': status.get('metadata', {}).get('processing_time'),
                'created_at': status['created_at'],
                'completed_at': status['completed_at']
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get processing result for {job_id}: {e}")
        return ProcessingResultResponse(
            success=False,
            job_id=job_id,
            error=str(e)
        )


@router.post("/cancel/{job_id}", response_model=JobControlResponse)
async def cancel_processing_job(
    job_id: str,
    meeting_processor: MeetingProcessor = Depends(get_meeting_processor)
):
    """
    Cancel a processing job
    
    Args:
        job_id: Processing job ID
        
    Returns:
        JobControlResponse with cancellation status
    """
    logger.info(f"❌ Cancelling processing job: {job_id}")
    
    try:
        success = await meeting_processor.cancel_job(job_id)
        
        if success:
            return JobControlResponse(
                success=True,
                job_id=job_id,
                action="cancel",
                message="Job cancelled successfully"
            )
        else:
            return JobControlResponse(
                success=False,
                job_id=job_id,
                action="cancel",
                message="Failed to cancel job - job not found or already completed"
            )
        
    except Exception as e:
        logger.error(f"❌ Failed to cancel job {job_id}: {e}")
        return JobControlResponse(
            success=False,
            job_id=job_id,
            action="cancel",
            message=f"Cancellation failed: {str(e)}"
        )


@router.post("/retry/{job_id}", response_model=JobControlResponse)
async def retry_failed_job(
    job_id: str,
    meeting_processor: MeetingProcessor = Depends(get_meeting_processor)
):
    """
    Retry a failed processing job
    
    Args:
        job_id: Processing job ID
        
    Returns:
        JobControlResponse with retry status
    """
    logger.info(f"🔄 Retrying failed job: {job_id}")
    
    try:
        success = await meeting_processor.retry_failed_job(job_id)
        
        if success:
            return JobControlResponse(
                success=True,
                job_id=job_id,
                action="retry",
                message="Job retry initiated successfully"
            )
        else:
            return JobControlResponse(
                success=False,
                job_id=job_id,
                action="retry",
                message="Failed to retry job - job not found, not failed, or max retries reached"
            )
        
    except Exception as e:
        logger.error(f"❌ Failed to retry job {job_id}: {e}")
        return JobControlResponse(
            success=False,
            job_id=job_id,
            action="retry",
            message=f"Retry failed: {str(e)}"
        )


@router.get("/statistics", response_model=ProcessingStatsResponse)
async def get_processing_statistics(
    meeting_processor: MeetingProcessor = Depends(get_meeting_processor),
    file_processor: FileProcessor = Depends(get_file_processor)
):
    """
    Get comprehensive processing statistics
    
    Returns:
        ProcessingStatsResponse with system statistics
    """
    logger.info("📈 Getting processing statistics")
    
    try:
        # Get processing statistics
        processing_stats = meeting_processor.get_processing_statistics()
        file_stats = file_processor.get_processing_stats()
        
        # Combine statistics
        combined_stats = {
            'processing': {
                'total_jobs': processing_stats.total_jobs,
                'active_jobs': processing_stats.active_jobs,
                'completed_jobs': processing_stats.completed_jobs,
                'failed_jobs': processing_stats.failed_jobs,
                'success_rate': processing_stats.success_rate,
                'average_processing_time': processing_stats.average_processing_time
            },
            'files': {
                'total_files': file_stats['total_files'],
                'status_distribution': file_stats['status_distribution'],
                'total_size_bytes': file_stats['total_size_bytes'],
                'memory_usage_estimate': file_stats['memory_usage_estimate']
            },
            'system': {
                'uptime_info': 'System running normally',
                'last_updated': datetime.utcnow().isoformat()
            }
        }
        
        return ProcessingStatsResponse(
            success=True,
            statistics=combined_stats
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to get processing statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")


@router.get("/health")
async def get_processing_health(
    meeting_processor: MeetingProcessor = Depends(get_meeting_processor)
):
    """
    Get processing system health status
    
    Returns:
        System health information
    """
    try:
        stats = meeting_processor.get_processing_statistics()
        
        # Determine health status
        health_status = "healthy"
        issues = []
        
        # Check for high failure rate
        if stats.success_rate < 0.8:
            health_status = "warning"
            issues.append(f"Low success rate: {stats.success_rate:.1%}")
        
        # Check for stuck jobs
        if stats.active_jobs > 10:  # Arbitrary threshold
            health_status = "warning" 
            issues.append(f"High number of active jobs: {stats.active_jobs}")
        
        # Check average processing time
        if stats.average_processing_time > 300:  # 5 minutes
            if health_status == "healthy":
                health_status = "warning"
            issues.append(f"Slow processing: {stats.average_processing_time:.1f}s average")
        
        return {
            'success': True,
            'health_status': health_status,
            'issues': issues,
            'metrics': {
                'total_jobs': stats.total_jobs,
                'active_jobs': stats.active_jobs,
                'success_rate': stats.success_rate,
                'average_processing_time': stats.average_processing_time
            },
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get processing health: {e}")
        return {
            'success': False,
            'health_status': 'error',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }


@router.websocket("/ws/status/{job_id}")
async def websocket_processing_status(
    websocket,
    job_id: str,
    meeting_processor: MeetingProcessor = Depends(get_meeting_processor)
):
    """
    WebSocket endpoint for real-time processing status updates
    
    Args:
        websocket: WebSocket connection
        job_id: Processing job ID
    """
    await websocket.accept()
    logger.info(f"🔗 WebSocket connected for job: {job_id}")
    
    try:
        import asyncio
        
        while True:
            # Get current status
            status = await meeting_processor.get_job_status(job_id)
            
            if not status:
                await websocket.send_json({
                    'success': False,
                    'error': 'Job not found'
                })
                break
            
            # Send status update
            await websocket.send_json({
                'success': True,
                'job_id': job_id,
                'status': status,
                'timestamp': datetime.utcnow().isoformat()
            })
            
            # Check if job is completed or failed
            if status['stage'] in ['completed', 'failed', 'cancelled']:
                logger.info(f"✅ Job {job_id} finished: {status['stage']}")
                break
            
            # Wait before next update
            await asyncio.sleep(2)
            
    except Exception as e:
        logger.error(f"❌ WebSocket error for job {job_id}: {e}")
        await websocket.send_json({
            'success': False,
            'error': str(e)
        })
    finally:
        await websocket.close()
        logger.info(f"🔌 WebSocket disconnected for job: {job_id}")