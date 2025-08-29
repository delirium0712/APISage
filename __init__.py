"""
APISage - Enterprise RAG Documentation Assistant

A production-ready, multi-agent RAG system with intelligent document processing,
auto-code generation, and comprehensive evaluation frameworks.
"""

__version__ = "0.1.0"
__author__ = "APISage Team"
__description__ = "Enterprise RAG Documentation Assistant"

# Import main components for easy access
from .sdk import RAGSystem, PresetConfigs
from .core.orchestrator import RAGOrchestrator, OrchestrationConfig

__all__ = [
    "RAGSystem",
    "PresetConfigs", 
    "RAGOrchestrator",
    "OrchestrationConfig",
]

