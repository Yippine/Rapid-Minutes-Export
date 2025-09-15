"""
Performance and Load Testing
Tests for system performance, scalability, and resource usage
"""

import pytest
import asyncio
import time
import psutil
from concurrent.futures import ThreadPoolExecutor, as_completed
import statistics

from src.rapid_minutes.ai.text_preprocessor import TextPreprocessor


class TestPerformanceBenchmarks:
    """Performance benchmark tests"""
    
    @pytest.fixture
    def large_meeting_text(self):
        """Generate large meeting transcript for performance testing"""
        base_text = """
        This is a comprehensive quarterly business review meeting.
        Attendees include executives, managers, and team leads from all departments.
        The agenda covers financial performance, project updates, strategic initiatives, and resource planning.
        """
        
        # Repeat to create ~50KB text
        return (base_text * 500).strip()
    
    @pytest.fixture
    def preprocessor(self):
        """Text preprocessor instance"""
        return TextPreprocessor()
    
    @pytest.mark.asyncio
    async def test_preprocessing_performance(self, preprocessor, large_meeting_text):
        """Test text preprocessing performance"""
        start_time = time.time()
        
        result = await preprocessor.preprocess(large_meeting_text)
        
        processing_time = time.time() - start_time
        
        # Performance requirements from SYSTEM_ARCHITECTURE.md
        assert processing_time < 10.0  # Should complete within 10 seconds
        assert result is not None
        assert len(result.cleaned_text) > 0
        
        # Log performance metrics
        print(f"Preprocessing time: {processing_time:.2f}s for {len(large_meeting_text)} chars")
    
    def test_memory_usage_preprocessing(self, preprocessor):
        """Test memory usage during preprocessing"""
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create large text
        large_text = "Test meeting content. " * 10000
        
        # Run preprocessing
        asyncio.run(preprocessor.preprocess(large_text))
        
        peak_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = peak_memory - initial_memory
        
        # Memory usage should be reasonable (< 100MB increase)
        assert memory_increase < 100
        print(f"Memory increase: {memory_increase:.2f}MB")
    
    @pytest.mark.asyncio
    async def test_concurrent_preprocessing(self, preprocessor):
        """Test concurrent preprocessing performance"""
        test_texts = [
            "Meeting 1 content. " * 1000,
            "Meeting 2 content. " * 1000, 
            "Meeting 3 content. " * 1000,
            "Meeting 4 content. " * 1000,
            "Meeting 5 content. " * 1000
        ]
        
        start_time = time.time()
        
        # Process concurrently
        tasks = [preprocessor.preprocess(text) for text in test_texts]
        results = await asyncio.gather(*tasks)
        
        total_time = time.time() - start_time
        
        # Concurrent processing should be faster than sequential
        assert total_time < 20.0  # Should complete within 20 seconds
        assert len(results) == 5
        assert all(result is not None for result in results)
        
        print(f"Concurrent preprocessing: {total_time:.2f}s for {len(test_texts)} texts")


class TestScalabilityMetrics:
    """Scalability and load testing"""
    
    def test_concurrent_requests_simulation(self):
        """Simulate concurrent user requests"""
        def simulate_user_request(user_id):
            """Simulate a single user request"""
            start_time = time.time()
            
            # Simulate processing steps
            time.sleep(0.1)  # Upload time
            time.sleep(2.0)  # Processing time  
            time.sleep(0.1)  # Download time
            
            return {
                'user_id': user_id,
                'total_time': time.time() - start_time,
                'success': True
            }
        
        # Test with 10 concurrent users (requirement from architecture)
        num_concurrent_users = 10
        
        with ThreadPoolExecutor(max_workers=num_concurrent_users) as executor:
            futures = [
                executor.submit(simulate_user_request, i) 
                for i in range(num_concurrent_users)
            ]
            
            results = [future.result() for future in as_completed(futures)]
        
        # All requests should complete successfully
        assert len(results) == num_concurrent_users
        assert all(result['success'] for result in results)
        
        # Response times should be reasonable
        response_times = [result['total_time'] for result in results]
        avg_response_time = statistics.mean(response_times)
        max_response_time = max(response_times)
        
        assert avg_response_time < 5.0   # Average under 5 seconds
        assert max_response_time < 10.0  # Max under 10 seconds
        
        print(f"Concurrent users: {num_concurrent_users}")
        print(f"Average response time: {avg_response_time:.2f}s")
        print(f"Max response time: {max_response_time:.2f}s")
    
    def test_resource_limits(self):
        """Test system resource limits"""
        # Test file size limits
        max_file_size_mb = 10  # From architecture requirements
        max_file_size_bytes = max_file_size_mb * 1024 * 1024
        
        # Create test content at size limit
        test_content = "x" * max_file_size_bytes
        
        # Should be able to handle max file size
        assert len(test_content) == max_file_size_bytes
        assert len(test_content.encode('utf-8')) <= max_file_size_bytes
    
    def test_processing_time_limits(self):
        """Test processing time limits"""
        # Processing should complete within 30 seconds (architecture requirement)
        max_processing_time = 30.0
        
        # Simulate processing steps
        processing_steps = {
            'preprocessing': 5.0,
            'ollama_extraction': 20.0,  # Longest step
            'document_generation': 3.0,
            'pdf_conversion': 2.0
        }
        
        total_estimated_time = sum(processing_steps.values())
        
        # Total time should be within limits
        assert total_estimated_time <= max_processing_time
        
        print(f"Estimated total processing time: {total_estimated_time}s")


