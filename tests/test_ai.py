"""
AI Processing Layer Tests  
Tests for text preprocessing, Ollama client, and structured data extraction
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
import json

from app.ai.text_preprocessor import TextPreprocessor, PreprocessedText
from app.ai.ollama_client import OllamaClient, GenerationResponse
from app.ai.extractor import StructuredDataExtractor, MeetingMinutes, ExtractionStatus


class TestTextPreprocessor:
    """Text preprocessor tests"""
    
    @pytest.fixture
    def preprocessor(self):
        """Create text preprocessor instance"""
        return TextPreprocessor()
    
    @pytest.fixture
    def sample_messy_text(self):
        """Sample messy meeting text"""
        return """
        Um, so, like, this is the, uh, weekly meeting transcript...
        [NOISE] Speaker 1: John Smith here, uh...
        Speaker 2: Sarah speaking, um... 
        [TIMESTAMP: 10:30 AM]
        So we discussed the project and, uh, made some decisions.
        Action item -- Mike will do the report by Friday.
        """
    
    @pytest.mark.asyncio
    async def test_basic_preprocessing(self, preprocessor, sample_messy_text):
        """Test basic text preprocessing functionality"""
        result = await preprocessor.preprocess(sample_messy_text)
        
        assert isinstance(result, PreprocessedText)
        assert len(result.cleaned_text) < len(result.original_text)
        assert len(result.segments) > 0
        assert result.preprocessing_stats['chars_removed'] > 0
    
    @pytest.mark.asyncio 
    async def test_noise_removal(self, preprocessor):
        """Test noise removal functionality"""
        text = "Um, this is, uh, like, a test, you know?"
        result = await preprocessor.preprocess(text)
        
        # Should remove filler words
        assert "um" not in result.cleaned_text.lower()
        assert "uh" not in result.cleaned_text.lower()
        assert "like" not in result.cleaned_text.lower()
    
    def test_pattern_setup(self, preprocessor):
        """Test that regex patterns are properly initialized"""
        assert hasattr(preprocessor, 'noise_patterns')
        assert hasattr(preprocessor, 'structure_patterns')
        assert hasattr(preprocessor, 'content_patterns')
        
        # Test specific patterns exist
        assert 'filler_words' in preprocessor.noise_patterns
        assert 'speaker_labels' in preprocessor.noise_patterns
        assert 'timestamps' in preprocessor.noise_patterns


class TestOllamaClient:
    """Ollama client tests"""
    
    @pytest.fixture
    def ollama_client(self):
        """Create Ollama client instance"""
        return OllamaClient()
    
    @pytest.mark.asyncio
    async def test_client_initialization(self, ollama_client):
        """Test client initialization"""
        assert ollama_client.base_url is not None
        assert ollama_client.model is not None
        assert ollama_client.session is None  # Not connected yet
    
    @pytest.mark.asyncio
    async def test_health_check_mock(self, ollama_client):
        """Test health check with mocked response"""
        with patch.object(ollama_client, 'session') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={'version': '1.0'})
            mock_session.get.return_value.__aenter__.return_value = mock_response
            
            result = await ollama_client.health_check()
            assert result is True
    
    @pytest.mark.asyncio
    async def test_generation_with_mock(self, ollama_client):
        """Test text generation with mocked Ollama response"""
        mock_response_data = {
            'response': 'Generated text response',
            'model': 'test-model',
            'done': True,
            'total_duration': 1000,
            'context': []
        }
        
        with patch.object(ollama_client, '_generate_single', return_value=GenerationResponse(
            content='Generated text response',
            model='test-model',
            created_at=None,
            done=True,
            total_duration=1000,
            load_duration=0,
            prompt_eval_count=0,
            prompt_eval_duration=0,
            eval_count=0,
            eval_duration=0,
            context=[],
            metadata={}
        )):
            result = await ollama_client.generate("Test prompt")
            assert isinstance(result, GenerationResponse)
            assert result.content == 'Generated text response'


class TestStructuredDataExtractor:
    """Structured data extractor tests"""
    
    @pytest.fixture
    def extractor(self):
        """Create extractor with mocked Ollama client"""
        mock_client = Mock(spec=OllamaClient)
        return StructuredDataExtractor(ollama_client=mock_client)
    
    @pytest.fixture
    def sample_meeting_text(self):
        """Sample meeting text for extraction"""
        return """
        Weekly Team Meeting
        January 15, 2024
        
        Attendees:
        - John Smith (Manager)
        - Sarah Johnson (Developer)  
        - Mike Chen (QA)
        
        Agenda:
        1. Project status update
        2. Budget discussion
        3. Next steps
        
        Action Items:
        - Mike: Complete testing by Friday
        - Sarah: Update documentation
        
        Decisions:
        - Approved additional budget of $5000
        - Extended deadline to January 30th
        """
    
    def test_extractor_initialization(self, extractor):
        """Test extractor initialization"""
        assert extractor.ollama_client is not None
        assert extractor.text_preprocessor is not None
        assert hasattr(extractor, 'extraction_prompts')
        assert hasattr(extractor, 'validation_rules')
    
    def test_extraction_prompts(self, extractor):
        """Test that extraction prompts are properly set up"""
        required_prompts = ['basic_info', 'attendees', 'agenda', 'action_items', 'decisions', 'key_outcomes']
        
        for prompt_type in required_prompts:
            assert prompt_type in extractor.extraction_prompts
            assert len(extractor.extraction_prompts[prompt_type]) > 0
    
    @pytest.mark.asyncio
    async def test_extraction_mock(self, extractor, sample_meeting_text):
        """Test extraction process with mocked responses"""
        # Mock the Ollama client responses
        mock_responses = {
            'basic_info': '{"title": "Weekly Team Meeting", "date": "2024-01-15"}',
            'attendees': '[{"name": "John Smith", "role": "Manager"}]',
            'agenda': '[{"title": "Project status update"}]',
            'action_items': '[{"task": "Complete testing", "assignee": "Mike"}]',
            'decisions': '[{"decision": "Approved budget"}]',
            'key_outcomes': '["Budget approved", "Deadline extended"]'
        }
        
        async def mock_generate(prompt, **kwargs):
            # Simple mock that returns basic JSON based on prompt content
            if 'basic' in prompt.lower():
                content = mock_responses['basic_info']
            elif 'attendee' in prompt.lower():
                content = mock_responses['attendees']
            elif 'agenda' in prompt.lower():
                content = mock_responses['agenda']
            elif 'action' in prompt.lower():
                content = mock_responses['action_items']
            elif 'decision' in prompt.lower():
                content = mock_responses['decisions']
            else:
                content = mock_responses['key_outcomes']
            
            return GenerationResponse(
                content=content,
                model='test',
                created_at=None,
                done=True,
                total_duration=0,
                load_duration=0,
                prompt_eval_count=0,
                prompt_eval_duration=0,
                eval_count=0,
                eval_duration=0,
                context=[],
                metadata={}
            )
        
        extractor.ollama_client.generate = mock_generate
        
        result = await extractor.extract_meeting_minutes(sample_meeting_text)
        
        assert isinstance(result.minutes, MeetingMinutes)
        assert result.status in [ExtractionStatus.COMPLETED, ExtractionStatus.VALIDATION_FAILED]
        assert result.confidence_score >= 0.0
    
    def test_confidence_calculation(self, extractor):
        """Test confidence score calculation"""
        from app.ai.extractor import MeetingBasicInfo, Attendee, DiscussionTopic, ActionItem, Decision
        
        # Create sample meeting minutes
        minutes = MeetingMinutes(
            basic_info=MeetingBasicInfo(title="Test Meeting"),
            attendees=[Attendee(name="John Doe")],
            agenda=[DiscussionTopic(title="Topic 1")],
            action_items=[ActionItem(task="Task 1")],
            decisions=[Decision(decision="Decision 1")],
            key_outcomes=["Outcome 1"]
        )
        
        validation_results = {
            'basic_info': True,
            'attendees': True, 
            'agenda': True,
            'action_items': True,
            'decisions': True,
            'key_outcomes': True,
            'overall': True
        }
        
        score = extractor._calculate_confidence_score(minutes, validation_results)
        assert 0.0 <= score <= 1.0
        assert score > 0.5  # Should be high for complete data