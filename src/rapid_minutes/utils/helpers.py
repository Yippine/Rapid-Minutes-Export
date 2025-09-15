"""
Helper Utilities
Common utility functions for the meeting minutes processing system
Implements 82 Rule principle - essential 20% helper functions for 80% functionality
"""

import asyncio
import logging
import hashlib
import json
import uuid
from typing import Any, Dict, List, Optional, Union, Callable, TypeVar
from datetime import datetime, timedelta
from pathlib import Path
import time
import functools
import os

logger = logging.getLogger(__name__)

T = TypeVar('T')


class DateTimeHelper:
    """Date and time utility functions"""
    
    @staticmethod
    def now_iso() -> str:
        """Get current timestamp in ISO format"""
        return datetime.utcnow().isoformat() + 'Z'
    
    @staticmethod
    def parse_flexible_date(date_str: str) -> Optional[datetime]:
        """Parse date string in various formats"""
        import dateparser
        try:
            return dateparser.parse(date_str)
        except Exception:
            return None
    
    @staticmethod
    def format_duration(seconds: float) -> str:
        """Format duration in human-readable format"""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f}m"
        else:
            hours = seconds / 3600
            return f"{hours:.1f}h"
    
    @staticmethod
    def is_recent(timestamp: datetime, hours: int = 24) -> bool:
        """Check if timestamp is within recent hours"""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        return timestamp > cutoff
    
    @staticmethod
    def get_timezone_offset() -> str:
        """Get current timezone offset string"""
        import time
        offset_seconds = -time.timezone if time.daylight == 0 else -time.altzone
        offset_hours = offset_seconds // 3600
        offset_minutes = (abs(offset_seconds) % 3600) // 60
        sign = '+' if offset_seconds >= 0 else '-'
        return f"{sign}{abs(offset_hours):02d}:{offset_minutes:02d}"


