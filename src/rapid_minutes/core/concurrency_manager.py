"""
Advanced Concurrency and Locking Manager (B4 - Business Logic Layer)
Sophisticated resource management with intelligent locking and queue management
Implements SESE and 82 Rule principles - systematic concurrency control for maximum efficiency
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid
from contextlib import asynccontextmanager
import time

logger = logging.getLogger(__name__)


class LockType(Enum):
    """Types of locks available"""
    SHARED = "shared"  # Multiple readers
    EXCLUSIVE = "exclusive"  # Single writer
    UPGRADEABLE = "upgradeable"  # Can upgrade from shared to exclusive


class QueuePriority(Enum):
    """Task priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class LockRequest:
    """Lock request information"""
    request_id: str
    resource_id: str
    lock_type: LockType
    requestor: str
    requested_at: datetime
    timeout: Optional[float] = None
    priority: QueuePriority = QueuePriority.NORMAL
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ActiveLock:
    """Active lock information"""
    lock_id: str
    resource_id: str
    lock_type: LockType
    holder: str
    acquired_at: datetime
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResourceMetrics:
    """Resource usage metrics"""
    resource_id: str
    total_lock_requests: int = 0
    successful_locks: int = 0
    failed_locks: int = 0
    average_hold_time: float = 0.0
    current_locks: int = 0
    max_concurrent_locks: int = 0
    last_accessed: Optional[datetime] = None


@dataclass
class ConcurrentTask:
    """Concurrent task information"""
    task_id: str
    name: str
    priority: QueuePriority
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    task_func: Optional[Callable] = None
    args: tuple = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    resources_needed: List[str] = field(default_factory=list)
    status: str = "pending"  # pending, running, completed, failed, cancelled
    result: Any = None
    error: Optional[Exception] = None


