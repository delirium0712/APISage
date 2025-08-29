"""
Qdrant Vector Store Implementation with Lazy Loading
"""

from typing import Dict, Any, List, Optional, Union
import numpy as np
import structlog
from .base_store import BaseVectorStore, VectorStoreConfig, VectorStoreType

# Lazy import - only installs qdrant-client when actually needed
from utils.dependency_manager import dependency_manager

logger = structlog.get_logger(__name__)


class QdrantStore(BaseVectorStore):
    """Qdrant vector store implementation with lazy loading"""
    
    def __init__(self, config: VectorStoreConfig):
        super().__init__(config)
        self.client = None
        self.collection_name = config.collection_name
        self._ensure_dependencies()
    
    def _ensure_dependencies(self):
        """Ensure Qdrant dependencies are available"""
        if not dependency_manager.is_feature_available("qdrant"):
            logger.info("qdrant_dependencies_not_available", 
                       message="Qdrant dependencies will be installed when needed")
    
    def _get_client(self):
        """Get Qdrant client, installing dependencies if needed"""
        if self.client is None:
            try:
                # Try to get the package with auto-install
                qdrant_client = dependency_manager.get_package("qdrant_client")
                if qdrant_client is None:
                    raise ImportError("Failed to install qdrant-client")
                
                self.client = qdrant_client.QdrantClient(
                    host=self.config.host,
                    port=self.config.port,
                    api_key=self.config.api_key
                )
                logger.info("qdrant_client_connected", 
                           host=self.config.host, port=self.config.port)
            except Exception as e:
                logger.error("qdrant_client_connection_failed", error=str(e))
                raise
        
        return self.client
    
    async def initialize(self) -> bool:
        """Initialize the Qdrant store"""
        try:
            client = self._get_client()
            
            # Check if collection exists
            collections = client.get_collections()
            collection_names = [c.name for c in collections.collections]
            
            if self.collection_name not in collection_names:
                # Create collection
                client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config={
                        "size": self.config.embedding_dim,
                        "distance": self.config.distance_metric.upper()
                    }
                )
                logger.info("qdrant_collection_created", name=self.collection_name)
            
            return True
        except Exception as e:
            logger.error("qdrant_initialization_failed", error=str(e))
            return False
    
    async def add_documents(self, documents: List[Dict[str, Any]], 
                           embeddings: List[np.ndarray]) -> bool:
        """Add documents to the store"""
        try:
            client = self._get_client()
            
            # Prepare points for Qdrant
            points = []
            for i, (doc, embedding) in enumerate(zip(documents, embeddings)):
                point = {
                    "id": doc.get("id", f"doc_{i}"),
                    "vector": embedding.tolist(),
                    "payload": {
                        "text": doc.get("text", ""),
                        "metadata": doc.get("metadata", {}),
                        "source": doc.get("source", ""),
                        "timestamp": doc.get("timestamp", "")
                    }
                }
                points.append(point)
            
            # Upsert points
            client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            
            logger.info("qdrant_documents_added", count=len(documents))
            return True
        except Exception as e:
            logger.error("qdrant_add_documents_failed", error=str(e))
            return False
    
    async def search(self, query_embedding: np.ndarray, 
                    top_k: int = 5) -> List[Dict[str, Any]]:
        """Search for similar documents"""
        try:
            client = self._get_client()
            
            # Search in Qdrant
            results = client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding.tolist(),
                limit=top_k
            )
            
            # Convert results to standard format
            documents = []
            for result in results:
                doc = {
                    "id": result.id,
                    "score": result.score,
                    "text": result.payload.get("text", ""),
                    "metadata": result.payload.get("metadata", {}),
                    "source": result.payload.get("source", ""),
                    "timestamp": result.payload.get("timestamp", "")
                }
                documents.append(doc)
            
            return documents
        except Exception as e:
            logger.error("qdrant_search_failed", error=str(e))
            return []
    
    async def delete_documents(self, document_ids: List[str]) -> bool:
        """Delete documents by ID"""
        try:
            client = self._get_client()
            
            client.delete(
                collection_name=self.collection_name,
                points_selector=document_ids
            )
            
            logger.info("qdrant_documents_deleted", count=len(document_ids))
            return True
        except Exception as e:
            logger.error("qdrant_delete_documents_failed", error=str(e))
            return False
    
    async def get_collection_info(self) -> Dict[str, Any]:
        """Get information about the collection"""
        try:
            client = self._get_client()
            
            collection_info = client.get_collection(self.collection_name)
            collection_stats = client.get_collection(self.collection_name)
            
            return {
                "name": collection_info.name,
                "vector_size": collection_info.config.params.vectors.size,
                "distance_metric": collection_info.config.params.vectors.distance,
                "points_count": collection_stats.points_count,
                "segments_count": collection_stats.segments_count,
                "status": collection_info.status
            }
        except Exception as e:
            logger.error("qdrant_get_collection_info_failed", error=str(e))
            return {}
    
    async def health_check(self) -> bool:
        """Check if the store is healthy"""
        try:
            client = self._get_client()
            collections = client.get_collections()
            return True
        except Exception as e:
            logger.error("qdrant_health_check_failed", error=str(e))
            return False
    
    # Missing abstract method implementations
    async def create_collection(self, name: str = None) -> bool:
        """Create a collection"""
        try:
            client = self._get_client()
            collection_name = name or self.collection_name
            
            client.create_collection(
                collection_name=collection_name,
                vectors_config={
                    "size": self.config.embedding_dim,
                    "distance": self.config.distance_metric.upper()
                }
            )
            logger.info("qdrant_collection_created", name=collection_name)
            return True
        except Exception as e:
            logger.error("qdrant_create_collection_failed", error=str(e))
            return False
    
    async def search_by_vector(self, vector: List[float], k: int = 5, filter_metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Search by vector embedding"""
        try:
            client = self._get_client()
            
            # Search in Qdrant
            results = client.search(
                collection_name=self.collection_name,
                query_vector=vector,
                limit=k
            )
            
            # Convert results to standard format
            documents = []
            for result in results:
                doc = {
                    "id": result.id,
                    "score": result.score,
                    "text": result.payload.get("text", ""),
                    "metadata": result.payload.get("metadata", {}),
                    "source": result.payload.get("source", ""),
                    "timestamp": result.payload.get("timestamp", "")
                }
                documents.append(doc)
            
            return documents
        except Exception as e:
            logger.error("qdrant_search_by_vector_failed", error=str(e))
            return []
    
    async def update_document(self, document: Dict[str, Any]) -> bool:
        """Update a document"""
        try:
            client = self._get_client()
            
            # Prepare point for Qdrant
            point = {
                "id": document.get("id"),
                "vector": document.get("embedding", []),
                "payload": {
                    "text": document.get("text", ""),
                    "metadata": document.get("metadata", {}),
                    "source": document.get("source", ""),
                    "timestamp": document.get("timestamp", "")
                }
            }
            
            # Upsert point
            client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )
            
            logger.info("qdrant_document_updated", id=document.get("id"))
            return True
        except Exception as e:
            logger.error("qdrant_update_document_failed", error=str(e))
            return False
    
    async def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get a document by ID"""
        try:
            client = self._get_client()
            
            # Get point from Qdrant
            point = client.retrieve(
                collection_name=self.collection_name,
                ids=[document_id]
            )
            
            if point and len(point) > 0:
                point = point[0]
                return {
                    "id": point.id,
                    "text": point.payload.get("text", ""),
                    "metadata": point.payload.get("metadata", {}),
                    "source": point.payload.get("source", ""),
                    "timestamp": point.payload.get("timestamp", ""),
                    "embedding": point.vector
                }
            
            return None
        except Exception as e:
            logger.error("qdrant_get_document_failed", error=str(e))
            return None
    
    async def list_collections(self) -> List[str]:
        """List all collections"""
        try:
            client = self._get_client()
            collections = client.get_collections()
            return [c.name for c in collections.collections]
        except Exception as e:
            logger.error("qdrant_list_collections_failed", error=str(e))
            return []
    
    async def delete_collection(self, name: str = None) -> bool:
        """Delete a collection"""
        try:
            client = self._get_client()
            collection_name = name or self.collection_name
            
            client.delete_collection(collection_name)
            logger.info("qdrant_collection_deleted", name=collection_name)
            return True
        except Exception as e:
            logger.error("qdrant_delete_collection_failed", error=str(e))
            return False
    
    async def get_collection_stats(self, name: str = None) -> Dict[str, Any]:
        """Get collection statistics"""
        try:
            client = self._get_client()
            collection_name = name or self.collection_name
            
            collection_info = client.get_collection(collection_name)
            
            return {
                "name": collection_info.name,
                "vector_size": collection_info.config.params.vectors.size,
                "distance_metric": collection_info.config.params.vectors.distance,
                "points_count": collection_info.points_count,
                "segments_count": collection_info.segments_count,
                "status": collection_info.status
            }
        except Exception as e:
            logger.error("qdrant_get_collection_stats_failed", error=str(e))
            return {}
    
    def is_available(self) -> bool:
        """Check if vector store is available"""
        try:
            client = self._get_client()
            collections = client.get_collections()
            return True
        except Exception as e:
            logger.error("qdrant_is_available_failed", error=str(e))
            return False