"""
API Analyzer Agent for analyzing API documentation and extracting structured information
"""

import json
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import structlog
from urllib.parse import urljoin, urlparse

from config.settings import AgentConfig, SystemConfig


@dataclass
class APIEndpoint:
    """Represents an API endpoint"""
    method: str
    path: str
    description: str = ""
    parameters: List[Dict[str, Any]] = None
    responses: Dict[str, Any] = None
    examples: List[Dict[str, Any]] = None
    authentication: Optional[str] = None
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = []
        if self.responses is None:
            self.responses = {}
        if self.examples is None:
            self.examples = []


@dataclass
class APIAuthentication:
    """Represents API authentication method"""
    type: str  # "bearer", "basic", "api_key", "oauth2"
    description: str = ""
    location: str = ""  # "header", "query", "cookie"
    name: str = ""  # parameter name for api_key
    scheme: str = ""  # for oauth2


@dataclass
class APIDocumentation:
    """Structured API documentation"""
    title: str
    version: str = ""
    base_url: str = ""
    description: str = ""
    endpoints: List[APIEndpoint] = None
    authentication: List[APIAuthentication] = None
    schemas: Dict[str, Any] = None
    rate_limits: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.endpoints is None:
            self.endpoints = []
        if self.authentication is None:
            self.authentication = []
        if self.schemas is None:
            self.schemas = {}
        if self.rate_limits is None:
            self.rate_limits = {}


