import logging
import requests
import json
from typing import Dict, Any, Optional
from rapid_minutes.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class OllamaClient:
    def __init__(self):
        self.host = settings.ollama_host
        self.model = settings.ollama_model
        self.session = requests.Session()
        
    def health_check(self) -> bool:
        try:
            response = self.session.get(f"{self.host}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False
    
    def list_models(self) -> Dict[str, Any]:
        try:
            response = self.session.get(f"{self.host}/api/tags")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return {"models": []}
    
    def generate_response(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "top_p": 0.9,
                    "num_predict": 2048
                }
            }
            
            if system_prompt:
                payload["system"] = system_prompt
            
            response = self.session.post(
                f"{self.host}/api/generate",
                json=payload,
                timeout=settings.max_processing_time
            )
            response.raise_for_status()
            
            result = response.json()
            return result.get("response", "")
            
        except requests.exceptions.Timeout:
            logger.error("Ollama request timed out")
            raise Exception("AI processing timed out. Please try again.")
        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama request failed: {e}")
            raise Exception("AI service unavailable. Please check Ollama connection.")
        except Exception as e:
            logger.error(f"Unexpected error in generate_response: {e}")
            raise Exception("Failed to process with AI. Please try again.")
    
    def chat_completion(self, messages: list) -> str:
        try:
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "top_p": 0.9,
                    "num_predict": 2048
                }
            }
            
            response = self.session.post(
                f"{self.host}/api/chat",
                json=payload,
                timeout=settings.max_processing_time
            )
            response.raise_for_status()
            
            result = response.json()
            return result.get("message", {}).get("content", "")
            
        except requests.exceptions.Timeout:
            logger.error("Ollama chat request timed out")
            raise Exception("AI processing timed out. Please try again.")
        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama chat request failed: {e}")
            raise Exception("AI service unavailable. Please check Ollama connection.")
        except Exception as e:
            logger.error(f"Unexpected error in chat_completion: {e}")
            raise Exception("Failed to process with AI. Please try again.")
    
    def extract_meeting_data(self, text: str) -> Dict[str, Any]:
        system_prompt = """You are an expert meeting minutes assistant specializing in structured data extraction. Your task is to analyze meeting transcripts and extract information with maximum accuracy and completeness.

CRITICAL INSTRUCTIONS:
1. Return ONLY valid JSON format - no additional text, explanations, or markdown
2. Extract information precisely from the text provided
3. Use context clues and inference for reasonable completions
4. Maintain professional language and formatting
5. Prioritize actionable items and clear decisions

REQUIRED JSON STRUCTURE:
{
    "meeting_title": "string - Infer from context if not explicitly stated",
    "date": "string - Format: YYYY-MM-DD if found, otherwise empty",
    "time": "string - Format: HH:MM if found, otherwise empty", 
    "location": "string - Physical or virtual location if mentioned",
    "attendees": ["string array - Names, roles, or departments mentioned"],
    "key_topics": ["string array - Main discussion points, max 8 items"],
    "decisions": ["string array - Concrete decisions made, resolutions passed"],
    "action_items": [
        {
            "task": "string - Clear, actionable task description",
            "assignee": "string - Person/team responsible",
            "deadline": "string - Deadline if mentioned, otherwise empty",
            "priority": "string - high/medium/low if indicated, otherwise medium"
        }
    ],
    "follow_up_items": ["string array - Items requiring future attention"],
    "next_meeting": "string - Next meeting details if mentioned",
    "meeting_type": "string - Type of meeting (e.g., status, planning, review)",
    "duration": "string - Meeting duration if mentioned",
    "summary": "string - Brief 1-2 sentence meeting summary"
}

EXTRACTION GUIDELINES:
- For meeting_title: If not stated, infer from main topics (e.g., "Project Status Meeting", "Budget Review")
- For attendees: Include names, titles, or departments mentioned in discussion
- For key_topics: Focus on substantial discussion points, not minor comments
- For decisions: Only include definitive resolutions, not ongoing discussions
- For action_items: Must be specific, assignable tasks with clear outcomes
- For meeting_type: Classify based on content (status, planning, decision, review, etc.)

QUALITY REQUIREMENTS:
- Minimum 90% accuracy in field extraction
- Professional, concise language
- Logical categorization of information
- Complete JSON structure with all fields present"""

        user_prompt = f"Please extract meeting information from this text:\n\n{text}"
        
        try:
            response = self.generate_response(user_prompt, system_prompt)
            
            # Try to parse as JSON
            import json
            try:
                data = json.loads(response)
                # Validate and normalize all fields
                validated_data = self._validate_and_normalize_data(data)
                return validated_data
            except json.JSONDecodeError:
                logger.warning("Failed to parse JSON response, using fallback")
                return self._fallback_extraction(text)
                
        except Exception as e:
            logger.error(f"Failed to extract meeting data: {e}")
            return self._fallback_extraction(text)
    
    def _validate_and_normalize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize extracted meeting data according to SESE principles"""
        default_structure = {
            "meeting_title": "General Meeting",
            "date": "",
            "time": "",
            "location": "",
            "attendees": [],
            "key_topics": [],
            "decisions": [],
            "action_items": [],
            "follow_up_items": [],
            "next_meeting": "",
            "meeting_type": "general",
            "duration": "",
            "summary": ""
        }
        
        # Ensure all required fields exist
        for key, default_value in default_structure.items():
            if key not in data:
                data[key] = default_value
        
        # Validate and clean string fields
        string_fields = ["meeting_title", "date", "time", "location", "next_meeting", "meeting_type", "duration", "summary"]
        for field in string_fields:
            if not isinstance(data[field], str):
                data[field] = str(data[field]) if data[field] else ""
            data[field] = data[field].strip()
        
        # Validate and clean array fields
        array_fields = ["attendees", "key_topics", "decisions", "follow_up_items"]
        for field in array_fields:
            if not isinstance(data[field], list):
                data[field] = []
            # Clean and validate each item in arrays
            data[field] = [str(item).strip() for item in data[field] if item and str(item).strip()]
        
        # Special validation for action_items
        if not isinstance(data["action_items"], list):
            data["action_items"] = []
        
        validated_actions = []
        for item in data["action_items"]:
            if isinstance(item, dict):
                action_item = {
                    "task": str(item.get("task", "")).strip(),
                    "assignee": str(item.get("assignee", "")).strip(),
                    "deadline": str(item.get("deadline", "")).strip(),
                    "priority": str(item.get("priority", "medium")).lower().strip()
                }
                if action_item["task"]:  # Only add if task is not empty
                    if action_item["priority"] not in ["high", "medium", "low"]:
                        action_item["priority"] = "medium"
                    validated_actions.append(action_item)
        
        data["action_items"] = validated_actions
        
        # Quality check - ensure meeting has some meaningful content
        total_content_items = len(data["key_topics"]) + len(data["decisions"]) + len(data["action_items"])
        if total_content_items == 0:
            # Generate basic content from text if AI extraction failed
            logger.warning("Low content extraction detected, enhancing data")
            data = self._enhance_minimal_data(data)
        
        return data
    
    def _enhance_minimal_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance data when AI extraction yields minimal results"""
        if not data["meeting_title"] or data["meeting_title"] == "General Meeting":
            data["meeting_title"] = "Meeting Minutes"
        
        if not data["summary"]:
            data["summary"] = "Meeting discussion and action items review."
        
        if not data["meeting_type"]:
            data["meeting_type"] = "general"
        
        return data

    def _fallback_extraction(self, text: str) -> Dict[str, Any]:
        """Fallback method for basic text processing when AI fails - implements ICE principle for reliability"""
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        # Basic extraction using text patterns
        title = "General Meeting"
        topics = []
        
        # Try to identify meeting topics from content
        for line in lines[:8]:  # Check first 8 lines for topics
            if len(line) > 10 and not any(char.isdigit() for char in line[:5]):
                topics.append(line[:100])  # Limit topic length
        
        return {
            "meeting_title": title,
            "date": "",
            "time": "",
            "location": "",
            "attendees": [],
            "key_topics": topics[:5],  # Limit to top 5 topics
            "decisions": [],
            "action_items": [],
            "follow_up_items": [],
            "next_meeting": "",
            "meeting_type": "general",
            "duration": "",
            "summary": f"Meeting with {len(topics)} discussion topics identified."
        }