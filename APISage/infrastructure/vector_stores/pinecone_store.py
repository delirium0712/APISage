"""
Pinecone vector store implementation
"""

import uuid
from typing import Dict, Any, List, Optional
from .base_store import BaseVectorStore, VectorStoreConfig, Document, SearchResult

try:
    import pinecone
    from pinecone import Pinecone
    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False
    pinecone = None


class PineconeStore(BaseVectorStore):
    """Pinecone vector store implementation"""
    
    def __init__(self, config: VectorStoreConfig, embeddings_function=None):
        super().__init__(config, embeddings_function)
        self._client = None
        self._index = None
    
    async def initialize(self) -> bool:
        """Initialize Pinecone client"""
        if not PINECONE_AVAILABLE:
            self.logger.error("Pinecone not available. Install with: pip install pinecone-client")
            return False
        
        if not self.config.api_key:
            self.logger.error("Pinecone API key required")
            return False
        
        try:
            # Initialize Pinecone
            self._client = Pinecone(api_key=self.config.api_key)
            
            # Create or connect to index
            await self.create_collection()
            
            self.logger.info("Pinecone initialized", 
                           index=self.config.collection_name)
            return True
            
        except Exception as e:
            self.logger.error("Failed to initialize Pinecone", error=str(e))
            return False
    
    async def create_collection(self, name: str = None) -> bool:
        """Create Pinecone index"""
        if not self._client:
            return False
        
        index_name = name or self.config.collection_name
        
        try:
            # Check if index exists
            existing_indexes = self._client.list_indexes()
            index_names = [idx.name for idx in existing_indexes.indexes]
            
            if index_name not in index_names:
                # Map distance metric
                metric_map = {
                    "cosine": "cosine",
                    "euclidean": "euclidean",
                    "dot": "dotproduct"
                }
                metric = metric_map.get(self.config.distance_metric.lower(), "cosine")
                
                # Create index
                self._client.create_index(
                    name=index_name,
                    dimension=self.config.embedding_dim,
                    metric=metric,
                    spec={
                        "serverless": {
                            "cloud": "aws",
                            "region": "us-east-1"
                        }
                    }
                )
                
                self.logger.info("Created Pinecone index", name=index_name)
            else:
                self.logger.info("Pinecone index already exists", name=index_name)
            
            # Connect to index
            self._index = self._client.Index(index_name)
            return True
            
        except Exception as e:
            self.logger.error("Failed to create Pinecone index", error=str(e))
            return False
    
    async def add_documents(self, documents: List[Document]) -> bool:
        """Add documents to Pinecone"""
        if not self._index:
            return False
        
        try:
            vectors = []
            
            for doc in documents:
                # Generate ID if not provided
                doc_id = doc.id or str(uuid.uuid4())
                
                # Generate embedding if not provided
                if doc.embedding:
                    vector_values = doc.embedding
                else:
                    vector_values = await self.embed_text(doc.content)
                
                # Prepare metadata (Pinecone has size limits)
                metadata = {
                    "content": doc.content[:40000],  # Limit content size
                    **(doc.metadata or {})
                }
                
                # Convert all metadata values to strings (Pinecone requirement)
                for key, value in metadata.items():
                    if not isinstance(value, (str, int, float, bool)):
                        metadata[key] = str(value)
                
                vector = {
                    "id": doc_id,
                    "values": vector_values,
                    "metadata": metadata
                }
                vectors.append(vector)
            
            # Upsert vectors in batches
            batch_size = 100
            for i in range(0, len(vectors), batch_size):
                batch = vectors[i:i + batch_size]
                self._index.upsert(vectors=batch)
            
            self.logger.info("Added documents to Pinecone", count=len(documents))
            return True
            
        except Exception as e:
            self.logger.error("Failed to add documents to Pinecone", error=str(e))
            return False
    
    async def search(self, query: str, k: int = 5, filter_metadata: Dict[str, Any] = None) -> List[SearchResult]:
        """Search Pinecone by text query"""
        if not self._index:
            return []
        
        try:
            # Generate query embedding
            query_vector = await self.embed_text(query)
            
            # Search using vector
            return await self.search_by_vector(query_vector, k, filter_metadata)
            
        except Exception as e:
            self.logger.error("Pinecone search failed", error=str(e))
            return []
    
    async def search_by_vector(self, vector: List[float], k: int = 5, filter_metadata: Dict[str, Any] = None) -> List[SearchResult]:
        """Search Pinecone by vector"""
        if not self._index:
            return []
        
        try:
            # Prepare filter
            query_filter = None
            if filter_metadata:
                # Pinecone filter format
                query_filter = {}
                for key, value in filter_metadata.items():
                    query_filter[key] = {"$eq": value}
            
            # Query Pinecone
            response = self._index.query(
                vector=vector,
                top_k=k,
                filter=query_filter,
                include_metadata=True
            )
            
            # Convert to SearchResult objects
            results = []
            
            for match in response.matches:
                metadata = match.metadata or {}
                content = metadata.pop("content", "")
                
                doc = Document(
                    id=match.id,
                    content=content,
                    metadata=metadata
                )
                
                results.append(SearchResult(document=doc, score=match.score))
            
            return results
            
        except Exception as e:
            self.logger.error("Pinecone vector search failed", error=str(e))
            return []
    
    async def delete_documents(self, document_ids: List[str]) -> bool:
        """Delete documents from Pinecone"""
        if not self._index:
            return False
        
        try:
            self._index.delete(ids=document_ids)
            
            self.logger.info("Deleted documents from Pinecone", count=len(document_ids))
            return True
            
        except Exception as e:
            self.logger.error("Failed to delete documents from Pinecone", error=str(e))
            return False
    
    async def update_document(self, document: Document) -> bool:
        """Update document in Pinecone"""
        if not self._index:
            return False
        
        try:
            # Generate embedding if not provided
            vector_values = document.embedding
            if not vector_values:
                vector_values = await self.embed_text(document.content)
            
            # Prepare metadata
            metadata = {
                "content": document.content[:40000],
                **(document.metadata or {})
            }
            
            # Convert metadata values to strings
            for key, value in metadata.items():
                if not isinstance(value, (str, int, float, bool)):
                    metadata[key] = str(value)
            
            # Upsert (update or insert)
            self._index.upsert(vectors=[{
                "id": document.id,
                "values": vector_values,
                "metadata": metadata
            }])
            
            return True
            
        except Exception as e:
            self.logger.error("Failed to update document in Pinecone", error=str(e))
            return False
    
    async def get_document(self, document_id: str) -> Optional[Document]:
        """Get document by ID from Pinecone"""
        if not self._index:
            return None
        
        try:
            response = self._index.fetch(ids=[document_id])
            
            if response.vectors and document_id in response.vectors:
                vector_data = response.vectors[document_id]
                metadata = vector_data.metadata or {}
                content = metadata.pop("content", "")
                
                return Document(
                    id=document_id,
                    content=content,
                    metadata=metadata
                )
            
            return None
            
        except Exception as e:
            self.logger.error("Failed to get document from Pinecone", error=str(e))
            return None
    
    async def list_collections(self) -> List[str]:
        """List Pinecone indexes"""
        if not self._client:
            return []
        
        try:
            indexes = self._client.list_indexes()
            return [idx.name for idx in indexes.indexes]
            
        except Exception as e:
            self.logger.error("Failed to list Pinecone indexes", error=str(e))
            return []
    
    async def delete_collection(self, name: str = None) -> bool:
        """Delete Pinecone index"""
        if not self._client:
            return False
        
        index_name = name or self.config.collection_name
        
        try:
            self._client.delete_index(index_name)
            if index_name == self.config.collection_name:
                self._index = None
            
            self.logger.info("Deleted Pinecone index", name=index_name)
            return True
            
        except Exception as e:
            self.logger.error("Failed to delete Pinecone index", error=str(e))
            return False
    
    async def get_collection_stats(self, name: str = None) -> Dict[str, Any]:
        """Get Pinecone index statistics"""
        if not self._index:
            return {}
        
        try:
            stats = self._index.describe_index_stats()
            
            return {
                "name": self.config.collection_name,
                "document_count": stats.total_vector_count,
                "embedding_dim": self.config.embedding_dim,
                "distance_metric": self.config.distance_metric,
                "store_type": "pinecone"
            }
            
        except Exception as e:
            self.logger.error("Failed to get Pinecone index stats", error=str(e))
            return {}
    
    def is_available(self) -> bool:
        """Check if Pinecone is available"""
        return PINECONE_AVAILABLE and self._client is not None