"""
Error Recovery and Retry Mechanisms (B3 - Business Logic Layer)
Advanced error handling with intelligent retry strategies
Implements SESE and 82 Rule principles - systematic error handling with focused retry logic
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable, Type
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import random
import traceback

logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """Classification of error types"""
    NETWORK_ERROR = "network_error"
    TIMEOUT_ERROR = "timeout_error"
    VALIDATION_ERROR = "validation_error"
    AI_SERVICE_ERROR = "ai_service_error"
    FILE_SYSTEM_ERROR = "file_system_error"
    PROCESSING_ERROR = "processing_error"
    RESOURCE_ERROR = "resource_error"
    USER_ERROR = "user_error"
    UNKNOWN_ERROR = "unknown_error"


class RetryStrategy(Enum):
    """Retry strategy types"""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_DELAY = "fixed_delay"
    IMMEDIATE = "immediate"
    NO_RETRY = "no_retry"


@dataclass
class ErrorInfo:
    """Comprehensive error information"""
    error_id: str
    error_type: ErrorType
    error_message: str
    original_exception: Optional[Exception] = None
    stack_trace: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    severity: str = "medium"  # low, medium, high, critical
    recoverable: bool = True
    suggested_action: Optional[str] = None


@dataclass
class RetryConfig:
    """Retry configuration parameters"""
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    max_attempts: int = 3
    base_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    backoff_factor: float = 2.0
    jitter: bool = True
    timeout: Optional[float] = None
    retry_on_exceptions: List[Type[Exception]] = field(default_factory=list)
    stop_on_exceptions: List[Type[Exception]] = field(default_factory=list)


@dataclass
class RecoveryAction:
    """Recovery action definition"""
    action_id: str
    description: str
    action_func: Callable
    preconditions: List[Callable] = field(default_factory=list)
    postconditions: List[Callable] = field(default_factory=list)
    priority: int = 5  # 1-10, higher = more priority
    automated: bool = True


@dataclass
class ErrorRecoveryResult:
    """Result of error recovery attempt"""
    success: bool
    error_info: ErrorInfo
    attempted_actions: List[str] = field(default_factory=list)
    recovery_time: Optional[float] = None
    final_attempt: bool = False
    next_retry_delay: Optional[float] = None
    recovered_data: Optional[Any] = None


class ErrorRecoveryManager:
    """
    Advanced error recovery and retry management system
    Provides intelligent error handling with multiple recovery strategies
    """
    
    def __init__(self):
        """Initialize error recovery manager"""
        self.error_history: Dict[str, List[ErrorInfo]] = {}
        self.recovery_actions: Dict[ErrorType, List[RecoveryAction]] = {}
        self.default_retry_configs: Dict[ErrorType, RetryConfig] = {}
        
        self._setup_default_configs()
        self._setup_recovery_actions()
        
        logger.info("🛡️ Error Recovery Manager initialized")
    
    def _setup_default_configs(self):
        """Setup default retry configurations for different error types"""
        self.default_retry_configs = {
            ErrorType.NETWORK_ERROR: RetryConfig(
                strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
                max_attempts=5,
                base_delay=2.0,
                max_delay=120.0,
                backoff_factor=2.0,
                jitter=True
            ),
            ErrorType.TIMEOUT_ERROR: RetryConfig(
                strategy=RetryStrategy.LINEAR_BACKOFF,
                max_attempts=3,
                base_delay=5.0,
                max_delay=30.0,
                backoff_factor=1.5
            ),
            ErrorType.AI_SERVICE_ERROR: RetryConfig(
                strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
                max_attempts=4,
                base_delay=3.0,
                max_delay=60.0,
                backoff_factor=2.5,
                jitter=True
            ),
            ErrorType.FILE_SYSTEM_ERROR: RetryConfig(
                strategy=RetryStrategy.FIXED_DELAY,
                max_attempts=2,
                base_delay=1.0,
                max_delay=5.0
            ),
            ErrorType.PROCESSING_ERROR: RetryConfig(
                strategy=RetryStrategy.IMMEDIATE,
                max_attempts=2
            ),
            ErrorType.VALIDATION_ERROR: RetryConfig(
                strategy=RetryStrategy.NO_RETRY,
                max_attempts=0
            ),
            ErrorType.RESOURCE_ERROR: RetryConfig(
                strategy=RetryStrategy.LINEAR_BACKOFF,
                max_attempts=3,
                base_delay=10.0,
                max_delay=60.0
            ),
            ErrorType.USER_ERROR: RetryConfig(
                strategy=RetryStrategy.NO_RETRY,
                max_attempts=0
            )
        }
    
    def _setup_recovery_actions(self):
        """Setup recovery actions for different error types"""
        # Network error recovery actions
        self.recovery_actions[ErrorType.NETWORK_ERROR] = [
            RecoveryAction(
                action_id="check_connection",
                description="Check network connectivity",
                action_func=self._check_network_connectivity,
                priority=9
            ),
            RecoveryAction(
                action_id="fallback_endpoint",
                description="Switch to fallback endpoint",
                action_func=self._switch_to_fallback_endpoint,
                priority=7
            ),
            RecoveryAction(
                action_id="reduce_payload",
                description="Reduce request payload size",
                action_func=self._reduce_request_payload,
                priority=6
            )
        ]
        
        # AI Service error recovery actions
        self.recovery_actions[ErrorType.AI_SERVICE_ERROR] = [
            RecoveryAction(
                action_id="check_ai_service",
                description="Check AI service health",
                action_func=self._check_ai_service_health,
                priority=10
            ),
            RecoveryAction(
                action_id="use_fallback_model",
                description="Switch to fallback AI model",
                action_func=self._use_fallback_ai_model,
                priority=8
            ),
            RecoveryAction(
                action_id="simplify_prompt",
                description="Simplify AI prompt complexity",
                action_func=self._simplify_ai_prompt,
                priority=6
            )
        ]
        
        # File System error recovery actions
        self.recovery_actions[ErrorType.FILE_SYSTEM_ERROR] = [
            RecoveryAction(
                action_id="check_disk_space",
                description="Check available disk space",
                action_func=self._check_disk_space,
                priority=9
            ),
            RecoveryAction(
                action_id="create_missing_dirs",
                description="Create missing directories",
                action_func=self._create_missing_directories,
                priority=8
            ),
            RecoveryAction(
                action_id="cleanup_temp_files",
                description="Clean up temporary files",
                action_func=self._cleanup_temp_files,
                priority=7
            )
        ]
        
        # Resource error recovery actions
        self.recovery_actions[ErrorType.RESOURCE_ERROR] = [
            RecoveryAction(
                action_id="free_memory",
                description="Free up memory resources",
                action_func=self._free_memory_resources,
                priority=8
            ),
            RecoveryAction(
                action_id="reduce_concurrency",
                description="Reduce concurrent operations",
                action_func=self._reduce_concurrency_level,
                priority=7
            )
        ]
    
    async def handle_error_with_retry(
        self,
        func: Callable,
        *args,
        error_context: Optional[Dict[str, Any]] = None,
        retry_config: Optional[RetryConfig] = None,
        **kwargs
    ) -> Any:
        """
        Execute function with error handling and retry logic
        
        Args:
            func: Function to execute
            *args: Function arguments
            error_context: Additional context for error handling
            retry_config: Custom retry configuration
            **kwargs: Function keyword arguments
            
        Returns:
            Function result or raises final exception
        """
        error_context = error_context or {}
        attempt = 0
        last_error = None
        
        while True:
            attempt += 1
            
            try:
                logger.debug(f"🔄 Executing function attempt {attempt}: {func.__name__}")
                result = await func(*args, **kwargs)
                
                if attempt > 1:
                    logger.info(f"✅ Function succeeded on attempt {attempt}: {func.__name__}")
                
                return result
                
            except Exception as e:
                last_error = e
                error_info = await self._classify_error(e, error_context)
                
                logger.warning(f"⚠️ Function failed on attempt {attempt}: {func.__name__} - {error_info.error_message}")
                
                # Get retry configuration
                config = retry_config or self.default_retry_configs.get(
                    error_info.error_type, 
                    self.default_retry_configs[ErrorType.UNKNOWN_ERROR]
                )
                
                # Check if we should retry
                if attempt >= config.max_attempts or not self._should_retry(error_info, config):
                    logger.error(f"❌ Function failed permanently: {func.__name__} after {attempt} attempts")
                    await self._record_error(error_info)
                    break
                
                # Attempt recovery
                recovery_result = await self._attempt_recovery(error_info)
                if recovery_result.success:
                    logger.info(f"🔧 Recovery successful for {func.__name__}, retrying immediately")
                    continue
                
                # Calculate retry delay
                delay = self._calculate_retry_delay(config, attempt)
                
                if delay > 0:
                    logger.info(f"⏳ Retrying {func.__name__} in {delay:.1f} seconds")
                    await asyncio.sleep(delay)
        
        # Record the final error
        await self._record_error(
            await self._classify_error(last_error, error_context)
        )
        raise last_error
    
    async def _classify_error(self, exception: Exception, context: Dict[str, Any]) -> ErrorInfo:
        """Classify error and create ErrorInfo object"""
        error_id = f"err_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{random.randint(1000, 9999)}"
        
        # Classify error type
        error_type = self._determine_error_type(exception)
        
        # Determine severity
        severity = self._determine_error_severity(exception, error_type)
        
        # Check if error is recoverable
        recoverable = self._is_error_recoverable(exception, error_type)
        
        # Generate suggested action
        suggested_action = self._generate_suggested_action(error_type, exception)
        
        return ErrorInfo(
            error_id=error_id,
            error_type=error_type,
            error_message=str(exception),
            original_exception=exception,
            stack_trace=traceback.format_exc(),
            context=context,
            severity=severity,
            recoverable=recoverable,
            suggested_action=suggested_action
        )
    
    def _determine_error_type(self, exception: Exception) -> ErrorType:
        """Determine error type from exception"""
        error_mapping = {
            'ConnectionError': ErrorType.NETWORK_ERROR,
            'TimeoutError': ErrorType.TIMEOUT_ERROR,
            'asyncio.TimeoutError': ErrorType.TIMEOUT_ERROR,
            'ValidationError': ErrorType.VALIDATION_ERROR,
            'ValueError': ErrorType.VALIDATION_ERROR,
            'FileNotFoundError': ErrorType.FILE_SYSTEM_ERROR,
            'PermissionError': ErrorType.FILE_SYSTEM_ERROR,
            'OSError': ErrorType.FILE_SYSTEM_ERROR,
            'MemoryError': ErrorType.RESOURCE_ERROR,
            'RecursionError': ErrorType.RESOURCE_ERROR
        }
        
        exception_name = type(exception).__name__
        
        # Check for AI service specific errors
        if 'ollama' in str(exception).lower() or 'llm' in str(exception).lower():
            return ErrorType.AI_SERVICE_ERROR
        
        # Check for network related errors
        if any(keyword in str(exception).lower() for keyword in ['connection', 'network', 'dns', 'ssl']):
            return ErrorType.NETWORK_ERROR
        
        return error_mapping.get(exception_name, ErrorType.UNKNOWN_ERROR)
    
    def _determine_error_severity(self, exception: Exception, error_type: ErrorType) -> str:
        """Determine error severity level"""
        # Critical errors that stop system operation
        if error_type in [ErrorType.RESOURCE_ERROR] and isinstance(exception, MemoryError):
            return "critical"
        
        # High severity errors
        if error_type in [ErrorType.AI_SERVICE_ERROR, ErrorType.FILE_SYSTEM_ERROR]:
            return "high"
        
        # Medium severity errors (retryable issues)
        if error_type in [ErrorType.NETWORK_ERROR, ErrorType.TIMEOUT_ERROR, ErrorType.PROCESSING_ERROR]:
            return "medium"
        
        # Low severity errors (user errors, validation issues)
        if error_type in [ErrorType.VALIDATION_ERROR, ErrorType.USER_ERROR]:
            return "low"
        
        return "medium"
    
    def _is_error_recoverable(self, exception: Exception, error_type: ErrorType) -> bool:
        """Determine if error is recoverable"""
        # Non-recoverable error types
        non_recoverable = [ErrorType.VALIDATION_ERROR, ErrorType.USER_ERROR]
        
        if error_type in non_recoverable:
            return False
        
        # Check for specific non-recoverable exceptions
        if isinstance(exception, (ValueError, TypeError)) and error_type == ErrorType.VALIDATION_ERROR:
            return False
        
        return True
    
    def _generate_suggested_action(self, error_type: ErrorType, exception: Exception) -> Optional[str]:
        """Generate suggested action for error resolution"""
        suggestions = {
            ErrorType.NETWORK_ERROR: "Check network connectivity and retry",
            ErrorType.TIMEOUT_ERROR: "Increase timeout settings or reduce payload size",
            ErrorType.VALIDATION_ERROR: "Verify input data format and requirements",
            ErrorType.AI_SERVICE_ERROR: "Check AI service status or use alternative model",
            ErrorType.FILE_SYSTEM_ERROR: "Check file permissions and available disk space",
            ErrorType.PROCESSING_ERROR: "Review processing parameters and input data",
            ErrorType.RESOURCE_ERROR: "Free up system resources or reduce concurrent operations",
            ErrorType.USER_ERROR: "Review user input and correct invalid data"
        }
        
        return suggestions.get(error_type, "Review error details and try again")
    
    def _should_retry(self, error_info: ErrorInfo, config: RetryConfig) -> bool:
        """Determine if error should be retried"""
        # Don't retry if error is not recoverable
        if not error_info.recoverable:
            return False
        
        # Don't retry if configured not to
        if config.strategy == RetryStrategy.NO_RETRY:
            return False
        
        # Check for specific exceptions to stop on
        if config.stop_on_exceptions:
            if any(isinstance(error_info.original_exception, exc_type) 
                  for exc_type in config.stop_on_exceptions):
                return False
        
        return True
    
    def _calculate_retry_delay(self, config: RetryConfig, attempt: int) -> float:
        """Calculate delay before next retry attempt"""
        if config.strategy == RetryStrategy.IMMEDIATE:
            return 0.0
        
        elif config.strategy == RetryStrategy.FIXED_DELAY:
            delay = config.base_delay
        
        elif config.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = config.base_delay * attempt
        
        elif config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = config.base_delay * (config.backoff_factor ** (attempt - 1))
        
        else:
            delay = config.base_delay
        
        # Apply maximum delay limit
        delay = min(delay, config.max_delay)
        
        # Add jitter to prevent thundering herd
        if config.jitter:
            jitter_factor = random.uniform(0.5, 1.5)
            delay *= jitter_factor
        
        return delay
    
    async def _attempt_recovery(self, error_info: ErrorInfo) -> ErrorRecoveryResult:
        """Attempt to recover from error using available recovery actions"""
        start_time = datetime.utcnow()
        attempted_actions = []
        
        # Get recovery actions for this error type
        actions = self.recovery_actions.get(error_info.error_type, [])
        
        if not actions:
            return ErrorRecoveryResult(
                success=False,
                error_info=error_info,
                attempted_actions=attempted_actions
            )
        
        # Sort actions by priority (highest first)
        actions.sort(key=lambda x: x.priority, reverse=True)
        
        for action in actions:
            if not action.automated:
                continue
            
            try:
                logger.info(f"🔧 Attempting recovery action: {action.description}")
                
                # Check preconditions
                if action.preconditions:
                    for precondition in action.preconditions:
                        if not await self._check_condition(precondition, error_info):
                            logger.debug(f"Precondition failed for {action.action_id}")
                            continue
                
                # Execute recovery action
                result = await action.action_func(error_info)
                attempted_actions.append(action.action_id)
                
                if result:
                    # Check postconditions
                    if action.postconditions:
                        for postcondition in action.postconditions:
                            if not await self._check_condition(postcondition, error_info):
                                logger.debug(f"Postcondition failed for {action.action_id}")
                                continue
                    
                    recovery_time = (datetime.utcnow() - start_time).total_seconds()
                    logger.info(f"✅ Recovery action succeeded: {action.description}")
                    
                    return ErrorRecoveryResult(
                        success=True,
                        error_info=error_info,
                        attempted_actions=attempted_actions,
                        recovery_time=recovery_time
                    )
                
            except Exception as e:
                logger.warning(f"⚠️ Recovery action failed: {action.description} - {e}")
                continue
        
        recovery_time = (datetime.utcnow() - start_time).total_seconds()
        return ErrorRecoveryResult(
            success=False,
            error_info=error_info,
            attempted_actions=attempted_actions,
            recovery_time=recovery_time
        )
    
    async def _check_condition(self, condition_func: Callable, error_info: ErrorInfo) -> bool:
        """Check if a condition is met"""
        try:
            if asyncio.iscoroutinefunction(condition_func):
                return await condition_func(error_info)
            else:
                return condition_func(error_info)
        except Exception as e:
            logger.warning(f"Condition check failed: {e}")
            return False
    
    async def _record_error(self, error_info: ErrorInfo):
        """Record error for analysis and reporting"""
        error_key = f"{error_info.error_type.value}_{error_info.timestamp.strftime('%Y%m%d')}"
        
        if error_key not in self.error_history:
            self.error_history[error_key] = []
        
        self.error_history[error_key].append(error_info)
        
        # Limit history size per error type per day
        if len(self.error_history[error_key]) > 100:
            self.error_history[error_key] = self.error_history[error_key][-100:]
        
        logger.debug(f"📝 Error recorded: {error_info.error_id}")
    
    # Recovery action implementations
    
    async def _check_network_connectivity(self, error_info: ErrorInfo) -> bool:
        """Check network connectivity"""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get('https://httpbin.org/status/200', timeout=5) as response:
                    return response.status == 200
        except Exception:
            return False
    
    async def _switch_to_fallback_endpoint(self, error_info: ErrorInfo) -> bool:
        """Switch to fallback endpoint (placeholder implementation)"""
        # This would implement actual endpoint switching logic
        logger.info("Switching to fallback endpoint")
        return True
    
    async def _reduce_request_payload(self, error_info: ErrorInfo) -> bool:
        """Reduce request payload size (placeholder implementation)"""
        # This would implement payload reduction logic
        logger.info("Reducing request payload size")
        return True
    
    async def _check_ai_service_health(self, error_info: ErrorInfo) -> bool:
        """Check AI service health"""
        try:
            from ..ai.ollama_client import OllamaClient
            client = OllamaClient()
            return await client.health_check()
        except Exception:
            return False
    
    async def _use_fallback_ai_model(self, error_info: ErrorInfo) -> bool:
        """Use fallback AI model (placeholder implementation)"""
        logger.info("Switching to fallback AI model")
        return True
    
    async def _simplify_ai_prompt(self, error_info: ErrorInfo) -> bool:
        """Simplify AI prompt complexity (placeholder implementation)"""
        logger.info("Simplifying AI prompt")
        return True
    
    async def _check_disk_space(self, error_info: ErrorInfo) -> bool:
        """Check available disk space"""
        try:
            import shutil
            _, _, free = shutil.disk_usage("/")
            # Require at least 100MB free space
            return free > 100 * 1024 * 1024
        except Exception:
            return False
    
    async def _create_missing_directories(self, error_info: ErrorInfo) -> bool:
        """Create missing directories"""
        try:
            # This would create directories based on error context
            logger.info("Creating missing directories")
            return True
        except Exception:
            return False
    
    async def _cleanup_temp_files(self, error_info: ErrorInfo) -> bool:
        """Clean up temporary files"""
        try:
            from ..storage.temp_storage import TempStorage
            temp_storage = TempStorage()
            cleaned_count = await temp_storage.cleanup_expired_files()
            return cleaned_count > 0
        except Exception:
            return False
    
    async def _free_memory_resources(self, error_info: ErrorInfo) -> bool:
        """Free up memory resources"""
        import gc
        gc.collect()
        logger.info("Freed memory resources")
        return True
    
    async def _reduce_concurrency_level(self, error_info: ErrorInfo) -> bool:
        """Reduce concurrent operations (placeholder implementation)"""
        logger.info("Reducing concurrency level")
        return True
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics and analytics"""
        total_errors = sum(len(errors) for errors in self.error_history.values())
        
        error_type_counts = {}
        severity_counts = {}
        
        for errors in self.error_history.values():
            for error in errors:
                error_type = error.error_type.value
                error_type_counts[error_type] = error_type_counts.get(error_type, 0) + 1
                
                severity = error.severity
                severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        return {
            'total_errors': total_errors,
            'error_types': error_type_counts,
            'severity_distribution': severity_counts,
            'recovery_actions_available': sum(len(actions) for actions in self.recovery_actions.values()),
            'error_history_keys': list(self.error_history.keys())
        }
    
    async def export_error_report(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Export comprehensive error report"""
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=7)
        if not end_date:
            end_date = datetime.utcnow()
        
        filtered_errors = []
        for errors in self.error_history.values():
            for error in errors:
                if start_date <= error.timestamp <= end_date:
                    filtered_errors.append({
                        'error_id': error.error_id,
                        'error_type': error.error_type.value,
                        'error_message': error.error_message,
                        'severity': error.severity,
                        'recoverable': error.recoverable,
                        'timestamp': error.timestamp.isoformat(),
                        'context': error.context
                    })
        
        return {
            'report_period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'total_errors': len(filtered_errors),
            'errors': filtered_errors,
            'statistics': self.get_error_statistics()
        }


# Global error recovery manager instance
error_recovery_manager = ErrorRecoveryManager()


def with_retry(
    retry_config: Optional[RetryConfig] = None,
    error_context: Optional[Dict[str, Any]] = None
):
    """
    Decorator for automatic error handling and retry
    
    Usage:
        @with_retry(RetryConfig(max_attempts=5))
        async def risky_function():
            # function implementation
            pass
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            return await error_recovery_manager.handle_error_with_retry(
                func, *args, 
                error_context=error_context,
                retry_config=retry_config,
                **kwargs
            )
        return wrapper
    return decorator