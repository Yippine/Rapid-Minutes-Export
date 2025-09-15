"""
Test Configuration and Fixtures
Centralized test setup following ICE principle - Intuitive, Concise, Encompassing test infrastructure
"""

import pytest
import asyncio
import tempfile
import shutil
import os
from pathlib import Path
from typing import Dict, Any, Generator
from unittest.mock import MagicMock

# Add app to path for imports
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.rapid_minutes.config.settings import get_settings
from src.rapid_minutes.ai.text_preprocessor import TextPreprocessor
from src.rapid_minutes.ai.ollama_client import OllamaClient
from src.rapid_minutes.ai.extractor import StructuredDataExtractor, MeetingMinutes, MeetingBasicInfo, Attendee
from src.rapid_minutes.core.file_processor import FileProcessor
from src.rapid_minutes.core.meeting_processor import MeetingProcessor
from src.rapid_minutes.core.template_controller import TemplateController
from src.rapid_minutes.core.output_manager import OutputController
from src.rapid_minutes.document.word_engine import WordEngine
from src.rapid_minutes.document.data_injector import DataInjector
from src.rapid_minutes.document.pdf_generator import PDFGenerator
from src.rapid_minutes.storage.file_manager import FileManager
from src.rapid_minutes.storage.temp_storage import TempStorage
from src.rapid_minutes.storage.template_storage import TemplateStorage
from src.rapid_minutes.storage.output_manager import OutputManager


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_temp_dir():
    """Create temporary directory for test files"""
    temp_dir = tempfile.mkdtemp(prefix="rapid_minutes_test_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def mock_settings(test_temp_dir):
    """Mock settings for testing"""
    settings = get_settings()
    original_settings = {}
    test_settings = {
        'data_dir': os.path.join(test_temp_dir, 'data'),
        'templates_dir': os.path.join(test_temp_dir, 'templates'),
        'output_dir': os.path.join(test_temp_dir, 'output'),
        'temp_dir': os.path.join(test_temp_dir, 'temp'),
        'max_file_size_mb': 10,
        'max_file_size_bytes': 10 * 1024 * 1024,
        'allowed_file_types': ['text/plain', 'application/pdf'],
        'max_batch_upload_files': 5
    }

    # Store original settings
    for key, value in test_settings.items():
        if hasattr(settings, key):
            original_settings[key] = getattr(settings, key)
        setattr(settings, key, value)

    # Create test directories
    for key, path in test_settings.items():
        if key.endswith('_dir'):
            os.makedirs(path, exist_ok=True)

    yield settings

    # Restore original settings
    for key, value in original_settings.items():
        setattr(settings, key, value)


@pytest.fixture
def sample_text_content():
    """Sample meeting text content for testing"""
    return """
    Meeting Title: Weekly Project Review
    Date: 2024-01-15
    Time: 2:00 PM
    Location: Conference Room A
    
    Attendees:
    - John Smith (Project Manager)
    - Jane Doe (Developer) 
    - Bob Johnson (Designer)
    
    Agenda:
    1. Project Progress Review
       - Current sprint status
       - Completed features
    
    2. Issues Discussion
       - Bug fixes needed
       - Resource constraints
    
    Action Items:
    - John to review budget by Friday
    - Jane to fix authentication bug
    - Bob to update UI designs
    
    Decisions:
    - Approved additional developer resource
    - Postponed feature X to next sprint
    
    Next Meeting: January 22, 2024 at 2:00 PM
    """


@pytest.fixture
def sample_meeting_minutes():
    """Sample meeting minutes object for testing"""
    return MeetingMinutes(
        basic_info=MeetingBasicInfo(
            title="Weekly Project Review",
            date="2024-01-15",
            time="2:00 PM",
            location="Conference Room A",
            organizer="John Smith"
        ),
        attendees=[
            Attendee(name="John Smith", role="Project Manager", present=True),
            Attendee(name="Jane Doe", role="Developer", present=True),
            Attendee(name="Bob Johnson", role="Designer", present=True)
        ],
        agenda=[],
        action_items=[],
        decisions=[],
        key_outcomes=["Project on track", "Additional resources approved"]
    )


@pytest.fixture
def mock_ollama_client():
    """Mock Ollama client for testing"""
    mock_client = MagicMock(spec=OllamaClient)
    mock_client.generate.return_value = MagicMock(content='{"test": "response"}')
    mock_client.model = "test-model"
    return mock_client


@pytest.fixture
async def text_preprocessor():
    """Text preprocessor instance for testing"""
    return TextPreprocessor()


@pytest.fixture
async def data_extractor(mock_ollama_client):
    """Data extractor with mocked dependencies"""
    return StructuredDataExtractor(mock_ollama_client)


@pytest.fixture
async def file_processor(mock_settings):
    """File processor instance for testing"""
    return FileProcessor()


@pytest.fixture
async def meeting_processor(mock_settings):
    """Meeting processor instance for testing"""
    return MeetingProcessor()


@pytest.fixture
async def template_controller(mock_settings):
    """Template controller instance for testing"""
    return TemplateController()


@pytest.fixture
async def output_controller(mock_settings):
    """Output controller instance for testing"""
    return OutputController()


@pytest.fixture
async def word_engine(mock_settings):
    """Word engine instance for testing"""
    return WordEngine()


@pytest.fixture
async def data_injector():
    """Data injector instance for testing"""
    return DataInjector()


@pytest.fixture
async def pdf_generator(mock_settings):
    """PDF generator instance for testing"""
    return PDFGenerator()


@pytest.fixture
def sample_text_file(test_temp_dir, sample_text_content):
    """Create sample text file for testing"""
    file_path = os.path.join(test_temp_dir, "sample_meeting.txt")
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(sample_text_content)
    return file_path


@pytest.fixture
def sample_binary_file(test_temp_dir):
    """Create sample binary file for testing"""
    file_path = os.path.join(test_temp_dir, "sample_binary.bin")
    with open(file_path, 'wb') as f:
        f.write(b"Binary content for testing")
    return file_path


@pytest.fixture
def large_text_file(test_temp_dir):
    """Create large text file for testing size limits"""
    file_path = os.path.join(test_temp_dir, "large_file.txt")
    content = "Large file content " * 100000  # Approximately 1.8MB
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    return file_path


@pytest.fixture
def empty_file(test_temp_dir):
    """Create empty file for testing"""
    file_path = os.path.join(test_temp_dir, "empty.txt")
    Path(file_path).touch()
    return file_path


class TestDataFactory:
    """Factory for creating test data"""
    
    @staticmethod
    def create_file_content(size_mb: float = 0.1) -> bytes:
        """Create file content of specified size"""
        content = "Test content " * int(size_mb * 1024 * 1024 / 13)  # Approximate size
        return content.encode('utf-8')
    
    @staticmethod
    def create_meeting_text(
        title: str = "Test Meeting",
        attendees: int = 3,
        agenda_items: int = 2,
        action_items: int = 2
    ) -> str:
        """Create formatted meeting text"""
        text = f"""
        Meeting Title: {title}
        Date: 2024-01-15
        Time: 2:00 PM
        
        Attendees:
        """
        
        for i in range(attendees):
            text += f"- Person {i+1} (Role {i+1})\n"
        
        text += "\nAgenda:\n"
        for i in range(agenda_items):
            text += f"{i+1}. Agenda Item {i+1}\n"
        
        text += "\nAction Items:\n"
        for i in range(action_items):
            text += f"- Action {i+1}\n"
        
        return text


@pytest.fixture
def test_data_factory():
    """Test data factory instance"""
    return TestDataFactory()


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "requires_ollama: Tests requiring Ollama server")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically"""
    for item in items:
        # Add unit marker to tests in unit directory
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        
        # Add integration marker to tests in integration directory  
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        
        # Add e2e marker to tests in e2e directory
        elif "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)


# Async test utilities
class AsyncTestCase:
    """Base class for async test cases"""
    
    @pytest.fixture(autouse=True)
    def setup_async_test(self, event_loop):
        """Setup async test environment"""
        self.loop = event_loop
        asyncio.set_event_loop(event_loop)
    
    async def run_async_test(self, coro):
        """Run async test coroutine"""
        return await coro


# Test configuration constants
TEST_CONFIG = {
    'TIMEOUT_SECONDS': 30,
    'MAX_RETRIES': 3,
    'TEST_FILE_SIZE_LIMIT': 1024 * 1024,  # 1MB
    'TEMP_FILE_PREFIX': 'rapid_minutes_test_',
    'DEFAULT_ENCODING': 'utf-8'
}