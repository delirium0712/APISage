"""
LLM Manager for handling multiple LLM providers, load balancing, and fallbacks
"""

import asyncio
import time
import random
import os
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import structlog

from .llm_providers.provider_factory import LLMProviderFactory
from config.settings import SystemConfig


class LLMStatus(Enum):
    """Status of an LLM provider"""
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    RATE_LIMITED = "rate_limited"
    ERROR = "error"
    TESTING = "testing"


@dataclass
class LLMProviderInfo:
    """Information about an LLM provider"""
    name: str
    provider_type: str  # "ollama", "openai", "huggingface", etc.
    model_name: str
    config: Dict[str, Any]
    status: LLMStatus = LLMStatus.AVAILABLE
    priority: int = 1  # Higher number = higher priority
    cost_per_token: float = 0.0  # Cost estimation
    max_tokens: Optional[int] = None
    context_window: Optional[int] = None
    
    # Performance metrics
    average_response_time: float = 0.0
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    last_request_time: float = 0.0
    last_error: Optional[str] = None
    
    # Rate limiting
    requests_per_minute: Optional[int] = None
    current_requests: int = 0
    rate_limit_reset_time: float = 0.0


@dataclass
class LLMRequest:
    """LLM request with metadata"""
    prompt: str
    model_preferences: List[str] = None  # Preferred models in order
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    timeout: float = 30.0
    retry_count: int = 3
    fallback_enabled: bool = True
    
    def __post_init__(self):
        if self.model_preferences is None:
            self.model_preferences = []


@dataclass
class LLMResponse:
    """LLM response with metadata"""
    content: str
    provider_name: str
    model_name: str
    response_time: float
    token_usage: Dict[str, int] = None  # {"prompt_tokens": X, "completion_tokens": Y}
    cost_estimate: float = 0.0
    cached: bool = False
    
    def __post_init__(self):
        if self.token_usage is None:
            self.token_usage = {}


class LoadBalancingStrategy(Enum):
    """Load balancing strategies"""
    ROUND_ROBIN = "round_robin"
    PRIORITY = "priority"
    FASTEST = "fastest"
    LEAST_LOADED = "least_loaded"
    RANDOM = "random"


