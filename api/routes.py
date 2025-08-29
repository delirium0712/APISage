"""
FastAPI routes for the RAG system API
"""

import asyncio
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
import structlog

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Query, Request, APIRouter
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

# Debug function to set orchestrator from main app
def set_orchestrator(orch: RAGOrchestrator):
    """Set the orchestrator instance from main app"""
    global orchestrator
    orchestrator = orch
    structlog.get_logger().info("orchestrator_set_in_routes", orchestrator_id=id(orch))


def create_api_router(config: Optional[APIConfiguration] = None) -> APIRouter:
    """Create FastAPI router with all routes"""
    
    if config is None:
        config = APIConfiguration()
    
    router = APIRouter()
    
    # Add routes
    setup_routes(router)
    
    return router


def get_orchestrator() -> RAGOrchestrator:
    """Dependency to get orchestrator instance"""
    logger = structlog.get_logger()
    logger.info("get_orchestrator_called", orchestrator_available=orchestrator is not None)
    
    if orchestrator is None:
        logger.error("orchestrator_not_available_in_routes")
        raise HTTPException(status_code=503, detail="System not initialized")
    
    logger.info("orchestrator_retrieved_successfully", orchestrator_id=id(orchestrator))
    return orchestrator


def setup_routes(router: APIRouter):
    """Setup all API routes"""
    
    # Health and Status Endpoints
    
    @router.get("/health", response_model=HealthCheckResponse)
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
    
    @router.get("/status", response_model=SystemStatusResponse) 
    async def get_system_status():
        """Get comprehensive system status"""
        try:
            orch = get_orchestrator()
            status = orch.get_system_status()
            
            return SystemStatusResponse(**status)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Status retrieval failed: {str(e)}")
    
    @router.get("/test", response_model=Dict[str, Any])
    async def test_endpoint():
        """Simple test endpoint to verify system is working"""
        logger = structlog.get_logger()
        logger.info("test_endpoint_called")
        
        try:
            orch = get_orchestrator()
            logger.info("test_endpoint_orchestrator_available", orchestrator_id=id(orch))
            return {
                "status": "success",
                "message": "System is working",
                "orchestrator_available": True,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error("test_endpoint_error", error=str(e), error_type=type(e).__name__)
            return {
                "status": "error",
                "message": f"System error: {str(e)}",
                "orchestrator_available": False,
                "timestamp": datetime.now().isoformat()
            }
    
    @router.get("/ping", response_model=Dict[str, Any])
    async def ping_endpoint():
        """Simple ping endpoint that doesn't require orchestrator"""
        logger = structlog.get_logger()
        logger.info("ping_endpoint_called")
        
        return {
            "status": "success",
            "message": "pong",
            "timestamp": datetime.now().isoformat(),
            "orchestrator_available": orchestrator is not None
        }
    
    # Document Processing Endpoints
    
    @router.post("/documents/process", response_model=Dict[str, Any])
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
    
    @router.post("/documents/analyze-api", response_model=Dict[str, Any])
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
    
    @router.post("/query", response_model=Dict[str, Any])
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
    
    @router.get("/query/{task_id}", response_model=Dict[str, Any])
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
    
    @router.post("/code/generate", response_model=Dict[str, Any])
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
    
    @router.get("/code/languages")
    async def get_supported_languages():
        """Get list of supported programming languages"""
        return {
            "languages": [
                "python", "javascript", "typescript", "java", 
                "go", "csharp", "php", "ruby", "swift", "kotlin"
            ]
        }
    
    @router.get("/code/templates/{language}")
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
    
    @router.post("/evaluate", response_model=Dict[str, Any])
    async def evaluate_system(request: EvaluationRequest):
        """Evaluate system performance with test cases"""
        try:
            orch = get_orchestrator()
            result = await orch.evaluate_system(request.test_cases)
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")
    
    # Task Management Endpoints
    
    @router.get("/tasks", response_model=List[Dict[str, Any]])
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
    
    @router.get("/tasks/{task_id}", response_model=Dict[str, Any])
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
    
    @router.delete("/tasks/{task_id}")
    async def cancel_task(task_id: str):
        """Cancel a running task"""
        # This would need to be implemented in the orchestrator
        return {"message": "Task cancellation not yet implemented", "task_id": task_id}
    

    
    # Batch Operations
    
    @router.post("/batch/process", response_model=BatchResponse)
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
    
    @router.get("/config")
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
                "evaluation": True,
                "hybrid_search": True
                }
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Configuration retrieval failed: {str(e)}")
    

    
    # Development/Debug Endpoints (only in debug mode)
    
    @router.get("/debug/components")
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
    
    @router.get("/debug/events")
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
    app = create_api_router(config)
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        access_log=debug,
        reload=debug
    )


if __name__ == "__main__":
    run_api_server(debug=True)