"""
API Agent Framework - FastAPI Application Entry Point
"""

import time

# Add a timestamp to force reload
RELOAD_TIMESTAMP = time.time()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog
from contextlib import asynccontextmanager

from .routes import create_api_router
from .models import HealthCheckResponse, ComponentStatusResponse, ComponentStatus, SystemStatus
from core.orchestrator import RAGOrchestrator, OrchestrationConfig
from config.config_loader import load_config

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("api_agent_starting", version="1.0.0")
    
    try:
        # Initialize the orchestrator
        logger.info("loading_system_config")
        system_config = load_config()
        logger.info("system_config_loaded", config_keys=list(system_config.__dict__.keys()) if hasattr(system_config, '__dict__') else "no_attrs")
        
        logger.info("creating_orchestration_config")
        orchestration_config = OrchestrationConfig(enable_api=True)
        logger.info("orchestration_config_created", config=orchestration_config.__dict__)
        
        logger.info("creating_rag_orchestrator")
        orchestrator = RAGOrchestrator(system_config, orchestration_config)
        logger.info("rag_orchestrator_created")
        
        logger.info("initializing_orchestrator")
        await orchestrator.initialize()
        logger.info("orchestrator_initialized_successfully")
        
        # Store orchestrator in routes module
        logger.info("storing_orchestrator_in_routes")
        from .routes import set_orchestrator
        set_orchestrator(orchestrator)
        logger.info("orchestrator_stored_in_routes")
        
        logger.info("orchestrator_initialization_complete")
    except Exception as e:
        logger.error("orchestrator_initialization_failed", 
                   error=str(e), 
                   error_type=type(e).__name__,
                   traceback=str(e.__traceback__) if hasattr(e, '__traceback__') else None)
        # Continue without orchestrator for now
    
    yield
    
    # Shutdown
    logger.info("api_agent_shutting_down")


def create_api_app() -> FastAPI:
    """Create and configure the FastAPI application"""
    
    app = FastAPI(
        title="API Agent Framework",
        description="Self-Hosted AI Agent Framework for API Documentation & Knowledge Management",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add request timing middleware
    @app.middleware("http")
    async def add_process_time_header(request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response
    
    # Add exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error("unhandled_exception", 
                    error=str(exc), 
                    error_type=type(exc).__name__,
                    path=request.url.path,
                    method=request.method,
                    traceback=str(exc.__traceback__) if hasattr(exc, '__traceback__') else None)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "detail": str(exc),
                "error_type": type(exc).__name__,
                "timestamp": time.time()
            }
        )
    
    # Include routes
    app.include_router(create_api_router(), prefix="/api/v1")
    
    # Health check endpoint
    @app.get("/health", response_model=HealthCheckResponse)
    async def health_check():
        """Health check endpoint"""
        from datetime import datetime
        
        try:
            # Check if orchestrator is available
            from .routes import orchestrator as routes_orchestrator
            
            if routes_orchestrator is None:
                logger.warning("health_check_orchestrator_not_available")
                return HealthCheckResponse(
                    status=SystemStatus.UNHEALTHY,
                    timestamp=datetime.now(),
                    components=[
                        ComponentStatusResponse(
                            name="api",
                            type="service",
                            status=ComponentStatus.RUNNING,
                            healthy=True,
                            last_activity=time.time(),
                            error_count=0,
                            last_error=None,
                            metrics={}
                        ),
                        ComponentStatusResponse(
                            name="orchestrator",
                            type="service",
                            status=ComponentStatus.INITIALIZING,
                            healthy=False,
                            last_activity=time.time(),
                            error_count=1,
                            last_error="Orchestrator not initialized",
                            metrics={}
                        )
                    ],
                    overall_health_percentage=50.0,
                    issues=["Orchestrator not initialized"]
                )
            
            # Try to get health from orchestrator
            try:
                health_report = routes_orchestrator.get_health_report()
                logger.info("health_check_success", orchestrator_status="available")
                
                return HealthCheckResponse(
                    status=SystemStatus.HEALTHY,
                    timestamp=datetime.now(),
                    components=[
                        ComponentStatusResponse(
                            name="api",
                            type="service",
                            status=ComponentStatus.RUNNING,
                            healthy=True,
                            last_activity=time.time(),
                            error_count=0,
                            last_error=None,
                            metrics={}
                        ),
                        ComponentStatusResponse(
                            name="orchestrator",
                            type="service",
                            status=ComponentStatus.RUNNING,
                            healthy=True,
                            last_activity=time.time(),
                            error_count=0,
                            last_error=None,
                            metrics={}
                        )
                    ],
                    overall_health_percentage=100.0,
                    issues=[]
                )
                
            except Exception as e:
                logger.error("health_check_orchestrator_error", error=str(e), error_type=type(e).__name__)
                return HealthCheckResponse(
                    status=SystemStatus.UNHEALTHY,
                    timestamp=datetime.now(),
                    components=[
                        ComponentStatusResponse(
                            name="api",
                            type="service",
                            status=ComponentStatus.RUNNING,
                            healthy=True,
                            last_activity=time.time(),
                            error_count=0,
                            last_error=None,
                            metrics={}
                        ),
                        ComponentStatusResponse(
                            name="orchestrator",
                            type="service",
                            status=ComponentStatus.ERROR,
                            healthy=False,
                            last_activity=time.time(),
                            error_count=1,
                            last_error=str(e),
                            metrics={}
                        )
                    ],
                    overall_health_percentage=50.0,
                    issues=[f"Orchestrator error: {str(e)}"]
                )
                
        except Exception as e:
            logger.error("health_check_unexpected_error", error=str(e), error_type=type(e).__name__)
            return HealthCheckResponse(
                status=SystemStatus.UNHEALTHY,
                timestamp=datetime.now(),
                components=[
                    ComponentStatusResponse(
                        name="api",
                        type="service",
                        status=ComponentStatus.ERROR,
                        healthy=False,
                        last_activity=time.time(),
                        error_count=1,
                        last_error=str(e),
                        metrics={}
                    )
                ],
                overall_health_percentage=0.0,
                issues=[f"Unexpected error: {str(e)}"]
            )
    
    # Root endpoint
    @app.get("/")
    async def root():
        """Root endpoint with API information"""
        return {
            "name": "API Agent Framework",
            "version": "1.0.0",
            "description": "Self-Hosted AI Agent Framework for API Documentation & Knowledge Management",
            "docs": "/docs",
            "health": "/health",
            "api": "/api/v1"
        }
    
    return app

# Create the app instance
app = create_api_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
