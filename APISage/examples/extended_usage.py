#!/usr/bin/env python3
"""
Extended Usage Example for RAG SDK

This example shows how to extend the SDK classes for custom functionality.
"""

import asyncio
import sys
import os
from typing import Dict, Any, List

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sdk import RAGSystem, DocumentProcessor, SearchEngine, RAGConfig, PresetConfigs


class CustomRAGSystem(RAGSystem):
    """
    Extended RAG system with custom preprocessing and query enhancement
    """
    
    def preprocess_query(self, query: str) -> str:
        """Custom query preprocessing"""
        # Add custom logic here
        query = query.strip()
        
        # Example: Add context keywords for API documentation
        if any(word in query.lower() for word in ['api', 'endpoint', 'authenticate']):
            query = f"API documentation: {query}"
            
        print(f"   🔍 Preprocessed query: {query}")
        return query
    
    def _chunk_content(self, content: str, chunk_size: int = 800, overlap: int = 100) -> List[str]:
        """Custom chunking strategy"""
        print(f"   📄 Using custom chunking (size: {chunk_size}, overlap: {overlap})")
        return super()._chunk_content(content, chunk_size, overlap)
    
    async def query_with_history(self, query: str, conversation_history: List[str] = None) -> Dict[str, Any]:
        """Enhanced query method with conversation history"""
        if conversation_history:
            # Combine with conversation history
            context = " ".join(conversation_history[-3:])  # Last 3 messages
            enhanced_query = f"Given this context: {context}. {query}"
        else:
            enhanced_query = query
            
        return await self.query(enhanced_query)


class APIDocumentProcessor(DocumentProcessor):
    """
    Specialized processor for API documentation
    """
    
    def preprocess_source(self, source: str, source_type: str) -> str:
        """Custom preprocessing for API docs"""
        if source_type == "url" and "api" in source.lower():
            print(f"   🌐 Processing API documentation: {source}")
            # Could add API-specific preprocessing here
            
        return super().preprocess_source(source, source_type)
    
    def postprocess_result(self, result: Dict[str, Any], 
                          original_source: str, 
                          source_type: str) -> Dict[str, Any]:
        """Enhanced processing for API content"""
        if source_type == "url" and "parsed_content" in result:
            # Add API-specific metadata
            if "metadata" not in result:
                result["metadata"] = {}
                
            result["metadata"]["content_type"] = "api_documentation"
            result["metadata"]["enhanced_processing"] = True
            
            # Could extract API endpoints, parameters, etc.
            print("   ✨ Applied API-specific enhancements")
            
        return super().postprocess_result(result, original_source, source_type)


class TechnicalSearchEngine(SearchEngine):
    """
    Search engine optimized for technical queries
    """
    
    def preprocess_query(self, query: str) -> str:
        """Technical query preprocessing"""
        query = query.strip()
        
        # Expand technical abbreviations
        replacements = {
            "auth": "authentication",
            "api": "application programming interface",
            "http": "hypertext transfer protocol"
        }
        
        for abbr, full in replacements.items():
            if abbr in query.lower():
                query = query.replace(abbr, f"{abbr} {full}")
                
        print(f"   🔧 Technical preprocessing: {query}")
        return query
    
    def create_answer_prompt(self, query: str, context: str) -> str:
        """Technical documentation focused prompt"""
        return f"""You are a technical documentation expert. Provide precise, actionable answers.

Technical Context:
{context}

Query: {query}

Provide a technical answer with:
1. Step-by-step instructions if applicable
2. Code examples or API calls
3. Configuration details
4. Clear explanation of technical concepts

Answer:"""


