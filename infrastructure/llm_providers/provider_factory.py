"""
LLM Provider Factory
"""

import os
from typing import Dict, Any, List, Optional
import structlog

from .base_provider import BaseLLMProvider, LLMProvider
from .openai_direct_provider import DirectOpenAIProvider, LLMConfig

logger = structlog.get_logger()


class LLMProviderFactory:
    """Factory for creating LLM providers"""
    
    @staticmethod
    def create_provider(config: LLMConfig) -> BaseLLMProvider:
        """Create LLM provider based on configuration"""
        
        provider_type = config.provider
        
        # Use direct OpenAI provider for OpenAI, skip others for now
        if provider_type.value == "openai":
            return DirectOpenAIProvider(config)
        else:
            raise ValueError(f"Provider {provider_type.value} not supported yet. Only OpenAI is supported.")
    
    @staticmethod
    def create_from_config(provider_configs: Dict[str, Dict[str, Any]]) -> Dict[str, BaseLLMProvider]:
        """Create multiple providers from configuration"""
        providers = {}
        
        for name, config_dict in provider_configs.items():
            try:
                # Convert config dict to LLMConfig
                provider_enum = LLMProvider(config_dict.get('provider', 'openai'))
                
                config = LLMConfig(
                    provider=provider_enum,
                    model=config_dict.get('model', 'gpt-4o-mini'),
                    api_key=config_dict.get('api_key') or os.getenv(f"{provider_enum.value.upper()}_API_KEY"),
                    base_url=config_dict.get('api_base') or config_dict.get('base_url'),
                    temperature=config_dict.get('temperature', 0.7),
                    max_tokens=config_dict.get('max_tokens', 2000),
                    timeout=config_dict.get('timeout', 60),
                    stream=config_dict.get('streaming', False)
                )
                
                provider = LLMProviderFactory.create_provider(config)
                providers[name] = provider
                
                logger.info("Created LLM provider", 
                          name=name, 
                          provider=provider_enum.value,
                          model=config.model)
                
            except Exception as e:
                logger.error("Failed to create LLM provider", 
                           name=name, 
                           error=str(e))
                continue
        
        return providers
    
    @staticmethod
    def get_default_configs() -> Dict[str, Dict[str, Any]]:
        """Get default provider configurations"""
        return {
            "openai": {
                "provider": "openai",
                "model": "gpt-4o-mini",
                "api_key": os.getenv("OPENAI_API_KEY"),
                "temperature": 0.7,
                "max_tokens": 2000
            },
            "claude": {
                "provider": "anthropic", 
                "model": "claude-3-sonnet-20240229",
                "api_key": os.getenv("ANTHROPIC_API_KEY"),
                "temperature": 0.7,
                "max_tokens": 2000
            },
            "gemini": {
                "provider": "google",
                "model": "gemini-pro",
                "api_key": os.getenv("GEMINI_API_KEY"),
                "temperature": 0.7,
                "max_tokens": 2000
            },
            "ollama": {
                "provider": "ollama",
                "model": "llama3:8b",
                "api_base": os.getenv("OLLAMA_API_BASE", "http://localhost:11434"),
                "temperature": 0.7,
                "max_tokens": 2000
            }
        }
    
    @staticmethod
    async def initialize_providers(providers: Dict[str, BaseLLMProvider]) -> Dict[str, BaseLLMProvider]:
        """Initialize all providers and return available ones"""
        available_providers = {}
        
        for name, provider in providers.items():
            try:
                if await provider.initialize():
                    available_providers[name] = provider
                    logger.info("Provider initialized successfully", name=name)
                else:
                    logger.warning("Provider initialization failed", name=name)
            except Exception as e:
                logger.error("Provider initialization error", name=name, error=str(e))
        
        return available_providers


class MultiLLMManager:
    """Manager for multiple LLM providers with fallback support"""
    
    def __init__(self, provider_configs: Dict[str, Dict[str, Any]], primary_provider: str = None):
        self.providers = LLMProviderFactory.create_from_config(provider_configs)
        self.primary_provider = primary_provider or list(self.providers.keys())[0] if self.providers else None
        self.fallback_order = list(self.providers.keys())
        self.logger = structlog.get_logger(component="MultiLLMManager")
    
    async def initialize(self) -> bool:
        """Initialize all providers"""
        self.providers = await LLMProviderFactory.initialize_providers(self.providers)
        
        if not self.providers:
            self.logger.error("No LLM providers available")
            return False
        
        # Update primary provider if it's not available
        if self.primary_provider not in self.providers:
            self.primary_provider = list(self.providers.keys())[0]
            self.logger.warning("Primary provider not available, using fallback", 
                              primary=self.primary_provider)
        
        self.logger.info("MultiLLM manager initialized", 
                        providers=list(self.providers.keys()),
                        primary=self.primary_provider)
        return True
    
    async def generate(self, prompt: str, provider_name: str = None, **kwargs) -> Any:
        """Generate response with fallback support"""
        
        # Determine provider order
        if provider_name and provider_name in self.providers:
            provider_order = [provider_name]
        else:
            provider_order = [self.primary_provider] + [p for p in self.fallback_order if p != self.primary_provider]
        
        last_error = None
        
        for provider_name in provider_order:
            if provider_name not in self.providers:
                continue
            
            try:
                provider = self.providers[provider_name]
                response = await provider.generate(prompt, **kwargs)
                
                self.logger.info("Generation successful", provider=provider_name)
                return response
                
            except Exception as e:
                last_error = e
                self.logger.warning("Provider failed, trying fallback", 
                                  provider=provider_name, 
                                  error=str(e))
                continue
        
        # All providers failed
        self.logger.error("All LLM providers failed", error=str(last_error))
        raise RuntimeError(f"All LLM providers failed. Last error: {last_error}")
    
    async def stream_generate(self, prompt: str, provider_name: str = None, **kwargs):
        """Stream generate with fallback support"""
        
        # Use primary provider for streaming (fallback is complex for streaming)
        target_provider = provider_name or self.primary_provider
        
        if target_provider not in self.providers:
            raise ValueError(f"Provider {target_provider} not available")
        
        provider = self.providers[target_provider]
        async for chunk in provider.stream_generate(prompt, **kwargs):
            yield chunk
    
    def get_available_providers(self) -> List[str]:
        """Get list of available provider names"""
        return list(self.providers.keys())
    
    def get_provider_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all providers"""
        return {name: provider.get_provider_info() for name, provider in self.providers.items()}
    
    def set_primary_provider(self, provider_name: str) -> bool:
        """Set primary provider"""
        if provider_name in self.providers:
            self.primary_provider = provider_name
            self.logger.info("Primary provider changed", provider=provider_name)
            return True
        return False