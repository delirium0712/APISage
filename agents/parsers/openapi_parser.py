"""
OpenAPI/Swagger specification parser
"""

import json
import yaml
from typing import Dict, Any, List, Union
from .base_parser import BaseDocumentParser, DocumentFormat, ParsedDocument


class OpenAPIParser(BaseDocumentParser):
    """Parser for OpenAPI/Swagger specifications"""
    
    def can_parse(self, content: Union[str, bytes], content_type: str = None, filename: str = None) -> bool:
        """Check if content is OpenAPI/Swagger format"""
        doc_format = self._detect_format(content, content_type, filename)
        return doc_format in [
            DocumentFormat.OPENAPI_JSON,
            DocumentFormat.OPENAPI_YAML,
            DocumentFormat.SWAGGER_JSON,
            DocumentFormat.SWAGGER_YAML
        ]
    
    async def parse(self, content: Union[str, bytes], content_type: str = None, filename: str = None) -> ParsedDocument:
        """Parse OpenAPI/Swagger specification"""
        
        if isinstance(content, bytes):
            content = content.decode('utf-8')
        
        doc_format = self._detect_format(content, content_type, filename)
        
        try:
            # Parse JSON or YAML
            if doc_format in [DocumentFormat.OPENAPI_JSON, DocumentFormat.SWAGGER_JSON]:
                spec = json.loads(content)
            else:
                spec = yaml.safe_load(content)
            
            # Extract basic info
            info = spec.get('info', {})
            title = info.get('title', 'API Documentation')
            description = info.get('description', '')
            version = info.get('version', '')
            
            # Extract servers
            servers = spec.get('servers', [])
            if not servers and 'host' in spec:
                # Swagger 2.0 format
                schemes = spec.get('schemes', ['https'])
                base_path = spec.get('basePath', '')
                servers = [{'url': f"{schemes[0]}://{spec['host']}{base_path}"}]
            
            # Extract paths and operations
            endpoints = []
            paths = spec.get('paths', {})
            
            for path, methods in paths.items():
                for method, operation in methods.items():
                    if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']:
                        endpoint = {
                            'path': path,
                            'method': method.upper(),
                            'summary': operation.get('summary', ''),
                            'description': operation.get('description', ''),
                            'parameters': operation.get('parameters', []),
                            'responses': operation.get('responses', {}),
                            'tags': operation.get('tags', [])
                        }
                        endpoints.append(endpoint)
            
            # Extract schemas/components
            schemas = []
            components = spec.get('components', {}) or spec.get('definitions', {})
            if isinstance(components, dict):
                schemas_dict = components.get('schemas', components)
                for name, schema in schemas_dict.items():
                    schemas.append({
                        'name': name,
                        'type': schema.get('type', 'object'),
                        'properties': schema.get('properties', {}),
                        'description': schema.get('description', '')
                    })
            
            # Generate examples
            examples = self._extract_examples(spec, endpoints)
            
            # Create structured content for chunking
            structured_content = self._create_structured_content(spec, endpoints, schemas)
            
            # Generate chunks
            chunks = self._chunk_content(structured_content)
            
            return ParsedDocument(
                format=doc_format,
                title=title,
                description=description,
                content=structured_content,
                metadata={
                    'version': version,
                    'servers': servers,
                    'tags': spec.get('tags', []),
                    'security': spec.get('security', [])
                },
                endpoints=endpoints,
                examples=examples,
                schemas=schemas,
                chunks=chunks
            )
            
        except Exception as e:
            self.logger.error("Failed to parse OpenAPI specification", error=str(e))
            raise ValueError(f"Invalid OpenAPI/Swagger specification: {str(e)}")
    
    def _extract_examples(self, spec: Dict[str, Any], endpoints: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract examples from the specification"""
        examples = []
        
        for endpoint in endpoints:
            path = endpoint['path']
            method = endpoint['method']
            
            # Create basic request example
            example = {
                'type': 'request',
                'endpoint': f"{method} {path}",
                'description': endpoint.get('summary', ''),
                'example': self._generate_request_example(endpoint, spec)
            }
            examples.append(example)
            
            # Add response examples if available
            for status_code, response in endpoint.get('responses', {}).items():
                if 'examples' in response:
                    for content_type, example_data in response['examples'].items():
                        examples.append({
                            'type': 'response',
                            'endpoint': f"{method} {path}",
                            'status_code': status_code,
                            'content_type': content_type,
                            'example': example_data
                        })
        
        return examples
    
    def _generate_request_example(self, endpoint: Dict[str, Any], spec: Dict[str, Any]) -> str:
        """Generate a request example for an endpoint"""
        method = endpoint['method']
        path = endpoint['path']
        
        # Get server URL
        servers = spec.get('servers', [])
        base_url = servers[0]['url'] if servers else 'https://api.example.com'
        
        # Build example
        example_lines = [f"{method} {base_url}{path}"]
        
        # Add headers
        example_lines.append("Content-Type: application/json")
        
        # Add parameters if any
        parameters = endpoint.get('parameters', [])
        query_params = [p for p in parameters if p.get('in') == 'query']
        if query_params:
            params = []
            for param in query_params:
                name = param.get('name', 'param')
                example_val = param.get('example', 'value')
                params.append(f"{name}={example_val}")
            if params:
                example_lines[0] += f"?{'&'.join(params)}"
        
        return "\n".join(example_lines)
    
    def _create_structured_content(self, spec: Dict[str, Any], endpoints: List[Dict[str, Any]], schemas: List[Dict[str, Any]]) -> str:
        """Create structured content for vector search"""
        
        content_parts = []
        
        # API Overview
        info = spec.get('info', {})
        content_parts.append(f"# {info.get('title', 'API Documentation')}")
        content_parts.append(f"Version: {info.get('version', 'N/A')}")
        if info.get('description'):
            content_parts.append(f"\n{info['description']}")
        
        # Servers
        servers = spec.get('servers', [])
        if servers:
            content_parts.append("\n## Base URLs")
            for server in servers:
                content_parts.append(f"- {server.get('url', '')}")
                if server.get('description'):
                    content_parts.append(f"  {server['description']}")
        
        # Endpoints
        content_parts.append("\n## Endpoints")
        for endpoint in endpoints:
            content_parts.append(f"\n### {endpoint['method']} {endpoint['path']}")
            if endpoint.get('summary'):
                content_parts.append(f"**Summary:** {endpoint['summary']}")
            if endpoint.get('description'):
                content_parts.append(f"**Description:** {endpoint['description']}")
            
            # Parameters
            if endpoint.get('parameters'):
                content_parts.append("**Parameters:**")
                for param in endpoint['parameters']:
                    param_info = f"- {param.get('name', '')} ({param.get('in', '')})"
                    if param.get('required'):
                        param_info += " *required*"
                    if param.get('description'):
                        param_info += f": {param['description']}"
                    content_parts.append(param_info)
            
            # Responses
            if endpoint.get('responses'):
                content_parts.append("**Responses:**")
                for status, response in endpoint['responses'].items():
                    response_info = f"- {status}"
                    if response.get('description'):
                        response_info += f": {response['description']}"
                    content_parts.append(response_info)
        
        # Schemas
        if schemas:
            content_parts.append("\n## Data Models")
            for schema in schemas:
                content_parts.append(f"\n### {schema['name']}")
                if schema.get('description'):
                    content_parts.append(schema['description'])
                
                if schema.get('properties'):
                    content_parts.append("**Properties:**")
                    for prop_name, prop_def in schema['properties'].items():
                        prop_info = f"- {prop_name} ({prop_def.get('type', 'unknown')})"
                        if prop_def.get('description'):
                            prop_info += f": {prop_def['description']}"
                        content_parts.append(prop_info)
        
        return "\n".join(content_parts)