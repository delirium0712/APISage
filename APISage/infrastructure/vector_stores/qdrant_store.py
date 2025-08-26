"""
Qdrant vector store implementation
"""

import uuid
from typing import Dict, Any, List, Optional
from .base_store import BaseVectorStore, VectorStoreConfig, Document, SearchResult

try:
    from qdrant_client import QdrantClient, models
    from qdrant_client.http.models import VectorParams, Distance
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    QdrantClient = None


class QdrantStore(BaseVectorStore):
    """Qdrant vector store implementation"""
    
    def __init__(self, config: VectorStoreConfig, embeddings_function=None):
        super().__init__(config, embeddings_function)
        self._client = None
    
    async def initialize(self) -> bool:
        """Initialize Qdrant client"""
        if not QDRANT_AVAILABLE:
            self.logger.error("Qdrant not available. Install with: pip install qdrant-client")
            return False
        
        try:
            # Create Qdrant client
            if self.config.api_key:
                self._client = QdrantClient(
                    url=f"https://{self.config.host}:{self.config.port}",
                    api_key=self.config.api_key
                )
            else:
                self._client = QdrantClient(
                    host=self.config.host,
                    port=self.config.port
                )
            
            # Create collection if it doesn't exist
            await self.create_collection()
            
            self.logger.info("Qdrant initialized", 
                           host=self.config.host,
                           collection=self.config.collection_name)
            return True
            
        except Exception as e:
            self.logger.error("Failed to initialize Qdrant", error=str(e))
            return False
    
    async def create_collection(self, name: str = None) -> bool:
        """Create Qdrant collection"""
        if not self._client:
            return False
        
        collection_name = name or self.config.collection_name
        
        try:
            # Check if collection exists
            collections = self._client.get_collections().collections
            existing_names = [col.name for col in collections]
            
            if collection_name not in existing_names:
                # Map distance metric
                distance_map = {
                    "cosine": Distance.COSINE,
                    "euclidean": Distance.EUCLID,
                    "dot": Distance.DOT
                }
                distance = distance_map.get(self.config.distance_metric.lower(), Distance.COSINE)
                
                # Create collection
                self._client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=self.config.embedding_dim,
                        distance=distance
                    )
                )
                
                self.logger.info("Created Qdrant collection", name=collection_name)
            else:
                self.logger.info("Qdrant collection already exists", name=collection_name)
            
            return True
            
        except Exception as e:
            self.logger.error("Failed to create Qdrant collection", error=str(e))
            return False
    
    async def add_documents(self, documents: List[Document]) -> bool:
        """Add documents to Qdrant"""
        if not self._client:
            return False
        
        try:
            points = []
            
            for doc in documents:
                # Generate ID if not provided
                doc_id = doc.id or str(uuid.uuid4())
                
                # Generate embedding if not provided
                if doc.embedding:
                    vector = doc.embedding
                else:
                    vector = await self.embed_text(doc.content)
                
                # Create point
                point = models.PointStruct(
                    id=doc_id,
                    vector=vector,
                    payload={
                        "content": doc.content,
                        **(doc.metadata or {})
                    }
                )
                points.append(point)
            
            # Upsert points
            self._client.upsert(
                collection_name=self.config.collection_name,
                points=points
            )
            
            self.logger.info("Added documents to Qdrant", count=len(documents))
            return True
            
        except Exception as e:
            self.logger.error("Failed to add documents to Qdrant", error=str(e))
            return False
    
    async def search(self, query: str, k: int = 5, filter_metadata: Dict[str, Any] = None) -> List[SearchResult]:
        """Search Qdrant by text query"""
        if not self._client:
            return []
        
        try:
            # Generate query embedding
            query_vector = await self.embed_text(query)
            
            # Search using vector
            return await self.search_by_vector(query_vector, k, filter_metadata)
            
        except Exception as e:
            self.logger.error("Qdrant search failed", error=str(e))
            return []
    
    async def search_by_vector(self, vector: List[float], k: int = 5, filter_metadata: Dict[str, Any] = None) -> List[SearchResult]:
        """Search Qdrant by vector"""
        if not self._client:
            return []
        
        try:
            # Prepare filter
            query_filter = None
            if filter_metadata:
                conditions = []
                for key, value in filter_metadata.items():
                    conditions.append(
                        models.FieldCondition(
                            key=key,
                            match=models.MatchValue(value=value)
                        )
                    )
                
                if conditions:
                    query_filter = models.Filter(must=conditions)
            
            # Search
            search_result = self._client.search(
                collection_name=self.config.collection_name,
                query_vector=vector,
                query_filter=query_filter,
                limit=k,
                with_payload=True
            )
            
            # Convert to SearchResult objects
            results = []
            for point in search_result:
                payload = point.payload or {}
                content = payload.pop("content", "")
                
                doc = Document(
                    id=str(point.id),
                    content=content,
                    metadata=payload
                )
                
                results.append(SearchResult(document=doc, score=point.score))
            
            return results
            
        except Exception as e:
            self.logger.error("Qdrant vector search failed", error=str(e))
            return []
    
    async def delete_documents(self, document_ids: List[str]) -> bool:
        """Delete documents from Qdrant"""
        if not self._client:
            return False
        
        try:
            self._client.delete(
                collection_name=self.config.collection_name,
                points_selector=models.PointIdsList(
                    points=document_ids
                )
            )
            
            self.logger.info("Deleted documents from Qdrant", count=len(document_ids))
            return True
            
        except Exception as e:
            self.logger.error("Failed to delete documents from Qdrant", error=str(e))
            return False
    
    async def update_document(self, document: Document) -> bool:
        """Update document in Qdrant"""
        if not self._client:
            return False
        
        try:
            # Generate embedding if not provided
            vector = document.embedding
            if not vector:
                vector = await self.embed_text(document.content)
            
            # Create updated point
            point = models.PointStruct(
                id=document.id,
                vector=vector,
                payload={
                    "content": document.content,
                    **(document.metadata or {})
                }
            )
            
            # Upsert (update or insert)
            self._client.upsert(
                collection_name=self.config.collection_name,
                points=[point]
            )
            
            return True
            
        except Exception as e:
            self.logger.error("Failed to update document in Qdrant", error=str(e))
            return False
    
    async def get_document(self, document_id: str) -> Optional[Document]:
        """Get document by ID from Qdrant"""
        if not self._client:
            return None
        
        try:
            points = self._client.retrieve(
                collection_name=self.config.collection_name,
                ids=[document_id],
                with_payload=True
            )
            
            if points and len(points) > 0:
                point = points[0]
                payload = point.payload or {}
                content = payload.pop("content", "")
                
                return Document(
                    id=str(point.id),
                    content=content,
                    metadata=payload
                )
            
            return None
            
        except Exception as e:
            self.logger.error("Failed to get document from Qdrant", error=str(e))
            return None
    
    async def list_collections(self) -> List[str]:
        """List Qdrant collections"""
        if not self._client:
            return []
        
        try:
            collections = self._client.get_collections().collections
            return [col.name for col in collections]
            
        except Exception as e:
            self.logger.error("Failed to list Qdrant collections", error=str(e))
            return []
    
    async def delete_collection(self, name: str = None) -> bool:
        """Delete Qdrant collection"""
        if not self._client:
            return False
        
        collection_name = name or self.config.collection_name
        
        try:
            self._client.delete_collection(collection_name=collection_name)
            self.logger.info("Deleted Qdrant collection", name=collection_name)
            return True
            
        except Exception as e:
            self.logger.error("Failed to delete Qdrant collection", error=str(e))
            return False
    
    async def get_collection_stats(self, name: str = None) -> Dict[str, Any]:
        """Get Qdrant collection statistics"""
        if not self._client:
            return {}
        
        collection_name = name or self.config.collection_name
        
        try:
            info = self._client.get_collection(collection_name=collection_name)
            
            return {
                "name": collection_name,
                "document_count": info.points_count,
                "embedding_dim": info.config.params.vectors.size,
                "distance_metric": info.config.params.vectors.distance.value,
                "store_type": "qdrant"
            }
            
        except Exception as e:
            self.logger.error("Failed to get Qdrant collection stats", error=str(e))
            return {}
    
    def is_available(self) -> bool:
        """Check if Qdrant is available"""
        return QDRANT_AVAILABLE and self._client is not None