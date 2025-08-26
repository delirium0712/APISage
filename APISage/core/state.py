"""
System state management for the RAG orchestrator
"""

import asyncio
import time
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone
import structlog


class SystemStatus(Enum):
    """Overall system status"""
    INITIALIZING = "initializing"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    SHUTTING_DOWN = "shutting_down"
    OFFLINE = "offline"


class ComponentStatus(Enum):
    """Individual component status"""
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"
    UNAVAILABLE = "unavailable"


@dataclass
class ComponentState:
    """State information for a system component"""
    name: str
    type: str  # "agent", "vector_store", "llm_provider", etc.
    status: ComponentStatus = ComponentStatus.STOPPED
    last_activity: float = 0.0
    error_count: int = 0
    last_error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, float] = field(default_factory=dict)
    
    def is_healthy(self) -> bool:
        """Check if component is healthy"""
        return self.status == ComponentStatus.RUNNING and self.error_count < 5


@dataclass 
class TaskState:
    """State information for a running task"""
    task_id: str
    type: str  # "document_processing", "query", "evaluation", etc.
    status: str  # "queued", "running", "completed", "failed"
    created_at: float
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    progress: float = 0.0
    result: Optional[Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class SystemState:
    """
    Maintains the current state of the entire RAG system including:
    - Component health and status
    - Running tasks and their progress
    - System metrics and performance data
    - Configuration and settings
    """
    
    def __init__(self):
        self.logger = structlog.get_logger(__name__)
        
        # System-level state
        self.status = SystemStatus.INITIALIZING
        self.started_at = time.time()
        self.last_update = time.time()
        
        # Component tracking
        self.components: Dict[str, ComponentState] = {}
        self.component_dependencies: Dict[str, Set[str]] = {}
        
        # Task tracking
        self.tasks: Dict[str, TaskState] = {}
        self.task_queue: List[str] = []
        self.running_tasks: Set[str] = set()
        
        # System metrics
        self.metrics = {
            "total_queries": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "avg_response_time": 0.0,
            "uptime": 0.0,
            "memory_usage": 0.0,
            "cpu_usage": 0.0
        }
        
        # Configuration state
        self.configuration: Dict[str, Any] = {}
        self.feature_flags: Dict[str, bool] = {}
        
        # Event history (keep last 1000 events)
        self.event_history: List[Dict[str, Any]] = []
        self.max_events = 1000
    
    def register_component(self, 
                         name: str, 
                         component_type: str, 
                         dependencies: List[str] = None) -> None:
        """Register a new component with the system"""
        self.components[name] = ComponentState(
            name=name,
            type=component_type,
            status=ComponentStatus.STARTING
        )
        
        if dependencies:
            self.component_dependencies[name] = set(dependencies)
        
        self._log_event("component_registered", {
            "component": name,
            "type": component_type,
            "dependencies": dependencies or []
        })
    
    def update_component_status(self, 
                              name: str, 
                              status: ComponentStatus,
                              error: Optional[str] = None,
                              metadata: Optional[Dict[str, Any]] = None) -> None:
        """Update component status"""
        if name not in self.components:
            self.logger.warning("unknown_component_status_update", component=name)
            return
        
        component = self.components[name]
        old_status = component.status
        
        component.status = status
        component.last_activity = time.time()
        
        if error:
            component.error_count += 1
            component.last_error = error
        elif status == ComponentStatus.RUNNING:
            # Reset error count on successful start
            component.error_count = 0
            component.last_error = None
        
        if metadata:
            component.metadata.update(metadata)
        
        # Update system status based on component changes
        self._update_system_status()
        
        if old_status != status:
            self._log_event("component_status_changed", {
                "component": name,
                "old_status": old_status.value,
                "new_status": status.value,
                "error": error
            })
    
    def update_component_metrics(self, 
                               name: str, 
                               metrics: Dict[str, float]) -> None:
        """Update component metrics"""
        if name not in self.components:
            return
        
        self.components[name].metrics.update(metrics)
        self.components[name].last_activity = time.time()
    
    def create_task(self, 
                   task_type: str, 
                   task_id: Optional[str] = None,
                   metadata: Optional[Dict[str, Any]] = None) -> str:
        """Create a new task and return task ID"""
        if not task_id:
            task_id = f"{task_type}_{int(time.time() * 1000)}"
        
        task = TaskState(
            task_id=task_id,
            type=task_type,
            status="queued",
            created_at=time.time(),
            metadata=metadata or {}
        )
        
        self.tasks[task_id] = task
        self.task_queue.append(task_id)
        
        self._log_event("task_created", {
            "task_id": task_id,
            "type": task_type,
            "queue_size": len(self.task_queue)
        })
        
        return task_id
    
    def start_task(self, task_id: str) -> bool:
        """Mark task as started"""
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        task.status = "running"
        task.started_at = time.time()
        
        if task_id in self.task_queue:
            self.task_queue.remove(task_id)
        
        self.running_tasks.add(task_id)
        
        self._log_event("task_started", {"task_id": task_id, "type": task.type})
        return True
    
    def complete_task(self, 
                     task_id: str, 
                     result: Optional[Any] = None,
                     error: Optional[str] = None) -> bool:
        """Mark task as completed"""
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        task.completed_at = time.time()
        task.progress = 100.0
        
        if error:
            task.status = "failed"
            task.error = error
            self.metrics["failed_queries"] += 1
        else:
            task.status = "completed"
            task.result = result
            self.metrics["successful_queries"] += 1
        
        self.running_tasks.discard(task_id)
        self.metrics["total_queries"] += 1
        
        # Update average response time
        if task.started_at:
            response_time = task.completed_at - task.started_at
            current_avg = self.metrics["avg_response_time"]
            total_queries = self.metrics["total_queries"]
            
            self.metrics["avg_response_time"] = (
                (current_avg * (total_queries - 1) + response_time) / total_queries
            )
        
        self._log_event("task_completed", {
            "task_id": task_id,
            "type": task.type,
            "status": task.status,
            "duration": task.completed_at - (task.started_at or task.created_at)
        })
        
        return True
    
    def update_task_progress(self, task_id: str, progress: float) -> bool:
        """Update task progress (0-100)"""
        if task_id not in self.tasks:
            return False
        
        self.tasks[task_id].progress = min(100.0, max(0.0, progress))
        return True
    
    def get_task(self, task_id: str) -> Optional[TaskState]:
        """Get task state"""
        return self.tasks.get(task_id)
    
    def get_running_tasks(self) -> List[TaskState]:
        """Get all currently running tasks"""
        return [self.tasks[task_id] for task_id in self.running_tasks]
    
    def get_component(self, name: str) -> Optional[ComponentState]:
        """Get component state"""
        return self.components.get(name)
    
    def get_healthy_components(self) -> List[ComponentState]:
        """Get all healthy components"""
        return [comp for comp in self.components.values() if comp.is_healthy()]
    
    def get_unhealthy_components(self) -> List[ComponentState]:
        """Get all unhealthy components"""
        return [comp for comp in self.components.values() if not comp.is_healthy()]
    
    def _update_system_status(self):
        """Update overall system status based on component states"""
        if not self.components:
            self.status = SystemStatus.INITIALIZING
            return
        
        healthy_count = len(self.get_healthy_components())
        total_count = len(self.components)
        health_ratio = healthy_count / total_count if total_count > 0 else 0
        
        if health_ratio >= 0.9:
            new_status = SystemStatus.HEALTHY
        elif health_ratio >= 0.5:
            new_status = SystemStatus.DEGRADED
        else:
            new_status = SystemStatus.UNHEALTHY
        
        if new_status != self.status:
            old_status = self.status
            self.status = new_status
            self._log_event("system_status_changed", {
                "old_status": old_status.value,
                "new_status": new_status.value,
                "health_ratio": health_ratio
            })
    
    def _log_event(self, event_type: str, data: Dict[str, Any]):
        """Log system event"""
        event = {
            "timestamp": time.time(),
            "event_type": event_type,
            "data": data
        }
        
        self.event_history.append(event)
        
        # Trim event history if too long
        if len(self.event_history) > self.max_events:
            self.event_history = self.event_history[-self.max_events:]
        
        self.last_update = time.time()
        
        # Log to structured logger
        self.logger.info("system_event", event_type=event_type, **data)
    
    def update_metrics(self, metrics: Dict[str, float]):
        """Update system-level metrics"""
        self.metrics.update(metrics)
        self.metrics["uptime"] = time.time() - self.started_at
    
    def get_system_summary(self) -> Dict[str, Any]:
        """Get comprehensive system summary"""
        healthy_components = self.get_healthy_components()
        unhealthy_components = self.get_unhealthy_components()
        running_tasks = self.get_running_tasks()
        
        return {
            "status": self.status.value,
            "uptime": time.time() - self.started_at,
            "components": {
                "total": len(self.components),
                "healthy": len(healthy_components),
                "unhealthy": len(unhealthy_components),
                "health_ratio": len(healthy_components) / len(self.components) if self.components else 0
            },
            "tasks": {
                "queued": len(self.task_queue),
                "running": len(running_tasks),
                "total_completed": self.metrics["total_queries"]
            },
            "performance": {
                "success_rate": (
                    self.metrics["successful_queries"] / self.metrics["total_queries"] * 100
                    if self.metrics["total_queries"] > 0 else 0
                ),
                "avg_response_time": self.metrics["avg_response_time"],
                "queries_per_minute": self._calculate_queries_per_minute()
            },
            "last_update": self.last_update
        }
    
    def _calculate_queries_per_minute(self) -> float:
        """Calculate queries per minute based on recent activity"""
        # Simple calculation based on total queries and uptime
        uptime_minutes = (time.time() - self.started_at) / 60
        return self.metrics["total_queries"] / uptime_minutes if uptime_minutes > 0 else 0
    
    def cleanup_old_tasks(self, max_age_hours: int = 24):
        """Remove old completed tasks"""
        cutoff_time = time.time() - (max_age_hours * 3600)
        
        to_remove = []
        for task_id, task in self.tasks.items():
            if (task.status in ["completed", "failed"] and 
                task.completed_at and 
                task.completed_at < cutoff_time):
                to_remove.append(task_id)
        
        for task_id in to_remove:
            del self.tasks[task_id]
        
        if to_remove:
            self._log_event("tasks_cleaned", {"removed_count": len(to_remove)})


class StateManager:
    """
    Manages system state persistence and provides state change notifications
    """
    
    def __init__(self, state: SystemState):
        self.state = state
        self.logger = structlog.get_logger(__name__)
        self.subscribers: Dict[str, List[callable]] = {}
        
        # State persistence
        self.persistence_enabled = False
        self.last_save = time.time()
        self.save_interval = 300  # 5 minutes
        
        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self._persistence_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start background state management tasks"""
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        if self.persistence_enabled:
            self._persistence_task = asyncio.create_task(self._persistence_loop())
        
        self.logger.info("state_manager_started")
    
    async def stop(self):
        """Stop background tasks"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        if self._persistence_task:
            self._persistence_task.cancel()
            try:
                await self._persistence_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("state_manager_stopped")
    
    async def _cleanup_loop(self):
        """Background cleanup of old tasks and events"""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                self.state.cleanup_old_tasks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("cleanup_loop_error", error=str(e))
    
    async def _persistence_loop(self):
        """Background state persistence"""
        while True:
            try:
                await asyncio.sleep(self.save_interval)
                await self.save_state()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("persistence_loop_error", error=str(e))
    
    def subscribe(self, event_type: str, callback: callable):
        """Subscribe to state change events"""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        
        self.subscribers[event_type].append(callback)
    
    def notify_subscribers(self, event_type: str, data: Dict[str, Any]):
        """Notify subscribers of state changes"""
        if event_type in self.subscribers:
            for callback in self.subscribers[event_type]:
                try:
                    callback(data)
                except Exception as e:
                    self.logger.error("subscriber_notification_failed", 
                                    event_type=event_type, error=str(e))
    
    async def save_state(self, file_path: Optional[str] = None):
        """Save current state to file"""
        # This would implement state persistence
        # For now, just log that save was requested
        self.logger.info("state_save_requested", path=file_path)
        self.last_save = time.time()
    
    async def load_state(self, file_path: str):
        """Load state from file"""
        # This would implement state loading
        self.logger.info("state_load_requested", path=file_path)
    
    def get_health_report(self) -> Dict[str, Any]:
        """Generate comprehensive health report"""
        summary = self.state.get_system_summary()
        
        # Add component details
        component_details = {}
        for name, component in self.state.components.items():
            component_details[name] = {
                "type": component.type,
                "status": component.status.value,
                "healthy": component.is_healthy(),
                "error_count": component.error_count,
                "last_error": component.last_error,
                "last_activity": component.last_activity,
                "metrics": component.metrics
            }
        
        return {
            **summary,
            "component_details": component_details,
            "recent_events": self.state.event_history[-10:],  # Last 10 events
            "system_configuration": {
                "features_enabled": sum(1 for v in self.state.feature_flags.values() if v),
                "total_features": len(self.state.feature_flags)
            }
        }