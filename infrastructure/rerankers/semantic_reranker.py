"""
Semantic Reranker
Uses cross-encoders and semantic similarity for reranking
"""

import numpy as np
from typing import List, Dict, Any, Optional
import structlog

from .base_reranker import BaseReranker, RerankerConfig
from ..vector_stores.base_store import SearchResult


class SemanticReranker(BaseReranker):
    """Semantic reranker using cross-encoders and semantic similarity"""
    
    def __init__(self, config: RerankerConfig):
        super().__init__(config)
        self.cross_encoder = None
        self.embeddings_model = None
        
    async def initialize(self, embeddings_function=None):
        """Initialize the semantic reranker with embeddings and cross-encoder"""
        try:
            self.embeddings_model = embeddings_function
            
            # Try to load cross-encoder if available
            try:
                from sentence_transformers import CrossEncoder
                self.cross_encoder = CrossEncoder(self.config.cross_encoder_model)
                self.logger.info("cross_encoder_loaded", model=self.config.cross_encoder_model)
            except ImportError:
                self.logger.warning("sentence_transformers_not_available", 
                                  message="Cross-encoder not available, using embeddings only")
                self.cross_encoder = None
            except Exception as e:
                self.logger.warning("cross_encoder_load_failed", error=str(e))
                self.cross_encoder = None
            
            self.logger.info("semantic_reranker_initialized",
                           cross_encoder_available=self.cross_encoder is not None,
                           embeddings_available=self.embeddings_model is not None)
            
        except Exception as e:
            self.logger.error("semantic_reranker_init_failed", error=str(e))
            raise
    
    async def rerank(self, 
                    query: str, 
                    results: List[SearchResult], 
                    context: Optional[Dict[str, Any]] = None) -> List[SearchResult]:
        """Rerank results using semantic similarity and cross-encoders"""
        
        if not results:
            return results
        
        # Check cache first
        cache_key = self.get_cache_key(query, results)
        cached_results = self.get_from_cache(cache_key)
        if cached_results:
            return cached_results
        
        try:
            if self.cross_encoder:
                # Use cross-encoder for more accurate reranking
                reranked_results = await self._rerank_with_cross_encoder(query, results)
            else:
                # Fallback to embeddings-based reranking
                reranked_results = await self._rerank_with_embeddings(query, results)
            
            # Apply threshold filtering
            if self.config.threshold > 0:
                reranked_results = [r for r in reranked_results if r.score >= self.config.threshold]
            
            # Limit to top_k
            final_results = reranked_results[:self.config.top_k]
            
            # Cache the results
            self.set_cache(cache_key, final_results)
            
            self.logger.info("semantic_reranking_completed",
                           query=query,
                           original_count=len(results),
                           reranked_count=len(final_results),
                           method="cross_encoder" if self.cross_encoder else "embeddings")
            
            return final_results
            
        except Exception as e:
            self.logger.error("semantic_reranking_failed", error=str(e))
            # Return original results on failure
            return results
    
    async def _rerank_with_cross_encoder(self, query: str, results: List[SearchResult]) -> List[SearchResult]:
        """Rerank using cross-encoder for more accurate semantic understanding"""
        
        try:
            # Prepare query-document pairs for cross-encoder
            pairs = []
            for result in results:
                # Truncate content to fit context window
                content = result.document.content[:self.config.context_window_size]
                pairs.append([query, content])
            
            # Get cross-encoder scores
            scores = self.cross_encoder.predict(pairs)
            
            # Create new results with cross-encoder scores
            scored_results = []
            for i, (result, score) in enumerate(zip(results, scores)):
                new_result = SearchResult(
                    document=result.document,
                    score=float(score)
                )
                new_result.metadata = result.metadata or {}
                new_result.metadata['reranking_method'] = 'cross_encoder'
                new_result.metadata['cross_encoder_score'] = float(score)
                new_result.metadata['original_score'] = result.score
                scored_results.append(new_result)
            
            # Sort by cross-encoder score (descending)
            scored_results.sort(key=lambda x: x.score, reverse=True)
            
            return scored_results
            
        except Exception as e:
            self.logger.error("cross_encoder_reranking_failed", error=str(e))
            # Fallback to embeddings
            return await self._rerank_with_embeddings(query, results)
    
    async def _rerank_with_embeddings(self, query: str, results: List[SearchResult]) -> List[SearchResult]:
        """Rerank using embeddings-based semantic similarity"""
        
        if not self.embeddings_model:
            self.logger.warning("embeddings_model_not_available")
            return results
        
        try:
            # Get query embedding
            query_embedding = await self._get_embedding(query)
            
            # Get document embeddings
            document_embeddings = []
            for result in results:
                doc_embedding = await self._get_embedding(result.document.content[:self.config.context_window_size])
                document_embeddings.append(doc_embedding)
            
            # Calculate cosine similarities
            similarities = []
            for doc_embedding in document_embeddings:
                similarity = self._cosine_similarity(query_embedding, doc_embedding)
                similarities.append(similarity)
            
            # Create new results with similarity scores
            scored_results = []
            for i, (result, similarity) in enumerate(zip(results, similarities)):
                # Combine original score with semantic similarity
                combined_score = (result.score * 0.3) + (similarity * 0.7)
                
                new_result = SearchResult(
                    document=result.document,
                    score=combined_score
                )
                new_result.metadata = result.metadata or {}
                new_result.metadata['reranking_method'] = 'embeddings'
                new_result.metadata['semantic_similarity'] = float(similarity)
                new_result.metadata['original_score'] = result.score
                new_result.metadata['combined_score'] = combined_score
                scored_results.append(new_result)
            
            # Sort by combined score (descending)
            scored_results.sort(key=lambda x: x.score, reverse=True)
            
            return scored_results
            
        except Exception as e:
            self.logger.error("embeddings_reranking_failed", error=str(e))
            return results
    
    async def _get_embedding(self, text: str) -> List[float]:
        """Get embedding for text using the embeddings model"""
        try:
            if hasattr(self.embeddings_model, 'embed_query'):
                # LangChain embeddings
                embedding = await self.embeddings_model.aembed_query(text)
            elif hasattr(self.embeddings_model, 'encode'):
                # Sentence transformers
                embedding = self.embeddings_model.encode(text)
            else:
                # Direct embedding function
                embedding = self.embeddings_model(text)
            
            # Ensure it's a list of floats
            if isinstance(embedding, np.ndarray):
                embedding = embedding.tolist()
            elif not isinstance(embedding, list):
                embedding = list(embedding)
            
            return embedding
            
        except Exception as e:
            self.logger.error("embedding_generation_failed", error=str(e), text=text[:100])
            # Return zero vector as fallback
            return [0.0] * 384  # Default dimension
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            # Convert to numpy arrays
            v1 = np.array(vec1)
            v2 = np.array(vec2)
            
            # Ensure same length
            min_len = min(len(v1), len(v2))
            v1 = v1[:min_len]
            v2 = v2[:min_len]
            
            # Calculate cosine similarity
            dot_product = np.dot(v1, v2)
            norm_v1 = np.linalg.norm(v1)
            norm_v2 = np.linalg.norm(v2)
            
            if norm_v1 == 0 or norm_v2 == 0:
                return 0.0
            
            similarity = dot_product / (norm_v1 * norm_v2)
            return float(similarity)
            
        except Exception as e:
            self.logger.error("cosine_similarity_calculation_failed", error=str(e))
            return 0.0
    
    def get_reranker_info(self) -> Dict[str, Any]:
        """Get information about the semantic reranker"""
        info = super().get_reranker_info()
        info.update({
            "reranker_type": "Semantic",
            "cross_encoder_available": self.cross_encoder is not None,
            "cross_encoder_model": self.config.cross_encoder_model if self.cross_encoder else None,
            "embeddings_available": self.embeddings_model is not None,
            "semantic_similarity_threshold": self.config.semantic_similarity_threshold,
            "context_window_size": self.config.context_window_size
        })
        return info
