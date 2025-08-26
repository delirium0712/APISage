"""
Configuration loader for the RAG system with support for multiple sources
"""

import os
import json
import yaml
from typing import Dict, Any, Optional, Union, List
from pathlib import Path
from dataclasses import dataclass, asdict
import structlog

from .settings import SystemConfig, AgentConfig
from .backends import BackendRegistry, DeploymentEnvironment


@dataclass
class ConfigSource:
    """Configuration source information"""
    type: str  # "file", "env", "dict", "default"
    location: str  # file path, "environment", etc.
    priority: int = 1  # Higher priority overrides lower
    loaded: bool = False
    data: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.data is None:
            self.data = {}


class ConfigurationError(Exception):
    """Configuration related errors"""
    pass


class ConfigLoader:
    """
    Loads configuration from multiple sources with priority-based merging:
    1. Default configuration (lowest priority)
    2. Configuration files (YAML/JSON)
    3. Environment variables (highest priority)
    """
    
    def __init__(self):
        self.logger = structlog.get_logger(__name__)
        self.config_sources: List[ConfigSource] = []
        self.merged_config: Dict[str, Any] = {}
        self.system_config: Optional[SystemConfig] = None
        self.backend_registry: Optional[BackendRegistry] = None
        
        # Configuration file search paths
        self.config_search_paths = [
            Path.cwd(),
            Path.cwd() / "config",
            Path.home() / ".rag-system",
            Path("/etc/rag-system")
        ]
        
        # Configuration file names to look for
        self.config_filenames = [
            "rag-config.yaml",
            "rag-config.yml",
            "rag-config.json",
            "config.yaml",
            "config.yml",
            "config.json"
        ]
    
    def load_configuration(self, 
                         config_file: Optional[str] = None,
                         environment: Optional[str] = None) -> SystemConfig:
        """
        Load complete system configuration from all sources
        
        Args:
            config_file: Specific config file path (optional)
            environment: Deployment environment (dev/staging/prod)
            
        Returns:
            SystemConfig object with merged configuration
        """
        self.logger.info("loading_system_configuration", config_file=config_file, env=environment)
        
        # 1. Load default configuration
        self._load_default_config()
        
        # 2. Load configuration files
        if config_file:
            self._load_config_file(config_file)
        else:
            self._auto_discover_config_files()
        
        # 3. Load environment variables
        self._load_environment_config()
        
        # 4. Merge all configurations
        self._merge_configurations()
        
        # 5. Create system config
        self.system_config = self._create_system_config()
        
        # 6. Configure backends
        self.backend_registry = BackendRegistry()
        if environment:
            self.backend_registry.set_environment(DeploymentEnvironment(environment))
        
        self.logger.info(
            "configuration_loaded",
            sources=len(self.config_sources),
            environment=environment or "development"
        )
        
        return self.system_config
    
    def _load_default_config(self):
        """Load default configuration"""
        default_config = {
            "system": {
                "name": "RAG Documentation Assistant",
                "version": "1.0.0",
                "environment": "development",
                "debug": True,
                "log_level": "INFO"
            },
            "agents": {
                "document_processor": {
                    "enabled": True,
                    "max_concurrent": 5,
                    "timeout": 30
                },
                "api_analyzer": {
                    "enabled": True,
                    "max_endpoints": 100
                },
                "evaluator": {
                    "enabled": True,
                    "metrics_enabled": True
                },
                "code_generator": {
                    "enabled": True,
                    "supported_languages": ["python", "javascript", "typescript"]
                },
                "web_scraper": {
                    "enabled": True,
                    "use_javascript": False,
                    "follow_links": True,
                    "max_depth": 2,
                    "delay_between_requests": 1.0
                }
            },
            "vector_stores": {
                "default": "qdrant",
                "qdrant": {
                    "host": "localhost",
                    "port": 6333,
                    "collection_name": "rag_documents",
                    "embedding_dim": 384,
                    "distance_metric": "cosine"
                },
                "chroma": {
                    "host": "localhost",
                    "port": 8000,
                    "collection_name": "rag_documents"
                }
            },
            "llm_providers": {
                "default": "ollama",
                "ollama": {
                    "base_url": "http://localhost:11434",
                    "model_name": "llama3:8b",
                    "temperature": 0.7,
                    "timeout": 30
                },
                "openai": {
                    "model_name": "gpt-3.5-turbo",
                    "temperature": 0.7,
                    "max_tokens": 2000
                }
            },
            "search": {
                "hybrid": {
                    "enabled": True,
                    "vector_weight": 0.6,
                    "lexical_weight": 0.4,
                    "rerank_top_k": 15,
                    "final_top_k": 5
                },
                "reranking": {
                    "enabled": True,
                    "method": "configurable",
                    "models": ["semantic_default", "llm_default"]
                }
            },
            "caching": {
                "enabled": False,
                "redis": {
                    "host": "localhost",
                    "port": 6379,
                    "db": 0,
                    "ttl": 3600
                }
            },
            "api": {
                "enabled": False,
                "host": "localhost",
                "port": 8000,
                "cors_enabled": True,
                "rate_limiting": {
                    "enabled": False,
                    "requests_per_minute": 60
                }
            },
            "monitoring": {
                "enabled": False,
                "prometheus": {
                    "enabled": False,
                    "port": 9090
                },
                "logging": {
                    "level": "INFO",
                    "format": "json",
                    "file": None
                }
            }
        }
        
        source = ConfigSource(
            type="default",
            location="built-in",
            priority=1,
            loaded=True,
            data=default_config
        )
        
        self.config_sources.append(source)
        self.logger.info("default_config_loaded")
    
    def _auto_discover_config_files(self):
        """Auto-discover configuration files in search paths"""
        for search_path in self.config_search_paths:
            if not search_path.exists():
                continue
            
            for filename in self.config_filenames:
                config_file = search_path / filename
                if config_file.is_file():
                    self._load_config_file(str(config_file))
                    return  # Load only the first found config file
    
    def _load_config_file(self, config_file_path: str):
        """Load configuration from a file"""
        config_path = Path(config_file_path)
        
        if not config_path.exists():
            self.logger.warning("config_file_not_found", path=config_file_path)
            return
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                if config_path.suffix.lower() in ['.yaml', '.yml']:
                    data = yaml.safe_load(f)
                elif config_path.suffix.lower() == '.json':
                    data = json.load(f)
                else:
                    raise ConfigurationError(f"Unsupported config file format: {config_path.suffix}")
            
            source = ConfigSource(
                type="file",
                location=str(config_path),
                priority=5,
                loaded=True,
                data=data or {}
            )
            
            self.config_sources.append(source)
            self.logger.info("config_file_loaded", path=config_file_path, keys=len(data) if data else 0)
            
        except Exception as e:
            self.logger.error("config_file_load_failed", path=config_file_path, error=str(e))
            raise ConfigurationError(f"Failed to load config file {config_file_path}: {e}")
    
    def _load_environment_config(self):
        """Load configuration from environment variables"""
        env_config = {}
        
        # System configuration
        system_env = {}
        if os.getenv("RAG_ENVIRONMENT"):
            system_env["environment"] = os.getenv("RAG_ENVIRONMENT")
        if os.getenv("RAG_DEBUG"):
            system_env["debug"] = os.getenv("RAG_DEBUG").lower() in ("true", "1", "yes")
        if os.getenv("RAG_LOG_LEVEL"):
            system_env["log_level"] = os.getenv("RAG_LOG_LEVEL")
        
        if system_env:
            env_config["system"] = system_env
        
        # Vector store configuration
        vector_stores = {}
        if os.getenv("QDRANT_HOST"):
            vector_stores["qdrant"] = {
                "host": os.getenv("QDRANT_HOST"),
                "port": int(os.getenv("QDRANT_PORT", "6333"))
            }
            if os.getenv("QDRANT_API_KEY"):
                vector_stores["qdrant"]["api_key"] = os.getenv("QDRANT_API_KEY")
        
        if os.getenv("CHROMA_HOST"):
            vector_stores["chroma"] = {
                "host": os.getenv("CHROMA_HOST"),
                "port": int(os.getenv("CHROMA_PORT", "8000"))
            }
        
        if vector_stores:
            env_config["vector_stores"] = vector_stores
        
        # LLM provider configuration
        llm_providers = {}
        if os.getenv("OLLAMA_HOST"):
            llm_providers["ollama"] = {
                "base_url": os.getenv("OLLAMA_HOST"),
                "model_name": os.getenv("OLLAMA_MODEL", "llama3:8b")
            }
        
        if os.getenv("OPENAI_API_KEY"):
            llm_providers["openai"] = {
                "api_key": os.getenv("OPENAI_API_KEY"),
                "model_name": os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
            }
        
        if os.getenv("ANTHROPIC_API_KEY"):
            llm_providers["anthropic"] = {
                "api_key": os.getenv("ANTHROPIC_API_KEY"),
                "model_name": os.getenv("ANTHROPIC_MODEL", "claude-3-sonnet-20240229")
            }
        
        if llm_providers:
            env_config["llm_providers"] = llm_providers
        
        # Cache configuration
        if os.getenv("REDIS_HOST"):
            env_config["caching"] = {
                "enabled": True,
                "redis": {
                    "host": os.getenv("REDIS_HOST"),
                    "port": int(os.getenv("REDIS_PORT", "6379")),
                    "db": int(os.getenv("REDIS_DB", "0"))
                }
            }
            if os.getenv("REDIS_PASSWORD"):
                env_config["caching"]["redis"]["password"] = os.getenv("REDIS_PASSWORD")
        
        # API configuration
        if os.getenv("RAG_API_HOST"):
            env_config["api"] = {
                "enabled": True,
                "host": os.getenv("RAG_API_HOST"),
                "port": int(os.getenv("RAG_API_PORT", "8000"))
            }
        
        if env_config:
            source = ConfigSource(
                type="env",
                location="environment",
                priority=10,  # Highest priority
                loaded=True,
                data=env_config
            )
            
            self.config_sources.append(source)
            self.logger.info("environment_config_loaded", keys=len(env_config))
    
    def _merge_configurations(self):
        """Merge all configuration sources by priority"""
        self.merged_config = {}
        
        # Sort sources by priority (lowest first)
        sorted_sources = sorted(self.config_sources, key=lambda s: s.priority)
        
        for source in sorted_sources:
            if source.loaded and source.data:
                self.merged_config = self._deep_merge(self.merged_config, source.data)
        
        self.logger.info("configurations_merged", final_keys=len(self.merged_config))
    
    def _deep_merge(self, base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries"""
        result = base.copy()
        
        for key, value in update.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _create_system_config(self) -> SystemConfig:
        """Create SystemConfig object from merged configuration"""
        system_data = self.merged_config.get("system", {})
        
        config = SystemConfig()
        config.config_data = self.merged_config
        return config
    
    def get_agent_config(self, agent_name: str) -> AgentConfig:
        """Get configuration for a specific agent"""
        agents_config = self.merged_config.get("agents", {})
        agent_config = agents_config.get(agent_name, {})
        
        return AgentConfig(
            name=agent_name,
            enabled=agent_config.get("enabled", True),
            config_data=agent_config
        )
    
    def get_section_config(self, section_name: str) -> Dict[str, Any]:
        """Get configuration for a specific section"""
        return self.merged_config.get(section_name, {})
    
    def get_config_value(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation
        
        Args:
            key_path: Dot-separated path (e.g., "vector_stores.qdrant.host")
            default: Default value if not found
            
        Returns:
            Configuration value
        """
        keys = key_path.split('.')
        value = self.merged_config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def validate_configuration(self) -> Dict[str, List[str]]:
        """Validate the merged configuration"""
        issues = {
            "errors": [],
            "warnings": [],
            "info": []
        }
        
        # Check required sections
        required_sections = ["system", "vector_stores", "llm_providers"]
        for section in required_sections:
            if section not in self.merged_config:
                issues["errors"].append(f"Missing required configuration section: {section}")
        
        # Validate vector store configuration
        vector_stores = self.merged_config.get("vector_stores", {})
        default_store = vector_stores.get("default")
        if default_store and default_store not in vector_stores:
            issues["errors"].append(f"Default vector store '{default_store}' is not configured")
        
        # Validate LLM provider configuration
        llm_providers = self.merged_config.get("llm_providers", {})
        default_llm = llm_providers.get("default")
        if default_llm and default_llm not in llm_providers:
            issues["errors"].append(f"Default LLM provider '{default_llm}' is not configured")
        
        # Check for API keys where needed
        openai_config = llm_providers.get("openai", {})
        if openai_config and not openai_config.get("api_key"):
            issues["warnings"].append("OpenAI provider configured but no API key provided")
        
        # Performance recommendations
        if not self.merged_config.get("caching", {}).get("enabled", False):
            issues["info"].append("Consider enabling caching for better performance")
        
        return issues
    
    def export_config(self, format: str = "yaml") -> str:
        """Export merged configuration in specified format"""
        if format.lower() == "json":
            return json.dumps(self.merged_config, indent=2)
        elif format.lower() in ["yaml", "yml"]:
            return yaml.dump(self.merged_config, default_flow_style=False)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def save_config(self, file_path: str, format: str = "yaml"):
        """Save current configuration to file"""
        config_str = self.export_config(format)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(config_str)
        
        self.logger.info("config_saved", path=file_path, format=format)
    
    def reload_configuration(self):
        """Reload configuration from all sources"""
        self.config_sources.clear()
        self.merged_config.clear()
        
        # Reload with same parameters
        return self.load_configuration()


# Utility functions
def load_config(config_file: Optional[str] = None, 
               environment: Optional[str] = None) -> SystemConfig:
    """Convenience function to load configuration"""
    loader = ConfigLoader()
    return loader.load_configuration(config_file, environment)


def create_sample_config() -> str:
    """Create a sample configuration file content"""
    sample_config = {
        "system": {
            "name": "My RAG System",
            "environment": "production",
            "debug": False,
            "log_level": "INFO"
        },
        "vector_stores": {
            "default": "qdrant",
            "qdrant": {
                "host": "localhost",
                "port": 6333,
                "collection_name": "my_documents"
            }
        },
        "llm_providers": {
            "default": "ollama",
            "ollama": {
                "base_url": "http://localhost:11434",
                "model_name": "llama3:8b"
            },
            "openai": {
                "api_key": "${OPENAI_API_KEY}",
                "model_name": "gpt-4"
            }
        },
        "search": {
            "hybrid": {
                "vector_weight": 0.7,
                "lexical_weight": 0.3
            }
        },
        "agents": {
            "document_processor": {
                "enabled": True,
                "max_concurrent": 10
            },
            "api_analyzer": {
                "enabled": True
            }
        }
    }
    
    return yaml.dump(sample_config, default_flow_style=False)