class APIAnalyzer:
    """
    Analyzes API documentation to extract structured information about endpoints,
    authentication, parameters, and other API details.
    """
    
    def __init__(self, config: AgentConfig, system_config: SystemConfig, redis_client=None):
        self.config = config
        self.system_config = system_config
        self.redis_client = redis_client
        self.logger = structlog.get_logger(__name__).bind(agent=config.name)
        
        # Common patterns for API documentation
        self.endpoint_patterns = [
            r'(GET|POST|PUT|DELETE|PATCH)\s+([^\s]+)',
            r'([A-Z]+)\s+`([^`]+)`',
            r'### (GET|POST|PUT|DELETE|PATCH)\s+([^\n]+)',
            r'## (GET|POST|PUT|DELETE|PATCH)\s+([^\n]+)',
        ]
        
        self.auth_patterns = [
            r'(?i)authentication?[:\s]+([^\n]+)',
            r'(?i)authorization[:\s]+([^\n]+)',
            r'(?i)api[_\s]key[:\s]*([^\n]+)',
            r'(?i)bearer[:\s]+([^\n]+)',
            r'(?i)oauth[:\s]*([^\n]+)',
        ]
        
        self.rate_limit_patterns = [
            r'(?i)rate[_\s]limit[s]?[:\s]*([^\n]+)',
            r'(?i)requests?[_\s]per[_\s](minute|hour|day)[:\s]*([^\n]+)',
            r'(?i)throttl(?:e|ing)[:\s]*([^\n]+)',
        ]
    
    async def analyze_api_documentation(self, content: str, source_url: str = "") -> APIDocumentation:
        """
        Analyze API documentation content and extract structured information
        
        Args:
            content: Raw API documentation content
            source_url: URL of the documentation source
            
        Returns:
            APIDocumentation object with extracted information
        """
        self.logger.info("analyzing_api_documentation", source=source_url)
        
        try:
            # Extract basic information
            title = self._extract_title(content)
            version = self._extract_version(content)
            base_url = self._extract_base_url(content, source_url)
            description = self._extract_description(content)
            
            # Extract endpoints
            endpoints = self._extract_endpoints(content)
            
            # Extract authentication information
            authentication = self._extract_authentication(content)
            
            # Extract schemas/models
            schemas = self._extract_schemas(content)
            
            # Extract rate limits
            rate_limits = self._extract_rate_limits(content)
            
            api_doc = APIDocumentation(
                title=title,
                version=version,
                base_url=base_url,
                description=description,
                endpoints=endpoints,
                authentication=authentication,
                schemas=schemas,
                rate_limits=rate_limits
            )
            
            self.logger.info(
                "api_analysis_completed",
                endpoints_count=len(endpoints),
                auth_methods=len(authentication),
                schemas_count=len(schemas)
            )
            
            return api_doc
            
        except Exception as e:
            self.logger.error("api_analysis_failed", error=str(e), source=source_url)
            # Return minimal documentation on error
            return APIDocumentation(
                title=self._extract_title(content) or "Unknown API",
                description="Failed to fully analyze API documentation"
            )
    
    def _extract_title(self, content: str) -> str:
        """Extract API title from content"""
        patterns = [
            r'# ([^\n]+)',
            r'<h1[^>]*>([^<]+)</h1>',
            r'(?i)title[:\s]*([^\n]+)',
            r'(?i)api[:\s]*([^\n]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                title = match.group(1).strip()
                if len(title) > 5 and len(title) < 100:  # Reasonable title length
                    return title
        
        return "API Documentation"
    
    def _extract_version(self, content: str) -> str:
        """Extract API version from content"""
        patterns = [
            r'(?i)version[:\s]*([0-9]+\.[0-9]+(?:\.[0-9]+)?)',
            r'(?i)v([0-9]+\.[0-9]+(?:\.[0-9]+)?)',
            r'/v([0-9]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                return match.group(1)
        
        return ""
    
    def _extract_base_url(self, content: str, source_url: str = "") -> str:
        """Extract base URL for the API"""
        patterns = [
            r'(?i)base[_\s]url[:\s]*([^\s\n]+)',
            r'(?i)endpoint[:\s]*([^\s\n]+)',
            r'https?://[^\s/]+/api[^\s]*',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                url = match.group(1).strip()
                if url.startswith('http'):
                    return url
        
        # Try to infer from source URL
        if source_url:
            parsed = urlparse(source_url)
            if parsed.hostname:
                return f"{parsed.scheme}://{parsed.hostname}/api"
        
        return ""
    
    def _extract_description(self, content: str) -> str:
        """Extract API description"""
        # Look for description after title
        lines = content.split('\n')
        in_description = False
        description_lines = []
        
        for line in lines:
            line = line.strip()
            if re.match(r'^#+\s', line):  # Heading
                if in_description:
                    break
                if any(word in line.lower() for word in ['api', 'description', 'overview']):
                    in_description = True
                    continue
            elif in_description and line:
                if not line.startswith('#'):
                    description_lines.append(line)
            elif not in_description and line and len(line) > 50:
                # First substantial paragraph might be description
                description_lines.append(line)
                if len(description_lines) > 2:
                    break
        
        return ' '.join(description_lines[:3])  # First 3 sentences
    
    def _extract_endpoints(self, content: str) -> List[APIEndpoint]:
        """Extract API endpoints from content"""
        endpoints = []
        
        for pattern in self.endpoint_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                method = match.group(1).upper()
                path = match.group(2).strip('`')
                
                # Extract description (look for text after the endpoint)
                start_pos = match.end()
                description = self._extract_endpoint_description(content, start_pos)
                
                endpoint = APIEndpoint(
                    method=method,
                    path=path,
                    description=description
                )
                
                endpoints.append(endpoint)
        
        # Remove duplicates
        unique_endpoints = []
        seen = set()
        for endpoint in endpoints:
            key = (endpoint.method, endpoint.path)
            if key not in seen:
                seen.add(key)
                unique_endpoints.append(endpoint)
        
        return unique_endpoints
    
    def _extract_endpoint_description(self, content: str, start_pos: int) -> str:
        """Extract description for an endpoint"""
        # Look for the next 200 characters for description
        section = content[start_pos:start_pos + 200]
        lines = section.split('\n')
        
        description_lines = []
        for line in lines[:3]:  # First 3 lines
            line = line.strip()
            if line and not line.startswith('#') and not re.match(r'^(GET|POST|PUT|DELETE|PATCH)', line):
                description_lines.append(line)
        
        return ' '.join(description_lines).strip()
    
    def _extract_authentication(self, content: str) -> List[APIAuthentication]:
        """Extract authentication methods"""
        auth_methods = []
        
        for pattern in self.auth_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                description = match.group(1).strip()
                
                # Determine auth type from description
                auth_type = "unknown"
                if any(word in description.lower() for word in ['bearer', 'jwt', 'token']):
                    auth_type = "bearer"
                elif 'api key' in description.lower() or 'apikey' in description.lower():
                    auth_type = "api_key"
                elif 'basic' in description.lower():
                    auth_type = "basic"
                elif 'oauth' in description.lower():
                    auth_type = "oauth2"
                
                auth = APIAuthentication(
                    type=auth_type,
                    description=description
                )
                auth_methods.append(auth)
        
        return auth_methods
    
    def _extract_schemas(self, content: str) -> Dict[str, Any]:
        """Extract data schemas/models"""
        schemas = {}
        
        # Look for JSON examples or schema definitions
        json_blocks = re.findall(r'```json\s*\n(.*?)\n```', content, re.DOTALL)
        for i, block in enumerate(json_blocks):
            try:
                schema = json.loads(block.strip())
                schemas[f"example_{i}"] = schema
            except json.JSONDecodeError:
                continue
        
        return schemas
    
    def _extract_rate_limits(self, content: str) -> Dict[str, Any]:
        """Extract rate limit information"""
        rate_limits = {}
        
        for pattern in self.rate_limit_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                limit_text = match.group(1) if match.lastindex >= 1 else match.group(0)
                
                # Try to extract numbers
                numbers = re.findall(r'\d+', limit_text)
                if numbers:
                    rate_limits['limit'] = int(numbers[0])
                    
                # Extract time unit
                if 'minute' in limit_text.lower():
                    rate_limits['per'] = 'minute'
                elif 'hour' in limit_text.lower():
                    rate_limits['per'] = 'hour'
                elif 'day' in limit_text.lower():
                    rate_limits['per'] = 'day'
                
                rate_limits['description'] = limit_text
                break
        
        return rate_limits
    
    def to_dict(self, api_doc: APIDocumentation) -> Dict[str, Any]:
        """Convert APIDocumentation to dictionary"""
        return {
            "title": api_doc.title,
            "version": api_doc.version,
            "base_url": api_doc.base_url,
            "description": api_doc.description,
            "endpoints": [
                {
                    "method": ep.method,
                    "path": ep.path,
                    "description": ep.description,
                    "parameters": ep.parameters,
                    "responses": ep.responses,
                    "examples": ep.examples,
                    "authentication": ep.authentication
                }
                for ep in api_doc.endpoints
            ],
            "authentication": [
                {
                    "type": auth.type,
                    "description": auth.description,
                    "location": auth.location,
                    "name": auth.name,
                    "scheme": auth.scheme
                }
                for auth in api_doc.authentication
            ],
            "schemas": api_doc.schemas,
            "rate_limits": api_doc.rate_limits
        }