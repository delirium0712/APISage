#!/usr/bin/env python3
"""
Main entry point for the RAG Documentation Assistant

This is the primary CLI interface for the next-generation intelligent documentation
assistant that provides Universal Documentation Intelligence with multi-format support,
multi-provider LLM integration, and real-world problem solving capabilities.
"""

import asyncio
import argparse
import sys
import os
from pathlib import Path
from typing import Optional
import structlog

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config.config_loader import load_config
from core.orchestrator import RAGOrchestrator, OrchestrationConfig
from api.routes import run_api_server
from sdk import RAGSystem, PresetConfigs


def setup_logging(log_level: str = "INFO", log_format: str = "console"):
    """Setup structured logging"""
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    
    if log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
    
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    import logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper(), logging.INFO),
    )


async def run_interactive_mode():
    """Run interactive RAG system mode"""
    print("🚀 RAG Documentation Assistant - Interactive Mode")
    print("=" * 55)
    print("Welcome to the next-generation documentation assistant!")
    print("Type 'help' for commands or 'quit' to exit.")
    print()
    
    # Initialize RAG system
    rag = RAGSystem(config=PresetConfigs.local_development())
    
    try:
        print("Initializing system...")
        await rag.initialize()
        print("✅ System ready!")
        print()
        
        while True:
            try:
                user_input = input("📖 RAG> ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    break
                elif user_input.lower() == 'help':
                    print_help()
                elif user_input.lower() == 'status':
                    await show_system_status(rag)
                elif user_input.startswith('add '):
                    source = user_input[4:].strip()
                    await add_document(rag, source)
                elif user_input.startswith('query '):
                    query = user_input[6:].strip()
                    await process_query(rag, query)
                else:
                    # Treat as a query
                    await process_query(rag, user_input)
                
            except KeyboardInterrupt:
                print("\nUse 'quit' to exit.")
            except Exception as e:
                print(f"❌ Error: {e}")
    
    finally:
        print("\nShutting down...")
        await rag.close()
        print("👋 Goodbye!")


def print_help():
    """Print help information"""
    print("""
📖 Available Commands:
  
  query <question>     - Ask a question about your documents
  add <source>         - Add a document (URL, file path, or text)
  status              - Show system status
  help                - Show this help message
  quit/exit/q         - Exit the program
  
Examples:
  query How do I authenticate with the API?
  add https://api.example.com/docs
  add /path/to/document.pdf
  add "This is some text content"
""")


async def show_system_status(rag: RAGSystem):
    """Show system status information"""
    try:
        stats = await rag.get_stats()
        
        print("📊 System Status:")
        print(f"  Status: {stats['system_status']}")
        print(f"  Vector Store: {stats['config']['vector_store_type']}")
        print(f"  LLM Provider: {stats['config']['llm_provider']}")
        print(f"  Hybrid Search: {'✅' if stats['config']['hybrid_search_enabled'] else '❌'}")
        
        search_stats = stats.get('search_engine', {})
        print(f"  Total Documents: {search_stats.get('total_documents', 0)}")
        
    except Exception as e:
        print(f"❌ Failed to get status: {e}")


async def add_document(rag: RAGSystem, source: str):
    """Add a document to the system"""
    try:
        print(f"📥 Processing document: {source}")
        
        # Determine source type
        if source.startswith(('http://', 'https://')):
            source_type = "url"
        elif Path(source).exists():
            source_type = "file"
        else:
            source_type = "text"
        
        result = await rag.add_documents([source], source_type=source_type)
        
        if result['successful'] > 0:
            print(f"✅ Successfully processed {result['documents_created']} documents")
        else:
            print(f"❌ Failed to process document")
            for error in result.get('errors', []):
                print(f"   Error: {error}")
                
    except Exception as e:
        print(f"❌ Error adding document: {e}")


async def process_query(rag: RAGSystem, query: str):
    """Process a user query"""
    try:
        print(f"🔍 Searching for: {query}")
        
        result = await rag.query(query)
        
        print(f"\n💬 Answer:")
        print(f"   {result['answer']}")
        print(f"\n📊 Confidence: {result['confidence']:.2f}")
        
        if result.get('sources'):
            print(f"📚 Sources ({len(result['sources'])}):")
            for i, source in enumerate(result['sources'], 1):
                content_preview = source['content'][:100]
                if len(source['content']) > 100:
                    content_preview += "..."
                print(f"   {i}. {content_preview} (score: {source['score']:.3f})")
        
        print()
        
    except Exception as e:
        print(f"❌ Error processing query: {e}")


async def run_batch_processing(input_file: str, output_file: Optional[str] = None):
    """Run batch processing of documents or queries"""
    print(f"📦 Running batch processing from: {input_file}")
    
    if not Path(input_file).exists():
        print(f"❌ Input file not found: {input_file}")
        return
    
    rag = RAGSystem(config=PresetConfigs.local_development())
    
    try:
        await rag.initialize()
        
        with open(input_file, 'r') as f:
            lines = [line.strip() for line in f if line.strip()]
        
        results = []
        
        for i, line in enumerate(lines, 1):
            print(f"Processing {i}/{len(lines)}: {line[:50]}...")
            
            try:
                if line.startswith(('http://', 'https://')) or Path(line).exists():
                    # Document processing
                    result = await rag.add_documents([line])
                    results.append({
                        "input": line,
                        "type": "document",
                        "success": result['successful'] > 0,
                        "result": result
                    })
                else:
                    # Query processing
                    result = await rag.query(line)
                    results.append({
                        "input": line,
                        "type": "query",
                        "success": True,
                        "result": result
                    })
                    
            except Exception as e:
                results.append({
                    "input": line,
                    "type": "error",
                    "success": False,
                    "error": str(e)
                })
        
        # Save results if output file specified
        if output_file:
            import json
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"✅ Results saved to: {output_file}")
        
        # Print summary
        successful = sum(1 for r in results if r['success'])
        print(f"\n📊 Batch Processing Summary:")
        print(f"   Total items: {len(results)}")
        print(f"   Successful: {successful}")
        print(f"   Failed: {len(results) - successful}")
        
    finally:
        await rag.close()


