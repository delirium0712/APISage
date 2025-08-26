"""
Code Generator Agent for creating code based on API documentation and examples
"""

import re
import json
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import structlog

from config.settings import AgentConfig, SystemConfig


@dataclass
class CodeTemplate:
    """Template for code generation"""
    name: str
    language: str
    template: str
    description: str = ""
    variables: List[str] = None
    
    def __post_init__(self):
        if self.variables is None:
            self.variables = []


@dataclass
class GeneratedCode:
    """Container for generated code"""
    language: str
    code: str
    description: str = ""
    dependencies: List[str] = None
    usage_example: str = ""
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.metadata is None:
            self.metadata = {}


class CodeGenerator:
    """
    Generates code examples, SDK wrappers, and client libraries based on API documentation.
    Supports multiple programming languages and frameworks.
    """
    
    def __init__(self, config: AgentConfig, system_config: SystemConfig, redis_client=None):
        self.config = config
        self.system_config = system_config
        self.redis_client = redis_client
        self.logger = structlog.get_logger(__name__).bind(agent=config.name)
        
        # Initialize code templates
        self.templates = self._load_default_templates()
        
        # Supported languages
        self.supported_languages = [
            "python", "javascript", "typescript", "java", "csharp", 
            "go", "rust", "php", "ruby", "swift", "kotlin"
        ]
    
    def _load_default_templates(self) -> Dict[str, Dict[str, CodeTemplate]]:
        """Load default code templates for different languages"""
        return {
            "python": {
                "http_client": CodeTemplate(
                    name="http_client",
                    language="python",
                    template="""
import requests
from typing import Optional, Dict, Any

class {class_name}:
    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        {auth_setup}
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        url = f"{{self.base_url}}/{{endpoint.lstrip('/')}}"
        response = self.session.request(method, url, **kwargs)
        response.raise_for_status()
        return response.json()
    
{methods}
""",
                    description="Python HTTP client template",
                    variables=["class_name", "auth_setup", "methods"]
                ),
                "async_client": CodeTemplate(
                    name="async_client",
                    language="python",
                    template="""
import aiohttp
import asyncio
from typing import Optional, Dict, Any

class {class_name}:
    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        {auth_setup}
    
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        url = f"{{self.base_url}}/{{endpoint.lstrip('/')}}"
        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, **kwargs) as response:
                response.raise_for_status()
                return await response.json()
    
{methods}
""",
                    description="Python async HTTP client template",
                    variables=["class_name", "auth_setup", "methods"]
                )
            },
            "javascript": {
                "fetch_client": CodeTemplate(
                    name="fetch_client",
                    language="javascript",
                    template=r"""
class {class_name} {{
    constructor(baseUrl, apiKey = null) {{
        this.baseUrl = baseUrl.replace(/\\/$/, '');
        this.apiKey = apiKey;
        {auth_setup}
    }}
    
    async _makeRequest(method, endpoint, options = {{}}) {{
        const url = `${{this.baseUrl}}/${{endpoint.replace(/^\//, '')}}`;
        const response = await fetch(url, {{
            method,
            headers: {{
                'Content-Type': 'application/json',
                ...this.headers,
                ...options.headers
            }},
            ...options
        }});
        
        if (!response.ok) {{
            throw new Error(`HTTP error! status: ${{response.status}}`);
        }}
        
        return response.json();
    }}
    
{methods}
}}
""",
                    description="JavaScript fetch-based client template",
                    variables=["class_name", "auth_setup", "methods"]
                )
            }
        }
    
    async def generate_client_code(self, 
                                 api_doc: Dict[str, Any], 
                                 language: str = "python",
                                 template_name: str = "http_client") -> GeneratedCode:
        """
        Generate client code for an API based on documentation
        
        Args:
            api_doc: API documentation dictionary
            language: Programming language
            template_name: Template to use
            
        Returns:
            Generated code with metadata
        """
        self.logger.info(
            "generating_client_code",
            language=language,
            template_name=template_name,
            api_title=api_doc.get("title", "Unknown")
        )
        
        if language not in self.supported_languages:
            raise ValueError(f"Language {language} not supported")
        
        # Get template
        template = self.templates.get(language, {}).get(template_name)
        if not template:
            raise ValueError(f"Template {template_name} not found for {language}")
        
        try:
            # Extract API information
            class_name = self._generate_class_name(api_doc.get("title", "APIClient"))
            base_url = api_doc.get("base_url", "")
            endpoints = api_doc.get("endpoints", [])
            authentication = api_doc.get("authentication", [])
            
            # Generate authentication setup
            auth_setup = self._generate_auth_setup(authentication, language)
            
            # Generate methods for endpoints
            methods = self._generate_endpoint_methods(endpoints, language)
            
            # Fill template
            code = template.template.format(
                class_name=class_name,
                auth_setup=auth_setup,
                methods=methods
            )
            
            # Generate usage example
            usage_example = self._generate_usage_example(class_name, base_url, endpoints, language)
            
            # Determine dependencies
            dependencies = self._get_dependencies(language, template_name, authentication)
            
            generated = GeneratedCode(
                language=language,
                code=code.strip(),
                description=f"{class_name} - Generated client for {api_doc.get('title', 'API')}",
                dependencies=dependencies,
                usage_example=usage_example,
                metadata={
                    "api_title": api_doc.get("title", ""),
                    "api_version": api_doc.get("version", ""),
                    "template_used": template_name,
                    "endpoints_count": len(endpoints),
                    "generated_at": datetime.now().isoformat()
                }
            )
            
            self.logger.info(
                "client_code_generated",
                language=language,
                class_name=class_name,
                methods_count=len(endpoints),
                code_length=len(code)
            )
            
            return generated
            
        except Exception as e:
            self.logger.error("code_generation_failed", error=str(e), language=language)
            raise
    
    def _generate_class_name(self, api_title: str) -> str:
        """Generate a valid class name from API title"""
        # Clean up title and convert to PascalCase
        cleaned = re.sub(r'[^a-zA-Z0-9\s]', '', api_title)
        words = cleaned.split()
        class_name = ''.join(word.capitalize() for word in words if word)
        
        # Ensure it ends with 'Client' if not already there
        if not class_name.endswith('Client'):
            class_name += 'Client'
        
        return class_name or 'APIClient'
    
    def _generate_auth_setup(self, auth_methods: List[Dict[str, Any]], language: str) -> str:
        """Generate authentication setup code"""
        if not auth_methods:
            return ""
        
        auth_setup = ""
        
        if language == "python":
            for auth in auth_methods:
                if auth.get("type") == "api_key":
                    auth_setup += """
        if self.api_key:
            self.session.headers['Authorization'] = f'Bearer {self.api_key}'"""
                elif auth.get("type") == "bearer":
                    auth_setup += """
        if self.api_key:
            self.session.headers['Authorization'] = f'Bearer {self.api_key}'"""
                elif auth.get("type") == "basic":
                    auth_setup += """
        if self.api_key:
            self.session.headers['Authorization'] = f'Basic {self.api_key}'"""
        
        elif language == "javascript":
            for auth in auth_methods:
                if auth.get("type") in ["api_key", "bearer"]:
                    auth_setup += """
        this.headers = {};
        if (this.apiKey) {
            this.headers['Authorization'] = `Bearer ${this.apiKey}`;
        }"""
                elif auth.get("type") == "basic":
                    auth_setup += """
        this.headers = {};
        if (this.apiKey) {
            this.headers['Authorization'] = `Basic ${this.apiKey}`;
        }"""
        
        return auth_setup.strip()
    
    def _generate_endpoint_methods(self, endpoints: List[Dict[str, Any]], language: str) -> str:
        """Generate methods for API endpoints"""
        methods = []
        
        for endpoint in endpoints:
            method_name = self._generate_method_name(endpoint.get("path", ""), endpoint.get("method", "GET"))
            http_method = endpoint.get("method", "GET").upper()
            path = endpoint.get("path", "")
            description = endpoint.get("description", "")
            
            if language == "python":
                method_code = f'''
    def {method_name}(self, **kwargs):
        """{description}"""
        return self._make_request("{http_method}", "{path}", **kwargs)'''
            
            elif language == "javascript":
                method_code = f'''
    async {method_name}(options = {{}}) {{
        // {description}
        return this._makeRequest("{http_method}", "{path}", options);
    }}'''
            
            else:
                method_code = f"    // {http_method} {path} - {description}"
            
            methods.append(method_code)
        
        return '\n'.join(methods)
    
    def _generate_method_name(self, path: str, method: str) -> str:
        """Generate a method name from endpoint path and HTTP method"""
        # Clean path and convert to snake_case
        cleaned_path = re.sub(r'[^a-zA-Z0-9/_]', '', path)
        parts = [part for part in cleaned_path.split('/') if part and not part.startswith('{')]
        
        # Add method prefix
        method_prefix = ""
        if method.upper() == "GET":
            method_prefix = "get_"
        elif method.upper() == "POST":
            method_prefix = "create_" if parts else "post_"
        elif method.upper() == "PUT":
            method_prefix = "update_"
        elif method.upper() == "DELETE":
            method_prefix = "delete_"
        elif method.upper() == "PATCH":
            method_prefix = "patch_"
        
        # Combine parts
        if parts:
            method_name = method_prefix + '_'.join(parts).lower()
        else:
            method_name = method_prefix + method.lower()
        
        # Ensure valid identifier
        method_name = re.sub(r'[^a-zA-Z0-9_]', '_', method_name)
        method_name = re.sub(r'_{2,}', '_', method_name)  # Remove multiple underscores
        method_name = method_name.strip('_')
        
        return method_name or f"call_{method.lower()}"
    
    def _generate_usage_example(self, 
                              class_name: str, 
                              base_url: str, 
                              endpoints: List[Dict[str, Any]], 
                              language: str) -> str:
        """Generate usage example code"""
        if language == "python":
            example = f"""# Usage example
client = {class_name}(
    base_url="{base_url or 'https://api.example.com'}",
    api_key="your_api_key_here"
)

# Example API calls"""
            
            for endpoint in endpoints[:3]:  # Show first 3 endpoints
                method_name = self._generate_method_name(endpoint.get("path", ""), endpoint.get("method", "GET"))
                example += f"\nresponse = client.{method_name}()"
                
        elif language == "javascript":
            example = f"""// Usage example
const client = new {class_name}(
    "{base_url or 'https://api.example.com'}",
    "your_api_key_here"
);

// Example API calls"""
            
            for endpoint in endpoints[:3]:  # Show first 3 endpoints
                method_name = self._generate_method_name(endpoint.get("path", ""), endpoint.get("method", "GET"))
                example += f"\nconst response = await client.{method_name}();"
        
        else:
            example = f"// Usage example for {class_name}"
        
        return example
    
    def _get_dependencies(self, language: str, template_name: str, auth_methods: List[Dict[str, Any]]) -> List[str]:
        """Get required dependencies for the generated code"""
        dependencies = []
        
        if language == "python":
            if "async" in template_name:
                dependencies.extend(["aiohttp", "asyncio"])
            else:
                dependencies.append("requests")
        
        elif language == "javascript":
            # Most modern environments have fetch built-in
            dependencies = []
        
        return dependencies
    
    async def generate_code_examples(self, 
                                   api_doc: Dict[str, Any],
                                   languages: List[str] = None) -> Dict[str, GeneratedCode]:
        """
        Generate code examples for multiple languages
        
        Args:
            api_doc: API documentation
            languages: List of languages to generate for
            
        Returns:
            Dictionary mapping language to generated code
        """
        if languages is None:
            languages = ["python", "javascript"]
        
        self.logger.info("generating_multi_language_examples", languages=languages)
        
        examples = {}
        
        for language in languages:
            if language not in self.supported_languages:
                self.logger.warning("unsupported_language", language=language)
                continue
            
            try:
                # Choose appropriate template
                template_name = "http_client"
                if language == "python":
                    template_name = "async_client"  # Prefer async for Python
                
                code = await self.generate_client_code(api_doc, language, template_name)
                examples[language] = code
                
            except Exception as e:
                self.logger.error("language_generation_failed", language=language, error=str(e))
                continue
        
        return examples
    
    def add_custom_template(self, template: CodeTemplate) -> None:
        """Add a custom code template"""
        if template.language not in self.templates:
            self.templates[template.language] = {}
        
        self.templates[template.language][template.name] = template
        self.logger.info("custom_template_added", language=template.language, name=template.name)
    
    def list_templates(self, language: Optional[str] = None) -> Dict[str, List[str]]:
        """List available templates"""
        if language:
            return {language: list(self.templates.get(language, {}).keys())}
        
        return {lang: list(templates.keys()) for lang, templates in self.templates.items()}