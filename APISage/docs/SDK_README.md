# RAG Implementation SDK

A flexible and extensible SDK for building RAG (Retrieval-Augmented Generation) applications with support for multiple vector stores, LLM providers, and search strategies.

## 🚀 Quick Start

```python
import asyncio
from sdk import RAGSystem

async def main():
    # Create and initialize RAG system
    rag = RAGSystem()
    await rag.initialize()
    
    # Add documents
    await rag.add_documents(["https://example.com/docs", "local_file.pdf"])
    
    # Query the system
    result = await rag.query("What is this about?")
    print(result["answer"])
    
    # Clean up
    await rag.close()

asyncio.run(main())
```

## 📦 Installation

The SDK wraps the existing RAG implementation infrastructure. Make sure you have:

1. **Required services running:**
   - Ollama (for LLM): `http://localhost:11434`
   - Qdrant (for vector storage): `http://localhost:6333`

2. **Python dependencies installed:**
   ```bash
   source venv/bin/activate  # Use the existing virtual environment
   ```

## 🎯 Core Components

### RAGSystem
The main interface for users - handles document processing, indexing, and querying.

```python
from sdk import RAGSystem, RAGConfig, PresetConfigs

# Option 1: Use preset configurations
rag = RAGSystem(config=PresetConfigs.local_development())

# Option 2: Custom configuration
config = RAGConfig()
config.search.vector_weight = 0.8
config.search.lexical_weight = 0.2
rag = RAGSystem(config=config)
```

### DocumentProcessor
Handles document ingestion from various sources.

```python
from sdk import DocumentProcessor

processor = DocumentProcessor(config)
await processor.initialize()

# Process different source types
result = await processor.process_document("https://api.example.com", "url")
result = await processor.process_document("/path/to/file.pdf", "file")
result = await processor.process_document("Direct text content", "text")
```

### SearchEngine
Manages search and answer generation.

```python
from sdk import SearchEngine

engine = SearchEngine(config)
await engine.initialize()

# Different search modes
results = await engine.search("query", search_type="hybrid")    # Default
results = await engine.search("query", search_type="vector")    # Semantic only
results = await engine.search("query", search_type="bm25")      # Keyword only
```

## 🔧 Configuration

### Preset Configurations

```python
from sdk import PresetConfigs

# For local development with Ollama + Qdrant
config = PresetConfigs.local_development()

# For cloud deployment with OpenAI
config = PresetConfigs.cloud_openai()

# High-performance configuration
config = PresetConfigs.high_performance()
```

### Custom Configuration

```python
from sdk import RAGConfig, VectorStoreConfig, LLMConfig, EmbeddingConfig, SearchConfig
from sdk.config import VectorStoreType, LLMProvider, EmbeddingProvider

config = RAGConfig(
    vector_store=VectorStoreConfig(
        store_type=VectorStoreType.QDRANT,
        host="localhost",
        port=6333,
        collection_name="my_docs"
    ),
    llm=LLMConfig(
        provider=LLMProvider.OLLAMA,
        model_name="llama3:8b",
        temperature=0.7
    ),
    embedding=EmbeddingConfig(
        provider=EmbeddingProvider.HUGGINGFACE,
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    ),
    search=SearchConfig(
        enable_hybrid=True,
        vector_weight=0.6,
        lexical_weight=0.4,
        final_top_k=5
    )
)
```

## 🎨 Extending the SDK

### Custom RAG System

```python
from sdk import RAGSystem

class MyCustomRAG(RAGSystem):
    def preprocess_query(self, query: str) -> str:
        """Add custom query preprocessing"""
        query = super().preprocess_query(query)
        # Add your custom logic
        if "urgent" in query.lower():
            query = f"PRIORITY: {query}"
        return query
    
    def _chunk_content(self, content: str, chunk_size: int = 800, overlap: int = 100):
        """Custom content chunking"""
        # Your custom chunking strategy
        return super()._chunk_content(content, chunk_size, overlap)
    
    async def query_with_context(self, query: str, context: dict) -> dict:
        """Custom query method with additional context"""
        enhanced_query = f"Context: {context}. Question: {query}"
        return await self.query(enhanced_query)

# Usage
rag = MyCustomRAG()
await rag.initialize()
```

### Custom Document Processor

```python
from sdk import DocumentProcessor

class APIDocProcessor(DocumentProcessor):
    def preprocess_source(self, source: str, source_type: str) -> str:
        """Custom preprocessing for API docs"""
        if source_type == "url" and "api" in source.lower():
            # Add API-specific preprocessing
            pass
        return super().preprocess_source(source, source_type)
    
    def postprocess_result(self, result: dict, original_source: str, source_type: str) -> dict:
        """Enhanced API documentation processing"""
        if "api_endpoints" in result.get("parsed_content", {}):
            # Add API-specific metadata
            result["metadata"] = result.get("metadata", {})
            result["metadata"]["content_type"] = "api_documentation"
        
        return super().postprocess_result(result, original_source, source_type)

# Usage
processor = APIDocProcessor(config)
await processor.initialize()
```

