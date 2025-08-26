"""
RAG Implementation SDK

A flexible SDK for building RAG (Retrieval-Augmented Generation) applications
with support for multiple vector stores, LLM providers, and search strategies.

Usage:
    from sdk import RAGSystem, DocumentProcessor, SearchEngine
    
    # Basic usage
    rag = RAGSystem()
    rag.add_documents(["doc1.pdf", "doc2.txt"])
    answer = rag.query("What is this about?")
    
    # Extended usage
    class MyCustomRAG(RAGSystem):
        def custom_processing(self, query):
            # Your custom logic here
            return super().query(query)
"""

from .rag_system import RAGSystem, create_rag_system
from .document_processor import DocumentProcessor, WebDocumentProcessor, APIDocumentProcessor
from .search_engine import SearchEngine, SemanticSearchEngine, TechnicalSearchEngine
from .config import RAGConfig, PresetConfigs, VectorStoreConfig, LLMConfig, EmbeddingConfig, SearchConfig

__version__ = "1.0.0"
__all__ = [
    "RAGSystem", "create_rag_system",
    "DocumentProcessor", "WebDocumentProcessor", "APIDocumentProcessor", 
    "SearchEngine", "SemanticSearchEngine", "TechnicalSearchEngine",
    "RAGConfig", "PresetConfigs", "VectorStoreConfig", "LLMConfig", "EmbeddingConfig", "SearchConfig"
]