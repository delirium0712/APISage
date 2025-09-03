"""
Simple LLM Manager for APISage
Clean, focused implementation for LLM integration
"""

import asyncio
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

import structlog

try:
    import openai
    from openai import AsyncOpenAI

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

logger = structlog.get_logger()


@dataclass
class LLMRequest:
    """Simple LLM request structure"""

    prompt: str
    max_tokens: int = 4000
    temperature: float = 0.3
    model: str = "gpt-4o-mini"
    response_format: Optional[Dict[str, Any]] = None  # For structured outputs


class ModelConfig:
    """Configuration for different model types"""

    # O1 models don't support temperature parameter
    O1_MODELS = {"o1", "o1-mini", "o1-preview"}

    # Default configurations for different model types
    DEFAULTS = {
        "gpt-4o": {"max_tokens": 4000, "temperature": 0.3},
        "gpt-4o-mini": {"max_tokens": 4000, "temperature": 0.3},
        "o1": {"max_tokens": 10000, "temperature": None},  # O1 doesn't use temperature
        "o1-mini": {"max_tokens": 8000, "temperature": None},
        "o1-preview": {"max_tokens": 10000, "temperature": None},
        "gpt-3.5-turbo": {"max_tokens": 4000, "temperature": 0.3},
    }

    @classmethod
    def is_o1_model(cls, model: str) -> bool:
        """Check if model is an O1 reasoning model"""
        return model in cls.O1_MODELS

    @classmethod
    def get_model_defaults(cls, model: str) -> Dict[str, Any]:
        """Get default configuration for a model"""
        return cls.DEFAULTS.get(model, cls.DEFAULTS["gpt-4o-mini"])


@dataclass
class LLMResponse:
    """Simple LLM response structure"""

    content: str
    model: str
    usage: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class SimpleLLMManager:
    """
    Simple LLM manager for basic OpenAI integration
    Clean, focused implementation without complex infrastructure
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")

        # Validate and set default model
        if not self._is_valid_model(model):
            logger.warning(f"Invalid model '{model}', falling back to gpt-4o-mini")
            model = "gpt-4o-mini"

        self.default_model = model
        self.client: Optional[AsyncOpenAI] = None

        if not self.api_key:
            logger.warning(
                "no_openai_api_key",
                message="OpenAI API key not provided - LLM functionality will be limited",
            )

        if OPENAI_AVAILABLE and self.api_key:
            self.client = AsyncOpenAI(api_key=self.api_key)
            logger.info("llm_manager_initialized", model=self.default_model)
        else:
            logger.warning(
                "llm_manager_disabled", reason="OpenAI not available or API key missing"
            )

    def _is_valid_model(self, model: str) -> bool:
        """Validate if the model is supported"""
        supported_models = set(ModelConfig.DEFAULTS.keys())
        return model in supported_models

    def optimize_request(self, request: LLMRequest) -> LLMRequest:
        """
        Optimize request parameters based on model type
        Applies optimal defaults for o1 reasoning models
        """
        if not isinstance(request, LLMRequest):
            return request

        # Get model defaults
        defaults = ModelConfig.get_model_defaults(request.model)

        # Create optimized request with model-specific defaults
        optimized = LLMRequest(
            prompt=request.prompt,
            model=request.model,
            max_tokens=request.max_tokens or defaults["max_tokens"],
            temperature=request.temperature if defaults["temperature"] is not None else 0.0,
            response_format=request.response_format
        )

        # Log optimization for o1 models
        if ModelConfig.is_o1_model(request.model):
            logger.info(
                "optimizing_o1_request",
                model=request.model,
                max_tokens=optimized.max_tokens,
                temperature="N/A (o1 model)"
            )

        return optimized

    async def generate(self, request: LLMRequest) -> Optional[LLMResponse]:
        """
        Generate response from LLM with optional structured output
        """
        if not self.client:
            return LLMResponse(
                content="LLM not available - please set OPENAI_API_KEY",
                model=request.model,
                error="No API key or OpenAI client",
            )

        # Validate model before proceeding
        if not self._is_valid_model(request.model):
            return LLMResponse(
                content=f"Unsupported model: {request.model}",
                model=request.model,
                error=f"Model {request.model} is not supported",
            )

        # Optimize request parameters for the specific model
        optimized_request = self.optimize_request(request)

        try:
            # Build the request parameters using optimized request
            completion_params = {
                "model": optimized_request.model,
                "messages": [{"role": "user", "content": optimized_request.prompt}],
                "max_tokens": optimized_request.max_tokens,
            }

            # O1 models don't support temperature parameter
            if not ModelConfig.is_o1_model(optimized_request.model):
                completion_params["temperature"] = optimized_request.temperature

            # Add response_format for structured outputs if provided
            # This uses the correct OpenAI Chat Completions API with response_format parameter
            if optimized_request.response_format:
                completion_params["response_format"] = optimized_request.response_format
                schema_props = (
                    optimized_request.response_format.get("json_schema", {})
                    .get("schema", {})
                    .get("properties", {})
                )
                logger.info(
                    "using_structured_output",
                    response_format_type=optimized_request.response_format.get("type"),
                    schema_name=optimized_request.response_format.get("json_schema", {}).get(
                        "name"
                    ),
                    schema_properties=list(schema_props.keys()) if schema_props else [],
                )
            else:
                logger.debug("no_structured_output_format")

            # Make the API call to /v1/chat/completions (the correct endpoint)
            response = await self.client.chat.completions.create(**completion_params)

            content = response.choices[0].message.content if response.choices else ""

            return LLMResponse(
                content=content,
                model=response.model or optimized_request.model,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens
                    if response.usage
                    else 0,
                    "completion_tokens": response.usage.completion_tokens
                    if response.usage
                    else 0,
                    "total_tokens": response.usage.total_tokens
                    if response.usage
                    else 0,
                },
            )

        except Exception as e:
            logger.error(
                "llm_generation_failed",
                error=str(e),
                model=optimized_request.model,
                has_response_format=bool(optimized_request.response_format),
            )
            return LLMResponse(
                content=f"LLM generation failed: {str(e)}",
                model=optimized_request.model,
                error=str(e),
            )

    def is_available(self) -> bool:
        """Check if LLM is available"""
        return self.client is not None

    async def generate_response(self, request: LLMRequest) -> Optional[str]:
        """
        Generate response from LLM and return content string
        Convenience method that wraps generate() and returns just the content
        """
        response = await self.generate(request)
        if response and not response.error:
            return response.content
        return None

    def refresh_api_key(self) -> bool:
        """Refresh the API key and client after environment variable change"""
        try:
            new_api_key = os.getenv("OPENAI_API_KEY")
            if new_api_key:
                # Always refresh the client, even if key appears the same
                self.api_key = new_api_key
                if OPENAI_AVAILABLE:
                    self.client = AsyncOpenAI(api_key=self.api_key)
                    logger.info(
                        "llm_manager_refreshed",
                        model=self.default_model,
                        api_key_prefix=self.api_key[:10] + "...",
                    )
                    return True
                else:
                    logger.warning(
                        "llm_manager_refresh_failed", reason="OpenAI not available"
                    )
                    return False
            else:
                self.api_key = None
                self.client = None
                logger.warning(
                    "llm_manager_disabled", reason="No API key in environment"
                )
                return False
        except Exception as e:
            logger.error("llm_manager_refresh_error", error=str(e))
            return False
