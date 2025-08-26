"""
Milvus vector store implementation
"""

import uuid
from typing import Dict, Any, List, Optional
from .base_store import BaseVectorStore, VectorStoreConfig, Document, SearchResult

try:
    from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility
    MILVUS_AVAILABLE = True
except ImportError:
    MILVUS_AVAILABLE = False


class MilvusStore(BaseVectorStore):
    """Milvus vector store implementation"""
    
    def __init__(self, config: VectorStoreConfig, embeddings_function=None):
        super().__init__(config, embeddings_function)
        self._collection = None
        self._connection_alias = "default"
    
    async def initialize(self) -> bool:
        """Initialize Milvus connection"""
        if not MILVUS_AVAILABLE:
            self.logger.error("Milvus not available. Install with: pip install pymilvus")
            return False
        
        try:
            # Connect to Milvus
            connections.connect(
                alias=self._connection_alias,
                host=self.config.host,
                port=self.config.port
            )
            
            # Create collection if it doesn't exist
            await self.create_collection()
            
            self.logger.info("Milvus initialized", 
                           host=self.config.host,
                           collection=self.config.collection_name)
            return True
            
        except Exception as e:
            self.logger.error("Failed to initialize Milvus", error=str(e))
            return False
    
    async def create_collection(self, name: str = None) -> bool:
        """Create Milvus collection"""
        collection_name = name or self.config.collection_name
        
        try:
            # Check if collection exists
            if utility.has_collection(collection_name, using=self._connection_alias):
                self._collection = Collection(collection_name, using=self._connection_alias)
                self.logger.info("Milvus collection already exists", name=collection_name)
                return True
            
            # Define schema
            fields = [
                FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=100),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.config.embedding_dim),
                FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
                FieldSchema(name="metadata", dtype=DataType.VARCHAR, max_length=10000)
            ]
            
            schema = CollectionSchema(
                fields=fields,
                description="API documentation collection"
            )
            
            # Create collection
            self._collection = Collection(
                name=collection_name,
                schema=schema,
                using=self._connection_alias
            )
            
            # Create index
            index_params = {
                "metric_type": self._get_milvus_metric(),
                "index_type": "IVF_FLAT",
                "params": {"nlist": 128}
            }
            
            self._collection.create_index(
                field_name="embedding",
                index_params=index_params
            )
            
            self.logger.info("Created Milvus collection", name=collection_name)
            return True
            
        except Exception as e:
            self.logger.error("Failed to create Milvus collection", error=str(e))
            return False
    
    def _get_milvus_metric(self) -> str:
        """Convert distance metric to Milvus format"""
        metric_map = {
            "cosine": "COSINE",
            "euclidean": "L2",
            "dot": "IP"
        }
        return metric_map.get(self.config.distance_metric.lower(), "COSINE")
    
    async def add_documents(self, documents: List[Document]) -> bool:
        """Add documents to Milvus"""
        if not self._collection:
            return False
        
        try:
            # Prepare data
            ids = []
            embeddings = []
            contents = []
            metadatas = []
            
            for doc in documents:
                # Generate ID if not provided
                doc_id = doc.id or str(uuid.uuid4())
                ids.append(doc_id)
                
                # Generate embedding if not provided
                if doc.embedding:
                    embeddings.append(doc.embedding)
                else:
                    embedding = await self.embed_text(doc.content)
                    embeddings.append(embedding)
                
                contents.append(doc.content)
                
                # Serialize metadata as JSON string
                import json
                metadata_str = json.dumps(doc.metadata or {})
                metadatas.append(metadata_str)
            
            # Insert data
            data = [ids, embeddings, contents, metadatas]
            self._collection.insert(data)
            
            # Load collection for search
            self._collection.load()
            
            self.logger.info("Added documents to Milvus", count=len(documents))
            return True
            
        except Exception as e:
            self.logger.error("Failed to add documents to Milvus", error=str(e))
            return False
    
    async def search(self, query: str, k: int = 5, filter_metadata: Dict[str, Any] = None) -> List[SearchResult]:
        """Search Milvus by text query"""
        if not self._collection:
            return []
        
        try:
            # Generate query embedding
            query_vector = await self.embed_text(query)
            
            # Search using vector
            return await self.search_by_vector(query_vector, k, filter_metadata)
            
        except Exception as e:
            self.logger.error("Milvus search failed", error=str(e))
            return []
    
    async def search_by_vector(self, vector: List[float], k: int = 5, filter_metadata: Dict[str, Any] = None) -> List[SearchResult]:
        """Search Milvus by vector"""
        if not self._collection:
            return []
        
        try:
            # Prepare search parameters
            search_params = {
                "metric_type": self._get_milvus_metric(),
                "params": {"nprobe": 10}
            }
            
            # Prepare expression for filtering
            expr = None
            if filter_metadata:
                # Simple key-value filtering (Milvus expressions are complex)
                # This is a simplified implementation
                pass
            
            # Search
            results = self._collection.search(
                data=[vector],
                anns_field="embedding",
                param=search_params,
                limit=k,
                expr=expr,
                output_fields=["id", "content", "metadata"]
            )
            
            # Convert to SearchResult objects
            search_results = []
            
            if results and len(results) > 0:
                for hit in results[0]:
                    # Deserialize metadata
                    import json
                    try:
                        metadata = json.loads(hit.entity.get("metadata", "{}"))
                    except:
                        metadata = {}
                    
                    doc = Document(
                        id=str(hit.entity.get("id", "")),
                        content=hit.entity.get("content", ""),
                        metadata=metadata
                    )
                    
                    # Milvus returns distance, convert to similarity score
                    score = 1.0 / (1.0 + hit.distance)
                    
                    search_results.append(SearchResult(document=doc, score=score))
            
            return search_results
            
        except Exception as e:
            self.logger.error("Milvus vector search failed", error=str(e))
            return []
    
    async def delete_documents(self, document_ids: List[str]) -> bool:
        """Delete documents from Milvus"""
        if not self._collection:
            return False
        
        try:
            # Create expression for deletion
            id_list = "', '".join(document_ids)
            expr = f"id in ['{id_list}']"
            
            self._collection.delete(expr)
            
            self.logger.info("Deleted documents from Milvus", count=len(document_ids))
            return True
            
        except Exception as e:
            self.logger.error("Failed to delete documents from Milvus", error=str(e))
            return False
    
    async def update_document(self, document: Document) -> bool:
        """Update document in Milvus (delete + insert)"""
        if not self._collection:
            return False
        
        try:
            # Delete existing document
            await self.delete_documents([document.id])
            
            # Insert updated document
            return await self.add_documents([document])
            
        except Exception as e:
            self.logger.error("Failed to update document in Milvus", error=str(e))
            return False
    
    async def get_document(self, document_id: str) -> Optional[Document]:
        """Get document by ID from Milvus"""
        if not self._collection:
            return None
        
        try:
            # Query by ID
            expr = f"id == '{document_id}'"
            results = self._collection.query(
                expr=expr,
                output_fields=["id", "content", "metadata"]
            )
            
            if results and len(results) > 0:
                result = results[0]
                
                # Deserialize metadata
                import json
                try:
                    metadata = json.loads(result.get("metadata", "{}"))
                except:
                    metadata = {}
                
                return Document(
                    id=str(result.get("id", "")),
                    content=result.get("content", ""),
                    metadata=metadata
                )
            
            return None
            
        except Exception as e:
            self.logger.error("Failed to get document from Milvus", error=str(e))
            return None
    
    async def list_collections(self) -> List[str]:
        """List Milvus collections"""
        try:
            return utility.list_collections(using=self._connection_alias)
            
        except Exception as e:
            self.logger.error("Failed to list Milvus collections", error=str(e))
            return []
    
    async def delete_collection(self, name: str = None) -> bool:
        """Delete Milvus collection"""
        collection_name = name or self.config.collection_name
        
        try:
            utility.drop_collection(collection_name, using=self._connection_alias)
            if collection_name == self.config.collection_name:
                self._collection = None
            
            self.logger.info("Deleted Milvus collection", name=collection_name)
            return True
            
        except Exception as e:
            self.logger.error("Failed to delete Milvus collection", error=str(e))
            return False
    
    async def get_collection_stats(self, name: str = None) -> Dict[str, Any]:
        """Get Milvus collection statistics"""
        if not self._collection:
            return {}
        
        try:
            # Get collection statistics
            stats = self._collection.num_entities
            
            return {
                "name": self.config.collection_name,
                "document_count": stats,
                "embedding_dim": self.config.embedding_dim,
                "distance_metric": self.config.distance_metric,
                "store_type": "milvus"
            }
            
        except Exception as e:
            self.logger.error("Failed to get Milvus collection stats", error=str(e))
            return {}
    
    def is_available(self) -> bool:
        """Check if Milvus is available"""
        return MILVUS_AVAILABLE and self._collection is not None