#!/usr/bin/env python3
"""
Basic Usage Example for RAG SDK

This example shows how to use the RAG SDK for simple document processing and querying.
"""

import asyncio
import sys
import os

# Add the project root to the path  
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sdk import RAGSystem, RAGConfig, PresetConfigs


async def basic_usage_example():
    """Basic usage with default configuration"""
    print("🚀 Basic RAG SDK Usage Example")
    print("=" * 40)
    
    # Method 1: Use preset configuration
    print("\\n1. Creating RAG system with preset config...")
    rag = RAGSystem(config=PresetConfigs.local_development())
    await rag.initialize()
    
    # Add documents
    print("\\n2. Adding documents...")
    sources = [
        "https://www.questionpro.com/api",  # Web URL
        # "path/to/document.pdf",          # Local file
        # "This is some text content"       # Direct text
    ]
    
    result = await rag.add_documents(sources)
    print(f"   Documents processed: {result['successful']}/{result['total_sources']}")
    if result['errors']:
        print(f"   Errors: {result['errors']}")
    
    # Query the system
    print("\\n3. Querying the system...")
    questions = [
        "How do I authenticate with the API?",
        "What endpoints are available?",
        "What is the rate limit?"
    ]
    
    for question in questions:
        print(f"\\n   Q: {question}")
        answer = await rag.query(question)
        print(f"   A: {answer['answer'][:200]}{'...' if len(answer['answer']) > 200 else ''}")
        print(f"   Confidence: {answer['confidence']:.2f}")
    
    # Get system statistics
    print("\\n4. System statistics...")
    stats = await rag.get_stats()
    print(f"   Status: {stats['system_status']}")
    print(f"   Vector Store: {stats['config']['vector_store_type']}")
    print(f"   LLM Provider: {stats['config']['llm_provider']}")
    
    # Clean up
    await rag.close()
    print("\\n✅ Basic usage example completed!")


async def custom_config_example():
    """Usage with custom configuration"""
    print("\\n\\n🔧 Custom Configuration Example")
    print("=" * 40)
    
    # Create custom configuration
    config = RAGConfig()
    config.search.vector_weight = 0.8  # Prefer semantic search
    config.search.lexical_weight = 0.2
    config.search.final_top_k = 3
    
    # Initialize with custom config
    rag = RAGSystem(config=config)
    await rag.initialize()
    
    print("\\n1. Custom configuration applied:")
    print(f"   Vector weight: {config.search.vector_weight}")
    print(f"   Lexical weight: {config.search.lexical_weight}")
    print(f"   Top K results: {config.search.final_top_k}")
    
    # Add and query as before
    await rag.add_documents(["This is example content about machine learning and AI."])
    
    result = await rag.query("What is this about?")
    print(f"\\n2. Query result: {result['answer']}")
    
    await rag.close()
    print("\\n✅ Custom configuration example completed!")


if __name__ == "__main__":
    asyncio.run(basic_usage_example())
    asyncio.run(custom_config_example())