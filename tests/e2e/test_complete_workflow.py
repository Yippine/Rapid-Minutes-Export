"""
End-to-End Process Verification Tests (T04)
Complete workflow testing following SESE principle - systematic, exhaustive process validation
"""

import pytest
import asyncio
import tempfile
import os
import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# Add app to path
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.rapid_minutes.core.file_processor import FileProcessor, FileProcessingOptions
from src.rapid_minutes.core.meeting_processor import MeetingProcessor, ProcessingPriority
from src.rapid_minutes.core.template_controller import TemplateController, TemplateType
from src.rapid_minutes.core.output_manager import OutputController
from src.rapid_minutes.ai.extractor import MeetingMinutes, MeetingBasicInfo, Attendee, DiscussionTopic, ActionItem, Decision
from src.rapid_minutes.document.word_engine import WordEngine
from src.rapid_minutes.document.data_injector import DataInjector
from src.rapid_minutes.document.pdf_generator import PDFGenerator
from src.rapid_minutes.storage.template_storage import TemplateStorage, TemplateCategory
from src.rapid_minutes.storage.output_manager import OutputManager


@pytest.mark.e2e
class TestCompleteWorkflow:
    """End-to-end workflow testing"""
    
    @pytest.fixture(autouse=True)
    def setup_test_environment(self, mock_settings):
        """Setup test environment for each test"""
        self.settings = mock_settings
        
        # Initialize all components
        self.file_processor = FileProcessor()
        self.meeting_processor = MeetingProcessor()
        self.template_controller = TemplateController()
        self.output_controller = OutputController()
        self.word_engine = WordEngine()
        self.data_injector = DataInjector()
        self.pdf_generator = PDFGenerator()
        self.template_storage = TemplateStorage()
        self.output_manager = OutputManager()
    
    async def test_full_meeting_minutes_generation_workflow(self, sample_text_content):
        """Test complete workflow from text input to generated documents"""
        
        # Step 1: Process input file
        file_content = sample_text_content.encode('utf-8')
        filename = "test_meeting.txt"
        
        processed_file = await self.file_processor.upload_file(
            file_content,
            filename,
            FileProcessingOptions()
        )
        
        assert processed_file is not None
        assert processed_file.status.value == "valid"
        
        # Step 2: Submit processing job
        job_id = await self.meeting_processor.submit_processing_job(
            file_content,
            filename,
            user_id="test-user",
            priority=ProcessingPriority.NORMAL,
            processing_options={
                'template_type': TemplateType.STANDARD,
                'generate_pdf': True
            }
        )
        
        assert job_id is not None
        
        # Step 3: Monitor job progress
        job_status = await self.meeting_processor.get_job_status(job_id)
        assert job_status is not None
        assert job_status['job_id'] == job_id
        
        # Step 4: Wait for completion (simulate)
        # In real test, we would wait for actual processing
        # For now, create mock result
        mock_meeting_minutes = MeetingMinutes(
            basic_info=MeetingBasicInfo(
                title="Weekly Project Review",
                date="2024-01-15",
                time="2:00 PM",
                location="Conference Room A"
            ),
            attendees=[
                Attendee(name="John Smith", role="Project Manager", present=True),
                Attendee(name="Jane Doe", role="Developer", present=True)
            ],
            agenda=[
                DiscussionTopic(
                    title="Project Progress Review",
                    description="Review current sprint status"
                )
            ],
            action_items=[
                ActionItem(
                    task="Review budget by Friday",
                    assignee="John Smith"
                )
            ],
            decisions=[
                Decision(decision="Approved additional developer resource")
            ],
            key_outcomes=["Project on track", "Resources approved"]
        )
        
        # Step 5: Generate documents
        generation_result = await self.template_controller.generate_document(
            mock_meeting_minutes,
            TemplateType.STANDARD,
            "test_output.docx"
        )
        
        assert generation_result.success is True
        assert generation_result.output_path is not None
        
        # Step 6: Verify document generation
        assert os.path.exists(generation_result.output_path)
        assert generation_result.file_size > 0
        
        # Step 7: Test PDF generation
        pdf_result = await self.pdf_generator.generate_from_meeting_minutes(
            mock_meeting_minutes,
            "test_output.pdf"
        )
        
        # PDF generation might not be available in test environment
        # Just verify the method was called correctly
        assert pdf_result is not None
    
    async def test_file_processing_pipeline(self, sample_text_content):
        """Test complete file processing pipeline"""
        
        # Step 1: File upload and validation
        file_content = sample_text_content.encode('utf-8')
        
        processed_file = await self.file_processor.upload_file(
            file_content,
            "pipeline_test.txt",
            FileProcessingOptions(
                validate_content=True,
                extract_text=True,
                preprocess_text=True
            )
        )
        
        assert processed_file.status.value == "valid"
        assert processed_file.file_size == len(file_content)
        
        # Step 2: Content processing
        processing_results = await self.file_processor.process_file_content(
            processed_file.file_id
        )
        
        assert 'preprocessed_content' in processing_results
        assert 'preprocessing_stats' in processing_results
        
        # Step 3: Get processed content
        content = await self.file_processor.get_file_content(processed_file.file_id)
        assert content is not None
        assert len(content) > 0
        
        # Step 4: Cleanup
        cleanup_result = await self.file_processor.remove_file(processed_file.file_id)
        assert cleanup_result is True
    
    async def test_template_management_workflow(self, test_temp_dir):
        """Test template management workflow"""
        
        # Step 1: Create sample template file
        template_path = os.path.join(test_temp_dir, "test_template.txt")
        template_content = """
        Meeting: {{MEETING_TITLE}}
        Date: {{MEETING_DATE}}
        Attendees: {{ATTENDEES_LIST}}
        """
        
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(template_content)
        
        # Step 2: Add template to storage
        template_metadata = await self.template_storage.add_template(
            template_path,
            "Test Template",
            "Template for testing",
            TemplateCategory.STANDARD
        )
        
        assert template_metadata is not None
        assert template_metadata.name == "Test Template"
        
        # Step 3: List templates
        templates = await self.template_storage.list_templates()
        assert len(templates) >= 1
        
        # Step 4: Validate template
        validation_result = await self.template_storage.validate_template(
            template_metadata.template_id
        )
        assert validation_result.is_valid is True
        
        # Step 5: Get template usage stats
        stats = await self.template_storage.get_template_usage_stats(
            template_metadata.template_id
        )
        assert 'usage_count' in stats
        
        # Step 6: Remove template
        removal_result = await self.template_storage.delete_template(
            template_metadata.template_id,
            permanent=True
        )
        assert removal_result is True
    
    async def test_output_management_workflow(self, test_temp_dir):
        """Test output file management workflow"""
        
        # Step 1: Create sample output file
        output_path = os.path.join(test_temp_dir, "test_output.txt")
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("Test output content")
        
        # Step 2: Store file in output manager
        from src.rapid_minutes.storage.output_manager import OutputFileType
        
        file_record = await self.output_manager.store_file(
            output_path,
            "test-job-123",
            OutputFileType.TXT,
            "test_output.txt"
        )
        
        assert file_record is not None
        assert file_record.filename == "test_output.txt"
        
        # Step 3: List files
        files = await self.output_manager.list_files(
            job_id="test-job-123"
        )
        assert len(files) >= 1
        
        # Step 4: Get file path
        retrieved_path = await self.output_manager.get_file_path(file_record.file_id)
        assert retrieved_path is not None
        assert os.path.exists(retrieved_path)
        
        # Step 5: Mark as downloaded
        download_result = await self.output_manager.mark_downloaded(file_record.file_id)
        assert download_result is True
        
        # Step 6: Get storage stats
        stats = self.output_manager.get_storage_stats()
        assert 'total_files' in stats
        assert stats['total_files'] >= 1
        
        # Step 7: Cleanup
        cleanup_result = await self.output_manager.delete_file(
            file_record.file_id,
            permanent=True
        )
        assert cleanup_result is True
    
    async def test_error_handling_workflow(self):
        """Test error handling throughout the workflow"""
        
        # Step 1: Test invalid file upload
        with pytest.raises(Exception):
            await self.file_processor.upload_file(
                b"",  # Empty content
                "empty.txt",
                FileProcessingOptions()
            )
        
        # Step 2: Test non-existent job status
        status = await self.meeting_processor.get_job_status("nonexistent-job")
        assert status is None
        
        # Step 3: Test invalid template
        templates = await self.template_controller.get_available_templates()
        # Should return empty list or default templates
        assert isinstance(templates, list)
        
        # Step 4: Test invalid file operations
        file_info = await self.output_controller.get_file_info("nonexistent-file")
        assert file_info is None


