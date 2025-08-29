"""
Enhanced Document Processor for Self-Hosted API Agent Framework
Supports multiple API documentation formats with quality evaluation
"""

import json
import hashlib
import os
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from enum import Enum
import structlog

from config.settings import AgentConfig, SystemConfig
from .parsers.base_parser import BaseDocumentParser
from .parsers.markdown_parser import MarkdownParser
from .parsers.openapi_parser import OpenAPIParser
from .parsers.postman_parser import PostmanParser
from .evaluation.quality_evaluator import APIDocQualityEvaluator
from infrastructure.backend_manager import BackendManager


class APIDocFormat(Enum):
    """Supported API documentation formats"""
    OPENAPI_3 = "openapi_3"
    SWAGGER_2 = "swagger_2"
    POSTMAN = "postman"
    RAML = "raml"
    API_BLUEPRINT = "api_blueprint"
    GRAPHQL = "graphql"
    ASYNCAPI = "asyncapi"
    INSOMNIA = "insomnia"
    MARKDOWN = "markdown"
    UNKNOWN = "unknown"


class DocumentProcessor:
    """Enhanced document processor for API documentation formats"""
    
    def __init__(self, config: AgentConfig, system_config: SystemConfig, 
                 backend_manager: BackendManager):
        self.config = config
        self.system_config = system_config
        self.backend_manager = backend_manager
        self.milvus = self.backend_manager.get_connection("milvus")
        self.redis = self.backend_manager.get_connection("redis")
        self.llm = self.backend_manager.llm_manager
        self.logger = structlog.get_logger(agent=config.name)
        
        # Initialize parsers based on configuration
        self.parsers: Dict[str, BaseDocumentParser] = self._initialize_parsers()
        
        # Initialize quality evaluator
        self.quality_evaluator = APIDocQualityEvaluator(self.llm) if self.llm else None
        
    def _initialize_parsers(self) -> Dict[str, BaseDocumentParser]:
        """Initialize document parsers based on system configuration"""
        parsers = {}
        
        # Get enabled formats from system config or use defaults
        enabled_formats = getattr(self.system_config, 'enabled_api_formats', [
            "markdown", "openapi_3", "swagger_2", "postman"
        ])
        
        if "markdown" in enabled_formats:
            parsers["markdown"] = MarkdownParser()
            
        if "openapi_3" in enabled_formats or "swagger_2" in enabled_formats:
            parsers["openapi"] = OpenAPIParser()
            
        if "postman" in enabled_formats:
            parsers["postman"] = PostmanParser()
            
        # Add more parsers as needed
        # parsers["raml"] = RAMLParser()
        # parsers["graphql"] = GraphQLParser()
        # parsers["asyncapi"] = AsyncAPIParser()
            
        self.logger.info("initialized_parsers", 
                        parser_count=len(parsers),
                        available_parsers=list(parsers.keys()))
        
        return parsers
    
    async def process_document(self, source: Union[str, bytes, Path], 
                             source_type: str = "auto",
                             metadata: Dict = None) -> Dict[str, Any]:
        """
        Process document from various sources and formats
        
        Args:
            source: Document source (file path, content, or API spec)
            source_type: Type of source ("file", "content", "api_spec", "auto")
            metadata: Additional metadata for the document
        """
        try:
            # Determine source type if auto
            if source_type == "auto":
                source_type = self._detect_source_type(source)
            
            # Extract content based on source type
            if source_type == "file":
                content = await self._extract_from_file(source)
            elif source_type == "content":
                content = source
            elif source_type == "api_spec":
                content = source
            else:
                raise ValueError(f"Unsupported source type: {source_type}")
            
            # Detect document format and parse
            document_format = self._detect_document_format(content)
            parsed_content = await self._parse_document(content, document_format)
            
            # Evaluate document quality if evaluator is available
            quality_report = None
            if self.quality_evaluator:
                quality_report = await self.quality_evaluator.evaluate_documentation(parsed_content)
            
            # Generate embeddings and store in Milvus
            embeddings_result = None
            if self.milvus:
                embeddings_result = await self._generate_and_store_embeddings(parsed_content)
            
            # Build knowledge graph
            knowledge_graph = await self._build_knowledge_graph(parsed_content)
            
            # Add metadata
            result = {
                "source": str(source),
                "source_type": source_type,
                "format": document_format.value if hasattr(document_format, 'value') else document_format,
                "parsed_content": parsed_content,
                "quality_report": quality_report,
                "embeddings_result": embeddings_result,
                "knowledge_graph": knowledge_graph,
                "processed_at": datetime.utcnow().isoformat(),
                "parser_used": document_format.value if hasattr(document_format, 'value') else document_format,
                "metadata": metadata or {}
            }
            
            # Cache result if Redis is available
            if self.redis and self.config.cache_ttl > 0:
                cache_key = f"doc:{hashlib.md5(str(source).encode()).hexdigest()}"
                await self.redis.setex(
                    cache_key,
                    self.config.cache_ttl,
                    json.dumps(result)
                )
            
            self.logger.info("document_processed", 
                           source=str(source),
                           format=document_format,
                           parser=document_format,
                           quality_score=quality_report.get("overall_score") if quality_report else None)
            
            return result
            
        except Exception as e:
            self.logger.error("document_processing_failed", 
                            source=str(source),
                            error=str(e))
            raise
    
    def _detect_source_type(self, source: Union[str, bytes, Path]) -> str:
        """Detect the type of source automatically"""
        if isinstance(source, Path) or (isinstance(source, str) and os.path.exists(source)):
            return "file"
        elif isinstance(source, bytes):
            return "content"
        else:
            # Check if it looks like an API spec
            if self._looks_like_api_spec(source):
                return "api_spec"
            return "content"
    
    def _looks_like_api_spec(self, content: str) -> bool:
        """Check if content looks like an API specification"""
        content_lower = content.lower()
        
        # Check for OpenAPI/Swagger
        if any(marker in content_lower for marker in ['openapi:', 'swagger:', '"swagger"']):
            return True
        
        # Check for Postman collection
        if any(marker in content_lower for marker in ['"info"', '"item"', '"request"']) and '"schema"' in content_lower:
            return True
        
        # Check for GraphQL schema
        if 'type' in content_lower and 'query' in content_lower and 'schema' in content_lower:
            return True
        
        # Check for RAML
        if content_lower.startswith('#%raml'):
            return True
        
        # Check for AsyncAPI
        if 'asyncapi:' in content_lower:
            return True
        
        return False
    
    def _detect_document_format(self, content: str) -> APIDocFormat:
        """Detect document format from content"""
        content_lower = content.lower()
        
        # Check for OpenAPI/Swagger
        if any(marker in content_lower for marker in ['openapi:', 'swagger:', '"swagger"']):
            if 'openapi:' in content_lower:
                return APIDocFormat.OPENAPI_3
            else:
                return APIDocFormat.SWAGGER_2
        
        # Check for Postman collection
        if any(marker in content_lower for marker in ['"info"', '"item"', '"request"']) and '"schema"' in content_lower:
            return APIDocFormat.POSTMAN
        
        # Check for Markdown
        if any(marker in content_lower for marker in ['# ', '## ', '### ', '**', '*', '```']):
            return APIDocFormat.MARKDOWN
        
        # Check for GraphQL
        if 'type' in content_lower and 'query' in content_lower and 'schema' in content_lower:
            return APIDocFormat.GRAPHQL
        
        # Check for RAML
        if content_lower.startswith('#%raml'):
            return APIDocFormat.RAML
        
        # Check for AsyncAPI
        if 'asyncapi:' in content_lower:
            return APIDocFormat.ASYNCAPI
        
        # Check for API Blueprint
        if content_lower.startswith('format: 1a') or 'api blueprint' in content_lower:
            return APIDocFormat.API_BLUEPRINT
        
        # Default to unknown
        return APIDocFormat.UNKNOWN
    
    async def _parse_document(self, content: str, format_type: APIDocFormat) -> Dict[str, Any]:
        """Parse document using appropriate parser"""
        if format_type in [APIDocFormat.OPENAPI_3, APIDocFormat.SWAGGER_2] and "openapi" in self.parsers:
            parser = self.parsers["openapi"]
            return await parser.parse(content)
        elif format_type == APIDocFormat.POSTMAN and "postman" in self.parsers:
            parser = self.parsers["postman"]
            return await parser.parse(content)
        elif format_type == APIDocFormat.MARKDOWN and "markdown" in self.parsers:
            parser = self.parsers["markdown"]
            return await parser.parse(content)
        else:
            # Fallback to basic text parsing
            return await self._parse_text_fallback(content, format_type)
    
    async def _parse_text_fallback(self, content: str, format_type: APIDocFormat) -> Dict[str, Any]:
        """Fallback text parser for unsupported formats"""
        return {
            "title": f"API Documentation ({format_type.value})",
            "content": content[:5000],
            "type": format_type.value,
            "endpoints": self._extract_endpoints_from_text(content),
            "format_detected": format_type.value,
            "parsing_method": "fallback_text"
        }
    
    def _extract_endpoints_from_text(self, content: str) -> List[Dict[str, str]]:
        """Extract API endpoint patterns from text content"""
        endpoints = []
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            for method in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                if method in line and ('/' in line or 'http' in line):
                    endpoints.append({
                        "method": method,
                        "path": line,
                        "raw": line
                    })
        
        return endpoints[:50]
    
    async def _extract_from_file(self, file_path: Union[str, Path]) -> str:
        """Extract content from file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # Try with different encoding
            with open(file_path, 'r', encoding='latin-1') as f:
                return f.read()
    
    async def _generate_and_store_embeddings(self, parsed_doc: Dict) -> Dict[str, Any]:
        """Generate embeddings and store in Milvus"""
        try:
            # Extract text for embedding
            text_chunks = self._create_text_chunks(parsed_doc)
            
            # Generate embeddings (this would use the LLM client)
            embeddings = []
            for chunk in text_chunks:
                # Generate embedding for each chunk
                embedding = await self._generate_embedding(chunk)
                embeddings.append(embedding)
            
            # Store in Milvus
            if self.milvus:
                await self.milvus.insert_endpoints(parsed_doc.get("endpoints", []), embeddings)
            
            return {
                "chunks_processed": len(text_chunks),
                "embeddings_generated": len(embeddings),
                "stored_in_milvus": True if self.milvus else False
            }
            
        except Exception as e:
            self.logger.error("embedding_generation_failed", error=str(e))
            return {
                "error": str(e),
                "chunks_processed": 0,
                "embeddings_generated": 0,
                "stored_in_milvus": False
            }
    
    def _create_text_chunks(self, parsed_doc: Dict) -> List[str]:
        """Create text chunks for embedding generation"""
        chunks = []
        
        # Add API title and description
        if parsed_doc.get("title"):
            chunks.append(f"API: {parsed_doc['title']}")
        
        if parsed_doc.get("description"):
            chunks.append(parsed_doc["description"])
        
        # Add endpoint information
        for endpoint in parsed_doc.get("endpoints", []):
            endpoint_text = f"{endpoint.get('method', '')} {endpoint.get('path', '')}"
            if endpoint.get("summary"):
                endpoint_text += f": {endpoint['summary']}"
            if endpoint.get("description"):
                endpoint_text += f" {endpoint['description']}"
            chunks.append(endpoint_text)
        
        # Add schema information
        if parsed_doc.get("schemas"):
            for schema_name, schema in parsed_doc["schemas"].items():
                schema_text = f"Schema {schema_name}: {json.dumps(schema, default=str)[:200]}"
                chunks.append(schema_text)
        
        return chunks
    
    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using configured LLM provider"""
        # This would use the LLM client to generate embeddings
        # For now, return a placeholder
        if self.llm:
            # Use the LLM client to generate embeddings
            # return await self.llm.generate_embedding(text)
            pass
        
        # Fallback: return zero vector
        return [0.0] * 1536  # OpenAI embedding dimension
    
    async def _build_knowledge_graph(self, parsed_doc: Dict) -> Dict[str, Any]:
        """Build knowledge graph from parsed document"""
        try:
            knowledge_graph = {
                "nodes": [],
                "edges": [],
                "metadata": {}
            }
            
            # Add API as root node
            api_node = {
                "id": "api_root",
                "type": "api",
                "label": parsed_doc.get("title", "Unknown API"),
                "properties": {
                    "version": parsed_doc.get("version", "unknown"),
                    "format": parsed_doc.get("format_detected", "unknown")
                }
            }
            knowledge_graph["nodes"].append(api_node)
            
            # Add endpoint nodes
            for i, endpoint in enumerate(parsed_doc.get("endpoints", [])):
                endpoint_node = {
                    "id": f"endpoint_{i}",
                    "type": "endpoint",
                    "label": f"{endpoint.get('method', '')} {endpoint.get('path', '')}",
                    "properties": {
                        "method": endpoint.get("method", ""),
                        "path": endpoint.get("path", ""),
                        "summary": endpoint.get("summary", ""),
                        "tags": endpoint.get("tags", [])
                    }
                }
                knowledge_graph["nodes"].append(endpoint_node)
                
                # Add edge from API to endpoint
                edge = {
                    "source": "api_root",
                    "target": f"endpoint_{i}",
                    "type": "contains"
                }
                knowledge_graph["edges"].append(edge)
            
            # Add metadata
            knowledge_graph["metadata"] = {
                "total_endpoints": len(parsed_doc.get("endpoints", [])),
                "total_schemas": len(parsed_doc.get("schemas", {})),
                "generated_at": datetime.utcnow().isoformat()
            }
            
            return knowledge_graph
            
        except Exception as e:
            self.logger.error("knowledge_graph_build_failed", error=str(e))
            return {
                "error": str(e),
                "nodes": [],
                "edges": [],
                "metadata": {}
            }
    
    async def process_api_spec(self, spec_content: str, spec_type: str = "auto") -> Dict[str, Any]:
        """Process API specification content directly"""
        if spec_type == "auto":
            spec_type = self._detect_document_format(spec_content)
        
        return await self.process_document(spec_content, "api_spec")
    
    async def validate_api_spec(self, spec_content: str) -> Dict[str, Any]:
        """Validate API specification and return validation results"""
        try:
            # Try to parse as JSON first
            json.loads(spec_content)
            format_type = self._detect_document_format(spec_content)
            
            # Basic validation
            validation_result = {
                "is_valid": True,
                "format": format_type.value if hasattr(format_type, 'value') else format_type,
                "size": len(spec_content),
                "line_count": len(spec_content.split('\n')),
                "validation_errors": []
            }
            
            # Format-specific validation
            if format_type in [APIDocFormat.OPENAPI_3, APIDocFormat.SWAGGER_2]:
                validation_result.update(self._validate_openapi_spec(spec_content))
            elif format_type == APIDocFormat.POSTMAN:
                validation_result.update(self._validate_postman_spec(spec_content))
            elif format_type == APIDocFormat.GRAPHQL:
                validation_result.update(self._validate_graphql_spec(spec_content))
            
            return validation_result
            
        except json.JSONDecodeError as e:
            return {
                "is_valid": False,
                "format": "unknown",
                "validation_errors": [f"Invalid JSON: {str(e)}"]
            }
        except Exception as e:
            return {
                "is_valid": False,
                "format": "unknown",
                "validation_errors": [f"Validation error: {str(e)}"]
            }
    
    def _validate_openapi_spec(self, content: str) -> Dict[str, Any]:
        """Basic OpenAPI specification validation"""
        errors = []
        content_lower = content.lower()
        
        if 'openapi:' not in content_lower and 'swagger:' not in content_lower:
            errors.append("Missing OpenAPI/Swagger version")
        
        if '"paths"' not in content_lower:
            errors.append("Missing paths definition")
        
        if '"info"' not in content_lower:
            errors.append("Missing API info section")
        
        return {
            "validation_errors": errors,
            "has_paths": '"paths"' in content_lower,
            "has_info": '"info"' in content_lower
        }
    
    def _validate_postman_spec(self, content: str) -> Dict[str, Any]:
        """Basic Postman collection validation"""
        errors = []
        content_lower = content.lower()
        
        if '"info"' not in content_lower:
            errors.append("Missing collection info")
        
        if '"item"' not in content_lower:
            errors.append("Missing collection items")
        
        return {
            "validation_errors": errors,
            "has_info": '"info"' in content_lower,
            "has_items": '"item"' in content_lower
        }
    
    def _validate_graphql_spec(self, content: str) -> Dict[str, Any]:
        """Basic GraphQL schema validation"""
        errors = []
        content_lower = content.lower()
        
        if 'type' not in content_lower:
            errors.append("Missing type definitions")
        
        if 'query' not in content_lower:
            errors.append("Missing query type")
        
        return {
            "validation_errors": errors,
            "has_types": 'type' in content_lower,
            "has_query": 'query' in content_lower
        }
    
    async def batch_process(self, sources: List[Union[str, bytes, Path]]) -> List[Dict[str, Any]]:
        """Process multiple documents in batch"""
        results = []
        
        for source in sources:
            try:
                result = await self.process_document(source)
                results.append(result)
            except Exception as e:
                self.logger.error("batch_processing_failed", 
                                source=str(source),
                                error=str(e))
                results.append({
                    "source": str(source),
                    "error": str(e),
                    "processed_at": datetime.utcnow().isoformat()
                })
        
        return results
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported document formats"""
        return [format.value for format in APIDocFormat if format != APIDocFormat.UNKNOWN]
    
    def is_format_supported(self, format_type: str) -> bool:
        """Check if a document format is supported"""
        try:
            format_enum = APIDocFormat(format_type)
            return format_enum in self.parsers or format_enum == APIDocFormat.MARKDOWN
        except ValueError:
            return False

