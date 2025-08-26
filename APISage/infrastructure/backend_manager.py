"""
Backend Manager for coordinating different backend services and configurations
"""

import asyncio
from typing import Dict, Any, List, Optional, Type
from dataclasses import dataclass
from enum import Enum
import structlog

from .vector_stores.base_store import VectorStoreConfig, VectorStoreType
from .vector_stores.store_factory import VectorStoreFactory
from .llm_providers.provider_factory import LLMProviderFactory
from config.settings import SystemConfig


class BackendStatus(Enum):
    """Status of backend services"""
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    CONNECTING = "connecting"
    DISCONNECTED = "disconnected"


@dataclass
class BackendInfo:
    """Information about a backend service"""
    name: str
    type: str  # "vector_store", "llm", "database", etc.
    status: BackendStatus = BackendStatus.UNKNOWN
    config: Dict[str, Any] = None
    health_check_url: Optional[str] = None
    last_health_check: Optional[float] = None
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if self.config is None:
            self.config = {}


class BackendManager:
    """
    Manages and coordinates multiple backend services including:
    - Vector stores (Qdrant, Chroma, Milvus, Pinecone)
    - LLM providers (Ollama, OpenAI, Hugging Face)
    - Other services (Redis, PostgreSQL, etc.)
    """
    
    def __init__(self, system_config: SystemConfig):
        self.system_config = system_config
        self.logger = structlog.get_logger(__name__)
        
        # Registry of backend services
        self.backends: Dict[str, BackendInfo] = {}
        
        # Active connections
        self.active_connections: Dict[str, Any] = {}
        
        # Health check interval (seconds)
        self.health_check_interval = 60
        
        # Background health check task
        self._health_check_task: Optional[asyncio.Task] = None
    
    async def initialize(self):
        """Initialize the backend manager"""
        self.logger.info("initializing_backend_manager")
        
        # Auto-discover available backends
        await self._discover_backends()
        
        # Start health monitoring
        await self._start_health_monitoring()
        
        self.logger.info(
            "backend_manager_initialized",
            backends_count=len(self.backends),
            active_connections=len(self.active_connections)
        )
    
    async def register_backend(self, 
                             name: str,
                             backend_type: str,
                             config: Dict[str, Any],
                             health_check_url: Optional[str] = None) -> None:
        """
        Register a new backend service
        
        Args:
            name: Unique backend name
            backend_type: Type of backend ("vector_store", "llm", etc.)
            config: Backend configuration
            health_check_url: URL for health checks
        """
        backend_info = BackendInfo(
            name=name,
            type=backend_type,
            config=config,
            health_check_url=health_check_url,
            status=BackendStatus.UNKNOWN
        )
        
        self.backends[name] = backend_info
        
        self.logger.info("backend_registered", name=name, type=backend_type)
        
        # Attempt initial connection
        await self._connect_backend(name)
    
    async def _discover_backends(self):
        """Auto-discover available backend services"""
        self.logger.info("discovering_backends")
        
        # Common backend configurations to try
        discovery_configs = [
            {
                "name": "ollama",
                "backend_type": "llm",
                "config": {"base_url": "http://localhost:11434", "provider": "ollama"},
                "health_check_url": "http://localhost:11434/api/version"
            },
            {
                "name": "qdrant",
                "backend_type": "vector_store",
                "config": {"host": "localhost", "port": 6333, "store_type": "qdrant"},
                "health_check_url": "http://localhost:6333/collections"
            },
            {
                "name": "chroma",
                "backend_type": "vector_store",
                "config": {"host": "localhost", "port": 8000, "store_type": "chroma"},
                "health_check_url": "http://localhost:8000/api/v1/version"
            },
            {
                "name": "redis",
                "backend_type": "cache",
                "config": {"host": "localhost", "port": 6379},
                "health_check_url": None  # Will use ping
            },
            {
                "name": "postgresql",
                "backend_type": "database",
                "config": {"host": "localhost", "port": 5432},
                "health_check_url": None
            }
        ]
        
        for config in discovery_configs:
            await self.register_backend(**config)
    
    async def _connect_backend(self, name: str) -> bool:
        """
        Attempt to connect to a backend service
        
        Args:
            name: Backend name
            
        Returns:
            True if connection successful
        """
        if name not in self.backends:
            return False
        
        backend = self.backends[name]
        backend.status = BackendStatus.CONNECTING
        
        try:
            if backend.type == "vector_store":
                connection = await self._connect_vector_store(backend.config)
            elif backend.type == "llm":
                connection = await self._connect_llm_provider(backend.config)
            elif backend.type == "cache":
                connection = await self._connect_redis(backend.config)
            elif backend.type == "database":
                connection = await self._connect_database(backend.config)
            else:
                self.logger.warning("unknown_backend_type", name=name, type=backend.type)
                backend.status = BackendStatus.UNKNOWN
                return False
            
            if connection:
                self.active_connections[name] = connection
                backend.status = BackendStatus.HEALTHY
                backend.error_message = None
                self.logger.info("backend_connected", name=name)
                return True
            else:
                backend.status = BackendStatus.UNHEALTHY
                backend.error_message = "Connection failed"
                return False
                
        except Exception as e:
            backend.status = BackendStatus.UNHEALTHY
            backend.error_message = str(e)
            self.logger.error("backend_connection_failed", name=name, error=str(e))
            return False
    
    async def _connect_vector_store(self, config: Dict[str, Any]):
        """Connect to a vector store"""
        try:
            store_config = VectorStoreConfig(
                store_type=VectorStoreType(config.get("store_type", "qdrant")),
                host=config.get("host", "localhost"),
                port=config.get("port", 6333),
                collection_name=config.get("collection_name", "test"),
                embedding_dim=config.get("embedding_dim", 384)
            )
            
            # Create store but don't initialize yet
            store = VectorStoreFactory.create_store(store_config, None)
            
            # Test connection
            await store.initialize()
            return store
            
        except Exception as e:
            self.logger.error("vector_store_connection_failed", error=str(e), config=config)
            return None
    
    async def _connect_llm_provider(self, config: Dict[str, Any]):
        """Connect to an LLM provider"""
        try:
            provider = LLMProviderFactory.create_provider(
                provider_type=config.get("provider", "ollama"),
                model_name=config.get("model_name", "llama3:8b"),
                base_url=config.get("base_url", "http://localhost:11434"),
                **config
            )
            
            # Test with a simple request
            if hasattr(provider, 'ainvoke'):
                response = await provider.ainvoke("test")
            else:
                response = provider.invoke("test")
            
            return provider
            
        except Exception as e:
            self.logger.error("llm_provider_connection_failed", error=str(e), config=config)
            return None
    
    async def _connect_redis(self, config: Dict[str, Any]):
        """Connect to Redis"""
        try:
            import redis.asyncio as redis
            
            client = redis.Redis(
                host=config.get("host", "localhost"),
                port=config.get("port", 6379),
                decode_responses=True
            )
            
            # Test connection
            await client.ping()
            return client
            
        except Exception as e:
            self.logger.error("redis_connection_failed", error=str(e), config=config)
            return None
    
    async def _connect_database(self, config: Dict[str, Any]):
        """Connect to PostgreSQL database"""
        try:
            import asyncpg
            
            conn = await asyncpg.connect(
                host=config.get("host", "localhost"),
                port=config.get("port", 5432),
                user=config.get("user", "postgres"),
                password=config.get("password", ""),
                database=config.get("database", "postgres")
            )
            
            # Test connection
            await conn.fetchval("SELECT 1")
            return conn
            
        except Exception as e:
            self.logger.error("database_connection_failed", error=str(e), config=config)
            return None
    
    async def _start_health_monitoring(self):
        """Start background health monitoring"""
        if self._health_check_task and not self._health_check_task.done():
            return
        
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        self.logger.info("health_monitoring_started", interval=self.health_check_interval)
    
    async def _health_check_loop(self):
        """Background health check loop"""
        while True:
            try:
                await asyncio.sleep(self.health_check_interval)
                await self._perform_health_checks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("health_check_loop_error", error=str(e))
    
    async def _perform_health_checks(self):
        """Perform health checks on all backends"""
        for name, backend in self.backends.items():
            try:
                is_healthy = await self._check_backend_health(name)
                
                if is_healthy and backend.status != BackendStatus.HEALTHY:
                    backend.status = BackendStatus.HEALTHY
                    backend.error_message = None
                    self.logger.info("backend_recovered", name=name)
                elif not is_healthy and backend.status == BackendStatus.HEALTHY:
                    backend.status = BackendStatus.UNHEALTHY
                    self.logger.warning("backend_became_unhealthy", name=name)
                
                backend.last_health_check = asyncio.get_event_loop().time()
                
            except Exception as e:
                backend.status = BackendStatus.UNHEALTHY
                backend.error_message = str(e)
                self.logger.error("health_check_failed", name=name, error=str(e))
    
    async def _check_backend_health(self, name: str) -> bool:
        """Check health of a specific backend"""
        if name not in self.backends:
            return False
        
        backend = self.backends[name]
        
        # Try health check URL first
        if backend.health_check_url:
            try:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(backend.health_check_url, timeout=5) as response:
                        return response.status == 200
            except:
                pass
        
        # Fallback to connection-specific health checks
        if name in self.active_connections:
            connection = self.active_connections[name]
            
            try:
                if backend.type == "cache":  # Redis
                    await connection.ping()
                elif backend.type == "database":  # PostgreSQL
                    await connection.fetchval("SELECT 1")
                elif backend.type == "llm":
                    # Simple test call
                    if hasattr(connection, 'ainvoke'):
                        await connection.ainvoke("ping")
                    else:
                        connection.invoke("ping")
                
                return True
            except:
                return False
        
        return False
    
    def get_backend_status(self, name: str) -> Optional[BackendInfo]:
        """Get status information for a backend"""
        return self.backends.get(name)
    
    def get_all_backends(self) -> Dict[str, BackendInfo]:
        """Get status of all backends"""
        return self.backends.copy()
    
    def get_healthy_backends(self, backend_type: Optional[str] = None) -> Dict[str, BackendInfo]:
        """Get all healthy backends, optionally filtered by type"""
        healthy = {
            name: backend
            for name, backend in self.backends.items()
            if backend.status == BackendStatus.HEALTHY
        }
        
        if backend_type:
            healthy = {
                name: backend
                for name, backend in healthy.items()
                if backend.type == backend_type
            }
        
        return healthy
    
    def get_connection(self, name: str):
        """Get active connection for a backend"""
        return self.active_connections.get(name)
    
    async def reconnect_backend(self, name: str) -> bool:
        """Attempt to reconnect a backend"""
        self.logger.info("reconnecting_backend", name=name)
        
        # Close existing connection if any
        if name in self.active_connections:
            connection = self.active_connections[name]
            try:
                if hasattr(connection, 'close'):
                    await connection.close()
            except:
                pass
            del self.active_connections[name]
        
        # Attempt reconnection
        return await self._connect_backend(name)
    
    async def shutdown(self):
        """Shutdown the backend manager and close all connections"""
        self.logger.info("shutting_down_backend_manager")
        
        # Cancel health check task
        if self._health_check_task and not self._health_check_task.done():
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        # Close all connections
        for name, connection in self.active_connections.items():
            try:
                if hasattr(connection, 'close'):
                    await connection.close()
                elif hasattr(connection, 'aclose'):
                    await connection.aclose()
            except Exception as e:
                self.logger.error("connection_close_failed", name=name, error=str(e))
        
        self.active_connections.clear()
        self.backends.clear()
        
        self.logger.info("backend_manager_shutdown_complete")
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status"""
        total_backends = len(self.backends)
        healthy_backends = len(self.get_healthy_backends())
        
        health_percentage = (healthy_backends / total_backends * 100) if total_backends > 0 else 0
        
        overall_status = "healthy"
        if health_percentage < 50:
            overall_status = "critical"
        elif health_percentage < 80:
            overall_status = "degraded"
        
        return {
            "overall_status": overall_status,
            "health_percentage": health_percentage,
            "total_backends": total_backends,
            "healthy_backends": healthy_backends,
            "unhealthy_backends": total_backends - healthy_backends,
            "backends": {
                name: {
                    "status": backend.status.value,
                    "type": backend.type,
                    "error": backend.error_message
                }
                for name, backend in self.backends.items()
            }
        }