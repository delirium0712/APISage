"""
Pydantic models for API request/response validation
"""

from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field, validator
from datetime import datetime
from enum import Enum


class TaskStatus(str, Enum):
    """Task status enumeration"""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ComponentStatus(str, Enum):
    """Component status enumeration"""
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"
    UNAVAILABLE = "unavailable"


class SystemStatus(str, Enum):
    """System status enumeration"""
    INITIALIZING = "initializing"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    SHUTTING_DOWN = "shutting_down"
    OFFLINE = "offline"


# Request Models

class DocumentProcessRequest(BaseModel):
    """Request to process a document"""
    source: str = Field(..., description="Document source (URL, file path, or text)")
    source_type: str = Field(default="auto", description="Type of source: auto, url, file, text")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")
    
    @validator('source_type')
    def validate_source_type(cls, v):
        allowed = ["auto", "url", "file", "text"]
        if v not in allowed:
            raise ValueError(f"source_type must be one of: {allowed}")
        return v


class QueryRequest(BaseModel):
    """Request to query the RAG system"""
    query: str = Field(..., min_length=1, description="The question or query")
    context: Optional[List[str]] = Field(default=None, description="Additional context")
    max_results: int = Field(default=5, ge=1, le=20, description="Maximum number of results")
    search_type: str = Field(default="hybrid", description="Search type: hybrid, vector, bm25")
    include_sources: bool = Field(default=True, description="Include source information")
    
    @validator('search_type')
    def validate_search_type(cls, v):
        allowed = ["hybrid", "vector", "bm25", "semantic", "keyword"]
        if v not in allowed:
            raise ValueError(f"search_type must be one of: {allowed}")
        return v


class APIAnalysisRequest(BaseModel):
    """Request to analyze API documentation"""
    content: str = Field(..., min_length=10, description="API documentation content")
    source_url: Optional[str] = Field(default="", description="Source URL of the documentation")
    format_hint: Optional[str] = Field(default=None, description="Format hint: html, markdown, openapi")


class CodeGenerationRequest(BaseModel):
    """Request to generate code from API documentation"""
    api_doc: Dict[str, Any] = Field(..., description="Parsed API documentation")
    language: str = Field(default="python", description="Programming language")
    template_name: str = Field(default="http_client", description="Code template to use")
    
    @validator('language')
    def validate_language(cls, v):
        allowed = ["python", "javascript", "typescript", "java", "go", "csharp", "php", "ruby"]
        if v.lower() not in allowed:
            raise ValueError(f"language must be one of: {allowed}")
        return v.lower()


class EvaluationRequest(BaseModel):
    """Request to evaluate system performance"""
    test_cases: List[Dict[str, Any]] = Field(..., min_items=1, description="Test cases to evaluate")
    suite_name: str = Field(default="api_evaluation", description="Name for the evaluation suite")
    include_detailed_metrics: bool = Field(default=True, description="Include detailed metrics")


class WebScrapingRequest(BaseModel):
    """Request to scrape web content"""
    url: str = Field(..., description="URL to scrape")
    use_javascript: bool = Field(default=False, description="Use JavaScript rendering")
    follow_links: bool = Field(default=False, description="Follow and scrape linked pages")
    max_depth: int = Field(default=1, ge=1, le=3, description="Maximum depth for link following")
    max_pages: int = Field(default=10, ge=1, le=100, description="Maximum pages to scrape")


# Response Models

class TaskResponse(BaseModel):
    """Response with task information"""
    task_id: str = Field(..., description="Unique task identifier")
    status: TaskStatus = Field(..., description="Current task status")
    progress: float = Field(default=0.0, ge=0.0, le=100.0, description="Progress percentage")
    created_at: datetime = Field(..., description="Task creation timestamp")
    started_at: Optional[datetime] = Field(default=None, description="Task start timestamp")
    completed_at: Optional[datetime] = Field(default=None, description="Task completion timestamp")
    result: Optional[Dict[str, Any]] = Field(default=None, description="Task result data")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class DocumentProcessResponse(BaseModel):
    """Response from document processing"""
    task_id: str = Field(..., description="Task identifier")
    source: str = Field(..., description="Original document source")
    format: str = Field(..., description="Detected document format")
    content_length: int = Field(..., description="Length of extracted content")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Document metadata")
    success: bool = Field(..., description="Whether processing was successful")


class QueryResponse(BaseModel):
    """Response from RAG query"""
    task_id: str = Field(..., description="Task identifier") 
    query: str = Field(..., description="Original query")
    answer: str = Field(..., description="Generated answer")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    response_time: float = Field(..., description="Response time in seconds")
    sources: Optional[List[Dict[str, Any]]] = Field(default=None, description="Source documents used")
    search_results_count: int = Field(..., description="Number of search results found")


class APIAnalysisResponse(BaseModel):
    """Response from API analysis"""
    task_id: str = Field(..., description="Task identifier")
    title: str = Field(..., description="API title")
    version: str = Field(default="", description="API version")
    base_url: str = Field(default="", description="Base URL")
    description: str = Field(default="", description="API description")
    endpoints_count: int = Field(..., description="Number of endpoints found")
    authentication_methods: int = Field(..., description="Number of auth methods found")
    analysis_success: bool = Field(..., description="Whether analysis was successful")


