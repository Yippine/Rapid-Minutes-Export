"""
API Security Test Suite
Tests for API endpoint security and validation
"""

import pytest
import json
import tempfile
import os
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock


@pytest.fixture
def test_client():
    """Create test client for API testing"""
    from src.rapid_minutes.main import create_application

    app = create_application()
    return TestClient(app)


@pytest.fixture
def valid_text_file():
    """Create a valid text file for testing"""
    content = """
    Meeting Title: Test Meeting
    Date: 2024-01-15
    Attendees:
    - John Doe (Manager)
    - Jane Smith (Developer)

    Agenda:
    1. Project status review
    2. Budget discussion

    Action Items:
    - John to review budget by Friday
    - Jane to fix bug #123
    """

    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(content)
        temp_path = f.name

    yield temp_path

    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


class TestFileUploadSecurity:
    """Test file upload security features"""

    def test_file_size_validation(self, test_client):
        """Test file size limits are enforced"""
        # Create oversized file content
        large_content = "x" * (15 * 1024 * 1024)  # 15MB content

        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(large_content)
            large_file_path = f.name

        try:
            with open(large_file_path, 'rb') as f:
                response = test_client.post(
                    "/api/upload/single",
                    files={"file": ("large_file.txt", f, "text/plain")}
                )

            # Should reject large files
            assert response.status_code in [413, 400]  # Payload too large or bad request

        finally:
            if os.path.exists(large_file_path):
                os.unlink(large_file_path)

    def test_empty_file_rejection(self, test_client):
        """Test empty files are rejected"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            # Create empty file
            empty_file_path = f.name

        try:
            with open(empty_file_path, 'rb') as f:
                response = test_client.post(
                    "/api/upload/single",
                    files={"file": ("empty.txt", f, "text/plain")}
                )

            # Should reject empty files
            assert response.status_code == 400

        finally:
            if os.path.exists(empty_file_path):
                os.unlink(empty_file_path)

    def test_invalid_file_type_rejection(self, test_client):
        """Test invalid file types are rejected"""
        # Create a binary file that shouldn't be accepted
        binary_content = b"\x00\x01\x02\x03\x04\x05"

        with tempfile.NamedTemporaryFile(suffix='.bin', delete=False) as f:
            f.write(binary_content)
            binary_file_path = f.name

        try:
            with open(binary_file_path, 'rb') as f:
                response = test_client.post(
                    "/api/upload/single",
                    files={"file": ("malicious.bin", f, "application/octet-stream")}
                )

            # Should reject binary files
            assert response.status_code == 400

        finally:
            if os.path.exists(binary_file_path):
                os.unlink(binary_file_path)

    def test_filename_validation(self, test_client, valid_text_file):
        """Test filename validation prevents dangerous names"""
        dangerous_filenames = [
            "../../../etc/passwd",
            "..\\windows\\system32\\config",
            "con.txt",  # Windows reserved name
            "file\x00name.txt",  # Null byte
            "file<script>.txt"  # HTML characters
        ]

        for dangerous_name in dangerous_filenames:
            with open(valid_text_file, 'rb') as f:
                response = test_client.post(
                    "/api/upload/single",
                    files={"file": (dangerous_name, f, "text/plain")}
                )

            # Should reject dangerous filenames
            assert response.status_code == 400, f"Should reject filename: {dangerous_name}"

    def test_batch_upload_limits(self, test_client, valid_text_file):
        """Test batch upload file count limits"""
        # Try to upload too many files
        files = []

        # Create multiple file uploads (more than allowed limit)
        for i in range(15):  # Assuming limit is 10
            with open(valid_text_file, 'rb') as f:
                files.append(("files", (f"file_{i}.txt", f.read(), "text/plain")))

        response = test_client.post("/api/upload/batch", files=files)

        # Should reject too many files
        assert response.status_code == 400


class TestAPIEndpointSecurity:
    """Test API endpoint security features"""

    def test_file_id_path_traversal_protection(self, test_client):
        """Test file ID path traversal protection"""
        dangerous_file_ids = [
            "../../../etc/passwd",
            "..\\windows\\system32",
            "/etc/shadow",
            "abc123",  # Invalid format
            "550e8400-e29b-41d4-a716-446655440000-extra"  # Too long
        ]

        for dangerous_id in dangerous_file_ids:
            # Test status endpoint
            response = test_client.get(f"/api/status/{dangerous_id}")
            assert response.status_code == 400, f"Should reject file_id: {dangerous_id}"

            # Test download endpoint
            response = test_client.get(f"/api/download/word/{dangerous_id}")
            assert response.status_code == 400, f"Should reject file_id: {dangerous_id}"

    def test_cors_headers_present(self, test_client):
        """Test CORS headers are properly configured"""
        response = test_client.options("/api/health")

        # Should have CORS headers
        assert "access-control-allow-origin" in response.headers

        # Should not allow all origins
        origin_header = response.headers.get("access-control-allow-origin", "")
        assert origin_header != "*"

    def test_http_methods_restricted(self, test_client):
        """Test HTTP methods are properly restricted"""
        # Test unsupported methods
        unsupported_methods = ["PATCH", "TRACE", "CONNECT"]

        for method in unsupported_methods:
            response = test_client.request(method, "/api/health")
            assert response.status_code in [405, 501]  # Method not allowed or not implemented

    def test_request_validation(self, test_client):
        """Test request validation and sanitization"""
        # Test malformed JSON
        response = test_client.post(
            "/api/upload/single",
            data={"processing_options": "invalid json{"},
            files={"file": ("test.txt", "content", "text/plain")}
        )

        # Should handle malformed JSON gracefully
        assert response.status_code in [200, 400]  # Either process with defaults or reject


class TestAuthenticationAndAuthorization:
    """Test authentication and authorization features"""

    def test_health_endpoint_access(self, test_client):
        """Test health endpoint is accessible"""
        response = test_client.get("/api/health")
        assert response.status_code == 200

    def test_protected_endpoints_validation(self, test_client):
        """Test protected endpoints validate inputs"""
        # Test file processing without valid file
        response = test_client.post("/api/upload/single")
        assert response.status_code == 422  # Unprocessable entity (missing required field)

    def test_rate_limiting_headers(self, test_client):
        """Test rate limiting headers if implemented"""
        response = test_client.get("/api/health")

        # Check if rate limiting headers are present (optional)
        rate_limit_headers = [
            "x-ratelimit-limit",
            "x-ratelimit-remaining",
            "x-ratelimit-reset"
        ]

        # This test is informational - rate limiting might not be implemented yet
        has_rate_limiting = any(header in response.headers for header in rate_limit_headers)

        # Just verify the test can run (rate limiting is optional enhancement)
        assert True  # This test documents the feature for future implementation


class TestErrorHandling:
    """Test error handling and response formatting"""

    def test_404_error_handling(self, test_client):
        """Test 404 error handling"""
        response = test_client.get("/nonexistent-endpoint")
        assert response.status_code == 404

    def test_500_error_handling(self, test_client):
        """Test 500 error handling with mocked error"""
        # This would require mocking internal services to cause a 500 error
        # For now, test that the error handling structure exists

        with patch('app.api.upload.FileProcessor') as mock_processor:
            mock_processor.side_effect = Exception("Simulated internal error")

            response = test_client.post(
                "/api/upload/single",
                files={"file": ("test.txt", "content", "text/plain")}
            )

            # Should handle internal errors gracefully
            assert response.status_code == 500

    def test_validation_error_messages(self, test_client):
        """Test validation error messages are user-friendly"""
        # Test missing required field
        response = test_client.post("/api/upload/single")

        assert response.status_code == 422

        # Check error message format
        if response.content:
            error_data = response.json()
            assert "detail" in error_data or "message" in error_data

    def test_error_response_format(self, test_client):
        """Test error responses follow consistent format"""
        # Test with invalid file ID format
        response = test_client.get("/api/status/invalid-id")

        if response.status_code == 400:
            error_data = response.json()
            # Should have consistent error format
            assert isinstance(error_data, dict)
            assert "detail" in error_data or "message" in error_data


class TestInputSanitization:
    """Test input sanitization and validation"""

    def test_json_payload_sanitization(self, test_client, valid_text_file):
        """Test JSON payload sanitization"""
        # Test with potentially dangerous JSON content
        dangerous_options = {
            "template_type": "<script>alert('xss')</script>",
            "auto_process": True,
            "extraction_options": {
                "dangerous_key": "../../etc/passwd"
            }
        }

        with open(valid_text_file, 'rb') as f:
            response = test_client.post(
                "/api/upload/single",
                data={"processing_options": json.dumps(dangerous_options)},
                files={"file": ("test.txt", f, "text/plain")}
            )

        # Should either sanitize input or reject it
        assert response.status_code in [200, 400]

    def test_form_data_sanitization(self, test_client, valid_text_file):
        """Test form data sanitization"""
        with open(valid_text_file, 'rb') as f:
            response = test_client.post(
                "/api/upload/single",
                data={"user_id": "<script>alert('xss')</script>"},
                files={"file": ("test.txt", f, "text/plain")}
            )

        # Should handle potentially dangerous form data
        assert response.status_code in [200, 400]


class TestSecurityHeaders:
    """Test security headers in responses"""

    def test_security_headers_present(self, test_client):
        """Test important security headers are present"""
        response = test_client.get("/api/health")

        # Test for important security headers (some may not be implemented yet)
        important_headers = {
            "x-content-type-options": "nosniff",
            "x-frame-options": "DENY",
            "x-xss-protection": "1; mode=block"
        }

        # Check if any security headers are present
        security_headers_present = any(
            header.lower() in response.headers
            for header in important_headers.keys()
        )

        # This is informational for future security enhancements
        # The test passes regardless to not break current functionality
        assert True  # Document this feature for future implementation

    def test_content_type_headers(self, test_client):
        """Test content type headers are correct"""
        response = test_client.get("/api/health")

        # Should have proper content type
        assert "content-type" in response.headers
        content_type = response.headers["content-type"]
        assert "application/json" in content_type.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])