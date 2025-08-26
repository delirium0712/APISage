"""
Hybrid search store combining BM25 lexical search with vector search and configurable reranking
"""

import asyncio
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
import structlog
import re
from collections import Counter
import math

from .base_store import BaseVectorStore, Document, SearchResult, VectorStoreConfig, VectorStoreType
# Removed: from .store_factory import VectorStoreFactory (to fix circular import)
from .chroma_store import ChromaStore # Added for direct import
from .qdrant_store import QdrantStore # Added for direct import
from .milvus_store import MilvusStore # Added for direct import
from .pinecone_store import PineconeStore # Added for direct import
from ..rerankers.reranker_factory import RerankerFactory
from ..rerankers.base_reranker import RerankerConfig


logger = structlog.get_logger()


@dataclass
class HybridSearchConfig:
    """Configuration for hybrid search"""
    vector_weight: float = 0.6  # Weight for vector search results
    lexical_weight: float = 0.4  # Weight for BM25 search results
    rerank_top_k: int = 20  # Number of candidates to rerank
    final_top_k: int = 5  # Final number of results to return
    enable_hybrid: bool = True  # Enable hybrid search
    enable_reranking: bool = True  # Enable result reranking
    bm25_k1: float = 1.2 # BM25 k1 parameter
    bm25_b: float = 0.75 # BM25 b parameter
    rrf_k: float = 60.0  # RRF constant (typically 60)
    
    # Reranking configuration
    reranker_pipeline: str = "default"  # Default reranker pipeline
    enable_llm_reranking: bool = True  # Enable LLM-based reranking
    enable_semantic_reranking: bool = True  # Enable semantic reranking
    enable_api_docs_reranking: bool = True  # Enable API docs reranking
    reranker_context: Dict[str, Any] = None  # Context for rerankers


