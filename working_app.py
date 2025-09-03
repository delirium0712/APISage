#!/usr/bin/env python3
"""
APISage - Working Interface
Focus: Actually functional UI with two tabs and global config
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
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("apisage")

# API Configuration
API_BASE_URL = os.getenv("APISAGE_URL", "http://localhost:8080")
TIMEOUT = 60

# Simple but effective dark theme
WORKING_CSS = """
/* Working Dark Theme */
:root {
    --bg-dark: #0d1117;
    --bg-light: #161b22;
    --bg-card: #21262d;
    --text-white: #f0f6fc;
    --text-gray: #7d8590;
    --blue: #58a6ff;
    --green: #3fb950;
    --red: #f85149;
    --border: #30363d;
}

body, .gradio-container {
    background: var(--bg-dark) !important;
    color: var(--text-white) !important;
}

.config-header {
    background: var(--bg-light);
    padding: 16px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 20px;
}

.metric-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 20px;
    margin: 10px 0;
}

.metric-value {
    font-size: 2rem;
    font-weight: bold;
    color: var(--blue);
}

.issue-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 16px;
    margin: 8px 0;
    border-left: 4px solid var(--red);
}

.chat-message {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 12px;
    margin: 8px 0;
}

.status-good { color: var(--green); }
.status-bad { color: var(--red); }
.status-ok { color: var(--blue); }
"""

# Global state
class AppState:
    def __init__(self):
        self.api_key = ""
        self.model = "gpt-4o-mini"
        self.server_connected = False
        self.last_spec = None
        
app_state = AppState()

def test_server_connection():
    """Test server connection"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def set_api_key(api_key):
    """Set and test API key"""
    if not api_key or not api_key.strip():
        return "❌ No API key provided"
    
    try:
        response = requests.post(f"{API_BASE_URL}/set-api-key", 
                               json={"api_key": api_key.strip()}, timeout=10)
        if response.status_code == 200:
            app_state.api_key = api_key.strip()
            os.environ["OPENAI_API_KEY"] = api_key.strip()
            app_state.server_connected = test_server_connection()
            return "✅ API key set successfully"
        else:
            return f"❌ Failed to set API key: {response.status_code}"
    except Exception as e:
        return f"❌ Error: {str(e)}"

def analyze_api(spec_file, focus_areas):
    """Analyze API specification"""
    if not spec_file:
        return "No file uploaded", "", ""
    
    if not app_state.server_connected:
        return "Server not connected. Set API key first.", "", ""
    
    try:
        # Read file
        if hasattr(spec_file, 'name'):
            with open(spec_file.name, 'r') as f:
                content = f.read()
        else:
            content = spec_file
        
        spec_data = json.loads(content)
        app_state.last_spec = spec_data
        
        # Call API with focus areas
        response = requests.post(f"{API_BASE_URL}/analyze", 
                               json={
                                   "openapi_spec": spec_data,
                                   "analysis_depth": "comprehensive",
                                   "focus_areas": focus_areas or []
                               }, timeout=TIMEOUT)
        
        if response.status_code == 200:
            result = response.json()
            
            # Create visual dashboard with scores
            dashboard = create_visual_dashboard(spec_data, result)
            
            # Get detailed analysis
            analysis = result.get("analysis", "Analysis completed")
            
            # Generate issues
            issues = create_issues_panel(spec_data, result)
            
            return dashboard, analysis, issues
        else:
            return f"Analysis failed: {response.status_code}", "", ""
            
    except json.JSONDecodeError:
        return "Invalid JSON file", "", ""
    except Exception as e:
        return f"Error: {str(e)}", "", ""