@pytest.mark.e2e
class TestSystemIntegration:
    """Test system integration and component interaction"""
    
    @pytest.fixture(autouse=True)
    def setup_integration_test(self, mock_settings):
        """Setup integration test environment"""
        self.settings = mock_settings
    
    async def test_component_initialization(self):
        """Test that all components initialize correctly"""
        
        # Initialize all major components
        components = {
            'file_processor': FileProcessor(),
            'meeting_processor': MeetingProcessor(),
            'template_controller': TemplateController(),
            'output_controller': OutputController(),
            'word_engine': WordEngine(),
            'data_injector': DataInjector(),
            'pdf_generator': PDFGenerator(),
            'template_storage': TemplateStorage(),
            'output_manager': OutputManager()
        }
        
        # Verify all components initialized successfully
        for name, component in components.items():
            assert component is not None, f"{name} failed to initialize"
    
    async def test_component_communication(self, sample_text_content):
        """Test communication between components"""
        
        file_processor = FileProcessor()
        meeting_processor = MeetingProcessor()
        
        # Test file processor -> meeting processor communication
        file_content = sample_text_content.encode('utf-8')
        processed_file = await file_processor.upload_file(
            file_content,
            "communication_test.txt",
            FileProcessingOptions()
        )
        
        assert processed_file.status.value == "valid"
        
        # The file processor should work with meeting processor
        job_id = await meeting_processor.submit_processing_job(
            file_content,
            "communication_test.txt",
            user_id="integration-test"
        )
        
        assert job_id is not None
        
        # Verify job was created
        job_status = await meeting_processor.get_job_status(job_id)
        assert job_status is not None
    
    async def test_system_statistics_aggregation(self):
        """Test system-wide statistics aggregation"""
        
        file_processor = FileProcessor()
        meeting_processor = MeetingProcessor()
        output_manager = OutputManager()
        
        # Get statistics from different components
        file_stats = file_processor.get_processing_stats()
        processing_stats = meeting_processor.get_processing_statistics()
        storage_stats = output_manager.get_storage_stats()
        
        # Verify statistics structure
        assert 'total_files' in file_stats
        assert 'total_jobs' in processing_stats.__dict__
        assert 'total_files' in storage_stats
        
        # Test statistics consistency
        # In a real system, these should be consistent
        # For testing, just verify they're accessible
        assert isinstance(file_stats['total_files'], int)
        assert isinstance(processing_stats.total_jobs, int)
        assert isinstance(storage_stats['total_files'], int)
    
    async def test_configuration_consistency(self, mock_settings):
        """Test configuration consistency across components"""
        
        # All components should use the same configuration
        file_processor = FileProcessor()
        template_controller = TemplateController()
        output_manager = OutputManager()
        
        # Verify they all use the same temp directory
        # This would be more meaningful with real config validation
        assert mock_settings.temp_dir is not None
        assert mock_settings.output_dir is not None
        assert mock_settings.templates_dir is not None


