"""
Postman collection parser
"""

import json
from typing import Dict, Any, List, Union
from .base_parser import BaseDocumentParser, DocumentFormat, ParsedDocument


class PostmanParser(BaseDocumentParser):
    """Parser for Postman collections"""
    
    def can_parse(self, content: Union[str, bytes], content_type: str = None, filename: str = None) -> bool:
        """Check if content is Postman collection format"""
        doc_format = self._detect_format(content, content_type, filename)
        return doc_format == DocumentFormat.POSTMAN_COLLECTION
    
    async def parse(self, content: Union[str, bytes], content_type: str = None, filename: str = None) -> ParsedDocument:
        """Parse Postman collection"""
        
        if isinstance(content, bytes):
            content = content.decode('utf-8')
        
        try:
            # Parse JSON collection
            collection = json.loads(content)
            
            # Extract basic info
            info = collection.get('info', {})
            title = info.get('name', 'Postman Collection')
            description = info.get('description', '')
            
            # Extract variables
            variables = self._extract_variables(collection)
            
            # Extract endpoints from items
            endpoints = self._extract_endpoints(collection.get('item', []), variables)
            
            # Generate examples from requests
            examples = self._generate_examples(endpoints)
            
            # Extract schemas from request/response bodies
            schemas = self._extract_schemas(endpoints)
            
            # Create structured content
            structured_content = self._create_structured_content(collection, endpoints)
            
            # Generate chunks
            chunks = self._chunk_content(structured_content)
            
            return ParsedDocument(
                format=DocumentFormat.POSTMAN_COLLECTION,
                title=title,
                description=description,
                content=structured_content,
                metadata={
                    'version': info.get('version', ''),
                    'schema': collection.get('info', {}).get('schema', ''),
                    'variables': variables,
                    'auth': collection.get('auth', {}),
                    'events': collection.get('event', [])
                },
                endpoints=endpoints,
                examples=examples,
                schemas=schemas,
                chunks=chunks
            )
            
        except Exception as e:
            self.logger.error("Failed to parse Postman collection", error=str(e))
            raise ValueError(f"Invalid Postman collection: {str(e)}")
    
    def _extract_variables(self, collection: Dict[str, Any]) -> Dict[str, str]:
        """Extract variables from collection"""
        variables = {}
        
        # Collection-level variables
        for var in collection.get('variable', []):
            if isinstance(var, dict):
                key = var.get('key', var.get('id', ''))
                value = var.get('value', '')
                if key:
                    variables[key] = value
        
        return variables
    
    def _extract_endpoints(self, items: List[Dict[str, Any]], variables: Dict[str, str], folder_path: str = "") -> List[Dict[str, Any]]:
        """Extract endpoints from Postman items (recursive for folders)"""
        endpoints = []
        
        for item in items:
            # Handle folders (recursive)
            if 'item' in item:
                folder_name = item.get('name', 'Folder')
                new_folder_path = f"{folder_path}/{folder_name}" if folder_path else folder_name
                endpoints.extend(self._extract_endpoints(item['item'], variables, new_folder_path))
            
            # Handle requests
            elif 'request' in item:
                request = item['request']
                
                # Extract URL
                url_obj = request.get('url', {})
                if isinstance(url_obj, str):
                    url = url_obj
                    path = url
                else:
                    # URL object format
                    host = url_obj.get('host', [])
                    if isinstance(host, list):
                        host = '.'.join(host)
                    elif isinstance(host, str):
                        host = host
                    else:
                        host = 'api.example.com'
                    
                    path_segments = url_obj.get('path', [])
                    if isinstance(path_segments, list):
                        path = '/' + '/'.join(str(seg) for seg in path_segments)
                    else:
                        path = str(path_segments) if path_segments else '/'
                    
                    protocol = url_obj.get('protocol', 'https')
                    port = url_obj.get('port', '')
                    port_str = f":{port}" if port else ""
                    
                    url = f"{protocol}://{host}{port_str}{path}"
                
                # Replace variables in URL
                for var_key, var_value in variables.items():
                    url = url.replace(f"{{{{{var_key}}}}}", var_value)
                    path = path.replace(f"{{{{{var_key}}}}}", var_value)
                
                # Extract method
                method = request.get('method', 'GET').upper()
                
                # Extract headers
                headers = {}
                for header in request.get('header', []):
                    if isinstance(header, dict) and not header.get('disabled', False):
                        key = header.get('key', '')
                        value = header.get('value', '')
                        if key:
                            headers[key] = value
                
                # Extract query parameters
                query_params = []
                if isinstance(url_obj, dict):
                    for query in url_obj.get('query', []):
                        if isinstance(query, dict) and not query.get('disabled', False):
                            query_params.append({
                                'name': query.get('key', ''),
                                'value': query.get('value', ''),
                                'description': query.get('description', '')
                            })
                
                # Extract body
                body = request.get('body', {})
                body_content = None
                if body.get('mode') == 'raw':
                    body_content = body.get('raw', '')
                elif body.get('mode') == 'formdata':
                    body_content = body.get('formdata', [])
                elif body.get('mode') == 'urlencoded':
                    body_content = body.get('urlencoded', [])
                
                # Extract responses
                responses = {}
                for response in item.get('response', []):
                    status_code = response.get('code', response.get('status', '200'))
                    responses[str(status_code)] = {
                        'description': response.get('name', ''),
                        'body': response.get('body', ''),
                        'headers': {h.get('key', ''): h.get('value', '') for h in response.get('header', [])}
                    }
                
                endpoint = {
                    'path': path,
                    'method': method,
                    'summary': item.get('name', f"{method} {path}"),
                    'description': self._extract_description(item),
                    'url': url,
                    'headers': headers,
                    'query_parameters': query_params,
                    'body': body_content,
                    'responses': responses,
                    'folder': folder_path,
                    'tags': [folder_path] if folder_path else []
                }
                
                endpoints.append(endpoint)
        
        return endpoints
    
    def _extract_description(self, item: Dict[str, Any]) -> str:
        """Extract description from Postman item"""
        # Try different description fields
        description_sources = [
            item.get('description', ''),
            item.get('request', {}).get('description', ''),
        ]
        
        for desc in description_sources:
            if isinstance(desc, dict):
                # Description object format
                desc = desc.get('content', '')
            
            if desc and isinstance(desc, str):
                return desc.strip()
        
        return ''
    
    def _generate_examples(self, endpoints: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate examples from endpoints"""
        examples = []
        
        for endpoint in endpoints:
            # Request example
            request_lines = [f"{endpoint['method']} {endpoint['url']}"]
            
            # Add headers
            for key, value in endpoint.get('headers', {}).items():
                request_lines.append(f"{key}: {value}")
            
            # Add body if present
            body = endpoint.get('body')
            if body and isinstance(body, str):
                request_lines.append("")
                request_lines.append(body)
            
            examples.append({
                'type': 'request',
                'endpoint': f"{endpoint['method']} {endpoint['path']}",
                'description': endpoint.get('summary', ''),
                'example': '\n'.join(request_lines)
            })
            
            # Response examples
            for status_code, response in endpoint.get('responses', {}).items():
                if response.get('body'):
                    examples.append({
                        'type': 'response',
                        'endpoint': f"{endpoint['method']} {endpoint['path']}",
                        'status_code': status_code,
                        'description': response.get('description', ''),
                        'example': response['body']
                    })
        
        return examples
    
    def _extract_schemas(self, endpoints: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract schemas from request/response bodies"""
        schemas = []
        schema_names = set()
        
        for endpoint in endpoints:
            # Try to extract schema from request body
            body = endpoint.get('body')
            if body and isinstance(body, str):
                try:
                    body_json = json.loads(body)
                    schema_name = f"{endpoint['method']}_{endpoint['path'].replace('/', '_').replace('{', '').replace('}', '')}_Request"
                    if schema_name not in schema_names:
                        schema = self._json_to_schema(body_json, schema_name)
                        if schema:
                            schemas.append(schema)
                            schema_names.add(schema_name)
                except json.JSONDecodeError:
                    pass
            
            # Try to extract schema from response bodies
            for status_code, response in endpoint.get('responses', {}).items():
                response_body = response.get('body', '')
                if response_body:
                    try:
                        response_json = json.loads(response_body)
                        schema_name = f"{endpoint['method']}_{endpoint['path'].replace('/', '_').replace('{', '').replace('}', '')}_Response_{status_code}"
                        if schema_name not in schema_names:
                            schema = self._json_to_schema(response_json, schema_name)
                            if schema:
                                schemas.append(schema)
                                schema_names.add(schema_name)
                    except json.JSONDecodeError:
                        pass
        
        return schemas
    
    def _json_to_schema(self, json_obj: Any, name: str) -> Dict[str, Any]:
        """Convert JSON object to schema representation"""
        if not isinstance(json_obj, dict):
            return None
        
        properties = {}
        for key, value in json_obj.items():
            prop_type = type(value).__name__
            if prop_type == 'dict':
                prop_type = 'object'
            elif prop_type == 'list':
                prop_type = 'array'
            elif prop_type == 'bool':
                prop_type = 'boolean'
            elif prop_type in ['int', 'float']:
                prop_type = 'number'
            else:
                prop_type = 'string'
            
            properties[key] = {
                'type': prop_type,
                'description': f"Property {key}"
            }
        
        return {
            'name': name,
            'type': 'object',
            'properties': properties,
            'description': f"Schema for {name}"
        }
    
    def _create_structured_content(self, collection: Dict[str, Any], endpoints: List[Dict[str, Any]]) -> str:
        """Create structured content for vector search"""
        content_parts = []
        
        # Collection info
        info = collection.get('info', {})
        content_parts.append(f"# {info.get('name', 'Postman Collection')}")
        if info.get('description'):
            content_parts.append(f"\n{info['description']}")
        
        # Variables
        variables = collection.get('variable', [])
        if variables:
            content_parts.append("\n## Variables")
            for var in variables:
                if isinstance(var, dict):
                    key = var.get('key', '')
                    value = var.get('value', '')
                    description = var.get('description', '')
                    content_parts.append(f"- {key}: {value}")
                    if description:
                        content_parts.append(f"  {description}")
        
        # Endpoints grouped by folder
        folders = {}
        for endpoint in endpoints:
            folder = endpoint.get('folder', 'Root')
            if folder not in folders:
                folders[folder] = []
            folders[folder].append(endpoint)
        
        for folder_name, folder_endpoints in folders.items():
            content_parts.append(f"\n## {folder_name}")
            
            for endpoint in folder_endpoints:
                content_parts.append(f"\n### {endpoint['method']} {endpoint['path']}")
                content_parts.append(f"**Summary:** {endpoint.get('summary', '')}")
                
                if endpoint.get('description'):
                    content_parts.append(f"**Description:** {endpoint['description']}")
                
                # Query parameters
                query_params = endpoint.get('query_parameters', [])
                if query_params:
                    content_parts.append("**Query Parameters:**")
                    for param in query_params:
                        param_line = f"- {param.get('name', '')}"
                        if param.get('description'):
                            param_line += f": {param['description']}"
                        content_parts.append(param_line)
                
                # Headers
                headers = endpoint.get('headers', {})
                if headers:
                    content_parts.append("**Headers:**")
                    for key, value in headers.items():
                        content_parts.append(f"- {key}: {value}")
                
                # Body
                body = endpoint.get('body')
                if body:
                    content_parts.append("**Request Body:**")
                    if isinstance(body, str):
                        content_parts.append(f"```\n{body}\n```")
                
                # Responses
                responses = endpoint.get('responses', {})
                if responses:
                    content_parts.append("**Responses:**")
                    for status_code, response in responses.items():
                        response_line = f"- {status_code}"
                        if response.get('description'):
                            response_line += f": {response['description']}"
                        content_parts.append(response_line)
        
        return '\n'.join(content_parts)