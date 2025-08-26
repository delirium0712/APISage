"""
ChromaDB vector store implementation
"""

import uuid
from typing import Dict, Any, List, Optional
from .base_store import BaseVectorStore, VectorStoreConfig, Document, SearchResult

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    chromadb = None


class ChromaStore(BaseVectorStore):
    """ChromaDB vector store implementation"""
    
    def __init__(self, config: VectorStoreConfig, embeddings_function=None):
        super().__init__(config, embeddings_function)
        self._client = None
        self._collection = None
    
    async def initialize(self) -> bool:
        """Initialize ChromaDB"""
        if not CHROMADB_AVAILABLE:
            self.logger.error("ChromaDB not available. Install with: pip install chromadb")
            return False
        
        try:
            # Configure ChromaDB
            if self.config.host == "localhost" and not self.config.api_key:
                # Local persistent storage
                settings = Settings(
                    persist_directory="./chroma_db",
                    anonymized_telemetry=False
                )
                self._client = chromadb.PersistentClient(settings=settings)
            else:
                # Remote client
                self._client = chromadb.HttpClient(
                    host=self.config.host,
                    port=self.config.port
                )
            
            # Create or get collection
            await self.create_collection()
            
            self.logger.info("ChromaDB initialized", 
                           collection=self.config.collection_name)
            return True
            
        except Exception as e:
            self.logger.error("Failed to initialize ChromaDB", error=str(e))
            return False
    
    async def create_collection(self, name: str = None) -> bool:
        """Create or get ChromaDB collection"""
        if not self._client:
            return False
        
        collection_name = name or self.config.collection_name
        
        try:
            # Get or create collection
            self._collection = self._client.get_or_create_collection(
                name=collection_name,
                metadata={"description": "API documentation collection"}
            )
            
            self.logger.info("ChromaDB collection ready", name=collection_name)
            return True
            
        except Exception as e:
            self.logger.error("Failed to create ChromaDB collection", error=str(e))
            return False
    
    async def add_documents(self, documents: List[Document]) -> bool:
        """Add documents to ChromaDB"""
        if not self._collection:
            return False
        
        try:
            # Prepare data for ChromaDB
            ids = []
            embeddings = []
            metadatas = []
            documents_content = []
            
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
                
                metadatas.append(doc.metadata or {})
                documents_content.append(doc.content)
            
            # Add to ChromaDB
            self._collection.add(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=documents_content
            )
            
            self.logger.info("Added documents to ChromaDB", count=len(documents))
            return True
            
        except Exception as e:
            self.logger.error("Failed to add documents to ChromaDB", error=str(e))
            return False
    
    async def search(self, query: str, k: int = 5, filter_metadata: Dict[str, Any] = None) -> List[SearchResult]:
        """Search ChromaDB by text query"""
        if not self._collection:
            return []
        
        try:
            # Generate query embedding
            query_embedding = await self.embed_text(query)
            
            # Search using embedding
            return await self.search_by_vector(query_embedding, k, filter_metadata)
            
        except Exception as e:
            self.logger.error("ChromaDB search failed", error=str(e))
            return []
    
    async def search_by_vector(self, vector: List[float], k: int = 5, filter_metadata: Dict[str, Any] = None) -> List[SearchResult]:
        """Search ChromaDB by vector"""
        if not self._collection:
            return []
        
        try:
            # Prepare where clause for filtering
            where_clause = filter_metadata if filter_metadata else None
            
            # Query ChromaDB
            results = self._collection.query(
                query_embeddings=[vector],
                n_results=k,
                where=where_clause
            )
            
            # Convert to SearchResult objects
            search_results = []
            
            if results['ids'] and len(results['ids']) > 0:
                for i in range(len(results['ids'][0])):
                    doc = Document(
                        id=results['ids'][0][i],
                        content=results['documents'][0][i],
                        metadata=results['metadatas'][0][i] if results['metadatas'] else {},
                        embedding=None  # ChromaDB doesn't return embeddings in query
                    )
                    
                    # ChromaDB returns distances, convert to similarity score
                    distance = results['distances'][0][i] if results['distances'] else 1.0
                    score = 1.0 - distance  # Convert distance to similarity
                    
                    search_results.append(SearchResult(document=doc, score=score))
            
            return search_results
            
        except Exception as e:
            self.logger.error("ChromaDB vector search failed", error=str(e))
            return []
    
    async def delete_documents(self, document_ids: List[str]) -> bool:
        """Delete documents from ChromaDB"""
        if not self._collection:
            return False
        
        try:
            self._collection.delete(ids=document_ids)
            self.logger.info("Deleted documents from ChromaDB", count=len(document_ids))
            return True
            
        except Exception as e:
            self.logger.error("Failed to delete documents from ChromaDB", error=str(e))
            return False
    
    async def update_document(self, document: Document) -> bool:
        """Update document in ChromaDB"""
        if not self._collection:
            return False
        
        try:
            # Generate embedding if not provided
            embedding = document.embedding
            if not embedding:
                embedding = await self.embed_text(document.content)
            
            # Update in ChromaDB
            self._collection.update(
                ids=[document.id],
                embeddings=[embedding],
                metadatas=[document.metadata or {}],
                documents=[document.content]
            )
            
            return True
            
        except Exception as e:
            self.logger.error("Failed to update document in ChromaDB", error=str(e))
            return False
    
    async def get_document(self, document_id: str) -> Optional[Document]:
        """Get document by ID from ChromaDB"""
        if not self._collection:
            return None
        
        try:
            results = self._collection.get(ids=[document_id])
            
            if results['ids'] and len(results['ids']) > 0:
                return Document(
                    id=results['ids'][0],
                    content=results['documents'][0] if results['documents'] else "",
                    metadata=results['metadatas'][0] if results['metadatas'] else {}
                )
            
            return None
            
        except Exception as e:
            self.logger.error("Failed to get document from ChromaDB", error=str(e))
            return None
    
    async def list_collections(self) -> List[str]:
        """List ChromaDB collections"""
        if not self._client:
            return []
        
        try:
            collections = self._client.list_collections()
            return [col.name for col in collections]
            
        except Exception as e:
            self.logger.error("Failed to list ChromaDB collections", error=str(e))
            return []
    
    async def delete_collection(self, name: str = None) -> bool:
        """Delete ChromaDB collection"""
        if not self._client:
            return False
        
        collection_name = name or self.config.collection_name
        
        try:
            self._client.delete_collection(name=collection_name)
            if collection_name == self.config.collection_name:
                self._collection = None
            
            self.logger.info("Deleted ChromaDB collection", name=collection_name)
            return True
            
        except Exception as e:
            self.logger.error("Failed to delete ChromaDB collection", error=str(e))
            return False
    
    async def get_collection_stats(self, name: str = None) -> Dict[str, Any]:
        """Get ChromaDB collection statistics"""
        if not self._collection:
            return {}
        
        try:
            # ChromaDB doesn't have built-in stats, count documents
            results = self._collection.get()
            count = len(results['ids']) if results['ids'] else 0
            
            return {
                "name": self.config.collection_name,
                "document_count": count,
                "embedding_dim": self.config.embedding_dim,
                "store_type": "chromadb"
            }
            
        except Exception as e:
            self.logger.error("Failed to get ChromaDB collection stats", error=str(e))
            return {}
    
    def is_available(self) -> bool:
        """Check if ChromaDB is available"""
        return CHROMADB_AVAILABLE and self._client is not None