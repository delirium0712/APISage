"""
Vector Store Factory
"""

import os
from typing import Dict, Any, Optional
import structlog

from .base_store import BaseVectorStore, VectorStoreType, VectorStoreConfig
from .chroma_store import ChromaStore
from .qdrant_store import QdrantStore
from .milvus_store import MilvusStore
from .pinecone_store import PineconeStore
from .hybrid_store import HybridVectorStore, HybridSearchConfig

logger = structlog.get_logger()


class VectorStoreFactory:
    """Factory for creating vector stores"""
    
    @staticmethod
    def create_store(config: VectorStoreConfig, embeddings_function=None, hybrid_config: HybridSearchConfig = None) -> BaseVectorStore:
        """Create vector store based on configuration"""
        
        store_type = config.store_type
        
        if store_type == VectorStoreType.HYBRID:
            return HybridVectorStore(config, embeddings_function, hybrid_config)
        elif store_type == VectorStoreType.CHROMA:
            return ChromaStore(config, embeddings_function)
        elif store_type == VectorStoreType.QDRANT:
            return QdrantStore(config, embeddings_function)
        elif store_type == VectorStoreType.MILVUS:
            return MilvusStore(config, embeddings_function)
        elif store_type == VectorStoreType.PINECONE:
            return PineconeStore(config, embeddings_function)
        elif store_type == VectorStoreType.MEMORY:
            # Fallback to Chroma in-memory
            return ChromaStore(config, embeddings_function)
        else:
            raise ValueError(f"Unsupported vector store type: {store_type}")
    
    @staticmethod
    def create_from_config(store_configs: Dict[str, Dict[str, Any]], embeddings_function=None) -> Dict[str, BaseVectorStore]:
        """Create multiple vector stores from configuration"""
        stores = {}
        
        for name, config_dict in store_configs.items():
            try:
                # Convert config dict to VectorStoreConfig
                store_type = VectorStoreType(config_dict.get('store_type', 'chroma'))
                
                config = VectorStoreConfig(
                    store_type=store_type,
                    collection_name=config_dict.get('collection_name', 'api_docs'),
                    host=config_dict.get('host', 'localhost'),
                    port=config_dict.get('port'),
                    api_key=config_dict.get('api_key') or os.getenv(f"{store_type.value.upper()}_API_KEY"),
                    embedding_dim=config_dict.get('embedding_dim', 384),
                    distance_metric=config_dict.get('distance_metric', 'cosine'),
                    additional_config=config_dict.get('additional_config', {})
                )
                
                store = VectorStoreFactory.create_store(config, embeddings_function)
                stores[name] = store
                
                logger.info("Created vector store", 
                          name=name, 
                          store_type=store_type.value,
                          collection=config.collection_name)
                
            except Exception as e:
                logger.error("Failed to create vector store", 
                           name=name, 
                           error=str(e))
                continue
        
        return stores
    
    @staticmethod
    def get_default_configs() -> Dict[str, Dict[str, Any]]:
        """Get default vector store configurations"""
        return {
            "hybrid": {
                "store_type": "hybrid",
                "collection_name": "api_docs",
                "host": "localhost",
                "embedding_dim": 384,
                "distance_metric": "cosine",
                "hybrid_config": {
                    "vector_weight": 0.7,
                    "lexical_weight": 0.3,
                    "rerank_top_k": 20,
                    "final_top_k": 5,
                    "enable_hybrid": True,
                    "enable_reranking": True
                }
            },
            "chroma": {
                "store_type": "chroma",
                "collection_name": "api_docs",
                "host": "localhost",
                "embedding_dim": 384,
                "distance_metric": "cosine"
            },
            "qdrant": {
                "store_type": "qdrant",
                "collection_name": "api_docs",
                "host": os.getenv("QDRANT_HOST", "localhost"),
                "port": int(os.getenv("QDRANT_PORT", "6333")),
                "api_key": os.getenv("QDRANT_API_KEY"),
                "embedding_dim": 384,
                "distance_metric": "cosine"
            },
            "milvus": {
                "store_type": "milvus",
                "collection_name": "api_docs",
                "host": os.getenv("MILVUS_HOST", "localhost"),
                "port": int(os.getenv("MILVUS_PORT", "19530")),
                "embedding_dim": 384,
                "distance_metric": "cosine"
            },
            "pinecone": {
                "store_type": "pinecone",
                "collection_name": "api-docs",
                "api_key": os.getenv("PINECONE_API_KEY"),
                "embedding_dim": 384,
                "distance_metric": "cosine"
            }
        }
    
    @staticmethod
    async def initialize_stores(stores: Dict[str, BaseVectorStore]) -> Dict[str, BaseVectorStore]:
        """Initialize all vector stores and return available ones"""
        available_stores = {}
        
        for name, store in stores.items():
            try:
                if await store.initialize():
                    available_stores[name] = store
                    logger.info("Vector store initialized successfully", name=name)
                else:
                    logger.warning("Vector store initialization failed", name=name)
            except Exception as e:
                logger.error("Vector store initialization error", name=name, error=str(e))
        
        return available_stores
    
    @staticmethod
    def auto_select_store(preference: str = "auto") -> VectorStoreType:
        """Auto-select best available vector store"""
        
        if preference != "auto":
            try:
                return VectorStoreType(preference)
            except ValueError:
                logger.warning("Invalid store preference, using auto-selection", preference=preference)
        
        # Check environment and availability
        if os.getenv("PINECONE_API_KEY"):
            return VectorStoreType.PINECONE
        elif os.getenv("QDRANT_HOST") or os.getenv("QDRANT_API_KEY"):
            return VectorStoreType.QDRANT
        elif os.getenv("MILVUS_HOST"):
            return VectorStoreType.MILVUS
        else:
            # Default to Chroma for development
            return VectorStoreType.CHROMA


