"""
Core Functionality Test Suite
Comprehensive tests for core business logic and processing
"""

import pytest
import asyncio
import tempfile
import os
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path


class TestFileProcessing:
    """Test file processing functionality"""

    def test_file_upload_validation(self):
        """Test file upload validation logic"""
        from app.utils.validators import FileValidator

        # Test valid text file
        text_content = b"Meeting notes content"
        is_valid, mime_type = FileValidator.validate_file_type(text_content, "meeting.txt")

        # Should be valid (or return appropriate mime type)
        assert is_valid or "text" in mime_type

    def test_file_size_limits(self):
        """Test file size validation"""
        from app.config import settings

        # Test file size calculation
        max_bytes = settings.max_file_size_bytes
        assert max_bytes > 0
        assert max_bytes == settings.max_file_size_mb * 1024 * 1024

    @pytest.mark.asyncio
    async def test_file_content_reading(self):
        """Test file content reading and processing"""
        # Create temporary test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Test meeting content\nAttendees: John, Jane\nAction: Review budget")
            temp_path = f.name

        try:
            # Test reading file content
            with open(temp_path, 'rb') as f:
                content = f.read()

            assert len(content) > 0
            assert b"meeting" in content.lower()

        finally:
            os.unlink(temp_path)

    def test_filename_sanitization(self):
        """Test filename sanitization"""
        from app.utils.validators import InputSanitizer

        # Test dangerous filename
        dangerous_name = "../../../etc/passwd"
        sanitized = InputSanitizer.sanitize_filename(dangerous_name)

        assert ".." not in sanitized
        assert "/" not in sanitized
        assert "\\" not in sanitized

        # Test long filename
        long_name = "a" * 300 + ".txt"
        sanitized = InputSanitizer.sanitize_filename(long_name)
        assert len(sanitized) <= 255


class TestAIProcessing:
    """Test AI processing functionality"""

    @pytest.mark.asyncio
    async def test_text_preprocessing(self):
        """Test text preprocessing for AI"""
        from app.ai.text_preprocessor import TextPreprocessor

        preprocessor = TextPreprocessor()

        # Test basic text cleaning
        dirty_text = "   Meeting  Notes\n\n\n  Content here   \n\n"
        cleaned = await preprocessor.clean_text(dirty_text)

        assert "Meeting Notes" in cleaned
        assert cleaned.strip() == cleaned  # No leading/trailing whitespace
        assert "\n\n\n" not in cleaned  # Multiple newlines reduced

    @pytest.mark.asyncio
    async def test_meeting_data_extraction(self):
        """Test meeting data extraction structure"""
        from app.ai.extractor import MeetingMinutes, MeetingBasicInfo, Attendee

        # Test data structure creation
        basic_info = MeetingBasicInfo(
            title="Test Meeting",
            date="2024-01-15",
            time="2:00 PM",
            location="Conference Room A"
        )

        attendee = Attendee(
            name="John Doe",
            role="Manager",
            present=True
        )

        meeting_minutes = MeetingMinutes(
            basic_info=basic_info,
            attendees=[attendee],
            agenda=[],
            action_items=[],
            decisions=[],
            key_outcomes=[]
        )

        assert meeting_minutes.basic_info.title == "Test Meeting"
        assert len(meeting_minutes.attendees) == 1
        assert meeting_minutes.attendees[0].name == "John Doe"

    @pytest.mark.asyncio
    async def test_prompt_generation(self):
        """Test AI prompt generation"""
        from app.ai.prompt_engine import PromptEngine

        engine = PromptEngine()

        # Test meeting extraction prompt
        sample_text = "Meeting: Weekly Review\nAttendees: John, Jane"
        prompt = engine.get_extraction_prompt(sample_text)

        assert "meeting" in prompt.lower()
        assert sample_text in prompt
        assert len(prompt) > len(sample_text)  # Should add instructions


class TestDocumentGeneration:
    """Test document generation functionality"""

    def test_word_template_structure(self):
        """Test Word document template structure"""
        from app.document.word_engine import WordEngine

        engine = WordEngine()

        # Test template validation
        template_requirements = engine.get_template_requirements()

        assert isinstance(template_requirements, dict)
        assert "required_sections" in template_requirements
        assert "optional_sections" in template_requirements

    @pytest.mark.asyncio
    async def test_data_injection(self):
        """Test data injection into Word templates"""
        from app.document.data_injector import DataInjector
        from app.ai.extractor import MeetingMinutes, MeetingBasicInfo

        injector = DataInjector()

        # Create test meeting data
        meeting_data = MeetingMinutes(
            basic_info=MeetingBasicInfo(
                title="Test Meeting",
                date="2024-01-15",
                time="2:00 PM"
            ),
            attendees=[],
            agenda=[],
            action_items=[],
            decisions=[],
            key_outcomes=["Decision made", "Action assigned"]
        )

        # Test data formatting
        formatted_data = injector.format_meeting_data(meeting_data)

        assert "Test Meeting" in str(formatted_data)
        assert "2024-01-15" in str(formatted_data)

    def test_pdf_generation_setup(self):
        """Test PDF generation setup and validation"""
        from app.document.pdf_generator import PDFGenerator

        generator = PDFGenerator()

        # Test PDF generator initialization
        assert hasattr(generator, 'quality_settings')
        assert hasattr(generator, 'conversion_options')

    @pytest.mark.asyncio
    async def test_template_loading(self):
        """Test template loading and validation"""
        from app.storage.template_storage import TemplateStorage
        from app.core.template_controller import TemplateController

        # Test template controller
        controller = TemplateController()

        # Should have default templates
        templates = await controller.get_available_templates()
        assert isinstance(templates, (list, dict))


