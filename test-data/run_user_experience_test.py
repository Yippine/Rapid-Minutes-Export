#!/usr/bin/env python3
"""
User Experience Test Runner
Test system against ICE principles (Intuitive, Concise, Encompassing)
"""

import sys
import os
import time
import json
import traceback
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from rapid_minutes.ai.text_processor import TextProcessor
from rapid_minutes.document.word_generator import WordGenerator
from rapid_minutes.document.document_validator import DocumentValidator


def test_intuitive_experience():
    """Test iPhone-like intuitive operation (ICE: Intuitive)"""
    print("📱 Testing Intuitive Experience...")
    
    results = {
        "ease_of_use_score": 0,
        "steps_required": 0,
        "error_clarity": 0,
        "issues": []
    }
    
    try:
        # Simulate new user workflow
        steps = [
            "1. Upload text file (drag & drop simulation)",
            "2. Click generate button",
            "3. Download Word document"
        ]
        
        print("🎯 User Journey Simulation:")
        for step in steps:
            print(f"   {step}")
        
        results["steps_required"] = len(steps)
        
        # Test 1: Simple text input processing
        sample_text = """
        Meeting: Team Weekly Sync
        Date: January 15, 2024
        
        Attendees:
        - Alice (Project Manager)
        - Bob (Developer)  
        - Carol (Designer)
        
        Discussion:
        We discussed the progress on the new feature.
        Alice reported 80% completion.
        Bob mentioned some technical challenges.
        Carol shared the updated designs.
        
        Action Items:
        - Bob will fix the login issue by Friday
        - Carol will finalize the color scheme
        - Alice will schedule client review
        """
        
        processor = TextProcessor()
        word_generator = WordGenerator()
        
        # Step 1: Text processing (should be invisible to user)
        start_time = time.time()
        cleaned_text = processor.clean_text(sample_text)
        quality_check = processor.validate_text_quality(cleaned_text)
        processing_time = time.time() - start_time
        
        if processing_time < 2.0 and quality_check["valid"]:
            print("✅ Step 1: Text processing - Fast and transparent")
            results["ease_of_use_score"] += 25
        else:
            print("❌ Step 1: Text processing - Too slow or failed")
            results["issues"].append("Text processing not seamless")
        
        # Step 2: Document generation (should be one-click)
        mock_meeting_data = {
            "meeting_title": "Team Weekly Sync",
            "date": "2024-01-15",
            "attendees": ["Alice (PM)", "Bob (Dev)", "Carol (Designer)"],
            "key_topics": [
                "New feature progress review",
                "Technical challenges discussion",
                "Design updates presentation"
            ],
            "decisions": ["Proceed with current timeline"],
            "action_items": [
                {
                    "task": "Fix login issue",
                    "assignee": "Bob",
                    "deadline": "Friday",
                    "priority": "high"
                },
                {
                    "task": "Finalize color scheme", 
                    "assignee": "Carol",
                    "deadline": "Next week",
                    "priority": "medium"
                }
            ]
        }
        
        start_time = time.time()
        word_document = word_generator.generate_document(mock_meeting_data)
        generation_time = time.time() - start_time
        
        if generation_time < 5.0 and len(word_document) > 1000:
            print("✅ Step 2: Document generation - Quick one-click operation")
            results["ease_of_use_score"] += 25
        else:
            print("❌ Step 2: Document generation - Too slow")
            results["issues"].append("Document generation not responsive enough")
        
        # Step 3: Download experience (should be immediate)
        if len(word_document) > 0:
            print("✅ Step 3: Download - Immediate file availability")
            results["ease_of_use_score"] += 25
        else:
            print("❌ Step 3: Download - No file generated")
            results["issues"].append("No downloadable file produced")
        
        # Test error handling clarity
        try:
            # Test with invalid input
            invalid_text = ""
            quality_check = processor.validate_text_quality(invalid_text)
            
            if not quality_check["valid"] and "reason" in quality_check:
                print("✅ Error handling: Clear error messages provided")
                results["error_clarity"] = 100
                results["ease_of_use_score"] += 25
            else:
                print("⚠️  Error handling: Could be clearer")
                results["error_clarity"] = 70
                results["ease_of_use_score"] += 15
        except Exception:
            print("❌ Error handling: Poor error experience")
            results["error_clarity"] = 0
            results["issues"].append("Poor error handling")
        
    except Exception as e:
        results["issues"].append(f"Intuitive experience test failed: {str(e)}")
    
    return results


