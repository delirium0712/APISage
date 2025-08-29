"""
Chroma Vector Store Implementation with Lazy Loading
"""

from typing import Dict, Any, List, Optional, Union
import numpy as np
import structlog
from .base_store import BaseVectorStore, VectorStoreConfig, VectorStoreType

# Lazy import - only installs chromadb when actually needed
from utils.dependency_manager import dependency_manager

logger = structlog.get_logger(__name__)


class ChromaStore(BaseVectorStore):
    """Chroma vector store implementation with lazy loading"""
    
    def __init__(self, config: VectorStoreConfig):
        super().__init__(config)
        self.client = None
        self.collection = None
        self.collection_name = config.collection_name
        self._ensure_dependencies()
    
    def _ensure_dependencies(self):
        """Ensure ChromaDB dependencies are available"""
        if not dependency_manager.is_feature_available("chroma"):
            logger.info("chroma_dependencies_not_available", 
                       message="ChromaDB dependencies will be installed when needed")
    
    def _get_client(self):
        """Get ChromaDB client, installing dependencies if needed"""
        if self.client is None:
            try:
                # Try to get the package with auto-install
                chromadb = dependency_manager.get_package("chromadb")
                if chromadb is None:
                    raise ImportError("Failed to install chromadb")
                
                # Create client based on config
                if hasattr(self.config, 'host') and self.config.host:
                    # Remote ChromaDB
                    self.client = chromadb.HttpClient(
                        host=self.config.host,
                        port=self.config.port
                    )
                else:
                    # Local ChromaDB
                    self.client = chromadb.PersistentClient(
                        path="./chroma_db"
                    )
                
                logger.info("chroma_client_connected", 
                           host=getattr(self.config, 'host', 'local'),
                           port=getattr(self.config, 'port', 'local'))
            except Exception as e:
                logger.error("chroma_client_connection_failed", error=str(e))
                raise
        
        return self.client
    
    def _get_collection(self):
        """Get or create ChromaDB collection"""
        if self.collection is None:
            client = self._get_client()
            
            try:
                # Try to get existing collection
                self.collection = client.get_collection(
                    name=self.collection_name,
                    embedding_function=None  # We'll handle embeddings separately
                )
                logger.info("chroma_collection_loaded", name=self.collection_name)
            except Exception:
                # Create new collection
                self.collection = client.create_collection(
                    name=self.collection_name,
                    metadata={
                        "embedding_dim": self.config.embedding_dim,
                        "distance_metric": self.config.distance_metric
                    }
                )
                logger.info("chroma_collection_created", name=self.collection_name)
        
        return self.collection
    
    async def initialize(self) -> bool:
        """Initialize the ChromaDB store"""
        try:
            collection = self._get_collection()
            return True
        except Exception as e:
            logger.error("chroma_initialization_failed", error=str(e))
            return False
    
    async def add_documents(self, documents: List[Dict[str, Any]], 
                           embeddings: List[np.ndarray]) -> bool:
        """Add documents to the store"""
        try:
            collection = self._get_collection()
            
            # Prepare data for ChromaDB
            ids = []
            texts = []
            metadatas = []
            vectors = []
            
            for i, (doc, embedding) in enumerate(zip(documents, embeddings)):
                doc_id = doc.get("id", f"doc_{i}")
                ids.append(doc_id)
                texts.append(doc.get("text", ""))
                metadatas.append({
                    "source": doc.get("source", ""),
                    "timestamp": doc.get("timestamp", ""),
                    **(doc.get("metadata", {}))
                })
                vectors.append(embedding.tolist())
            
            # Add to collection
            collection.add(
                ids=ids,
                documents=texts,
                metadatas=metadatas,
                embeddings=vectors
            )
            
            logger.info("chroma_documents_added", count=len(documents))
            return True
        except Exception as e:
            logger.error("chroma_add_documents_failed", error=str(e))
            return False
    
    async def search(self, query_embedding: np.ndarray, 
                    top_k: int = 5) -> List[Dict[str, Any]]:
        """Search for similar documents"""
        try:
            collection = self._get_collection()
            
            # Search in ChromaDB
            results = collection.query(
                query_embeddings=[query_embedding.tolist()],
                n_results=top_k,
                include=["documents", "metadatas", "distances"]
            )
            
            # Convert results to standard format
            documents = []
            if results['ids'] and len(results['ids'][0]) > 0:
                for i in range(len(results['ids'][0])):
                    doc = {
                        "id": results['ids'][0][i],
                        "score": 1.0 - results['distances'][0][i],  # Convert distance to similarity
                        "text": results['documents'][0][i],
                        "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                        "source": results['metadatas'][0][i].get("source", "") if results['metadatas'] else "",
                        "timestamp": results['metadatas'][0][i].get("timestamp", "") if results['metadatas'] else ""
                    }
                    documents.append(doc)
            
            return documents
        except Exception as e:
            logger.error("chroma_search_failed", error=str(e))
            return []
    
    async def delete_documents(self, document_ids: List[str]) -> bool:
        """Delete documents by ID"""
        try:
            collection = self._get_collection()
            
            collection.delete(ids=document_ids)
            
            logger.info("chroma_documents_deleted", count=len(document_ids))
            return True
        except Exception as e:
            logger.error("chroma_delete_documents_failed", error=str(e))
            return False
    
    async def get_collection_info(self) -> Dict[str, Any]:
        """Get information about the collection"""
        try:
            collection = self._get_collection()
            
            # Get collection count
            count = collection.count()
            
            return {
                "name": collection.name,
                "count": count,
                "embedding_dim": self.config.embedding_dim,
                "distance_metric": self.config.distance_metric,
                "metadata": collection.metadata
            }
        except Exception as e:
            logger.error("chroma_get_collection_info_failed", error=str(e))
            return {}
    
    async def health_check(self) -> bool:
        """Check if the store is healthy"""
        try:
            collection = self._get_collection()
            count = collection.count()
            return True
        except Exception as e:
            logger.error("chroma_health_check_failed", error=str(e))
            return False
    
    # Missing abstract method implementations
    async def create_collection(self, name: str = None) -> bool:
        """Create a collection"""
        try:
            collection_name = name or self.collection_name
            collection = self._get_collection()
            
            # ChromaDB collections are created automatically when accessed
            # Just verify it exists
            count = collection.count()
            logger.info("chroma_collection_verified", name=collection_name, count=count)
            return True
        except Exception as e:
            logger.error("chroma_create_collection_failed", error=str(e))
            return False
    
    async def search_by_vector(self, vector: List[float], k: int = 5, filter_metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Search by vector embedding"""
        try:
            collection = self._get_collection()
            
            # Search in ChromaDB
            results = collection.query(
                query_embeddings=[vector],
                n_results=k,
                include=["documents", "metadatas", "distances"]
            )
            
            # Convert results to standard format
            documents = []
            if results['ids'] and len(results['ids'][0]) > 0:
                for i in range(len(results['ids'][0])):
                    doc = {
                        "id": results['ids'][0][i],
                        "score": 1.0 - results['distances'][0][i],  # Convert distance to similarity
                        "text": results['documents'][0][i],
                        "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                        "source": results['metadatas'][0][i].get("source", "") if results['metadatas'] else "",
                        "timestamp": results['metadatas'][0][i].get("timestamp", "") if results['metadatas'] else ""
                    }
                    documents.append(doc)
            
            return documents
        except Exception as e:
            logger.error("chroma_search_by_vector_failed", error=str(e))
            return []
    
    async def update_document(self, document: Dict[str, Any]) -> bool:
        """Update a document"""
        try:
            collection = self._get_collection()
            
            # ChromaDB doesn't have a direct update method, so we delete and re-add
            if document.get("id"):
                collection.delete(ids=[document["id"]])
            
            # Add the updated document
            collection.add(
                ids=[document.get("id", "doc_updated")],
                documents=[document.get("text", "")],
                metadatas=[{
                    "source": document.get("source", ""),
                    "timestamp": document.get("timestamp", ""),
                    **(document.get("metadata", {}))
                }],
                embeddings=[document.get("embedding", [])]
            )
            
            logger.info("chroma_document_updated", id=document.get("id"))
            return True
        except Exception as e:
            logger.error("chroma_update_document_failed", error=str(e))
            return False
    
    async def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get a document by ID"""
        try:
            collection = self._get_collection()
            
            # Get document from ChromaDB
            results = collection.get(
                ids=[document_id],
                include=["documents", "metadatas", "embeddings"]
            )
            
            if results['ids'] and len(results['ids']) > 0:
                return {
                    "id": results['ids'][0],
                    "text": results['documents'][0] if results['documents'] else "",
                    "metadata": results['metadatas'][0] if results['metadatas'] else {},
                    "source": results['metadatas'][0].get("source", "") if results['metadatas'] else "",
                    "timestamp": results['metadatas'][0].get("timestamp", "") if results['metadatas'] else "",
                    "embedding": results['embeddings'][0] if results['embeddings'] else []
                }
            
            return None
        except Exception as e:
            logger.error("chroma_get_document_failed", error=str(e))
            return None
    
    async def list_collections(self) -> List[str]:
        """List all collections"""
        try:
            client = self._get_client()
            collections = client.list_collections()
            return [c.name for c in collections]
        except Exception as e:
            logger.error("chroma_list_collections_failed", error=str(e))
            return []
    
    async def delete_collection(self, name: str = None) -> bool:
        """Delete a collection"""
        try:
            collection_name = name or self.collection_name
            client = self._get_client()
            
            client.delete_collection(collection_name)
            logger.info("chroma_collection_deleted", name=collection_name)
            return True
        except Exception as e:
            logger.error("chroma_delete_collection_failed", error=str(e))
            return False
    
    async def get_collection_stats(self, name: str = None) -> Dict[str, Any]:
        """Get collection statistics"""
        try:
            collection = self._get_collection()
            collection_name = name or self.collection_name
            
            count = collection.count()
            
            return {
                "name": collection_name,
                "count": count,
                "embedding_dim": self.config.embedding_dim,
                "distance_metric": self.config.distance_metric,
                "metadata": collection.metadata
            }
        except Exception as e:
            logger.error("chroma_get_collection_stats_failed", error=str(e))
            return {}
    
    def is_available(self) -> bool:
        """Check if vector store is available"""
        try:
            collection = self._get_collection()
            count = collection.count()
            return True
        except Exception as e:
            logger.error("chroma_is_available_failed", error=str(e))
            return False