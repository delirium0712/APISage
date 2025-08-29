"""
Reranker Factory
Creates and manages different reranking strategies
"""

from typing import Dict, List, Optional, Any
import structlog

from .base_reranker import BaseReranker, RerankerConfig
from .llm_reranker import LLMReranker
from .semantic_reranker import SemanticReranker
from .api_docs_reranker import APIDocsReranker


class RerankerFactory:
    """Factory for creating and managing rerankers"""
    
    def __init__(self):
        self.logger = structlog.get_logger(component="RerankerFactory")
        self.rerankers: Dict[str, BaseReranker] = {}
        self.reranker_configs: Dict[str, RerankerConfig] = {}
        
    def create_reranker(self, 
                       reranker_type: str, 
                       config: RerankerConfig,
                       **kwargs) -> BaseReranker:
        """Create a reranker of the specified type"""
        
        try:
            if reranker_type == "llm":
                reranker = LLMReranker(config)
            elif reranker_type == "semantic":
                reranker = SemanticReranker(config)
            elif reranker_type == "api_docs":
                reranker = APIDocsReranker(config)
            else:
                raise ValueError(f"Unknown reranker type: {reranker_type}")
            
            # Store the reranker
            self.rerankers[config.name] = reranker
            self.reranker_configs[config.name] = config
            
            self.logger.info("reranker_created",
                           type=reranker_type,
                           name=config.name,
                           enabled=config.enabled)
            
            return reranker
            
        except Exception as e:
            self.logger.error("reranker_creation_failed",
                            type=reranker_type,
                            name=config.name,
                            error=str(e))
            raise
    
    def get_reranker(self, name: str) -> Optional[BaseReranker]:
        """Get a reranker by name"""
        return self.rerankers.get(name)
    
    def get_all_rerankers(self) -> Dict[str, BaseReranker]:
        """Get all created rerankers"""
        return self.rerankers.copy()
    
    def get_enabled_rerankers(self) -> List[BaseReranker]:
        """Get all enabled rerankers"""
        return [reranker for reranker in self.rerankers.values() if reranker.is_enabled()]
    
    def remove_reranker(self, name: str) -> bool:
        """Remove a reranker by name"""
        if name in self.rerankers:
            del self.rerankers[name]
            if name in self.reranker_configs:
                del self.reranker_configs[name]
            self.logger.info("reranker_removed", name=name)
            return True
        return False
    
    def clear_all_rerankers(self):
        """Clear all rerankers"""
        self.rerankers.clear()
        self.reranker_configs.clear()
        self.logger.info("all_rerankers_cleared")
    
    def get_reranker_info(self) -> Dict[str, Any]:
        """Get information about all rerankers"""
        info = {
            "total_rerankers": len(self.rerankers),
            "enabled_rerankers": len(self.get_enabled_rerankers()),
            "rerankers": {}
        }
        
        for name, reranker in self.rerankers.items():
            info["rerankers"][name] = {
                "type": reranker.__class__.__name__,
                "enabled": reranker.is_enabled(),
                "config": self.reranker_configs.get(name, {}),
                "info": reranker.get_reranker_info()
            }
        
        return info
    
    def create_default_configs(self) -> Dict[str, RerankerConfig]:
        """Create default configurations for common reranker types"""
        
        default_configs = {
            "llm_default": RerankerConfig(
                name="llm_default",
                reranker_type="llm",
                enabled=True,
                top_k=10,
                threshold=0.0,
                max_tokens=4000,
                temperature=0.1,
                llm_model="gpt-3.5-turbo",
                llm_provider="openai"
            ),
            
            "llm_api_docs": RerankerConfig(
                name="llm_api_docs",
                reranker_type="llm",
                enabled=True,
                top_k=10,
                threshold=0.0,
                max_tokens=4000,
                temperature=0.1,
                llm_model="gpt-3.5-turbo",
                llm_provider="openai",
                prompt_template="api_documentation"
            ),
            
            "semantic_default": RerankerConfig(
                name="semantic_default",
                reranker_type="semantic",
                enabled=True,
                top_k=10,
                threshold=0.7,
                semantic_similarity_threshold=0.7,
                context_window_size=512,
                cross_encoder_model="cross-encoder/ms-marco-MiniLM-L-6-v2"
            ),
            
            "api_docs_default": RerankerConfig(
                name="api_docs_default",
                reranker_type="api_docs",
                enabled=True,
                top_k=10,
                threshold=0.5,
                api_context_weight=0.7,
                technical_accuracy_weight=0.8,
                endpoint_relevance_weight=0.9,
                code_example_weight=0.6
            ),
            
            "llm_technical": RerankerConfig(
                name="llm_technical",
                reranker_type="llm",
                enabled=True,
                top_k=10,
                threshold=0.0,
                max_tokens=4000,
                temperature=0.1,
                llm_model="gpt-3.5-turbo",
                llm_provider="openai",
                prompt_template="technical_support"
            )
        }
        
        return default_configs
    
    def create_use_case_configs(self, use_case: str) -> List[RerankerConfig]:
        """Create configurations optimized for specific use cases"""
        
        use_case_configs = {
            "api_documentation": [
                # Primary: API-specific reranker
                RerankerConfig(
                    name="api_docs_primary",
                    reranker_type="api_docs",
                    enabled=True,
                    top_k=15,
                    threshold=0.6,
                    api_context_weight=0.8,
                    technical_accuracy_weight=0.9,
                    endpoint_relevance_weight=1.0,
                    code_example_weight=0.7
                ),
                # Secondary: LLM reranker with API template
                RerankerConfig(
                    name="llm_api_secondary",
                    reranker_type="llm",
                    enabled=True,
                    top_k=10,
                    threshold=0.0,
                    max_tokens=4000,
                    temperature=0.1,
                    llm_model="gpt-3.5-turbo",
                    llm_provider="openai",
                    prompt_template="api_documentation"
                )
            ],
            
            "technical_support": [
                # Primary: LLM reranker with technical template
                RerankerConfig(
                    name="llm_technical_primary",
                    reranker_type="llm",
                    enabled=True,
                    top_k=12,
                    threshold=0.0,
                    max_tokens=4000,
                    temperature=0.1,
                    llm_model="gpt-3.5-turbo",
                    llm_provider="openai",
                    prompt_template="technical_support"
                ),
                # Secondary: Semantic reranker
                RerankerConfig(
                    name="semantic_technical_secondary",
                    reranker_type="semantic",
                    enabled=True,
                    top_k=10,
                    threshold=0.6,
                    semantic_similarity_threshold=0.6,
                    context_window_size=512
                )
            ],
            
            "general_search": [
                # Primary: Semantic reranker
                RerankerConfig(
                    name="semantic_general_primary",
                    reranker_type="semantic",
                    enabled=True,
                    top_k=15,
                    threshold=0.5,
                    semantic_similarity_threshold=0.6,
                    context_window_size=512
                ),
                # Secondary: LLM reranker with default template
                RerankerConfig(
                    name="llm_general_secondary",
                    reranker_type="llm",
                    enabled=True,
                    top_k=10,
                    threshold=0.0,
                    max_tokens=4000,
                    temperature=0.1,
                    llm_model="gpt-3.5-turbo",
                    llm_provider="openai",
                    prompt_template="default"
                )
            ]
        }
        
        return use_case_configs.get(use_case, [])
    
    async def initialize_rerankers(self, 
                                 configs: List[RerankerConfig],
                                 llm_provider_factory=None,
                                 embeddings_function=None):
        """Initialize multiple rerankers with their dependencies"""
        
        for config in configs:
            try:
                reranker = self.create_reranker(config.reranker_type, config)
                
                # Initialize based on type
                if config.reranker_type == "llm" and llm_provider_factory:
                    await reranker.initialize(llm_provider_factory)
                elif config.reranker_type == "semantic":
                    await reranker.initialize(embeddings_function)
                elif config.reranker_type == "api_docs":
                    # API docs reranker doesn't need external initialization
                    pass
                
                self.logger.info("reranker_initialized", name=config.name, type=config.reranker_type)
                
            except Exception as e:
                self.logger.error("reranker_initialization_failed",
                               name=config.name,
                               type=config.reranker_type,
                               error=str(e))
                # Continue with other rerankers
    
    def get_reranker_pipeline(self, 
                            pipeline_name: str = "default") -> List[BaseReranker]:
        """Get a predefined pipeline of rerankers"""
        
        pipelines = {
            "default": ["semantic_default", "llm_default"],
            "api_docs": ["api_docs_default", "llm_api_docs"],
            "technical": ["llm_technical", "semantic_default"],
            "semantic_only": ["semantic_default"],
            "llm_only": ["llm_default"],
            "api_only": ["api_docs_default"]
        }
        
        pipeline_names = pipelines.get(pipeline_name, ["semantic_default"])
        pipeline = []
        
        for name in pipeline_names:
            reranker = self.get_reranker(name)
            if reranker and reranker.is_enabled():
                pipeline.append(reranker)
        
        return pipeline