class BM25Search:
    """BM25 lexical search implementation"""

    def __init__(self, k1: float = 1.2, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.documents: List[Document] = []
        self.doc_lengths: List[int] = []
        self.avg_doc_length = 0.0
        self.term_freq: Dict[str, Dict[int, int]] = {}  # term -> {doc_id -> freq}
        self.doc_freq: Dict[str, int] = {}  # term -> number of docs containing term
        self.total_docs = 0

    def add_documents(self, documents: List[Document]):
        """Add documents to the BM25 index"""
        self.documents = documents
        self.total_docs = len(documents)

        # Calculate document lengths
        self.doc_lengths = [len(doc.content.split()) for doc in documents]
        self.avg_doc_length = sum(self.doc_lengths) / self.total_docs if self.total_docs > 0 else 0

        # Build term frequency and document frequency indexes
        self.term_freq = {}
        self.doc_freq = {}

        for doc_idx, doc in enumerate(documents):
            terms = self._tokenize(doc.content)
            term_counts = Counter(terms)

            for term, freq in term_counts.items():
                if term not in self.term_freq:
                    self.term_freq[term] = {}
                self.term_freq[term][doc_idx] = freq

                if term not in self.doc_freq:
                    self.doc_freq[term] = 0
                self.doc_freq[term] += 1

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into terms"""
        # Simple tokenization - split on whitespace and remove punctuation
        terms = re.findall(r'\b\w+\b', text.lower())
        # Filter out very short terms and common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        return [term for term in terms if len(term) > 2 and term not in stop_words]

    def search(self, query: str, k: int = 5) -> List[tuple[int, float]]:
        """Search using BM25 algorithm"""
        query_terms = self._tokenize(query)

        if not query_terms:
            return []

        scores = []

        for doc_idx in range(self.total_docs):
            score = 0.0

            for term in query_terms:
                if term in self.term_freq and doc_idx in self.term_freq[term]:
                    # Calculate BM25 score
                    tf = self.term_freq[term][doc_idx]
                    df = self.doc_freq[term]
                    doc_len = self.doc_lengths[doc_idx]

                    # BM25 formula
                    numerator = tf * (self.k1 + 1)
                    denominator = tf + self.k1 * (1 - self.b + self.b * (doc_len / self.avg_doc_length))

                    idf = math.log((self.total_docs - df + 0.5) / (df + 0.5) + 1)
                    term_score = idf * (numerator / denominator)
                    score += term_score

            if score > 0:
                scores.append((doc_idx, score))

        # Sort by score and return top k
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:k]


class RRF:
    """Reciprocal Rank Fusion implementation"""
    
    def __init__(self, k: float = 60.0):
        """
        Initialize RRF with constant k
        
        Args:
            k: RRF constant (typically 60, higher values give more weight to top-ranked items)
        """
        self.k = k
    
    def fuse_rankings(self, rankings: List[List[SearchResult]], 
                      query: str, 
                      final_k: int = 5) -> List[SearchResult]:
        """
        Fuse multiple rankings using Reciprocal Rank Fusion
        
        Args:
            rankings: List of ranked result lists from different search methods
            query: Original search query
            final_k: Number of final results to return
            
        Returns:
            Fused and reranked results
        """
        if not rankings or not any(rankings):
            return []
        
        # Create document ID to RRF score mapping
        doc_scores = {}
        
        # Process each ranking
        for ranking_idx, ranking in enumerate(rankings):
            if not ranking:
                continue
                
            for rank, result in enumerate(ranking):
                doc_id = result.document.id
                
                # Calculate RRF score: 1 / (k + rank)
                rrf_score = 1.0 / (self.k + rank + 1)  # +1 because rank is 0-indexed
                
                if doc_id not in doc_scores:
                    doc_scores[doc_id] = {
                        'document': result.document,
                        'rrf_score': 0.0,
                        'ranks': [],
                        'scores': []
                    }
                
                doc_scores[doc_id]['rrf_score'] += rrf_score
                doc_scores[doc_id]['ranks'].append(rank + 1)  # Store 1-indexed rank
                doc_scores[doc_id]['scores'].append(result.score)
        
        # Convert to SearchResult objects and sort by RRF score
        fused_results = []
        for doc_id, data in doc_scores.items():
            # Create a new SearchResult with RRF score
            fused_result = SearchResult(
                document=data['document'],
                score=data['rrf_score']
            )
            
            # Add metadata about the fusion
            fused_result.metadata = {
                'rrf_score': data['rrf_score'],
                'ranks': data['ranks'],
                'original_scores': data['scores'],
                'fusion_method': 'RRF',
                'k_constant': self.k
            }
            
            fused_results.append(fused_result)
        
        # Sort by RRF score (descending) and return top k
        fused_results.sort(key=lambda x: x.score, reverse=True)
        return fused_results[:final_k]


class HybridVectorStore(BaseVectorStore):
    """Hybrid search store combining BM25 and vector search with configurable reranking"""

    def __init__(self, config: VectorStoreConfig, embeddings_function=None, hybrid_config: HybridSearchConfig = None):
        super().__init__(config, embeddings_function)
        self.hybrid_config = hybrid_config or HybridSearchConfig()
        self.bm25_search = BM25Search(k1=self.hybrid_config.bm25_k1, b=self.hybrid_config.bm25_b)
        self.vector_store: Optional[BaseVectorStore] = None
        self.documents: List[Document] = []
        self.logger = structlog.get_logger(component="HybridVectorStore")
        
        # Initialize RRF reranker
        self.rrf_reranker = RRF(k=self.hybrid_config.rrf_k)
        
        # Initialize reranker factory
        self.reranker_factory = RerankerFactory()
        self.rerankers_initialized = False

    async def initialize(self) -> bool:
        """Initialize the hybrid store"""
        try:
            # Initialize the underlying vector store
            if self.config.store_type != VectorStoreType.MEMORY:
                try:
                    if self.config.store_type == VectorStoreType.QDRANT:
                        from .qdrant_store import QdrantStore
                        self.vector_store = QdrantStore(self.config, self.embeddings_function)
                    elif self.config.store_type == VectorStoreType.CHROMA:
                        from .chroma_store import ChromaStore
                        self.vector_store = ChromaStore(self.config, self.embeddings_function)
                    elif self.config.store_type == VectorStoreType.MILVUS:
                        from .milvus_store import MilvusStore
                        self.vector_store = MilvusStore(self.config, self.embeddings_function)
                    elif self.config.store_type == VectorStoreType.PINECONE:
                        from .pinecone_store import PineconeStore
                        self.vector_store = PineconeStore(self.config, self.embeddings_function)

                    if self.vector_store:
                        await self.vector_store.initialize()
                    else:
                        self.logger.warning("Failed to initialize vector store, falling back to memory-only")
                        self.config.store_type = VectorStoreType.MEMORY
                except Exception as e:
                    self.logger.warning(f"Failed to initialize vector store: {e}, falling back to memory-only")
                    self.config.store_type = VectorStoreType.MEMORY

            # Initialize BM25
            self.bm25_search = BM25Search(k1=self.hybrid_config.bm25_k1, b=self.hybrid_config.bm25_b)

            # Initialize rerankers
            await self._initialize_rerankers()

            self.logger.info("hybrid_store_initialized",
                           vector_store_type=self.config.store_type.value,
                           hybrid_enabled=self.hybrid_config.enable_hybrid,
                           rrf_enabled=True,
                           rrf_k=self.hybrid_config.rrf_k,
                           rerankers_initialized=self.rerankers_initialized)
            return True

        except Exception as e:
            self.logger.error("hybrid_store_init_failed", error=str(e))
            return False

    async def _initialize_rerankers(self):
        """Initialize the reranker system"""
        try:
            # Create default reranker configurations
            default_configs = self.reranker_factory.create_default_configs()
            
            # Initialize rerankers
            await self.reranker_factory.initialize_rerankers(
                configs=list(default_configs.values()),
                llm_provider_factory=None,  # Will be set later if needed
                embeddings_function=self.embeddings_function
            )
            
            self.rerankers_initialized = True
            self.logger.info("rerankers_initialized", count=len(default_configs))
            
        except Exception as e:
            self.logger.warning("reranker_initialization_failed", error=str(e))
            self.rerankers_initialized = False

    async def create_collection(self, name: str = None) -> bool:
        """Create collection in underlying vector store"""
        if self.vector_store:
            return await self.vector_store.create_collection(name)
        return True

    async def add_documents(self, documents: List[Document]) -> bool:
        """Add documents to both BM25 and vector stores"""
        try:
            # Add to BM25 index
            self.bm25_search.add_documents(documents)
            self.documents.extend(documents)

            # Add to vector store if available
            if self.vector_store:
                await self.vector_store.add_documents(documents)

            self.logger.info("documents_added",
                           count=len(documents),
                           total_docs=len(self.documents))
            return True

        except Exception as e:
            self.logger.error("failed_to_add_documents", error=str(e))
            return False

    async def search(self, query: str, k: int = 5, filter_metadata: Dict[str, Any] = None) -> List[SearchResult]:
        """Perform hybrid search combining BM25 and vector search with configurable reranking"""
        if not self.hybrid_config.enable_hybrid:
            # Fallback to vector search only
            if self.vector_store:
                return await self.vector_store.search(query, k, filter_metadata)
            else:
                return await self._bm25_only_search(query, k, filter_metadata)

        try:
            # Perform both searches
            vector_results = []
            bm25_results = []

            # Vector search
            if self.vector_store:
                vector_results = await self.vector_store.search(query, self.hybrid_config.rerank_top_k, filter_metadata)

            # BM25 search
            bm25_scores = self.bm25_search.search(query, self.hybrid_config.rerank_top_k)
            bm25_results = []
            for doc_idx, score in bm25_scores:
                if doc_idx < len(self.documents):
                    doc = self.documents[doc_idx]
                    bm25_results.append(SearchResult(document=doc, score=score))

            # Use configurable reranking if enabled
            if self.hybrid_config.enable_reranking and self.rerankers_initialized:
                combined_results = await self._configurable_rerank(
                    query, vector_results, bm25_results, k, filter_metadata
                )
            else:
                # Fallback to RRF reranking
                combined_results = await self._rrf_rerank(
                    query, vector_results, bm25_results, k
                )

            self.logger.info("hybrid_search_completed",
                           query=query,
                           vector_results=len(vector_results),
                           bm25_results=len(bm25_results),
                           final_results=len(combined_results),
                           reranking_method="configurable" if self.hybrid_config.enable_reranking else "RRF")

            return combined_results

        except Exception as e:
            self.logger.error("hybrid_search_failed", error=str(e))
            # Fallback to BM25 only
            return await self._bm25_only_search(query, k, filter_metadata)

    async def _configurable_rerank(self, 
                                 query: str, 
                                 vector_results: List[SearchResult],
                                 bm25_results: List[SearchResult], 
                                 k: int,
                                 filter_metadata: Dict[str, Any] = None) -> List[SearchResult]:
        """Rerank results using the configurable reranker pipeline"""
        
        try:
            # Get the reranker pipeline
            pipeline = self.reranker_factory.get_reranker_pipeline(self.hybrid_config.reranker_pipeline)
            
            if not pipeline:
                self.logger.warning("no_reranker_pipeline_available", pipeline_name=self.hybrid_config.reranker_pipeline)
                return await self._rrf_rerank(query, vector_results, bm25_results, k)
            
            # Combine results for reranking
            all_results = []
            
            # Add vector results with metadata
            for result in vector_results:
                result.metadata = result.metadata or {}
                result.metadata['source'] = 'vector_search'
                all_results.append(result)
            
            # Add BM25 results with metadata
            for result in bm25_results:
                result.metadata = result.metadata or {}
                result.metadata['source'] = 'bm25_search'
                all_results.append(result)
            
            # Remove duplicates based on document ID
            unique_results = {}
            for result in all_results:
                doc_id = result.document.id
                if doc_id not in unique_results or result.score > unique_results[doc_id].score:
                    unique_results[doc_id] = result
            
            unique_results_list = list(unique_results.values())
            
            # Apply reranker pipeline
            current_results = unique_results_list
            reranking_context = self.hybrid_config.reranker_context or {}
            reranking_context['query'] = query
            reranking_context['filter_metadata'] = filter_metadata
            
            for reranker in pipeline:
                if reranker.is_enabled():
                    try:
                        current_results = await reranker.rerank(query, current_results, reranking_context)
                        self.logger.debug("reranker_applied",
                                        reranker_name=reranker.config.name,
                                        reranker_type=reranker.config.reranker_type,
                                        results_count=len(current_results))
                    except Exception as e:
                        self.logger.warning("reranker_failed",
                                          reranker_name=reranker.config.name,
                                          error=str(e))
                        # Continue with next reranker
            
            # Return top k results
            return current_results[:k]
            
        except Exception as e:
            self.logger.error("configurable_reranking_failed", error=str(e))
            # Fallback to RRF
            return await self._rrf_rerank(query, vector_results, bm25_results, k)

    async def _rrf_rerank(self, query: str, vector_results: List[SearchResult],
                          bm25_results: List[SearchResult], k: int) -> List[SearchResult]:
        """Rerank results using Reciprocal Rank Fusion"""
        
        # Prepare rankings for RRF
        rankings = []
        
        if vector_results:
            rankings.append(vector_results)
        if bm25_results:
            rankings.append(bm25_results)
        
        # Use RRF to fuse rankings
        fused_results = self.rrf_reranker.fuse_rankings(
            rankings=rankings,
            query=query,
            final_k=k
        )
        
        self.logger.info("rrf_reranking_completed",
                        query=query,
                        input_rankings=len(rankings),
                        output_results=len(fused_results),
                        rrf_k=self.hybrid_config.rrf_k)
        
        return fused_results

    async def _combineAnd_rerank(self, query: str, vector_results: List[SearchResult],
                                bm25_results: List[SearchResult], k: int) -> List[SearchResult]:
        """Legacy weighted combination method (kept for fallback)"""
        # Create a mapping of document ID to scores
        doc_scores = {}

        # Add vector search scores
        for result in vector_results:
            doc_id = result.document.id
            if doc_id not in doc_scores:
                doc_scores[doc_id] = {'vector_score': 0.0, 'bm25_score': 0.0, 'document': result.document}
            doc_scores[doc_id]['vector_score'] = result.score

        # Add BM25 search scores
        for result in bm25_results:
            doc_id = result.document.id
            if doc_id not in doc_scores:
                doc_scores[doc_id] = {'vector_score': 0.0, 'bm25_score': 0.0, 'document': result.document}
            doc_scores[doc_id]['bm25_score'] = result.score

        # Normalize scores to 0-1 range
        max_vector_score = max([scores['vector_score'] for scores in doc_scores.values()]) if doc_scores else 1.0
        max_bm25_score = max([scores['bm25_score'] for scores in doc_scores.values()]) if doc_scores else 1.0

        # Calculate combined scores
        combined_results = []
        for doc_id, scores in doc_scores.items():
            if max_vector_score > 0:
                normalized_vector = scores['vector_score'] / max_vector_score
            else:
                normalized_vector = 0.0

            if max_bm25_score > 0:
                normalized_bm25 = scores['bm25_score'] / max_bm25_score
            else:
                normalized_bm25 = 0.0

            # Weighted combination
            combined_score = (self.hybrid_config.vector_weight * normalized_vector +
                            self.hybrid_config.lexical_weight * normalized_bm25)

            combined_results.append(SearchResult(
                document=scores['document'],
                score=combined_score
            ))

        # Sort by combined score and return top k
        combined_results.sort(key=lambda x: x.score, reverse=True)
        return combined_results[:k]

    async def _bm25_only_search(self, query: str, k: int, filter_metadata: Dict[str, Any] = None) -> List[SearchResult]:
        """Fallback to BM25 search only"""
        bm25_scores = self.bm25_search.search(query, k)
        results = []

        for doc_idx, score in bm25_scores:
            if doc_idx < len(self.documents):
                doc = self.documents[doc_idx]
                # Apply metadata filtering if specified
                if filter_metadata and not self._matches_filter(doc, filter_metadata):
                    continue
                results.append(SearchResult(document=doc, score=score))

        return results

    def _matches_filter(self, document: Document, filter_metadata: Dict[str, Any]) -> bool:
        """Check if document matches metadata filter"""
        for key, value in filter_metadata.items():
            if key not in document.metadata or document.metadata[key] != value:
                return False
        return True

    async def search_by_vector(self, vector: List[float], k: int = 5, filter_metadata: Dict[str, Any] = None) -> List[SearchResult]:
        """Search by vector (delegate to underlying vector store)"""
        if self.vector_store:
            return await self.vector_store.search_by_vector(vector, k, filter_metadata)
        return []

    async def delete_documents(self, document_ids: List[str]) -> bool:
        """Delete documents from both stores"""
        try:
            # Remove from BM25 index
            self.documents = [doc for doc in self.documents if doc.id not in document_ids]
            self.bm25_search.add_documents(self.documents)  # Rebuild index

            # Remove from vector store
            if self.vector_store:
                await self.vector_store.delete_documents(document_ids)

            return True
        except Exception as e:
            self.logger.error("failed_to_delete_documents", error=str(e))
            return False

    async def update_document(self, document: Document) -> bool:
        """Update document in both stores"""
        try:
            # Update in BM25 index
            for i, doc in enumerate(self.documents):
                if doc.id == document.id:
                    self.documents[i] = document
                    break
            self.bm25_search.add_documents(self.documents)  # Rebuild index

            # Update in vector store
            if self.vector_store:
                await self.vector_store.update_document(document)

            return True
        except Exception as e:
            self.logger.error("failed_to_update_document", error=str(e))
            return False

    async def get_document(self, document_id: str) -> Optional[Document]:
        """Get a document by ID"""
        for doc in self.documents:
            if doc.id == document_id:
                return doc
        return None

    async def list_collections(self) -> List[str]:
        """List collections from underlying vector store"""
        if self.vector_store:
            return await self.vector_store.list_collections()
        return [self.config.collection_name]

    async def delete_collection(self, name: str = None) -> bool:
        """Delete collection from underlying vector store"""
        if self.vector_store:
            return await self.vector_store.delete_collection(name)
        return True

    async def get_collection_stats(self, name: str = None) -> Dict[str, Any]:
        """Get collection statistics"""
        stats = {
            "total_documents": len(self.documents),
            "hybrid_search_enabled": self.hybrid_config.enable_hybrid,
            "vector_weight": self.hybrid_config.vector_weight,
            "lexical_weight": self.hybrid_config.lexical_weight,
            "reranking_method": "configurable" if self.hybrid_config.enable_reranking else "RRF",
            "rrf_k": self.hybrid_config.rrf_k,
            "rerankers_initialized": self.rerankers_initialized,
            "reranker_pipeline": self.hybrid_config.reranker_pipeline
        }

        if self.vector_store:
            try:
                vector_stats = await self.vector_store.get_collection_stats(name)
                if vector_stats:
                    stats["vector_store_stats"] = vector_stats
            except Exception as e:
                self.logger.warning("failed_to_get_vector_store_stats", error=str(e))

        # Add reranker information
        if self.rerankers_initialized:
            try:
                stats["reranker_info"] = self.reranker_factory.get_reranker_info()
            except Exception as e:
                self.logger.warning("failed_to_get_reranker_info", error=str(e))

        return stats

    def is_available(self) -> bool:
        """Check if store is available"""
        return len(self.documents) > 0 or (self.vector_store and self.vector_store.is_available())

    def get_store_info(self) -> Dict[str, Any]:
        """Get store information"""
        info = super().get_store_info()
        info.update({
            "store_type": "hybrid",
            "hybrid_config": {
                "vector_weight": self.hybrid_config.vector_weight,
                "lexical_weight": self.hybrid_config.lexical_weight,
                "enable_hybrid": self.hybrid_config.enable_hybrid,
                "enable_reranking": self.hybrid_config.enable_reranking,
                "reranking_method": "configurable" if self.hybrid_config.enable_reranking else "RRF",
                "rrf_k": self.hybrid_config.rrf_k,
                "reranker_pipeline": self.hybrid_config.reranker_pipeline
            },
            "bm25_documents": len(self.documents),
            "vector_store_available": self.vector_store is not None,
            "rerankers_initialized": self.rerankers_initialized
        })
        return info

    def set_reranker_pipeline(self, pipeline_name: str):
        """Set the reranker pipeline to use"""
        self.hybrid_config.reranker_pipeline = pipeline_name
        self.logger.info("reranker_pipeline_changed", new_pipeline=pipeline_name)

    def get_available_reranker_pipelines(self) -> List[str]:
        """Get list of available reranker pipelines"""
        return ["default", "api_docs", "technical", "semantic_only", "llm_only", "api_only"]

    def set_reranker_context(self, context: Dict[str, Any]):
        """Set context for rerankers"""
        self.hybrid_config.reranker_context = context
        self.logger.info("reranker_context_updated", context_keys=list(context.keys()))