class MultiVectorManager:
    """Manager for multiple vector stores with automatic selection"""
    
    def __init__(self, store_configs: Dict[str, Dict[str, Any]], embeddings_function=None, primary_store: str = None):
        self.stores = VectorStoreFactory.create_from_config(store_configs, embeddings_function)
        self.primary_store = primary_store or self._auto_select_primary()
        self.embeddings_function = embeddings_function
        self.logger = structlog.get_logger(component="MultiVectorManager")
    
    def _auto_select_primary(self) -> str:
        """Auto-select primary store based on availability"""
        # Priority order: Pinecone > Qdrant > Milvus > Chroma
        priority_order = ["pinecone", "qdrant", "milvus", "chroma"]
        
        for store_name in priority_order:
            if store_name in self.stores:
                return store_name
        
        # Return first available store
        return list(self.stores.keys())[0] if self.stores else None
    
    async def initialize(self) -> bool:
        """Initialize all vector stores"""
        self.stores = await VectorStoreFactory.initialize_stores(self.stores)
        
        if not self.stores:
            self.logger.error("No vector stores available")
            return False
        
        # Update primary store if it's not available
        if self.primary_store not in self.stores:
            self.primary_store = self._auto_select_primary()
            self.logger.warning("Primary store not available, using fallback", 
                              primary=self.primary_store)
        
        self.logger.info("MultiVector manager initialized", 
                        stores=list(self.stores.keys()),
                        primary=self.primary_store)
        return True
    
    async def add_documents(self, documents, store_name: str = None):
        """Add documents to specified or primary store"""
        target_store = store_name or self.primary_store
        
        if target_store not in self.stores:
            raise ValueError(f"Vector store {target_store} not available")
        
        store = self.stores[target_store]
        return await store.add_documents(documents)
    
    async def search(self, query: str, k: int = 5, store_name: str = None, **kwargs):
        """Search in specified or primary store"""
        target_store = store_name or self.primary_store
        
        if target_store not in self.stores:
            raise ValueError(f"Vector store {target_store} not available")
        
        store = self.stores[target_store]
        return await store.search(query, k, **kwargs)
    
    def get_available_stores(self) -> list[str]:
        """Get list of available store names"""
        return list(self.stores.keys())
    
    def get_store_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all stores"""
        return {name: store.get_store_info() for name, store in self.stores.items()}
    
    def set_primary_store(self, store_name: str) -> bool:
        """Set primary store"""
        if store_name in self.stores:
            self.primary_store = store_name
            self.logger.info("Primary store changed", store=store_name)
            return True
        return False
    
    async def get_store_stats(self, store_name: str = None) -> Dict[str, Any]:
        """Get statistics for specified or primary store"""
        target_store = store_name or self.primary_store
        
        if target_store not in self.stores:
            return {}
        
        store = self.stores[target_store]
        return await store.get_collection_stats()