async def run_orchestrator_mode(config_file: Optional[str] = None):
    """Run the full orchestrator system"""
    print("🎛️  Running RAG Orchestrator System")
    print("=" * 40)
    
    try:
        # Load configuration
        system_config = load_config(config_file)
        orchestration_config = OrchestrationConfig(
            enable_api=False,  # Don't start API server in this mode
            enable_metrics=True
        )
        
        # Initialize orchestrator
        async with RAGOrchestrator(system_config, orchestration_config) as orchestrator:
            print("✅ Orchestrator initialized successfully!")
            print("📊 System Status:")
            
            status = orchestrator.get_system_status()
            print(f"   Overall Status: {status['status']}")
            print(f"   Components: {status['components']['total']}")
            print(f"   Healthy Components: {status['components']['healthy']}")
            
            print("\nPress Ctrl+C to shutdown...")
            
            # Keep running until interrupted
            try:
                while True:
                    await asyncio.sleep(60)
                    # Could add periodic status updates here
            except KeyboardInterrupt:
                print("\n\nShutting down orchestrator...")
                
    except Exception as e:
        print(f"❌ Orchestrator failed: {e}")
        return 1
    
    return 0


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="RAG Documentation Assistant - Next-generation intelligent documentation assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s interactive                    # Run interactive mode
  %(prog)s api --port 8080               # Start API server on port 8080
  %(prog)s batch input.txt -o results.json  # Process batch file
  %(prog)s orchestrator                  # Run full orchestrator system
  
For more information, visit: https://github.com/your-repo/rag-implementation
        """
    )
    
    parser.add_argument(
        'mode',
        choices=['interactive', 'api', 'batch', 'orchestrator'],
        help='Operation mode'
    )
    
    parser.add_argument(
        '--config', '-c',
        help='Configuration file path'
    )
    
    parser.add_argument(
        '--log-level',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging level'
    )
    
    parser.add_argument(
        '--log-format',
        default='console',
        choices=['console', 'json'],
        help='Logging format'
    )
    
    # API mode arguments
    parser.add_argument(
        '--host',
        default='localhost',
        help='API server host (api mode)'
    )
    
    parser.add_argument(
        '--port', '-p',
        type=int,
        default=8000,
        help='API server port (api mode)'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode (api mode)'
    )
    
    # Batch mode arguments
    parser.add_argument(
        'input_file',
        nargs='?',
        help='Input file for batch processing (batch mode)'
    )
    
    parser.add_argument(
        '--output', '-o',
        help='Output file for batch results (batch mode)'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level, args.log_format)
    logger = structlog.get_logger()
    
    try:
        if args.mode == 'interactive':
            logger.info("starting_interactive_mode")
            asyncio.run(run_interactive_mode())
            
        elif args.mode == 'api':
            logger.info("starting_api_server", host=args.host, port=args.port)
            run_api_server(host=args.host, port=args.port, debug=args.debug)
            
        elif args.mode == 'batch':
            if not args.input_file:
                print("❌ Input file required for batch mode")
                return 1
            logger.info("starting_batch_processing", input_file=args.input_file)
            asyncio.run(run_batch_processing(args.input_file, args.output))
            
        elif args.mode == 'orchestrator':
            logger.info("starting_orchestrator_mode", config=args.config)
            return asyncio.run(run_orchestrator_mode(args.config))
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("interrupted_by_user")
        print("\n👋 Interrupted by user")
        return 0
    except Exception as e:
        logger.error("main_execution_failed", error=str(e))
        print(f"❌ Execution failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())