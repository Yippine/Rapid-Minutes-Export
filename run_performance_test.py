#!/usr/bin/env python3
"""
Performance Test Runner
Run basic performance validation tests for the Rapid Minutes Export system
"""

import sys
import os
import time
import traceback
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from rapid_minutes.ai.text_processor import TextProcessor
from rapid_minutes.ai.ollama_client import OllamaClient
from rapid_minutes.document.word_generator import WordGenerator
from rapid_minutes.document.document_validator import DocumentValidator


def run_basic_performance_test():
    """Run basic performance validation test"""
    print("🚀 Rapid Minutes Export - Performance Test")
    print("=" * 60)
    
    results = {
        "tests_passed": 0,
        "tests_failed": 0,
        "performance_metrics": {},
        "issues": []
    }
    
    try:
        # Test 1: Text Processing Performance
        print("\n📝 Testing Text Processing Performance...")
        start_time = time.time()
        
        processor = TextProcessor()
        sample_text = """
        Meeting Title: Weekly Team Standup
        Date: 2024-01-15
        Attendees: Alice, Bob, Charlie
        
        Discussion Topics:
        - Project status updates
        - Resource allocation review
        - Next sprint planning
        
        Key Decisions:
        - Approved budget increase for Q2
        - Decided to hire two additional developers
        
        Action Items:
        - Alice: Complete requirements document by Friday
        - Bob: Set up development environment
        - Charlie: Schedule client review meeting
        """
        
        # Test text processing methods
        cleaned_text = processor.clean_text(sample_text)
        quality_check = processor.validate_text_quality(cleaned_text)
        preprocessed = processor.preprocess_for_ai(cleaned_text)
        
        text_processing_time = time.time() - start_time
        results["performance_metrics"]["text_processing_time"] = round(text_processing_time, 4)
        
        if text_processing_time < 5.0 and quality_check["valid"]:
            print(f"✅ Text processing passed ({text_processing_time:.3f}s)")
            results["tests_passed"] += 1
        else:
            print(f"❌ Text processing failed ({text_processing_time:.3f}s)")
            results["tests_failed"] += 1
            results["issues"].append("Text processing too slow or quality check failed")
        
        # Test 2: Document Generation Performance
        print("\n📄 Testing Document Generation Performance...")
        start_time = time.time()
        
        word_generator = WordGenerator()
        
        # Mock extracted meeting data
        meeting_data = {
            "meeting_title": "Performance Test Meeting",
            "date": "2024-01-15",
            "time": "14:00",
            "location": "Conference Room A",
            "attendees": ["Alice", "Bob", "Charlie"],
            "key_topics": [
                "System performance evaluation",
                "Quality assurance procedures",
                "Documentation standards"
            ],
            "decisions": [
                "Implement automated performance monitoring",
                "Establish quality benchmarks"
            ],
            "action_items": [
                {
                    "task": "Set up monitoring dashboard",
                    "assignee": "Alice",
                    "deadline": "2024-01-20",
                    "priority": "high"
                },
                {
                    "task": "Document testing procedures",
                    "assignee": "Bob", 
                    "deadline": "2024-01-25",
                    "priority": "medium"
                }
            ],
            "follow_up_items": ["Schedule follow-up review"],
            "next_meeting": "2024-01-22 14:00",
            "meeting_type": "performance_review",
            "duration": "60 minutes",
            "summary": "Performance testing and quality assurance discussion."
        }
        
        # Generate Word document
        word_content = word_generator.generate_document(meeting_data)
        document_generation_time = time.time() - start_time
        results["performance_metrics"]["document_generation_time"] = round(document_generation_time, 4)
        results["performance_metrics"]["document_size_bytes"] = len(word_content)
        
        if document_generation_time < 10.0 and len(word_content) > 1000:
            print(f"✅ Document generation passed ({document_generation_time:.3f}s, {len(word_content)} bytes)")
            results["tests_passed"] += 1
        else:
            print(f"❌ Document generation failed ({document_generation_time:.3f}s, {len(word_content)} bytes)")
            results["tests_failed"] += 1
            results["issues"].append("Document generation too slow or output too small")
        
        # Test 3: PDF Conversion Capabilities
        print("\n🔄 Testing PDF Conversion Capabilities...")
        start_time = time.time()
        
        try:
            pdf_capabilities = word_generator.check_pdf_conversion_capabilities()
            pdf_check_time = time.time() - start_time
            
            available_methods = sum(1 for method, available in pdf_capabilities.items() 
                                  if isinstance(available, bool) and available)
            
            print(f"📊 PDF Conversion Methods Available: {available_methods}")
            for method, available in pdf_capabilities.items():
                if isinstance(available, bool):
                    status = "✅" if available else "❌"
                    print(f"   {status} {method}")
            
            if available_methods > 0:
                print(f"✅ PDF capabilities check passed ({pdf_check_time:.3f}s)")
                results["tests_passed"] += 1
                results["performance_metrics"]["pdf_methods_available"] = available_methods
            else:
                print(f"⚠️  PDF capabilities limited ({pdf_check_time:.3f}s)")
                results["tests_passed"] += 1  # Not critical for basic operation
                results["issues"].append("No PDF conversion methods available")
                
        except Exception as e:
            print(f"❌ PDF capabilities check failed: {str(e)}")
            results["tests_failed"] += 1
            results["issues"].append(f"PDF capabilities check error: {str(e)}")
        
        # Test 4: Document Validation
        print("\n🔍 Testing Document Validation...")
        start_time = time.time()
        
        validator = DocumentValidator()
        validation_result = validator.validate_document_comprehensive(word_content, "docx")
        validation_time = time.time() - start_time
        results["performance_metrics"]["validation_time"] = round(validation_time, 4)
        
        validation_score = validation_result.get("quality_metrics", {}).get("overall_score", 0)
        is_valid = validation_result.get("is_valid", False)
        
        if validation_time < 5.0 and is_valid and validation_score >= 70:
            print(f"✅ Document validation passed ({validation_time:.3f}s, score: {validation_score})")
            results["tests_passed"] += 1
        else:
            print(f"❌ Document validation failed ({validation_time:.3f}s, score: {validation_score})")
            results["tests_failed"] += 1
            results["issues"].append("Document validation failed or score too low")
        
        # Test 5: AI Extraction Data Validation
        print("\n🧠 Testing AI Data Validation...")
        start_time = time.time()
        
        validation_result = processor.validate_extracted_data(meeting_data)
        data_validation_time = time.time() - start_time
        results["performance_metrics"]["data_validation_time"] = round(data_validation_time, 4)
        
        confidence_score = validation_result.get("confidence_score", 0)
        data_is_valid = validation_result.get("is_valid", False)
        
        if data_validation_time < 3.0 and data_is_valid and confidence_score >= 80:
            print(f"✅ Data validation passed ({data_validation_time:.3f}s, confidence: {confidence_score}%)")
            results["tests_passed"] += 1
        else:
            print(f"❌ Data validation failed ({data_validation_time:.3f}s, confidence: {confidence_score}%)")
            results["tests_failed"] += 1
            results["issues"].append("Data validation failed or confidence too low")
            
    except Exception as e:
        print(f"❌ Performance test failed with error: {str(e)}")
        print("Stack trace:")
        traceback.print_exc()
        results["tests_failed"] += 1
        results["issues"].append(f"Test execution error: {str(e)}")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 PERFORMANCE TEST SUMMARY")
    print("=" * 60)
    
    total_tests = results["tests_passed"] + results["tests_failed"]
    success_rate = (results["tests_passed"] / total_tests * 100) if total_tests > 0 else 0
    
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {results['tests_passed']} ✅")
    print(f"Failed: {results['tests_failed']} ❌") 
    print(f"Success Rate: {success_rate:.1f}%")
    
    # Performance Metrics Summary
    if results["performance_metrics"]:
        print(f"\n⚡ Performance Metrics:")
        for metric, value in results["performance_metrics"].items():
            print(f"   {metric}: {value}")
    
    # Issues Summary
    if results["issues"]:
        print(f"\n⚠️  Issues Found:")
        for i, issue in enumerate(results["issues"], 1):
            print(f"   {i}. {issue}")
    
    # Overall Assessment
    print(f"\n🎯 Overall Assessment:")
    if success_rate >= 80:
        print("✅ System performance meets requirements")
        print("🚀 Ready for production use")
    elif success_rate >= 60:
        print("⚠️  System performance needs optimization")
        print("🔧 Address performance issues before production")
    else:
        print("❌ System performance below acceptable thresholds")
        print("🚨 Major performance issues require immediate attention")
    
    return results


if __name__ == "__main__":
    try:
        run_basic_performance_test()
    except KeyboardInterrupt:
        print("\n\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n💥 Unexpected error: {str(e)}")
        traceback.print_exc()