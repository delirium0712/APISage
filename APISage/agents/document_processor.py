"""
Document Processor Agent for the LangChain Agent Orchestration System
Refactored from web scraper to handle multiple document formats
"""

import json
import hashlib
import os
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
import structlog

from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from playwright.async_api import async_playwright
import trafilatura
from tenacity import retry, stop_after_attempt, wait_exponential

from config.settings import AgentConfig, SystemConfig
from .parsers.base_parser import BaseDocumentParser
from .parsers.markdown_parser import MarkdownParser
from .parsers.openapi_parser import OpenAPIParser
from .parsers.postman_parser import PostmanParser


class DocumentProcessor:
    """Unified document processor for multiple formats"""
    
    def __init__(self, config: AgentConfig, system_config: SystemConfig, redis_client=None):
        self.config = config
        self.system_config = system_config
        self.redis = redis_client
        self.logger = structlog.get_logger(agent=config.name)
        self.ddgs = DDGS()
        
        # Initialize parsers based on configuration
        self.parsers: Dict[str, BaseDocumentParser] = self._initialize_parsers()
        
    def _initialize_parsers(self) -> Dict[str, BaseDocumentParser]:
        """Initialize document parsers based on system configuration"""
        parsers = {}
        
        if self.system_config.document_parsers.get("markdown", True):
            parsers["markdown"] = MarkdownParser()
            
        if self.system_config.document_parsers.get("openapi", True):
            parsers["openapi"] = OpenAPIParser()
            
        if self.system_config.document_parsers.get("postman", True):
            parsers["postman"] = PostmanParser()
            
        self.logger.info("initialized_parsers", 
                        parser_count=len(parsers),
                        available_parsers=list(parsers.keys()))
        
        return parsers
    
    async def process_document(self, source: Union[str, bytes, Path], 
                             source_type: str = "auto") -> Dict[str, Any]:
        """
        Process document from various sources and formats
        
        Args:
            source: Document source (URL, file path, or content)
            source_type: Type of source ("url", "file", "content", "auto")
        """
        try:
            # Determine source type if auto
            if source_type == "auto":
                source_type = self._detect_source_type(source)
            
            # Extract content based on source type
            if source_type == "url":
                content = await self._extract_from_url(source)
            elif source_type == "file":
                content = await self._extract_from_file(source)
            elif source_type == "content":
                content = source
            else:
                raise ValueError(f"Unsupported source type: {source_type}")
            
            # Detect document format and parse
            document_format = self._detect_document_format(content)
            parsed_content = await self._parse_document(content, document_format)
            
            # Add metadata
            result = {
                "source": str(source),
                "source_type": source_type,
                "format": document_format,
                "parsed_content": parsed_content,
                "processed_at": datetime.utcnow().isoformat(),
                "parser_used": document_format
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
                           parser=document_format)
            
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
        elif isinstance(source, str) and (source.startswith(('http://', 'https://'))):
            return "url"
        elif isinstance(source, bytes):
            return "content"
        else:
            return "content"
    
    def _detect_document_format(self, content: str) -> str:
        """Detect document format from content"""
        content_lower = content.lower()
        
        # Check for OpenAPI/Swagger
        if any(marker in content_lower for marker in ['openapi:', 'swagger:', '"swagger"']):
            return "openapi"
        
        # Check for Postman collection
        if any(marker in content_lower for marker in ['"info"', '"item"', '"request"']) and '"schema"' in content_lower:
            return "postman"
        
        # Check for Markdown
        if any(marker in content_lower for marker in ['# ', '## ', '### ', '**', '*', '```']):
            return "markdown"
        
        # Default to HTML/text
        return "html"
    
    async def _parse_document(self, content: str, format_type: str) -> Dict[str, Any]:
        """Parse document using appropriate parser"""
        if format_type in self.parsers:
            parser = self.parsers[format_type]
            return await parser.parse(content)
        else:
            # Fallback to basic HTML parsing
            return await self._parse_html_fallback(content)
    
    async def _parse_html_fallback(self, content: str) -> Dict[str, Any]:
        """Fallback HTML parser for unsupported formats"""
        soup = BeautifulSoup(content, 'html.parser')
        
        # Extract API documentation patterns
        api_endpoints = self._extract_api_patterns(soup)
        
        return {
            "title": soup.title.string if soup.title else "",
            "content": soup.get_text()[:5000],
            "api_endpoints": api_endpoints,
            "type": "html"
        }
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _extract_from_url(self, url: str) -> str:
        """Extract content from URL with caching and retry logic"""
        
        # Check cache
        cache_key = f"url:{hashlib.md5(url.encode()).hexdigest()}"
        if self.redis and self.config.cache_ttl > 0:
            cached = await self.redis.get(cache_key)
            if cached:
                self.logger.info("cache_hit", url=url)
                return json.loads(cached)["content"]
        
        try:
            # Try trafilatura first (more efficient)
            content = await self._scrape_with_trafilatura(url)
            
            # Cache result
            if self.redis and self.config.cache_ttl > 0:
                await self.redis.setex(
                    cache_key,
                    self.config.cache_ttl,
                    json.dumps({"content": content, "scraped_at": datetime.utcnow().isoformat()})
                )
            
            return content
            
        except Exception as e:
            self.logger.warning("trafilatura_failed", url=url, error=str(e))
            # Fallback to Playwright for JavaScript-heavy sites
            content = await self._scrape_with_playwright(url)
            
            # Cache result
            if self.redis and self.config.cache_ttl > 0:
                await self.redis.setex(
                    cache_key,
                    self.config.cache_ttl,
                    json.dumps({"content": content, "scraped_at": datetime.utcnow().isoformat()})
                )
            
            return content
    
    async def _extract_from_file(self, file_path: Union[str, Path]) -> str:
        """Extract content from file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # Try with different encoding
            with open(file_path, 'r', encoding='latin-1') as f:
                return f.read()
    
    async def _scrape_with_trafilatura(self, url: str) -> str:
        """Use Trafilatura for efficient content extraction"""
        downloaded = trafilatura.fetch_url(url)
        content = trafilatura.extract(downloaded, include_formatting=True)
        return content or downloaded
    
    async def _scrape_with_playwright(self, url: str) -> str:
        """Playwright for JavaScript-heavy sites"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, wait_until="networkidle")
            content = await page.content()
            await browser.close()
            return content
    
    async def search_web(self, query: str) -> List[Dict[str, str]]:
        """Search web using DuckDuckGo"""
        results = self.ddgs.text(query, max_results=5)
        return [{"title": r["title"], "url": r["link"], "snippet": r["body"]} for r in results]
    
    def _extract_api_patterns(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract API endpoint patterns from HTML"""
        endpoints = []
        
        for code_block in soup.find_all(['code', 'pre']):
            text = code_block.get_text()
            
            for method in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                if method in text:
                    lines = text.split('\n')
                    for line in lines:
                        if method in line and ('/' in line or 'http' in line):
                            endpoints.append({
                                "method": method,
                                "path": line.strip(),
                                "raw": line
                            })
        
        return endpoints[:50]
    
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
        return list(self.parsers.keys())
    
    def is_format_supported(self, format_type: str) -> bool:
        """Check if a document format is supported"""
        return format_type in self.parsers

