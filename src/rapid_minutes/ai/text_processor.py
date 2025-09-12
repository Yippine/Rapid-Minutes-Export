import re
import logging
from typing import List, Dict, Any

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