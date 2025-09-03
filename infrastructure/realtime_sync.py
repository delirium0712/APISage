#!/usr/bin/env python3
"""
Real-time API Specification Synchronization System
Provides live updates from Git repositories, file watchers, and webhooks
"""

import asyncio
import json
import os
import hashlib
import time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from pathlib import Path
import structlog
import aiofiles
import websockets
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import requests
import yaml

logger = structlog.get_logger(__name__)


@dataclass
class SpecChange:
    """Represents a change to an API specification"""
    spec_id: str
    change_type: str  # created, modified, deleted
    file_path: str
    content: Optional[Dict[str, Any]]
    hash: str
    timestamp: float
    source: str  # git, file_watcher, webhook, manual
    author: Optional[str] = None
    commit_message: Optional[str] = None


@dataclass
class SyncConfig:
    """Configuration for real-time synchronization"""
    spec_id: str
    source_type: str  # git, file, webhook
    source_path: str  # Git URL, file path, webhook URL
    polling_interval: int = 30  # seconds
    enabled: bool = True
    filters: List[str] = None  # File patterns to watch
    webhook_secret: Optional[str] = None
    git_branch: str = "main"


class FileWatcher(FileSystemEventHandler):
    """Watches local files for changes"""
    
    def __init__(self, callback: Callable[[str, str], None]):
        super().__init__()
        self.callback = callback
        self.logger = logger.bind(component="file_watcher")
    
    def on_modified(self, event):
        if not event.is_directory and self._is_spec_file(event.src_path):
            self.logger.info("File modified", path=event.src_path)
            self.callback(event.src_path, "modified")
    
    def on_created(self, event):
        if not event.is_directory and self._is_spec_file(event.src_path):
            self.logger.info("File created", path=event.src_path)
            self.callback(event.src_path, "created")
    
    def on_deleted(self, event):
        if not event.is_directory and self._is_spec_file(event.src_path):
            self.logger.info("File deleted", path=event.src_path)
            self.callback(event.src_path, "deleted")
    
    def _is_spec_file(self, file_path: str) -> bool:
        """Check if file is an API specification"""
        file_path = file_path.lower()
        return (file_path.endswith(('.json', '.yaml', '.yml')) and 
                ('openapi' in file_path or 'swagger' in file_path or 'api' in file_path))


