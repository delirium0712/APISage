"""
Backend registry and deployment environment configuration
"""

from enum import Enum
from typing import Dict, Any, Optional


class DeploymentEnvironment(Enum):
    """Deployment environment types"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class BackendRegistry:
    """Simple backend registry for configuration"""
    
    def __init__(self):
        self.environment = DeploymentEnvironment.DEVELOPMENT
        self.backends: Dict[str, Any] = {}
    
    def set_environment(self, environment: DeploymentEnvironment):
        """Set the deployment environment"""
        self.environment = environment
    
    def register_backend(self, name: str, config: Dict[str, Any]):
        """Register a backend configuration"""
        self.backends[name] = config
    
    def get_backend(self, name: str) -> Optional[Dict[str, Any]]:
        """Get backend configuration by name"""
        return self.backends.get(name)