class CodeGenerationResponse(BaseModel):
    """Response from code generation"""
    task_id: str = Field(..., description="Task identifier")
    language: str = Field(..., description="Programming language")
    code: str = Field(..., description="Generated code")
    description: str = Field(..., description="Code description")
    dependencies: List[str] = Field(default_factory=list, description="Required dependencies")
    usage_example: str = Field(default="", description="Usage example")
    generation_success: bool = Field(..., description="Whether generation was successful")


class SystemStatusResponse(BaseModel):
    """Response with system status"""
    status: SystemStatus = Field(..., description="Overall system status")
    uptime: float = Field(..., description="System uptime in seconds")
    components: Dict[str, Any] = Field(..., description="Component status information")
    tasks: Dict[str, Any] = Field(..., description="Task information")
    performance: Dict[str, Any] = Field(..., description="Performance metrics")
    last_update: float = Field(..., description="Last status update timestamp")


class ComponentStatusResponse(BaseModel):
    """Response with component status details"""
    name: str = Field(..., description="Component name")
    type: str = Field(..., description="Component type")
    status: ComponentStatus = Field(..., description="Component status")
    healthy: bool = Field(..., description="Whether component is healthy")
    last_activity: float = Field(..., description="Last activity timestamp")
    error_count: int = Field(..., description="Number of errors encountered")
    last_error: Optional[str] = Field(default=None, description="Most recent error message")
    metrics: Dict[str, float] = Field(default_factory=dict, description="Component metrics")


class HealthCheckResponse(BaseModel):
    """Response from health check endpoint"""
    status: SystemStatus = Field(..., description="System health status")
    timestamp: datetime = Field(..., description="Health check timestamp")
    components: List[ComponentStatusResponse] = Field(..., description="Component health details")
    overall_health_percentage: float = Field(..., ge=0.0, le=100.0, description="Overall health percentage")
    issues: List[str] = Field(default_factory=list, description="Current system issues")


class ErrorResponse(BaseModel):
    """Error response model"""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp")
    request_id: Optional[str] = Field(default=None, description="Request identifier")


class ValidationErrorResponse(BaseModel):
    """Validation error response"""
    error: str = Field(default="validation_error", description="Error type")
    message: str = Field(..., description="Validation error message")
    field_errors: List[Dict[str, Any]] = Field(..., description="Field-specific validation errors")


# Configuration Models

class APIConfiguration(BaseModel):
    """API server configuration"""
    host: str = Field(default="localhost", description="Server host")
    port: int = Field(default=8000, ge=1, le=65535, description="Server port")
    debug: bool = Field(default=False, description="Debug mode")
    cors_enabled: bool = Field(default=True, description="Enable CORS")
    cors_origins: List[str] = Field(default=["*"], description="Allowed CORS origins")
    rate_limiting: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_requests: int = Field(default=100, description="Requests per minute limit")
    max_request_size: int = Field(default=10*1024*1024, description="Maximum request size in bytes")
    timeout: int = Field(default=300, description="Request timeout in seconds")


# Utility Models

class PaginationParams(BaseModel):
    """Pagination parameters"""
    page: int = Field(default=1, ge=1, description="Page number")
    limit: int = Field(default=20, ge=1, le=100, description="Items per page")
    
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.limit


class PaginatedResponse(BaseModel):
    """Paginated response wrapper"""
    items: List[Dict[str, Any]] = Field(..., description="Response items")
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    limit: int = Field(..., description="Items per page")
    pages: int = Field(..., description="Total number of pages")
    
    @validator('pages', pre=True, always=True)
    def calculate_pages(cls, v, values):
        total = values.get('total', 0)
        limit = values.get('limit', 20)
        return (total + limit - 1) // limit if limit > 0 else 0


class BatchRequest(BaseModel):
    """Batch request wrapper"""
    requests: List[Dict[str, Any]] = Field(..., min_items=1, max_items=10, description="Batch of requests")
    parallel: bool = Field(default=True, description="Process requests in parallel")


class BatchResponse(BaseModel):
    """Batch response wrapper"""
    results: List[Dict[str, Any]] = Field(..., description="Batch results")
    successful: int = Field(..., description="Number of successful requests")
    failed: int = Field(..., description="Number of failed requests")
    total_time: float = Field(..., description="Total processing time")


# WebSocket Models (for real-time updates)

class WebSocketMessage(BaseModel):
    """WebSocket message model"""
    type: str = Field(..., description="Message type")
    data: Dict[str, Any] = Field(..., description="Message data")
    timestamp: datetime = Field(default_factory=datetime.now, description="Message timestamp")


class TaskUpdateMessage(WebSocketMessage):
    """Task progress update message"""
    type: str = Field(default="task_update", description="Message type")
    task_id: str = Field(..., description="Task identifier")
    status: TaskStatus = Field(..., description="Task status")
    progress: float = Field(..., description="Progress percentage")


class SystemEventMessage(WebSocketMessage):
    """System event message"""
    type: str = Field(default="system_event", description="Message type") 
    event_type: str = Field(..., description="Event type")
    component: Optional[str] = Field(default=None, description="Related component")
    severity: str = Field(default="info", description="Event severity")