class FileHelper:
    """File system utility functions"""
    
    @staticmethod
    def ensure_directory(path: Union[str, Path]) -> Path:
        """Ensure directory exists, create if necessary"""
        directory = Path(path)
        directory.mkdir(parents=True, exist_ok=True)
        return directory
    
    @staticmethod
    def get_file_size_human(size_bytes: int) -> str:
        """Convert bytes to human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} PB"
    
    @staticmethod
    def calculate_checksum(file_path: str, algorithm: str = 'sha256') -> str:
        """Calculate file checksum"""
        hash_algo = hashlib.new(algorithm)
        
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hash_algo.update(chunk)
        
        return hash_algo.hexdigest()
    
    @staticmethod
    async def async_read_file(file_path: str) -> bytes:
        """Asynchronously read file content"""
        import aiofiles
        async with aiofiles.open(file_path, 'rb') as f:
            return await f.read()
    
    @staticmethod
    async def async_write_file(file_path: str, content: Union[str, bytes]) -> bool:
        """Asynchronously write file content"""
        import aiofiles
        try:
            mode = 'w' if isinstance(content, str) else 'wb'
            async with aiofiles.open(file_path, mode) as f:
                await f.write(content)
            return True
        except Exception as e:
            logger.error(f"Error writing file {file_path}: {e}")
            return False
    
    @staticmethod
    def safe_filename(filename: str, max_length: int = 200) -> str:
        """Create safe filename by removing problematic characters"""
        import re
        # Replace problematic characters with underscores
        safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', filename)
        
        # Remove multiple underscores
        safe = re.sub(r'_+', '_', safe)
        
        # Trim and ensure length limit
        safe = safe.strip('_')[:max_length]
        
        return safe or 'unnamed_file'
    
    @staticmethod
    def get_directory_size(directory: Union[str, Path]) -> int:
        """Calculate total size of directory recursively"""
        total_size = 0
        directory = Path(directory)
        
        if directory.exists():
            for file_path in directory.rglob('*'):
                if file_path.is_file():
                    try:
                        total_size += file_path.stat().st_size
                    except (OSError, IOError):
                        pass
        
        return total_size


class StringHelper:
    """String manipulation utilities"""
    
    @staticmethod
    def truncate_string(text: str, max_length: int, suffix: str = '...') -> str:
        """Truncate string with suffix if too long"""
        if len(text) <= max_length:
            return text
        
        return text[:max_length - len(suffix)] + suffix
    
    @staticmethod
    def normalize_whitespace(text: str) -> str:
        """Normalize whitespace in text"""
        import re
        # Replace multiple whitespace with single space
        normalized = re.sub(r'\s+', ' ', text)
        return normalized.strip()
    
    @staticmethod
    def extract_words(text: str, min_length: int = 3) -> List[str]:
        """Extract words from text, filtering by minimum length"""
        import re
        words = re.findall(r'\b[a-zA-Z]{' + str(min_length) + r',}\b', text.lower())
        return list(set(words))  # Remove duplicates
    
    @staticmethod
    def calculate_similarity(text1: str, text2: str) -> float:
        """Calculate similarity between two texts (0.0 to 1.0)"""
        from difflib import SequenceMatcher
        return SequenceMatcher(None, text1, text2).ratio()
    
    @staticmethod
    def generate_slug(text: str, max_length: int = 50) -> str:
        """Generate URL-friendly slug from text"""
        import re
        # Convert to lowercase and replace non-alphanumeric with hyphens
        slug = re.sub(r'[^a-zA-Z0-9\s-]', '', text.lower())
        slug = re.sub(r'[\s-]+', '-', slug)
        slug = slug.strip('-')[:max_length]
        
        return slug or 'unnamed'
    
    @staticmethod
    def mask_sensitive_data(text: str) -> str:
        """Mask potentially sensitive data in text"""
        import re
        
        # Mask email addresses
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 
                     '[EMAIL_MASKED]', text)
        
        # Mask phone numbers
        text = re.sub(r'\b(?:\+?1[-.\s]?)?(?:\(?[0-9]{3}\)?[-.\s]?)?[0-9]{3}[-.\s]?[0-9]{4}\b', 
                     '[PHONE_MASKED]', text)
        
        # Mask potential credit card numbers
        text = re.sub(r'\b(?:\d{4}[-\s]?){3}\d{4}\b', '[CARD_MASKED]', text)
        
        return text


class JSONHelper:
    """JSON handling utilities"""
    
    @staticmethod
    def safe_json_loads(json_str: str, default: Any = None) -> Any:
        """Safely parse JSON string with fallback"""
        try:
            return json.loads(json_str)
        except (json.JSONDecodeError, TypeError):
            return default
    
    @staticmethod
    def safe_json_dumps(obj: Any, default: str = '{}') -> str:
        """Safely serialize object to JSON with fallback"""
        try:
            return json.dumps(obj, default=str, ensure_ascii=False, indent=2)
        except (TypeError, ValueError):
            return default
    
    @staticmethod
    def flatten_json(data: Dict[str, Any], separator: str = '.') -> Dict[str, Any]:
        """Flatten nested JSON object"""
        def _flatten(obj: Any, parent_key: str = '') -> Dict[str, Any]:
            items = []
            
            if isinstance(obj, dict):
                for key, value in obj.items():
                    new_key = f"{parent_key}{separator}{key}" if parent_key else key
                    items.extend(_flatten(value, new_key).items())
            elif isinstance(obj, list):
                for i, value in enumerate(obj):
                    new_key = f"{parent_key}{separator}{i}" if parent_key else str(i)
                    items.extend(_flatten(value, new_key).items())
            else:
                return {parent_key: obj}
            
            return dict(items)
        
        return _flatten(data)
    
    @staticmethod
    def merge_json_objects(obj1: Dict[str, Any], obj2: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two JSON objects"""
        import copy
        result = copy.deepcopy(obj1)
        
        def _merge(target: Dict[str, Any], source: Dict[str, Any]):
            for key, value in source.items():
                if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                    _merge(target[key], value)
                else:
                    target[key] = copy.deepcopy(value)
        
        _merge(result, obj2)
        return result


class HashHelper:
    """Hashing and ID generation utilities"""
    
    @staticmethod
    def generate_id(prefix: str = '', length: int = 8) -> str:
        """Generate unique ID with optional prefix"""
        unique_id = str(uuid.uuid4()).replace('-', '')[:length]
        return f"{prefix}{unique_id}" if prefix else unique_id
    
    @staticmethod
    def hash_string(text: str, algorithm: str = 'sha256') -> str:
        """Generate hash of string"""
        return hashlib.new(algorithm, text.encode('utf-8')).hexdigest()
    
    @staticmethod
    def hash_dict(data: Dict[str, Any]) -> str:
        """Generate hash of dictionary (order-independent)"""
        # Sort keys to ensure consistent hash
        sorted_json = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(sorted_json.encode('utf-8')).hexdigest()
    
    @staticmethod
    def short_hash(text: str, length: int = 8) -> str:
        """Generate short hash for display purposes"""
        return hashlib.sha256(text.encode('utf-8')).hexdigest()[:length]


