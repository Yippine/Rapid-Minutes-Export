"""
Validation Utilities
Comprehensive validation functions for files, data, and system inputs
Implements MECE principle - complete validation coverage without overlap
"""

import re
import magic
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime
import email_validator
import validators


class FileValidator:
    """File validation utilities"""
    
    # Supported file types and their specifications
    SUPPORTED_TYPES = {
        'text/plain': {
            'extensions': ['.txt', '.text'],
            'max_size': 10 * 1024 * 1024,  # 10MB
            'description': 'Plain text files'
        },
        'application/pdf': {
            'extensions': ['.pdf'],
            'max_size': 10 * 1024 * 1024,  # 10MB
            'description': 'PDF documents'
        }
    }
    
    @staticmethod
    def validate_file_type(file_data: bytes, filename: str) -> Tuple[bool, str]:
        """
        Validate file type based on content and extension
        
        Returns:
            (is_valid, mime_type_or_error)
        """
        try:
            # Detect MIME type from content
            mime_type = magic.from_buffer(file_data, mime=True)
            
            # Check if MIME type is supported
            if mime_type not in FileValidator.SUPPORTED_TYPES:
                return False, f"Unsupported file type: {mime_type}"
            
            # Check file extension
            file_ext = Path(filename).suffix.lower()
            allowed_extensions = FileValidator.SUPPORTED_TYPES[mime_type]['extensions']
            
            if file_ext not in allowed_extensions:
                return False, f"File extension {file_ext} doesn't match content type {mime_type}"
            
            return True, mime_type
            
        except Exception as e:
            return False, f"File type validation error: {str(e)}"
    
    @staticmethod
    def validate_file_size(file_data: bytes, mime_type: str) -> Tuple[bool, str]:
        """Validate file size against limits"""
        file_size = len(file_data)
        
        if file_size == 0:
            return False, "Empty file not allowed"
        
        if mime_type in FileValidator.SUPPORTED_TYPES:
            max_size = FileValidator.SUPPORTED_TYPES[mime_type]['max_size']
            if file_size > max_size:
                return False, f"File too large: {file_size} bytes > {max_size} bytes"
        
        return True, "File size valid"
    
    @staticmethod
    def validate_filename(filename: str) -> Tuple[bool, str]:
        """Validate filename for security and compatibility"""
        if not filename or len(filename.strip()) == 0:
            return False, "Filename cannot be empty"
        
        # Check length
        if len(filename) > 255:
            return False, "Filename too long (max 255 characters)"
        
        # Check for dangerous characters
        dangerous_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|', '\0']
        if any(char in filename for char in dangerous_chars):
            return False, f"Filename contains prohibited characters: {dangerous_chars}"
        
        # Check for reserved names (Windows)
        reserved_names = [
            'CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4', 'COM5',
            'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2', 'LPT3', 'LPT4',
            'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
        ]
        
        name_without_ext = Path(filename).stem.upper()
        if name_without_ext in reserved_names:
            return False, f"Filename uses reserved name: {name_without_ext}"
        
        return True, "Filename valid"
    
    @staticmethod
    def validate_text_content(content: str) -> Tuple[bool, str, Dict[str, Any]]:
        """Validate text content for meeting processing"""
        if not content or len(content.strip()) == 0:
            return False, "Content is empty", {}
        
        # Basic content metrics
        char_count = len(content)
        word_count = len(content.split())
        line_count = len(content.splitlines())
        
        # Minimum content requirements
        if word_count < 10:
            return False, "Content too short (minimum 10 words)", {}
        
        if char_count > 1_000_000:  # 1MB of text
            return False, "Content too large (maximum 1MB of text)", {}
        
        # Check for potential meeting content indicators
        meeting_indicators = [
            'meeting', 'agenda', 'attendees', 'discussion', 'action', 'decision',
            'minutes', 'notes', 'participants', 'topics', 'follow-up'
        ]
        
        content_lower = content.lower()
        indicator_count = sum(1 for indicator in meeting_indicators if indicator in content_lower)
        
        quality_metrics = {
            'char_count': char_count,
            'word_count': word_count,
            'line_count': line_count,
            'meeting_indicators': indicator_count,
            'avg_word_length': sum(len(word) for word in content.split()) / word_count,
            'avg_line_length': char_count / line_count if line_count > 0 else 0
        }
        
        return True, "Content valid", quality_metrics


