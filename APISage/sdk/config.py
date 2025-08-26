"""
Configuration classes for the RAG SDK
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum


class VectorStoreType(Enum):
    """Supported vector store types"""
    QDRANT = "qdrant"
    CHROMA = "chroma"
    MILVUS = "milvus"
    PINECONE = "pinecone"


class LLMProvider(Enum):
    """Supported LLM providers"""
    OLLAMA = "ollama"
    OPENAI = "openai"
    HUGGINGFACE = "huggingface"
    LITELLM = "litellm"


class EmbeddingProvider(Enum):
    """Supported embedding providers"""
    HUGGINGFACE = "huggingface"
    OPENAI = "openai"
    SENTENCE_TRANSFORMERS = "sentence-transformers"


@dataclass
class VectorStoreConfig:
    """Configuration for vector stores"""
    store_type: VectorStoreType = VectorStoreType.QDRANT
    host: str = "localhost"
    port: int = 6333
    collection_name: str = "rag_documents"
    embedding_dim: int = 384
    distance_metric: str = "cosine"
    api_key: Optional[str] = None


@dataclass
class LLMConfig:
    """Configuration for LLM providers"""
    provider: LLMProvider = LLMProvider.OLLAMA
    model_name: str = "llama3:8b"
    base_url: str = "http://localhost:11434"
    api_key: Optional[str] = None
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    extra_params: Dict[str, Any] = None


@dataclass
class EmbeddingConfig:
    """Configuration for embedding models"""
    provider: EmbeddingProvider = EmbeddingProvider.HUGGINGFACE
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    device: str = "cpu"
    normalize_embeddings: bool = True


@dataclass
class SearchConfig:
    """Configuration for search strategies"""
    enable_hybrid: bool = True
    vector_weight: float = 0.6
    lexical_weight: float = 0.4
    rerank_top_k: int = 15
    final_top_k: int = 5
    enable_reranking: bool = True
    reranker_model: Optional[str] = None


@dataclass
class RAGConfig:
    """Main configuration class for the RAG system"""
    vector_store: VectorStoreConfig = None
    llm: LLMConfig = None
    embedding: EmbeddingConfig = None
    search: SearchConfig = None
    
    def __post_init__(self):
        """Initialize default configs if not provided"""
        if self.vector_store is None:
            self.vector_store = VectorStoreConfig()
        if self.llm is None:
            self.llm = LLMConfig()
        if self.embedding is None:
            self.embedding = EmbeddingConfig()
        if self.search is None:
            self.search = SearchConfig()


# Predefined configurations for common use cases
class PresetConfigs:
    """Predefined configurations for common scenarios"""
    
    @staticmethod
    def local_development() -> RAGConfig:
        """Configuration for local development with Ollama and Qdrant"""
        return RAGConfig(
            vector_store=VectorStoreConfig(
                store_type=VectorStoreType.QDRANT,
                host="localhost",
                port=6333
            ),
            llm=LLMConfig(
                provider=LLMProvider.OLLAMA,
                model_name="llama3:8b",
                base_url="http://localhost:11434"
            ),
            embedding=EmbeddingConfig(
                provider=EmbeddingProvider.HUGGINGFACE,
                model_name="sentence-transformers/all-MiniLM-L6-v2"
            )
        )
    
    @staticmethod
    def cloud_openai() -> RAGConfig:
        """Configuration for cloud deployment with OpenAI"""
        return RAGConfig(
            llm=LLMConfig(
                provider=LLMProvider.OPENAI,
                model_name="gpt-3.5-turbo"
            ),
            embedding=EmbeddingConfig(
                provider=EmbeddingProvider.OPENAI,
                model_name="text-embedding-ada-002"
            )
        )
    
    @staticmethod
    def high_performance() -> RAGConfig:
        """Configuration optimized for high performance"""
        return RAGConfig(
            search=SearchConfig(
                enable_hybrid=True,
                vector_weight=0.7,
                lexical_weight=0.3,
                rerank_top_k=20,
                final_top_k=10,
                enable_reranking=True
            )
        )