async def extended_usage_example():
    """Demonstrate extended functionality"""
    print("🚀 Extended RAG SDK Usage Example")
    print("=" * 45)
    
    # 1. Use extended RAG system
    print("\\n1. Creating extended RAG system...")
    rag = CustomRAGSystem(config=PresetConfigs.local_development())
    await rag.initialize()
    
    # 2. Add documents with custom processor
    print("\\n2. Processing documents with custom processor...")
    api_processor = APIDocumentProcessor(rag.config)
    await api_processor.initialize()
    
    # Override the processor in the RAG system
    rag._document_processor = api_processor
    
    result = await rag.add_documents(["https://www.questionpro.com/api"])
    print(f"   Processing result: {result['successful']}/{result['total_sources']} successful")
    
    # 3. Use enhanced search engine
    print("\\n3. Using technical search engine...")
    tech_engine = TechnicalSearchEngine(rag.config)
    await tech_engine.initialize()
    
    # Override the search engine
    rag._search_engine = tech_engine
    
    # 4. Query with enhancements
    print("\\n4. Querying with enhanced functionality...")
    
    # Basic enhanced query
    result1 = await rag.query("How do I auth with the API?")
    print(f"   Enhanced query result: {result1['answer'][:150]}...")
    
    # Query with conversation history
    history = [
        "I'm building a web application",
        "I need to integrate with QuestionPro",
        "I'm using JavaScript"
    ]
    
    result2 = await rag.query_with_history("What's the best way to authenticate?", history)
    print(f"   Context-aware result: {result2['answer'][:150]}...")
    
    # 5. System statistics
    print("\\n5. Enhanced system statistics...")
    stats = await rag.get_stats()
    print(f"   Documents indexed: {stats['search_engine'].get('total_documents', 0)}")
    print(f"   Hybrid search: {stats['config']['hybrid_search_enabled']}")
    
    await rag.close()
    print("\\n✅ Extended usage example completed!")


class MyCompanyRAG(RAGSystem):
    """
    Example of a company-specific RAG system
    """
    
    def __init__(self, company_name: str, domain_expertise: str = "general"):
        """Initialize with company-specific settings"""
        config = PresetConfigs.local_development()
        config.vector_store.collection_name = f"{company_name.lower()}_docs"
        
        super().__init__(config=config)
        self.company_name = company_name
        self.domain_expertise = domain_expertise
        
    def preprocess_query(self, query: str) -> str:
        """Add company context to queries"""
        query = super().preprocess_query(query)
        
        # Add company context
        if self.domain_expertise != "general":
            query = f"In the context of {self.domain_expertise}: {query}"
            
        return query
    
    def create_answer_prompt(self, query: str, context: str) -> str:
        """Company-specific answer generation"""
        return f"""You are an AI assistant for {self.company_name}, specializing in {self.domain_expertise}.

Company Documentation:
{context}

Employee Question: {query}

Provide a helpful answer specific to {self.company_name}'s context and {self.domain_expertise} domain. 
If the documentation doesn't contain enough information, suggest who the employee might contact or where to find more information.

Answer:"""


async def company_specific_example():
    """Example of company-specific RAG system"""
    print("\\n\\n🏢 Company-Specific RAG Example")
    print("=" * 40)
    
    # Create company-specific RAG
    company_rag = MyCompanyRAG("TechCorp", "software development")
    await company_rag.initialize()
    
    print(f"\\n1. Created RAG for {company_rag.company_name}")
    print(f"   Domain expertise: {company_rag.domain_expertise}")
    print(f"   Collection name: {company_rag.config.vector_store.collection_name}")
    
    # Add company documents
    documents = [
        "Our company uses Python and FastAPI for backend development.",
        "All API endpoints must include authentication headers.",
        "Code reviews are required before merging to main branch."
    ]
    
    await company_rag.add_documents(documents, source_type="text")
    
    # Query with company context
    result = await company_rag.query("What is our authentication policy?")
    print(f"\\n2. Company-specific answer: {result['answer']}")
    
    await company_rag.close()
    print("\\n✅ Company-specific example completed!")


if __name__ == "__main__":
    asyncio.run(extended_usage_example())
    asyncio.run(company_specific_example())