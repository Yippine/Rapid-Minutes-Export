"""
Template Generation Controller (B3 - Business Logic Layer)
Word template processing and data injection coordination
Implements ICE principle - Intuitive template processing with comprehensive coverage
"""

import logging
import os
import shutil
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
import json

from ..ai.extractor import MeetingMinutes
from ..config import settings
from ..storage.template_storage import TemplateStorage
from ..storage.output_manager import OutputManager
from ..document.word_engine import WordEngine
from ..document.data_injector import DataInjector

logger = logging.getLogger(__name__)


class TemplateType(Enum):
    """Template types for different meeting formats"""
    STANDARD = "standard"
    EXECUTIVE = "executive" 
    PROJECT = "project"
    BOARD = "board"
    TEAM = "team"
    CUSTOM = "custom"


class GenerationStatus(Enum):
    """Template generation status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TemplateConfig:
    """Template configuration"""
    template_id: str
    template_type: TemplateType
    template_path: str
    name: str
    description: str
    version: str = "1.0.0"
    language: str = "zh-TW"
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    field_mappings: Dict[str, str] = field(default_factory=dict)
    is_active: bool = True


@dataclass
class GenerationJob:
    """Template generation job"""
    job_id: str
    meeting_minutes: MeetingMinutes
    template_config: TemplateConfig
    output_filename: str
    status: GenerationStatus = GenerationStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: float = 0.0
    status_message: str = "Generation queued"
    output_path: Optional[str] = None
    error_message: Optional[str] = None
    generation_options: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GenerationResult:
    """Template generation result"""
    job_id: str
    status: GenerationStatus
    output_path: Optional[str] = None
    file_size: Optional[int] = None
    generation_time: Optional[float] = None
    template_used: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class TemplateController:
    """
    Template generation controller
    Manages Word template processing and data injection workflow
    """
    
    def __init__(
        self,
        template_storage: Optional[TemplateStorage] = None,
        output_manager: Optional[OutputManager] = None,
        word_engine: Optional[WordEngine] = None,
        data_injector: Optional[DataInjector] = None
    ):
        """Initialize template controller with dependencies"""
        self.template_storage = template_storage or TemplateStorage()
        self.output_manager = output_manager or OutputManager()
        self.word_engine = word_engine or WordEngine()
        self.data_injector = data_injector or DataInjector()
        
        # Job management
        self._active_jobs: Dict[str, GenerationJob] = {}
        self._completed_jobs: Dict[str, GenerationJob] = {}
        
        # Template registry
        self._template_configs: Dict[str, TemplateConfig] = {}
        
        # Load available templates
        self._load_available_templates()
        
        logger.info("📝 Template Controller initialized")
    
    async def generate_document(
        self,
        meeting_minutes: MeetingMinutes,
        template_type: TemplateType = TemplateType.STANDARD,
        output_filename: Optional[str] = None,
        generation_options: Optional[Dict] = None
    ) -> GenerationResult:
        """
        Generate Word document from meeting minutes
        
        Args:
            meeting_minutes: Extracted meeting minutes data
            template_type: Type of template to use
            output_filename: Desired output filename
            generation_options: Generation options
            
        Returns:
            GenerationResult with document generation results
        """
        generation_options = generation_options or {}
        
        # Generate job ID and filename
        job_id = self._generate_job_id()
        if not output_filename:
            output_filename = self._generate_output_filename(meeting_minutes, template_type)
        
        logger.info(f"📄 Starting document generation: {job_id}")
        
        # Get template configuration
        template_config = await self._get_template_config(template_type)
        if not template_config:
            return GenerationResult(
                job_id=job_id,
                status=GenerationStatus.FAILED,
                error_message=f"Template not found: {template_type.value}"
            )
        
        # Create generation job
        job = GenerationJob(
            job_id=job_id,
            meeting_minutes=meeting_minutes,
            template_config=template_config,
            output_filename=output_filename,
            generation_options=generation_options
        )
        
        try:
            self._active_jobs[job_id] = job
            job.status = GenerationStatus.PROCESSING
            job.started_at = datetime.utcnow()
            
            # Stage 1: Prepare template data
            await self._update_job_progress(job, 0.2, "Preparing template data...")
            template_data = await self._prepare_template_data(meeting_minutes, template_config)
            
            # Stage 2: Process Word template
            await self._update_job_progress(job, 0.5, "Processing Word template...")
            processed_doc = await self.word_engine.process_template(
                template_config.template_path,
                template_data,
                generation_options
            )
            
            # Stage 3: Inject meeting data
            await self._update_job_progress(job, 0.7, "Injecting meeting data...")
            final_doc = await self.data_injector.inject_data(
                processed_doc,
                meeting_minutes,
                template_config
            )
            
            # Stage 4: Save output document
            await self._update_job_progress(job, 0.9, "Saving document...")
            output_path = await self.output_manager.save_document(
                final_doc,
                output_filename,
                job_id
            )
            
            # Complete job
            job.status = GenerationStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            job.output_path = output_path
            job.progress = 1.0
            job.status_message = "Document generated successfully"
            
            # Calculate generation time
            generation_time = (job.completed_at - job.started_at).total_seconds()
            
            # Get file size
            file_size = os.path.getsize(output_path) if os.path.exists(output_path) else None
            
            # Move to completed jobs
            self._completed_jobs[job_id] = job
            if job_id in self._active_jobs:
                del self._active_jobs[job_id]
            
            logger.info(f"✅ Document generation completed: {job_id} ({generation_time:.2f}s)")
            
            return GenerationResult(
                job_id=job_id,
                status=GenerationStatus.COMPLETED,
                output_path=output_path,
                file_size=file_size,
                generation_time=generation_time,
                template_used=template_config.name,
                metadata={
                    'template_type': template_type.value,
                    'generation_options': generation_options,
                    'meeting_basic_info': {
                        'title': meeting_minutes.basic_info.title,
                        'date': meeting_minutes.basic_info.date,
                        'attendees_count': len(meeting_minutes.attendees)
                    }
                }
            )
            
        except Exception as e:
            return await self._handle_generation_error(job, str(e))
    
    async def get_available_templates(self) -> List[Dict[str, Any]]:
        """Get list of available templates"""
        templates = []
        for template_id, config in self._template_configs.items():
            if config.is_active:
                templates.append({
                    'template_id': template_id,
                    'name': config.name,
                    'description': config.description,
                    'type': config.template_type.value,
                    'version': config.version,
                    'language': config.language,
                    'created_at': config.created_at.isoformat()
                })
        
        return sorted(templates, key=lambda x: x['name'])
    
    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get generation job status"""
        # Check active jobs
        if job_id in self._active_jobs:
            job = self._active_jobs[job_id]
            return self._serialize_job_status(job)
        
        # Check completed jobs
        if job_id in self._completed_jobs:
            job = self._completed_jobs[job_id]
            return self._serialize_job_status(job)
        
        return None
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a generation job"""
        if job_id not in self._active_jobs:
            return False
        
        job = self._active_jobs[job_id]
        job.status = GenerationStatus.CANCELLED
        job.status_message = "Job cancelled by user"
        job.completed_at = datetime.utcnow()
        
        # Move to completed jobs
        self._completed_jobs[job_id] = job
        del self._active_jobs[job_id]
        
        logger.info(f"❌ Generation job cancelled: {job_id}")
        return True
    
    async def preview_template_fields(self, template_type: TemplateType) -> Dict[str, Any]:
        """Preview template fields and mappings"""
        template_config = await self._get_template_config(template_type)
        if not template_config:
            return {}
        
        return {
            'template_name': template_config.name,
            'template_type': template_type.value,
            'available_fields': list(template_config.field_mappings.keys()),
            'field_mappings': template_config.field_mappings,
            'template_metadata': template_config.metadata
        }
    
    def get_generation_statistics(self) -> Dict[str, Any]:
        """Get template generation statistics"""
        total_jobs = len(self._active_jobs) + len(self._completed_jobs)
        completed_jobs = len(self._completed_jobs)
        failed_jobs = sum(1 for job in self._completed_jobs.values() 
                         if job.status == GenerationStatus.FAILED)
        
        # Calculate average generation time
        completed_times = [
            (job.completed_at - job.started_at).total_seconds()
            for job in self._completed_jobs.values()
            if job.started_at and job.completed_at and job.status == GenerationStatus.COMPLETED
        ]
        
        avg_time = sum(completed_times) / len(completed_times) if completed_times else 0
        
        return {
            'total_jobs': total_jobs,
            'active_jobs': len(self._active_jobs),
            'completed_jobs': completed_jobs,
            'failed_jobs': failed_jobs,
            'success_rate': (completed_jobs - failed_jobs) / completed_jobs if completed_jobs > 0 else 0,
            'average_generation_time': avg_time,
            'available_templates': len(self._template_configs)
        }
    
    # Private methods
    
    def _generate_job_id(self) -> str:
        """Generate unique job ID"""
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        import uuid
        return f"doc_{timestamp}_{str(uuid.uuid4())[:8]}"
    
    def _generate_output_filename(
        self, 
        meeting_minutes: MeetingMinutes, 
        template_type: TemplateType
    ) -> str:
        """Generate output filename based on meeting info"""
        # Try to use meeting title and date
        title = meeting_minutes.basic_info.title or "Meeting"
        date = meeting_minutes.basic_info.date or datetime.utcnow().strftime('%Y-%m-%d')
        
        # Clean filename
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '_', '-')).rstrip()
        safe_title = safe_title.replace(' ', '_')[:50]  # Limit length
        
        return f"{safe_title}_{date}_{template_type.value}.docx"
    
    async def _get_template_config(self, template_type: TemplateType) -> Optional[TemplateConfig]:
        """Get template configuration by type"""
        for config in self._template_configs.values():
            if config.template_type == template_type and config.is_active:
                return config
        return None
    
    async def _prepare_template_data(
        self, 
        meeting_minutes: MeetingMinutes,
        template_config: TemplateConfig
    ) -> Dict[str, Any]:
        """Prepare data for template processing"""
        # Basic meeting information
        basic_data = {
            'meeting_title': meeting_minutes.basic_info.title or "Meeting Minutes",
            'meeting_date': meeting_minutes.basic_info.date or datetime.utcnow().strftime('%Y-%m-%d'),
            'meeting_time': meeting_minutes.basic_info.time or "",
            'meeting_location': meeting_minutes.basic_info.location or "",
            'meeting_duration': meeting_minutes.basic_info.duration or "",
            'meeting_organizer': meeting_minutes.basic_info.organizer or "",
            'generation_date': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Attendees data
        attendees_data = []
        for attendee in meeting_minutes.attendees:
            attendees_data.append({
                'name': attendee.name,
                'role': attendee.role or "",
                'organization': attendee.organization or "",
                'present': "出席" if attendee.present else "缺席"
            })
        
        # Agenda/discussion topics
        agenda_data = []
        for topic in meeting_minutes.agenda:
            agenda_data.append({
                'title': topic.title,
                'description': topic.description or "",
                'presenter': topic.presenter or "",
                'key_points': topic.key_points or []
            })
        
        # Action items
        actions_data = []
        for action in meeting_minutes.action_items:
            actions_data.append({
                'task': action.task,
                'assignee': action.assignee or "",
                'due_date': action.due_date or "",
                'priority': action.priority or "",
                'status': action.status or "待處理"
            })
        
        # Decisions
        decisions_data = []
        for decision in meeting_minutes.decisions:
            decisions_data.append({
                'decision': decision.decision,
                'rationale': decision.rationale or "",
                'impact': decision.impact or "",
                'responsible_party': decision.responsible_party or ""
            })
        
        return {
            'basic_info': basic_data,
            'attendees': attendees_data,
            'agenda': agenda_data,
            'action_items': actions_data,
            'decisions': decisions_data,
            'key_outcomes': meeting_minutes.key_outcomes or [],
            'additional_notes': meeting_minutes.additional_notes or "",
            'next_meeting': meeting_minutes.next_meeting or {}
        }
    
    async def _handle_generation_error(self, job: GenerationJob, error_message: str) -> GenerationResult:
        """Handle generation error"""
        job.status = GenerationStatus.FAILED
        job.error_message = error_message
        job.status_message = f"Generation failed: {error_message}"
        job.completed_at = datetime.utcnow()
        
        # Move to completed jobs
        self._completed_jobs[job.job_id] = job
        if job.job_id in self._active_jobs:
            del self._active_jobs[job.job_id]
        
        generation_time = (job.completed_at - job.started_at).total_seconds() if job.started_at else 0
        
        logger.error(f"❌ Document generation failed: {job.job_id} - {error_message}")
        
        return GenerationResult(
            job_id=job.job_id,
            status=GenerationStatus.FAILED,
            error_message=error_message,
            generation_time=generation_time
        )
    
    async def _update_job_progress(self, job: GenerationJob, progress: float, message: str):
        """Update job progress"""
        job.progress = progress
        job.status_message = message
        logger.debug(f"📈 Generation job {job.job_id}: {progress*100:.1f}% - {message}")
    
    def _serialize_job_status(self, job: GenerationJob) -> Dict[str, Any]:
        """Serialize job status for API response"""
        return {
            'job_id': job.job_id,
            'status': job.status.value,
            'progress': job.progress,
            'status_message': job.status_message,
            'template_type': job.template_config.template_type.value,
            'template_name': job.template_config.name,
            'output_filename': job.output_filename,
            'created_at': job.created_at.isoformat(),
            'started_at': job.started_at.isoformat() if job.started_at else None,
            'completed_at': job.completed_at.isoformat() if job.completed_at else None,
            'output_path': job.output_path,
            'error_message': job.error_message,
            'metadata': job.metadata
        }
    
    def _load_available_templates(self):
        """Load available template configurations"""
        # Standard meeting template
        self._template_configs['standard'] = TemplateConfig(
            template_id='standard',
            template_type=TemplateType.STANDARD,
            template_path='templates/standard_meeting_template.docx',
            name='標準會議記錄模板',
            description='適用於一般會議的標準格式模板',
            field_mappings={
                'meeting_title': '會議標題',
                'meeting_date': '會議日期', 
                'attendees': '出席人員',
                'agenda': '議程項目',
                'action_items': '行動項目',
                'decisions': '決議事項'
            }
        )
        
        # Executive meeting template
        self._template_configs['executive'] = TemplateConfig(
            template_id='executive',
            template_type=TemplateType.EXECUTIVE,
            template_path='templates/executive_meeting_template.docx',
            name='高階主管會議模板',
            description='適用於高階主管會議的正式格式模板',
            field_mappings={
                'meeting_title': '會議標題',
                'meeting_date': '會議日期',
                'attendees': '與會主管',
                'key_outcomes': '重要決議',
                'strategic_decisions': '策略決定'
            }
        )
        
        # Project meeting template
        self._template_configs['project'] = TemplateConfig(
            template_id='project',
            template_type=TemplateType.PROJECT,
            template_path='templates/project_meeting_template.docx',
            name='專案會議模板',
            description='適用於專案進度會議的結構化模板',
            field_mappings={
                'project_name': '專案名稱',
                'meeting_date': '會議日期',
                'project_status': '專案狀態',
                'milestones': '里程碑',
                'action_items': '待辦事項',
                'risks': '風險議題'
            }
        )
        
        logger.info(f"📚 Loaded {len(self._template_configs)} template configurations")