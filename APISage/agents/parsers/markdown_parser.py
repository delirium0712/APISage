"""
Markdown document parser
"""

import re
from typing import Dict, Any, List, Union
from .base_parser import BaseDocumentParser, DocumentFormat, ParsedDocument


class MarkdownParser(BaseDocumentParser):
    """Parser for Markdown API documentation"""
    
    def can_parse(self, content: Union[str, bytes], content_type: str = None, filename: str = None) -> bool:
        """Check if content is Markdown format"""
        doc_format = self._detect_format(content, content_type, filename)
        return doc_format == DocumentFormat.MARKDOWN
    
    async def parse(self, content: Union[str, bytes], content_type: str = None, filename: str = None) -> ParsedDocument:
        """Parse Markdown documentation"""
        
        if isinstance(content, bytes):
            content = content.decode('utf-8')
        
        try:
            # Extract title and description
            title, description = self._extract_title_description(content)
            
            # Extract endpoints from markdown
            endpoints = self._extract_endpoints(content)
            
            # Extract code examples
            examples = self._extract_examples(content)
            
            # Extract schema information
            schemas = self._extract_schemas(content)
            
            # Create structured content
            structured_content = self._create_structured_content(content)
            
            # Generate chunks
            chunks = self._chunk_content(structured_content)
            
            return ParsedDocument(
                format=DocumentFormat.MARKDOWN,
                title=title,
                description=description,
                content=structured_content,
                metadata={
                    'sections': self._extract_sections(content),
                    'code_blocks': len(re.findall(r'```', content)) // 2,
                    'links': len(re.findall(r'\[.*?\]\(.*?\)', content))
                },
                endpoints=endpoints,
                examples=examples,
                schemas=schemas,
                chunks=chunks
            )
            
        except Exception as e:
            self.logger.error("Failed to parse Markdown", error=str(e))
            raise ValueError(f"Invalid Markdown document: {str(e)}")
    
    def _extract_title_description(self, content: str) -> tuple[str, str]:
        """Extract title and description from markdown"""
        lines = content.split('\n')
        title = "API Documentation"
        description = ""
        
        # Find the first H1 header
        for line in lines:
            if line.strip().startswith('# '):
                title = line.strip()[2:]
                break
        
        # Extract description (first paragraph after title)
        in_description = False
        description_lines = []
        
        for line in lines:
            if line.strip().startswith('# '):
                in_description = True
                continue
            elif in_description:
                if line.strip().startswith('#') or (line.strip() == '' and description_lines):
                    break
                elif line.strip():
                    description_lines.append(line.strip())
        
        description = ' '.join(description_lines)
        return title, description
    
    def _extract_sections(self, content: str) -> List[Dict[str, Any]]:
        """Extract section structure from markdown"""
        sections = []
        lines = content.split('\n')
        
        current_section = None
        for i, line in enumerate(lines):
            if line.strip().startswith('#'):
                if current_section:
                    sections.append(current_section)
                
                level = len(line) - len(line.lstrip('#'))
                title = line.strip()[level:].strip()
                current_section = {
                    'level': level,
                    'title': title,
                    'line_number': i + 1,
                    'content': []
                }
            elif current_section:
                current_section['content'].append(line)
        
        if current_section:
            sections.append(current_section)
        
        return sections
    
    def _extract_endpoints(self, content: str) -> List[Dict[str, Any]]:
        """Extract API endpoints from markdown content"""
        endpoints = []
        
        # Common patterns for API endpoints in markdown
        patterns = [
            # HTTP method and path
            r'`?(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\s+([^\s`]+)`?',
            # Method in headers
            r'#{1,6}\s*(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\s+([^\s#]+)',
            # Code blocks with HTTP requests
            r'```(?:http|bash|curl)?\n(?:curl\s+)?(?:-X\s+)?(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\s+([^\s\n]+)',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                method = match.group(1).upper()
                path = match.group(2)
                
                # Find context around the match
                lines = content[:match.start()].split('\n')
                line_num = len(lines)
                
                # Look for description in nearby text
                context_start = max(0, line_num - 5)
                context_end = min(len(content.split('\n')), line_num + 5)
                context_lines = content.split('\n')[context_start:context_end]
                
                description = self._extract_endpoint_description(context_lines, method, path)
                
                endpoint = {
                    'path': path,
                    'method': method,
                    'summary': f"{method} {path}",
                    'description': description,
                    'line_number': line_num,
                    'parameters': [],
                    'responses': {},
                    'tags': []
                }
                
                # Avoid duplicates
                if not any(e['path'] == path and e['method'] == method for e in endpoints):
                    endpoints.append(endpoint)
        
        return endpoints
    
    def _extract_endpoint_description(self, context_lines: List[str], method: str, path: str) -> str:
        """Extract description for an endpoint from context"""
        description_parts = []
        
        for line in context_lines:
            # Skip lines with the endpoint itself
            if method in line and path in line:
                continue
            
            # Look for descriptive text
            clean_line = line.strip()
            if clean_line and not clean_line.startswith('#') and not clean_line.startswith('```'):
                # Remove markdown formatting
                clean_line = re.sub(r'\*\*(.*?)\*\*', r'\1', clean_line)
                clean_line = re.sub(r'\*(.*?)\*', r'\1', clean_line)
                clean_line = re.sub(r'`(.*?)`', r'\1', clean_line)
                description_parts.append(clean_line)
        
        return ' '.join(description_parts)[:200]  # Limit description length
    
    def _extract_examples(self, content: str) -> List[Dict[str, Any]]:
        """Extract code examples from markdown"""
        examples = []
        
        # Find code blocks
        code_block_pattern = r'```(\w*)\n(.*?)\n```'
        matches = re.finditer(code_block_pattern, content, re.DOTALL)
        
        for match in matches:
            language = match.group(1) or 'text'
            code = match.group(2)
            
            # Determine example type
            example_type = 'code'
            if language.lower() in ['http', 'curl', 'bash']:
                example_type = 'request'
            elif language.lower() in ['json', 'xml', 'yaml']:
                example_type = 'response'
            
            examples.append({
                'type': example_type,
                'language': language,
                'code': code,
                'description': self._get_example_context(content, match.start())
            })
        
        return examples
    
    def _get_example_context(self, content: str, position: int) -> str:
        """Get context description for a code example"""
        # Look backwards for the nearest header or descriptive text
        before_content = content[:position]
        lines = before_content.split('\n')
        
        # Find the most recent header
        for line in reversed(lines[-10:]):  # Check last 10 lines
            if line.strip().startswith('#'):
                return line.strip()[line.strip().index(' '):].strip()
            elif line.strip() and not line.strip().startswith('```'):
                return line.strip()[:100]  # First non-empty line
        
        return "Code example"
    
    def _extract_schemas(self, content: str) -> List[Dict[str, Any]]:
        """Extract schema/model information from markdown"""
        schemas = []
        
        # Look for common schema patterns
        patterns = [
            # Tables with field descriptions
            r'#{1,6}\s*(.*?(?:Schema|Model|Object|Response|Request).*?)\n(.*?)(?=\n#|\n```|\Z)',
            # JSON examples that might represent schemas
            r'```json\n(\{.*?"type".*?\})\n```',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, content, re.DOTALL | re.IGNORECASE)
            for match in matches:
                if len(match.groups()) >= 2:
                    name = match.group(1).strip()
                    content_block = match.group(2)
                    
                    schema = {
                        'name': name,
                        'type': 'object',
                        'description': self._extract_schema_description(content_block),
                        'properties': self._parse_properties_from_text(content_block)
                    }
                    schemas.append(schema)
        
        return schemas
    
    def _extract_schema_description(self, content_block: str) -> str:
        """Extract description from schema content block"""
        lines = content_block.split('\n')
        description_lines = []
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith('|') and not line.startswith('-'):
                description_lines.append(line)
            if len(description_lines) >= 3:  # Limit description
                break
        
        return ' '.join(description_lines)
    
    def _parse_properties_from_text(self, content_block: str) -> Dict[str, Any]:
        """Parse properties from markdown table or text"""
        properties = {}
        
        # Look for markdown tables
        table_rows = []
        for line in content_block.split('\n'):
            if '|' in line and not line.strip().startswith('|---'):
                table_rows.append(line)
        
        if len(table_rows) >= 2:  # Header + at least one data row
            headers = [h.strip() for h in table_rows[0].split('|') if h.strip()]
            
            for row in table_rows[1:]:
                cells = [c.strip() for c in row.split('|') if c.strip()]
                if len(cells) >= 2:
                    prop_name = cells[0]
                    prop_type = cells[1] if len(cells) > 1 else 'string'
                    prop_desc = cells[2] if len(cells) > 2 else ''
                    
                    properties[prop_name] = {
                        'type': prop_type,
                        'description': prop_desc
                    }
        
        return properties
    
    def _create_structured_content(self, content: str) -> str:
        """Create structured content optimized for vector search"""
        # Clean up markdown for better search
        structured = content
        
        # Convert headers to more searchable format
        structured = re.sub(r'^#{1,6}\s*(.*?)$', r'\1', structured, flags=re.MULTILINE)
        
        # Clean up code blocks but keep their content
        structured = re.sub(r'```(\w*)\n(.*?)\n```', r'Code example (\1): \2', structured, flags=re.DOTALL)
        
        # Clean up excessive whitespace
        structured = re.sub(r'\n{3,}', '\n\n', structured)
        
        return structured.strip()