#!/usr/bin/env python3
"""
APISage RAG Interface - Dark Theme
Focus on RAG functionality for API documentation analysis and querying
"""

import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import gradio as gr
import requests

# Configure logging
def setup_logging():
    os.makedirs("logs", exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(f"logs/apisage_{datetime.now().strftime('%Y%m%d')}.log"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return logging.getLogger("apisage")

logger = setup_logging()

# API Configuration
API_BASE_URL = os.getenv("APISAGE_URL", "http://localhost:8080")
TIMEOUT = 120

# Dark Theme CSS
DARK_THEME_CSS = """
/* Dark Theme for APISage RAG Interface */
:root {
    /* Dark color palette */
    --bg-primary: #0f0f0f;
    --bg-secondary: #1a1a1a;
    --bg-elevated: #2d2d2d;
    --bg-card: #242424;
    
    /* Text colors */
    --text-primary: #ffffff;
    --text-secondary: #b4b4b4;
    --text-muted: #8a8a8a;
    --text-accent: #f0f0f0;
    
    /* Accent colors */
    --accent-blue: #4285f4;
    --accent-green: #34a853;
    --accent-red: #ea4335;
    --accent-orange: #fbbc04;
    --accent-purple: #9c27b0;
    
    /* Semantic colors */
    --critical: #ef4444;
    --critical-bg: #2d1b1b;
    --critical-border: #7c2d12;
    
    --warning: #f59e0b;
    --warning-bg: #2d2a1b;
    --warning-border: #a16207;
    
    --success: #10b981;
    --success-bg: #1b2d1f;
    --success-border: #166534;
    
    --info: #3b82f6;
    --info-bg: #1e293b;
    --info-border: #1e40af;
    
    /* Borders and shadows */
    --border-subtle: #404040;
    --border-default: #525252;
    --border-strong: #737373;
    
    --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.3);
    --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.4), 0 2px 4px -2px rgb(0 0 0 / 0.4);
    --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.5), 0 4px 6px -4px rgb(0 0 0 / 0.5);
}

/* Global reset and base styles */
html, body {
    margin: 0 !important;
    padding: 0 !important;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif !important;
    background: var(--bg-primary) !important;
    color: var(--text-primary) !important;
    line-height: 1.6 !important;
}

.gradio-container {
    max-width: none !important;
    width: 100% !important;
    margin: 0 !important;
    padding: 0 !important;
    background: var(--bg-primary) !important;
}

/* Header styling */
.app-header {
    background: linear-gradient(135deg, var(--bg-secondary) 0%, var(--bg-elevated) 100%);
    border-bottom: 2px solid var(--border-default);
    padding: 20px 32px;
    box-shadow: var(--shadow-md);
    display: flex;
    justify-content: space-between;
    align-items: center;
    position: sticky;
    top: 0;
    z-index: 1000;
}

.brand-section {
    display: flex;
    align-items: center;
    gap: 16px;
}

.app-logo {
    width: 48px;
    height: 48px;
    background: linear-gradient(135deg, var(--accent-blue) 0%, var(--accent-purple) 100%);
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-weight: 800;
    font-size: 1.5rem;
    box-shadow: var(--shadow-md);
}

.brand-info h1 {
    margin: 0;
    font-size: 1.75rem;
    font-weight: 700;
    color: var(--text-primary);
    background: linear-gradient(135deg, var(--accent-blue), var(--accent-purple));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.brand-info p {
    margin: 0;
    font-size: 0.9rem;
    color: var(--text-secondary);
}

.header-status {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 16px;
    background: var(--bg-elevated);
    border: 1px solid var(--border-subtle);
    border-radius: 8px;
    font-size: 0.875rem;
    color: var(--text-secondary);
    box-shadow: var(--shadow-sm);
}

.status-indicator {
    width: 8px;
    height: 8px;
    background: var(--success);
    border-radius: 50%;
    animation: pulse 2s infinite;
}

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}

/* Main layout */
.main-container {
    display: grid;
    grid-template-columns: 350px 1fr 400px;
    gap: 24px;
    padding: 24px;
    min-height: calc(100vh - 120px);
}

/* Left panel - RAG configuration */
.rag-config-panel {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: 16px;
    padding: 24px;
    height: fit-content;
    box-shadow: var(--shadow-md);
}

.config-section {
    margin-bottom: 24px;
    padding-bottom: 20px;
    border-bottom: 1px solid var(--border-subtle);
}

.config-section:last-child {
    margin-bottom: 0;
    border-bottom: none;
}

.section-title {
    font-size: 0.95rem;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 8px;
}

.section-icon {
    font-size: 1.2rem;
}

.form-group {
    margin-bottom: 16px;
}

.form-label {
    display: block;
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--text-secondary);
    margin-bottom: 8px;
}

/* Center panel - RAG interface */
.rag-interface {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: 16px;
    box-shadow: var(--shadow-md);
    overflow: hidden;
    display: flex;
    flex-direction: column;
}

.rag-header {
    background: var(--bg-elevated);
    border-bottom: 1px solid var(--border-subtle);
    padding: 24px;
}

.rag-title {
    margin: 0;
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--text-primary);
    background: linear-gradient(135deg, var(--accent-blue), var(--accent-green));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.rag-subtitle {
    margin: 8px 0 0 0;
    font-size: 0.9rem;
    color: var(--text-secondary);
}

.rag-content {
    flex: 1;
    padding: 24px;
    display: flex;
    flex-direction: column;
    gap: 20px;
}

/* Query interface */
.query-interface {
    background: var(--bg-elevated);
    border: 1px solid var(--border-subtle);
    border-radius: 12px;
    padding: 20px;
}

.query-title {
    font-size: 1.1rem;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 8px;
}

.query-input {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: 8px;
    padding: 16px;
    color: var(--text-primary);
    font-size: 0.9rem;
    width: 100%;
    resize: vertical;
    min-height: 120px;
    transition: border-color 0.2s ease;
}

.query-input:focus {
    outline: none;
    border-color: var(--accent-blue);
    box-shadow: 0 0 0 3px rgba(66, 133, 244, 0.1);
}

/* Response display */
.response-display {
    background: var(--bg-elevated);
    border: 1px solid var(--border-subtle);
    border-radius: 12px;
    padding: 20px;
    min-height: 300px;
    flex: 1;
}

.response-title {
    font-size: 1.1rem;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 8px;
}

.response-content {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: 8px;
    padding: 16px;
    color: var(--text-secondary);
    font-size: 0.9rem;
    line-height: 1.6;
    white-space: pre-wrap;
    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
    overflow-y: auto;
    max-height: 400px;
}

/* Right panel - Context & docs */
.context-panel {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: 16px;
    box-shadow: var(--shadow-md);
    height: fit-content;
}

.context-header {
    background: var(--bg-elevated);
    border-bottom: 1px solid var(--border-subtle);
    padding: 20px 24px;
    border-radius: 16px 16px 0 0;
}

.context-title {
    margin: 0;
    font-size: 1.2rem;
    font-weight: 700;
    color: var(--text-primary);
}

.context-subtitle {
    margin: 4px 0 0 0;
    font-size: 0.85rem;
    color: var(--text-secondary);
}

.context-content {
    padding: 20px;
}

/* Document cards */
.doc-card {
    background: var(--bg-elevated);
    border: 1px solid var(--border-subtle);
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 12px;
    transition: all 0.2s ease;
}

.doc-card:hover {
    border-color: var(--accent-blue);
    box-shadow: var(--shadow-md);
}

.doc-card:last-child {
    margin-bottom: 0;
}

.doc-card-title {
    font-size: 0.9rem;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 8px;
}

.doc-card-content {
    font-size: 0.8rem;
    color: var(--text-secondary);
    line-height: 1.5;
}

.doc-card-meta {
    margin-top: 8px;
    padding-top: 8px;
    border-top: 1px solid var(--border-subtle);
    font-size: 0.75rem;
    color: var(--text-muted);
}

/* Buttons */
.btn {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 12px 20px;
    font-size: 0.9rem;
    font-weight: 600;
    text-decoration: none;
    border-radius: 8px;
    border: 1px solid;
    cursor: pointer;
    transition: all 0.2s ease;
    background: none;
    outline: none;
}

.btn-primary {
    background: linear-gradient(135deg, var(--accent-blue), var(--accent-purple));
    border-color: var(--accent-blue);
    color: white;
    box-shadow: var(--shadow-sm);
}

.btn-primary:hover {
    transform: translateY(-1px);
    box-shadow: var(--shadow-md);
}

.btn-secondary {
    background: var(--bg-elevated);
    border-color: var(--border-default);
    color: var(--text-secondary);
}

.btn-secondary:hover {
    background: var(--bg-card);
    border-color: var(--border-strong);
    color: var(--text-primary);
}

/* Loading states */
.loading {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 40px;
    color: var(--text-muted);
}

.loading-spinner {
    width: 24px;
    height: 24px;
    border: 2px solid var(--border-subtle);
    border-radius: 50%;
    border-top-color: var(--accent-blue);
    animation: spin 1s ease-in-out infinite;
    margin-right: 12px;
}

@keyframes spin {
    to { transform: rotate(360deg); }
}

/* Empty states */
.empty-state {
    text-align: center;
    padding: 40px 20px;
    color: var(--text-muted);
}

.empty-state-icon {
    font-size: 3rem;
    margin-bottom: 16px;
    opacity: 0.5;
}

.empty-state h3 {
    margin: 0 0 8px 0;
    font-size: 1.1rem;
    color: var(--text-secondary);
}

.empty-state p {
    margin: 0;
    font-size: 0.9rem;
    line-height: 1.5;
}

/* Scrollbar styling */
::-webkit-scrollbar {
    width: 8px;
    height: 8px;
}

::-webkit-scrollbar-track {
    background: var(--bg-secondary);
}

::-webkit-scrollbar-thumb {
    background: var(--border-default);
    border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
    background: var(--border-strong);
}

/* Responsive design */
@media (max-width: 1200px) {
    .main-container {
        grid-template-columns: 300px 1fr;
        grid-template-areas: 
            "config interface"
            "context context";
    }
    
    .rag-config-panel { grid-area: config; }
    .rag-interface { grid-area: interface; }
    .context-panel { 
        grid-area: context;
        grid-column: 1 / -1;
    }
}

@media (max-width: 768px) {
    .main-container {
        grid-template-columns: 1fr;
        gap: 16px;
        padding: 16px;
    }
    
    .app-header {
        padding: 16px;
        flex-direction: column;
        text-align: center;
        gap: 12px;
    }
}

/* Focus styles for accessibility */
button:focus,
input:focus,
textarea:focus,
select:focus {
    outline: 2px solid var(--accent-blue);
    outline-offset: 2px;
}

/* High contrast mode support */
@media (prefers-contrast: high) {
    :root {
        --border-subtle: #ffffff;
        --border-default: #ffffff;
        --text-muted: #ffffff;
    }
}
"""

# Utility Functions
def fetch_available_models():
    """Fetch available models from the API"""
    try:
        response = requests.get(f"{API_BASE_URL}/models", timeout=10)
        if response.status_code == 200:
            models_data = response.json()
            models_list = models_data.get("models", ["gpt-4o", "gpt-4o-mini"])
            return models_list, models_list[0] if models_list else "gpt-4o"
        else:
            logger.warning(f"Failed to fetch models: {response.status_code}")
            return ["gpt-4o", "gpt-4o-mini"], "gpt-4o"
    except Exception as e:
        logger.error(f"Error fetching models: {str(e)}")
        return ["gpt-4o", "gpt-4o-mini"], "gpt-4o"

def check_server_connection():
    """Check if the APISage server is available"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            health_data = response.json()
            logger.info(f"Connected to APISage server: {health_data}")
            return True
        else:
            logger.warning(f"Server health check failed: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"Cannot connect to APISage server: {e}")
        return False

def analyze_api_simple(spec_file, progress=gr.Progress()):
    """Simple API analysis for basic evaluation"""
    
    if spec_file is None:
        return "Please upload an OpenAPI specification file to begin analysis."
    
    try:
        progress(0.1, desc="Processing file...")
        
        # Read and parse the spec file
        if hasattr(spec_file, 'name'):
            with open(spec_file.name, 'r', encoding='utf-8') as f:
                spec_content = f.read()
        else:
            spec_content = spec_file
            
        spec_data = json.loads(spec_content)
        
        progress(0.5, desc="Running analysis...")
        
        # Call the basic analyze endpoint
        response = requests.post(
            f"{API_BASE_URL}/analyze",
            json={
                "openapi_spec": spec_data,
                "analysis_depth": "quick",
                "focus_areas": ["completeness", "documentation"]
            },
            timeout=TIMEOUT
        )
        
        if response.status_code == 200:
            result = response.json()
            progress(1.0, desc="Analysis complete!")
            return result.get("analysis", "Analysis completed successfully")
        else:
            return f"Analysis failed: {response.status_code} - {response.text}"
            
    except json.JSONDecodeError:
        return "Error: Invalid JSON format in specification file"
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        return f"Error: {str(e)}"

def rag_query(query: str, context_docs: List[str] = None) -> str:
    """Process RAG query against API documentation"""
    
    if not query.strip():
        return "Please enter a question about your API documentation."
    
    # TODO: Implement actual RAG functionality
    # This is a placeholder that will need to be connected to a proper RAG system
    
    # Simulate RAG response based on query
    if "authentication" in query.lower():
        return """Based on your API documentation:

**Authentication Methods:**
- Bearer Token authentication is commonly used
- API Key authentication for simpler access
- OAuth 2.0 for third-party integrations

**Implementation Recommendations:**
1. Use JWT tokens for stateless authentication
2. Implement proper token expiration
3. Add refresh token mechanism
4. Secure token storage practices

**Code Example:**
```yaml
securitySchemes:
  BearerAuth:
    type: http
    scheme: bearer
    bearerFormat: JWT
```

Would you like more details about implementing any of these authentication methods?"""
    
    elif "error" in query.lower():
        return """Based on your API documentation:

**Error Handling Best Practices:**
- Use standard HTTP status codes
- Provide clear error messages
- Include error codes for programmatic handling
- Document all possible errors

**Common Error Responses:**
- 400 Bad Request - Invalid input
- 401 Unauthorized - Authentication required
- 403 Forbidden - Insufficient permissions
- 404 Not Found - Resource not found
- 500 Internal Server Error - Server issues

**Example Error Response:**
```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "The request body is missing required field 'name'",
    "details": {
      "field": "name",
      "expected_type": "string"
    }
  }
}
```"""
    
    elif "endpoint" in query.lower() or "api" in query.lower():
        return """Based on your API documentation analysis:

**Available Endpoints:**
- GET /users - List all users
- POST /users - Create new user
- GET /users/{id} - Get specific user
- PUT /users/{id} - Update user
- DELETE /users/{id} - Delete user

**Missing Endpoints (Recommendations):**
- GET /users/search - Search users by criteria
- POST /users/batch - Bulk operations
- GET /users/{id}/profile - User profile data

**Endpoint Design Best Practices:**
1. Use proper HTTP methods
2. Implement consistent URL patterns
3. Add pagination for list endpoints
4. Include filtering and sorting options

Would you like me to generate OpenAPI specifications for any missing endpoints?"""
    
    else:
        # Generic response for other queries
        return f"""I understand you're asking about: "{query}"

Based on your API documentation, I can help you with:

**Available Information:**
- API structure and endpoints
- Authentication and security
- Request/response formats
- Error handling patterns
- Best practices and recommendations

**Common Questions I Can Answer:**
- "How do I authenticate with this API?"
- "What error codes does this API return?"
- "What endpoints are available?"
- "How do I implement pagination?"
- "What's missing from this API specification?"

Please ask a more specific question, and I'll provide detailed information from your API documentation."""

def update_context_docs(spec_file):
    """Update context documents based on uploaded spec"""
    
    if spec_file is None:
        return create_empty_context()
    
    try:
        # Read and parse the spec file
        if hasattr(spec_file, 'name'):
            with open(spec_file.name, 'r', encoding='utf-8') as f:
                spec_content = f.read()
        else:
            spec_content = spec_file
            
        spec_data = json.loads(spec_content)
        
        # Extract context information
        api_title = spec_data.get('info', {}).get('title', 'Unknown API')
        api_version = spec_data.get('info', {}).get('version', '1.0.0')
        paths_count = len(spec_data.get('paths', {}))
        
        context_html = f"""
        <div class="doc-card">
            <div class="doc-card-title">📋 API Specification</div>
            <div class="doc-card-content">
                <strong>{api_title}</strong><br>
                Version: {api_version}<br>
                Endpoints: {paths_count}
            </div>
            <div class="doc-card-meta">Source: OpenAPI 3.0 Specification</div>
        </div>
        
        <div class="doc-card">
            <div class="doc-card-title">🔍 Available Queries</div>
            <div class="doc-card-content">
                • Authentication methods<br>
                • Error handling patterns<br>
                • Available endpoints<br>
                • Missing functionality<br>
                • Best practices
            </div>
            <div class="doc-card-meta">Ask questions about your API</div>
        </div>
        
        <div class="doc-card">
            <div class="doc-card-title">💡 Suggestions</div>
            <div class="doc-card-content">
                Try asking:<br>
                "How do I authenticate?"<br>
                "What errors can occur?"<br>
                "What endpoints exist?"
            </div>
            <div class="doc-card-meta">Example queries</div>
        </div>
        """
        
        return context_html
        
    except Exception as e:
        return f"<div class='doc-card'><div class='doc-card-title'>❌ Error</div><div class='doc-card-content'>Failed to process specification: {str(e)}</div></div>"

def create_empty_context():
    """Create empty context display"""
    return """
    <div class="empty-state">
        <div class="empty-state-icon">📚</div>
        <h3>No Documentation Loaded</h3>
        <p>Upload an OpenAPI specification to enable RAG queries and get contextual assistance.</p>
    </div>
    """

def create_interface():
    """Create the RAG-focused interface with dark theme"""
    logger.info("Creating RAG-focused interface with dark theme")
    
    # Fetch available models
    models_list, default_model = fetch_available_models()
    logger.info(f"Available models: {models_list}")
    
    with gr.Blocks(
        css=DARK_THEME_CSS,
        title="APISage RAG - API Documentation Assistant",
        theme=gr.themes.Base()
    ) as interface:
        
        # Header
        gr.HTML(f"""
        <div class="app-header">
            <div class="brand-section">
                <div class="app-logo">🔍</div>
                <div class="brand-info">
                    <h1>APISage RAG</h1>
                    <p>AI-Powered API Documentation Assistant</p>
                </div>
            </div>
            <div class="header-status">
                <div class="status-indicator"></div>
                RAG System Ready
            </div>
        </div>
        """)
        
        # Main container
        with gr.Row():
            with gr.Column(scale=1, min_width=350):
                # RAG Configuration Panel
                gr.HTML('<div class="section-title"><span class="section-icon">⚙️</span> RAG Configuration</div>')
                
                with gr.Group():
                    spec_file = gr.File(
                        label="📄 API Specification",
                        file_types=[".json", ".yaml", ".yml"],
                        file_count="single"
                    )
                    
                    model_selector = gr.Dropdown(
                        choices=models_list,
                        value=default_model,
                        label="🤖 AI Model"
                    )
                    
                    analysis_btn = gr.Button(
                        "📊 Quick Analysis",
                        variant="secondary",
                        size="lg"
                    )
                
                gr.HTML('<div style="margin: 20px 0;"><div class="section-title"><span class="section-icon">🎯</span> RAG Settings</div></div>')
                
                with gr.Group():
                    rag_mode = gr.Radio(
                        choices=["conversational", "analytical", "documentation"],
                        value="conversational",
                        label="🎭 Response Mode"
                    )
                    
                    max_context = gr.Slider(
                        minimum=1000,
                        maximum=8000,
                        value=4000,
                        step=500,
                        label="📏 Max Context Length"
                    )
            
            with gr.Column(scale=2, min_width=600):
                # RAG Interface
                gr.HTML("""
                <div class="rag-header">
                    <h2 class="rag-title">🤖 Ask Questions About Your API</h2>
                    <p class="rag-subtitle">Upload your OpenAPI spec and ask questions to get intelligent insights</p>
                </div>
                """)
                
                with gr.Group():
                    # Query Interface
                    gr.HTML('<div class="query-title"><span class="section-icon">💬</span> Your Question</div>')
                    
                    query_input = gr.Textbox(
                        placeholder="Ask anything about your API documentation...\n\nExamples:\n• How do I authenticate with this API?\n• What error codes are returned?\n• What endpoints are available?\n• What's missing from this API?",
                        lines=4,
                        elem_classes=["query-input"]
                    )
                    
                    ask_btn = gr.Button(
                        "🔍 Ask Question",
                        variant="primary",
                        size="lg"
                    )
                
                # Response Display
                gr.HTML('<div class="response-title"><span class="section-icon">💡</span> AI Response</div>')
                
                response_output = gr.Markdown(
                    "Upload an API specification and ask a question to get started!",
                    elem_classes=["response-content"]
                )
            
            with gr.Column(scale=1, min_width=400):
                # Context Panel
                gr.HTML("""
                <div class="context-header">
                    <h3 class="context-title">📚 Context & Documentation</h3>
                    <p class="context-subtitle">Available information from your API spec</p>
                </div>
                """)
                
                context_display = gr.HTML(create_empty_context())
        
        # Quick Analysis Output (initially hidden)
        analysis_output = gr.Markdown(
            "Analysis results will appear here...",
            visible=False,
            elem_classes=["response-content"]
        )
        
        # Wire up the functionality
        ask_btn.click(
            fn=rag_query,
            inputs=[query_input],
            outputs=[response_output]
        )
        
        analysis_btn.click(
            fn=analyze_api_simple,
            inputs=[spec_file],
            outputs=[analysis_output]
        ).then(
            lambda: gr.update(visible=True),
            outputs=[analysis_output]
        )
        
        spec_file.change(
            fn=update_context_docs,
            inputs=[spec_file],
            outputs=[context_display]
        )
        
        # Footer
        gr.HTML("""
        <div style="margin-top: 2rem; padding: 1.5rem; background: var(--bg-elevated); border-radius: 12px; text-align: center; font-size: 0.875rem; color: var(--text-muted); border: 1px solid var(--border-subtle);">
            <strong>APISage RAG v1.0</strong> | 
            <span style="color: var(--accent-blue);">🤖 AI-Powered</span> | 
            <span style="color: var(--accent-green);">📚 RAG-Enhanced</span> | 
            <span id="system-status">🟢 System Ready</span>
        </div>
        """)
    
    return interface

def main():
    """Launch the RAG-focused interface"""
    logger.info("Starting APISage RAG Interface v1.0")
    
    # Check server connectivity
    if not check_server_connection():
        logger.warning("APISage server is not available - basic RAG functionality will still work")
        print("⚠️  Warning: APISage server (localhost:8080) is not available")
        print("   Basic RAG functionality will still work with simulated responses")
        print("   For full functionality, start server with: poetry run python -m api.main")
    else:
        logger.info("✅ Successfully connected to APISage server")
        print("✅ Connected to APISage server")
    
    interface = create_interface()
    
    try:
        print("\n🚀 Launching APISage RAG Interface...")
        print("📍 Interface: http://localhost:7860")
        print("🔗 Server API: http://localhost:8080")
        print("🎯 Focus: RAG functionality for API documentation")
        
        interface.launch(
            server_name="0.0.0.0",
            server_port=7860,
            share=False,
            show_error=True,
            quiet=False,
            inbrowser=True
        )
    except Exception as e:
        logger.error(f"Failed to launch interface: {e}")
        raise

if __name__ == "__main__":
    main()