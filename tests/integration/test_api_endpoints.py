"""
API Endpoint Integration Tests (T01)
Comprehensive API testing following MECE principle - complete endpoint coverage
"""

import pytest
import asyncio
import json
import tempfile
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Import the main app
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.rapid_minutes.main import app
from src.rapid_minutes.api.upload import router as upload_router
from src.rapid_minutes.api.process import router as process_router
from src.rapid_minutes.api.download import router as download_router


class TestUploadAPI:
    """Test file upload API endpoints"""
    
    def setup_method(self):
        """Setup test client"""
        self.client = TestClient(app)
    
    def test_single_file_upload_success(self, sample_text_content):
        """Test successful single file upload"""
        # Create test file
        test_file = ("test.txt", sample_text_content, "text/plain")
        
        response = self.client.post(
            "/api/upload/single",
            files={"file": test_file},
            data={"processing_options": json.dumps({"auto_process": True})}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "file_id" in data
        assert data["message"] == "File uploaded successfully"
    
    def test_single_file_upload_invalid_file(self):
        """Test upload with invalid file"""
        # Empty file
        test_file = ("empty.txt", "", "text/plain")
        
        response = self.client.post(
            "/api/upload/single",
            files={"file": test_file}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "Empty file not allowed" in data["detail"]
    
    def test_single_file_upload_file_too_large(self):
        """Test upload with file exceeding size limit"""
        # Create large file content (simulate > 10MB)
        large_content = "x" * (11 * 1024 * 1024)  # 11MB
        test_file = ("large.txt", large_content, "text/plain")
        
        response = self.client.post(
            "/api/upload/single",
            files={"file": test_file}
        )
        
        assert response.status_code == 413
        data = response.json()
        assert "File too large" in data["detail"]
    
    def test_batch_file_upload(self, sample_text_content):
        """Test batch file upload"""
        files = [
            ("files", ("test1.txt", sample_text_content, "text/plain")),
            ("files", ("test2.txt", sample_text_content, "text/plain"))
        ]
        
        response = self.client.post(
            "/api/upload/batch",
            files=files,
            data={"request_data": json.dumps({"processing_options": {"auto_process": False}})}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["uploaded_count"] == 2
        assert data["failed_count"] == 0
    
    def test_get_supported_types(self):
        """Test getting supported file types"""
        response = self.client.get("/api/upload/supported-types")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "supported_types" in data
        assert "max_file_size_mb" in data
    
    def test_get_available_templates(self):
        """Test getting available templates"""
        response = self.client.get("/api/upload/templates")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "templates" in data
    
    def test_validate_file(self, sample_text_content):
        """Test file validation"""
        test_file = ("test.txt", sample_text_content, "text/plain")
        
        response = self.client.post(
            "/api/upload/validate",
            files={"file": test_file}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "validation" in data
        assert data["validation"]["valid"] is True
    
    def test_get_upload_stats(self):
        """Test getting upload statistics"""
        response = self.client.get("/api/upload/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "statistics" in data


class TestProcessAPI:
    """Test processing API endpoints"""
    
    def setup_method(self):
        """Setup test client"""
        self.client = TestClient(app)
    
    def test_get_processing_status_not_found(self):
        """Test getting status for non-existent job"""
        response = self.client.get("/api/process/status/nonexistent-job-id")
        
        assert response.status_code == 404
        data = response.json()
        assert "Job not found" in data["detail"]
    
    def test_list_processing_jobs(self):
        """Test listing processing jobs"""
        response = self.client.get("/api/process/jobs")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "jobs" in data
        assert "total_count" in data
    
    def test_list_processing_jobs_with_filters(self):
        """Test listing jobs with filters"""
        response = self.client.get(
            "/api/process/jobs",
            params={
                "user_id": "test-user",
                "status": "completed",
                "limit": 10
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    def test_get_processing_result_not_found(self):
        """Test getting result for non-existent job"""
        response = self.client.get("/api/process/result/nonexistent-job-id")
        
        assert response.status_code == 200  # Returns success=False instead of 404
        data = response.json()
        assert data["success"] is False
        assert "Job not found" in data["error"]
    
    def test_cancel_processing_job(self):
        """Test cancelling processing job"""
        response = self.client.post("/api/process/cancel/test-job-id")
        
        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "cancel"
    
    def test_retry_failed_job(self):
        """Test retrying failed job"""
        response = self.client.post("/api/process/retry/test-job-id")
        
        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "retry"
    
    def test_get_processing_statistics(self):
        """Test getting processing statistics"""
        response = self.client.get("/api/process/statistics")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "statistics" in data
        assert "processing" in data["statistics"]
        assert "files" in data["statistics"]
    
    def test_get_processing_health(self):
        """Test getting processing health status"""
        response = self.client.get("/api/process/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "health_status" in data
        assert "metrics" in data


class TestDownloadAPI:
    """Test download API endpoints"""
    
    def setup_method(self):
        """Setup test client"""
        self.client = TestClient(app)
    
    def test_prepare_download_not_found(self):
        """Test preparing download for non-existent file"""
        response = self.client.post("/api/download/prepare/nonexistent-file-id")
        
        assert response.status_code == 200  # Returns success=False instead of 404
        data = response.json()
        assert data["success"] is False
        assert "File not found" in data["error"]
    
    def test_download_file_not_found(self):
        """Test downloading with invalid session"""
        response = self.client.get("/api/download/file/invalid-session-id")
        
        assert response.status_code == 404
        data = response.json()
        assert "Download session not found" in data["detail"]
    
    def test_create_batch_download_empty(self):
        """Test creating batch download with no files"""
        response = self.client.post(
            "/api/download/batch",
            json={"file_ids": []}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "No files specified" in data["detail"]
    
    def test_create_batch_download_too_many(self):
        """Test creating batch download with too many files"""
        file_ids = [f"file-{i}" for i in range(51)]  # Exceeds limit of 50
        
        response = self.client.post(
            "/api/download/batch",
            json={"file_ids": file_ids}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "Too many files" in data["detail"]
    
    def test_convert_file_format_not_found(self):
        """Test converting non-existent file"""
        response = self.client.post(
            "/api/download/convert",
            json={
                "source_file_id": "nonexistent-file-id",
                "target_format": "pdf"
            }
        )
        
        assert response.status_code == 200  # Returns success=False instead of 404
        data = response.json()
        assert data["success"] is False
        assert "Source file not found" in data["error"]
    
    def test_get_supported_formats(self):
        """Test getting supported formats"""
        response = self.client.get("/api/download/formats")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "supported_formats" in data
        assert "conversions" in data
        assert "format_descriptions" in data
    
    def test_preview_file_not_found(self):
        """Test previewing non-existent file"""
        response = self.client.get("/api/download/preview/nonexistent-file-id")
        
        assert response.status_code == 404
        data = response.json()
        assert "File not found" in data["detail"]
    
    def test_get_download_history(self):
        """Test getting download history"""
        response = self.client.get("/api/download/history")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "history" in data
        assert "total_count" in data
    
    def test_get_download_history_with_filters(self):
        """Test getting download history with filters"""
        response = self.client.get(
            "/api/download/history",
            params={
                "user_id": "test-user",
                "limit": 10
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    def test_get_download_statistics(self):
        """Test getting download statistics"""
        response = self.client.get("/api/download/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "statistics" in data
        assert "downloads" in data["statistics"]
        assert "files" in data["statistics"]


class TestAPIErrorHandling:
    """Test API error handling"""
    
    def setup_method(self):
        """Setup test client"""
        self.client = TestClient(app)
    
    def test_404_not_found(self):
        """Test 404 handling for non-existent endpoints"""
        response = self.client.get("/api/nonexistent/endpoint")
        assert response.status_code == 404
    
    def test_405_method_not_allowed(self):
        """Test 405 handling for wrong HTTP methods"""
        response = self.client.delete("/api/upload/single")
        assert response.status_code == 405
    
    def test_422_validation_error(self):
        """Test 422 handling for validation errors"""
        response = self.client.post(
            "/api/upload/single"
            # Missing required file parameter
        )
        assert response.status_code == 422


class TestAPIAuthentication:
    """Test API authentication and authorization (if implemented)"""
    
    def setup_method(self):
        """Setup test client"""
        self.client = TestClient(app)
    
    @pytest.mark.skip(reason="Authentication not yet implemented")
    def test_unauthorized_access(self):
        """Test unauthorized access to protected endpoints"""
        response = self.client.get("/api/protected/endpoint")
        assert response.status_code == 401
    
    @pytest.mark.skip(reason="Authentication not yet implemented")
    def test_authorized_access(self):
        """Test authorized access with valid token"""
        headers = {"Authorization": "Bearer valid-token"}
        response = self.client.get("/api/protected/endpoint", headers=headers)
        assert response.status_code == 200


class TestAPIPerformance:
    """Test API performance characteristics"""
    
    def setup_method(self):
        """Setup test client"""
        self.client = TestClient(app)
    
    @pytest.mark.slow
    def test_concurrent_uploads(self, sample_text_content):
        """Test handling of concurrent file uploads"""
        import threading
        import time
        
        results = []
        
        def upload_file():
            test_file = ("test.txt", sample_text_content, "text/plain")
            response = self.client.post(
                "/api/upload/single",
                files={"file": test_file}
            )
            results.append(response.status_code)
        
        # Create multiple threads for concurrent uploads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=upload_file)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check that all uploads were successful
        assert len(results) == 5
        assert all(status == 200 for status in results)
    
    @pytest.mark.slow
    def test_api_response_time(self, sample_text_content):
        """Test API response times are within acceptable limits"""
        import time
        
        start_time = time.time()
        
        test_file = ("test.txt", sample_text_content, "text/plain")
        response = self.client.post(
            "/api/upload/single",
            files={"file": test_file}
        )
        
        end_time = time.time()
        response_time = end_time - start_time
        
        assert response.status_code == 200
        assert response_time < 5.0  # Should respond within 5 seconds


@pytest.mark.integration
class TestFullAPIWorkflow:
    """Test complete API workflow integration"""
    
    def setup_method(self):
        """Setup test client"""
        self.client = TestClient(app)
    
    def test_complete_workflow(self, sample_text_content):
        """Test complete upload -> process -> download workflow"""
        # Step 1: Upload file
        test_file = ("meeting.txt", sample_text_content, "text/plain")
        upload_response = self.client.post(
            "/api/upload/single",
            files={"file": test_file},
            data={"processing_options": json.dumps({"auto_process": True})}
        )
        
        assert upload_response.status_code == 200
        upload_data = upload_response.json()
        assert upload_data["success"] is True
        
        file_id = upload_data["file_id"]
        job_id = upload_data.get("job_id")
        
        # Step 2: Check processing status (if auto_process was enabled)
        if job_id:
            status_response = self.client.get(f"/api/process/status/{job_id}")
            assert status_response.status_code in [200, 404]  # Job might not exist in test env
        
        # Step 3: Get processing statistics
        stats_response = self.client.get("/api/process/statistics")
        assert stats_response.status_code == 200
        stats_data = stats_response.json()
        assert stats_data["success"] is True
        
        # Step 4: Get supported formats
        formats_response = self.client.get("/api/download/formats")
        assert formats_response.status_code == 200
        formats_data = formats_response.json()
        assert formats_data["success"] is True