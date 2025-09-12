"""
Ollama LLM Client Module (C2 - AI Processing Layer)
High-performance Ollama integration based on SYSTEM_ARCHITECTURE.md specifications
Implements 82 Rule principle - 20% core functionality for 80% AI processing effectiveness
"""

import asyncio
import logging
import json
from typing import Dict, List, Optional, Union, AsyncIterator
from dataclasses import dataclass
from datetime import datetime, timedelta
import aiohttp
import time

from ..config import settings

logger = logging.getLogger(__name__)


@dataclass
class ModelInfo:
    """Model information container"""
    name: str
    size: str
    digest: str
    modified_at: datetime
    details: Dict[str, any]


@dataclass
class GenerationResponse:
    """LLM generation response container"""
    content: str
    model: str
    created_at: datetime
    done: bool
    total_duration: int
    load_duration: int
    prompt_eval_count: int
    prompt_eval_duration: int
    eval_count: int
    eval_duration: int
    context: List[int]
    metadata: Dict[str, any]


class OllamaClient:
    """
    High-performance Ollama client with async support
    Handles all LLM interactions for meeting minutes generation
    """
    
    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None):
        """Initialize Ollama client with configuration"""
        self.base_url = base_url or settings.ollama_url
        self.model = model or settings.ollama_model
        self.timeout = aiohttp.ClientTimeout(total=settings.ollama_timeout)
        self.max_retries = settings.ollama_max_retries
        self.session: Optional[aiohttp.ClientSession] = None
        self._connection_pool_size = 10
        self._connection_pool_limit = 100
        
        logger.info(f"🤖 Initializing Ollama client - URL: {self.base_url}, Model: {self.model}")
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def connect(self):
        """Establish connection to Ollama service"""
        if self.session is None or self.session.closed:
            connector = aiohttp.TCPConnector(
                limit=self._connection_pool_limit,
                limit_per_host=self._connection_pool_size,
                keepalive_timeout=30,
                enable_cleanup_closed=True
            )
            
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=self.timeout,
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': f'{settings.app_name}/{settings.app_version}'
                }
            )
            
            logger.debug("📡 Ollama client session created")
    
    async def close(self):
        """Close connection to Ollama service"""
        if self.session and not self.session.closed:
            await self.session.close()
            logger.debug("📡 Ollama client session closed")
    
    async def health_check(self) -> bool:
        """Check if Ollama service is available"""
        try:
            await self.connect()
            async with self.session.get(f"{self.base_url}/api/version") as response:
                if response.status == 200:
                    version_info = await response.json()
                    logger.info(f"✅ Ollama service is healthy - Version: {version_info.get('version', 'unknown')}")
                    return True
                else:
                    logger.warning(f"⚠️ Ollama health check failed - Status: {response.status}")
                    return False
        except Exception as e:
            logger.error(f"❌ Ollama health check failed: {e}")
            return False
    
    async def list_models(self) -> List[ModelInfo]:
        """List available models"""
        try:
            await self.connect()
            async with self.session.get(f"{self.base_url}/api/tags") as response:
                if response.status == 200:
                    data = await response.json()
                    models = []
                    for model_data in data.get('models', []):
                        models.append(ModelInfo(
                            name=model_data['name'],
                            size=model_data.get('size', 0),
                            digest=model_data.get('digest', ''),
                            modified_at=datetime.fromisoformat(model_data.get('modified_at', datetime.now().isoformat()).replace('Z', '+00:00')),
                            details=model_data.get('details', {})
                        ))
                    logger.debug(f"📋 Found {len(models)} available models")
                    return models
                else:
                    logger.error(f"Failed to list models - Status: {response.status}")
                    return []
        except Exception as e:
            logger.error(f"Error listing models: {e}")
            return []
    
    async def pull_model(self, model_name: str) -> bool:
        """Pull a model if not available locally"""
        try:
            await self.connect()
            
            payload = {"name": model_name}
            
            async with self.session.post(
                f"{self.base_url}/api/pull",
                json=payload
            ) as response:
                if response.status == 200:
                    logger.info(f"📥 Starting to pull model: {model_name}")
                    
                    async for line in response.content:
                        if line:
                            try:
                                progress_data = json.loads(line.decode())
                                if progress_data.get('status'):
                                    logger.debug(f"Pull progress: {progress_data['status']}")
                            except json.JSONDecodeError:
                                continue
                    
                    logger.info(f"✅ Model {model_name} pulled successfully")
                    return True
                else:
                    logger.error(f"Failed to pull model {model_name} - Status: {response.status}")
                    return False
        except Exception as e:
            logger.error(f"Error pulling model {model_name}: {e}")
            return False
    
    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        system: Optional[str] = None,
        template: Optional[str] = None,
        context: Optional[List[int]] = None,
        stream: bool = False,
        raw: bool = False,
        format: Optional[str] = None,
        options: Optional[Dict] = None
    ) -> Union[GenerationResponse, AsyncIterator[GenerationResponse]]:
        """
        Generate text using Ollama model
        
        Args:
            prompt: The prompt to send to the model
            model: Model name to use (defaults to configured model)
            system: System message to set context
            template: Custom template to use
            context: Previous conversation context
            stream: Whether to stream the response
            raw: Whether to pass prompt without formatting
            format: Response format (json, etc.)
            options: Additional model options
            
        Returns:
            GenerationResponse or AsyncIterator[GenerationResponse] if streaming
        """
        model_name = model or self.model
        
        # Ensure model is available
        if not await self._ensure_model_available(model_name):
            raise RuntimeError(f"Model {model_name} is not available")
        
        # Prepare payload
        payload = {
            "model": model_name,
            "prompt": prompt,
            "stream": stream
        }
        
        if system:
            payload["system"] = system
        if template:
            payload["template"] = template
        if context:
            payload["context"] = context
        if raw:
            payload["raw"] = raw
        if format:
            payload["format"] = format
        if options:
            payload["options"] = options
        
        logger.debug(f"🚀 Generating with model {model_name} - Prompt length: {len(prompt)}")
        
        try:
            if stream:
                return self._generate_stream(payload)
            else:
                return await self._generate_single(payload)
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            raise
    
    async def _generate_single(self, payload: Dict) -> GenerationResponse:
        """Generate single response (non-streaming)"""
        await self.connect()
        
        for attempt in range(self.max_retries):
            try:
                start_time = time.time()
                
                async with self.session.post(
                    f"{self.base_url}/api/generate",
                    json=payload
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        duration = time.time() - start_time
                        logger.info(f"✅ Generation completed in {duration:.2f}s")
                        
                        return GenerationResponse(
                            content=data.get('response', ''),
                            model=data.get('model', ''),
                            created_at=datetime.utcnow(),
                            done=data.get('done', True),
                            total_duration=data.get('total_duration', 0),
                            load_duration=data.get('load_duration', 0),
                            prompt_eval_count=data.get('prompt_eval_count', 0),
                            prompt_eval_duration=data.get('prompt_eval_duration', 0),
                            eval_count=data.get('eval_count', 0),
                            eval_duration=data.get('eval_duration', 0),
                            context=data.get('context', []),
                            metadata={
                                'attempt': attempt + 1,
                                'response_time': duration,
                                'status_code': response.status
                            }
                        )
                    else:
                        error_text = await response.text()
                        raise aiohttp.ClientResponseError(
                            request_info=response.request_info,
                            history=response.history,
                            status=response.status,
                            message=f"HTTP {response.status}: {error_text}"
                        )
            
            except Exception as e:
                logger.warning(f"Generation attempt {attempt + 1} failed: {e}")
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
    
    async def _generate_stream(self, payload: Dict) -> AsyncIterator[GenerationResponse]:
        """Generate streaming response"""
        await self.connect()
        
        async with self.session.post(
            f"{self.base_url}/api/generate",
            json=payload
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                raise aiohttp.ClientResponseError(
                    request_info=response.request_info,
                    history=response.history,
                    status=response.status,
                    message=f"HTTP {response.status}: {error_text}"
                )
            
            async for line in response.content:
                if line:
                    try:
                        data = json.loads(line.decode())
                        yield GenerationResponse(
                            content=data.get('response', ''),
                            model=data.get('model', ''),
                            created_at=datetime.utcnow(),
                            done=data.get('done', False),
                            total_duration=data.get('total_duration', 0),
                            load_duration=data.get('load_duration', 0),
                            prompt_eval_count=data.get('prompt_eval_count', 0),
                            prompt_eval_duration=data.get('prompt_eval_duration', 0),
                            eval_count=data.get('eval_count', 0),
                            eval_duration=data.get('eval_duration', 0),
                            context=data.get('context', []),
                            metadata={'streaming': True}
                        )
                    except json.JSONDecodeError:
                        continue
    
    async def _ensure_model_available(self, model_name: str) -> bool:
        """Ensure model is available locally"""
        try:
            models = await self.list_models()
            available_models = [model.name for model in models]
            
            if model_name in available_models:
                return True
            
            # Try to pull the model if not available
            logger.info(f"📥 Model {model_name} not found locally, attempting to pull...")
            return await self.pull_model(model_name)
            
        except Exception as e:
            logger.error(f"Error checking model availability: {e}")
            return False
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        stream: bool = False,
        options: Optional[Dict] = None
    ) -> Union[GenerationResponse, AsyncIterator[GenerationResponse]]:
        """
        Chat with model using conversation format
        
        Args:
            messages: List of messages in chat format
            model: Model name to use
            stream: Whether to stream response
            options: Additional options
            
        Returns:
            GenerationResponse or AsyncIterator[GenerationResponse]
        """
        model_name = model or self.model
        
        payload = {
            "model": model_name,
            "messages": messages,
            "stream": stream
        }
        
        if options:
            payload["options"] = options
        
        logger.debug(f"💬 Starting chat with {len(messages)} messages")
        
        await self.connect()
        
        try:
            if stream:
                return self._chat_stream(payload)
            else:
                return await self._chat_single(payload)
        except Exception as e:
            logger.error(f"Chat failed: {e}")
            raise
    
    async def _chat_single(self, payload: Dict) -> GenerationResponse:
        """Single chat response"""
        async with self.session.post(
            f"{self.base_url}/api/chat",
            json=payload
        ) as response:
            if response.status == 200:
                data = await response.json()
                message = data.get('message', {})
                
                return GenerationResponse(
                    content=message.get('content', ''),
                    model=data.get('model', ''),
                    created_at=datetime.utcnow(),
                    done=data.get('done', True),
                    total_duration=data.get('total_duration', 0),
                    load_duration=data.get('load_duration', 0),
                    prompt_eval_count=data.get('prompt_eval_count', 0),
                    prompt_eval_duration=data.get('prompt_eval_duration', 0),
                    eval_count=data.get('eval_count', 0),
                    eval_duration=data.get('eval_duration', 0),
                    context=[],
                    metadata={'chat_mode': True}
                )
            else:
                error_text = await response.text()
                raise aiohttp.ClientResponseError(
                    request_info=response.request_info,
                    history=response.history,
                    status=response.status,
                    message=f"HTTP {response.status}: {error_text}"
                )
    
    async def _chat_stream(self, payload: Dict) -> AsyncIterator[GenerationResponse]:
        """Streaming chat response"""
        async with self.session.post(
            f"{self.base_url}/api/chat",
            json=payload
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                raise aiohttp.ClientResponseError(
                    request_info=response.request_info,
                    history=response.history,
                    status=response.status,
                    message=f"HTTP {response.status}: {error_text}"
                )
            
            async for line in response.content:
                if line:
                    try:
                        data = json.loads(line.decode())
                        message = data.get('message', {})
                        
                        yield GenerationResponse(
                            content=message.get('content', ''),
                            model=data.get('model', ''),
                            created_at=datetime.utcnow(),
                            done=data.get('done', False),
                            total_duration=data.get('total_duration', 0),
                            load_duration=data.get('load_duration', 0),
                            prompt_eval_count=data.get('prompt_eval_count', 0),
                            prompt_eval_duration=data.get('prompt_eval_duration', 0),
                            eval_count=data.get('eval_count', 0),
                            eval_duration=data.get('eval_duration', 0),
                            context=[],
                            metadata={'streaming': True, 'chat_mode': True}
                        )
                    except json.JSONDecodeError:
                        continue
    
    def get_performance_stats(self) -> Dict[str, any]:
        """Get performance statistics"""
        # This would be implemented with actual performance tracking
        return {
            'model': self.model,
            'base_url': self.base_url,
            'max_retries': self.max_retries,
            'timeout': self.timeout.total if self.timeout else None,
            'session_active': self.session is not None and not self.session.closed
        }