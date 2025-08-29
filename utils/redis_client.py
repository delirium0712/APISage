"""
Redis client utilities for caching and session management
"""

import json
import pickle
import hashlib
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
import structlog

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class RedisManager:
    """
    Redis client for caching and session management:
    - Response caching for expensive operations
    - Session storage for API clients
    - Temporary data storage
    - Pub/sub for real-time notifications
    """
    
    def __init__(self, 
                 host: str = "localhost",
                 port: int = 6379,
                 db: int = 0,
                 password: Optional[str] = None,
                 decode_responses: bool = True):
        
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.decode_responses = decode_responses
        
        self.logger = structlog.get_logger(__name__)
        self.client: Optional[redis.Redis] = None
        self._is_initialized = False
        
        # Cache prefixes for different data types
        self.prefixes = {
            "query": "query:",
            "document": "doc:",
            "api_analysis": "api:",
            "code_gen": "code:",
            "session": "session:",
            "metrics": "metrics:",
            "config": "config:"
        }
        
        if not REDIS_AVAILABLE:
            self.logger.warning("redis_not_available", 
                              message="Redis functionality disabled - install redis to enable")
    
    async def initialize(self):
        """Initialize Redis connection"""
        if not REDIS_AVAILABLE:
            return
        
        try:
            self.client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=self.decode_responses,
                socket_keepalive=True,
                socket_keepalive_options={},
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Test connection
            await self.client.ping()
            
            self._is_initialized = True
            self.logger.info("redis_initialized", host=self.host, port=self.port, db=self.db)
            
        except Exception as e:
            self.logger.error("redis_initialization_failed", error=str(e))
            raise
    
    def _ensure_initialized(self):
        """Ensure Redis is initialized"""
        if not self._is_initialized or not REDIS_AVAILABLE:
            raise RuntimeError("Redis not initialized or not available")
    
    def _make_key(self, prefix: str, key: str) -> str:
        """Create a prefixed cache key"""
        return f"{self.prefixes.get(prefix, prefix)}{key}"
    
    def _hash_key(self, data: Union[str, Dict[str, Any]]) -> str:
        """Create a hash key from data"""
        if isinstance(data, dict):
            data = json.dumps(data, sort_keys=True)
        return hashlib.md5(data.encode()).hexdigest()
    
    # Query Response Caching
    
    async def cache_query_response(self, 
                                 query: str,
                                 response: Dict[str, Any],
                                 ttl: int = 3600) -> bool:
        """Cache a query response"""
        self._ensure_initialized()
        
        try:
            key = self._make_key("query", self._hash_key(query))
            value = json.dumps({
                "query": query,
                "response": response,
                "cached_at": datetime.utcnow().isoformat()
            })
            
            result = await self.client.setex(key, ttl, value)
            return bool(result)
            
        except Exception as e:
            self.logger.error("query_cache_store_failed", error=str(e), query=query[:100])
            return False
    
    async def get_cached_query_response(self, query: str) -> Optional[Dict[str, Any]]:
        """Get cached query response"""
        self._ensure_initialized()
        
        try:
            key = self._make_key("query", self._hash_key(query))
            value = await self.client.get(key)
            
            if value:
                cached_data = json.loads(value)
                return cached_data["response"]
            
            return None
            
        except Exception as e:
            self.logger.error("query_cache_retrieve_failed", error=str(e), query=query[:100])
            return None
    
    # Document Metadata Caching
    
    async def cache_document_metadata(self, 
                                    document_id: str,
                                    metadata: Dict[str, Any],
                                    ttl: int = 7200) -> bool:
        """Cache document metadata"""
        self._ensure_initialized()
        
        try:
            key = self._make_key("document", document_id)
            value = json.dumps(metadata)
            
            result = await self.client.setex(key, ttl, value)
            return bool(result)
            
        except Exception as e:
            self.logger.error("document_cache_store_failed", error=str(e), doc_id=document_id)
            return False
    
    async def get_cached_document_metadata(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get cached document metadata"""
        self._ensure_initialized()
        
        try:
            key = self._make_key("document", document_id)
            value = await self.client.get(key)
            
            if value:
                return json.loads(value)
            
            return None
            
        except Exception as e:
            self.logger.error("document_cache_retrieve_failed", error=str(e), doc_id=document_id)
            return None
    
    # API Analysis Caching
    
    async def cache_api_analysis(self, 
                               content_hash: str,
                               analysis: Dict[str, Any],
                               ttl: int = 14400) -> bool:
        """Cache API analysis results"""
        self._ensure_initialized()
        
        try:
            key = self._make_key("api_analysis", content_hash)
            value = json.dumps(analysis)
            
            result = await self.client.setex(key, ttl, value)
            return bool(result)
            
        except Exception as e:
            self.logger.error("api_analysis_cache_store_failed", error=str(e))
            return False
    
    async def get_cached_api_analysis(self, content_hash: str) -> Optional[Dict[str, Any]]:
        """Get cached API analysis"""
        self._ensure_initialized()
        
        try:
            key = self._make_key("api_analysis", content_hash)
            value = await self.client.get(key)
            
            if value:
                return json.loads(value)
            
            return None
            
        except Exception as e:
            self.logger.error("api_analysis_cache_retrieve_failed", error=str(e))
            return None
    
    # Code Generation Caching
    
    async def cache_generated_code(self, 
                                 api_doc_hash: str,
                                 language: str,
                                 template: str,
                                 generated_code: Dict[str, Any],
                                 ttl: int = 7200) -> bool:
        """Cache generated code"""
        self._ensure_initialized()
        
        try:
            cache_key = f"{api_doc_hash}:{language}:{template}"
            key = self._make_key("code_gen", cache_key)
            value = json.dumps(generated_code)
            
            result = await self.client.setex(key, ttl, value)
            return bool(result)
            
        except Exception as e:
            self.logger.error("code_cache_store_failed", error=str(e))
            return False
    
    async def get_cached_generated_code(self, 
                                      api_doc_hash: str,
                                      language: str,
                                      template: str) -> Optional[Dict[str, Any]]:
        """Get cached generated code"""
        self._ensure_initialized()
        
        try:
            cache_key = f"{api_doc_hash}:{language}:{template}"
            key = self._make_key("code_gen", cache_key)
            value = await self.client.get(key)
            
            if value:
                return json.loads(value)
            
            return None
            
        except Exception as e:
            self.logger.error("code_cache_retrieve_failed", error=str(e))
            return None
    
    # Session Management
    
    async def create_session(self, 
                           session_id: str,
                           user_data: Dict[str, Any],
                           ttl: int = 86400) -> bool:
        """Create a user session"""
        self._ensure_initialized()
        
        try:
            key = self._make_key("session", session_id)
            value = json.dumps({
                **user_data,
                "created_at": datetime.utcnow().isoformat(),
                "last_activity": datetime.utcnow().isoformat()
            })
            
            result = await self.client.setex(key, ttl, value)
            return bool(result)
            
        except Exception as e:
            self.logger.error("session_create_failed", error=str(e), session_id=session_id)
            return False
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data"""
        self._ensure_initialized()
        
        try:
            key = self._make_key("session", session_id)
            value = await self.client.get(key)
            
            if value:
                session_data = json.loads(value)
                # Update last activity
                await self.update_session_activity(session_id)
                return session_data
            
            return None
            
        except Exception as e:
            self.logger.error("session_retrieve_failed", error=str(e), session_id=session_id)
            return None
    
    async def update_session_activity(self, session_id: str) -> bool:
        """Update session last activity timestamp"""
        self._ensure_initialized()
        
        try:
            key = self._make_key("session", session_id)
            
            # Use Lua script to atomically update the timestamp
            lua_script = """
            local key = KEYS[1]
            local session_data = redis.call('GET', key)
            if session_data then
                local data = cjson.decode(session_data)
                data['last_activity'] = ARGV[1]
                redis.call('SET', key, cjson.encode(data))
                return 1
            end
            return 0
            """
            
            result = await self.client.eval(
                lua_script, 
                1, 
                key, 
                datetime.utcnow().isoformat()
            )
            return bool(result)
            
        except Exception as e:
            self.logger.error("session_activity_update_failed", error=str(e), session_id=session_id)
            return False
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        self._ensure_initialized()
        
        try:
            key = self._make_key("session", session_id)
            result = await self.client.delete(key)
            return bool(result)
            
        except Exception as e:
            self.logger.error("session_delete_failed", error=str(e), session_id=session_id)
            return False
    
    # Metrics Storage
    
    async def store_metric(self, 
                         metric_name: str,
                         value: float,
                         tags: Dict[str, str] = None,
                         ttl: int = 604800) -> bool:  # 1 week default
        """Store a metric value"""
        self._ensure_initialized()
        
        try:
            timestamp = datetime.utcnow().isoformat()
            metric_data = {
                "name": metric_name,
                "value": value,
                "timestamp": timestamp,
                "tags": tags or {}
            }
            
            # Store with timestamp-based key for time series
            key = self._make_key("metrics", f"{metric_name}:{timestamp}")
            value = json.dumps(metric_data)
            
            result = await self.client.setex(key, ttl, value)
            return bool(result)
            
        except Exception as e:
            self.logger.error("metric_store_failed", error=str(e), metric=metric_name)
            return False
    
    async def get_metrics(self, 
                        metric_name: str,
                        limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent metric values"""
        self._ensure_initialized()
        
        try:
            pattern = self._make_key("metrics", f"{metric_name}:*")
            keys = await self.client.keys(pattern)
            
            if not keys:
                return []
            
            # Sort keys to get most recent first
            keys.sort(reverse=True)
            keys = keys[:limit]
            
            values = await self.client.mget(keys)
            metrics = []
            
            for value in values:
                if value:
                    try:
                        metric_data = json.loads(value)
                        metrics.append(metric_data)
                    except json.JSONDecodeError:
                        continue
            
            return metrics
            
        except Exception as e:
            self.logger.error("metrics_retrieve_failed", error=str(e), metric=metric_name)
            return []
    
    # Configuration Caching
    
    async def cache_config(self, 
                         config_key: str,
                         config_data: Dict[str, Any],
                         ttl: int = 3600) -> bool:
        """Cache configuration data"""
        self._ensure_initialized()
        
        try:
            key = self._make_key("config", config_key)
            value = json.dumps(config_data)
            
            result = await self.client.setex(key, ttl, value)
            return bool(result)
            
        except Exception as e:
            self.logger.error("config_cache_store_failed", error=str(e), config_key=config_key)
            return False
    
    async def get_cached_config(self, config_key: str) -> Optional[Dict[str, Any]]:
        """Get cached configuration"""
        self._ensure_initialized()
        
        try:
            key = self._make_key("config", config_key)
            value = await self.client.get(key)
            
            if value:
                return json.loads(value)
            
            return None
            
        except Exception as e:
            self.logger.error("config_cache_retrieve_failed", error=str(e), config_key=config_key)
            return None
    
    # Utility Methods
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        self._ensure_initialized()
        
        try:
            info = await self.client.info()
            
            # Count keys by prefix
            prefix_counts = {}
            for prefix_name, prefix in self.prefixes.items():
                pattern = f"{prefix}*"
                keys = await self.client.keys(pattern)
                prefix_counts[prefix_name] = len(keys)
            
            return {
                "redis_info": {
                    "connected_clients": info.get("connected_clients", 0),
                    "used_memory": info.get("used_memory", 0),
                    "used_memory_human": info.get("used_memory_human", "0B"),
                    "total_commands_processed": info.get("total_commands_processed", 0),
                    "keyspace_hits": info.get("keyspace_hits", 0),
                    "keyspace_misses": info.get("keyspace_misses", 0)
                },
                "prefix_counts": prefix_counts,
                "hit_rate": self._calculate_hit_rate(info)
            }
            
        except Exception as e:
            self.logger.error("cache_stats_failed", error=str(e))
            return {}
    
    def _calculate_hit_rate(self, info: Dict[str, Any]) -> float:
        """Calculate cache hit rate"""
        hits = info.get("keyspace_hits", 0)
        misses = info.get("keyspace_misses", 0)
        total = hits + misses
        
        if total == 0:
            return 0.0
        
        return (hits / total) * 100
    
    async def clear_cache(self, prefix: Optional[str] = None) -> int:
        """Clear cache by prefix or all cache"""
        self._ensure_initialized()
        
        try:
            if prefix:
                if prefix in self.prefixes:
                    pattern = f"{self.prefixes[prefix]}*"
                else:
                    pattern = f"{prefix}*"
                
                keys = await self.client.keys(pattern)
                if keys:
                    return await self.client.delete(*keys)
                return 0
            else:
                # Clear all cache (use with caution)
                return await self.client.flushdb()
                
        except Exception as e:
            self.logger.error("cache_clear_failed", error=str(e), prefix=prefix)
            return 0
    
    async def set_expiry(self, key: str, ttl: int) -> bool:
        """Set TTL for an existing key"""
        self._ensure_initialized()
        
        try:
            result = await self.client.expire(key, ttl)
            return bool(result)
        except Exception as e:
            self.logger.error("set_expiry_failed", error=str(e), key=key)
            return False
    
    # Pub/Sub for real-time notifications
    
    async def publish_event(self, channel: str, event_data: Dict[str, Any]) -> int:
        """Publish event to channel"""
        self._ensure_initialized()
        
        try:
            message = json.dumps({
                **event_data,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            subscribers = await self.client.publish(channel, message)
            return subscribers
            
        except Exception as e:
            self.logger.error("publish_event_failed", error=str(e), channel=channel)
            return 0
    
    async def subscribe_to_events(self, channels: List[str]):
        """Subscribe to event channels"""
        self._ensure_initialized()
        
        try:
            pubsub = self.client.pubsub()
            await pubsub.subscribe(*channels)
            return pubsub
        except Exception as e:
            self.logger.error("redis_subscribe_failed", error=str(e))
            return None
    
    async def close(self):
        """Close Redis connection"""
        if self.client:
            await self.client.close()
            self._is_initialized = False
            self.logger.info("redis_connection_closed")