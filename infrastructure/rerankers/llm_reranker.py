"""
LLM-based Reranker
Uses language models to semantically rerank search results
"""

import json
import re
from typing import List, Dict, Any, Optional
import structlog

from .base_reranker import BaseReranker, RerankerConfig
from ..vector_stores.base_store import SearchResult


class LLMReranker(BaseReranker):
    """LLM-based reranker using language models for semantic understanding"""
    
    def __init__(self, config: RerankerConfig):
        super().__init__(config)
        self.llm_provider = None
        self.prompt_templates = self._initialize_prompt_templates()
        
    def _initialize_prompt_templates(self) -> Dict[str, str]:
        """Initialize different prompt templates for different use cases"""
        return {
            "default": """You are an expert at evaluating the relevance of documents to user questions. Your task is to rerank a list of documents based on their relevance to a specific question.

User Question: {query}

Documents to evaluate:
{documents}

Instructions:
1. Analyze each document's relevance to the user question
2. Consider semantic meaning, not just keyword matches
3. Rank the documents from most relevant to least relevant
4. Return exactly {top_k} documents in order of relevance

Output Format:
Return a JSON array with document IDs in order of relevance:
["doc_id_1", "doc_id_2", "doc_id_3", ...]

Only return the JSON array, no additional text.""",
            
            "api_documentation": """You are an expert at evaluating API documentation relevance. Your task is to rerank API documentation documents based on their relevance to a specific question.

User Question: {query}

API Documentation Documents:
{documents}

Evaluation Criteria:
1. **Technical Accuracy**: How well does the document answer the technical question?
2. **Endpoint Relevance**: Does it contain relevant API endpoints or methods?
3. **Code Examples**: Does it provide useful code examples or implementation details?
4. **Context Completeness**: Does it provide enough context to solve the problem?

Instructions:
1. Analyze each document's relevance to the user's API question
2. Consider the technical depth and practical usefulness
3. Rank the documents from most relevant to least relevant
4. Return exactly {top_k} documents in order of relevance

Output Format:
Return a JSON array with document IDs in order of relevance:
["doc_id_1", "doc_id_2", "doc_id_3", ...]

Only return the JSON array, no additional text.""",
            
            "technical_support": """You are an expert technical support specialist. Your task is to rerank technical documentation based on how well it addresses a user's technical problem.

User Question: {query}

Technical Documents:
{documents}

Evaluation Criteria:
1. **Problem-Solution Match**: Does the document directly address the user's problem?
2. **Step-by-Step Guidance**: Does it provide clear, actionable steps?
3. **Troubleshooting**: Does it help identify and resolve common issues?
4. **Technical Depth**: Is the technical level appropriate for the question?

Instructions:
1. Analyze each document's ability to solve the user's technical problem
2. Consider practical applicability and clarity of instructions
3. Rank the documents from most helpful to least helpful
4. Return exactly {top_k} documents in order of helpfulness

Output Format:
Return a JSON array with document IDs in order of helpfulness:
["doc_id_1", "doc_id_2", "doc_id_3", ...]

Only return the JSON array, no additional text."""
        }
    
    async def initialize(self, llm_provider_factory=None):
        """Initialize the LLM provider"""
        try:
            # For now, we'll skip LLM initialization to avoid import issues
            # In a real implementation, this would initialize the LLM provider
            self.logger.info("llm_reranker_initialized", 
                           provider=self.config.llm_provider,
                           model=self.config.llm_model,
                           note="LLM provider not initialized - using fallback mode")
        except Exception as e:
            self.logger.error("llm_reranker_init_failed", error=str(e))
            raise
    
    async def rerank(self, 
                    query: str, 
                    results: List[SearchResult], 
                    context: Optional[Dict[str, Any]] = None) -> List[SearchResult]:
        """Rerank results using LLM-based semantic understanding"""
        
        # Since LLM provider is not available, return original results
        # This is a fallback mode for testing
        self.logger.info("llm_reranker_fallback_mode",
                        query=query,
                        results_count=len(results),
                        note="LLM provider not available, returning original results")
        
        return results
    
    def get_reranker_info(self) -> Dict[str, Any]:
        """Get information about the LLM reranker"""
        info = super().get_reranker_info()
        info.update({
            "reranker_type": "LLM-based",
            "llm_provider": self.config.llm_provider,
            "llm_model": self.config.llm_model,
            "prompt_templates": list(self.prompt_templates.keys()),
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "max_retries": self.config.max_retries,
            "llm_initialized": self.llm_provider is not None,
            "note": "Currently in fallback mode - LLM provider not available"
        })
        return info