def extract_scores_from_analysis(analysis_text):
    """Extract scores from LLM analysis text"""
    scores = {
        'overall': 75,  # Default
        'completeness': 70,
        'documentation': 65,
        'security': 60,
        'usability': 70,
        'standards': 65
    }
    
    # Try to extract actual scores from analysis
    import re
    
    # Pattern for "Overall Score:** 30/100"
    overall_match = re.search(r'overall score:\*?\*?\s*(\d+)/100', analysis_text, re.IGNORECASE)
    if overall_match:
        scores['overall'] = int(overall_match.group(1))
    
    # Pattern for "- **Completeness:** 20/100"
    completeness_match = re.search(r'\*?\*?completeness:\*?\*?\s*(\d+)/100', analysis_text, re.IGNORECASE)
    if completeness_match:
        scores['completeness'] = int(completeness_match.group(1))
    
    documentation_match = re.search(r'\*?\*?documentation:\*?\*?\s*(\d+)/100', analysis_text, re.IGNORECASE)
    if documentation_match:
        scores['documentation'] = int(documentation_match.group(1))
    
    security_match = re.search(r'\*?\*?security:\*?\*?\s*(\d+)/100', analysis_text, re.IGNORECASE)
    if security_match:
        scores['security'] = int(security_match.group(1))
    
    usability_match = re.search(r'\*?\*?usability:\*?\*?\s*(\d+)/100', analysis_text, re.IGNORECASE)
    if usability_match:
        scores['usability'] = int(usability_match.group(1))
    
    standards_match = re.search(r'\*?\*?standards[^:]*:\*?\*?\s*(\d+)/100', analysis_text, re.IGNORECASE)
    if standards_match:
        scores['standards'] = int(standards_match.group(1))
    
    return scores