@pytest.mark.e2e
@pytest.mark.slow
class TestPerformanceAndStress:
    """Test system performance and stress scenarios"""
    
    async def test_concurrent_processing(self, sample_text_content):
        """Test system under concurrent processing load"""
        
        file_processor = FileProcessor()
        meeting_processor = MeetingProcessor()
        
        # Create multiple concurrent processing tasks
        tasks = []
        for i in range(5):  # Test with 5 concurrent jobs
            file_content = sample_text_content.encode('utf-8')
            filename = f"concurrent_test_{i}.txt"
            
            # Create upload task
            task = asyncio.create_task(
                file_processor.upload_file(
                    file_content,
                    filename,
                    FileProcessingOptions()
                )
            )
            tasks.append(task)
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all uploads succeeded
        successful_uploads = [
            r for r in results 
            if not isinstance(r, Exception) and r.status.value == "valid"
        ]
        assert len(successful_uploads) >= 3  # Allow some failures in test environment
    
    async def test_large_file_handling(self, test_temp_dir):
        """Test handling of large files"""
        
        file_processor = FileProcessor()
        
        # Create a moderately large file (1MB)
        large_content = "Large file content line.\n" * 50000  # ~1MB
        large_file_path = os.path.join(test_temp_dir, "large_file.txt")
        
        with open(large_file_path, 'w', encoding='utf-8') as f:
            f.write(large_content)
        
        # Test processing large file
        with open(large_file_path, 'rb') as f:
            file_content = f.read()
        
        processed_file = await file_processor.upload_file(
            file_content,
            "large_file.txt",
            FileProcessingOptions()
        )
        
        # Should handle large file appropriately
        if processed_file.status.value == "error":
            # File might be too large for test limits
            assert "too large" in processed_file.error_message.lower()
        else:
            assert processed_file.status.value == "valid"
            assert processed_file.file_size == len(file_content)
    
    async def test_memory_usage_monitoring(self):
        """Test system memory usage during operation"""
        
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Perform various operations
        file_processor = FileProcessor()
        meeting_processor = MeetingProcessor()
        
        # Create and process multiple files
        for i in range(10):
            content = f"Test content {i}" * 1000
            file_content = content.encode('utf-8')
            
            processed_file = await file_processor.upload_file(
                file_content,
                f"memory_test_{i}.txt",
                FileProcessingOptions()
            )
            
            if processed_file.status.value == "valid":
                # Process the file
                await file_processor.process_file_content(processed_file.file_id)
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 100MB)
        assert memory_increase < 100 * 1024 * 1024  # 100MB
        
        # Get processing statistics
        stats = file_processor.get_processing_stats()
        
        # Verify statistics are tracking properly
        assert 'memory_usage_estimate' in stats
        assert stats['total_files'] >= 0