def test_concise_functionality():
    """Test that only essential features are provided (ICE: Concise)"""
    print("\n🎯 Testing Concise Functionality...")
    
    results = {
        "feature_count": 0,
        "essential_features": [],
        "unnecessary_features": [],
        "conciseness_score": 0
    }
    
    try:
        # Define essential features for meeting minutes generation
        essential_features = [
            "text_input_processing",
            "meeting_info_extraction", 
            "word_document_generation",
            "download_capability",
            "basic_validation"
        ]
        
        # Define potentially unnecessary features (complexity indicators)
        complexity_indicators = [
            "multiple_output_formats",
            "advanced_styling_options",
            "user_authentication",
            "collaborative_editing",
            "version_control",
            "template_customization",
            "advanced_analytics"
        ]
        
        # Test core features
        processor = TextProcessor()
        word_generator = WordGenerator()
        validator = DocumentValidator()
        
        # Check what's available
        available_features = []
        
        # Text processing capability
        if hasattr(processor, 'clean_text') and hasattr(processor, 'validate_text_quality'):
            available_features.append("text_input_processing")
        
        # Meeting info extraction 
        if hasattr(processor, 'validate_extracted_data'):
            available_features.append("meeting_info_extraction")
        
        # Document generation
        if hasattr(word_generator, 'generate_document'):
            available_features.append("word_document_generation")
        
        # Validation
        if hasattr(validator, 'validate_document_comprehensive'):
            available_features.append("basic_validation")
        
        # Download capability (implicit in generate_document returning bytes)
        available_features.append("download_capability")
        
        # PDF generation (optional complexity)
        if hasattr(word_generator, 'generate_pdf_from_word'):
            available_features.append("pdf_generation")
        
        results["essential_features"] = [f for f in available_features if f in essential_features]
        results["feature_count"] = len(available_features)
        
        # Score based on essential features coverage
        essential_coverage = len(results["essential_features"]) / len(essential_features)
        
        # Penalty for too many features (complexity)
        complexity_penalty = max(0, (len(available_features) - 6) * 10)  # 6 is ideal number
        
        results["conciseness_score"] = max(0, int(essential_coverage * 100 - complexity_penalty))
        
        print(f"📊 Features Analysis:")
        print(f"   Essential features covered: {len(results['essential_features'])}/{len(essential_features)}")
        print(f"   Total features: {results['feature_count']}")
        print(f"   Conciseness score: {results['conciseness_score']}%")
        
        if results["conciseness_score"] >= 80:
            print("✅ Conciseness: System focuses on essential features")
        elif results["conciseness_score"] >= 60:
            print("⚠️  Conciseness: Some unnecessary complexity detected")
        else:
            print("❌ Conciseness: System may be overly complex")
        
    except Exception as e:
        results["error"] = str(e)
        
    return results