def create_visual_dashboard(spec_data, result):
    """Create visual dashboard with score visualization"""
    analysis_text = result.get("analysis", "")
    scores = extract_scores_from_analysis(analysis_text)
    
    endpoints = len(spec_data.get("paths", {}))
    schemas = len(spec_data.get("components", {}).get("schemas", {}))
    has_auth = bool(spec_data.get("components", {}).get("securitySchemes"))
    
    def get_color(score):
        if score >= 80: return "#3fb950"  # Green
        elif score >= 60: return "#d29922"  # Orange  
        else: return "#f85149"  # Red
    
    def get_status_text(score):
        if score >= 80: return "Excellent"
        elif score >= 60: return "Good"
        else: return "Needs Work"
    
    return f"""
    <!-- Overall Score Card -->
    <div style="background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px; padding: 24px; margin-bottom: 20px; text-align: center;">
        <h2 style="margin: 0 0 16px 0; color: var(--text-white);">Overall API Score</h2>
        <div style="display: inline-block; position: relative; width: 120px; height: 120px;">
            <svg width="120" height="120" style="transform: rotate(-90deg);">
                <circle cx="60" cy="60" r="50" fill="none" stroke="#30363d" stroke-width="8"/>
                <circle cx="60" cy="60" r="50" fill="none" stroke="{get_color(scores['overall'])}" 
                        stroke-width="8" stroke-dasharray="314" 
                        stroke-dashoffset="{314 - (314 * scores['overall'] / 100)}"
                        style="transition: stroke-dashoffset 1s ease;"/>
            </svg>
            <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); text-align: center;">
                <div style="font-size: 2rem; font-weight: bold; color: {get_color(scores['overall'])};">
                    {scores['overall']}
                </div>
                <div style="font-size: 0.8rem; color: var(--text-gray);">out of 100</div>
            </div>
        </div>
        <div style="margin-top: 12px; font-size: 1.1rem; color: {get_color(scores['overall'])}; font-weight: 600;">
            {get_status_text(scores['overall'])}
        </div>
    </div>

    <!-- Metric Cards Grid -->
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 20px;">
        
        <!-- Completeness -->
        <div class="metric-card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <h4 style="margin: 0; color: var(--text-white);">📋 Completeness</h4>
                <span style="color: {get_color(scores['completeness'])}; font-weight: bold; font-size: 1.2rem;">
                    {scores['completeness']}/100
                </span>
            </div>
            <div style="background: #30363d; height: 8px; border-radius: 4px; overflow: hidden;">
                <div style="background: {get_color(scores['completeness'])}; height: 100%; width: {scores['completeness']}%; 
                           transition: width 1s ease; border-radius: 4px;"></div>
            </div>
            <div style="margin-top: 8px; font-size: 0.85rem; color: var(--text-gray);">
                API coverage and endpoint completeness
            </div>
        </div>
        
        <!-- Documentation -->
        <div class="metric-card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <h4 style="margin: 0; color: var(--text-white);">📖 Documentation</h4>
                <span style="color: {get_color(scores['documentation'])}; font-weight: bold; font-size: 1.2rem;">
                    {scores['documentation']}/100
                </span>
            </div>
            <div style="background: #30363d; height: 8px; border-radius: 4px; overflow: hidden;">
                <div style="background: {get_color(scores['documentation'])}; height: 100%; width: {scores['documentation']}%; 
                           transition: width 1s ease; border-radius: 4px;"></div>
            </div>
            <div style="margin-top: 8px; font-size: 0.85rem; color: var(--text-gray);">
                Descriptions, examples, and clarity
            </div>
        </div>
        
        <!-- Security -->
        <div class="metric-card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <h4 style="margin: 0; color: var(--text-white);">🔒 Security</h4>
                <span style="color: {get_color(scores['security'])}; font-weight: bold; font-size: 1.2rem;">
                    {scores['security']}/100
                </span>
            </div>
            <div style="background: #30363d; height: 8px; border-radius: 4px; overflow: hidden;">
                <div style="background: {get_color(scores['security'])}; height: 100%; width: {scores['security']}%; 
                           transition: width 1s ease; border-radius: 4px;"></div>
            </div>
            <div style="margin-top: 8px; font-size: 0.85rem; color: var(--text-gray);">
                Authentication and authorization
            </div>
        </div>
        
        <!-- Usability -->
        <div class="metric-card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <h4 style="margin: 0; color: var(--text-white);">👥 Usability</h4>
                <span style="color: {get_color(scores['usability'])}; font-weight: bold; font-size: 1.2rem;">
                    {scores['usability']}/100
                </span>
            </div>
            <div style="background: #30363d; height: 8px; border-radius: 4px; overflow: hidden;">
                <div style="background: {get_color(scores['usability'])}; height: 100%; width: {scores['usability']}%; 
                           transition: width 1s ease; border-radius: 4px;"></div>
            </div>
            <div style="margin-top: 8px; font-size: 0.85rem; color: var(--text-gray);">
                Developer experience and ease of use
            </div>
        </div>
        
        <!-- Standards Compliance -->
        <div class="metric-card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <h4 style="margin: 0; color: var(--text-white);">✅ Standards</h4>
                <span style="color: {get_color(scores['standards'])}; font-weight: bold; font-size: 1.2rem;">
                    {scores['standards']}/100
                </span>
            </div>
            <div style="background: #30363d; height: 8px; border-radius: 4px; overflow: hidden;">
                <div style="background: {get_color(scores['standards'])}; height: 100%; width: {scores['standards']}%; 
                           transition: width 1s ease; border-radius: 4px;"></div>
            </div>
            <div style="margin-top: 8px; font-size: 0.85rem; color: var(--text-gray);">
                OpenAPI and REST compliance
            </div>
        </div>
        
        <!-- API Info -->
        <div class="metric-card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <h4 style="margin: 0; color: var(--text-white);">🔧 Resources</h4>
                <span style="color: var(--blue); font-weight: bold; font-size: 1.2rem;">
                    {endpoints + schemas}
                </span>
            </div>
            <div style="display: flex; justify-content: space-between; margin: 8px 0;">
                <span style="color: var(--text-gray); font-size: 0.85rem;">Endpoints:</span>
                <span style="color: var(--text-white); font-weight: 500;">{endpoints}</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin: 8px 0;">
                <span style="color: var(--text-gray); font-size: 0.85rem;">Models:</span>
                <span style="color: var(--text-white); font-weight: 500;">{schemas}</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin: 8px 0;">
                <span style="color: var(--text-gray); font-size: 0.85rem;">Auth:</span>
                <span style="color: {'var(--green)' if has_auth else 'var(--red)'}; font-weight: 500;">
                    {'✅ Yes' if has_auth else '❌ No'}
                </span>
            </div>
        </div>
    </div>
    """