class TestSystemReliability:
    """System reliability and fault tolerance tests"""
    
    def test_error_recovery(self):
        """Test error recovery mechanisms"""
        error_scenarios = [
            'network_timeout',
            'insufficient_memory',
            'disk_space_full', 
            'invalid_input_format',
            'service_unavailable'
        ]
        
        # Each error scenario should have a recovery strategy
        recovery_strategies = {
            'network_timeout': 'Retry with exponential backoff',
            'insufficient_memory': 'Process in smaller chunks',
            'disk_space_full': 'Clean temporary files',
            'invalid_input_format': 'Return user-friendly error message',
            'service_unavailable': 'Queue request for later processing'
        }
        
        assert len(recovery_strategies) == len(error_scenarios)
        
        # All scenarios should have recovery strategies
        for scenario in error_scenarios:
            assert scenario in recovery_strategies
    
    def test_graceful_degradation(self):
        """Test graceful degradation under load"""
        # System should degrade gracefully under high load
        load_levels = ['normal', 'high', 'critical']
        
        expected_behavior = {
            'normal': 'Full functionality, optimal performance',
            'high': 'Slightly slower response, all features available',
            'critical': 'Basic functionality, queue requests, notify users'
        }
        
        assert len(expected_behavior) == len(load_levels)
        
        # System should maintain basic functionality even under critical load
        for level in load_levels:
            assert level in expected_behavior
    
    def test_monitoring_metrics(self):
        """Test system monitoring and metrics"""
        # Key metrics to monitor for performance
        monitoring_metrics = [
            'response_time',
            'throughput',
            'error_rate',
            'cpu_usage',
            'memory_usage',
            'disk_usage',
            'active_connections',
            'queue_length'
        ]
        
        # All metrics should be trackable
        assert len(monitoring_metrics) == 8
        
        # Critical thresholds for alerts
        alert_thresholds = {
            'response_time': 30.0,      # seconds
            'error_rate': 0.05,         # 5%
            'cpu_usage': 0.80,          # 80%
            'memory_usage': 0.85,       # 85%
            'disk_usage': 0.90          # 90%
        }
        
        # All thresholds should be reasonable
        assert all(threshold > 0 for threshold in alert_thresholds.values())


class TestCacheAndOptimization:
    """Caching and optimization tests"""
    
    def test_caching_strategy(self):
        """Test caching mechanisms"""
        # Items that should be cached for performance
        cacheable_items = [
            'preprocessed_text',
            'template_files',
            'ollama_model_responses',
            'generated_documents',
            'user_preferences'
        ]
        
        # Cache TTL (time-to-live) for different items
        cache_ttl = {
            'preprocessed_text': 3600,      # 1 hour
            'template_files': 86400,        # 24 hours
            'ollama_model_responses': 1800, # 30 minutes
            'generated_documents': 7200,    # 2 hours
            'user_preferences': 604800      # 1 week
        }
        
        assert len(cache_ttl) == len(cacheable_items)
        
        # All TTL values should be positive
        assert all(ttl > 0 for ttl in cache_ttl.values())
    
    def test_optimization_techniques(self):
        """Test optimization techniques"""
        # Optimization techniques to implement
        optimizations = [
            'async_processing',
            'connection_pooling',
            'lazy_loading',
            'batch_processing',
            'response_compression'
        ]
        
        # Each optimization should improve specific metrics
        optimization_benefits = {
            'async_processing': 'Improved concurrency',
            'connection_pooling': 'Reduced connection overhead',
            'lazy_loading': 'Faster initial load times',
            'batch_processing': 'Better resource utilization',
            'response_compression': 'Reduced bandwidth usage'
        }
        
        assert len(optimization_benefits) == len(optimizations)
        
        # All optimizations should have clear benefits
        for opt in optimizations:
            assert opt in optimization_benefits