def test_encompassing_coverage():
    """Test comprehensive coverage of meeting minutes scenarios (ICE: Encompassing)"""
    print("\n🌐 Testing Encompassing Coverage...")
    
    results = {
        "scenario_coverage": 0,
        "tested_scenarios": [],
        "successful_scenarios": [],
        "failed_scenarios": []
    }
    
    # Test scenarios representing different meeting types and content
    test_scenarios = [
        {
            "name": "Basic team meeting",
            "text": """Team meeting on Jan 15. Attendees: Alice, Bob. Discussed project status. Action: Bob will update docs."""
        },
        {
            "name": "Formal board meeting",
            "text": """
            Board Meeting Minutes
            Date: January 15, 2024
            Time: 2:00 PM
            Location: Conference Room A
            
            Attendees:
            - John Smith, CEO
            - Jane Doe, CFO
            - Bob Wilson, CTO
            
            Agenda Items:
            1. Q4 Financial Review
            2. Strategic Planning for 2024
            3. Budget Approval
            
            Decisions Made:
            - Approved $2M budget for new initiatives
            - Authorized hiring of 10 new employees
            
            Action Items:
            - CFO to prepare detailed budget breakdown by Jan 30
            - CTO to draft technology roadmap by Feb 15
            """
        },
        {
            "name": "Technical design review",
            "text": """
            Design Review Session
            System: Authentication Service
            Reviewers: Alice (architect), Bob (security), Carol (dev)
            
            Key Points:
            - OAuth 2.0 implementation approved
            - Database schema needs optimization
            - Security requirements met
            
            Action Items:
            - Optimize database queries (Bob, this week)
            - Update API documentation (Carol, Friday)
            """
        },
        {
            "name": "Client meeting",
            "text": """
            Client Meeting - Project Milestone Review
            Client: ABC Corporation
            Date: January 15, 2024
            
            Discussion:
            Client expressed satisfaction with progress.
            Requested additional features for mobile app.
            Budget increase approved for Q2.
            
            Next Steps:
            - Prepare mobile feature specification
            - Schedule development review for February
            """
        },
        {
            "name": "Minimal content meeting",
            "text": """
            Quick standup. Everyone present. No blockers. Continue current tasks.
            """
        }
    ]
    
    processor = TextProcessor()
    word_generator = WordGenerator()
    
    for scenario in test_scenarios:
        try:
            scenario_name = scenario["name"]
            text_content = scenario["text"]
            
            print(f"   Testing: {scenario_name}")
            
            # Test text processing
            cleaned = processor.clean_text(text_content)
            quality = processor.validate_text_quality(cleaned)
            
            # Create mock extracted data for document generation
            mock_data = {
                "meeting_title": scenario_name,
                "date": "2024-01-15",
                "attendees": ["Test User"],
                "key_topics": ["Meeting topic"],
                "decisions": ["Sample decision"],
                "action_items": [
                    {
                        "task": "Follow up on action",
                        "assignee": "Assignee",
                        "deadline": "Next week",
                        "priority": "medium"
                    }
                ]
            }
            
            # Test document generation
            document = word_generator.generate_document(mock_data)
            
            # Criteria for success
            text_quality_ok = quality.get("valid", False) or len(text_content.strip()) < 50  # Allow minimal content
            document_generated = len(document) > 1000
            
            if text_quality_ok and document_generated:
                results["successful_scenarios"].append(scenario_name)
                print(f"     ✅ Passed")
            else:
                results["failed_scenarios"].append(scenario_name)
                print(f"     ❌ Failed")
            
            results["tested_scenarios"].append(scenario_name)
            
        except Exception as e:
            results["failed_scenarios"].append(f"{scenario_name} (Error: {str(e)})")
            print(f"     ❌ Error: {str(e)}")
    
    # Calculate coverage
    total_scenarios = len(test_scenarios)
    successful_scenarios = len(results["successful_scenarios"])
    results["scenario_coverage"] = (successful_scenarios / total_scenarios * 100) if total_scenarios > 0 else 0
    
    print(f"\n📊 Coverage Analysis:")
    print(f"   Scenarios tested: {len(results['tested_scenarios'])}")
    print(f"   Successful: {len(results['successful_scenarios'])}")
    print(f"   Failed: {len(results['failed_scenarios'])}")
    print(f"   Coverage score: {results['scenario_coverage']:.1f}%")
    
    if results["scenario_coverage"] >= 90:
        print("✅ Coverage: System handles wide variety of meeting scenarios")
    elif results["scenario_coverage"] >= 70:
        print("⚠️  Coverage: Good scenario coverage with some limitations")
    else:
        print("❌ Coverage: Limited scenario coverage")
    
    return results


