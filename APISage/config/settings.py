"""
Configuration settings for the LangChain Agent Orchestration System
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
import os


@dataclass
class AgentConfig:
    """Production configuration for agents"""
    name: str
    model: str = "llama3:8b"  # Ollama model
    temperature: float = 0.7
    max_tokens: int = 2000
    max_retries: int = 3
    timeout: int = 60
    cache_ttl: int = 3600
    memory_window: int = 10
    vector_store_collection: str = "api_docs"


@dataclass
class SystemConfig:
    """Enhanced system-wide configuration"""
    # Database Configuration
    redis_url: str = field(default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379"))
    postgres_url: str = field(default_factory=lambda: os.getenv("POSTGRES_URL", 
        f"postgresql://{os.getenv('DATABASE_USERNAME', 'agentuser')}:{os.getenv('DATABASE_PASSWORD', 'agentpass123')}@{os.getenv('DATABASE_HOST', 'localhost')}:{os.getenv('DATABASE_PORT', '5433')}/{os.getenv('DATABASE_DATABASE', 'agentdb')}"))
    
    # LLM Provider Configuration
    llm_providers: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        "openai": {
            "provider": "openai",
            "model": os.getenv("OPENAI_MODEL", "gpt-4o"),
            "api_key": os.getenv("OPENAI_API_KEY"),
            "temperature": float(os.getenv("OPENAI_TEMPERATURE", "0.7")),
            "max_tokens": int(os.getenv("OPENAI_MAX_TOKENS", "2000"))
        },
        "claude": {
            "provider": "anthropic",
            "model": os.getenv("ANTHROPIC_MODEL", "claude-3-sonnet-20240229"),
            "api_key": os.getenv("ANTHROPIC_API_KEY"),
            "temperature": float(os.getenv("ANTHROPIC_TEMPERATURE", "0.7")),
            "max_tokens": int(os.getenv("ANTHROPIC_MAX_TOKENS", "2000"))
        },
        "gemini": {
            "provider": "google",
            "model": os.getenv("GEMINI_MODEL", "gemini-pro"),
            "api_key": os.getenv("GEMINI_API_KEY"),
            "temperature": float(os.getenv("GEMINI_TEMPERATURE", "0.7")),
            "max_tokens": int(os.getenv("GEMINI_MAX_TOKENS", "2000"))
        },
        "ollama": {
            "provider": "ollama",
            "model": os.getenv("OLLAMA_MODEL", "llama3:8b"),
            "api_base": os.getenv("OLLAMA_API_BASE", "http://localhost:11434"),
            "temperature": float(os.getenv("OLLAMA_TEMPERATURE", "0.7")),
            "max_tokens": int(os.getenv("OLLAMA_MAX_TOKENS", "2000"))
        }
    })
    primary_llm_provider: str = field(default_factory=lambda: os.getenv("PRIMARY_LLM_PROVIDER", "ollama"))
    fallback_llm_providers: List[str] = field(default_factory=lambda: os.getenv("FALLBACK_LLM_PROVIDERS", "openai,claude").split(","))
    
    # Vector store configurations
    vector_stores: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        "chroma": {
            "host": os.getenv("CHROMA_HOST", "localhost"),
            "port": int(os.getenv("CHROMA_PORT", "8000")),
            "collection_name": os.getenv("CHROMA_COLLECTION", "documents"),
            "embedding_dim": int(os.getenv("CHROMA_EMBEDDING_DIM", "1536")),
            "distance_metric": os.getenv("CHROMA_DISTANCE_METRIC", "cosine")
        },
        "qdrant": {
            "host": os.getenv("QDRANT_HOST", "localhost"),
            "port": int(os.getenv("QDRANT_PORT", "6333")),
            "collection_name": os.getenv("QDRANT_COLLECTION", "documents"),
            "embedding_dim": int(os.getenv("QDRANT_EMBEDDING_DIM", "1536")),
            "distance_metric": os.getenv("QDRANT_DISTANCE_METRIC", "cosine"),
            "api_key": os.getenv("QDRANT_API_KEY")
        },
        "milvus": {
            "host": os.getenv("MILVUS_HOST", "localhost"),
            "port": int(os.getenv("MILVUS_PORT", "19530")),
            "collection_name": os.getenv("MILVUS_COLLECTION", "documents"),
            "embedding_dim": int(os.getenv("MILVUS_EMBEDDING_DIM", "1536")),
            "distance_metric": os.getenv("MILVUS_DISTANCE_METRIC", "cosine")
        },
        "pinecone": {
            "api_key": os.getenv("PINECONE_API_KEY"),
            "environment": os.getenv("PINECONE_ENVIRONMENT", "us-west1-gcp"),
            "index_name": os.getenv("PINECONE_INDEX", "documents"),
            "embedding_dim": int(os.getenv("PINECONE_EMBEDDING_DIM", "1536")),
            "distance_metric": os.getenv("PINECONE_DISTANCE_METRIC", "cosine")
        },
        "hybrid": {
            "vector_weight": float(os.getenv("HYBRID_VECTOR_WEIGHT", "0.6")),
            "lexical_weight": float(os.getenv("HYBRID_LEXICAL_WEIGHT", "0.4")),
            "rerank_top_k": int(os.getenv("HYBRID_RERANK_TOP_K", "15")),
            "final_top_k": int(os.getenv("HYBRID_FINAL_TOP_K", "5")),
            "enable_hybrid": os.getenv("HYBRID_ENABLE", "true").lower() == "true",
            "enable_reranking": os.getenv("HYBRID_ENABLE_RERANKING", "true").lower() == "true",
            "rrf_k": float(os.getenv("HYBRID_RRF_K", "60.0")),
            "bm25_k1": float(os.getenv("HYBRID_BM25_K1", "1.2")),
            "bm25_b": float(os.getenv("HYBRID_BM25_B", "0.75"))
        }
    })
    primary_vector_store: str = field(default_factory=lambda: os.getenv("PRIMARY_VECTOR_STORE", "hybrid"))
    
    # Document Processing Configuration
    document_parsers: Dict[str, bool] = field(default_factory=lambda: {
        "openapi": os.getenv("ENABLE_OPENAPI_PARSER", "true").lower() == "true",
        "markdown": os.getenv("ENABLE_MARKDOWN_PARSER", "true").lower() == "true",
        "postman": os.getenv("ENABLE_POSTMAN_PARSER", "true").lower() == "true",
        "html": os.getenv("ENABLE_HTML_PARSER", "true").lower() == "true"
    })
    chunking_strategy: Dict[str, Any] = field(default_factory=lambda: {
        "chunk_size": int(os.getenv("CHUNK_SIZE", "1000")),
        "chunk_overlap": int(os.getenv("CHUNK_OVERLAP", "200")),
        "strategy": os.getenv("CHUNKING_STRATEGY", "semantic")  # semantic, fixed, adaptive
    })
    
    # System Configuration
    max_concurrent_agents: int = field(default_factory=lambda: int(os.getenv("MAX_CONCURRENT_AGENTS", "10")))
    enable_tracing: bool = field(default_factory=lambda: os.getenv("ENABLE_TRACING", "true").lower() == "true")
    enable_caching: bool = field(default_factory=lambda: os.getenv("ENABLE_CACHING", "true").lower() == "true")
    embedding_model: str = field(default_factory=lambda: os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"))
    
    # File Upload Configuration
    max_file_size: int = field(default_factory=lambda: int(os.getenv("MAX_FILE_SIZE", "10485760")))  # 10MB
    allowed_file_types: List[str] = field(default_factory=lambda: os.getenv("ALLOWED_FILE_TYPES", "json,yaml,yml,md,markdown,txt").split(","))
    upload_directory: str = field(default_factory=lambda: os.getenv("UPLOAD_DIRECTORY", "./uploads"))
    
    # Evaluation Configuration
    evaluation_enabled: bool = field(default_factory=lambda: os.getenv("ENABLE_EVALUATION", "false").lower() == "true")
    evaluation_metrics: List[str] = field(default_factory=lambda: os.getenv("EVALUATION_METRICS", "faithfulness,answer_relevancy,context_precision").split(","))
    
    # Configuration data storage
    config_data: Dict[str, Any] = field(default_factory=dict)
    
    # Legacy compatibility
    @property
    def ollama_host(self) -> str:
        return self.llm_providers.get("ollama", {}).get("api_base", "http://localhost:11434")
    
    @property
    def qdrant_host(self) -> str:
        return self.vector_stores.get("qdrant", {}).get("host", "localhost")
    
    @property
    def qdrant_port(self) -> int:
        return self.vector_stores.get("qdrant", {}).get("port", 6333)
    
    @property
    def llm_model(self) -> str:
        primary_provider = self.llm_providers.get(self.primary_llm_provider, {})
        return primary_provider.get("model", "llama3:8b")
