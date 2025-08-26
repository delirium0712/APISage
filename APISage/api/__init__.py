"""
REST API module for the RAG system
"""

from .models import *
from .routes import create_app

__all__ = ["create_app"]