class ConcurrencyManager:
    """
    Advanced concurrency and resource management system
    Provides sophisticated locking, task queuing, and resource coordination
    """
    
    def __init__(self, max_concurrent_tasks: int = 10):
        """Initialize concurrency manager"""
        self.max_concurrent_tasks = max_concurrent_tasks
        
        # Lock management
        self._active_locks: Dict[str, ActiveLock] = {}
        self._lock_queues: Dict[str, List[LockRequest]] = {}
        self._lock_events: Dict[str, asyncio.Event] = {}
        self._lock_semaphores: Dict[str, asyncio.Semaphore] = {}
        
        # Task management
        self._task_queue: List[ConcurrentTask] = []
        self._running_tasks: Dict[str, ConcurrentTask] = {}
        self._completed_tasks: Dict[str, ConcurrentTask] = {}
        self._task_semaphore = asyncio.Semaphore(max_concurrent_tasks)
        
        # Resource tracking
        self._resource_metrics: Dict[str, ResourceMetrics] = {}
        self._resource_dependencies: Dict[str, Set[str]] = {}
        
        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self._queue_processor_task: Optional[asyncio.Task] = None
        
        # Performance tracking
        self._performance_stats = {
            'total_locks_granted': 0,
            'total_locks_denied': 0,
            'total_tasks_executed': 0,
            'average_task_execution_time': 0.0,
            'deadlocks_detected': 0,
            'lock_timeouts': 0
        }
        
        # Don't start background tasks in __init__ to avoid event loop issues
        self._background_tasks_started = False
        logger.info(f"🔄 Concurrency Manager initialized - max concurrent tasks: {max_concurrent_tasks}")

    def _start_background_tasks(self):
        """Start background maintenance tasks"""
        if self._background_tasks_started:
            return

        try:
            self._cleanup_task = asyncio.create_task(self._cleanup_expired_locks())
            self._queue_processor_task = asyncio.create_task(self._process_task_queue())
            self._background_tasks_started = True
            logger.debug("🔧 Background tasks started")
        except RuntimeError:
            # No event loop running, tasks will be started later
            logger.debug("⏳ Event loop not running, background tasks deferred")
    
    @asynccontextmanager
    async def acquire_lock(
        self,
        resource_id: str,
        lock_type: LockType = LockType.EXCLUSIVE,
        timeout: Optional[float] = None,
        holder_id: Optional[str] = None
    ):
        """
        Acquire a lock on a resource with automatic release
        
        Args:
            resource_id: Unique resource identifier
            lock_type: Type of lock to acquire
            timeout: Maximum time to wait for lock
            holder_id: Identifier of lock holder
            
        Yields:
            Lock object if successful
        """
        # Ensure background tasks are started
        self._start_background_tasks()

        holder_id = holder_id or f"task_{asyncio.current_task().get_name() if asyncio.current_task() else 'unknown'}"
        lock_id = None

        try:
            lock_id = await self._acquire_lock_internal(resource_id, lock_type, timeout, holder_id)
            yield lock_id
        finally:
            if lock_id:
                await self._release_lock_internal(lock_id, holder_id)
    
    async def _acquire_lock_internal(
        self,
        resource_id: str,
        lock_type: LockType,
        timeout: Optional[float],
        holder_id: str
    ) -> str:
        """Internal lock acquisition logic"""
        request_id = str(uuid.uuid4())
        lock_request = LockRequest(
            request_id=request_id,
            resource_id=resource_id,
            lock_type=lock_type,
            requestor=holder_id,
            requested_at=datetime.utcnow(),
            timeout=timeout
        )
        
        # Initialize resource tracking if needed
        if resource_id not in self._resource_metrics:
            self._resource_metrics[resource_id] = ResourceMetrics(resource_id=resource_id)
            self._lock_queues[resource_id] = []
            self._lock_events[resource_id] = asyncio.Event()
        
        metrics = self._resource_metrics[resource_id]
        metrics.total_lock_requests += 1
        metrics.last_accessed = datetime.utcnow()
        
        # Check if lock can be granted immediately
        if self._can_grant_lock(resource_id, lock_type):
            lock_id = await self._grant_lock(resource_id, lock_type, holder_id)
            metrics.successful_locks += 1
            self._performance_stats['total_locks_granted'] += 1
            return lock_id
        
        # Add to queue and wait
        self._lock_queues[resource_id].append(lock_request)
        logger.debug(f"🔒 Lock request queued: {request_id} for resource {resource_id}")
        
        # Wait for lock with timeout
        try:
            if timeout:
                await asyncio.wait_for(
                    self._wait_for_lock(resource_id, request_id),
                    timeout=timeout
                )
            else:
                await self._wait_for_lock(resource_id, request_id)
            
            # Check if our request was granted
            for lock_id, active_lock in self._active_locks.items():
                if active_lock.resource_id == resource_id and active_lock.holder == holder_id:
                    metrics.successful_locks += 1
                    self._performance_stats['total_locks_granted'] += 1
                    return lock_id
            
            raise RuntimeError(f"Lock not granted for resource {resource_id}")
            
        except asyncio.TimeoutError:
            # Remove from queue on timeout
            self._lock_queues[resource_id] = [
                req for req in self._lock_queues[resource_id] 
                if req.request_id != request_id
            ]
            metrics.failed_locks += 1
            self._performance_stats['lock_timeouts'] += 1
            raise asyncio.TimeoutError(f"Lock acquisition timeout for resource {resource_id}")
    
    def _can_grant_lock(self, resource_id: str, lock_type: LockType) -> bool:
        """Check if lock can be granted immediately"""
        resource_locks = [
            lock for lock in self._active_locks.values()
            if lock.resource_id == resource_id
        ]
        
        if not resource_locks:
            return True  # No existing locks
        
        if lock_type == LockType.SHARED:
            # Shared locks can coexist with other shared locks
            return all(lock.lock_type == LockType.SHARED for lock in resource_locks)
        
        elif lock_type == LockType.EXCLUSIVE:
            # Exclusive locks require no other locks
            return len(resource_locks) == 0
        
        elif lock_type == LockType.UPGRADEABLE:
            # Upgradeable locks can coexist with shared locks
            exclusive_locks = [lock for lock in resource_locks if lock.lock_type == LockType.EXCLUSIVE]
            return len(exclusive_locks) == 0
        
        return False
    
    async def _grant_lock(self, resource_id: str, lock_type: LockType, holder_id: str) -> str:
        """Grant lock and update tracking"""
        lock_id = str(uuid.uuid4())
        
        active_lock = ActiveLock(
            lock_id=lock_id,
            resource_id=resource_id,
            lock_type=lock_type,
            holder=holder_id,
            acquired_at=datetime.utcnow()
        )
        
        self._active_locks[lock_id] = active_lock
        
        # Update metrics
        metrics = self._resource_metrics[resource_id]
        metrics.current_locks += 1
        metrics.max_concurrent_locks = max(metrics.max_concurrent_locks, metrics.current_locks)
        
        logger.debug(f"🔓 Lock granted: {lock_id} for resource {resource_id} to {holder_id}")
        return lock_id
    
    async def _wait_for_lock(self, resource_id: str, request_id: str):
        """Wait for lock to become available"""
        while True:
            # Check if we can be granted the lock
            request = next(
                (req for req in self._lock_queues[resource_id] if req.request_id == request_id),
                None
            )
            
            if not request:
                break  # Request was removed (timeout or cancellation)
            
            if self._can_grant_lock(resource_id, request.lock_type):
                # Remove from queue and grant lock
                self._lock_queues[resource_id] = [
                    req for req in self._lock_queues[resource_id] 
                    if req.request_id != request_id
                ]
                await self._grant_lock(resource_id, request.lock_type, request.requestor)
                break
            
            # Wait for lock state to change
            self._lock_events[resource_id].clear()
            await self._lock_events[resource_id].wait()
    
    async def _release_lock_internal(self, lock_id: str, holder_id: str):
        """Internal lock release logic"""
        if lock_id not in self._active_locks:
            logger.warning(f"⚠️ Attempted to release non-existent lock: {lock_id}")
            return
        
        active_lock = self._active_locks[lock_id]
        
        if active_lock.holder != holder_id:
            logger.error(f"❌ Lock holder mismatch: {active_lock.holder} vs {holder_id}")
            return
        
        resource_id = active_lock.resource_id
        
        # Update metrics
        hold_time = (datetime.utcnow() - active_lock.acquired_at).total_seconds()
        metrics = self._resource_metrics[resource_id]
        
        if metrics.average_hold_time == 0:
            metrics.average_hold_time = hold_time
        else:
            # Exponential moving average
            alpha = 0.1
            metrics.average_hold_time = alpha * hold_time + (1 - alpha) * metrics.average_hold_time
        
        metrics.current_locks -= 1
        
        # Remove lock
        del self._active_locks[lock_id]
        
        # Notify waiting lock requests
        if resource_id in self._lock_events:
            self._lock_events[resource_id].set()
        
        logger.debug(f"🔓 Lock released: {lock_id} for resource {resource_id}")
    
    async def submit_task(
        self,
        task_func: Callable,
        *args,
        task_name: Optional[str] = None,
        priority: QueuePriority = QueuePriority.NORMAL,
        dependencies: Optional[List[str]] = None,
        resources_needed: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """
        Submit a task for concurrent execution
        
        Args:
            task_func: Function to execute
            *args: Function arguments
            task_name: Task name for identification
            priority: Task priority
            dependencies: Task IDs this task depends on
            resources_needed: Resources this task needs
            **kwargs: Function keyword arguments
            
        Returns:
            Task ID for tracking
        """
        task_id = str(uuid.uuid4())
        task_name = task_name or f"task_{task_func.__name__}"
        
        task = ConcurrentTask(
            task_id=task_id,
            name=task_name,
            priority=priority,
            created_at=datetime.utcnow(),
            task_func=task_func,
            args=args,
            kwargs=kwargs,
            dependencies=dependencies or [],
            resources_needed=resources_needed or []
        )
        
        self._task_queue.append(task)
        self._task_queue.sort(key=lambda t: t.priority.value, reverse=True)  # Higher priority first
        
        logger.info(f"📋 Task submitted: {task_id} ({task_name})")
        return task_id
    
    async def _process_task_queue(self):
        """Process task queue in background"""
        while True:
            try:
                if not self._task_queue:
                    await asyncio.sleep(0.1)
                    continue
                
                # Find ready tasks (no unresolved dependencies)
                ready_tasks = []
                for task in self._task_queue:
                    if self._are_dependencies_satisfied(task):
                        ready_tasks.append(task)
                
                if not ready_tasks:
                    await asyncio.sleep(0.1)
                    continue
                
                # Select highest priority ready task
                task = max(ready_tasks, key=lambda t: t.priority.value)
                
                # Check if we can run more tasks
                if len(self._running_tasks) >= self.max_concurrent_tasks:
                    await asyncio.sleep(0.1)
                    continue
                
                # Remove from queue and start execution
                self._task_queue.remove(task)
                asyncio.create_task(self._execute_task(task))
                
            except Exception as e:
                logger.error(f"❌ Error in task queue processor: {e}")
                await asyncio.sleep(1)
    
    def _are_dependencies_satisfied(self, task: ConcurrentTask) -> bool:
        """Check if task dependencies are satisfied"""
        for dep_id in task.dependencies:
            if dep_id in self._running_tasks:
                return False  # Dependency still running
            if dep_id not in self._completed_tasks:
                return False  # Dependency not completed
            if self._completed_tasks[dep_id].status == "failed":
                return False  # Dependency failed
        return True
    
    async def _execute_task(self, task: ConcurrentTask):
        """Execute a single task"""
        async with self._task_semaphore:
            task.status = "running"
            task.started_at = datetime.utcnow()
            self._running_tasks[task.task_id] = task
            
            logger.info(f"🚀 Executing task: {task.task_id} ({task.name})")
            
            try:
                # Acquire required resources
                acquired_locks = []
                for resource_id in task.resources_needed:
                    async with self.acquire_lock(resource_id, LockType.EXCLUSIVE) as lock_id:
                        acquired_locks.append(lock_id)
                        
                        # Execute task function
                        if asyncio.iscoroutinefunction(task.task_func):
                            task.result = await task.task_func(*task.args, **task.kwargs)
                        else:
                            # Run sync function in thread pool
                            loop = asyncio.get_event_loop()
                            task.result = await loop.run_in_executor(
                                None, lambda: task.task_func(*task.args, **task.kwargs)
                            )
                
                task.status = "completed"
                task.completed_at = datetime.utcnow()
                
                # Update performance stats
                execution_time = (task.completed_at - task.started_at).total_seconds()
                self._performance_stats['total_tasks_executed'] += 1
                
                if self._performance_stats['average_task_execution_time'] == 0:
                    self._performance_stats['average_task_execution_time'] = execution_time
                else:
                    alpha = 0.1
                    old_avg = self._performance_stats['average_task_execution_time']
                    self._performance_stats['average_task_execution_time'] = (
                        alpha * execution_time + (1 - alpha) * old_avg
                    )
                
                logger.info(f"✅ Task completed: {task.task_id} in {execution_time:.2f}s")
                
            except Exception as e:
                task.status = "failed"
                task.error = e
                task.completed_at = datetime.utcnow()
                logger.error(f"❌ Task failed: {task.task_id} - {e}")
            
            finally:
                # Move to completed tasks
                if task.task_id in self._running_tasks:
                    del self._running_tasks[task.task_id]
                self._completed_tasks[task.task_id] = task
    
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a submitted task"""
        # Check running tasks
        if task_id in self._running_tasks:
            task = self._running_tasks[task_id]
        elif task_id in self._completed_tasks:
            task = self._completed_tasks[task_id]
        else:
            # Check queue
            task = next((t for t in self._task_queue if t.task_id == task_id), None)
        
        if not task:
            return None
        
        return {
            'task_id': task.task_id,
            'name': task.name,
            'status': task.status,
            'priority': task.priority.value,
            'created_at': task.created_at.isoformat(),
            'started_at': task.started_at.isoformat() if task.started_at else None,
            'completed_at': task.completed_at.isoformat() if task.completed_at else None,
            'dependencies': task.dependencies,
            'resources_needed': task.resources_needed,
            'error_message': str(task.error) if task.error else None
        }
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending or running task"""
        # Remove from queue
        self._task_queue = [t for t in self._task_queue if t.task_id != task_id]
        
        # Cancel running task (limited support)
        if task_id in self._running_tasks:
            task = self._running_tasks[task_id]
            task.status = "cancelled"
            # Note: Can't really cancel a running asyncio task safely
            logger.warning(f"⚠️ Task marked as cancelled but may still be running: {task_id}")
            return True
        
        logger.info(f"🚫 Task cancelled: {task_id}")
        return True
    
    async def wait_for_task(self, task_id: str, timeout: Optional[float] = None) -> Any:
        """Wait for task completion and return result"""
        start_time = time.time()
        
        while True:
            if task_id in self._completed_tasks:
                task = self._completed_tasks[task_id]
                if task.status == "completed":
                    return task.result
                elif task.status == "failed":
                    raise task.error or RuntimeError(f"Task {task_id} failed")
                elif task.status == "cancelled":
                    raise asyncio.CancelledError(f"Task {task_id} was cancelled")
            
            if timeout and (time.time() - start_time) > timeout:
                raise asyncio.TimeoutError(f"Task {task_id} did not complete within {timeout}s")
            
            await asyncio.sleep(0.1)
    
    def detect_deadlocks(self) -> List[Dict[str, Any]]:
        """Detect potential deadlocks in lock dependency graph"""
        deadlocks = []
        
        # Build dependency graph
        resource_holders = {}
        resource_waiters = {}
        
        for lock_id, active_lock in self._active_locks.items():
            resource_id = active_lock.resource_id
            holder = active_lock.holder
            
            if resource_id not in resource_holders:
                resource_holders[resource_id] = []
            resource_holders[resource_id].append(holder)
        
        for resource_id, queue in self._lock_queues.items():
            resource_waiters[resource_id] = [req.requestor for req in queue]
        
        # Simple cycle detection (simplified implementation)
        for resource_id, waiters in resource_waiters.items():
            holders = resource_holders.get(resource_id, [])
            
            for waiter in waiters:
                for holder in holders:
                    # Check if holder is waiting for resources that waiter holds
                    waiter_resources = [
                        r for r, h in resource_holders.items() if waiter in h
                    ]
                    
                    holder_waiting = []
                    for r, w in resource_waiters.items():
                        if holder in w:
                            holder_waiting.append(r)
                    
                    # Simple deadlock detection
                    if any(wr in holder_waiting for wr in waiter_resources):
                        deadlocks.append({
                            'resource_1': resource_id,
                            'resource_2': waiter_resources[0] if waiter_resources else None,
                            'participant_1': waiter,
                            'participant_2': holder,
                            'detected_at': datetime.utcnow().isoformat()
                        })
        
        if deadlocks:
            self._performance_stats['deadlocks_detected'] += len(deadlocks)
            logger.warning(f"🚨 Detected {len(deadlocks)} potential deadlocks")
        
        return deadlocks
    
    async def _cleanup_expired_locks(self):
        """Clean up expired locks and stale tasks"""
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                current_time = datetime.utcnow()
                
                # Clean up expired locks
                expired_locks = []
                for lock_id, active_lock in self._active_locks.items():
                    if active_lock.expires_at and current_time > active_lock.expires_at:
                        expired_locks.append(lock_id)
                
                for lock_id in expired_locks:
                    logger.warning(f"⏰ Force releasing expired lock: {lock_id}")
                    active_lock = self._active_locks[lock_id]
                    await self._release_lock_internal(lock_id, active_lock.holder)
                
                # Clean up old completed tasks (keep last 1000)
                if len(self._completed_tasks) > 1000:
                    sorted_tasks = sorted(
                        self._completed_tasks.items(),
                        key=lambda x: x[1].completed_at or datetime.min
                    )
                    tasks_to_remove = sorted_tasks[:-1000]
                    for task_id, _ in tasks_to_remove:
                        del self._completed_tasks[task_id]
                
                # Detect deadlocks periodically
                deadlocks = self.detect_deadlocks()
                if deadlocks:
                    logger.error(f"🚨 Active deadlocks detected: {len(deadlocks)}")
                
            except Exception as e:
                logger.error(f"❌ Error in cleanup task: {e}")
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get comprehensive system statistics"""
        return {
            'locks': {
                'active_locks': len(self._active_locks),
                'queued_requests': sum(len(q) for q in self._lock_queues.values()),
                'resources_tracked': len(self._resource_metrics),
                'performance': self._performance_stats.copy()
            },
            'tasks': {
                'queued_tasks': len(self._task_queue),
                'running_tasks': len(self._running_tasks),
                'completed_tasks': len(self._completed_tasks),
                'max_concurrent': self.max_concurrent_tasks,
                'queue_by_priority': {
                    priority.name: len([t for t in self._task_queue if t.priority == priority])
                    for priority in QueuePriority
                }
            },
            'resources': {
                resource_id: {
                    'total_requests': metrics.total_lock_requests,
                    'success_rate': (metrics.successful_locks / metrics.total_lock_requests * 100) 
                                  if metrics.total_lock_requests > 0 else 0,
                    'current_locks': metrics.current_locks,
                    'max_concurrent': metrics.max_concurrent_locks,
                    'avg_hold_time': metrics.average_hold_time
                }
                for resource_id, metrics in self._resource_metrics.items()
            }
        }
    
    async def cleanup(self):
        """Clean up all resources and stop background tasks"""
        # Cancel background tasks
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        if self._queue_processor_task:
            self._queue_processor_task.cancel()
            try:
                await self._queue_processor_task
            except asyncio.CancelledError:
                pass
        
        # Release all active locks
        for lock_id in list(self._active_locks.keys()):
            active_lock = self._active_locks[lock_id]
            await self._release_lock_internal(lock_id, active_lock.holder)
        
        logger.info("🧹 Concurrency Manager cleanup completed")
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.cleanup()


# Global concurrency manager instance
# concurrency_manager = ConcurrencyManager()  # Commented out to avoid event loop issues during testing


# Convenience functions
def get_concurrency_manager() -> ConcurrencyManager:
    """Get or create concurrency manager instance"""
    return ConcurrencyManager()


async def with_exclusive_lock(resource_id: str, timeout: Optional[float] = None):
    """Convenience function for exclusive lock context"""
    manager = get_concurrency_manager()
    async with manager.acquire_lock(
        resource_id,
        LockType.EXCLUSIVE, 
        timeout
    ) as lock:
        yield lock


async def submit_concurrent_task(
    func: Callable, 
    *args, 
    priority: QueuePriority = QueuePriority.NORMAL,
    **kwargs
) -> str:
    """Convenience function to submit concurrent task"""
    manager = get_concurrency_manager()
    return await manager.submit_task(
        func, *args, priority=priority, **kwargs
    )