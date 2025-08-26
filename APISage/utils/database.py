"""
Database utilities for storing system data, metrics, and metadata
"""

import asyncio
import json
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone
import structlog

try:
    import asyncpg
    ASYNCPG_AVAILABLE = True
except ImportError:
    ASYNCPG_AVAILABLE = False


class DatabaseManager:
    """
    Manages PostgreSQL database connections and operations for:
    - Document metadata storage
    - System metrics and analytics
    - User preferences and settings
    - Task history and audit logs
    """
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.logger = structlog.get_logger(__name__)
        self.pool: Optional[asyncpg.Pool] = None
        self._is_initialized = False
        
        if not ASYNCPG_AVAILABLE:
            self.logger.warning("asyncpg_not_available", 
                              message="Database functionality disabled - install asyncpg to enable")
    
    async def initialize(self):
        """Initialize database connection pool and create tables"""
        if not ASYNCPG_AVAILABLE:
            return
        
        try:
            self.pool = await asyncpg.create_pool(
                self.connection_string,
                min_size=2,
                max_size=10,
                command_timeout=60
            )
            
            # Create tables if they don't exist
            await self._create_tables()
            
            self._is_initialized = True
            self.logger.info("database_initialized", connection_string=self.connection_string.split('@')[0] + '@***')
            
        except Exception as e:
            self.logger.error("database_initialization_failed", error=str(e))
            raise
    
    async def _create_tables(self):
        """Create necessary database tables"""
        
        tables_sql = [
            # Documents table
            """
            CREATE TABLE IF NOT EXISTS documents (
                id SERIAL PRIMARY KEY,
                document_id VARCHAR(255) UNIQUE NOT NULL,
                source_url TEXT,
                source_type VARCHAR(50),
                title TEXT,
                content_hash VARCHAR(64),
                metadata JSONB,
                processed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
            """,
            
            # Tasks table
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id SERIAL PRIMARY KEY,
                task_id VARCHAR(255) UNIQUE NOT NULL,
                task_type VARCHAR(100) NOT NULL,
                status VARCHAR(50) NOT NULL,
                progress FLOAT DEFAULT 0.0,
                input_data JSONB,
                result_data JSONB,
                error_message TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                started_at TIMESTAMP WITH TIME ZONE,
                completed_at TIMESTAMP WITH TIME ZONE
            )
            """,
            
            # System metrics table
            """
            CREATE TABLE IF NOT EXISTS system_metrics (
                id SERIAL PRIMARY KEY,
                metric_name VARCHAR(100) NOT NULL,
                metric_value FLOAT NOT NULL,
                component_name VARCHAR(100),
                metadata JSONB,
                timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
            """,
            
            # API usage analytics table
            """
            CREATE TABLE IF NOT EXISTS api_usage (
                id SERIAL PRIMARY KEY,
                endpoint VARCHAR(200) NOT NULL,
                method VARCHAR(10) NOT NULL,
                status_code INTEGER,
                response_time FLOAT,
                request_size INTEGER,
                response_size INTEGER,
                user_agent TEXT,
                ip_address INET,
                timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
            """,
            
            # User settings table
            """
            CREATE TABLE IF NOT EXISTS user_settings (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(255) NOT NULL,
                setting_key VARCHAR(100) NOT NULL,
                setting_value JSONB NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                UNIQUE(user_id, setting_key)
            )
            """,
            
            # System events table
            """
            CREATE TABLE IF NOT EXISTS system_events (
                id SERIAL PRIMARY KEY,
                event_type VARCHAR(100) NOT NULL,
                component VARCHAR(100),
                severity VARCHAR(20) DEFAULT 'info',
                message TEXT,
                event_data JSONB,
                timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
            """
        ]
        
        # Create indexes
        indexes_sql = [
            "CREATE INDEX IF NOT EXISTS idx_documents_document_id ON documents(document_id)",
            "CREATE INDEX IF NOT EXISTS idx_documents_source_type ON documents(source_type)",
            "CREATE INDEX IF NOT EXISTS idx_documents_processed_at ON documents(processed_at)",
            
            "CREATE INDEX IF NOT EXISTS idx_tasks_task_id ON tasks(task_id)",
            "CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)",
            "CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at)",
            
            "CREATE INDEX IF NOT EXISTS idx_metrics_name_timestamp ON system_metrics(metric_name, timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_metrics_component ON system_metrics(component_name)",
            
            "CREATE INDEX IF NOT EXISTS idx_api_usage_endpoint ON api_usage(endpoint)",
            "CREATE INDEX IF NOT EXISTS idx_api_usage_timestamp ON api_usage(timestamp)",
            
            "CREATE INDEX IF NOT EXISTS idx_events_type_timestamp ON system_events(event_type, timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_events_component ON system_events(component)"
        ]
        
        async with self.pool.acquire() as conn:
            # Create tables
            for table_sql in tables_sql:
                await conn.execute(table_sql)
            
            # Create indexes
            for index_sql in indexes_sql:
                await conn.execute(index_sql)
    
    async def store_document_metadata(self, 
                                    document_id: str,
                                    source_url: str,
                                    source_type: str,
                                    title: str = "",
                                    content_hash: str = "",
                                    metadata: Dict[str, Any] = None) -> int:
        """Store document metadata"""
        if not self._is_initialized:
            return 0
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO documents (document_id, source_url, source_type, title, content_hash, metadata)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (document_id) DO UPDATE SET
                    title = EXCLUDED.title,
                    content_hash = EXCLUDED.content_hash,
                    metadata = EXCLUDED.metadata,
                    updated_at = NOW()
                RETURNING id
                """,
                document_id, source_url, source_type, title, content_hash, json.dumps(metadata or {})
            )
            return row['id'] if row else 0
    
    async def get_document_metadata(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get document metadata by ID"""
        if not self._is_initialized:
            return None
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM documents WHERE document_id = $1",
                document_id
            )
            
            if row:
                return {
                    "id": row['id'],
                    "document_id": row['document_id'],
                    "source_url": row['source_url'],
                    "source_type": row['source_type'],
                    "title": row['title'],
                    "content_hash": row['content_hash'],
                    "metadata": row['metadata'],
                    "processed_at": row['processed_at'],
                    "created_at": row['created_at'],
                    "updated_at": row['updated_at']
                }
            return None
    
    async def store_task_info(self, 
                            task_id: str,
                            task_type: str,
                            status: str,
                            progress: float = 0.0,
                            input_data: Dict[str, Any] = None,
                            result_data: Dict[str, Any] = None,
                            error_message: str = None) -> None:
        """Store or update task information"""
        if not self._is_initialized:
            return
        
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO tasks (task_id, task_type, status, progress, input_data, result_data, error_message)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (task_id) DO UPDATE SET
                    status = EXCLUDED.status,
                    progress = EXCLUDED.progress,
                    result_data = EXCLUDED.result_data,
                    error_message = EXCLUDED.error_message,
                    completed_at = CASE WHEN EXCLUDED.status IN ('completed', 'failed') THEN NOW() ELSE tasks.completed_at END,
                    started_at = CASE WHEN tasks.started_at IS NULL AND EXCLUDED.status = 'running' THEN NOW() ELSE tasks.started_at END
                """,
                task_id, task_type, status, progress,
                json.dumps(input_data or {}), json.dumps(result_data or {}), error_message
            )
    
    async def get_task_history(self, 
                             task_type: Optional[str] = None,
                             status: Optional[str] = None,
                             limit: int = 100) -> List[Dict[str, Any]]:
        """Get task history with optional filtering"""
        if not self._is_initialized:
            return []
        
        query = "SELECT * FROM tasks WHERE 1=1"
        params = []
        param_count = 0
        
        if task_type:
            param_count += 1
            query += f" AND task_type = ${param_count}"
            params.append(task_type)
        
        if status:
            param_count += 1
            query += f" AND status = ${param_count}"
            params.append(status)
        
        query += f" ORDER BY created_at DESC LIMIT ${param_count + 1}"
        params.append(limit)
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            
            return [
                {
                    "task_id": row['task_id'],
                    "task_type": row['task_type'],
                    "status": row['status'],
                    "progress": row['progress'],
                    "input_data": row['input_data'],
                    "result_data": row['result_data'],
                    "error_message": row['error_message'],
                    "created_at": row['created_at'],
                    "started_at": row['started_at'],
                    "completed_at": row['completed_at']
                }
                for row in rows
            ]
    
    async def store_metric(self, 
                         metric_name: str,
                         metric_value: float,
                         component_name: str = None,
                         metadata: Dict[str, Any] = None) -> None:
        """Store a system metric"""
        if not self._is_initialized:
            return
        
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO system_metrics (metric_name, metric_value, component_name, metadata)
                VALUES ($1, $2, $3, $4)
                """,
                metric_name, metric_value, component_name, json.dumps(metadata or {})
            )
    
    async def get_metrics(self, 
                        metric_name: str,
                        component_name: Optional[str] = None,
                        hours_back: int = 24,
                        limit: int = 1000) -> List[Dict[str, Any]]:
        """Get metrics for analysis"""
        if not self._is_initialized:
            return []
        
        query = """
        SELECT * FROM system_metrics 
        WHERE metric_name = $1 
        AND timestamp > NOW() - INTERVAL '%s hours'
        """ % hours_back
        
        params = [metric_name]
        
        if component_name:
            query += " AND component_name = $2"
            params.append(component_name)
        
        query += f" ORDER BY timestamp DESC LIMIT ${len(params) + 1}"
        params.append(limit)
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            
            return [
                {
                    "metric_name": row['metric_name'],
                    "metric_value": row['metric_value'],
                    "component_name": row['component_name'],
                    "metadata": row['metadata'],
                    "timestamp": row['timestamp']
                }
                for row in rows
            ]
    
    async def log_api_usage(self, 
                          endpoint: str,
                          method: str,
                          status_code: int,
                          response_time: float,
                          request_size: int = 0,
                          response_size: int = 0,
                          user_agent: str = None,
                          ip_address: str = None) -> None:
        """Log API usage for analytics"""
        if not self._is_initialized:
            return
        
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO api_usage 
                (endpoint, method, status_code, response_time, request_size, response_size, user_agent, ip_address)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                endpoint, method, status_code, response_time, 
                request_size, response_size, user_agent, ip_address
            )
    
    async def get_api_analytics(self, hours_back: int = 24) -> Dict[str, Any]:
        """Get API usage analytics"""
        if not self._is_initialized:
            return {}
        
        async with self.pool.acquire() as conn:
            # Total requests
            total_requests = await conn.fetchval(
                "SELECT COUNT(*) FROM api_usage WHERE timestamp > NOW() - INTERVAL '%s hours'" % hours_back
            )
            
            # Average response time
            avg_response_time = await conn.fetchval(
                "SELECT AVG(response_time) FROM api_usage WHERE timestamp > NOW() - INTERVAL '%s hours'" % hours_back
            ) or 0
            
            # Top endpoints
            top_endpoints = await conn.fetch(
                """
                SELECT endpoint, COUNT(*) as request_count, AVG(response_time) as avg_response_time
                FROM api_usage 
                WHERE timestamp > NOW() - INTERVAL '%s hours'
                GROUP BY endpoint
                ORDER BY request_count DESC
                LIMIT 10
                """ % hours_back
            )
            
            # Status code distribution
            status_codes = await conn.fetch(
                """
                SELECT status_code, COUNT(*) as count
                FROM api_usage 
                WHERE timestamp > NOW() - INTERVAL '%s hours'
                GROUP BY status_code
                ORDER BY count DESC
                """ % hours_back
            )
            
            return {
                "total_requests": total_requests,
                "average_response_time": float(avg_response_time),
                "top_endpoints": [
                    {
                        "endpoint": row['endpoint'],
                        "request_count": row['request_count'],
                        "avg_response_time": float(row['avg_response_time'])
                    }
                    for row in top_endpoints
                ],
                "status_codes": [
                    {
                        "status_code": row['status_code'],
                        "count": row['count']
                    }
                    for row in status_codes
                ]
            }
    
    async def store_system_event(self, 
                               event_type: str,
                               component: str = None,
                               severity: str = "info",
                               message: str = None,
                               event_data: Dict[str, Any] = None) -> None:
        """Store system event for audit log"""
        if not self._is_initialized:
            return
        
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO system_events (event_type, component, severity, message, event_data)
                VALUES ($1, $2, $3, $4, $5)
                """,
                event_type, component, severity, message, json.dumps(event_data or {})
            )
    
    async def get_system_events(self, 
                              event_type: Optional[str] = None,
                              component: Optional[str] = None,
                              severity: Optional[str] = None,
                              hours_back: int = 24,
                              limit: int = 100) -> List[Dict[str, Any]]:
        """Get system events for monitoring"""
        if not self._is_initialized:
            return []
        
        query = "SELECT * FROM system_events WHERE timestamp > NOW() - INTERVAL '%s hours'" % hours_back
        params = []
        param_count = 0
        
        if event_type:
            param_count += 1
            query += f" AND event_type = ${param_count}"
            params.append(event_type)
        
        if component:
            param_count += 1
            query += f" AND component = ${param_count}"
            params.append(component)
        
        if severity:
            param_count += 1
            query += f" AND severity = ${param_count}"
            params.append(severity)
        
        query += f" ORDER BY timestamp DESC LIMIT ${param_count + 1}"
        params.append(limit)
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            
            return [
                {
                    "event_type": row['event_type'],
                    "component": row['component'],
                    "severity": row['severity'],
                    "message": row['message'],
                    "event_data": row['event_data'],
                    "timestamp": row['timestamp']
                }
                for row in rows
            ]
    
    async def cleanup_old_data(self, days_back: int = 30) -> Dict[str, int]:
        """Clean up old data to prevent database bloat"""
        if not self._is_initialized:
            return {}
        
        cleanup_results = {}
        
        async with self.pool.acquire() as conn:
            # Clean old tasks
            tasks_deleted = await conn.fetchval(
                "DELETE FROM tasks WHERE created_at < NOW() - INTERVAL '%s days' RETURNING COUNT(*)" % days_back
            ) or 0
            cleanup_results["tasks_deleted"] = tasks_deleted
            
            # Clean old metrics (keep longer for analysis)
            metrics_deleted = await conn.fetchval(
                "DELETE FROM system_metrics WHERE timestamp < NOW() - INTERVAL '%s days' RETURNING COUNT(*)" % (days_back * 2)
            ) or 0
            cleanup_results["metrics_deleted"] = metrics_deleted
            
            # Clean old API usage data
            api_usage_deleted = await conn.fetchval(
                "DELETE FROM api_usage WHERE timestamp < NOW() - INTERVAL '%s days' RETURNING COUNT(*)" % days_back
            ) or 0
            cleanup_results["api_usage_deleted"] = api_usage_deleted
            
            # Clean old events
            events_deleted = await conn.fetchval(
                "DELETE FROM system_events WHERE timestamp < NOW() - INTERVAL '%s days' RETURNING COUNT(*)" % days_back
            ) or 0
            cleanup_results["events_deleted"] = events_deleted
        
        self.logger.info("database_cleanup_completed", results=cleanup_results)
        return cleanup_results
    
    async def close(self):
        """Close database connections"""
        if self.pool:
            await self.pool.close()
            self._is_initialized = False
            self.logger.info("database_connections_closed")