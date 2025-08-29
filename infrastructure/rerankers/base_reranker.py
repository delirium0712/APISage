"""
Base Reranker Class
Defines the interface for all reranking strategies
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import structlog

from ..vector_stores.base_store import SearchResult


@dataclass
class RerankerConfig:
    """Configuration for rerankers"""
    name: str
    reranker_type: str
    enabled: bool = True
    top_k: int = 10
    threshold: float = 0.0
    max_tokens: int = 4000
    temperature: float = 0.1
    use_cache: bool = True
    cache_ttl: int = 3600  # 1 hour
    
    # API documentation specific settings
    api_context_weight: float = 0.7
    technical_accuracy_weight: float = 0.8
    endpoint_relevance_weight: float = 0.9
    code_example_weight: float = 0.6
    
    # Semantic reranking settings
    semantic_similarity_threshold: float = 0.7
    context_window_size: int = 512
    cross_encoder_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    
    # LLM reranking settings
    llm_model: str = "gpt-3.5-turbo"
    llm_provider: str = "openai"
    prompt_template: str = "default"
    max_retries: int = 3


class BaseReranker(ABC):
    """Abstract base class for all rerankers"""
    
    def __init__(self, config: RerankerConfig):
        self.config = config
        self.logger = structlog.get_logger(component=f"Reranker_{config.name}")
        self.cache = {}  # Simple in-memory cache
        
    @abstractmethod
    async def rerank(self, 
                    query: str, 
                    results: List[SearchResult], 
                    context: Optional[Dict[str, Any]] = None) -> List[SearchResult]:
        """
        Rerank search results based on the query and context
        
        Args:
            query: The original search query
            results: List of search results to rerank
            context: Additional context for reranking (e.g., user preferences, domain info)
            
        Returns:
            Reranked list of search results
        """
        pass
    
    @abstractmethod
    def get_reranker_info(self) -> Dict[str, Any]:
        """Get information about the reranker"""
        pass
    
    def is_enabled(self) -> bool:
        """Check if reranker is enabled"""
        return self.config.enabled
    
    def get_cache_key(self, query: str, results: List[SearchResult]) -> str:
        """Generate cache key for query and results"""
        import hashlib
        content = f"{query}:{len(results)}:{','.join([r.document.id for r in results])}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def get_from_cache(self, cache_key: str) -> Optional[List[SearchResult]]:
        """Get results from cache if available and not expired"""
        if not self.config.use_cache:
            return None
            
        if cache_key in self.cache:
            cached_data = self.cache[cache_key]
            if cached_data['expires_at'] > self._get_current_time():
                self.logger.debug("cache_hit", cache_key=cache_key)
                return cached_data['results']
            else:
                # Remove expired cache entry
                del self.cache[cache_key]
        
        return None
    
    def set_cache(self, cache_key: str, results: List[SearchResult]):
        """Cache results with TTL"""
        if not self.config.use_cache:
            return
            
        self.cache[cache_key] = {
            'results': results,
            'expires_at': self._get_current_time() + self.config.cache_ttl
        }
        self.logger.debug("cache_set", cache_key=cache_key, ttl=self.config.cache_ttl)
    
    def _get_current_time(self) -> int:
        """Get current timestamp for cache expiration"""
        import time
        return int(time.time())
    
    def clear_cache(self):
        """Clear all cached results"""
        self.cache.clear()
        self.logger.debug("cache_cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        current_time = self._get_current_time()
        active_entries = sum(1 for entry in self.cache.values() 
                           if entry['expires_at'] > current_time)
        expired_entries = len(self.cache) - active_entries
        
        return {
            "total_entries": len(self.cache),
            "active_entries": active_entries,
            "expired_entries": expired_entries,
            "cache_enabled": self.config.use_cache,
            "cache_ttl": self.config.cache_ttl
        }




