"""
Base vector store interface
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
import structlog

logger = structlog.get_logger()


class VectorStoreType(Enum):
    """Supported vector store types"""
    CHROMA = "chroma"
    QDRANT = "qdrant"
    MILVUS = "milvus"
    PINECONE = "pinecone"
    MEMORY = "memory"
    HYBRID = "hybrid"


@dataclass
class VectorStoreConfig:
    """Vector store configuration"""
    store_type: VectorStoreType
    collection_name: str = "api_docs"
    host: str = "localhost"
    port: int = None
    api_key: Optional[str] = None
    embedding_dim: int = 384
    distance_metric: str = "cosine"
    additional_config: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.additional_config is None:
            self.additional_config = {}
        
        # Set default ports
        if self.port is None:
            if self.store_type == VectorStoreType.QDRANT:
                self.port = 6333
            elif self.store_type == VectorStoreType.MILVUS:
                self.port = 19530
            else:
                self.port = 8000


@dataclass
class Document:
    """Document container for vector stores"""
    id: str
    content: str
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None


@dataclass
class SearchResult:
    """Search result container"""
    document: Document
    score: float


class BaseVectorStore(ABC):
    """Abstract base class for vector stores"""
    
    def __init__(self, config: VectorStoreConfig, embeddings_function=None):
        self.config = config
        self.embeddings_function = embeddings_function
        self.logger = structlog.get_logger(component=f"{self.__class__.__name__}")
        self._client = None
        self._collection = None
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the vector store"""
        pass
    
    @abstractmethod
    async def create_collection(self, name: str = None) -> bool:
        """Create a collection/index"""
        pass
    
    @abstractmethod
    async def add_documents(self, documents: List[Document]) -> bool:
        """Add documents to the vector store"""
        pass
    
    @abstractmethod
    async def search(self, query: str, k: int = 5, filter_metadata: Dict[str, Any] = None) -> List[SearchResult]:
        """Search for similar documents"""
        pass
    
    @abstractmethod
    async def search_by_vector(self, vector: List[float], k: int = 5, filter_metadata: Dict[str, Any] = None) -> List[SearchResult]:
        """Search by vector embedding"""
        pass
    
    @abstractmethod
    async def delete_documents(self, document_ids: List[str]) -> bool:
        """Delete documents by IDs"""
        pass
    
    @abstractmethod
    async def update_document(self, document: Document) -> bool:
        """Update a document"""
        pass
    
    @abstractmethod
    async def get_document(self, document_id: str) -> Optional[Document]:
        """Get a document by ID"""
        pass
    
    @abstractmethod
    async def list_collections(self) -> List[str]:
        """List all collections"""
        pass
    
    @abstractmethod
    async def delete_collection(self, name: str = None) -> bool:
        """Delete a collection"""
        pass
    
    @abstractmethod
    async def get_collection_stats(self, name: str = None) -> Dict[str, Any]:
        """Get collection statistics"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if vector store is available"""
        pass
    
    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for text"""
        if self.embeddings_function:
            try:
                # Handle different embedding function signatures
                if hasattr(self.embeddings_function, 'embed_query'):
                    # LangChain style
                    return self.embeddings_function.embed_query(text)
                elif hasattr(self.embeddings_function, 'encode'):
                    # Sentence transformers style
                    embedding = self.embeddings_function.encode(text)
                    return embedding.tolist() if hasattr(embedding, 'tolist') else list(embedding)
                elif callable(self.embeddings_function):
                    # Function style
                    result = self.embeddings_function([text])
                    return result[0] if isinstance(result, list) and len(result) > 0 else []
                else:
                    self.logger.warning("Unknown embedding function type")
                    return []
            except Exception as e:
                self.logger.error("Embedding generation failed", error=str(e))
                return []
        else:
            # Return dummy embedding
            return [0.0] * self.config.embedding_dim
    
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        if self.embeddings_function:
            try:
                if hasattr(self.embeddings_function, 'embed_documents'):
                    # LangChain style
                    return self.embeddings_function.embed_documents(texts)
                elif hasattr(self.embeddings_function, 'encode'):
                    # Sentence transformers style
                    embeddings = self.embeddings_function.encode(texts)
                    return [emb.tolist() if hasattr(emb, 'tolist') else list(emb) for emb in embeddings]
                elif callable(self.embeddings_function):
                    # Function style
                    return self.embeddings_function(texts)
                else:
                    # Fallback to individual embedding
                    return [await self.embed_text(text) for text in texts]
            except Exception as e:
                self.logger.error("Batch embedding generation failed", error=str(e))
                return [[0.0] * self.config.embedding_dim for _ in texts]
        else:
            # Return dummy embeddings
            return [[0.0] * self.config.embedding_dim for _ in texts]
    
    async def health_check(self) -> bool:
        """Perform health check"""
        try:
            # Try to get collection stats
            stats = await self.get_collection_stats()
            return bool(stats)
        except Exception as e:
            self.logger.error("Health check failed", error=str(e))
            return False
    
    def get_store_info(self) -> Dict[str, Any]:
        """Get vector store information"""
        return {
            "store_type": self.config.store_type.value,
            "collection_name": self.config.collection_name,
            "host": self.config.host,
            "port": self.config.port,
            "available": self.is_available(),
            "embedding_dim": self.config.embedding_dim
        }