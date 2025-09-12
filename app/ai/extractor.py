"""
Structured Data Extractor Module (C3 - AI Processing Layer)
Advanced meeting minutes extraction using Ollama LLM
Implements 82 Rule principle - core 20% AI functionality for 80% extraction effectiveness
"""

import json
import logging
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import re
import asyncio

from .ollama_client import OllamaClient, GenerationResponse
from .text_preprocessor import TextPreprocessor, PreprocessedText
from ..config import settings

logger = logging.getLogger(__name__)


class ExtractionStatus(Enum):
    """Extraction process status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    VALIDATION_FAILED = "validation_failed"


@dataclass
class MeetingBasicInfo:
    """Basic meeting information"""
    title: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None
    duration: Optional[str] = None
    location: Optional[str] = None
    meeting_type: Optional[str] = None
    organizer: Optional[str] = None


@dataclass
class Attendee:
    """Meeting attendee information"""
    name: str
    role: Optional[str] = None
    organization: Optional[str] = None
    email: Optional[str] = None
    present: bool = True


@dataclass
class DiscussionTopic:
    """Discussion topic information"""
    title: str
    description: Optional[str] = None
    presenter: Optional[str] = None
    duration: Optional[str] = None
    key_points: List[str] = None
    
    def __post_init__(self):
        if self.key_points is None:
            self.key_points = []


@dataclass
class ActionItem:
    """Action item information"""
    task: str
    assignee: Optional[str] = None
    due_date: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class Decision:
    """Meeting decision information"""
    decision: str
    rationale: Optional[str] = None
    impact: Optional[str] = None
    responsible_party: Optional[str] = None
    implementation_date: Optional[str] = None


@dataclass
class MeetingMinutes:
    """Complete meeting minutes structure"""
    basic_info: MeetingBasicInfo
    attendees: List[Attendee]
    agenda: List[DiscussionTopic] 
    action_items: List[ActionItem]
    decisions: List[Decision]
    key_outcomes: List[str]
    next_meeting: Optional[Dict[str, str]] = None
    additional_notes: Optional[str] = None
    
    def __post_init__(self):
        # Ensure lists are not None
        if self.attendees is None:
            self.attendees = []
        if self.agenda is None:
            self.agenda = []
        if self.action_items is None:
            self.action_items = []
        if self.decisions is None:
            self.decisions = []
        if self.key_outcomes is None:
            self.key_outcomes = []


@dataclass
class ExtractionResult:
    """Extraction process result"""
    status: ExtractionStatus
    minutes: Optional[MeetingMinutes] = None
    confidence_score: float = 0.0
    extraction_metadata: Dict[str, Any] = None
    validation_results: Dict[str, bool] = None
    error_message: Optional[str] = None
    processing_time: Optional[float] = None
    
    def __post_init__(self):
        if self.extraction_metadata is None:
            self.extraction_metadata = {}
        if self.validation_results is None:
            self.validation_results = {}


class StructuredDataExtractor:
    """
    Advanced structured data extractor for meeting minutes
    Uses Ollama LLM to extract structured information from preprocessed text
    """
    
    def __init__(self, ollama_client: Optional[OllamaClient] = None):
        """Initialize extractor with Ollama client"""
        self.ollama_client = ollama_client or OllamaClient()
        self.text_preprocessor = TextPreprocessor()
        self.extraction_prompts = self._setup_extraction_prompts()
        self.validation_rules = self._setup_validation_rules()
        
        logger.info("🔍 Structured Data Extractor initialized")
    
    def _setup_extraction_prompts(self) -> Dict[str, str]:
        """Setup extraction prompts for different information types"""
        return {
            'basic_info': '''
You are an expert meeting minutes analyzer. Extract basic meeting information from the following text.
Return ONLY a JSON object with these exact fields (use null for missing information):
{
    "title": "meeting title or subject",
    "date": "meeting date in YYYY-MM-DD format", 
    "time": "meeting time",
    "duration": "meeting duration",
    "location": "meeting location or platform",
    "meeting_type": "type of meeting",
    "organizer": "meeting organizer name"
}

Text to analyze:
{text}

JSON Response:''',
            
            'attendees': '''
You are an expert meeting minutes analyzer. Extract attendee information from the following text.
Return ONLY a JSON array of attendee objects with these exact fields:
[
    {
        "name": "full name",
        "role": "job title or role",
        "organization": "company or department", 
        "email": "email address if mentioned",
        "present": true
    }
]

Text to analyze:
{text}

JSON Response:''',
            
            'agenda': '''
You are an expert meeting minutes analyzer. Extract discussion topics and agenda items from the following text.
Return ONLY a JSON array of topic objects with these exact fields:
[
    {
        "title": "topic or agenda item title",
        "description": "brief description of discussion",
        "presenter": "who presented or led the discussion",
        "duration": "time spent on topic if mentioned",
        "key_points": ["key point 1", "key point 2", "key point 3"]
    }
]

Text to analyze:
{text}

JSON Response:''',
            
            'action_items': '''
You are an expert meeting minutes analyzer. Extract action items and tasks from the following text.
Return ONLY a JSON array of action item objects with these exact fields:
[
    {
        "task": "description of task or action",
        "assignee": "person responsible for the task",
        "due_date": "deadline in YYYY-MM-DD format if mentioned",
        "priority": "high/medium/low priority if mentioned",
        "status": "current status if mentioned",
        "notes": "additional notes about the task"
    }
]

Text to analyze:
{text}

JSON Response:''',
            
            'decisions': '''
You are an expert meeting minutes analyzer. Extract decisions made during the meeting from the following text.
Return ONLY a JSON array of decision objects with these exact fields:
[
    {
        "decision": "the decision that was made",
        "rationale": "reasoning behind the decision",
        "impact": "expected impact or consequences",
        "responsible_party": "person or team responsible for implementation",
        "implementation_date": "when decision takes effect in YYYY-MM-DD format"
    }
]

Text to analyze:
{text}

JSON Response:''',
            
            'key_outcomes': '''
You are an expert meeting minutes analyzer. Extract key outcomes and summary points from the following text.
Return ONLY a JSON array of strings representing key outcomes:
["outcome 1", "outcome 2", "outcome 3"]

Text to analyze:
{text}

JSON Response:'''
        }
    
    def _setup_validation_rules(self) -> Dict[str, callable]:
        """Setup validation rules for extracted data"""
        return {
            'basic_info': self._validate_basic_info,
            'attendees': self._validate_attendees,
            'agenda': self._validate_agenda,
            'action_items': self._validate_action_items,
            'decisions': self._validate_decisions,
            'key_outcomes': self._validate_key_outcomes
        }
    
    async def extract_meeting_minutes(
        self, 
        text: str,
        preprocessing_options: Optional[Dict] = None,
        extraction_options: Optional[Dict] = None
    ) -> ExtractionResult:
        """
        Main method to extract structured meeting minutes from text
        
        Args:
            text: Raw meeting transcript text
            preprocessing_options: Options for text preprocessing
            extraction_options: Options for extraction process
            
        Returns:
            ExtractionResult with structured meeting minutes
        """
        start_time = datetime.utcnow()
        logger.info(f"🚀 Starting meeting minutes extraction - text length: {len(text)}")
        
        try:
            # Step 1: Preprocess text
            preprocessed = await self.text_preprocessor.preprocess(text, preprocessing_options)
            logger.info(f"✅ Text preprocessing completed - {len(preprocessed.segments)} segments")
            
            # Step 2: Extract structured data
            extraction_result = await self._extract_all_components(preprocessed, extraction_options)
            
            # Step 3: Validate extracted data
            validation_results = await self._validate_extraction(extraction_result)
            
            # Step 4: Calculate confidence score
            confidence_score = self._calculate_confidence_score(extraction_result, validation_results)
            
            # Step 5: Generate metadata
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            metadata = {
                'processing_time': processing_time,
                'preprocessing_stats': preprocessed.preprocessing_stats,
                'text_segments': len(preprocessed.segments),
                'extraction_timestamp': datetime.utcnow().isoformat(),
                'model_used': self.ollama_client.model,
                'preprocessing_metadata': preprocessed.metadata
            }
            
            result = ExtractionResult(
                status=ExtractionStatus.COMPLETED if all(validation_results.values()) else ExtractionStatus.VALIDATION_FAILED,
                minutes=extraction_result,
                confidence_score=confidence_score,
                extraction_metadata=metadata,
                validation_results=validation_results,
                processing_time=processing_time
            )
            
            logger.info(f"✅ Extraction completed - confidence: {confidence_score:.2f}, time: {processing_time:.2f}s")
            return result
            
        except Exception as e:
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"❌ Extraction failed: {e}")
            
            return ExtractionResult(
                status=ExtractionStatus.FAILED,
                error_message=str(e),
                processing_time=processing_time
            )
    
    async def _extract_all_components(
        self, 
        preprocessed: PreprocessedText,
        options: Optional[Dict] = None
    ) -> MeetingMinutes:
        """Extract all meeting components from preprocessed text"""
        options = options or {}
        
        # Prepare full text for extraction
        full_text = preprocessed.cleaned_text
        
        logger.info("🔍 Starting structured data extraction...")
        
        # Extract components in parallel for efficiency
        extraction_tasks = {
            'basic_info': self._extract_basic_info(full_text),
            'attendees': self._extract_attendees(full_text),
            'agenda': self._extract_agenda(full_text),
            'action_items': self._extract_action_items(full_text),
            'decisions': self._extract_decisions(full_text),
            'key_outcomes': self._extract_key_outcomes(full_text)
        }
        
        # Execute extractions concurrently
        results = await asyncio.gather(*extraction_tasks.values(), return_exceptions=True)
        component_results = dict(zip(extraction_tasks.keys(), results))
        
        # Handle any extraction failures
        for component, result in component_results.items():
            if isinstance(result, Exception):
                logger.warning(f"⚠️ Failed to extract {component}: {result}")
                component_results[component] = self._get_default_component(component)
        
        # Assemble complete meeting minutes
        meeting_minutes = MeetingMinutes(
            basic_info=component_results['basic_info'],
            attendees=component_results['attendees'],
            agenda=component_results['agenda'],
            action_items=component_results['action_items'],
            decisions=component_results['decisions'],
            key_outcomes=component_results['key_outcomes']
        )
        
        logger.info("✅ All components extracted successfully")
        return meeting_minutes
    
    async def _extract_basic_info(self, text: str) -> MeetingBasicInfo:
        """Extract basic meeting information"""
        prompt = self.extraction_prompts['basic_info'].format(text=text[:2000])  # Limit text length
        
        try:
            response = await self.ollama_client.generate(
                prompt=prompt,
                format='json',
                options={'temperature': 0.1, 'top_p': 0.9}
            )
            
            data = json.loads(response.content)
            return MeetingBasicInfo(**data)
            
        except (json.JSONDecodeError, TypeError, KeyError) as e:
            logger.warning(f"⚠️ Failed to parse basic info JSON: {e}")
            return MeetingBasicInfo()
    
    async def _extract_attendees(self, text: str) -> List[Attendee]:
        """Extract attendee information"""
        prompt = self.extraction_prompts['attendees'].format(text=text[:2000])
        
        try:
            response = await self.ollama_client.generate(
                prompt=prompt,
                format='json',
                options={'temperature': 0.1}
            )
            
            data = json.loads(response.content)
            return [Attendee(**attendee) for attendee in data if isinstance(attendee, dict)]
            
        except (json.JSONDecodeError, TypeError, KeyError) as e:
            logger.warning(f"⚠️ Failed to parse attendees JSON: {e}")
            return []
    
    async def _extract_agenda(self, text: str) -> List[DiscussionTopic]:
        """Extract discussion topics and agenda"""
        prompt = self.extraction_prompts['agenda'].format(text=text)
        
        try:
            response = await self.ollama_client.generate(
                prompt=prompt,
                format='json',
                options={'temperature': 0.2}
            )
            
            data = json.loads(response.content)
            topics = []
            for topic in data:
                if isinstance(topic, dict):
                    # Ensure key_points is a list
                    if topic.get('key_points') and not isinstance(topic['key_points'], list):
                        topic['key_points'] = []
                    topics.append(DiscussionTopic(**topic))
            
            return topics
            
        except (json.JSONDecodeError, TypeError, KeyError) as e:
            logger.warning(f"⚠️ Failed to parse agenda JSON: {e}")
            return []
    
    async def _extract_action_items(self, text: str) -> List[ActionItem]:
        """Extract action items"""
        prompt = self.extraction_prompts['action_items'].format(text=text)
        
        try:
            response = await self.ollama_client.generate(
                prompt=prompt,
                format='json',
                options={'temperature': 0.1}
            )
            
            data = json.loads(response.content)
            return [ActionItem(**item) for item in data if isinstance(item, dict)]
            
        except (json.JSONDecodeError, TypeError, KeyError) as e:
            logger.warning(f"⚠️ Failed to parse action items JSON: {e}")
            return []
    
    async def _extract_decisions(self, text: str) -> List[Decision]:
        """Extract decisions made in the meeting"""
        prompt = self.extraction_prompts['decisions'].format(text=text)
        
        try:
            response = await self.ollama_client.generate(
                prompt=prompt,
                format='json',
                options={'temperature': 0.1}
            )
            
            data = json.loads(response.content)
            return [Decision(**decision) for decision in data if isinstance(decision, dict)]
            
        except (json.JSONDecodeError, TypeError, KeyError) as e:
            logger.warning(f"⚠️ Failed to parse decisions JSON: {e}")
            return []
    
    async def _extract_key_outcomes(self, text: str) -> List[str]:
        """Extract key outcomes and summary points"""
        prompt = self.extraction_prompts['key_outcomes'].format(text=text[-2000:])  # Use ending text
        
        try:
            response = await self.ollama_client.generate(
                prompt=prompt,
                format='json',
                options={'temperature': 0.2}
            )
            
            data = json.loads(response.content)
            if isinstance(data, list):
                return [str(outcome) for outcome in data if outcome]
            else:
                return []
                
        except (json.JSONDecodeError, TypeError, KeyError) as e:
            logger.warning(f"⚠️ Failed to parse key outcomes JSON: {e}")
            return []
    
    def _get_default_component(self, component: str) -> Any:
        """Get default value for failed component extraction"""
        defaults = {
            'basic_info': MeetingBasicInfo(),
            'attendees': [],
            'agenda': [],
            'action_items': [],
            'decisions': [],
            'key_outcomes': []
        }
        return defaults.get(component, None)
    
    async def _validate_extraction(self, minutes: MeetingMinutes) -> Dict[str, bool]:
        """Validate extracted meeting minutes"""
        validation_results = {}
        
        # Validate each component
        for component, validator in self.validation_rules.items():
            try:
                validation_results[component] = validator(getattr(minutes, component, None))
            except Exception as e:
                logger.warning(f"⚠️ Validation failed for {component}: {e}")
                validation_results[component] = False
        
        # Overall validation
        validation_results['overall'] = all(validation_results.values())
        
        return validation_results
    
    def _validate_basic_info(self, basic_info: MeetingBasicInfo) -> bool:
        """Validate basic meeting information"""
        if not basic_info:
            return False
        
        # At least title or meeting_type should be present
        return bool(basic_info.title or basic_info.meeting_type)
    
    def _validate_attendees(self, attendees: List[Attendee]) -> bool:
        """Validate attendees list"""
        if not attendees:
            return False
        
        # At least one attendee should have a name
        return any(attendee.name for attendee in attendees)
    
    def _validate_agenda(self, agenda: List[DiscussionTopic]) -> bool:
        """Validate agenda/discussion topics"""
        if not agenda:
            return True  # Optional component
        
        # All topics should have a title
        return all(topic.title for topic in agenda)
    
    def _validate_action_items(self, action_items: List[ActionItem]) -> bool:
        """Validate action items"""
        if not action_items:
            return True  # Optional component
        
        # All action items should have a task description
        return all(item.task for item in action_items)
    
    def _validate_decisions(self, decisions: List[Decision]) -> bool:
        """Validate decisions"""
        if not decisions:
            return True  # Optional component
        
        # All decisions should have a decision description
        return all(decision.decision for decision in decisions)
    
    def _validate_key_outcomes(self, key_outcomes: List[str]) -> bool:
        """Validate key outcomes"""
        return True  # Always valid as it's optional
    
    def _calculate_confidence_score(
        self, 
        minutes: MeetingMinutes, 
        validation_results: Dict[str, bool]
    ) -> float:
        """Calculate confidence score for the extraction"""
        # Base score from validation results
        validation_score = sum(validation_results.values()) / len(validation_results) if validation_results else 0
        
        # Content richness score
        richness_score = 0.0
        
        # Basic info contributes 20%
        if minutes.basic_info and (minutes.basic_info.title or minutes.basic_info.meeting_type):
            richness_score += 0.2
        
        # Attendees contribute 20%
        if minutes.attendees and len(minutes.attendees) > 0:
            richness_score += 0.2
        
        # Agenda contributes 20%
        if minutes.agenda and len(minutes.agenda) > 0:
            richness_score += 0.2
        
        # Action items contribute 15%
        if minutes.action_items and len(minutes.action_items) > 0:
            richness_score += 0.15
        
        # Decisions contribute 15%
        if minutes.decisions and len(minutes.decisions) > 0:
            richness_score += 0.15
        
        # Key outcomes contribute 10%
        if minutes.key_outcomes and len(minutes.key_outcomes) > 0:
            richness_score += 0.1
        
        # Combine validation and richness scores
        final_score = (validation_score * 0.6) + (richness_score * 0.4)
        
        return round(min(1.0, max(0.0, final_score)), 2)
    
    async def export_to_json(self, minutes: MeetingMinutes) -> str:
        """Export meeting minutes to JSON format"""
        try:
            data = asdict(minutes)
            return json.dumps(data, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            logger.error(f"❌ Failed to export to JSON: {e}")
            raise
    
    def get_extraction_summary(self, result: ExtractionResult) -> Dict[str, Any]:
        """Get summary of extraction results"""
        if not result.minutes:
            return {'status': result.status.value, 'error': result.error_message}
        
        minutes = result.minutes
        return {
            'status': result.status.value,
            'confidence_score': result.confidence_score,
            'processing_time': result.processing_time,
            'components': {
                'basic_info': bool(minutes.basic_info.title or minutes.basic_info.meeting_type),
                'attendees_count': len(minutes.attendees),
                'agenda_items_count': len(minutes.agenda),
                'action_items_count': len(minutes.action_items),
                'decisions_count': len(minutes.decisions),
                'key_outcomes_count': len(minutes.key_outcomes)
            },
            'validation_results': result.validation_results
        }