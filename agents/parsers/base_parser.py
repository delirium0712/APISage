"""
Base parser interface for document parsing
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
import structlog

logger = structlog.get_logger()


class DocumentFormat(Enum):
    """Supported document formats"""
    OPENAPI_JSON = "openapi_json"
    OPENAPI_YAML = "openapi_yaml"
    SWAGGER_JSON = "swagger_json"
    SWAGGER_YAML = "swagger_yaml"
    MARKDOWN = "markdown"
    POSTMAN_COLLECTION = "postman_collection"
    HTML = "html"
    UNKNOWN = "unknown"


@dataclass
class ParsedDocument:
    """Parsed document container"""
    format: DocumentFormat
    title: str
    description: str
    content: str
    metadata: Dict[str, Any]
    endpoints: List[Dict[str, Any]]
    examples: List[Dict[str, Any]]
    schemas: List[Dict[str, Any]]
    chunks: List[str]


class BaseDocumentParser(ABC):
    """Abstract base class for document parsers"""
    
    def __init__(self):
        self.logger = structlog.get_logger(component=self.__class__.__name__)
    
    @abstractmethod
    def can_parse(self, content: Union[str, bytes], content_type: str = None, filename: str = None) -> bool:
        """Check if this parser can handle the given content"""
        pass
    
    @abstractmethod
    async def parse(self, content: Union[str, bytes], content_type: str = None, filename: str = None) -> ParsedDocument:
        """Parse the document and extract structured information"""
        pass
    
    def _detect_format(self, content: Union[str, bytes], content_type: str = None, filename: str = None) -> DocumentFormat:
        """Detect document format from content/metadata"""
        
        if isinstance(content, bytes):
            try:
                content = content.decode('utf-8')
            except UnicodeDecodeError:
                return DocumentFormat.UNKNOWN
        
        # Check by content type
        if content_type:
            if 'json' in content_type.lower():
                if 'openapi' in content or 'swagger' in content:
                    return DocumentFormat.OPENAPI_JSON if 'openapi' in content else DocumentFormat.SWAGGER_JSON
            elif 'yaml' in content_type.lower() or 'yml' in content_type.lower():
                if 'openapi' in content or 'swagger' in content:
                    return DocumentFormat.OPENAPI_YAML if 'openapi' in content else DocumentFormat.SWAGGER_YAML
            elif 'markdown' in content_type.lower():
                return DocumentFormat.MARKDOWN
        
        # Check by filename
        if filename:
            filename_lower = filename.lower()
            if filename_lower.endswith('.json'):
                if 'openapi' in content or 'swagger' in content:
                    return DocumentFormat.OPENAPI_JSON if 'openapi' in content else DocumentFormat.SWAGGER_JSON
                elif 'postman' in filename_lower or 'collection' in filename_lower:
                    return DocumentFormat.POSTMAN_COLLECTION
            elif filename_lower.endswith(('.yaml', '.yml')):
                if 'openapi' in content or 'swagger' in content:
                    return DocumentFormat.OPENAPI_YAML if 'openapi' in content else DocumentFormat.SWAGGER_YAML
            elif filename_lower.endswith(('.md', '.markdown')):
                return DocumentFormat.MARKDOWN
        
        # Check by content patterns
        if isinstance(content, str):
            content_lower = content.lower()
            
            # JSON-based formats
            if content.strip().startswith('{'):
                if '"openapi"' in content_lower:
                    return DocumentFormat.OPENAPI_JSON
                elif '"swagger"' in content_lower:
                    return DocumentFormat.SWAGGER_JSON
                elif '"info"' in content_lower and '"item"' in content_lower:
                    return DocumentFormat.POSTMAN_COLLECTION
            
            # YAML-based formats
            elif any(line.strip().startswith(('openapi:', 'swagger:')) for line in content.split('\n')[:10]):
                return DocumentFormat.OPENAPI_YAML if 'openapi:' in content else DocumentFormat.SWAGGER_YAML
            
            # Markdown
            elif any(line.strip().startswith('#') for line in content.split('\n')[:10]):
                return DocumentFormat.MARKDOWN
            
            # HTML
            elif '<html' in content_lower or '<!doctype html' in content_lower:
                return DocumentFormat.HTML
        
        return DocumentFormat.UNKNOWN
    
    def _chunk_content(self, content: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[str]:
        """Split content into overlapping chunks"""
        
        if len(content) <= chunk_size:
            return [content]
        
        chunks = []
        start = 0
        
        while start < len(content):
            end = start + chunk_size
            
            # Try to break at sentence boundaries
            if end < len(content):
                # Look for sentence endings within the last 100 characters
                sentence_end = content.rfind('.', start + chunk_size - 100, end)
                if sentence_end > start:
                    end = sentence_end + 1
                else:
                    # Fall back to word boundaries
                    word_end = content.rfind(' ', start + chunk_size - 50, end)
                    if word_end > start:
                        end = word_end
            
            chunks.append(content[start:end].strip())
            start = end - chunk_overlap if end < len(content) else end
        
        return chunks