"""
Main orchestrator for coordinating all RAG system components
"""

import asyncio
import time
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
import structlog

from config.settings import SystemConfig, AgentConfig
from config.config_loader import ConfigLoader
from infrastructure.backend_manager import BackendManager
from infrastructure.llm_manager import LLMManager
from agents.document_processor import DocumentProcessor
from agents.api_analyzer import APIAnalyzer
from agents.evaluator import RAGEvaluator
from agents.code_generator import CodeGenerator
from .state import SystemState, StateManager, ComponentStatus, SystemStatus


@dataclass
class OrchestrationConfig:
    """Configuration for the RAG orchestrator"""
    max_concurrent_tasks: int = 10
    task_timeout: int = 300  # 5 minutes
    health_check_interval: int = 60
    auto_recovery: bool = True
    enable_metrics: bool = True
    enable_api: bool = False


class RAGOrchestrator:
    """
    Main orchestrator that coordinates all RAG system components:
    - Manages system lifecycle (startup, shutdown, recovery)
    - Coordinates between agents and infrastructure
    - Handles task scheduling and execution
    - Monitors system health and performance
    - Provides unified API for the entire system
    """
    
    def __init__(self, system_config: SystemConfig, orchestration_config: OrchestrationConfig = None):
        self.system_config = system_config
        self.orchestration_config = orchestration_config or OrchestrationConfig()
        
        self.logger = structlog.get_logger(__name__)
        
        # System state management
        self.state = SystemState()
        self.state_manager = StateManager(self.state)
        
        # Infrastructure managers
        self.backend_manager: Optional[BackendManager] = None
        self.llm_manager: Optional[LLMManager] = None
        
        # Agent instances
        self.agents: Dict[str, Any] = {}
        
        # Task management
        self.task_semaphore = asyncio.Semaphore(self.orchestration_config.max_concurrent_tasks)
        
        # Background tasks
        self._health_check_task: Optional[asyncio.Task] = None
        self._is_running = False
        
    async def initialize(self) -> None:
        """Initialize the entire RAG system"""
        self.logger.info("initializing_rag_orchestrator")
        
        try:
            # Update system state
            self.state.status = SystemStatus.INITIALIZING
            
            # Start state manager
            await self.state_manager.start()
            
            # Initialize infrastructure
            await self._initialize_infrastructure()
            
            # Initialize agents
            await self._initialize_agents()
            
            # Start background tasks
            await self._start_background_tasks()
            
            # Mark system as healthy
            self.state.status = SystemStatus.HEALTHY
            self._is_running = True
            
            self.logger.info(
                "rag_orchestrator_initialized",
                components=len(self.state.components),
                agents=len(self.agents)
            )
            
        except Exception as e:
            self.logger.error("orchestrator_initialization_failed", error=str(e))
            self.state.status = SystemStatus.UNHEALTHY
            raise
    
    async def _initialize_infrastructure(self):
        """Initialize infrastructure components"""
        self.logger.info("initializing_infrastructure")
        
        # Backend Manager
        self.state.register_component("backend_manager", "infrastructure")
        try:
            self.backend_manager = BackendManager(self.system_config)
            await self.backend_manager.initialize()
            self.state.update_component_status("backend_manager", ComponentStatus.RUNNING)
        except Exception as e:
            self.state.update_component_status("backend_manager", ComponentStatus.ERROR, str(e))
            raise
        
        # LLM Manager
        self.state.register_component("llm_manager", "infrastructure", ["backend_manager"])
        try:
            self.llm_manager = LLMManager(self.system_config)
            await self.llm_manager.initialize()
            self.state.update_component_status("llm_manager", ComponentStatus.RUNNING)
        except Exception as e:
            self.state.update_component_status("llm_manager", ComponentStatus.ERROR, str(e))
            raise
    
    async def _initialize_agents(self):
        """Initialize all agent components"""
        self.logger.info("initializing_agents")
        
        # Load agent configurations - use default enabled agents
        agents_config = {
            "document_processor": {"enabled": True},
            "api_analyzer": {"enabled": True},
            "evaluator": {"enabled": True},
            "code_generator": {"enabled": True}
        }
        
        # Document Processor
        if agents_config.get("document_processor", {}).get("enabled", True):
            await self._initialize_agent("document_processor", DocumentProcessor)
        
        # API Analyzer
        if agents_config.get("api_analyzer", {}).get("enabled", True):
            await self._initialize_agent("api_analyzer", APIAnalyzer)
        
        # Evaluator
        if agents_config.get("evaluator", {}).get("enabled", True):
            await self._initialize_agent("evaluator", RAGEvaluator)
        
        # Code Generator
        if agents_config.get("code_generator", {}).get("enabled", True):
            await self._initialize_agent("code_generator", CodeGenerator)
    
    async def _initialize_agent(self, agent_name: str, agent_class):
        """Initialize a specific agent"""
        self.state.register_component(agent_name, "agent", ["backend_manager"])
        
        try:
            agent_config = AgentConfig(name=agent_name)
            redis_client = None
            
            # Get Redis client if available
            if self.backend_manager:
                redis_client = self.backend_manager.get_connection("redis")
            
            # Pass backend_manager to agents that need it (like APIAnalyzer)
            if agent_name in ["api_analyzer", "evaluator", "code_generator"]:
                agent = agent_class(agent_config, self.system_config, self.backend_manager)
            else:
                agent = agent_class(agent_config, self.system_config, redis_client)

            self.agents[agent_name] = agent
            
            self.state.update_component_status(agent_name, ComponentStatus.RUNNING)
            self.logger.info("agent_initialized", agent=agent_name)
            
        except Exception as e:
            self.state.update_component_status(agent_name, ComponentStatus.ERROR, str(e))
            self.logger.error("agent_initialization_failed", agent=agent_name, error=str(e))
    
    async def _start_background_tasks(self):
        """Start background monitoring tasks"""
        if self.orchestration_config.enable_metrics:
            self._health_check_task = asyncio.create_task(self._health_check_loop())
    
    async def _health_check_loop(self):
        """Background health monitoring loop"""
        while self._is_running:
            try:
                await asyncio.sleep(self.orchestration_config.health_check_interval)
                await self._perform_health_checks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("health_check_loop_error", error=str(e))
    
    async def _perform_health_checks(self):
        """Perform health checks on all components"""
        # Update system metrics
        self.state.update_metrics({
            "memory_usage": self._get_memory_usage(),
            "active_tasks": len(self.state.running_tasks),
            "queue_size": len(self.state.task_queue)
        })
        
        # Check agent health
        for agent_name, agent in self.agents.items():
            try:
                # Simple health check - could be enhanced per agent type
                component = self.state.get_component(agent_name)
                if component and component.status == ComponentStatus.RUNNING:
                    component.last_activity = time.time()
            except Exception as e:
                self.state.update_component_status(agent_name, ComponentStatus.ERROR, str(e))
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage (simplified)"""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024  # MB
        except:
            return 0.0
    
    # Main API Methods
    
    async def process_document(self, 
                             source: str, 
                             source_type: str = "auto",
                             metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process a document through the RAG pipeline"""
        task_id = self.state.create_task("document_processing", metadata={
            "source": source,
            "source_type": source_type,
            "metadata": metadata
        })
        
        async with self.task_semaphore:
            self.state.start_task(task_id)
            
            try:
                if "document_processor" not in self.agents:
                    raise RuntimeError("Document processor not available")
                
                processor = self.agents["document_processor"]
                result = await processor.process_document(source, source_type)
                
                self.state.complete_task(task_id, result)
                return {"task_id": task_id, "result": result}
                
            except Exception as e:
                self.state.complete_task(task_id, error=str(e))
                raise
    
    async def analyze_api_documentation(self, 
                                      content: str, 
                                      source_url: str = "") -> Dict[str, Any]:
        """Analyze API documentation and extract structured information"""
        task_id = self.state.create_task("api_analysis", metadata={
            "source_url": source_url,
            "content_length": len(content)
        })
        
        async with self.task_semaphore:
            self.state.start_task(task_id)
            
            try:
                if "api_analyzer" not in self.agents:
                    raise RuntimeError("API analyzer not available")
                
                analyzer = self.agents["api_analyzer"]
                result = await analyzer.analyze_api_documentation(content, source_url)
                
                self.state.complete_task(task_id, result)
                return {"task_id": task_id, "result": analyzer.to_dict(result)}
                
            except Exception as e:
                self.state.complete_task(task_id, error=str(e))
                raise
    
    async def generate_code(self, 
                          api_doc: Dict[str, Any], 
                          language: str = "python",
                          template_name: str = "http_client") -> Dict[str, Any]:
        """Generate client code for an API"""
        task_id = self.state.create_task("code_generation", metadata={
            "language": language,
            "template": template_name,
            "api_title": api_doc.get("title", "Unknown")
        })
        
        async with self.task_semaphore:
            self.state.start_task(task_id)
            
            try:
                if "code_generator" not in self.agents:
                    raise RuntimeError("Code generator not available")
                
                generator = self.agents["code_generator"]
                result = await generator.generate_client_code(api_doc, language, template_name)
                
                self.state.complete_task(task_id, result)
                return {
                    "task_id": task_id, 
                    "result": {
                        "language": result.language,
                        "code": result.code,
                        "description": result.description,
                        "dependencies": result.dependencies,
                        "usage_example": result.usage_example
                    }
                }
                
            except Exception as e:
                self.state.complete_task(task_id, error=str(e))
                raise
    
    async def query_system(self, 
                         query: str, 
                         context: Optional[List[str]] = None,
                         max_results: int = 5) -> Dict[str, Any]:
        """Query the RAG system for information"""
        task_id = self.state.create_task("query", metadata={
            "query": query,
            "max_results": max_results,
            "has_context": bool(context)
        })
        
        async with self.task_semaphore:
            self.state.start_task(task_id)
            
            try:
                # Integrate with the hybrid search system through document processor
                if 'document_processor' in self.agents:
                    doc_processor = self.agents['document_processor']
                    search_result = await doc_processor.search_documents(query, max_results=max_results)
                    
                    # Generate answer using LLM with retrieved context
                    if self.llm_manager and search_result.get('documents'):
                        context_text = "\n\n".join([doc['content'] for doc in search_result['documents']])
                        
                        prompt = f"""Based on the following context, answer the question: {query}

Context:
{context_text}

Answer:"""
                        
                        llm_response = await self.llm_manager.generate(prompt, max_tokens=500)
                        
                        result = {
                            "query": query,
                            "answer": llm_response.content if llm_response else "Unable to generate response",
                            "sources": search_result['documents'],
                            "confidence": search_result.get('confidence', 0.0)
                        }
                    else:
                        result = {
                            "query": query,
                            "answer": "No relevant documents found or LLM unavailable",
                            "sources": [],
                            "confidence": 0.0
                        }
                else:
                    result = {
                        "query": query,
                        "answer": "Document processor not available",
                        "sources": [],
                        "confidence": 0.0
                    }
                
                self.state.complete_task(task_id, result)
                return {"task_id": task_id, "result": result}
                
            except Exception as e:
                self.state.complete_task(task_id, error=str(e))
                raise
    
    async def evaluate_system(self, 
                            test_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Evaluate system performance"""
        task_id = self.state.create_task("evaluation", metadata={
            "test_cases_count": len(test_cases)
        })
        
        async with self.task_semaphore:
            self.state.start_task(task_id)
            
            try:
                if "evaluator" not in self.agents:
                    raise RuntimeError("Evaluator not available")
                
                evaluator = self.agents["evaluator"]
                
                # Create evaluation suite
                suite = evaluator.create_evaluation_suite("orchestrator_eval", "System evaluation")
                for case in test_cases:
                    evaluator.add_test_case(
                        suite, 
                        case.get("query", ""), 
                        case.get("expected_answer"),
                        case.get("context")
                    )
                
                # Run actual evaluation with the RAG system
                results = await evaluator.run_evaluation(suite)
                
                result = {
                    "suite_name": suite.name,
                    "test_cases": len(test_cases),
                    "results": results,
                    "status": "completed" if results else "failed",
                    "summary": f"Evaluation completed with {len(results)} results" if results else "Evaluation failed"
                }
                
                self.state.complete_task(task_id, result)
                return {"task_id": task_id, "result": result}
                
            except Exception as e:
                self.state.complete_task(task_id, error=str(e))
                raise
    
    # System Management Methods
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        return self.state.get_system_summary()
    
    def get_health_report(self) -> Dict[str, Any]:
        """Get detailed health report"""
        return self.state_manager.get_health_report()
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific task"""
        task = self.state.get_task(task_id)
        if not task:
            return None
        
        return {
            "task_id": task.task_id,
            "type": task.type,
            "status": task.status,
            "progress": task.progress,
            "created_at": task.created_at,
            "started_at": task.started_at,
            "completed_at": task.completed_at,
            "error": task.error
        }
    
    def list_running_tasks(self) -> List[Dict[str, Any]]:
        """List all currently running tasks"""
        running_tasks = self.state.get_running_tasks()
        return [
            {
                "task_id": task.task_id,
                "type": task.type,
                "progress": task.progress,
                "started_at": task.started_at
            }
            for task in running_tasks
        ]
    
    async def shutdown(self):
        """Gracefully shutdown the orchestrator"""
        self.logger.info("shutting_down_orchestrator")
        self._is_running = False
        self.state.status = SystemStatus.SHUTTING_DOWN
        
        # Cancel background tasks
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        # Shutdown managers
        if self.llm_manager:
            await self.llm_manager.shutdown()
        
        if self.backend_manager:
            await self.backend_manager.shutdown()
        
        # Stop state manager
        await self.state_manager.stop()
        
        self.state.status = SystemStatus.OFFLINE
        self.logger.info("orchestrator_shutdown_complete")
    
    # Context manager support
    
    async def __aenter__(self):
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.shutdown()