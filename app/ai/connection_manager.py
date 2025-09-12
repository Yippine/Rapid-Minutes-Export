"""
Advanced Ollama Connection Manager (C2 - AI Processing Layer)
Sophisticated connection pooling, health monitoring, and failover management
Implements SESE and 82 Rule principles - focused connection management for maximum reliability
"""

import asyncio
import logging
from typing import Dict, List, Optional, Union, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import aiohttp
import json
import time
import random
from contextlib import asynccontextmanager

from .ollama_client import OllamaClient, GenerationResponse
from ..core.error_recovery import with_retry, RetryConfig, ErrorType
from ..config import settings

logger = logging.getLogger(__name__)


class ConnectionStatus(Enum):
    """Connection status types"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class LoadBalancingStrategy(Enum):
    """Load balancing strategies"""
    ROUND_ROBIN = "round_robin"
    RANDOM = "random"
    LEAST_CONNECTIONS = "least_connections"
    RESPONSE_TIME = "response_time"
    HEALTH_BASED = "health_based"


@dataclass
class ConnectionMetrics:
    """Connection performance metrics"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_response_time: float = 0.0
    last_request_time: Optional[datetime] = None
    connection_errors: int = 0
    timeout_errors: int = 0
    last_health_check: Optional[datetime] = None
    uptime: timedelta = field(default_factory=timedelta)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ConnectionEndpoint:
    """Connection endpoint configuration"""
    endpoint_id: str
    base_url: str
    model: str
    priority: int = 5  # 1-10, higher = preferred
    max_concurrent: int = 5
    timeout: float = 60.0
    enabled: bool = True
    status: ConnectionStatus = ConnectionStatus.UNKNOWN
    metrics: ConnectionMetrics = field(default_factory=ConnectionMetrics)
    client: Optional[OllamaClient] = None
    active_connections: int = 0
    health_check_interval: int = 30  # seconds


@dataclass
class ConnectionPool:
    """Connection pool for managing multiple endpoints"""
    pool_id: str
    endpoints: List[ConnectionEndpoint]
    strategy: LoadBalancingStrategy = LoadBalancingStrategy.HEALTH_BASED
    max_retries: int = 3
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: int = 60
    health_check_enabled: bool = True


