#!/usr/bin/env python3
"""
SDK Demo - Fixed version of the original QuestionPro demo using the new SDK

This demonstrates how the new SDK solves the original issues while providing
a clean, extensible interface.
"""

import asyncio
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sdk import RAGSystem, RAGConfig, PresetConfigs
from sdk.search_engine import TechnicalSearchEngine
from sdk.document_processor import APIDocumentProcessor


async def sdk_demo():
    """
    Demo using the new SDK that fixes all the original issues:
    1. ✅ Proper UUID handling for document IDs
    2. ✅ Clean configuration interface
    3. ✅ Better error handling
    4. ✅ Extensible design
    5. ✅ Improved content processing
    """
    print("🚀 RAG SDK Demo - QuestionPro API Documentation")
    print("=" * 55)
    print("This demo shows the SDK improvements:")
    print("✅ Fixed UUID/ID format issues")
    print("✅ Clean, extensible interfaces")
    print("✅ Better error handling")
    print("✅ Improved content processing")
    print("=" * 55)
    
    # Step 1: Create and configure RAG system
    print("\\n🔧 Step 1: Creating RAG system with SDK...")
    
    # Option A: Use preset config
    config = PresetConfigs.local_development()
    config.search.final_top_k = 5
    config.search.enable_reranking = True
    
    # Option B: You could create custom components
    # This is where users can extend functionality
    rag = RAGSystem(config=config)
    
    # Step 2: Initialize (this handles all the complex setup)
    print("\\n🚀 Step 2: Initializing system...")
    await rag.initialize()
    
    # Step 3: Add documents (with better error handling)
    print("\\n📚 Step 3: Processing QuestionPro API documentation...")
    
    sources = [
        "https://www.questionpro.com/api",
        # Could add more sources:
        # "https://api.questionpro.com/docs",
        # "path/to/local/api_docs.pdf"
    ]
    
    results = await rag.add_documents(sources, source_type="url")
    
    print(f"   📊 Processing Results:")
    print(f"   ✅ Successful: {results['successful']}")
    print(f"   ❌ Failed: {results['failed']}")
    print(f"   📄 Documents created: {results['documents_created']}")
    
    if results['errors']:
        print(f"   ⚠️  Errors: {results['errors'][:2]}")  # Show first 2 errors
    
    # Step 4: Query the system
    print("\\n🔍 Step 4: Querying with improved search...")
    
    test_questions = [
        "How do I authenticate with the QuestionPro API?",
        "What are the available survey endpoints?", 
        "What is the rate limit for API calls?",
        "How do I create a new survey?",
        "What response formats are supported?"
    ]
    
    for i, question in enumerate(test_questions, 1):
        print(f"\\n{i}. Question: {question}")
        print("-" * 50)
        
        # Query with the SDK (handles all the complexity)
        result = await rag.query(question, top_k=3, include_sources=True)
        
        print(f"   🤖 Answer: {result['answer']}")
        print(f"   📊 Confidence: {result['confidence']:.2f}")
        print(f"   📚 Sources: {len(result.get('sources', []))} documents")
        
        # Show top source
        if result.get('sources'):
            source = result['sources'][0]
            print(f"   📖 Top source (score: {source['score']:.3f}): {source['content'][:100]}...")
    
    # Step 5: Demonstrate different search modes
    print("\\n🎛️  Step 5: Demonstrating search modes...")
    
    test_query = "API authentication methods"
    
    # Hybrid search (default)
    hybrid_results = await rag.query(test_query, search_type="hybrid", top_k=3)
    print(f"\\n   🔀 Hybrid Search: {len(hybrid_results.get('sources', []))} results")
    
    # Vector-only search
    vector_results = await rag.query(test_query, search_type="vector", top_k=3)
    print(f"   🧠 Vector Search: {len(vector_results.get('sources', []))} results")
    
    # BM25-only search
    bm25_results = await rag.query(test_query, search_type="bm25", top_k=3)
    print(f"   📝 BM25 Search: {len(bm25_results.get('sources', []))} results")
    
    # Step 6: System statistics
    print("\\n📊 Step 6: System Statistics")
    print("-" * 30)
    
    stats = await rag.get_stats()
    print(f"   System Status: {stats['system_status']}")
    print(f"   Vector Store: {stats['config']['vector_store_type']}")
    print(f"   LLM Provider: {stats['config']['llm_provider']}")
    print(f"   Hybrid Search: {stats['config']['hybrid_search_enabled']}")
    
    search_stats = stats.get('search_engine', {})
    print(f"   Total Documents: {search_stats.get('total_documents', 0)}")
    
    # Step 7: Clean up
    print("\\n🧹 Step 7: Cleanup")
    await rag.close()
    
    print("\\n🎉 SDK Demo completed successfully!")
    print("\\nKey Improvements Demonstrated:")
    print("✅ No more UUID format errors")
    print("✅ Clean, simple API interface")
    print("✅ Better error handling and reporting")
    print("✅ Extensible design for customization")
    print("✅ Improved search and answer quality")


async def extended_sdk_demo():
    """
    Demo showing how to extend the SDK for custom needs
    """
    print("\\n\\n🎨 Extended SDK Demo - Custom Components")
    print("=" * 50)
    
    # Create custom RAG system
    class QuestionProRAG(RAGSystem):
        def preprocess_query(self, query: str) -> str:
            # Add QuestionPro-specific context
            if "survey" in query.lower():
                query = f"QuestionPro survey platform: {query}"
            return super().preprocess_query(query)
    
    # Use custom components
    config = PresetConfigs.local_development()
    rag = QuestionProRAG(config=config)
    
    # You could also use specialized components
    api_processor = APIDocumentProcessor(config)
    tech_search = TechnicalSearchEngine(config)
    
    await rag.initialize()
    
    # Override components if needed
    await api_processor.initialize()
    await tech_search.initialize()
    
    rag._document_processor = api_processor  # Use API-specialized processor
    rag._search_engine = tech_search        # Use technical search engine
    
    print("\\n✨ Custom RAG system created with:")
    print("   🔧 Custom query preprocessing")
    print("   📄 API-specialized document processor")
    print("   🔍 Technical search engine")
    
    # Add documents and test
    await rag.add_documents(["The QuestionPro API supports survey management and data collection."])
    
    result = await rag.query("How do I create surveys?")
    print(f"\\n🎯 Custom system result: {result['answer']}")
    
    await rag.close()
    print("\\n✅ Extended SDK demo completed!")


if __name__ == "__main__":
    asyncio.run(sdk_demo())
    asyncio.run(extended_sdk_demo())