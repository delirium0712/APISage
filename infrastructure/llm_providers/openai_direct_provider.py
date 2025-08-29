"""
Direct OpenAI Provider Implementation
Using the openai library directly without LiteLLM
"""

import os
import asyncio
from typing import Optional, Dict, Any, List
import structlog
from dataclasses import dataclass
from enum import Enum

try:
    import openai
    from openai import OpenAI, AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class LLMProvider(str, Enum):
    """Supported LLM providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OLLAMA = "ollama"


@dataclass
class LLMConfig:
    """LLM configuration for direct OpenAI integration"""
    provider: LLMProvider
    model: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    
    # OpenAI-specific settings
    max_tokens: int = 2048
    temperature: float = 0.7
    timeout: int = 30


class DirectOpenAIProvider:
    """Direct OpenAI provider using the openai library"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.logger = structlog.get_logger(component=f"DirectOpenAI_{config.provider.value}")
        
        # Performance monitoring
        self.response_times = []
        self.total_requests = 0
        self.successful_requests = 0
        
        # Initialize OpenAI client
        self._initialize_openai()
    
    def _initialize_openai(self):
        """Initialize OpenAI client"""
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI library not available. Install with: pip install openai")
        
        try:
            # Set API key
            api_key = self.config.api_key or os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OpenAI API key is required")
            
            # Initialize sync and async clients
            self.client = OpenAI(
                api_key=api_key,
                timeout=self.config.timeout
            )
            self.async_client = AsyncOpenAI(
                api_key=api_key,
                timeout=self.config.timeout
            )
            
            self.logger.info("openai_client_initialized",
                           model=self.config.model,
                           timeout=self.config.timeout)
            
        except Exception as e:
            self.logger.error("openai_initialization_failed", error=str(e))
            raise
    
    async def initialize(self) -> bool:
        """Initialize the provider - called by the factory"""
        try:
            return OPENAI_AVAILABLE and hasattr(self, 'client')
        except Exception as e:
            self.logger.error("provider_initialization_failed", error=str(e))
            return False
    
    def is_available(self) -> bool:
        """Check if provider is available"""
        return OPENAI_AVAILABLE and hasattr(self, 'client')
    
    async def generate(self, 
                      prompt: str, 
                      max_tokens: Optional[int] = None,
                      temperature: Optional[float] = None,
                      **kwargs) -> str:
        """Generate response using OpenAI API"""
        
        start_time = asyncio.get_event_loop().time()
        self.total_requests += 1
        
        try:
            # Use config defaults if not specified
            max_tokens = max_tokens or self.config.max_tokens
            temperature = temperature or self.config.temperature
            
            # Prepare messages
            messages = [{"role": "user", "content": prompt}]
            
            self.logger.info("generating_response",
                           model=self.config.model,
                           max_tokens=max_tokens,
                           temperature=temperature)
            
            # Make API call
            response = await self.async_client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )
            
            # Extract content
            if response.choices and len(response.choices) > 0:
                content = response.choices[0].message.content
                
                # Update stats
                end_time = asyncio.get_event_loop().time()
                response_time = end_time - start_time
                self.response_times.append(response_time)
                self.successful_requests += 1
                
                self.logger.info("response_generated",
                               response_time=response_time,
                               content_length=len(content) if content else 0)
                
                return content or ""
            else:
                self.logger.error("no_choices_in_response")
                return ""
                
        except Exception as e:
            end_time = asyncio.get_event_loop().time()
            response_time = end_time - start_time
            self.logger.error("generation_failed",
                            error=str(e),
                            response_time=response_time,
                            model=self.config.model)
            raise
    
    async def stream_generate(self, prompt: str, **kwargs) -> str:
        """Stream generate response from prompt"""
        # For now, just return the regular generate response
        # TODO: Implement proper streaming
        return await self.generate(prompt, **kwargs)
    
    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts"""
        try:
            response = await self.async_client.embeddings.create(
                model="text-embedding-3-small",
                input=texts
            )
            
            embeddings = []
            for data in response.data:
                embeddings.append(data.embedding)
            
            return embeddings
            
        except Exception as e:
            self.logger.error("embedding_failed", error=str(e))
            # Return placeholder embeddings
            return [[0.0] * 1536 for _ in texts]
    
    async def health_check(self) -> bool:
        """Check if the provider is healthy and responsive"""
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
            "provider": self.config.provider.value,
            "model": self.config.model
        }
