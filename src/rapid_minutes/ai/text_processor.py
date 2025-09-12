import re
import logging
import json
from typing import List, Dict, Any, Optional, Union
from datetime import datetime

logger = logging.getLogger(__name__)


class TextProcessor:
    def __init__(self):
        self.common_noise_patterns = [
            r'\[音樂\]',
            r'\[雜音\]', 
            r'\[笑聲\]',
            r'\[掌聲\]',
            r'\[inaudible\]',
            r'\[unclear\]',
            r'嗯+',
            r'呃+',
            r'啊+',
            r'那個+',
            r'就是說+'
        ]
    
    def clean_text(self, text: str) -> str:
        if not text or not isinstance(text, str):
            return ""
        
        try:
            # Remove common noise patterns
            cleaned = text
            for pattern in self.common_noise_patterns:
                cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
            
            # Remove multiple spaces and normalize whitespace
            cleaned = re.sub(r'\s+', ' ', cleaned)
            
            # Remove empty lines and normalize line breaks
            lines = [line.strip() for line in cleaned.split('\n') if line.strip()]
            cleaned = '\n'.join(lines)
            
            # Remove speaker labels if they exist (e.g., "Speaker 1:" or "張三:")
            cleaned = re.sub(r'^[^:]+:\s*', '', cleaned, flags=re.MULTILINE)
            
            # Remove timestamps if they exist (e.g., "[00:05:30]")
            cleaned = re.sub(r'\[\d{2}:\d{2}:\d{2}\]', '', cleaned)
            
            # Remove excessive punctuation
            cleaned = re.sub(r'[.]{3,}', '...', cleaned)
            cleaned = re.sub(r'[?]{2,}', '?', cleaned)
            cleaned = re.sub(r'[!]{2,}', '!', cleaned)
            
            return cleaned.strip()
            
        except Exception as e:
            logger.error(f"Error cleaning text: {e}")
            return text
    
    def extract_sentences(self, text: str) -> List[str]:
        if not text:
            return []
        
        try:
            # Split by common sentence endings
            sentences = re.split(r'[.!?。！？]\s*', text)
            
            # Clean and filter sentences
            cleaned_sentences = []
            for sentence in sentences:
                cleaned = sentence.strip()
                if len(cleaned) > 5:  # Only keep sentences with substantial content
                    cleaned_sentences.append(cleaned)
            
            return cleaned_sentences
            
        except Exception as e:
            logger.error(f"Error extracting sentences: {e}")
            return [text]
    
    def preprocess_for_ai(self, text: str) -> str:
        if not text:
            return ""
        
        try:
            # Clean the text
            cleaned = self.clean_text(text)
            
            # Add structure hints for better AI processing
            lines = cleaned.split('\n')
            processed_lines = []
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Add context markers for better AI understanding
                if any(keyword in line.lower() for keyword in ['會議', '討論', '決定', '決議']):
                    processed_lines.append(f"[會議內容] {line}")
                elif any(keyword in line.lower() for keyword in ['行動', '任務', '負責', '執行']):
                    processed_lines.append(f"[行動事項] {line}")
                elif any(keyword in line.lower() for keyword in ['下次', '下個', '未來', '計畫']):
                    processed_lines.append(f"[後續計畫] {line}")
                else:
                    processed_lines.append(line)
            
            return '\n'.join(processed_lines)
            
        except Exception as e:
            logger.error(f"Error preprocessing text for AI: {e}")
            return text
    
    def validate_text_quality(self, text: str) -> Dict[str, Any]:
        if not text:
            return {"valid": False, "reason": "Empty text", "score": 0}
        
        try:
            word_count = len(text.split())
            char_count = len(text)
            line_count = len([line for line in text.split('\n') if line.strip()])
            
            # Quality checks
            quality_score = 100
            issues = []
            
            if word_count < 10:
                quality_score -= 30
                issues.append("Too few words")
            
            if char_count < 50:
                quality_score -= 20
                issues.append("Too short")
            
            if line_count < 2:
                quality_score -= 15
                issues.append("Too few lines")
            
            # Check for excessive repetition
            words = text.lower().split()
            unique_words = set(words)
            if len(words) > 0 and len(unique_words) / len(words) < 0.3:
                quality_score -= 25
                issues.append("Excessive repetition")
            
            # Check for meaningful content
            meaningful_chars = len(re.sub(r'[^\w\s]', '', text))
            if meaningful_chars / char_count < 0.5:
                quality_score -= 20
                issues.append("Too much noise")
            
            return {
                "valid": quality_score >= 50,
                "score": max(0, quality_score),
                "word_count": word_count,
                "char_count": char_count,
                "line_count": line_count,
                "issues": issues
            }
            
        except Exception as e:
            logger.error(f"Error validating text quality: {e}")
            return {"valid": False, "reason": f"Validation error: {e}", "score": 0}
    
    def segment_long_text(self, text: str, max_length: int = 4000) -> List[str]:
        if not text or len(text) <= max_length:
            return [text] if text else []
        
        try:
            segments = []
            sentences = self.extract_sentences(text)
            current_segment = ""
            
            for sentence in sentences:
                if len(current_segment + sentence) <= max_length:
                    current_segment += sentence + ". "
                else:
                    if current_segment:
                        segments.append(current_segment.strip())
                    current_segment = sentence + ". "
            
            if current_segment:
                segments.append(current_segment.strip())
            
            return segments
            
        except Exception as e:
            logger.error(f"Error segmenting text: {e}")
            # Fallback: simple character-based splitting
            segments = []
            for i in range(0, len(text), max_length):
                segments.append(text[i:i + max_length])
            return segments
    
    def validate_extracted_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Comprehensive validation of extracted meeting data according to SESE principles"""
        validation_result = {
            "is_valid": True,
            "confidence_score": 100.0,
            "quality_metrics": {},
            "issues": [],
            "suggestions": []
        }
        
        try:
            # Structural validation
            structural_score = self._validate_data_structure(data)
            validation_result["quality_metrics"]["structural_score"] = structural_score
            
            # Content validation
            content_score = self._validate_content_quality(data)
            validation_result["quality_metrics"]["content_score"] = content_score
            
            # Completeness validation
            completeness_score = self._validate_data_completeness(data)
            validation_result["quality_metrics"]["completeness_score"] = completeness_score
            
            # Calculate overall confidence
            overall_confidence = (structural_score + content_score + completeness_score) / 3
            validation_result["confidence_score"] = round(overall_confidence, 2)
            
            # Determine if data meets quality threshold
            validation_result["is_valid"] = overall_confidence >= 70.0
            
            # Generate improvement suggestions
            if overall_confidence < 90.0:
                validation_result["suggestions"] = self._generate_improvement_suggestions(data, validation_result["quality_metrics"])
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Error during data validation: {e}")
            return {
                "is_valid": False,
                "confidence_score": 0.0,
                "quality_metrics": {},
                "issues": [f"Validation error: {str(e)}"],
                "suggestions": ["Please check the data format and try again."]
            }
    
    def _validate_data_structure(self, data: Dict[str, Any]) -> float:
        """Validate the structural integrity of extracted data"""
        required_fields = [
            "meeting_title", "attendees", "key_topics", "decisions", 
            "action_items", "meeting_type", "summary"
        ]
        
        score = 100.0
        
        # Check required fields exist
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            score -= len(missing_fields) * 10
            logger.warning(f"Missing required fields: {missing_fields}")
        
        # Check data types
        type_validations = {
            "meeting_title": str,
            "date": str,
            "time": str,
            "location": str,
            "attendees": list,
            "key_topics": list,
            "decisions": list,
            "action_items": list,
            "next_meeting": str,
            "meeting_type": str,
            "summary": str
        }
        
        for field, expected_type in type_validations.items():
            if field in data and not isinstance(data[field], expected_type):
                score -= 5
                logger.warning(f"Field {field} has incorrect type: expected {expected_type}, got {type(data[field])}")
        
        # Validate action items structure
        if "action_items" in data and isinstance(data["action_items"], list):
            for item in data["action_items"]:
                if not isinstance(item, dict):
                    score -= 5
                    continue
                required_action_fields = ["task", "assignee"]
                for field in required_action_fields:
                    if field not in item or not item[field]:
                        score -= 3
        
        return max(0.0, score)
    
    def _validate_content_quality(self, data: Dict[str, Any]) -> float:
        """Validate the quality and meaningfulness of extracted content"""
        score = 100.0
        
        # Check meeting title quality
        if "meeting_title" in data:
            title = data["meeting_title"]
            if not title or len(title) < 3:
                score -= 10
            elif title.lower() in ["meeting", "general meeting", "untitled"]:
                score -= 5
        
        # Check summary quality
        if "summary" in data:
            summary = data["summary"]
            if not summary or len(summary) < 10:
                score -= 15
            elif len(summary.split()) < 5:
                score -= 10
        
        # Check key topics quality
        if "key_topics" in data and isinstance(data["key_topics"], list):
            if len(data["key_topics"]) == 0:
                score -= 20
            else:
                # Check for meaningful topics
                meaningful_topics = [topic for topic in data["key_topics"] if len(topic.split()) >= 2]
                if len(meaningful_topics) < len(data["key_topics"]) * 0.7:
                    score -= 10
        
        # Check decisions quality
        if "decisions" in data and isinstance(data["decisions"], list):
            if len(data["decisions"]) == 0:
                score -= 5  # Decisions are not always required
            else:
                # Check for actionable decisions
                actionable_decisions = [d for d in data["decisions"] if len(d.split()) >= 3]
                if len(actionable_decisions) < len(data["decisions"]) * 0.8:
                    score -= 5
        
        # Check action items quality
        if "action_items" in data and isinstance(data["action_items"], list):
            total_actions = len(data["action_items"])
            if total_actions == 0:
                score -= 10  # Meetings should typically have some actions
            else:
                complete_actions = 0
                for action in data["action_items"]:
                    if isinstance(action, dict):
                        if action.get("task") and action.get("assignee"):
                            complete_actions += 1
                
                completion_ratio = complete_actions / total_actions if total_actions > 0 else 0
                if completion_ratio < 0.8:
                    score -= 15
        
        return max(0.0, score)
    
    def _validate_data_completeness(self, data: Dict[str, Any]) -> float:
        """Validate the completeness of extracted information"""
        score = 100.0
        
        # Essential content areas
        content_areas = {
            "attendees": 10,      # Nice to have
            "key_topics": 25,     # Very important
            "decisions": 15,      # Important
            "action_items": 20,   # Very important
            "meeting_type": 5,    # Nice to have
            "summary": 15,        # Important
            "next_meeting": 5,    # Nice to have
            "location": 5         # Nice to have
        }
        
        for area, weight in content_areas.items():
            if area not in data:
                score -= weight
                continue
                
            value = data[area]
            if isinstance(value, list) and len(value) == 0:
                score -= weight * 0.8
            elif isinstance(value, str) and not value.strip():
                score -= weight * 0.8
        
        return max(0.0, score)
    
    def _generate_improvement_suggestions(self, data: Dict[str, Any], metrics: Dict[str, float]) -> List[str]:
        """Generate actionable suggestions for improving data quality"""
        suggestions = []
        
        if metrics.get("structural_score", 100) < 90:
            suggestions.append("Check that all required fields are present and properly formatted.")
        
        if metrics.get("content_score", 100) < 80:
            suggestions.append("Improve content quality: ensure meeting title is descriptive, summary is comprehensive, and topics are meaningful.")
        
        if metrics.get("completeness_score", 100) < 70:
            suggestions.append("Add more detailed information: attendees, specific decisions, and actionable items with assignees.")
        
        # Specific suggestions based on data content
        if "key_topics" in data and len(data.get("key_topics", [])) < 2:
            suggestions.append("Include more key discussion topics to better capture meeting content.")
        
        if "action_items" in data and len(data.get("action_items", [])) == 0:
            suggestions.append("Add action items with clear tasks and responsible parties.")
        
        if "summary" in data and len(data.get("summary", "").split()) < 10:
            suggestions.append("Provide a more detailed meeting summary.")
        
        return suggestions
    
    def extract_meeting_insights(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract deeper insights from validated meeting data using AI principles"""
        insights = {
            "meeting_effectiveness": self._analyze_meeting_effectiveness(data),
            "action_priority_analysis": self._analyze_action_priorities(data),
            "participation_analysis": self._analyze_participation(data),
            "follow_up_recommendations": self._generate_follow_up_recommendations(data)
        }
        
        return insights
    
    def _analyze_meeting_effectiveness(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze meeting effectiveness based on outcomes"""
        decisions_count = len(data.get("decisions", []))
        actions_count = len(data.get("action_items", []))
        topics_count = len(data.get("key_topics", []))
        
        effectiveness_score = 0
        if decisions_count > 0:
            effectiveness_score += 30
        if actions_count > 0:
            effectiveness_score += 40
        if topics_count >= 3:
            effectiveness_score += 30
        
        return {
            "score": effectiveness_score,
            "decisions_made": decisions_count,
            "actions_assigned": actions_count,
            "topics_discussed": topics_count,
            "assessment": "Highly Effective" if effectiveness_score >= 80 else
                         "Moderately Effective" if effectiveness_score >= 50 else
                         "Needs Improvement"
        }
    
    def _analyze_action_priorities(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze and categorize action item priorities"""
        action_items = data.get("action_items", [])
        priority_distribution = {"high": 0, "medium": 0, "low": 0}
        
        for action in action_items:
            if isinstance(action, dict):
                priority = action.get("priority", "medium").lower()
                if priority in priority_distribution:
                    priority_distribution[priority] += 1
        
        return {
            "total_actions": len(action_items),
            "priority_distribution": priority_distribution,
            "high_priority_ratio": priority_distribution["high"] / len(action_items) if action_items else 0
        }
    
    def _analyze_participation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze meeting participation based on attendees and action assignments"""
        attendees = data.get("attendees", [])
        action_items = data.get("action_items", [])
        
        assignees = set()
        for action in action_items:
            if isinstance(action, dict) and action.get("assignee"):
                assignees.add(action.get("assignee"))
        
        return {
            "total_attendees": len(attendees),
            "active_participants": len(assignees),
            "engagement_ratio": len(assignees) / len(attendees) if attendees else 0
        }
    
    def _generate_follow_up_recommendations(self, data: Dict[str, Any]) -> List[str]:
        """Generate recommendations for follow-up actions"""
        recommendations = []
        
        action_items = data.get("action_items", [])
        if len(action_items) == 0:
            recommendations.append("Consider defining specific action items with clear ownership.")
        
        high_priority_actions = [a for a in action_items if isinstance(a, dict) and a.get("priority") == "high"]
        if len(high_priority_actions) > 0:
            recommendations.append(f"Follow up on {len(high_priority_actions)} high-priority action items within 24-48 hours.")
        
        if data.get("next_meeting"):
            recommendations.append("Send calendar invites for the next meeting mentioned.")
        
        decisions = data.get("decisions", [])
        if len(decisions) > 0:
            recommendations.append("Communicate key decisions to relevant stakeholders not present in the meeting.")
        
        return recommendations