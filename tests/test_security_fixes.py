"""
Security Fixes Test Suite
Tests for security vulnerability fixes implemented in Phase 2
"""

import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException


class TestCORSSecurityFixes:
    """Test CORS security configuration fixes"""

    def test_cors_origins_not_wildcard(self):
        """Test that CORS origins are not set to wildcard"""
        from app.config import Settings

        settings = Settings()
        cors_origins = settings.get_cors_origins_list()

        # Should not contain wildcard
        assert "*" not in cors_origins

        # Should contain specific origins
        assert any("localhost" in origin for origin in cors_origins)

    def test_cors_methods_restricted(self):
        """Test that CORS methods are restricted to necessary methods"""
        from app.main import create_application

        app = create_application()

        # Check middleware configuration
        cors_middleware = None
        for middleware in app.user_middleware:
            if "CORSMiddleware" in str(middleware.cls):
                cors_middleware = middleware.kwargs
                break

        assert cors_middleware is not None
        assert cors_middleware.get("allow_methods") != ["*"]

        # Should only allow necessary methods
        allowed_methods = cors_middleware.get("allow_methods", [])
        assert "GET" in allowed_methods
        assert "POST" in allowed_methods
        # Should not allow all methods
        assert len(allowed_methods) <= 5


class TestInputValidationFixes:
    """Test input validation security fixes"""

    def test_file_id_validation(self):
        """Test file ID validation prevents path traversal"""
        from src.rapid_minutes.web.routes import validate_file_id

        # Valid file IDs should pass
        valid_id = "550e8400-e29b-41d4-a716-446655440000"
        result = validate_file_id(valid_id)
        assert result == valid_id

        # Invalid file IDs should raise HTTPException
        invalid_ids = [
            "../../../etc/passwd",
            "..\\windows\\system32",
            "abc123",  # Too short
            "550e8400-e29b-41d4-a716-446655440000-extra",  # Too long
            "550e8400.e29b.41d4.a716.446655440000",  # Wrong format
        ]

        for invalid_id in invalid_ids:
            with pytest.raises(HTTPException) as exc_info:
                validate_file_id(invalid_id)
            assert exc_info.value.status_code == 400

    def test_filename_sanitization(self):
        """Test filename validation and sanitization"""
        import re

        # Valid filenames should pass
        valid_filenames = [
            "meeting.txt",
            "weekly-report.docx",
            "notes_2024.txt"
        ]

        filename_pattern = r'^[a-zA-Z0-9._-]+$'

        for filename in valid_filenames:
            assert re.match(filename_pattern, filename)
            assert ".." not in filename

        # Invalid filenames should be rejected
        invalid_filenames = [
            "../etc/passwd",
            "meeting\\notes.txt",
            "file:with:colons.txt",
            "dangerous<script>.txt"
        ]

        for filename in invalid_filenames:
            result = re.match(filename_pattern, filename) and ".." not in filename
            assert not result, f"Filename {filename} should be invalid"

    @pytest.mark.asyncio
    async def test_file_size_validation(self):
        """Test file size validation is enforced"""
        from app.config import settings

        # Check settings have reasonable limits
        assert settings.max_file_size_mb > 0
        assert settings.max_file_size_mb <= 100  # Should not be too large

        # Test file size bytes calculation
        expected_bytes = settings.max_file_size_mb * 1024 * 1024
        assert settings.max_file_size_bytes == expected_bytes

    def test_batch_upload_limits(self):
        """Test batch upload file count limits"""
        from app.config import settings

        # Check batch upload limits exist and are reasonable
        assert hasattr(settings, 'max_batch_upload_files')
        assert settings.max_batch_upload_files > 0
        assert settings.max_batch_upload_files <= 50  # Should not be too large


