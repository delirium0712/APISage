"""
Search Engine SDK interface - wrapper around vector stores and LLM functionality
"""

import sys
import os
import uuid
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone

# Add the project root to the path to access existing modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infrastructure.vector_stores.hybrid_store import HybridVectorStore, HybridSearchConfig
from infrastructure.vector_stores.base_store import VectorStoreConfig, VectorStoreType, Document
from infrastructure.vector_stores.store_factory import VectorStoreFactory
from infrastructure.llm_providers.provider_factory import LLMProviderFactory
from langchain_community.embeddings import HuggingFaceEmbeddings
from .config import RAGConfig


class SearchEngine:
    """
    SDK wrapper for search and retrieval functionality.
    
    This class provides a clean interface for search operations while wrapping
    the existing infrastructure. Can be extended for custom search strategies.
    
    Example:
        # Basic usage
        engine = SearchEngine(config)
        await engine.initialize()
        results = await engine.search("What is this about?")
        
        # Extended usage
        class MySearchEngine(SearchEngine):
            def preprocess_query(self, query: str) -> str:
                return f"enhanced: {query}"
                
            async def search(self, query, top_k=5, search_type="hybrid"):
                enhanced_query = self.preprocess_query(query)
                return await super().search(enhanced_query, top_k, search_type)
    """
    
    def __init__(self, config: RAGConfig):
        """
        Initialize the search engine
        
        Args:
            config: RAG configuration object
        """
        self.config = config
        self._vector_store: Optional[HybridVectorStore] = None
        self._embeddings = None
        self._llm = None
        self._is_initialized = False
    
    async def initialize(self) -> None:
        """
        Initialize the search engine components
        """
        if self._is_initialized:
            return
            
        # Initialize embeddings
        await self._init_embeddings()
        
        # Initialize vector store
        await self._init_vector_store()
        
        # Initialize LLM
        await self._init_llm()
        
        self._is_initialized = True
    
    async def _init_embeddings(self):
        """Initialize embedding model"""
        embedding_config = self.config.embedding
        
        if embedding_config.provider.value == "huggingface":
            self._embeddings = HuggingFaceEmbeddings(
                model_name=embedding_config.model_name,
                model_kwargs={'device': embedding_config.device},
                encode_kwargs={'normalize_embeddings': embedding_config.normalize_embeddings}
            )
        else:
            # Could extend to support other embedding providers
            raise ValueError(f"Embedding provider {embedding_config.provider.value} not yet supported in SDK")
    
    async def _init_vector_store(self):
        """Initialize vector store with hybrid capabilities"""
        vs_config = self.config.vector_store
        
        # Create vector store configuration
        vector_store_config = VectorStoreConfig(
            store_type=VectorStoreType(vs_config.store_type.value),
            collection_name=vs_config.collection_name,
            host=vs_config.host,
            port=vs_config.port,
            embedding_dim=vs_config.embedding_dim,
            distance_metric=vs_config.distance_metric,
            api_key=vs_config.api_key
        )
        
        # Create hybrid search configuration
        search_config = self.config.search
        hybrid_config = HybridSearchConfig(
            vector_weight=search_config.vector_weight,
            lexical_weight=search_config.lexical_weight,
            rerank_top_k=search_config.rerank_top_k,
            final_top_k=search_config.final_top_k,
            enable_hybrid=search_config.enable_hybrid,
            enable_reranking=search_config.enable_reranking
        )
        
        # Create hybrid vector store
        self._vector_store = HybridVectorStore(
            vector_store_config, 
            self._embeddings, 
            hybrid_config
        )
        await self._vector_store.initialize()
    
    async def _init_llm(self):
        """Initialize LLM provider"""
        llm_config = self.config.llm
        
        try:
            # Use the existing LLM provider factory
            self._llm = LLMProviderFactory.create_provider(
                provider_type=llm_config.provider.value,
                model_name=llm_config.model_name,
                base_url=llm_config.base_url,
                api_key=llm_config.api_key,
                temperature=llm_config.temperature,
                max_tokens=llm_config.max_tokens,
                extra_params=llm_config.extra_params or {}
            )
        except Exception as e:
            # Fallback for simple Ollama setup
            if llm_config.provider.value == "ollama":
                from langchain_ollama import OllamaLLM
                self._llm = OllamaLLM(
                    model=llm_config.model_name,
                    base_url=llm_config.base_url,
                    temperature=llm_config.temperature
                )
            else:
                raise e
    
    def _ensure_initialized(self):
        """Ensure the search engine is initialized"""
        if not self._is_initialized:
            raise RuntimeError(
                "Search engine not initialized. Call 'await engine.initialize()' first."
            )
    
    async def add_documents(self, documents: List[Union[Dict[str, Any], Document]]) -> Dict[str, Any]:
        """
        Add documents to the search index
        
        Args:
            documents: List of document dictionaries or Document objects
            
        Returns:
            Dict with indexing results
        """
        self._ensure_initialized()
        
        # Convert dict documents to Document objects if needed
        doc_objects = []
        for doc in documents:
            if isinstance(doc, dict):
                # Ensure proper UUID format for IDs
                doc_id = doc.get("id", str(uuid.uuid4()))
                if not self._is_valid_uuid_or_int(doc_id):
                    doc_id = str(uuid.uuid4())
                
                doc_obj = Document(
                    id=doc_id,
                    content=doc.get("content", ""),
                    metadata=doc.get("metadata", {})
                )
            else:
                doc_obj = doc
                # Fix ID format if needed
                if not self._is_valid_uuid_or_int(doc_obj.id):
                    doc_obj.id = str(uuid.uuid4())
            
            doc_objects.append(doc_obj)
        
        try:
            await self._vector_store.add_documents(doc_objects)
            return {
                "success": True,
                "documents_added": len(doc_objects),
                "total_documents": await self._get_document_count()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "documents_attempted": len(doc_objects)
            }
    
    def _is_valid_uuid_or_int(self, value: str) -> bool:
        """Check if value is a valid UUID or integer"""
        try:
            # Try UUID
            uuid.UUID(value)
            return True
        except ValueError:
            try:
                # Try integer
                int(value)
                return True
            except ValueError:
                return False
    
    async def search(self, 
                    query: str, 
                    top_k: int = 5,
                    search_type: str = "hybrid") -> List[Dict[str, Any]]:
        """
        Search for relevant documents
        
        Args:
            query: Search query
            top_k: Number of results to return
            search_type: Type of search ("hybrid", "vector", "bm25")
            
        Returns:
            List of search results
        """
        self._ensure_initialized()
        
        # Preprocess query (can be overridden)
        processed_query = self.preprocess_query(query)
        
        # Configure search type
        original_config = self._configure_search_type(search_type)
        
        try:
            # Perform search
            results = await self._vector_store.search(processed_query, k=top_k)
            
            # Convert results to dict format for SDK consistency
            formatted_results = []
            for result in results:
                formatted_result = {
                    "content": result.document.content,
                    "metadata": result.document.metadata,
                    "score": result.score,
                    "id": result.document.id
                }
                formatted_results.append(formatted_result)
            
            return formatted_results
            
        except Exception as e:
            # Log error and return empty results
            print(f"Search error: {e}")
            return []
        finally:
            # Restore original configuration
            self._restore_search_config(original_config)
    
    def preprocess_query(self, query: str) -> str:
        """
        Preprocess query before search (can be overridden in subclasses)
        
        Args:
            query: Original query
            
        Returns:
            Processed query
        """
        # Default implementation - basic cleaning
        return query.strip()
    
    def _configure_search_type(self, search_type: str) -> Dict[str, Any]:
        """Configure vector store for specific search type"""
        if not self._vector_store or not hasattr(self._vector_store, 'hybrid_config'):
            return {}
            
        # Store original configuration
        original_config = {
            "enable_hybrid": self._vector_store.hybrid_config.enable_hybrid,
            "vector_weight": self._vector_store.hybrid_config.vector_weight,
            "lexical_weight": self._vector_store.hybrid_config.lexical_weight
        }
        
        # Configure based on search type
        if search_type == "vector":
            self._vector_store.hybrid_config.enable_hybrid = True
            self._vector_store.hybrid_config.vector_weight = 1.0
            self._vector_store.hybrid_config.lexical_weight = 0.0
        elif search_type == "bm25":
            self._vector_store.hybrid_config.enable_hybrid = False
        elif search_type == "hybrid":
            self._vector_store.hybrid_config.enable_hybrid = True
            # Use configured weights
            
        return original_config
    
    def _restore_search_config(self, original_config: Dict[str, Any]):
        """Restore original search configuration"""
        if not self._vector_store or not hasattr(self._vector_store, 'hybrid_config'):
            return
            
        if original_config:
            self._vector_store.hybrid_config.enable_hybrid = original_config["enable_hybrid"]
            self._vector_store.hybrid_config.vector_weight = original_config["vector_weight"]
            self._vector_store.hybrid_config.lexical_weight = original_config["lexical_weight"]
    
    async def generate_answer(self, query: str, search_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate an answer based on search results
        
        Args:
            query: Original query
            search_results: Results from search
            
        Returns:
            Dict with generated answer and metadata
        """
        self._ensure_initialized()
        
        if not search_results:
            return {
                "answer": "I couldn't find any relevant information to answer your question.",
                "confidence": 0.0,
                "sources_used": 0
            }
        
        # Prepare context from search results
        context_parts = []
        for result in search_results[:3]:  # Use top 3 results
            content = result.get("content", "")
            if content:
                context_parts.append(content)
        
        context = "\\n\\n".join(context_parts)
        
        # Create prompt (can be overridden in subclasses)
        prompt = self.create_answer_prompt(query, context)
        
        try:
            # Generate answer using LLM
            if hasattr(self._llm, 'ainvoke'):
                response = await self._llm.ainvoke(prompt)
            else:
                response = self._llm.invoke(prompt)
            
            answer = str(response).strip()
            
            # Calculate confidence based on search scores
            avg_score = sum(r.get("score", 0) for r in search_results[:3]) / min(3, len(search_results))
            confidence = min(avg_score * 2, 1.0)  # Simple confidence calculation
            
            return {
                "answer": answer,
                "confidence": confidence,
                "sources_used": len(context_parts),
                "context_length": len(context)
            }
            
        except Exception as e:
            return {
                "answer": f"I encountered an error while generating the answer: {str(e)}",
                "confidence": 0.0,
                "sources_used": 0,
                "error": str(e)
            }
    
    def create_answer_prompt(self, query: str, context: str) -> str:
        """
        Create prompt for answer generation (can be overridden in subclasses)
        
        Args:
            query: User query
            context: Retrieved context
            
        Returns:
            Formatted prompt
        """
        return f"""Based on the following context, answer the question. If the context doesn't contain enough information, say so clearly.

Context:
{context}

Question: {query}

Please provide a clear, helpful answer based on the context above. If the context doesn't contain sufficient information to fully answer the question, explain what information is available and what might be missing.

Answer:"""
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get search engine statistics
        
        Returns:
            Dict with statistics
        """
        self._ensure_initialized()
        
        try:
            store_stats = await self._vector_store.get_collection_stats()
            return {
                "initialized": True,
                "total_documents": await self._get_document_count(),
                "vector_store_stats": store_stats,
                "config": {
                    "hybrid_enabled": self.config.search.enable_hybrid,
                    "vector_weight": self.config.search.vector_weight,
                    "lexical_weight": self.config.search.lexical_weight,
                    "reranking_enabled": self.config.search.enable_reranking
                }
            }
        except Exception as e:
            return {
                "initialized": True,
                "error": str(e),
                "config": {
                    "hybrid_enabled": self.config.search.enable_hybrid,
                    "vector_weight": self.config.search.vector_weight,
                    "lexical_weight": self.config.search.lexical_weight
                }
            }
    
    async def _get_document_count(self) -> int:
        """Get total document count"""
        try:
            stats = await self._vector_store.get_collection_stats()
            return stats.get("total_documents", 0)
        except:
            return 0
    
    async def reset(self) -> None:
        """
        Reset the search index (remove all documents)
        """
        self._ensure_initialized()
        # Implementation would depend on vector store capabilities
        # For now, just reinitialize
        await self._vector_store.initialize()
    
    async def close(self) -> None:
        """
        Clean up resources
        """
        if self._vector_store:
            # Close vector store if it has a close method
            if hasattr(self._vector_store, 'close'):
                await self._vector_store.close()
        
        self._vector_store = None
        self._embeddings = None
        self._llm = None
        self._is_initialized = False


class SemanticSearchEngine(SearchEngine):
    """
    Search engine specialized for semantic search
    """
    
    def preprocess_query(self, query: str) -> str:
        """Enhanced query preprocessing for semantic search"""
        # Add semantic-specific preprocessing
        query = query.strip()
        # Could add query expansion, synonym handling, etc.
        return query
    
    def create_answer_prompt(self, query: str, context: str) -> str:
        """Enhanced prompt for semantic understanding"""
        return f"""You are a helpful assistant that provides accurate answers based on the given context. Focus on semantic meaning and provide comprehensive answers.

Context:
{context}

Question: {query}

Instructions:
1. Provide a detailed answer based on the context
2. If the context is incomplete, explain what additional information would be helpful
3. Use the context to provide specific examples or details when possible
4. Maintain accuracy and don't make assumptions beyond the provided context

Answer:"""


class TechnicalSearchEngine(SearchEngine):
    """
    Search engine specialized for technical documentation
    """
    
    def preprocess_query(self, query: str) -> str:
        """Enhanced query preprocessing for technical content"""
        query = query.strip()
        # Could add technical term normalization, API-specific preprocessing
        return query
    
    def create_answer_prompt(self, query: str, context: str) -> str:
        """Technical documentation focused prompt"""
        return f"""You are a technical documentation assistant. Provide precise, actionable answers based on the given context.

Technical Documentation Context:
{context}

Technical Query: {query}

Instructions:
1. Provide step-by-step instructions when applicable
2. Include code examples, API endpoints, or configuration details from the context
3. If the context contains partial information, clearly state what's provided and what might be missing
4. Use technical terminology appropriately
5. Structure your response for easy scanning (use bullet points, numbered lists when helpful)

Technical Answer:"""