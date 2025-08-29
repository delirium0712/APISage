"""
Lazy Dependency Manager for API Agent Framework
Only installs dependencies when they're actually needed
"""

import importlib
import subprocess
import sys
from typing import Dict, Any, Optional, List
import structlog

logger = structlog.get_logger(__name__)


class LazyDependencyManager:
    """
    Manages optional dependencies with lazy loading.
    Only installs packages when they're actually needed.
    """
    
    def __init__(self):
        self.installed_packages: Dict[str, bool] = {}
        self.required_packages: Dict[str, List[str]] = {
            "qdrant": ["qdrant-client"],
            "chroma": ["chromadb"],
            "postgres": ["asyncpg"],
            "milvus": ["pymilvus"],
            "pinecone": ["pinecone-client"],
            "confluence": ["atlassian-python-api"],
            "notion": ["notion-client"],
            "github": ["PyGithub"],
            "slack": ["slack-sdk"],
            "google_drive": ["google-auth", "google-auth-oauthlib", "google-api-python-client"],
            "pdf": ["pypdf2"],
            "excel": ["openpyxl"],
            "image": ["pillow"],
        }
    
    def check_package_available(self, package_name: str) -> bool:
        """Check if a package is available without importing it"""
        try:
            importlib.import_module(package_name)
            return True
        except ImportError:
            return False
    
    def install_package(self, package_name: str) -> bool:
        """Install a package using pip"""
        try:
            logger.info("installing_package", package=package_name)
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", package_name
            ], capture_output=True)
            self.installed_packages[package_name] = True
            logger.info("package_installed", package=package_name)
            return True
        except subprocess.CalledProcessError as e:
            logger.error("package_installation_failed", 
                        package=package_name, error=str(e))
            return False
    
    def get_package(self, package_name: str, auto_install: bool = True) -> Optional[Any]:
        """
        Get a package, installing it if needed and auto_install is True
        
        Args:
            package_name: Name of the package to import
            auto_install: Whether to automatically install if missing
            
        Returns:
            The imported module or None if failed
        """
        try:
            # Try to import directly
            module = importlib.import_module(package_name)
            return module
        except ImportError:
            if not auto_install:
                logger.warning("package_not_available", package=package_name)
                return None
            
            # Try to install the package
            if self.install_package(package_name):
                try:
                    module = importlib.import_module(package_name)
                    return module
                except ImportError:
                    logger.error("package_import_failed_after_install", package=package_name)
                    return None
            else:
                return None
    
    def get_feature_dependencies(self, feature_name: str) -> Dict[str, Any]:
        """
        Get all dependencies for a specific feature
        
        Args:
            feature_name: Name of the feature (e.g., 'qdrant', 'chroma')
            
        Returns:
            Dictionary of package names to modules
        """
        if feature_name not in self.required_packages:
            logger.warning("unknown_feature", feature_name=feature_name)
            return {}
        
        dependencies = {}
        for package in self.required_packages[feature_name]:
            module = self.get_package(package)
            if module:
                dependencies[package] = module
            else:
                logger.error("feature_dependency_missing", 
                           feature=feature_name, package=package)
        
        return dependencies
    
    def is_feature_available(self, feature_name: str) -> bool:
        """Check if a feature is available (all dependencies satisfied)"""
        if feature_name not in self.required_packages:
            return False
        
        for package in self.required_packages[feature_name]:
            if not self.check_package_available(package):
                return False
        return True
    
    def list_available_features(self) -> List[str]:
        """List all features that are currently available"""
        return [
            feature for feature in self.required_packages.keys()
            if self.is_feature_available(feature)
        ]
    
    def list_installed_packages(self) -> List[str]:
        """List all packages that were installed by this manager"""
        return list(self.installed_packages.keys())


# Global instance
dependency_manager = LazyDependencyManager()


def lazy_import(package_name: str, auto_install: bool = True):
    """
    Decorator for lazy importing packages
    
    Usage:
        @lazy_import("qdrant-client")
        def use_qdrant():
            qdrant = importlib.import_module("qdrant_client")
            # ... rest of function
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Check if package is available
            if not dependency_manager.check_package_available(package_name):
                if auto_install:
                    dependency_manager.install_package(package_name)
                else:
                    raise ImportError(f"Package {package_name} is required but not available")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def require_feature(feature_name: str):
    """
    Decorator to require a specific feature
    
    Usage:
        @require_feature("qdrant")
        def qdrant_function():
            # This function will only work if qdrant dependencies are available
            pass
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            if not dependency_manager.is_feature_available(feature_name):
                # Try to install dependencies
                dependencies = dependency_manager.get_feature_dependencies(feature_name)
                if not dependencies:
                    raise ImportError(f"Feature {feature_name} is not available and dependencies could not be installed")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator
