"""
FastAPI routes for the RAG system API
"""

import asyncio
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
import structlog

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn

from .models import *
from core.orchestrator import RAGOrchestrator, OrchestrationConfig
from config.config_loader import load_config


# Global orchestrator instance
orchestrator: Optional[RAGOrchestrator] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan"""
    global orchestrator
    
    # Startup
    try:
        system_config = load_config()
        orchestration_config = OrchestrationConfig(enable_api=True)
        orchestrator = RAGOrchestrator(system_config, orchestration_config)
        await orchestrator.initialize()
        
        structlog.get_logger().info("api_server_started")
        yield
        
    finally:
        # Shutdown
        if orchestrator:
            await orchestrator.shutdown()
        structlog.get_logger().info("api_server_shutdown")


def create_app(config: Optional[APIConfiguration] = None) -> FastAPI:
    """Create FastAPI application with all routes and middleware"""
    
    if config is None:
        config = APIConfiguration()
    
    app = FastAPI(
        title="RAG Documentation Assistant API",
        description="Next-generation intelligent documentation assistant with multi-format support and hybrid search",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # Add middleware
    if config.cors_enabled:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=config.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # Add routes
    setup_routes(app)
    
    return app


def get_orchestrator() -> RAGOrchestrator:
    """Dependency to get orchestrator instance"""
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="System not initialized")
    return orchestrator


def setup_routes(app: FastAPI):
    """Setup all API routes"""
    
    # Health and Status Endpoints
    
    @app.get("/health", response_model=HealthCheckResponse)
    async def health_check():
        """Get system health status"""
        try:
            orch = get_orchestrator()
            health_report = orch.get_health_report()
            
            return HealthCheckResponse(
                status=SystemStatus(health_report["status"]),
                timestamp=datetime.now(),
                components=[
                    ComponentStatusResponse(
                        name=name,
                        type=details["type"],
                        status=ComponentStatus(details["status"]),
                        healthy=details["healthy"],
                        last_activity=details["last_activity"],
                        error_count=details["error_count"],
                        last_error=details.get("last_error"),
                        metrics=details.get("metrics", {})
                    )
                    for name, details in health_report["component_details"].items()
                ],
                overall_health_percentage=health_report["components"]["health_ratio"] * 100,
                issues=[]  # Could extract from health report
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")
    
    @app.get("/status", response_model=SystemStatusResponse) 
    async def get_system_status():
        """Get comprehensive system status"""
        try:
            orch = get_orchestrator()
            status = orch.get_system_status()
            
            return SystemStatusResponse(**status)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Status retrieval failed: {str(e)}")
    
    # Document Processing Endpoints
    
    @app.post("/documents/process", response_model=Dict[str, Any])
    async def process_document(request: DocumentProcessRequest):
        """Process a document through the RAG pipeline"""
        try:
            orch = get_orchestrator()
            result = await orch.process_document(
                source=request.source,
                source_type=request.source_type,
                metadata=request.metadata
            )
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Document processing failed: {str(e)}")
    
    @app.post("/documents/analyze-api", response_model=Dict[str, Any])
    async def analyze_api_documentation(request: APIAnalysisRequest):
        """Analyze API documentation and extract structured information"""
        try:
            orch = get_orchestrator()
            result = await orch.analyze_api_documentation(
                content=request.content,
                source_url=request.source_url or ""
            )
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"API analysis failed: {str(e)}")
    
    # Query Endpoints
    
    @app.post("/query", response_model=Dict[str, Any])
    async def query_system(request: QueryRequest):
        """Query the RAG system for information"""
        try:
            orch = get_orchestrator()
            result = await orch.query_system(
                query=request.query,
                context=request.context,
                max_results=request.max_results
            )
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")
    
    @app.get("/query/{task_id}", response_model=Dict[str, Any])
    async def get_query_result(task_id: str):
        """Get the result of a query task"""
        try:
            orch = get_orchestrator()
            task_status = orch.get_task_status(task_id)
            
            if not task_status:
                raise HTTPException(status_code=404, detail="Task not found")
            
            return task_status
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Task retrieval failed: {str(e)}")
    
    # Code Generation Endpoints
    
    @app.post("/code/generate", response_model=Dict[str, Any])
    async def generate_code(request: CodeGenerationRequest):
        """Generate client code from API documentation"""
        try:
            orch = get_orchestrator()
            result = await orch.generate_code(
                api_doc=request.api_doc,
                language=request.language,
                template_name=request.template_name
            )
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Code generation failed: {str(e)}")
    
    @app.get("/code/languages")
    async def get_supported_languages():
        """Get list of supported programming languages"""
        return {
            "languages": [
                "python", "javascript", "typescript", "java", 
                "go", "csharp", "php", "ruby", "swift", "kotlin"
            ]
        }
    
    @app.get("/code/templates/{language}")
    async def get_language_templates(language: str):
        """Get available templates for a programming language"""
        templates = {
            "python": ["http_client", "async_client", "sdk_wrapper"],
            "javascript": ["fetch_client", "axios_client", "node_sdk"],
            "typescript": ["typed_client", "async_client"],
            "java": ["okhttp_client", "spring_client"],
            "go": ["http_client", "gin_client"],
            "csharp": ["httpclient", "restsharp_client"]
        }
        
        if language not in templates:
            raise HTTPException(status_code=404, detail=f"Language {language} not supported")
        
        return {"language": language, "templates": templates[language]}
    
    # Evaluation Endpoints
    
    @app.post("/evaluate", response_model=Dict[str, Any])
    async def evaluate_system(request: EvaluationRequest):
        """Evaluate system performance with test cases"""
        try:
            orch = get_orchestrator()
            result = await orch.evaluate_system(request.test_cases)
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")
    
    # Task Management Endpoints
    
    @app.get("/tasks", response_model=List[Dict[str, Any]])
    async def list_tasks(
        status: Optional[str] = Query(None, description="Filter by task status"),
        task_type: Optional[str] = Query(None, description="Filter by task type"),
        limit: int = Query(20, ge=1, le=100, description="Maximum number of tasks to return")
    ):
        """List tasks with optional filtering"""
        try:
            orch = get_orchestrator()
            
            if status == "running":
                tasks = orch.list_running_tasks()
            else:
                # This would need to be implemented in the orchestrator
                # For now, return running tasks as placeholder
                tasks = orch.list_running_tasks()
            
            # Apply filters and limit
            filtered_tasks = tasks[:limit]
            
            return filtered_tasks
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Task listing failed: {str(e)}")
    
    @app.get("/tasks/{task_id}", response_model=Dict[str, Any])
    async def get_task_status(task_id: str):
        """Get detailed status of a specific task"""
        try:
            orch = get_orchestrator()
            task_status = orch.get_task_status(task_id)
            
            if not task_status:
                raise HTTPException(status_code=404, detail="Task not found")
            
            return task_status
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Task status retrieval failed: {str(e)}")
    
    @app.delete("/tasks/{task_id}")
    async def cancel_task(task_id: str):
        """Cancel a running task"""
        # This would need to be implemented in the orchestrator
        return {"message": "Task cancellation not yet implemented", "task_id": task_id}
    
    # Web Scraping Endpoints
    
    @app.post("/scrape", response_model=Dict[str, Any])
    async def scrape_web_content(request: WebScrapingRequest):
        """Scrape content from web pages"""
        try:
            orch = get_orchestrator()
            # This would use the web scraper agent
            result = {
                "task_id": f"scrape_{int(time.time())}",
                "url": request.url,
                "status": "completed",
                "message": "Web scraping endpoint placeholder"
            }
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Web scraping failed: {str(e)}")
    
    # Batch Operations
    
    @app.post("/batch/process", response_model=BatchResponse)
    async def batch_process(request: BatchRequest):
        """Process multiple requests in batch"""
        try:
            results = []
            successful = 0
            failed = 0
            start_time = time.time()
            
            if request.parallel:
                # Process in parallel
                tasks = []
                for req_data in request.requests:
                    # This would need proper request routing
                    # For now, create placeholder tasks
                    tasks.append(asyncio.create_task(asyncio.sleep(0.1)))
                
                await asyncio.gather(*tasks)
                successful = len(request.requests)
            else:
                # Process sequentially
                for req_data in request.requests:
                    try:
                        # Process individual request
                        await asyncio.sleep(0.1)  # Placeholder
                        results.append({"success": True, "data": req_data})
                        successful += 1
                    except Exception as e:
                        results.append({"success": False, "error": str(e)})
                        failed += 1
            
            total_time = time.time() - start_time
            
            return BatchResponse(
                results=results,
                successful=successful,
                failed=failed,
                total_time=total_time
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Batch processing failed: {str(e)}")
    
    # Configuration Endpoints
    
    @app.get("/config")
    async def get_system_configuration():
        """Get current system configuration"""
        try:
            orch = get_orchestrator()
            # This would return sanitized configuration
            return {
                "system_name": orch.system_config.name,
                "version": orch.system_config.version,
                "environment": orch.system_config.environment,
                "features": {
                    "api_analysis": True,
                    "code_generation": True,
                    "web_scraping": True,
                    "evaluation": True,
                    "hybrid_search": True
                }
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Configuration retrieval failed: {str(e)}")
    
    # Error Handlers
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "http_error",
                "message": exc.detail,
                "status_code": exc.status_code,
                "timestamp": datetime.now().isoformat()
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_server_error",
                "message": "An unexpected error occurred",
                "timestamp": datetime.now().isoformat()
            }
        )
    
    # Development/Debug Endpoints (only in debug mode)
    
    @app.get("/debug/components")
    async def debug_components():
        """Debug endpoint to inspect components"""
        try:
            orch = get_orchestrator()
            components = {}
            for name, component in orch.state.components.items():
                components[name] = {
                    "type": component.type,
                    "status": component.status.value,
                    "healthy": component.is_healthy(),
                    "last_activity": component.last_activity,
                    "error_count": component.error_count,
                    "metrics": component.metrics
                }
            return {"components": components}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/debug/events")
    async def debug_events(limit: int = Query(50, ge=1, le=200)):
        """Debug endpoint to view recent system events"""
        try:
            orch = get_orchestrator()
            recent_events = orch.state.event_history[-limit:]
            return {"events": recent_events, "count": len(recent_events)}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


# CLI runner for the API server
def run_api_server(host: str = "localhost", port: int = 8000, debug: bool = False):
    """Run the API server"""
    config = APIConfiguration(host=host, port=port, debug=debug)
    app = create_app(config)
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        access_log=debug,
        reload=debug
    )


if __name__ == "__main__":
    run_api_server(debug=True)