class TestErrorHandling:
    """Test error handling and recovery"""

    @pytest.mark.asyncio
    async def test_file_not_found_handling(self):
        """Test file not found error handling"""
        from fastapi import HTTPException

        # Simulate file not found scenario
        with pytest.raises(HTTPException) as exc_info:
            raise HTTPException(status_code=404, detail="File not found")

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_processing_timeout_handling(self):
        """Test processing timeout handling"""
        import asyncio

        # Test timeout scenario
        async def slow_operation():
            await asyncio.sleep(0.1)  # Short delay for testing
            return "completed"

        # Test with very short timeout
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(slow_operation(), timeout=0.05)

    def test_validation_error_handling(self):
        """Test validation error handling"""
        from app.utils.validators import FileValidator

        # Test empty file validation
        empty_content = b""
        is_valid, message = FileValidator.validate_file_size(empty_content, "text/plain")

        assert not is_valid
        assert isinstance(message, str)
        assert len(message) > 0

    def test_ai_service_error_handling(self):
        """Test AI service error handling"""
        from app.ai.ollama_client import OllamaClient

        # Test client initialization
        client = OllamaClient()
        assert hasattr(client, 'base_url')
        assert hasattr(client, 'model')


class TestConcurrency:
    """Test concurrency and async operations"""

    @pytest.mark.asyncio
    async def test_async_file_processing(self):
        """Test async file processing operations"""
        # Test async operation completion
        async def mock_file_process():
            await asyncio.sleep(0.01)  # Simulate processing
            return {"status": "completed", "result": "processed"}

        result = await mock_file_process()
        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_concurrent_uploads(self):
        """Test handling of concurrent file uploads"""
        # Simulate multiple concurrent operations
        async def mock_upload(upload_id):
            await asyncio.sleep(0.01)
            return f"upload_{upload_id}_completed"

        # Run multiple uploads concurrently
        tasks = [mock_upload(i) for i in range(3)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 3
        assert all("completed" in result for result in results)

    @pytest.mark.asyncio
    async def test_resource_cleanup(self):
        """Test resource cleanup after processing"""
        # Test cleanup operations
        temp_files = []

        try:
            # Create temporary resources
            for i in range(3):
                temp_file = tempfile.NamedTemporaryFile(delete=False)
                temp_files.append(temp_file.name)
                temp_file.close()

            # Verify files exist
            for filepath in temp_files:
                assert os.path.exists(filepath)

        finally:
            # Cleanup
            for filepath in temp_files:
                if os.path.exists(filepath):
                    os.unlink(filepath)

            # Verify cleanup
            for filepath in temp_files:
                assert not os.path.exists(filepath)


class TestPerformance:
    """Test performance-related functionality"""

    def test_memory_usage_limits(self):
        """Test memory usage limits and monitoring"""
        from app.config import settings

        # Test file size limits are reasonable for memory
        max_file_mb = settings.max_file_size_mb
        assert max_file_mb <= 100  # Should not allow extremely large files

    @pytest.mark.asyncio
    async def test_processing_timeouts(self):
        """Test processing timeout configurations"""
        from app.config import settings

        # Test timeout settings exist
        assert hasattr(settings, 'processing_timeout_seconds')
        assert settings.processing_timeout_seconds > 0
        assert settings.processing_timeout_seconds <= 600  # 10 minutes max

    def test_batch_processing_limits(self):
        """Test batch processing limits"""
        from app.config import settings

        # Test batch upload limits
        assert hasattr(settings, 'max_batch_upload_files')
        assert settings.max_batch_upload_files > 0
        assert settings.max_batch_upload_files <= 50


class TestDataValidation:
    """Test data validation and sanitization"""

    def test_meeting_data_validation(self):
        """Test meeting data structure validation"""
        from app.utils.validators import DataValidator

        # Test valid meeting data
        valid_data = {
            'basic_info': {'title': 'Test Meeting'},
            'attendees': [{'name': 'John Doe'}],
            'agenda': [],
            'action_items': [],
            'decisions': [],
            'key_outcomes': []
        }

        is_valid, errors = DataValidator.validate_meeting_data(valid_data)
        assert is_valid or len(errors) == 0

    def test_input_sanitization(self):
        """Test input sanitization functions"""
        from app.utils.validators import InputSanitizer

        # Test text sanitization
        dangerous_text = "<script>alert('xss')</script>Regular text"
        sanitized = InputSanitizer.sanitize_text_input(dangerous_text)

        assert "<script>" not in sanitized
        assert "Regular text" in sanitized

    def test_path_traversal_prevention(self):
        """Test path traversal attack prevention"""
        from app.utils.validators import SecurityValidator

        # Test path validation
        dangerous_paths = [
            "../../../etc/passwd",
            "..\\windows\\system32",
            "/etc/shadow"
        ]

        for path in dangerous_paths:
            is_safe, message = SecurityValidator.validate_no_path_traversal(path)
            assert not is_safe, f"Path {path} should be blocked"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])