def create_issues_panel(spec_data, result=None):
    """Create issues panel"""
    has_auth = bool(spec_data.get("components", {}).get("securitySchemes"))
    
    issues_html = ""
    
    if not has_auth:
        issues_html += """
        <div class="issue-card">
            <h4>🔒 Missing Authentication</h4>
            <p>API endpoints are not protected by authentication.</p>
            <p><strong>Priority:</strong> High</p>
            <p><strong>Fix:</strong> Add securitySchemes to components</p>
        </div>
        """
    
    # Check for missing error responses
    paths = spec_data.get("paths", {})
    missing_errors = False
    for path, methods in paths.items():
        for method, details in methods.items():
            responses = details.get("responses", {})
            if not any(code.startswith("4") or code.startswith("5") for code in responses.keys()):
                missing_errors = True
                break
        if missing_errors:
            break
    
    if missing_errors:
        issues_html += """
        <div class="issue-card">
            <h4>⚠️ Missing Error Responses</h4>
            <p>Endpoints missing 4xx/5xx error response definitions.</p>
            <p><strong>Priority:</strong> Medium</p>
            <p><strong>Fix:</strong> Add error response schemas</p>
        </div>
        """
    
    if not issues_html:
        issues_html = """
        <div class="metric-card">
            <div class="status-good">✅ No critical issues found</div>
        </div>
        """
    
    return issues_html

def chat_response(message, history):
    """Simple chat response"""
    if not message:
        return "", history
    
    if not app_state.last_spec:
        response = "Please upload and analyze an API specification first in the Evaluation tab."
    elif "auth" in message.lower():
        has_auth = bool(app_state.last_spec.get("components", {}).get("securitySchemes"))
        if has_auth:
            response = "Your API has authentication configured. The securitySchemes are defined in the components section."
        else:
            response = """Your API is missing authentication. Here's how to add it:

```yaml
components:
  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
      
security:
  - BearerAuth: []
```"""
    elif "error" in message.lower():
        response = """To add proper error handling, include these responses in your endpoints:

```yaml
responses:
  '400':
    description: Bad Request
    content:
      application/json:
        schema:
          type: object
          properties:
            error:
              type: string
  '401':
    description: Unauthorized
  '404':
    description: Not Found
  '500':
    description: Internal Server Error
```"""
    else:
        api_title = app_state.last_spec.get("info", {}).get("title", "your API")
        response = f"""I can help you with {api_title}. Ask me about:

- Authentication: "How do I add authentication?"
- Error handling: "What error responses should I add?"
- Security: "What security issues exist?"
- Documentation: "How can I improve documentation?"

What would you like to know?"""
    
    history.append([message, response])
    return "", history