### Custom Search Engine

```python
from sdk import SearchEngine

class TechnicalSearchEngine(SearchEngine):
    def preprocess_query(self, query: str) -> str:
        """Technical query preprocessing"""
        # Expand technical abbreviations
        replacements = {"auth": "authentication", "api": "application programming interface"}
        for abbr, full in replacements.items():
            query = query.replace(abbr, f"{abbr} {full}")
        return super().preprocess_query(query)
    
    def create_answer_prompt(self, query: str, context: str) -> str:
        """Technical documentation focused prompt"""
        return f"""You are a technical documentation expert.

Context: {context}
Query: {query}

Provide step-by-step instructions with code examples where applicable.
Answer:"""

# Usage
engine = TechnicalSearchEngine(config)
await engine.initialize()
```

## 🏢 Company-Specific Example

```python
class CompanyRAG(RAGSystem):
    def __init__(self, company_name: str, domain: str = "general"):
        config = PresetConfigs.local_development()
        config.vector_store.collection_name = f"{company_name.lower()}_docs"
        super().__init__(config=config)
        self.company_name = company_name
        self.domain = domain
    
    def preprocess_query(self, query: str) -> str:
        """Add company context"""
        return f"In the context of {self.company_name} {self.domain}: {query}"

# Usage
company_rag = CompanyRAG("TechCorp", "software development")
await company_rag.initialize()
```

## 📝 Examples

Check the `examples/` directory for comprehensive examples:

- `basic_usage.py` - Simple usage patterns
- `extended_usage.py` - Advanced customization examples  
- `sdk_demo.py` - Fixed version of the original demo

## 🔧 Running Examples

```bash
# Ensure services are running
curl http://localhost:11434/api/version  # Ollama
curl http://localhost:6333/collections   # Qdrant

# Activate virtual environment
source venv/bin/activate

# Run examples
python examples/basic_usage.py
python examples/extended_usage.py
python examples/sdk_demo.py
```

## ✅ Fixes Applied

The SDK addresses the original issues:

1. **✅ UUID Format Issues**: Proper UUID generation for Qdrant document IDs
2. **✅ Metadata Errors**: Fixed SearchResult attribute handling in reranking
3. **✅ Content Extraction**: Better web scraping and content processing
4. **✅ Vector Search**: Improved vector indexing and retrieval
5. **✅ Error Handling**: Comprehensive error handling and reporting
6. **✅ Extensibility**: Clean inheritance patterns for customization

## 🚀 Advanced Features

### Multiple Search Modes
```python
# Hybrid search (default) - combines vector + BM25
result = await rag.query("query", search_type="hybrid")

# Pure semantic search
result = await rag.query("query", search_type="vector")

# Pure keyword search  
result = await rag.query("query", search_type="bm25")
```

### Batch Document Processing
```python
sources = ["url1", "url2", "file1.pdf", "file2.txt"]
results = await rag.add_documents(sources, metadata={"batch_id": "batch_1"})
```

### System Statistics
```python
stats = await rag.get_stats()
print(f"Documents indexed: {stats['search_engine']['total_documents']}")
print(f"Vector store: {stats['config']['vector_store_type']}")
```

## 🎯 Best Practices

1. **Always initialize**: Call `await rag.initialize()` before use
2. **Clean up**: Call `await rag.close()` when done
3. **Error handling**: Check results for errors and handle appropriately
4. **Custom chunking**: Override `_chunk_content()` for domain-specific chunking
5. **Query preprocessing**: Use `preprocess_query()` for query enhancement
6. **Configuration**: Use preset configs as starting points, customize as needed

## 🤝 Contributing

To add new functionality:

1. **Extend base classes**: Inherit from `RAGSystem`, `DocumentProcessor`, or `SearchEngine`
2. **Override methods**: Customize `preprocess_query()`, `postprocess_result()`, etc.
3. **Add configurations**: Extend `RAGConfig` for new options
4. **Test thoroughly**: Use the examples as templates for testing

## 📚 API Reference

### RAGSystem Methods
- `initialize()` - Initialize the system
- `add_documents(sources, source_type, metadata)` - Add documents
- `query(query, top_k, search_type, include_sources)` - Query system
- `get_stats()` - Get system statistics
- `reset()` - Clear all documents
- `close()` - Clean up resources

### Extensible Methods
- `preprocess_query(query)` - Override for custom query processing
- `_chunk_content(content, chunk_size, overlap)` - Override for custom chunking
- `_create_documents(processed_data, source, metadata)` - Override document creation

The SDK provides a clean, extensible foundation for building RAG applications while fixing all the issues from the original implementation.