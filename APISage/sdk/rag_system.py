"""
Main RAG System class - the primary interface for users
"""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Union
from pathlib import Path

from .config import RAGConfig, PresetConfigs
from .document_processor import DocumentProcessor
from .search_engine import SearchEngine


class RAGSystem:
    """
    Main RAG System class that orchestrates document processing, indexing, and querying.
    
    This is the primary class users will interact with. It can be extended for custom functionality.
    
    Example:
        # Basic usage
        rag = RAGSystem()
        rag.add_documents(["doc1.pdf", "doc2.txt"])
        answer = rag.query("What is this about?")
        
        # Custom configuration
        config = RAGConfig(...)
        rag = RAGSystem(config=config)
        
        # Extending the class
        class MyRAG(RAGSystem):
            def preprocess_query(self, query: str) -> str:
                return f"Enhanced: {query}"
                
            def query(self, query: str) -> str:
                enhanced_query = self.preprocess_query(query)
                return super().query(enhanced_query)
    """
    
    def __init__(self, config: Optional[RAGConfig] = None):
        """
        Initialize the RAG system
        
        Args:
            config: RAGConfig object. If None, uses local development preset.
        """
        self.config = config or PresetConfigs.local_development()
        self._document_processor: Optional[DocumentProcessor] = None
        self._search_engine: Optional[SearchEngine] = None
        self._is_initialized = False
        
    async def initialize(self) -> None:
        """
        Initialize the RAG system components asynchronously.
        This method must be called before using the system.
        """
        if self._is_initialized:
            return
            
        # Initialize document processor
        self._document_processor = DocumentProcessor(self.config)
        await self._document_processor.initialize()
        
        # Initialize search engine
        self._search_engine = SearchEngine(self.config)
        await self._search_engine.initialize()
        
        self._is_initialized = True
        
    def _ensure_initialized(self):
        """Ensure the system is initialized"""
        if not self._is_initialized:
            raise RuntimeError(
                "RAG system not initialized. Call 'await rag.initialize()' first."
            )
    
    async def add_documents(self, 
                          sources: Union[str, List[str]], 
                          source_type: str = "auto",
                          metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Add documents to the RAG system
        
        Args:
            sources: Single source or list of sources (URLs, file paths, etc.)
            source_type: Type of source ("url", "file", "text", "auto")
            metadata: Optional metadata to attach to documents
            
        Returns:
            Dict with processing results and statistics
        """
        self._ensure_initialized()
        
        if isinstance(sources, str):
            sources = [sources]
            
        results = {
            "total_sources": len(sources),
            "successful": 0,
            "failed": 0,
            "documents_created": 0,
            "errors": []
        }
        
        for source in sources:
            try:
                # Process document
                processed_data = await self._document_processor.process_document(
                    source, source_type, metadata
                )
                
                if processed_data and "parsed_content" in processed_data:
                    # Create documents and add to search engine
                    documents = self._create_documents(processed_data, source, metadata)
                    await self._search_engine.add_documents(documents)
                    
                    results["successful"] += 1
                    results["documents_created"] += len(documents)
                else:
                    results["failed"] += 1
                    results["errors"].append(f"Failed to process: {source}")
                    
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(f"Error processing {source}: {str(e)}")
                
        return results
    
    def _create_documents(self, processed_data: Dict[str, Any], 
                         source: str, 
                         metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Create documents from processed data (can be overridden in subclasses)
        
        Args:
            processed_data: Data from document processor
            source: Original source URL/path
            metadata: Additional metadata
            
        Returns:
            List of document dictionaries
        """
        documents = []
        parsed_content = processed_data.get("parsed_content", {})
        base_metadata = {
            "source": source,
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "format": processed_data.get("format", "unknown"),
            **(metadata or {})
        }
        
        # Handle different content types
        if isinstance(parsed_content, dict) and "content" in parsed_content:
            content = parsed_content["content"]
            # Split into chunks
            chunks = self._chunk_content(content)
            
            for i, chunk in enumerate(chunks):
                if len(chunk.strip()) > 50:  # Skip very short chunks
                    doc = {
                        "id": str(uuid.uuid4()),  # Use proper UUID
                        "content": chunk.strip(),
                        "metadata": {
                            **base_metadata,
                            "chunk_id": i,
                            "chunk_count": len(chunks)
                        }
                    }
                    documents.append(doc)
        
        # Handle API endpoints if present
        if isinstance(parsed_content, dict) and "api_endpoints" in parsed_content:
            endpoints = parsed_content["api_endpoints"]
            for i, endpoint in enumerate(endpoints):
                doc = {
                    "id": str(uuid.uuid4()),
                    "content": f"API Endpoint: {endpoint.get('method', 'GET')} {endpoint.get('path', '')}\\n{endpoint.get('description', '')}",
                    "metadata": {
                        **base_metadata,
                        "type": "api_endpoint",
                        "method": endpoint.get("method", "GET"),
                        "path": endpoint.get("path", ""),
                        "endpoint_id": i
                    }
                }
                documents.append(doc)
        
        # Fallback: create single document
        if not documents:
            doc = {
                "id": str(uuid.uuid4()),
                "content": str(parsed_content),
                "metadata": {
                    **base_metadata,
                    "type": "full_content"
                }
            }
            documents = [doc]
            
        return documents
    
    def _chunk_content(self, content: str, chunk_size: int = 1000, overlap: int = 100) -> List[str]:
        """
        Chunk content into smaller pieces (can be overridden in subclasses)
        
        Args:
            content: Text content to chunk
            chunk_size: Maximum size of each chunk
            overlap: Overlap between chunks
            
        Returns:
            List of text chunks
        """
        # Simple chunking strategy - can be enhanced in subclasses
        if len(content) <= chunk_size:
            return [content]
            
        chunks = []
        start = 0
        
        while start < len(content):
            end = start + chunk_size
            if end >= len(content):
                chunks.append(content[start:])
                break
                
            # Try to find a good breaking point
            break_point = content.rfind('. ', start, end)
            if break_point == -1:
                break_point = content.rfind(' ', start, end)
            if break_point == -1:
                break_point = end
                
            chunks.append(content[start:break_point])
            start = break_point - overlap if break_point > overlap else break_point
            
        return chunks
    
    async def query(self, 
                   query: str, 
                   top_k: int = 5,
                   search_type: str = "hybrid",
                   include_sources: bool = True) -> Dict[str, Any]:
        """
        Query the RAG system
        
        Args:
            query: The question/query string
            top_k: Number of results to return
            search_type: Type of search ("hybrid", "vector", "bm25")
            include_sources: Whether to include source information
            
        Returns:
            Dict with answer, sources, and metadata
        """
        self._ensure_initialized()
        
        # Pre-process query (can be overridden)
        processed_query = self.preprocess_query(query)
        
        # Search for relevant documents
        search_results = await self._search_engine.search(
            processed_query, top_k, search_type
        )
        
        if not search_results:
            return {
                "answer": "I couldn't find any relevant information to answer your question.",
                "query": query,
                "sources": [],
                "confidence": 0.0
            }
        
        # Generate answer
        answer_data = await self._search_engine.generate_answer(
            processed_query, search_results
        )
        
        result = {
            "answer": answer_data.get("answer", ""),
            "query": query,
            "confidence": answer_data.get("confidence", 0.0),
            "search_results_count": len(search_results)
        }
        
        if include_sources:
            result["sources"] = [
                {
                    "content": result.get("content", "")[:200] + "..." if len(result.get("content", "")) > 200 else result.get("content", ""),
                    "metadata": result.get("metadata", {}),
                    "score": result.get("score", 0.0)
                }
                for result in search_results[:3]  # Top 3 sources
            ]
            
        return result
    
    def preprocess_query(self, query: str) -> str:
        """
        Preprocess query before search (can be overridden in subclasses)
        
        Args:
            query: Original query string
            
        Returns:
            Processed query string
        """
        # Default implementation - just return the query as-is
        # Subclasses can override this for custom preprocessing
        return query.strip()
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get system statistics
        
        Returns:
            Dict with system statistics
        """
        self._ensure_initialized()
        
        search_stats = await self._search_engine.get_stats()
        
        return {
            "system_status": "initialized" if self._is_initialized else "not_initialized",
            "config": {
                "vector_store_type": self.config.vector_store.store_type.value,
                "llm_provider": self.config.llm.provider.value,
                "embedding_provider": self.config.embedding.provider.value,
                "hybrid_search_enabled": self.config.search.enable_hybrid
            },
            "search_engine": search_stats
        }
    
    async def reset(self) -> None:
        """
        Reset the RAG system (clear all documents)
        """
        self._ensure_initialized()
        await self._search_engine.reset()
        
    async def close(self) -> None:
        """
        Clean up resources
        """
        if self._search_engine:
            await self._search_engine.close()
        if self._document_processor:
            await self._document_processor.close()
        self._is_initialized = False


# Convenience function for quick setup
async def create_rag_system(config_name: str = "local") -> RAGSystem:
    """
    Create and initialize a RAG system with preset configuration
    
    Args:
        config_name: Preset config name ("local", "cloud", "high_performance")
        
    Returns:
        Initialized RAG system
    """
    config_map = {
        "local": PresetConfigs.local_development(),
        "cloud": PresetConfigs.cloud_openai(),
        "high_performance": PresetConfigs.high_performance()
    }
    
    config = config_map.get(config_name, PresetConfigs.local_development())
    rag = RAGSystem(config=config)
    await rag.initialize()
    return rag