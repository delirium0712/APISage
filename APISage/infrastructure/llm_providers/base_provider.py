"""
Base LLM provider interface
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, List, Optional, AsyncGenerator
from dataclasses import dataclass
import structlog

logger = structlog.get_logger()


class LLMProvider(Enum):
    """Supported LLM providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OLLAMA = "ollama"
    AZURE_OPENAI = "azure_openai"
    AWS_BEDROCK = "aws_bedrock"
    HUGGINGFACE = "huggingface"
    COHERE = "cohere"
    MISTRAL = "mistral"


@dataclass
class LLMConfig:
    """LLM configuration"""
    provider: LLMProvider
    model: str
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2000
    timeout: int = 60
    streaming: bool = False
    additional_config: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.additional_config is None:
            self.additional_config = {}


@dataclass
class LLMResponse:
    """LLM response container"""
    content: str
    model: str
    provider: str
    usage: Dict[str, int]
    metadata: Dict[str, Any]


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.logger = structlog.get_logger(component=f"{self.__class__.__name__}")
        self._client = None
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the provider"""
        pass
    
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate response from prompt"""
        pass
    
    @abstractmethod
    async def stream_generate(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        """Stream generate response from prompt"""
        pass
    
    @abstractmethod
    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available"""
        pass
    
    async def health_check(self) -> bool:
        """Perform health check"""
        try:
            test_response = await self.generate("Hello", max_tokens=5)
            return bool(test_response.content)
        except Exception as e:
            self.logger.error("Health check failed", error=str(e))
            return False
    
    def get_provider_info(self) -> Dict[str, Any]:
        """Get provider information"""
        return {
            "provider": self.config.provider.value,
            "model": self.config.model,
            "available": self.is_available(),
            "streaming": self.config.streaming
        }