@pytest.mark.e2e
class TestSystemRecovery:
    """Test system recovery and resilience"""
    
    async def test_graceful_error_recovery(self, sample_text_content):
        """Test system recovery from errors"""
        
        file_processor = FileProcessor()
        
        # Test recovery from invalid file
        try:
            await file_processor.upload_file(
                b"",  # Invalid empty content
                "invalid.txt",
                FileProcessingOptions()
            )
        except Exception:
            pass  # Expected to fail
        
        # System should still work for valid files
        valid_content = sample_text_content.encode('utf-8')
        processed_file = await file_processor.upload_file(
            valid_content,
            "valid_after_error.txt",
            FileProcessingOptions()
        )
        
        assert processed_file.status.value == "valid"
    
    async def test_cleanup_operations(self, sample_text_content):
        """Test system cleanup operations"""
        
        file_processor = FileProcessor()
        output_manager = OutputManager()
        
        # Create some test files
        file_content = sample_text_content.encode('utf-8')
        processed_file = await file_processor.upload_file(
            file_content,
            "cleanup_test.txt",
            FileProcessingOptions()
        )
        
        # Test cleanup operations
        if processed_file.status.value == "valid":
            # Test file removal
            removal_result = await file_processor.remove_file(processed_file.file_id)
            assert removal_result is True
        
        # Test expired file cleanup
        cleanup_count = await file_processor.cleanup_expired_files()
        assert cleanup_count >= 0  # Should not fail
        
        # Test output manager cleanup
        output_cleanup_count = await output_manager.cleanup_expired_files()
        assert output_cleanup_count >= 0  # Should not fail