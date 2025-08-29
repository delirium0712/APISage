"""
REST API module for the RAG system
"""

from .models import *
from .routes import create_api_router

__all__ = ["create_api_router"]