class ConnectionManager:
    """
    Advanced connection manager with pooling, failover, and health monitoring
    Provides high-availability AI service connections with intelligent load balancing
    """
    
    def __init__(self, pool_config: Optional[Dict[str, Any]] = None):
        """Initialize connection manager"""
        self.pools: Dict[str, ConnectionPool] = {}
        self.current_pool_id: str = "default"
        
        # Health monitoring
        self._health_check_task: Optional[asyncio.Task] = None
        self._health_check_interval = 30  # seconds
        
        # Circuit breaker state
        self._circuit_breakers: Dict[str, Dict[str, Any]] = {}
        
        # Load balancing state
        self._round_robin_counters: Dict[str, int] = {}
        
        self._initialize_default_pool(pool_config)
        self._start_health_monitoring()
        
        logger.info("🔗 Advanced Connection Manager initialized")
    
    def _initialize_default_pool(self, config: Optional[Dict[str, Any]]):
        """Initialize default connection pool"""
        config = config or {}
        
        # Create default endpoint
        default_endpoint = ConnectionEndpoint(
            endpoint_id="primary",
            base_url=settings.ollama_url,
            model=settings.ollama_model,
            priority=10,
            max_concurrent=settings.max_concurrent_requests or 5,
            timeout=settings.ollama_timeout or 60.0
        )
        
        # Create fallback endpoints if configured
        endpoints = [default_endpoint]
        
        fallback_urls = config.get('fallback_urls', [])
        for i, url in enumerate(fallback_urls):
            fallback_endpoint = ConnectionEndpoint(
                endpoint_id=f"fallback_{i}",
                base_url=url,
                model=settings.ollama_model,
                priority=5 - i,  # Decreasing priority
                max_concurrent=3,
                timeout=settings.ollama_timeout or 60.0
            )
            endpoints.append(fallback_endpoint)
        
        # Create default pool
        default_pool = ConnectionPool(
            pool_id="default",
            endpoints=endpoints,
            strategy=LoadBalancingStrategy(config.get('strategy', 'health_based')),
            max_retries=config.get('max_retries', 3),
            health_check_enabled=config.get('health_check_enabled', True)
        )
        
        self.pools["default"] = default_pool
        
        # Initialize clients for all endpoints
        asyncio.create_task(self._initialize_endpoint_clients(default_pool))
    
    async def _initialize_endpoint_clients(self, pool: ConnectionPool):
        """Initialize Ollama clients for all endpoints"""
        for endpoint in pool.endpoints:
            if not endpoint.client:
                endpoint.client = OllamaClient(
                    base_url=endpoint.base_url,
                    model=endpoint.model
                )
                logger.debug(f"🔌 Initialized client for endpoint: {endpoint.endpoint_id}")
    
    async def get_healthy_endpoint(self, pool_id: Optional[str] = None) -> Optional[ConnectionEndpoint]:
        """Get a healthy endpoint using load balancing strategy"""
        pool_id = pool_id or self.current_pool_id
        pool = self.pools.get(pool_id)
        
        if not pool:
            logger.error(f"❌ Pool not found: {pool_id}")
            return None
        
        # Filter healthy and enabled endpoints
        available_endpoints = [
            ep for ep in pool.endpoints 
            if ep.enabled and ep.status in [ConnectionStatus.HEALTHY, ConnectionStatus.DEGRADED]
            and ep.active_connections < ep.max_concurrent
            and not self._is_circuit_breaker_open(ep.endpoint_id)
        ]
        
        if not available_endpoints:
            logger.warning("⚠️ No healthy endpoints available")
            return None
        
        # Apply load balancing strategy
        selected_endpoint = self._select_endpoint(available_endpoints, pool.strategy, pool_id)
        
        if selected_endpoint:
            selected_endpoint.active_connections += 1
            logger.debug(f"🎯 Selected endpoint: {selected_endpoint.endpoint_id}")
        
        return selected_endpoint
    
    def _select_endpoint(
        self, 
        endpoints: List[ConnectionEndpoint], 
        strategy: LoadBalancingStrategy,
        pool_id: str
    ) -> Optional[ConnectionEndpoint]:
        """Select endpoint based on load balancing strategy"""
        if not endpoints:
            return None
        
        if strategy == LoadBalancingStrategy.ROUND_ROBIN:
            if pool_id not in self._round_robin_counters:
                self._round_robin_counters[pool_id] = 0
            
            index = self._round_robin_counters[pool_id] % len(endpoints)
            self._round_robin_counters[pool_id] += 1
            return endpoints[index]
        
        elif strategy == LoadBalancingStrategy.RANDOM:
            return random.choice(endpoints)
        
        elif strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
            return min(endpoints, key=lambda ep: ep.active_connections)
        
        elif strategy == LoadBalancingStrategy.RESPONSE_TIME:
            # Select endpoint with best response time
            return min(endpoints, key=lambda ep: ep.metrics.avg_response_time or float('inf'))
        
        elif strategy == LoadBalancingStrategy.HEALTH_BASED:
            # Prioritize by health status and priority
            healthy_endpoints = [ep for ep in endpoints if ep.status == ConnectionStatus.HEALTHY]
            if healthy_endpoints:
                return max(healthy_endpoints, key=lambda ep: ep.priority)
            else:
                return max(endpoints, key=lambda ep: ep.priority)
        
        return endpoints[0]
    
    @asynccontextmanager
    async def get_connection(self, pool_id: Optional[str] = None):
        """Get a connection from the pool with automatic cleanup"""
        endpoint = await self.get_healthy_endpoint(pool_id)
        
        if not endpoint:
            raise ConnectionError("No healthy endpoints available")
        
        try:
            yield endpoint
        finally:
            # Release connection
            endpoint.active_connections = max(0, endpoint.active_connections - 1)
    
    @with_retry(RetryConfig(max_attempts=3, base_delay=1.0))
    async def generate_with_failover(
        self,
        prompt: str,
        model: Optional[str] = None,
        system: Optional[str] = None,
        options: Optional[Dict] = None,
        pool_id: Optional[str] = None
    ) -> GenerationResponse:
        """
        Generate text with automatic failover to backup endpoints
        
        Args:
            prompt: Text prompt for generation
            model: Model name override
            system: System message
            options: Generation options
            pool_id: Connection pool ID
            
        Returns:
            GenerationResponse from successful endpoint
        """
        pool_id = pool_id or self.current_pool_id
        pool = self.pools.get(pool_id)
        
        if not pool:
            raise ValueError(f"Pool not found: {pool_id}")
        
        last_exception = None
        attempts = 0
        
        for attempt in range(pool.max_retries):
            attempts += 1
            
            try:
                async with self.get_connection(pool_id) as endpoint:
                    start_time = time.time()
                    
                    # Update metrics
                    endpoint.metrics.total_requests += 1
                    endpoint.metrics.last_request_time = datetime.utcnow()
                    
                    # Make request
                    response = await endpoint.client.generate(
                        prompt=prompt,
                        model=model or endpoint.model,
                        system=system,
                        options=options
                    )
                    
                    # Update success metrics
                    request_time = time.time() - start_time
                    endpoint.metrics.successful_requests += 1
                    self._update_response_time(endpoint, request_time)
                    
                    # Reset circuit breaker on success
                    self._reset_circuit_breaker(endpoint.endpoint_id)
                    
                    logger.debug(f"✅ Generation successful on endpoint {endpoint.endpoint_id}")
                    return response
                    
            except Exception as e:
                last_exception = e
                
                # Update failure metrics
                if 'endpoint' in locals():
                    endpoint.metrics.failed_requests += 1
                    
                    if isinstance(e, asyncio.TimeoutError):
                        endpoint.metrics.timeout_errors += 1
                    elif isinstance(e, (ConnectionError, aiohttp.ClientError)):
                        endpoint.metrics.connection_errors += 1
                    
                    # Update circuit breaker
                    self._update_circuit_breaker(endpoint.endpoint_id, e)
                
                logger.warning(f"⚠️ Generation attempt {attempts} failed: {e}")
                
                if attempt == pool.max_retries - 1:
                    break
                
                # Brief delay before retry
                await asyncio.sleep(0.5 * attempt)
        
        # All attempts failed
        raise last_exception or ConnectionError("All endpoints failed")
    
    def _update_response_time(self, endpoint: ConnectionEndpoint, request_time: float):
        """Update average response time for endpoint"""
        metrics = endpoint.metrics
        
        if metrics.avg_response_time == 0:
            metrics.avg_response_time = request_time
        else:
            # Exponential moving average
            alpha = 0.1
            metrics.avg_response_time = (alpha * request_time) + ((1 - alpha) * metrics.avg_response_time)
    
    def _is_circuit_breaker_open(self, endpoint_id: str) -> bool:
        """Check if circuit breaker is open for endpoint"""
        breaker = self._circuit_breakers.get(endpoint_id)
        
        if not breaker:
            return False
        
        if breaker['state'] == 'open':
            # Check if timeout has passed
            if datetime.utcnow() - breaker['last_failure'] > timedelta(seconds=breaker['timeout']):
                # Move to half-open state
                breaker['state'] = 'half_open'
                return False
            return True
        
        return False
    
    def _update_circuit_breaker(self, endpoint_id: str, error: Exception):
        """Update circuit breaker state after failure"""
        if endpoint_id not in self._circuit_breakers:
            self._circuit_breakers[endpoint_id] = {
                'failure_count': 0,
                'state': 'closed',
                'last_failure': None,
                'timeout': 60
            }
        
        breaker = self._circuit_breakers[endpoint_id]
        breaker['failure_count'] += 1
        breaker['last_failure'] = datetime.utcnow()
        
        # Open circuit breaker if threshold exceeded
        threshold = self.pools[self.current_pool_id].circuit_breaker_threshold
        if breaker['failure_count'] >= threshold and breaker['state'] == 'closed':
            breaker['state'] = 'open'
            logger.warning(f"🚫 Circuit breaker opened for endpoint: {endpoint_id}")
    
    def _reset_circuit_breaker(self, endpoint_id: str):
        """Reset circuit breaker after successful request"""
        if endpoint_id in self._circuit_breakers:
            breaker = self._circuit_breakers[endpoint_id]
            breaker['failure_count'] = 0
            breaker['state'] = 'closed'
    
    def _start_health_monitoring(self):
        """Start background health monitoring task"""
        async def health_monitor():
            while True:
                try:
                    await asyncio.sleep(self._health_check_interval)
                    await self._check_all_endpoints_health()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"❌ Health monitoring error: {e}")
        
        self._health_check_task = asyncio.create_task(health_monitor())
        logger.debug("💓 Health monitoring started")
    
    async def _check_all_endpoints_health(self):
        """Check health of all endpoints"""
        for pool_id, pool in self.pools.items():
            if not pool.health_check_enabled:
                continue
            
            health_tasks = []
            for endpoint in pool.endpoints:
                if endpoint.enabled:
                    task = asyncio.create_task(self._check_endpoint_health(endpoint))
                    health_tasks.append(task)
            
            if health_tasks:
                await asyncio.gather(*health_tasks, return_exceptions=True)
    
    async def _check_endpoint_health(self, endpoint: ConnectionEndpoint):
        """Check health of individual endpoint"""
        if not endpoint.client:
            return
        
        try:
            start_time = time.time()
            is_healthy = await endpoint.client.health_check()
            response_time = time.time() - start_time
            
            # Update health status
            if is_healthy:
                if response_time < 5.0:  # Good response time
                    endpoint.status = ConnectionStatus.HEALTHY
                else:  # Slow response
                    endpoint.status = ConnectionStatus.DEGRADED
            else:
                endpoint.status = ConnectionStatus.UNHEALTHY
            
            endpoint.metrics.last_health_check = datetime.utcnow()
            
        except Exception as e:
            endpoint.status = ConnectionStatus.UNHEALTHY
            logger.debug(f"Health check failed for {endpoint.endpoint_id}: {e}")
    
    def add_endpoint(
        self, 
        pool_id: str, 
        endpoint_id: str, 
        base_url: str, 
        model: str,
        priority: int = 5
    ) -> bool:
        """Add new endpoint to pool"""
        pool = self.pools.get(pool_id)
        if not pool:
            return False
        
        # Check if endpoint already exists
        if any(ep.endpoint_id == endpoint_id for ep in pool.endpoints):
            logger.warning(f"Endpoint {endpoint_id} already exists in pool {pool_id}")
            return False
        
        new_endpoint = ConnectionEndpoint(
            endpoint_id=endpoint_id,
            base_url=base_url,
            model=model,
            priority=priority
        )
        
        new_endpoint.client = OllamaClient(base_url=base_url, model=model)
        pool.endpoints.append(new_endpoint)
        
        logger.info(f"➕ Added endpoint {endpoint_id} to pool {pool_id}")
        return True
    
    def remove_endpoint(self, pool_id: str, endpoint_id: str) -> bool:
        """Remove endpoint from pool"""
        pool = self.pools.get(pool_id)
        if not pool:
            return False
        
        endpoint = next((ep for ep in pool.endpoints if ep.endpoint_id == endpoint_id), None)
        if not endpoint:
            return False
        
        pool.endpoints.remove(endpoint)
        
        # Clean up circuit breaker
        if endpoint_id in self._circuit_breakers:
            del self._circuit_breakers[endpoint_id]
        
        logger.info(f"➖ Removed endpoint {endpoint_id} from pool {pool_id}")
        return True
    
    def enable_endpoint(self, pool_id: str, endpoint_id: str) -> bool:
        """Enable endpoint"""
        pool = self.pools.get(pool_id)
        if not pool:
            return False
        
        endpoint = next((ep for ep in pool.endpoints if ep.endpoint_id == endpoint_id), None)
        if not endpoint:
            return False
        
        endpoint.enabled = True
        logger.info(f"✅ Enabled endpoint {endpoint_id}")
        return True
    
    def disable_endpoint(self, pool_id: str, endpoint_id: str) -> bool:
        """Disable endpoint"""
        pool = self.pools.get(pool_id)
        if not pool:
            return False
        
        endpoint = next((ep for ep in pool.endpoints if ep.endpoint_id == endpoint_id), None)
        if not endpoint:
            return False
        
        endpoint.enabled = False
        logger.info(f"❌ Disabled endpoint {endpoint_id}")
        return True
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get comprehensive connection statistics"""
        stats = {}
        
        for pool_id, pool in self.pools.items():
            pool_stats = {
                'strategy': pool.strategy.value,
                'total_endpoints': len(pool.endpoints),
                'healthy_endpoints': len([ep for ep in pool.endpoints if ep.status == ConnectionStatus.HEALTHY]),
                'degraded_endpoints': len([ep for ep in pool.endpoints if ep.status == ConnectionStatus.DEGRADED]),
                'unhealthy_endpoints': len([ep for ep in pool.endpoints if ep.status == ConnectionStatus.UNHEALTHY]),
                'active_connections': sum(ep.active_connections for ep in pool.endpoints),
                'endpoints': []
            }
            
            for endpoint in pool.endpoints:
                endpoint_stats = {
                    'endpoint_id': endpoint.endpoint_id,
                    'base_url': endpoint.base_url,
                    'model': endpoint.model,
                    'status': endpoint.status.value,
                    'enabled': endpoint.enabled,
                    'priority': endpoint.priority,
                    'active_connections': endpoint.active_connections,
                    'max_concurrent': endpoint.max_concurrent,
                    'metrics': {
                        'total_requests': endpoint.metrics.total_requests,
                        'successful_requests': endpoint.metrics.successful_requests,
                        'failed_requests': endpoint.metrics.failed_requests,
                        'success_rate': (endpoint.metrics.successful_requests / endpoint.metrics.total_requests * 100) if endpoint.metrics.total_requests > 0 else 0,
                        'avg_response_time': endpoint.metrics.avg_response_time,
                        'connection_errors': endpoint.metrics.connection_errors,
                        'timeout_errors': endpoint.metrics.timeout_errors,
                        'last_health_check': endpoint.metrics.last_health_check.isoformat() if endpoint.metrics.last_health_check else None
                    },
                    'circuit_breaker': self._circuit_breakers.get(endpoint.endpoint_id, {'state': 'closed'})
                }
                pool_stats['endpoints'].append(endpoint_stats)
            
            stats[pool_id] = pool_stats
        
        return stats
    
    async def cleanup(self):
        """Clean up resources"""
        # Stop health monitoring
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        # Close all client connections
        for pool in self.pools.values():
            for endpoint in pool.endpoints:
                if endpoint.client:
                    await endpoint.client.close()
        
        logger.info("🧹 Connection Manager cleanup completed")
    
    def set_load_balancing_strategy(self, pool_id: str, strategy: LoadBalancingStrategy) -> bool:
        """Set load balancing strategy for pool"""
        pool = self.pools.get(pool_id)
        if not pool:
            return False
        
        pool.strategy = strategy
        logger.info(f"⚖️ Set load balancing strategy for {pool_id}: {strategy.value}")
        return True
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.cleanup()


# Global connection manager instance
connection_manager = ConnectionManager()


async def get_ai_response(
    prompt: str,
    model: Optional[str] = None,
    system: Optional[str] = None,
    options: Optional[Dict] = None
) -> GenerationResponse:
    """
    Convenience function to get AI response with failover
    
    Args:
        prompt: Text prompt
        model: Model name override
        system: System message
        options: Generation options
        
    Returns:
        GenerationResponse
    """
    return await connection_manager.generate_with_failover(
        prompt=prompt,
        model=model,
        system=system,
        options=options
    )