class LLMManager:
    """
    Manages multiple LLM providers with features:
    - Load balancing across providers
    - Automatic failover and retries
    - Rate limit handling
    - Performance monitoring
    - Cost optimization
    - Response caching
    """
    
    def __init__(self, system_config: SystemConfig):
        self.system_config = system_config
        self.logger = structlog.get_logger(__name__)
        
        # Provider registry
        self.providers: Dict[str, LLMProviderInfo] = {}
        self.active_providers: Dict[str, Any] = {}  # Actual provider instances
        
        # Load balancing
        self.load_balancing_strategy = LoadBalancingStrategy.PRIORITY
        self.round_robin_index = 0
        
        # Caching
        self.response_cache: Dict[str, Tuple[LLMResponse, float]] = {}
        self.cache_ttl = 3600  # 1 hour
        
        # Health monitoring
        self.health_check_interval = 60
        self._health_check_task: Optional[asyncio.Task] = None
        
        # Performance tracking
        self.global_stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_response_time": 0.0,
            "cache_hits": 0,
            "cache_misses": 0
        }
    
    async def initialize(self):
        """Initialize the LLM manager"""
        self.logger.info("initializing_llm_manager")
        
        # Auto-register common providers
        await self._auto_register_providers()
        
        # Start health monitoring
        await self._start_health_monitoring()
        
        self.logger.info(
            "llm_manager_initialized",
            providers_count=len(self.providers),
            strategy=self.load_balancing_strategy.value
        )
    
    async def register_provider(self,
                              name: str,
                              provider_type: str,
                              model_name: str,
                              config: Dict[str, Any],
                              priority: int = 1,
                              cost_per_token: float = 0.0) -> bool:
        """
        Register a new LLM provider
        
        Args:
            name: Unique provider name
            provider_type: Type of provider (ollama, openai, etc.)
            model_name: Model name to use
            config: Provider configuration
            priority: Priority for load balancing (higher = more preferred)
            cost_per_token: Estimated cost per token
            
        Returns:
            True if registration successful
        """
        try:
            # Create provider instance
            from .llm_providers.openai_direct_provider import LLMProvider, LLMConfig
            
            # Convert provider_type string to enum
            try:
                provider_enum = LLMProvider(provider_type)
            except ValueError:
                self.logger.error("invalid_provider_type", provider_type=provider_type)
                return False
            
            # Create LLMConfig object - filter out conflicting keys
            config_copy = config.copy()
            config_copy.pop('provider', None)  # Remove provider key to avoid conflict
            
            # Map config attributes to LiteLLM LLMConfig
            llm_config = LLMConfig(
                provider=provider_enum,
                model=model_name,
                api_key=config_copy.get('api_key'),
                base_url=config_copy.get('api_base'),
                temperature=config_copy.get('temperature', 0.7),
                max_tokens=config_copy.get('max_tokens', 2000),
                timeout=config_copy.get('timeout', 30)
            )
            
            provider = LLMProviderFactory.create_provider(llm_config)
            
            # Test the provider
            test_response = await self._test_provider(provider)
            if not test_response:
                self.logger.error("provider_test_failed", name=name)
                return False
            
            # Store provider info
            provider_info = LLMProviderInfo(
                name=name,
                provider_type=provider_type,
                model_name=model_name,
                config=config,
                priority=priority,
                cost_per_token=cost_per_token,
                status=LLMStatus.AVAILABLE
            )
            
            self.providers[name] = provider_info
            self.active_providers[name] = provider
            
            self.logger.info(
                "provider_registered",
                name=name,
                type=provider_type,
                model=model_name,
                priority=priority
            )
            
            return True
            
        except Exception as e:
            self.logger.error("provider_registration_failed", name=name, error=str(e))
            return False
    
    async def _auto_register_providers(self):
        """Auto-register OpenAI provider only"""
        providers_config = [
            {
                "name": "openai_gpt35",
                "provider_type": "openai",
                "model_name": "gpt-3.5-turbo",
                "config": {"api_key": os.getenv("OPENAI_API_KEY")},
                "priority": 10,
            }
        ]
        
        for config in providers_config:
            # Only register if config is valid (e.g., API key exists for OpenAI)
            if config["provider_type"] == "openai" and not config["config"]["api_key"]:
                self.logger.warning("openai_api_key_not_found", message="OPENAI_API_KEY not set")
                continue
            await self.register_provider(**config)
    
    async def _test_provider(self, provider) -> bool:
        """Test if a provider is working"""
        try:
            if hasattr(provider, 'generate'):
                response = await provider.generate("Hello", max_tokens=5)
                return bool(response and str(response).strip())
            elif hasattr(provider, 'ainvoke'):
                response = await provider.ainvoke("Hello", timeout=10)
                return bool(response and str(response).strip())
            else:
                response = provider.invoke("Hello")
                return bool(response and str(response).strip())
            
        except Exception as e:
            self.logger.error("provider_test_error", error=str(e))
            return False
    
    async def generate(self, request: Union[str, LLMRequest]) -> LLMResponse:
        """
        Generate response using best available provider
        
        Args:
            request: Either a simple prompt string or LLMRequest object
            
        Returns:
            LLMResponse with generated content and metadata
        """
        # Convert string to LLMRequest
        if isinstance(request, str):
            request = LLMRequest(prompt=request)
        
        self.global_stats["total_requests"] += 1
        
        # Check cache first
        cache_key = self._generate_cache_key(request)
        cached_response = self._get_cached_response(cache_key)
        if cached_response:
            self.global_stats["cache_hits"] += 1
            return cached_response
        
        self.global_stats["cache_misses"] += 1
        
        # Select provider
        selected_provider = self._select_provider(request.model_preferences)
        if not selected_provider:
            raise RuntimeError("No available LLM providers")
        
        # Attempt generation with retries and fallbacks
        for attempt in range(request.retry_count):
            try:
                response = await self._generate_with_provider(selected_provider, request)
                
                # Cache successful response
                self._cache_response(cache_key, response)
                
                # Update stats
                self.global_stats["successful_requests"] += 1
                self.global_stats["total_response_time"] += response.response_time
                
                return response
                
            except Exception as e:
                self.logger.error(
                    "generation_attempt_failed",
                    provider=selected_provider,
                    attempt=attempt + 1,
                    error=str(e)
                )
                
                # Update provider error status
                if selected_provider in self.providers:
                    provider_info = self.providers[selected_provider]
                    provider_info.failed_requests += 1
                    provider_info.last_error = str(e)
                    provider_info.status = LLMStatus.ERROR
                
                # Try fallback provider if enabled
                if request.fallback_enabled and attempt < request.retry_count - 1:
                    fallback_provider = self._select_fallback_provider(selected_provider)
                    if fallback_provider:
                        selected_provider = fallback_provider
                        continue
                
                if attempt == request.retry_count - 1:
                    self.global_stats["failed_requests"] += 1
                    raise
    
    def _select_provider(self, preferences: List[str] = None) -> Optional[str]:
        """Select best provider based on strategy and preferences"""
        available_providers = [
            name for name, info in self.providers.items()
            if info.status == LLMStatus.AVAILABLE and name in self.active_providers
        ]
        
        if not available_providers:
            return None
        
        # Filter by preferences if provided
        if preferences:
            preferred_available = [p for p in preferences if p in available_providers]
            if preferred_available:
                available_providers = preferred_available
        
        # Apply load balancing strategy
        if self.load_balancing_strategy == LoadBalancingStrategy.PRIORITY:
            return max(available_providers, key=lambda p: self.providers[p].priority)
        
        elif self.load_balancing_strategy == LoadBalancingStrategy.FASTEST:
            return min(
                available_providers,
                key=lambda p: self.providers[p].average_response_time or float('inf')
            )
        
        elif self.load_balancing_strategy == LoadBalancingStrategy.LEAST_LOADED:
            return min(available_providers, key=lambda p: self.providers[p].current_requests)
        
        elif self.load_balancing_strategy == LoadBalancingStrategy.ROUND_ROBIN:
            selected = available_providers[self.round_robin_index % len(available_providers)]
            self.round_robin_index += 1
            return selected
        
        elif self.load_balancing_strategy == LoadBalancingStrategy.RANDOM:
            return random.choice(available_providers)
        
        else:
            return available_providers[0]  # Default fallback
    
    def _select_fallback_provider(self, failed_provider: str) -> Optional[str]:
        """Select a fallback provider when the primary fails"""
        available_providers = [
            name for name, info in self.providers.items()
            if (info.status == LLMStatus.AVAILABLE and 
                name in self.active_providers and 
                name != failed_provider)
        ]
        
        if not available_providers:
            return None
        
        # Select highest priority available provider
        return max(available_providers, key=lambda p: self.providers[p].priority)
    
    async def _generate_with_provider(self, provider_name: str, request: LLMRequest) -> LLMResponse:
        """Generate response using specific provider"""
        provider = self.active_providers[provider_name]
        provider_info = self.providers[provider_name]
        
        # Update current requests count
        provider_info.current_requests += 1
        provider_info.total_requests += 1
        
        start_time = time.time()
        
        try:
            # Prepare generation parameters
            kwargs = {}
            if request.max_tokens:
                kwargs['max_tokens'] = request.max_tokens
            if request.temperature is not None:
                kwargs['temperature'] = request.temperature
            
            # Generate response
            if hasattr(provider, 'generate'):
                raw_response = await asyncio.wait_for(
                    provider.generate(request.prompt, **kwargs),
                    timeout=request.timeout
                )
            elif hasattr(provider, 'ainvoke'):
                raw_response = await asyncio.wait_for(
                    provider.ainvoke(request.prompt, **kwargs),
                    timeout=request.timeout
                )
            else:
                raw_response = provider.invoke(request.prompt, **kwargs)
            
            response_time = time.time() - start_time
            content = str(raw_response).strip()
            
            # Update provider metrics
            provider_info.successful_requests += 1
            provider_info.last_request_time = time.time()
            provider_info.average_response_time = (
                (provider_info.average_response_time * (provider_info.successful_requests - 1) + response_time)
                / provider_info.successful_requests
            )
            
            # Estimate token usage and cost
            token_usage = self._estimate_token_usage(request.prompt, content)
            cost_estimate = self._calculate_cost(token_usage, provider_info.cost_per_token)
            
            return LLMResponse(
                content=content,
                provider_name=provider_name,
                model_name=provider_info.model_name,
                response_time=response_time,
                token_usage=token_usage,
                cost_estimate=cost_estimate
            )
            
        finally:
            provider_info.current_requests -= 1
    
    def _estimate_token_usage(self, prompt: str, response: str) -> Dict[str, int]:
        """Rough estimation of token usage (4 chars ≈ 1 token)"""
        prompt_tokens = len(prompt) // 4
        completion_tokens = len(response) // 4
        
        return {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens
        }
    
    def _calculate_cost(self, token_usage: Dict[str, int], cost_per_token: float) -> float:
        """Calculate estimated cost for the request"""
        return token_usage.get("total_tokens", 0) * cost_per_token
    
    def _generate_cache_key(self, request: LLMRequest) -> str:
        """Generate cache key for request"""
        import hashlib
        key_data = f"{request.prompt}:{request.max_tokens}:{request.temperature}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _get_cached_response(self, cache_key: str) -> Optional[LLMResponse]:
        """Get cached response if available and not expired"""
        if cache_key in self.response_cache:
            response, timestamp = self.response_cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                response.cached = True
                return response
            else:
                # Remove expired cache entry
                del self.response_cache[cache_key]
        
        return None
    
    def _cache_response(self, cache_key: str, response: LLMResponse):
        """Cache response"""
        self.response_cache[cache_key] = (response, time.time())
        
        # Clean old cache entries periodically
        if len(self.response_cache) % 100 == 0:
            self._clean_expired_cache()
    
    def _clean_expired_cache(self):
        """Remove expired cache entries"""
        current_time = time.time()
        expired_keys = [
            key for key, (_, timestamp) in self.response_cache.items()
            if current_time - timestamp > self.cache_ttl
        ]
        
        for key in expired_keys:
            del self.response_cache[key]
    
    async def _start_health_monitoring(self):
        """Start background health monitoring"""
        if self._health_check_task and not self._health_check_task.done():
            return
        
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        self.logger.info("llm_health_monitoring_started")
    
    async def _health_check_loop(self):
        """Background health check loop"""
        while True:
            try:
                await asyncio.sleep(self.health_check_interval)
                await self._perform_health_checks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("llm_health_check_error", error=str(e))
    
    async def _perform_health_checks(self):
        """Perform health checks on all providers"""
        for name, provider_info in self.providers.items():
            if name not in self.active_providers:
                continue
            
            try:
                provider = self.active_providers[name]
                is_healthy = await self._test_provider(provider)
                
                if is_healthy:
                    if provider_info.status != LLMStatus.AVAILABLE:
                        provider_info.status = LLMStatus.AVAILABLE
                        provider_info.last_error = None
                        self.logger.info("llm_provider_recovered", name=name)
                else:
                    if provider_info.status == LLMStatus.AVAILABLE:
                        provider_info.status = LLMStatus.ERROR
                        self.logger.warning("llm_provider_unhealthy", name=name)
                
            except Exception as e:
                provider_info.status = LLMStatus.ERROR
                provider_info.last_error = str(e)
    
    def set_load_balancing_strategy(self, strategy: LoadBalancingStrategy):
        """Set load balancing strategy"""
        self.load_balancing_strategy = strategy
        self.logger.info("load_balancing_strategy_changed", strategy=strategy.value)
    
    def get_provider_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all providers"""
        stats = {}
        for name, info in self.providers.items():
            stats[name] = {
                "status": info.status.value,
                "model_name": info.model_name,
                "priority": info.priority,
                "total_requests": info.total_requests,
                "successful_requests": info.successful_requests,
                "failed_requests": info.failed_requests,
                "success_rate": (info.successful_requests / info.total_requests * 100) if info.total_requests > 0 else 0,
                "average_response_time": info.average_response_time,
                "current_requests": info.current_requests,
                "last_error": info.last_error
            }
        
        return stats
    
    def get_global_stats(self) -> Dict[str, Any]:
        """Get global LLM manager statistics"""
        avg_response_time = (
            self.global_stats["total_response_time"] / self.global_stats["successful_requests"]
            if self.global_stats["successful_requests"] > 0 else 0
        )
        
        return {
            **self.global_stats,
            "average_response_time": avg_response_time,
            "success_rate": (
                self.global_stats["successful_requests"] / self.global_stats["total_requests"] * 100
                if self.global_stats["total_requests"] > 0 else 0
            ),
            "cache_hit_rate": (
                self.global_stats["cache_hits"] / 
                (self.global_stats["cache_hits"] + self.global_stats["cache_misses"]) * 100
                if (self.global_stats["cache_hits"] + self.global_stats["cache_misses"]) > 0 else 0
            ),
            "cached_responses": len(self.response_cache),
            "active_providers": len([p for p in self.providers.values() if p.status == LLMStatus.AVAILABLE])
        }
    
    async def shutdown(self):
        """Shutdown LLM manager"""
        self.logger.info("shutting_down_llm_manager")
        
        # Cancel health check task
        if self._health_check_task and not self._health_check_task.done():
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        # Clear providers and cache
        self.active_providers.clear()
        self.providers.clear()
        self.response_cache.clear()
        
        self.logger.info("llm_manager_shutdown_complete")