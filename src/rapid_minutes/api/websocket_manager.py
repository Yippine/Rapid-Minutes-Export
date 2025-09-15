"""
WebSocket Real-time Progress Manager (A2 - API Layer)
Advanced WebSocket management for real-time progress updates
Implements ICE and 82 Rule principles - intuitive real-time communication with comprehensive coverage
"""

import asyncio
import logging
import json
import uuid
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum

try:
    from fastapi import WebSocket, WebSocketDisconnect
    from fastapi.websockets import WebSocketState
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """WebSocket message types"""
    PROGRESS_UPDATE = "progress_update"
    STATUS_CHANGE = "status_change"
    ERROR = "error"
    SUCCESS = "success"
    INFO = "info"
    WARNING = "warning"
    HEARTBEAT = "heartbeat"
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"


class ProgressStatus(Enum):
    """Progress status types"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ProgressUpdate:
    """Progress update information"""
    task_id: str
    status: ProgressStatus
    progress: float  # 0.0 to 1.0
    current_step: Optional[str] = None
    total_steps: Optional[int] = None
    current_step_index: Optional[int] = None
    message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WebSocketMessage:
    """WebSocket message structure"""
    message_type: MessageType
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class ConnectionInfo:
    """WebSocket connection information"""
    connection_id: str
    websocket: Optional[Any]  # WebSocket object
    connected_at: datetime
    last_activity: datetime
    subscribed_channels: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)


class WebSocketManager:
    """
    Advanced WebSocket manager for real-time progress updates
    Handles multiple connections, channels, and message broadcasting
    """
    
    def __init__(self):
        """Initialize WebSocket manager"""
        self.connections: Dict[str, ConnectionInfo] = {}
        self.channels: Dict[str, Set[str]] = {}  # channel -> connection_ids
        self.task_subscribers: Dict[str, Set[str]] = {}  # task_id -> connection_ids
        
        # Message history for reconnection
        self.message_history: Dict[str, List[WebSocketMessage]] = {}
        self.max_history_per_channel = 50
        
        # Background tasks
        self.cleanup_task: Optional[asyncio.Task] = None
        self.heartbeat_task: Optional[asyncio.Task] = None
        
        # Statistics
        self.stats = {
            'total_connections': 0,
            'current_connections': 0,
            'messages_sent': 0,
            'messages_failed': 0,
            'channels_created': 0
        }
        
        self._start_background_tasks()
        logger.info("🔌 WebSocket Manager initialized")
    
    def _start_background_tasks(self):
        """Start background maintenance tasks"""
        self.cleanup_task = asyncio.create_task(self._cleanup_connections())
        self.heartbeat_task = asyncio.create_task(self._send_heartbeats())
        logger.debug("🔧 WebSocket background tasks started")
    
    async def connect(self, websocket, connection_id: Optional[str] = None) -> str:
        """
        Register a new WebSocket connection
        
        Args:
            websocket: WebSocket instance
            connection_id: Optional custom connection ID
            
        Returns:
            Connection ID
        """
        if not FASTAPI_AVAILABLE:
            raise RuntimeError("FastAPI WebSocket support not available")
        
        connection_id = connection_id or str(uuid.uuid4())
        
        # Accept the WebSocket connection
        await websocket.accept()
        
        # Register connection
        connection_info = ConnectionInfo(
            connection_id=connection_id,
            websocket=websocket,
            connected_at=datetime.utcnow(),
            last_activity=datetime.utcnow()
        )
        
        self.connections[connection_id] = connection_info
        
        # Update statistics
        self.stats['total_connections'] += 1
        self.stats['current_connections'] += 1
        
        logger.info(f"🔗 WebSocket connected: {connection_id}")
        
        # Send welcome message
        await self.send_to_connection(
            connection_id,
            MessageType.INFO,
            {
                'message': 'Connected successfully',
                'connection_id': connection_id,
                'server_time': datetime.utcnow().isoformat()
            }
        )
        
        return connection_id
    
    async def disconnect(self, connection_id: str):
        """
        Handle WebSocket disconnection
        
        Args:
            connection_id: Connection ID to disconnect
        """
        if connection_id not in self.connections:
            return
        
        connection_info = self.connections[connection_id]
        
        # Remove from all channels
        for channel in list(connection_info.subscribed_channels):
            await self.unsubscribe_from_channel(connection_id, channel)
        
        # Remove from task subscriptions
        for task_id, subscribers in list(self.task_subscribers.items()):
            if connection_id in subscribers:
                subscribers.discard(connection_id)
                if not subscribers:
                    del self.task_subscribers[task_id]
        
        # Remove connection
        del self.connections[connection_id]
        self.stats['current_connections'] -= 1
        
        logger.info(f"🔌 WebSocket disconnected: {connection_id}")
    
    async def send_to_connection(
        self,
        connection_id: str,
        message_type: MessageType,
        data: Dict[str, Any]
    ) -> bool:
        """
        Send message to specific connection
        
        Args:
            connection_id: Target connection ID
            message_type: Type of message
            data: Message data
            
        Returns:
            Success status
        """
        if connection_id not in self.connections:
            return False
        
        connection_info = self.connections[connection_id]
        websocket = connection_info.websocket
        
        if not websocket or websocket.client_state != WebSocketState.CONNECTED:
            await self.disconnect(connection_id)
            return False
        
        message = WebSocketMessage(
            message_type=message_type,
            data=data
        )
        
        try:
            await websocket.send_text(json.dumps(asdict(message), default=str))
            
            # Update activity
            connection_info.last_activity = datetime.utcnow()
            self.stats['messages_sent'] += 1
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send message to {connection_id}: {e}")
            self.stats['messages_failed'] += 1
            await self.disconnect(connection_id)
            return False
    
    async def broadcast_to_channel(
        self,
        channel: str,
        message_type: MessageType,
        data: Dict[str, Any],
        exclude_connections: Optional[Set[str]] = None
    ) -> int:
        """
        Broadcast message to all connections in a channel
        
        Args:
            channel: Channel name
            message_type: Type of message
            data: Message data
            exclude_connections: Connections to exclude from broadcast
            
        Returns:
            Number of successful sends
        """
        if channel not in self.channels:
            return 0
        
        exclude_connections = exclude_connections or set()
        connection_ids = self.channels[channel] - exclude_connections
        
        message = WebSocketMessage(
            message_type=message_type,
            data=data
        )
        
        # Store in history
        if channel not in self.message_history:
            self.message_history[channel] = []
        
        self.message_history[channel].append(message)
        
        # Limit history size
        if len(self.message_history[channel]) > self.max_history_per_channel:
            self.message_history[channel] = self.message_history[channel][-self.max_history_per_channel:]
        
        # Send to all connections
        successful_sends = 0
        failed_connections = []
        
        for connection_id in connection_ids:
            if await self.send_to_connection(connection_id, message_type, data):
                successful_sends += 1
            else:
                failed_connections.append(connection_id)
        
        # Clean up failed connections
        for failed_id in failed_connections:
            if failed_id in self.channels[channel]:
                self.channels[channel].discard(failed_id)
        
        logger.debug(f"📡 Broadcast to channel {channel}: {successful_sends} successful")
        return successful_sends
    
    async def subscribe_to_channel(self, connection_id: str, channel: str) -> bool:
        """
        Subscribe connection to a channel
        
        Args:
            connection_id: Connection ID
            channel: Channel name
            
        Returns:
            Success status
        """
        if connection_id not in self.connections:
            return False
        
        # Create channel if it doesn't exist
        if channel not in self.channels:
            self.channels[channel] = set()
            self.stats['channels_created'] += 1
        
        # Add connection to channel
        self.channels[channel].add(connection_id)
        self.connections[connection_id].subscribed_channels.add(channel)
        
        logger.debug(f"📢 Connection {connection_id} subscribed to channel: {channel}")
        
        # Send recent message history
        if channel in self.message_history:
            recent_messages = self.message_history[channel][-10:]  # Last 10 messages
            for msg in recent_messages:
                await self.send_to_connection(connection_id, msg.message_type, msg.data)
        
        return True
    
    async def unsubscribe_from_channel(self, connection_id: str, channel: str) -> bool:
        """
        Unsubscribe connection from a channel
        
        Args:
            connection_id: Connection ID
            channel: Channel name
            
        Returns:
            Success status
        """
        if connection_id not in self.connections:
            return False
        
        if channel in self.channels:
            self.channels[channel].discard(connection_id)
            
            # Clean up empty channels
            if not self.channels[channel]:
                del self.channels[channel]
        
        if connection_id in self.connections:
            self.connections[connection_id].subscribed_channels.discard(channel)
        
        logger.debug(f"📢 Connection {connection_id} unsubscribed from channel: {channel}")
        return True
    
    async def subscribe_to_task(self, connection_id: str, task_id: str) -> bool:
        """
        Subscribe connection to task progress updates
        
        Args:
            connection_id: Connection ID
            task_id: Task ID to monitor
            
        Returns:
            Success status
        """
        if connection_id not in self.connections:
            return False
        
        if task_id not in self.task_subscribers:
            self.task_subscribers[task_id] = set()
        
        self.task_subscribers[task_id].add(connection_id)
        logger.debug(f"📊 Connection {connection_id} subscribed to task: {task_id}")
        return True
    
    async def unsubscribe_from_task(self, connection_id: str, task_id: str) -> bool:
        """
        Unsubscribe connection from task progress updates
        
        Args:
            connection_id: Connection ID
            task_id: Task ID to stop monitoring
            
        Returns:
            Success status
        """
        if task_id in self.task_subscribers:
            self.task_subscribers[task_id].discard(connection_id)
            
            # Clean up empty subscriptions
            if not self.task_subscribers[task_id]:
                del self.task_subscribers[task_id]
        
        logger.debug(f"📊 Connection {connection_id} unsubscribed from task: {task_id}")
        return True
    
    async def send_progress_update(
        self,
        task_id: str,
        progress: float,
        status: ProgressStatus,
        message: Optional[str] = None,
        current_step: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Send progress update to task subscribers
        
        Args:
            task_id: Task ID
            progress: Progress percentage (0.0 to 1.0)
            status: Current status
            message: Optional status message
            current_step: Current processing step
            metadata: Additional metadata
            
        Returns:
            Number of connections notified
        """
        if task_id not in self.task_subscribers:
            return 0
        
        progress_update = ProgressUpdate(
            task_id=task_id,
            status=status,
            progress=progress,
            current_step=current_step,
            message=message,
            metadata=metadata or {}
        )
        
        data = asdict(progress_update)
        
        successful_sends = 0
        failed_connections = []
        
        for connection_id in list(self.task_subscribers[task_id]):
            if await self.send_to_connection(connection_id, MessageType.PROGRESS_UPDATE, data):
                successful_sends += 1
            else:
                failed_connections.append(connection_id)
        
        # Clean up failed connections
        for failed_id in failed_connections:
            self.task_subscribers[task_id].discard(failed_id)
        
        if not self.task_subscribers[task_id]:
            del self.task_subscribers[task_id]
        
        return successful_sends
    
    async def handle_client_message(
        self,
        connection_id: str,
        message_data: Dict[str, Any]
    ):
        """
        Handle incoming message from client
        
        Args:
            connection_id: Source connection ID
            message_data: Message data from client
        """
        try:
            message_type = MessageType(message_data.get('type', 'info'))
            data = message_data.get('data', {})
            
            if message_type == MessageType.SUBSCRIBE:
                channel = data.get('channel')
                if channel:
                    await self.subscribe_to_channel(connection_id, channel)
                
                task_id = data.get('task_id')
                if task_id:
                    await self.subscribe_to_task(connection_id, task_id)
            
            elif message_type == MessageType.UNSUBSCRIBE:
                channel = data.get('channel')
                if channel:
                    await self.unsubscribe_from_channel(connection_id, channel)
                
                task_id = data.get('task_id')
                if task_id:
                    await self.unsubscribe_from_task(connection_id, task_id)
            
            elif message_type == MessageType.HEARTBEAT:
                # Respond to heartbeat
                await self.send_to_connection(
                    connection_id,
                    MessageType.HEARTBEAT,
                    {'timestamp': datetime.utcnow().isoformat()}
                )
            
            # Update last activity
            if connection_id in self.connections:
                self.connections[connection_id].last_activity = datetime.utcnow()
                
        except Exception as e:
            logger.error(f"❌ Error handling client message from {connection_id}: {e}")
            await self.send_to_connection(
                connection_id,
                MessageType.ERROR,
                {'message': 'Invalid message format'}
            )
    
    async def _cleanup_connections(self):
        """Clean up stale connections"""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                current_time = datetime.utcnow()
                stale_connections = []
                
                for connection_id, connection_info in self.connections.items():
                    # Remove connections inactive for more than 5 minutes
                    if (current_time - connection_info.last_activity).total_seconds() > 300:
                        stale_connections.append(connection_id)
                
                for connection_id in stale_connections:
                    logger.info(f"🧹 Cleaning up stale connection: {connection_id}")
                    await self.disconnect(connection_id)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Error in connection cleanup: {e}")
    
    async def _send_heartbeats(self):
        """Send periodic heartbeats to all connections"""
        while True:
            try:
                await asyncio.sleep(30)  # Heartbeat every 30 seconds
                
                if self.connections:
                    heartbeat_data = {
                        'timestamp': datetime.utcnow().isoformat(),
                        'active_connections': len(self.connections)
                    }
                    
                    failed_connections = []
                    for connection_id in list(self.connections.keys()):
                        if not await self.send_to_connection(
                            connection_id, 
                            MessageType.HEARTBEAT, 
                            heartbeat_data
                        ):
                            failed_connections.append(connection_id)
                    
                    # Clean up failed connections
                    for failed_id in failed_connections:
                        await self.disconnect(failed_id)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Error sending heartbeats: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get WebSocket manager statistics"""
        return {
            **self.stats,
            'active_channels': len(self.channels),
            'active_task_subscriptions': len(self.task_subscribers),
            'message_history_size': sum(len(history) for history in self.message_history.values()),
            'connections_per_channel': {
                channel: len(connection_ids)
                for channel, connection_ids in self.channels.items()
            },
            'task_subscriber_counts': {
                task_id: len(subscribers)
                for task_id, subscribers in self.task_subscribers.items()
            }
        }
    
    async def cleanup(self):
        """Clean up all resources"""
        # Cancel background tasks
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass
        
        # Close all connections
        for connection_id in list(self.connections.keys()):
            await self.disconnect(connection_id)
        
        logger.info("🧹 WebSocket Manager cleanup completed")
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.cleanup()


# Global WebSocket manager instance
websocket_manager = WebSocketManager()


# Convenience functions for progress tracking
class ProgressTracker:
    """Helper class for tracking task progress"""
    
    def __init__(self, task_id: str, total_steps: int = 100):
        self.task_id = task_id
        self.total_steps = total_steps
        self.current_step = 0
    
    async def update(
        self,
        progress: Optional[float] = None,
        message: Optional[str] = None,
        step_name: Optional[str] = None
    ):
        """Update progress"""
        if progress is None:
            progress = self.current_step / self.total_steps
        
        await websocket_manager.send_progress_update(
            task_id=self.task_id,
            progress=progress,
            status=ProgressStatus.PROCESSING,
            message=message,
            current_step=step_name
        )
    
    async def next_step(self, message: Optional[str] = None, step_name: Optional[str] = None):
        """Move to next step"""
        self.current_step += 1
        await self.update(message=message, step_name=step_name)
    
    async def complete(self, message: str = "Task completed successfully"):
        """Mark task as completed"""
        await websocket_manager.send_progress_update(
            task_id=self.task_id,
            progress=1.0,
            status=ProgressStatus.COMPLETED,
            message=message
        )
    
    async def fail(self, error_message: str):
        """Mark task as failed"""
        await websocket_manager.send_progress_update(
            task_id=self.task_id,
            progress=self.current_step / self.total_steps,
            status=ProgressStatus.FAILED,
            message=error_message
        )