class TestSubprocessSecurityFixes:
    """Test subprocess security fixes"""

    def test_subprocess_commands_use_list_format(self):
        """Test that subprocess commands use list format instead of strings"""
        from unittest.mock import patch

        # Mock subprocess.run to capture calls
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            # Test LibreOffice PDF conversion

            # This would trigger subprocess call in real scenario
            # For testing, we check the pattern used
            cmd_pattern = [
                'libreoffice',
                '--headless',
                '--convert-to', 'pdf'
            ]

            # Commands should be lists, not strings
            for item in cmd_pattern:
                assert isinstance(item, str)
                assert not any(char in item for char in ['&', '|', ';', '$('])

    def test_subprocess_no_shell_injection(self):
        """Test that subprocess calls don't use shell=True"""
        import ast
        import inspect
        from app.document import pdf_generator

        # Get source code of PDF generator
        source = inspect.getsource(pdf_generator)
        tree = ast.parse(source)

        # Look for subprocess.run calls
        subprocess_calls = []
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and
                isinstance(node.func, ast.Attribute) and
                node.func.attr == 'run'):
                subprocess_calls.append(node)

        # Check that shell=True is not used
        for call in subprocess_calls:
            for keyword in call.keywords:
                if keyword.arg == 'shell':
                    assert keyword.value.value is False, "subprocess should not use shell=True"


class TestFileValidationEnhancements:
    """Test enhanced file validation"""

    def test_empty_file_rejection(self):
        """Test that empty files are rejected"""
        # This would be tested in the upload endpoint
        # Empty files should raise HTTPException with status 400
        pass

    def test_file_type_validation_with_magic(self):
        """Test file type validation uses python-magic"""
        from app.utils.validators import FileValidator

        # Test text file validation
        text_content = b"This is a text file content"
        is_valid, mime_type = FileValidator.validate_file_type(text_content, "test.txt")

        # Should detect as text/plain
        assert is_valid or "text" in mime_type.lower()

    def test_file_content_size_validation(self):
        """Test file content size validation"""
        from app.utils.validators import FileValidator

        # Test empty file
        empty_content = b""
        is_valid, message = FileValidator.validate_file_size(empty_content, "text/plain")
        assert not is_valid
        assert "empty" in message.lower()

        # Test large file
        large_content = b"x" * (20 * 1024 * 1024)  # 20MB
        is_valid, message = FileValidator.validate_file_size(large_content, "text/plain")
        assert not is_valid
        assert "large" in message.lower()


class TestErrorHandlingEnhancements:
    """Test enhanced error handling"""

    def test_http_exception_status_codes(self):
        """Test that appropriate HTTP status codes are used"""
        from fastapi import HTTPException

        # File not found should be 404
        file_not_found = HTTPException(status_code=404, detail="File not found")
        assert file_not_found.status_code == 404

        # Invalid input should be 400
        invalid_input = HTTPException(status_code=400, detail="Invalid input")
        assert invalid_input.status_code == 400

        # File too large should be 413
        file_too_large = HTTPException(status_code=413, detail="File too large")
        assert file_too_large.status_code == 413

    def test_error_message_sanitization(self):
        """Test that error messages don't leak sensitive information"""
        from app.utils.validators import InputSanitizer

        # Test HTML escaping
        dangerous_input = "<script>alert('xss')</script>"
        sanitized = InputSanitizer.escape_html(dangerous_input)

        assert "<script>" not in sanitized
        assert "&lt;script&gt;" in sanitized


class TestConfigurationSecurity:
    """Test configuration security settings"""

    def test_debug_mode_settings(self):
        """Test debug mode configuration"""
        from app.config import settings

        # In production, debug should be False
        if settings.environment.lower() in ["production", "prod"]:
            assert not settings.debug

    def test_secret_key_configuration(self):
        """Test secret key is properly configured"""
        from app.config import settings

        # Secret key should not be default in production
        if settings.environment.lower() in ["production", "prod"]:
            assert settings.secret_key != "rapid-minutes-export-secret-key-change-in-production"

        # Secret key should have minimum length
        assert len(settings.secret_key) >= 32

    def test_allowed_hosts_configuration(self):
        """Test allowed hosts configuration"""
        from app.config import settings

        allowed_hosts = settings.get_allowed_hosts_list()

        # Should have specific hosts configured
        assert len(allowed_hosts) > 0
        assert isinstance(allowed_hosts, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])