class PerformanceHelper:
    """Performance monitoring and optimization utilities"""
    
    @staticmethod
    def time_function(func: Callable[..., T]) -> Callable[..., T]:
        """Decorator to time function execution"""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()
            
            logger.debug(f"Function {func.__name__} took {end_time - start_time:.4f} seconds")
            return result
        
        return wrapper
    
    @staticmethod
    def async_time_function(func: Callable[..., T]) -> Callable[..., T]:
        """Decorator to time async function execution"""
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            result = await func(*args, **kwargs)
            end_time = time.time()
            
            logger.debug(f"Async function {func.__name__} took {end_time - start_time:.4f} seconds")
            return result
        
        return wrapper
    
    @staticmethod
    async def run_with_timeout(coro, timeout_seconds: float):
        """Run coroutine with timeout"""
        try:
            return await asyncio.wait_for(coro, timeout=timeout_seconds)
        except asyncio.TimeoutError:
            logger.warning(f"Operation timed out after {timeout_seconds} seconds")
            raise
    
    @staticmethod
    def batch_process(items: List[T], batch_size: int, processor: Callable[[List[T]], Any]) -> List[Any]:
        """Process items in batches"""
        results = []
        
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            result = processor(batch)
            results.append(result)
        
        return results
    
    @staticmethod
    async def async_batch_process(
        items: List[T], 
        batch_size: int, 
        processor: Callable[[List[T]], Any],
        max_concurrent: int = 5
    ) -> List[Any]:
        """Process items in async batches with concurrency limit"""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_batch(batch: List[T]) -> Any:
            async with semaphore:
                return await processor(batch)
        
        tasks = []
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            task = asyncio.create_task(process_batch(batch))
            tasks.append(task)
        
        return await asyncio.gather(*tasks)


class MemoryHelper:
    """Memory usage monitoring utilities"""
    
    @staticmethod
    def get_memory_usage() -> Dict[str, float]:
        """Get current memory usage statistics"""
        import psutil
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        
        return {
            'rss_mb': memory_info.rss / 1024 / 1024,  # Resident Set Size
            'vms_mb': memory_info.vms / 1024 / 1024,  # Virtual Memory Size
            'percent': process.memory_percent(),
            'available_mb': psutil.virtual_memory().available / 1024 / 1024
        }
    
    @staticmethod
    def memory_monitor(threshold_mb: float = 500.0) -> Callable:
        """Decorator to monitor memory usage"""
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                memory_before = MemoryHelper.get_memory_usage()
                result = func(*args, **kwargs)
                memory_after = MemoryHelper.get_memory_usage()
                
                memory_increase = memory_after['rss_mb'] - memory_before['rss_mb']
                
                if memory_increase > threshold_mb:
                    logger.warning(
                        f"Function {func.__name__} increased memory by {memory_increase:.1f}MB"
                    )
                
                return result
            
            return wrapper
        return decorator


class ConfigHelper:
    """Configuration and environment utilities"""
    
    @staticmethod
    def get_env_bool(key: str, default: bool = False) -> bool:
        """Get boolean from environment variable"""
        value = os.getenv(key, '').lower()
        return value in ('true', '1', 'yes', 'on')
    
    @staticmethod
    def get_env_int(key: str, default: int = 0) -> int:
        """Get integer from environment variable"""
        try:
            return int(os.getenv(key, str(default)))
        except ValueError:
            return default
    
    @staticmethod
    def get_env_list(key: str, separator: str = ',', default: Optional[List[str]] = None) -> List[str]:
        """Get list from environment variable"""
        value = os.getenv(key, '')
        if not value:
            return default or []
        
        return [item.strip() for item in value.split(separator) if item.strip()]
    
    @staticmethod
    def validate_required_env_vars(required_vars: List[str]) -> List[str]:
        """Validate that required environment variables are set"""
        missing_vars = []
        
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        return missing_vars