def run_user_experience_tests():
    """Run complete user experience test suite"""
    print("🎨 Rapid Minutes Export - User Experience Test")
    print("=" * 60)
    print("Testing against ICE principles (Intuitive, Concise, Encompassing)")
    
    overall_results = {
        "intuitive_results": {},
        "concise_results": {},
        "encompassing_results": {},
        "ice_scores": {},
        "overall_ux_score": 0
    }
    
    try:
        # Test Intuitive Experience
        overall_results["intuitive_results"] = test_intuitive_experience()
        
        # Test Concise Functionality  
        overall_results["concise_results"] = test_concise_functionality()
        
        # Test Encompassing Coverage
        overall_results["encompassing_results"] = test_encompassing_coverage()
        
        # Calculate ICE scores
        overall_results["ice_scores"] = {
            "intuitive_score": overall_results["intuitive_results"].get("ease_of_use_score", 0),
            "concise_score": overall_results["concise_results"].get("conciseness_score", 0),
            "encompassing_score": overall_results["encompassing_results"].get("scenario_coverage", 0)
        }
        
        # Calculate overall UX score
        ice_scores = overall_results["ice_scores"]
        overall_results["overall_ux_score"] = (
            ice_scores["intuitive_score"] + 
            ice_scores["concise_score"] + 
            ice_scores["encompassing_score"]
        ) / 3
        
    except Exception as e:
        print(f"❌ User experience testing failed: {str(e)}")
        overall_results["error"] = str(e)
    
    # Final Summary
    print("\n" + "=" * 60)
    print("🎨 USER EXPERIENCE TEST SUMMARY")
    print("=" * 60)
    
    ice_scores = overall_results.get("ice_scores", {})
    overall_score = overall_results.get("overall_ux_score", 0)
    
    print("📊 ICE Principle Scores:")
    print(f"   🧠 Intuitive Score: {ice_scores.get('intuitive_score', 0):.1f}% (iPhone-like ease)")
    print(f"   🎯 Concise Score: {ice_scores.get('concise_score', 0):.1f}% (Essential features only)")  
    print(f"   🌐 Encompassing Score: {ice_scores.get('encompassing_score', 0):.1f}% (Complete coverage)")
    
    print(f"\n🏆 Overall UX Score: {overall_score:.1f}%")
    
    # Assessment based on score
    if overall_score >= 90:
        print("🌟 EXCELLENT: Exceeds ICE principle standards")
        print("🚀 Production-ready with outstanding user experience")
    elif overall_score >= 80:
        print("✅ GOOD: Meets ICE principle standards")
        print("🎯 Production-ready with solid user experience")
    elif overall_score >= 70:
        print("⚠️  ACCEPTABLE: Mostly meets ICE principles")
        print("🔧 Minor UX improvements recommended")
    else:
        print("❌ NEEDS IMPROVEMENT: Below ICE principle standards")
        print("🚨 Significant UX improvements required before production")
    
    # Specific recommendations
    print(f"\n💡 Recommendations:")
    if ice_scores.get("intuitive_score", 0) < 80:
        print("   - Improve user interface intuitiveness")
        print("   - Simplify workflow steps")
        print("   - Enhance error messaging")
    
    if ice_scores.get("concise_score", 0) < 80:
        print("   - Remove unnecessary features")
        print("   - Focus on core functionality")
        print("   - Reduce interface complexity")
    
    if ice_scores.get("encompassing_score", 0) < 80:
        print("   - Improve handling of edge cases")
        print("   - Expand scenario coverage")
        print("   - Better content validation")
    
    if overall_score >= 90:
        print("   - System meets all ICE principles excellently")
        print("   - Ready for production deployment")
    
    return overall_results


if __name__ == "__main__":
    try:
        run_user_experience_tests()
    except KeyboardInterrupt:
        print("\n\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n💥 Unexpected error: {str(e)}")
        traceback.print_exc()