class GitMonitor:
    """Monitors Git repositories for API spec changes"""
    
    def __init__(self, repo_path: str, branch: str = "main"):
        self.repo_path = repo_path
        self.branch = branch
        self.last_commit = None
        self.logger = logger.bind(component="git_monitor", repo=repo_path)
    
    async def check_for_updates(self) -> List[SpecChange]:
        """Check for new commits affecting API specs"""
        try:
            # Get latest commit hash
            current_commit = await self._get_latest_commit()
            
            if current_commit != self.last_commit:
                self.logger.info("New commit detected", 
                                commit=current_commit, 
                                previous=self.last_commit)
                
                # Get changed files
                changes = await self._get_spec_changes(self.last_commit, current_commit)
                self.last_commit = current_commit
                return changes
            
            return []
            
        except Exception as e:
            self.logger.error("Git check failed", error=str(e))
            return []
    
    async def _get_latest_commit(self) -> str:
        """Get latest commit hash"""
        process = await asyncio.create_subprocess_exec(
            'git', 'rev-parse', f'origin/{self.branch}',
            cwd=self.repo_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            return stdout.decode().strip()
        else:
            raise Exception(f"Git command failed: {stderr.decode()}")
    
    async def _get_spec_changes(self, old_commit: str, new_commit: str) -> List[SpecChange]:
        """Get API spec changes between commits"""
        changes = []
        
        # Get list of changed files
        process = await asyncio.create_subprocess_exec(
            'git', 'diff', '--name-status', f'{old_commit}..{new_commit}',
            cwd=self.repo_path,
            stdout=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            return changes
        
        # Parse changed files
        for line in stdout.decode().split('\n'):
            if not line.strip():
                continue
                
            parts = line.split('\t', 1)
            if len(parts) != 2:
                continue
                
            status, file_path = parts
            full_path = os.path.join(self.repo_path, file_path)
            
            # Only process API spec files
            if not self._is_spec_file(file_path):
                continue
            
            change_type = {
                'A': 'created',
                'M': 'modified', 
                'D': 'deleted'
            }.get(status, 'modified')
            
            # Load file content (except for deletions)
            content = None
            file_hash = ""
            if change_type != 'deleted' and os.path.exists(full_path):
                content = await self._load_spec_file(full_path)
                file_hash = self._calculate_hash(str(content))
            
            change = SpecChange(
                spec_id=self._generate_spec_id(file_path),
                change_type=change_type,
                file_path=file_path,
                content=content,
                hash=file_hash,
                timestamp=time.time(),
                source="git",
                commit_message=await self._get_commit_message(new_commit)
            )
            
            changes.append(change)
        
        return changes
    
    def _is_spec_file(self, file_path: str) -> bool:
        """Check if file is likely an API specification"""
        file_path = file_path.lower()
        return (file_path.endswith(('.json', '.yaml', '.yml')) and 
                ('openapi' in file_path or 'swagger' in file_path or 'api' in file_path))
    
    async def _load_spec_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Load and parse API specification file"""
        try:
            async with aiofiles.open(file_path, 'r') as f:
                content = await f.read()
            
            if file_path.endswith('.json'):
                return json.loads(content)
            else:
                return yaml.safe_load(content)
                
        except Exception as e:
            self.logger.error("Failed to load spec file", path=file_path, error=str(e))
            return None
    
    def _calculate_hash(self, content: str) -> str:
        """Calculate content hash for change detection"""
        return hashlib.sha256(content.encode()).hexdigest()
    
    def _generate_spec_id(self, file_path: str) -> str:
        """Generate unique spec ID from file path"""
        return hashlib.md5(file_path.encode()).hexdigest()
    
    async def _get_commit_message(self, commit_hash: str) -> str:
        """Get commit message for a commit"""
        try:
            process = await asyncio.create_subprocess_exec(
                'git', 'log', '-1', '--pretty=%B', commit_hash,
                cwd=self.repo_path,
                stdout=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            return stdout.decode().strip() if process.returncode == 0 else ""
        except:
            return ""


class RealtimeSync:
    """Main real-time synchronization orchestrator"""
    
    def __init__(self):
        self.configs: Dict[str, SyncConfig] = {}
        self.watchers: Dict[str, Any] = {}
        self.git_monitors: Dict[str, GitMonitor] = {}
        self.change_callbacks: List[Callable[[SpecChange], None]] = []
        self.websocket_clients: List[websockets.WebSocketServerProtocol] = []
        self.logger = logger.bind(component="realtime_sync")
        self.running = False
    
    def add_sync_config(self, config: SyncConfig):
        """Add a new synchronization configuration"""
        self.configs[config.spec_id] = config
        self.logger.info("Added sync config", spec_id=config.spec_id, source=config.source_type)
        
        # Initialize appropriate monitor
        if config.source_type == "git":
            self.git_monitors[config.spec_id] = GitMonitor(config.source_path, config.git_branch)
        elif config.source_type == "file":
            self._setup_file_watcher(config)
    
    def _setup_file_watcher(self, config: SyncConfig):
        """Setup file system watcher for local files"""
        def on_file_change(file_path: str, change_type: str):
            asyncio.create_task(self._handle_file_change(config.spec_id, file_path, change_type))
        
        watcher = FileWatcher(on_file_change)
        observer = Observer()
        observer.schedule(watcher, config.source_path, recursive=True)
        observer.start()
        
        self.watchers[config.spec_id] = observer
    
    async def _handle_file_change(self, spec_id: str, file_path: str, change_type: str):
        """Handle file system changes"""
        try:
            content = None
            file_hash = ""
            
            if change_type != "deleted" and os.path.exists(file_path):
                # Load file content
                async with aiofiles.open(file_path, 'r') as f:
                    file_content = await f.read()
                
                if file_path.endswith('.json'):
                    content = json.loads(file_content)
                else:
                    content = yaml.safe_load(file_content)
                
                file_hash = hashlib.sha256(file_content.encode()).hexdigest()
            
            change = SpecChange(
                spec_id=spec_id,
                change_type=change_type,
                file_path=file_path,
                content=content,
                hash=file_hash,
                timestamp=time.time(),
                source="file_watcher"
            )
            
            await self._broadcast_change(change)
            
        except Exception as e:
            self.logger.error("Failed to handle file change", error=str(e), path=file_path)
    
    async def start_monitoring(self):
        """Start all monitoring processes"""
        if self.running:
            return
        
        self.running = True
        self.logger.info("Starting real-time monitoring")
        
        # Start monitoring tasks
        tasks = []
        
        # Git monitoring
        for spec_id, monitor in self.git_monitors.items():
            config = self.configs[spec_id]
            if config.enabled:
                tasks.append(self._monitor_git_repo(spec_id, monitor, config.polling_interval))
        
        if tasks:
            await asyncio.gather(*tasks)
    
    async def _monitor_git_repo(self, spec_id: str, monitor: GitMonitor, interval: int):
        """Monitor a Git repository for changes"""
        while self.running:
            try:
                changes = await monitor.check_for_updates()
                for change in changes:
                    await self._broadcast_change(change)
                    
                await asyncio.sleep(interval)
                
            except Exception as e:
                self.logger.error("Git monitoring error", spec_id=spec_id, error=str(e))
                await asyncio.sleep(interval)
    
    async def _broadcast_change(self, change: SpecChange):
        """Broadcast change to all subscribers"""
        self.logger.info("Broadcasting change", 
                        spec_id=change.spec_id, 
                        change_type=change.change_type,
                        source=change.source)
        
        # Call registered callbacks
        for callback in self.change_callbacks:
            try:
                await callback(change) if asyncio.iscoroutinefunction(callback) else callback(change)
            except Exception as e:
                self.logger.error("Callback failed", error=str(e))
        
        # Broadcast to WebSocket clients
        if self.websocket_clients:
            message = json.dumps({
                "type": "spec_change",
                "data": asdict(change)
            })
            
            # Remove disconnected clients
            active_clients = []
            for client in self.websocket_clients:
                try:
                    await client.send(message)
                    active_clients.append(client)
                except websockets.exceptions.ConnectionClosed:
                    pass
            
            self.websocket_clients = active_clients
    
    def add_change_callback(self, callback: Callable[[SpecChange], None]):
        """Add callback for spec changes"""
        self.change_callbacks.append(callback)
    
    async def handle_webhook(self, payload: Dict[str, Any], spec_id: str) -> bool:
        """Handle webhook payload from Git providers"""
        try:
            # GitHub webhook format
            if 'commits' in payload and 'repository' in payload:
                repo_name = payload['repository']['name']
                
                for commit in payload['commits']:
                    # Check if any API specs were modified
                    modified_files = commit.get('modified', []) + commit.get('added', [])
                    
                    for file_path in modified_files:
                        if self._is_spec_file(file_path):
                            # Create change event
                            change = SpecChange(
                                spec_id=spec_id,
                                change_type="modified",
                                file_path=file_path,
                                content=None,  # Will be fetched later
                                hash="",
                                timestamp=time.time(),
                                source="webhook",
                                author=commit.get('author', {}).get('name'),
                                commit_message=commit.get('message', '')
                            )
                            
                            await self._broadcast_change(change)
                
                return True
                
        except Exception as e:
            self.logger.error("Webhook handling failed", error=str(e))
        
        return False
    
    def _is_spec_file(self, file_path: str) -> bool:
        """Check if file is an API specification"""
        file_path = file_path.lower()
        return (file_path.endswith(('.json', '.yaml', '.yml')) and 
                ('openapi' in file_path or 'swagger' in file_path or 'api' in file_path))
    
    async def websocket_handler(self, websocket, path):
        """Handle WebSocket connections for real-time updates"""
        self.logger.info("New WebSocket client connected")
        self.websocket_clients.append(websocket)
        
        try:
            await websocket.wait_closed()
        finally:
            if websocket in self.websocket_clients:
                self.websocket_clients.remove(websocket)
            self.logger.info("WebSocket client disconnected")
    
    def stop_monitoring(self):
        """Stop all monitoring processes"""
        self.running = False
        
        # Stop file watchers
        for observer in self.watchers.values():
            observer.stop()
            observer.join()
        
        self.watchers.clear()
        self.logger.info("Real-time monitoring stopped")


# Global instance
realtime_sync = RealtimeSync()

# Convenience functions
async def setup_git_sync(spec_id: str, repo_path: str, branch: str = "main", polling_interval: int = 30):
    """Setup Git repository synchronization"""
    config = SyncConfig(
        spec_id=spec_id,
        source_type="git",
        source_path=repo_path,
        polling_interval=polling_interval,
        git_branch=branch
    )
    realtime_sync.add_sync_config(config)

async def setup_file_sync(spec_id: str, directory_path: str):
    """Setup file system synchronization"""
    config = SyncConfig(
        spec_id=spec_id,
        source_type="file", 
        source_path=directory_path
    )
    realtime_sync.add_sync_config(config)

def add_change_listener(callback: Callable[[SpecChange], None]):
    """Add listener for specification changes"""
    realtime_sync.add_change_callback(callback)