class DataValidator:
    """Data structure validation utilities"""
    
    @staticmethod
    def validate_email(email: str) -> Tuple[bool, str]:
        """Validate email address"""
        try:
            email_validator.validate_email(email)
            return True, "Valid email"
        except email_validator.EmailNotValidError as e:
            return False, str(e)
    
    @staticmethod
    def validate_url(url: str) -> Tuple[bool, str]:
        """Validate URL"""
        if validators.url(url):
            return True, "Valid URL"
        else:
            return False, "Invalid URL format"
    
    @staticmethod
    def validate_date_string(date_str: str) -> Tuple[bool, str, Optional[datetime]]:
        """Validate and parse date string"""
        import dateparser
        
        try:
            parsed_date = dateparser.parse(date_str)
            if parsed_date:
                return True, "Valid date", parsed_date
            else:
                return False, "Could not parse date", None
        except Exception as e:
            return False, f"Date parsing error: {str(e)}", None
    
    @staticmethod
    def validate_phone_number(phone: str) -> Tuple[bool, str]:
        """Validate phone number format"""
        # Remove common formatting characters
        cleaned_phone = re.sub(r'[\s\-\(\)\+\.]', '', phone)
        
        # Check if it's all digits (with optional country code)
        if not cleaned_phone.isdigit():
            return False, "Phone number must contain only digits and formatting characters"
        
        # Check length (7-15 digits is reasonable range)
        if len(cleaned_phone) < 7 or len(cleaned_phone) > 15:
            return False, "Phone number length must be between 7 and 15 digits"
        
        return True, "Valid phone number format"
    
    @staticmethod
    def validate_meeting_data(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate meeting minutes data structure"""
        errors = []
        
        # Check required top-level keys
        required_keys = ['basic_info', 'attendees', 'agenda', 'action_items', 'decisions', 'key_outcomes']
        for key in required_keys:
            if key not in data:
                errors.append(f"Missing required field: {key}")
        
        # Validate basic info
        if 'basic_info' in data and isinstance(data['basic_info'], dict):
            basic_info = data['basic_info']
            if not basic_info.get('title') and not basic_info.get('meeting_type'):
                errors.append("Basic info must have either title or meeting_type")
        
        # Validate attendees
        if 'attendees' in data and isinstance(data['attendees'], list):
            for i, attendee in enumerate(data['attendees']):
                if not isinstance(attendee, dict):
                    errors.append(f"Attendee {i} must be an object")
                elif not attendee.get('name'):
                    errors.append(f"Attendee {i} must have a name")
        
        # Validate action items
        if 'action_items' in data and isinstance(data['action_items'], list):
            for i, item in enumerate(data['action_items']):
                if not isinstance(item, dict):
                    errors.append(f"Action item {i} must be an object")
                elif not item.get('task'):
                    errors.append(f"Action item {i} must have a task description")
        
        # Validate decisions
        if 'decisions' in data and isinstance(data['decisions'], list):
            for i, decision in enumerate(data['decisions']):
                if not isinstance(decision, dict):
                    errors.append(f"Decision {i} must be an object")
                elif not decision.get('decision'):
                    errors.append(f"Decision {i} must have a decision description")
        
        return len(errors) == 0, errors


class SystemValidator:
    """System and configuration validation"""
    
    @staticmethod
    def validate_config_values(config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate system configuration values"""
        errors = []
        
        # Check required configuration
        required_configs = [
            'data_dir', 'temp_dir', 'max_file_size_mb',
            'ollama_url', 'ollama_model'
        ]
        
        for key in required_configs:
            if key not in config or config[key] is None:
                errors.append(f"Missing required configuration: {key}")
        
        # Validate specific values
        if 'max_file_size_mb' in config:
            max_size = config['max_file_size_mb']
            if not isinstance(max_size, (int, float)) or max_size <= 0:
                errors.append("max_file_size_mb must be a positive number")
            elif max_size > 100:  # Reasonable limit
                errors.append("max_file_size_mb seems too large (>100MB)")
        
        if 'ollama_url' in config:
            url = config['ollama_url']
            if not validators.url(url):
                errors.append(f"Invalid Ollama URL: {url}")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_directory_permissions(directory: str) -> Tuple[bool, str]:
        """Validate directory exists and is writable"""
        path = Path(directory)
        
        try:
            # Check if directory exists
            if not path.exists():
                # Try to create it
                path.mkdir(parents=True, exist_ok=True)
            
            # Check if it's actually a directory
            if not path.is_dir():
                return False, f"Path exists but is not a directory: {directory}"
            
            # Test write permissions
            test_file = path / '.write_test'
            try:
                test_file.write_text('test')
                test_file.unlink()
                return True, "Directory is writable"
            except PermissionError:
                return False, f"No write permission for directory: {directory}"
            
        except Exception as e:
            return False, f"Directory validation error: {str(e)}"
    
    @staticmethod
    def validate_disk_space(directory: str, required_mb: int) -> Tuple[bool, str]:
        """Validate available disk space"""
        import shutil
        
        try:
            total, used, free = shutil.disk_usage(directory)
            free_mb = free / (1024 * 1024)
            
            if free_mb < required_mb:
                return False, f"Insufficient disk space: {free_mb:.1f}MB available, {required_mb}MB required"
            
            return True, f"Sufficient disk space: {free_mb:.1f}MB available"
            
        except Exception as e:
            return False, f"Disk space check error: {str(e)}"


class InputSanitizer:
    """Input sanitization utilities"""
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename by removing/replacing dangerous characters"""
        if not filename:
            return "unnamed_file"
        
        # Replace dangerous characters with underscores
        dangerous_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|', '\0']
        sanitized = filename
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, '_')
        
        # Trim and ensure it's not empty
        sanitized = sanitized.strip()
        if not sanitized:
            sanitized = "unnamed_file"
        
        # Limit length
        if len(sanitized) > 200:
            name_part = Path(sanitized).stem[:190]
            ext_part = Path(sanitized).suffix[:10]
            sanitized = f"{name_part}{ext_part}"
        
        return sanitized
    
    @staticmethod
    def sanitize_text_input(text: str, max_length: Optional[int] = None) -> str:
        """Sanitize text input"""
        if not text:
            return ""
        
        # Remove null bytes and control characters
        sanitized = ''.join(char for char in text if ord(char) >= 32 or char in ['\n', '\t', '\r'])
        
        # Limit length if specified
        if max_length and len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        
        return sanitized.strip()
    
    @staticmethod
    def escape_html(text: str) -> str:
        """Escape HTML characters"""
        html_escape_table = {
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#x27;",
        }
        
        return "".join(html_escape_table.get(c, c) for c in text)


class SecurityValidator:
    """Security validation utilities"""
    
    @staticmethod
    def validate_no_script_injection(text: str) -> Tuple[bool, str]:
        """Check for potential script injection"""
        dangerous_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'vbscript:',
            r'onload\s*=',
            r'onerror\s*=',
            r'onclick\s*=',
            r'<iframe[^>]*>',
            r'<object[^>]*>',
            r'<embed[^>]*>',
        ]
        
        text_lower = text.lower()
        for pattern in dangerous_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return False, f"Potential script injection detected: {pattern}"
        
        return True, "No script injection detected"
    
    @staticmethod
    def validate_no_path_traversal(path: str) -> Tuple[bool, str]:
        """Check for path traversal attempts"""
        dangerous_patterns = [
            '..',
            '~/',
            '/etc/',
            '/proc/',
            '/sys/',
            '\\windows\\',
            '\\system32\\'
        ]
        
        path_lower = path.lower()
        for pattern in dangerous_patterns:
            if pattern in path_lower:
                return False, f"Potential path traversal detected: {pattern}"
        
        return True, "No path traversal detected"