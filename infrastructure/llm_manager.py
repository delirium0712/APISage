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

        try:
            # Build the request parameters
            completion_params = {
                "model": request.model,
                "messages": [{"role": "user", "content": request.prompt}],
                "max_tokens": request.max_tokens,
                "temperature": request.temperature,
            }

            # Add response_format for structured outputs if provided
            # This uses the correct OpenAI Chat Completions API with response_format parameter
            if request.response_format:
                completion_params["response_format"] = request.response_format
                schema_props = (
                    request.response_format.get("json_schema", {})
                    .get("schema", {})
                    .get("properties", {})
                )
                logger.info(
                    "using_structured_output",
                    response_format_type=request.response_format.get("type"),
                    schema_name=request.response_format.get("json_schema", {}).get(
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
                model=response.model,
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
                model=request.model,
                has_response_format=bool(request.response_format),
            )
            return LLMResponse(
                content=f"LLM generation failed: {str(e)}",
                model=request.model,
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
