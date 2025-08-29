"""
API Documentation Specific Reranker
Specialized reranker for API documentation with technical understanding
"""

import re
from typing import List, Dict, Any, Optional
import structlog

from .base_reranker import BaseReranker, RerankerConfig
from ..vector_stores.base_store import SearchResult


class APIDocsReranker(BaseReranker):
    """Specialized reranker for API documentation with technical relevance scoring"""
    
    def __init__(self, config: RerankerConfig):
        super().__init__(config)
        self.api_patterns = self._initialize_api_patterns()
        self.technical_keywords = self._initialize_technical_keywords()
        
    def _initialize_api_patterns(self) -> Dict[str, re.Pattern]:
        """Initialize regex patterns for API-related content"""
        return {
            'endpoint': re.compile(r'(GET|POST|PUT|DELETE|PATCH)\s+([/\w\-{}]+)', re.IGNORECASE),
            'http_status': re.compile(r'HTTP\s+(\d{3})', re.IGNORECASE),
            'json_schema': re.compile(r'\{[^{}]*"[^"]*"[^{}]*\}', re.IGNORECASE),
            'code_block': re.compile(r'```[\w]*\n(.*?)\n```', re.DOTALL),
            'parameter': re.compile(r'[?&]([^=&]+)=([^&]*)', re.IGNORECASE),
            'version': re.compile(r'v\d+(\.\d+)*', re.IGNORECASE),
            'authentication': re.compile(r'(bearer|basic|api.?key|oauth|jwt)', re.IGNORECASE),
            'rate_limit': re.compile(r'(rate.?limit|throttling|quota)', re.IGNORECASE)
        }
    
    def _initialize_technical_keywords(self) -> Dict[str, List[str]]:
        """Initialize technical keywords for different API documentation aspects"""
        return {
            'endpoints': ['endpoint', 'route', 'path', 'url', 'uri', 'api', 'rest'],
            'authentication': ['auth', 'authentication', 'authorization', 'token', 'key', 'credential'],
            'parameters': ['parameter', 'query', 'body', 'header', 'form', 'multipart'],
            'responses': ['response', 'status', 'code', 'error', 'success', 'failure'],
            'examples': ['example', 'sample', 'code', 'snippet', 'implementation'],
            'errors': ['error', 'exception', 'failure', 'invalid', 'unauthorized', 'forbidden'],
            'rate_limiting': ['rate', 'limit', 'throttle', 'quota', 'usage', 'restriction'],
            'versioning': ['version', 'deprecated', 'legacy', 'stable', 'beta', 'alpha']
        }
    
    async def rerank(self, 
                    query: str, 
                    results: List[SearchResult], 
                    context: Optional[Dict[str, Any]] = None) -> List[SearchResult]:
        """Rerank API documentation results based on technical relevance"""
        
        if not results:
            return results
        
        # Check cache first
        cache_key = self.get_cache_key(query, results)
        cached_results = self.get_from_cache(cache_key)
        if cached_results:
            return cached_results
        
        try:
            # Analyze query for API-specific patterns
            query_analysis = self._analyze_query(query)
            
            # Score and rerank each result
            scored_results = []
            for result in results:
                score = self._calculate_api_relevance_score(result, query_analysis, context)
                # Create a copy with new score
                new_result = SearchResult(
                    document=result.document,
                    score=score
                )
                new_result.metadata = result.metadata or {}
                new_result.metadata['reranking_method'] = 'api_docs'
                new_result.metadata['api_relevance_score'] = score
                scored_results.append(new_result)
            
            # Sort by score (descending)
            scored_results.sort(key=lambda x: x.score, reverse=True)
            
            # Apply threshold filtering
            if self.config.threshold > 0:
                scored_results = [r for r in scored_results if r.score >= self.config.threshold]
            
            # Limit to top_k
            final_results = scored_results[:self.config.top_k]
            
            # Cache the results
            self.set_cache(cache_key, final_results)
            
            self.logger.info("api_docs_reranking_completed",
                           query=query,
                           original_count=len(results),
                           reranked_count=len(final_results),
                           threshold=self.config.threshold)
            
            return final_results
            
        except Exception as e:
            self.logger.error("api_docs_reranking_failed", error=str(e), query=query)
            return results
    
    def _analyze_query(self, query: str) -> Dict[str, Any]:
        """Analyze the query for API-specific patterns and intent"""
        query_lower = query.lower()
        
        analysis = {
            'query_type': 'general',
            'intent': 'information',
            'technical_level': 'basic',
            'api_specific': False,
            'patterns_found': [],
            'keywords_found': []
        }
        
        # Detect query type
        if any(word in query_lower for word in ['how', 'create', 'make', 'build']):
            analysis['query_type'] = 'implementation'
            analysis['intent'] = 'how_to'
        elif any(word in query_lower for word in ['what', 'list', 'show', 'get']):
            analysis['query_type'] = 'information'
            analysis['intent'] = 'information'
        elif any(word in query_lower for word in ['error', 'problem', 'issue', 'fix']):
            analysis['query_type'] = 'troubleshooting'
            analysis['intent'] = 'problem_solving'
        elif any(word in query_lower for word in ['endpoint', 'api', 'method', 'route']):
            analysis['query_type'] = 'endpoint_specific'
            analysis['intent'] = 'endpoint_info'
            analysis['api_specific'] = True
        
        # Detect technical level
        technical_terms = ['authentication', 'oauth', 'jwt', 'rate limiting', 'pagination', 'webhook']
        if any(term in query_lower for term in technical_terms):
            analysis['technical_level'] = 'advanced'
        elif any(term in query_lower for term in ['example', 'sample', 'code']):
            analysis['technical_level'] = 'intermediate'
        
        # Find API patterns in query
        for pattern_name, pattern in self.api_patterns.items():
            if pattern.search(query):
                analysis['patterns_found'].append(pattern_name)
        
        # Find technical keywords
        for category, keywords in self.technical_keywords.items():
            found = [kw for kw in keywords if kw in query_lower]
            if found:
                analysis['keywords_found'].extend(found)
        
        return analysis
    
    def _calculate_api_relevance_score(self, 
                                     result: SearchResult, 
                                     query_analysis: Dict[str, Any],
                                     context: Optional[Dict[str, Any]] = None) -> float:
        """Calculate API-specific relevance score for a document"""
        
        doc = result.document
        content = doc.content.lower()
        metadata = doc.metadata or {}
        
        # Base score from original ranking
        base_score = result.score
        
        # Initialize relevance score
        relevance_score = 0.0
        
        # 1. Content Pattern Matching (40% weight)
        pattern_score = self._calculate_pattern_score(content, query_analysis)
        relevance_score += pattern_score * 0.4
        
        # 2. Technical Depth Scoring (25% weight)
        technical_score = self._calculate_technical_depth_score(content, query_analysis)
        relevance_score += technical_score * 0.25
        
        # 3. Metadata Relevance (20% weight)
        metadata_score = self._calculate_metadata_score(metadata, query_analysis)
        relevance_score += metadata_score * 0.2
        
        # 4. Query-Document Alignment (15% weight)
        alignment_score = self._calculate_query_alignment_score(doc, query_analysis)
        relevance_score += alignment_score * 0.15
        
        # Combine with base score
        final_score = (base_score * 0.3) + (relevance_score * 0.7)
        
        return min(1.0, max(0.0, final_score))
    
    def _calculate_pattern_score(self, content: str, query_analysis: Dict[str, Any]) -> float:
        """Calculate score based on API patterns found in content"""
        pattern_score = 0.0
        
        for pattern_name, pattern in self.api_patterns.items():
            matches = pattern.findall(content)
            if matches:
                # Different patterns have different weights
                pattern_weights = {
                    'endpoint': 0.3,
                    'http_status': 0.2,
                    'json_schema': 0.25,
                    'code_block': 0.3,
                    'parameter': 0.2,
                    'version': 0.15,
                    'authentication': 0.25,
                    'rate_limit': 0.2
                }
                
                weight = pattern_weights.get(pattern_name, 0.1)
                pattern_score += weight * min(len(matches), 5) / 5  # Cap at 5 matches
        
        return min(1.0, pattern_score)
    
    def _calculate_technical_depth_score(self, content: str, query_analysis: Dict[str, Any]) -> float:
        """Calculate score based on technical depth of content"""
        technical_score = 0.0
        
        # Check for code examples
        if '```' in content or '<code>' in content:
            technical_score += 0.3
        
        # Check for technical specifications
        tech_indicators = [
            'http', 'json', 'xml', 'oauth', 'jwt', 'bearer', 'basic',
            'rate limit', 'pagination', 'webhook', 'callback', 'async',
            'streaming', 'batch', 'bulk', 'webhook', 'sdk', 'library'
        ]
        
        for indicator in tech_indicators:
            if indicator in content:
                technical_score += 0.1
        
        # Check for structured data
        if re.search(r'\{[^{}]*"[^"]*"[^{}]*\}', content):
            technical_score += 0.2
        
        # Check for error codes and status messages
        if re.search(r'\d{3}\s+[A-Z\s]+', content):
            technical_score += 0.2
        
        return min(1.0, technical_score)
    
    def _calculate_metadata_score(self, metadata: Dict[str, Any], query_analysis: Dict[str, Any]) -> float:
        """Calculate score based on document metadata"""
        metadata_score = 0.0
        
        # Type relevance
        doc_type = metadata.get('type', '').lower()
        if query_analysis['api_specific'] and doc_type in ['endpoint', 'api', 'method']:
            metadata_score += 0.4
        
        # Topic relevance
        doc_topic = metadata.get('topic', '').lower()
        if doc_topic in query_analysis['keywords_found']:
            metadata_score += 0.3
        
        # Method relevance for endpoint-specific queries
        if query_analysis['query_type'] == 'endpoint_specific':
            doc_method = metadata.get('method', '').lower()
            if doc_method:
                metadata_score += 0.2
        
        # Source relevance
        source = metadata.get('source', '').lower()
        if 'api' in source or 'docs' in source:
            metadata_score += 0.1
        
        return min(1.0, metadata_score)
    
    def _calculate_query_alignment_score(self, doc, query_analysis: Dict[str, Any]) -> float:
        """Calculate score based on query-document alignment"""
        alignment_score = 0.0
        
        # Check if document content length matches query complexity
        content_length = len(doc.content)
        
        if query_analysis['technical_level'] == 'basic' and content_length < 200:
            alignment_score += 0.3  # Short, simple content for basic queries
        elif query_analysis['technical_level'] == 'advanced' and content_length > 500:
            alignment_score += 0.3  # Detailed content for advanced queries
        elif query_analysis['technical_level'] == 'intermediate' and 200 <= content_length <= 500:
            alignment_score += 0.3  # Medium content for intermediate queries
        
        # Check for implementation vs information alignment
        if query_analysis['query_type'] == 'implementation':
            if 'example' in doc.content.lower() or '```' in doc.content:
                alignment_score += 0.4  # Code examples for implementation queries
        elif query_analysis['query_type'] == 'information':
            if 'endpoint' in doc.content.lower() or 'api' in doc.content.lower():
                alignment_score += 0.4  # API info for information queries
        
        return min(1.0, alignment_score)
    
    def get_reranker_info(self) -> Dict[str, Any]:
        """Get information about the API docs reranker"""
        info = super().get_reranker_info()
        info.update({
            "reranker_type": "API Documentation Specific",
            "api_patterns": list(self.api_patterns.keys()),
            "technical_keywords": list(self.technical_keywords.keys()),
            "api_context_weight": self.config.api_context_weight,
            "technical_accuracy_weight": self.config.technical_accuracy_weight,
            "endpoint_relevance_weight": self.config.endpoint_relevance_weight,
            "code_example_weight": self.config.code_example_weight
        })
        return info