def create_interface():
    """Create the working interface"""
    
    with gr.Blocks(css=WORKING_CSS, title="APISage - Working Interface") as app:
        
        # Global Configuration Header
        with gr.Row():
            gr.HTML("""
            <div class="config-header">
                <h2>🔧 APISage - API Analysis Platform</h2>
                <p>Configure your settings below, then use the tabs for analysis and chat.</p>
            </div>
            """)
        
        # Configuration Section
        with gr.Row():
            with gr.Column(scale=2):
                api_key_input = gr.Textbox(
                    label="OpenAI API Key",
                    placeholder="sk-...",
                    type="password"
                )
            with gr.Column(scale=1):
                model_select = gr.Dropdown(
                    choices=["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"],
                    value="gpt-4o-mini",
                    label="Model"
                )
            with gr.Column(scale=1):
                test_btn = gr.Button("🧪 Test Connection", variant="primary")
        
        # Status display
        status_display = gr.Markdown("❌ Not configured - Enter API key and test connection")
        
        # Main Tabs
        with gr.Tabs():
            # Tab 1: Evaluation
            with gr.Tab("📊 API Evaluation"):
                with gr.Row():
                    # Left: Upload and config
                    with gr.Column(scale=1):
                        gr.Markdown("### 📁 Upload Specification")
                        spec_file = gr.File(
                            label="OpenAPI Spec (.json/.yaml)",
                            file_types=[".json", ".yaml", ".yml"]
                        )
                        analyze_btn = gr.Button("🚀 Analyze API", variant="primary", size="lg")
                        
                        gr.Markdown("### ⚙️ Analysis Options")
                        analysis_focus = gr.CheckboxGroup(
                            choices=["security", "performance", "documentation", "completeness", "standards"],
                            value=["security", "completeness"],
                            label="Focus Areas"
                        )
                    
                    # Center: Dashboard
                    with gr.Column(scale=2):
                        gr.Markdown("### 📊 Metrics Dashboard")
                        dashboard_display = gr.HTML("""
                        <div style="text-align: center; padding: 40px; color: #7d8590;">
                            <h3>Upload API specification to see metrics</h3>
                        </div>
                        """)
                        
                        gr.Markdown("### 📋 Detailed Analysis")
                        analysis_display = gr.Markdown("Analysis results will appear here...")
                    
                    # Right: Issues
                    with gr.Column(scale=1):
                        gr.Markdown("### 🚨 Issues & Fixes")
                        issues_display = gr.HTML("""
                        <div style="text-align: center; padding: 20px; color: #7d8590;">
                            <p>Issues will appear here after analysis</p>
                        </div>
                        """)
            
            # Tab 2: Chat
            with gr.Tab("💬 API Assistant"):
                gr.Markdown("### 🤖 Chat with your API Documentation")
                gr.Markdown("Upload an API spec in the Evaluation tab first, then ask questions here.")
                
                chatbot = gr.Chatbot(height=400)
                
                with gr.Row():
                    chat_input = gr.Textbox(
                        placeholder="Ask about your API... (e.g., 'How do I add authentication?')",
                        scale=4
                    )
                    chat_btn = gr.Button("Send", variant="primary", scale=1)
        
        # Wire up functions
        
        # Test connection
        def test_connection(api_key, model):
            result = set_api_key(api_key)
            app_state.model = model
            return result
        
        test_btn.click(
            test_connection,
            inputs=[api_key_input, model_select],
            outputs=[status_display]
        )
        
        # Analysis
        analyze_btn.click(
            analyze_api,
            inputs=[spec_file, analysis_focus],
            outputs=[dashboard_display, analysis_display, issues_display]
        )
        
        # Chat
        chat_btn.click(
            chat_response,
            inputs=[chat_input, chatbot],
            outputs=[chat_input, chatbot]
        )
        
        chat_input.submit(
            chat_response,
            inputs=[chat_input, chatbot],
            outputs=[chat_input, chatbot]
        )
    
    return app

def main():
    """Launch the working interface"""
    print("🚀 APISage - Working Interface")
    print("=" * 40)
    
    # Check server
    if test_server_connection():
        print("✅ Server connected")
        app_state.server_connected = True
    else:
        print("⚠️ Server offline - configure API key")
    
    app = create_interface()
    
    print("\n📍 Interface: http://localhost:7860")
    print("🎯 Two tabs: Evaluation + Chat")
    print("⚙️ Configure API key first, then use tabs")
    
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True,
        inbrowser=True
    )

if __name__ == "__main__":
    main()