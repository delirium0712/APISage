"""
LiteLLM Provider Implementation
Optimized for GPU acceleration and fast response times
"""

import os
import asyncio
from typing import Optional, Dict, Any, List
import structlog
from dataclasses import dataclass
from enum import Enum

try:
    import litellm
    from litellm import completion, acompletion
    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False

try:
    import torch
    import transformers
    GPU_AVAILABLE = torch.cuda.is_available()
    if GPU_AVAILABLE:
        GPU_DEVICE = torch.cuda.get_device_name(0)
        GPU_MEMORY = torch.cuda.get_device_properties(0).total_memory / 1024**3  # GB
    else:
        GPU_DEVICE = "CPU"
        GPU_MEMORY = 0
except ImportError:
    GPU_AVAILABLE = False
    GPU_DEVICE = "CPU"
    GPU_MEMORY = 0


class LLMProvider(str, Enum):
    """Supported LLM providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OLLAMA = "ollama"
    AZURE = "azure"
    AWS_BEDROCK = "aws_bedrock"
    HUGGINGFACE = "huggingface"
    COHERE = "cohere"
    MISTRAL = "mistral"


@dataclass
class LLMConfig:
    """LLM configuration with performance optimizations"""
    provider: LLMProvider
    model: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    
    # Performance optimization settings
    max_tokens: int = 2048
    temperature: float = 0.1
    top_p: float = 0.9
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    
    # GPU acceleration settings
    use_gpu: bool = True
    gpu_memory_fraction: float = 0.8
    enable_fast_inference: bool = True
    
    # Response optimization
    stream: bool = False
    timeout: int = 30  # Reduced from default
    max_retries: int = 2  # Reduced for faster fallback
    
    # Batch processing
    batch_size: int = 1
    enable_batching: bool = False
    
    # Caching
    enable_cache: bool = True
    cache_ttl: int = 3600


class LiteLLMProvider:
    """High-performance LiteLLM provider with GPU acceleration"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.logger = structlog.get_logger(component=f"LLMProvider_{config.provider.value}")
        
        # Performance monitoring
        self.response_times = []
        self.total_requests = 0
        self.successful_requests = 0
        
        # Initialize GPU settings
        self._setup_gpu_acceleration()
        
        # Initialize LiteLLM
        self._initialize_litellm()
    
    def _setup_gpu_acceleration(self):
        """Setup GPU acceleration for optimal performance"""
        if GPU_AVAILABLE and self.config.use_gpu:
            try:
                # Set CUDA device
                os.environ["CUDA_VISIBLE_DEVICES"] = "0"
                
                # Optimize PyTorch for inference
                torch.backends.cudnn.benchmark = True
                torch.backends.cudnn.deterministic = False
                
                # Set memory fraction
                if hasattr(torch.cuda, 'set_per_process_memory_fraction'):
                    torch.cuda.set_per_process_memory_fraction(self.config.gpu_memory_fraction)
                
                self.logger.info("gpu_acceleration_enabled",
                               device=GPU_DEVICE,
                               memory_gb=GPU_MEMORY,
                               memory_fraction=self.config.gpu_memory_fraction)
                
            except Exception as e:
                self.logger.warning("gpu_setup_failed", error=str(e))
                self.config.use_gpu = False
        else:
            self.logger.info("gpu_not_available", using_cpu=True)
    
    def _initialize_litellm(self):
        """Initialize LiteLLM with performance optimizations"""
        if not LITELLM_AVAILABLE:
            raise ImportError("LiteLLM not available. Install with: pip install litellm")
        
        try:
            # Set environment variables for performance
            if self.config.api_key:
                os.environ[f"{self.config.provider.value.upper()}_API_KEY"] = self.config.api_key
            
            if self.config.base_url:
                os.environ[f"{self.config.provider.value.upper()}_BASE_URL"] = self.config.base_url
            
            # LiteLLM performance settings
            litellm.set_verbose = False  # Reduce logging overhead
            litellm.drop_params = True   # Drop unused parameters
            
            # Enable caching if available
            if self.config.enable_cache:
                try:
                    litellm.cache = litellm.Cache(
                        type="redis",
                        host="localhost",
                        port=6379,
                        password=None
                    )
                    self.logger.info("caching_enabled", type="redis")
                except Exception as e:
                    self.logger.warning("caching_failed", error=str(e))
                    self.config.enable_cache = False
            
            self.logger.info("litellm_initialized",
                           provider=self.config.provider.value,
                           model=self.config.model,
                           gpu_enabled=self.config.use_gpu,
                           caching_enabled=self.config.enable_cache)
            
        except Exception as e:
            self.logger.error("litellm_initialization_failed", error=str(e))
            raise
    
    async def generate(self, 
                      prompt: str, 
                      max_tokens: Optional[int] = None,
                      temperature: Optional[float] = None,
                      **kwargs) -> str:
        """Generate response with performance optimizations"""
        
        start_time = asyncio.get_event_loop().time()
        self.total_requests += 1
        
        try:
            # Use config defaults if not specified
            max_tokens = max_tokens or self.config.max_tokens
            temperature = temperature or self.config.temperature
            
            # Prepare completion parameters with performance optimizations
            completion_params = {
                "model": self.config.model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": temperature,
                "top_p": self.config.top_p,
                "frequency_penalty": self.config.frequency_penalty,
                "presence_penalty": self.config.presence_penalty,
                "stream": self.config.stream,
                "timeout": self.config.timeout,
                "max_retries": self.config.max_retries,
                **kwargs
            }
            
            # Add provider-specific optimizations
            if self.config.provider == LLMProvider.OLLAMA:
                completion_params.update({
                    "num_ctx": 4096,  # Optimize context window
                    "num_gpu": 1 if self.config.use_gpu else 0,
                    "num_thread": 8,  # Optimize CPU threading
                    "repeat_penalty": 1.1,
                    "top_k": 40
                })
            
            elif self.config.provider == LLMProvider.HUGGINGFACE:
                completion_params.update({
                    "device": "cuda" if self.config.use_gpu else "cpu",
                    "torch_dtype": "auto",
                    "low_cpu_mem_usage": True
                })
            
            # Execute with timeout and retry logic
            response = await asyncio.wait_for(
                self._execute_completion(completion_params),
                timeout=self.config.timeout
            )
            
            # Extract response content
            if hasattr(response, 'choices') and response.choices:
                content = response.choices[0].message.content
            else:
                content = str(response)
            
            # Record performance metrics
            response_time = asyncio.get_event_loop().time() - start_time
            self.response_times.append(response_time)
            self.successful_requests += 1
            
            self.logger.info("generation_completed",
                           response_time=response_time,
                           tokens_generated=len(content.split()),
                           provider=self.config.provider.value,
                           model=self.config.model)
            
            return content
            
        except asyncio.TimeoutError:
            self.logger.error("generation_timeout",
                            timeout=self.config.timeout,
                            prompt_length=len(prompt))
            raise TimeoutError(f"LLM generation timed out after {self.config.timeout}s")
            
        except Exception as e:
            self.logger.error("generation_failed",
                            error=str(e),
                            provider=self.config.provider.value,
                            model=self.config.model)
            raise
    
    async def _execute_completion(self, params: Dict[str, Any]):
        """Execute completion with error handling and fallbacks"""
        
        for attempt in range(self.config.max_retries + 1):
            try:
                if self.config.provider == LLMProvider.OLLAMA:
                    # Use async completion for Ollama
                    return await acompletion(**params)
                else:
                    # Use regular completion for other providers
                    return completion(**params)
                    
            except Exception as e:
                if attempt == self.config.max_retries:
                    raise
                
                self.logger.warning("completion_retry",
                                  attempt=attempt + 1,
                                  max_retries=self.config.max_retries,
                                  error=str(e))
                
                # Exponential backoff
                await asyncio.sleep(2 ** attempt)
    
    async def generate_batch(self, prompts: List[str], **kwargs) -> List[str]:
        """Generate responses for multiple prompts in batch for better performance"""
        
        if not self.config.enable_batching:
            # Fallback to sequential processing
            return [await self.generate(prompt, **kwargs) for prompt in prompts]
        
        try:
            # Prepare batch parameters
            batch_params = {
                "model": self.config.model,
                "messages": [[{"role": "user", "content": prompt}] for prompt in prompts],
                "max_tokens": kwargs.get('max_tokens', self.config.max_tokens),
                "temperature": kwargs.get('temperature', self.config.temperature),
                "timeout": self.config.timeout * 2,  # Longer timeout for batch
                **kwargs
            }
            
            # Execute batch completion
            responses = await asyncio.wait_for(
                acompletion(**batch_params),
                timeout=batch_params["timeout"]
            )
            
            # Extract content from batch response
            if hasattr(responses, 'choices'):
                return [choice.message.content for choice in responses.choices]
            else:
                return [str(response) for response in responses]
                
        except Exception as e:
            self.logger.error("batch_generation_failed", error=str(e))
            # Fallback to sequential processing
            return [await self.generate(prompt, **kwargs) for prompt in prompts]
    
    async def health_check(self) -> bool:
        """Check if the LLM provider is healthy and responsive"""
        try:
            test_prompt = "Hello, this is a health check. Please respond with 'OK'."
            response = await asyncio.wait_for(
                self.generate(test_prompt, max_tokens=10),
                timeout=10
            )
            
            is_healthy = "ok" in response.lower() or len(response.strip()) > 0
            self.logger.info("health_check_completed",
                           status="healthy" if is_healthy else "unhealthy",
                           response=response[:100])
            
            return is_healthy
            
        except Exception as e:
            self.logger.error("health_check_failed", error=str(e))
            return False
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        if not self.response_times:
            return {"error": "No requests processed yet"}
        
        avg_response_time = sum(self.response_times) / len(self.response_times)
        min_response_time = min(self.response_times)
        max_response_time = max(self.response_times)
        
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "success_rate": self.successful_requests / self.total_requests if self.total_requests > 0 else 0,
            "average_response_time": avg_response_time,
            "min_response_time": min_response_time,
            "max_response_time": max_response_time,
            "gpu_enabled": self.config.use_gpu,
            "gpu_device": GPU_DEVICE,
            "gpu_memory_gb": GPU_MEMORY,
            "caching_enabled": self.config.enable_cache,
            "provider": self.config.provider.value,
            "model": self.config.model
        }
    
    def optimize_for_speed(self):
        """Apply additional speed optimizations"""
        try:
            # Reduce token limits for faster responses
            self.config.max_tokens = min(self.config.max_tokens, 1024)
            
            # Lower temperature for more focused responses
            self.config.temperature = min(self.config.temperature, 0.05)
            
            # Enable streaming for faster first token
            self.config.stream = True
            
            # Reduce timeout for faster fallback
            self.config.timeout = 15
            
            self.logger.info("speed_optimizations_applied",
                           max_tokens=self.config.max_tokens,
                           temperature=self.config.temperature,
                           timeout=self.config.timeout)
            
        except Exception as e:
            self.logger.warning("speed_optimization_failed", error=str(e))
    
    def optimize_for_quality(self):
        """Apply quality optimizations (may be slower)"""
        try:
            # Increase token limits for better responses
            self.config.max_tokens = max(self.config.max_tokens, 2048)
            
            # Higher temperature for more creative responses
            self.config.temperature = max(self.config.temperature, 0.3)
            
            # Increase timeout for complex reasoning
            self.config.timeout = 60
            
            self.logger.info("quality_optimizations_applied",
                           max_tokens=self.config.max_tokens,
                           temperature=self.config.temperature,
                           timeout=self.config.timeout)
            
        except Exception as e:
            self.logger.warning("quality_optimization_failed", error=str(e))