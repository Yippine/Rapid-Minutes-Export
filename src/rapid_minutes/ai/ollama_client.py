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
        system_prompt = """You are a professional meeting minutes assistant. Extract structured information from meeting transcripts and return it as JSON format.

Always return a JSON object with these exact fields:
{
    "meeting_title": "string - meeting title or subject",
    "date": "string - meeting date if mentioned, otherwise empty string",
    "time": "string - meeting time if mentioned, otherwise empty string", 
    "location": "string - meeting location if mentioned, otherwise empty string",
    "attendees": ["array", "of", "attendee", "names"],
    "key_topics": ["array", "of", "main", "discussion", "topics"],
    "decisions": ["array", "of", "decisions", "made"],
    "action_items": [
        {
            "task": "description of task",
            "assignee": "person responsible",
            "deadline": "deadline if mentioned"
        }
    ],
    "next_meeting": "next meeting info if mentioned, otherwise empty string"
}

Be precise and extract only information that is clearly stated in the text. If information is not available, use empty strings or empty arrays."""

        user_prompt = f"Please extract meeting information from this text:\n\n{text}"
        
        try:
            response = self.generate_response(user_prompt, system_prompt)
            
            # Try to parse as JSON
            import json
            try:
                data = json.loads(response)
                # Validate required fields
                required_fields = ["meeting_title", "attendees", "key_topics", "decisions", "action_items"]
                for field in required_fields:
                    if field not in data:
                        data[field] = [] if field != "meeting_title" else "General Meeting"
                return data
            except json.JSONDecodeError:
                logger.warning("Failed to parse JSON response, using fallback")
                return self._fallback_extraction(text)
                
        except Exception as e:
            logger.error(f"Failed to extract meeting data: {e}")
            return self._fallback_extraction(text)
    
    def _fallback_extraction(self, text: str) -> Dict[str, Any]:
        """Fallback method for basic text processing when AI fails"""
        lines = text.split('\n')
        return {
            "meeting_title": "General Meeting",
            "date": "",
            "time": "",
            "location": "",
            "attendees": [],
            "key_topics": [line.strip() for line in lines[:3] if line.strip()],
            "decisions": [],
            "action_items": [],
            "next_meeting": ""
        }