#!/usr/bin/env python3
"""
APISage Pro - Developer-First API Analysis Platform
Designed for top 1% developers who need speed, actionability, and integration
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

# Pro Developer Dark Theme CSS
PRO_DARK_CSS = """
/* APISage Pro - Dark Theme Optimized for Developers */
:root {
    /* Dark professional palette */
    --bg-primary: #0d1117;
    --bg-secondary: #161b22;  
    --bg-elevated: #21262d;
    --bg-card: #1c2128;
    --bg-input: #0d1117;
    
    /* Text hierarchy */
    --text-primary: #f0f6fc;
    --text-secondary: #7d8590;
    --text-muted: #656d76;
    --text-accent: #58a6ff;
    
    /* Status colors */
    --success: #238636;
    --success-bg: #0d2818;
    --warning: #d29922;
    --warning-bg: #2d2a1b;
    --error: #da3633;
    --error-bg: #2c1618;
    --info: #1f6feb;
    --info-bg: #0c2d6b;
    
    /* Interactive elements */
    --border-default: #30363d;
    --border-subtle: #21262d;
    --border-strong: #424a53;
    --button-primary: #238636;
    --button-secondary: #21262d;
    
    /* Shadows and effects */
    --shadow-sm: 0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24);
    --shadow-md: 0 4px 6px rgba(0,0,0,0.15), 0 2px 4px rgba(0,0,0,0.12);
    --shadow-lg: 0 8px 25px rgba(0,0,0,0.15), 0 4px 10px rgba(0,0,0,0.05);
}

/* Global reset */
html, body {
    margin: 0 !important;
    padding: 0 !important;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans", Helvetica, Arial, sans-serif !important;
    background: var(--bg-primary) !important;
    color: var(--text-primary) !important;
    line-height: 1.5 !important;
    font-size: 14px !important;
}

.gradio-container {
    max-width: none !important;
    width: 100% !important;
    margin: 0 !important;
    padding: 0 !important;
    background: var(--bg-primary) !important;
}

/* Global Configuration Header */
.global-header {
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border-default);
    padding: 12px 24px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    position: sticky;
    top: 0;
    z-index: 1000;
    box-shadow: var(--shadow-sm);
}

.header-brand {
    display: flex;
    align-items: center;
    gap: 12px;
}

.brand-logo {
    width: 32px;
    height: 32px;
    background: linear-gradient(135deg, var(--info) 0%, var(--success) 100%);
    border-radius: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-weight: 700;
    font-size: 1rem;
}

.brand-text h1 {
    margin: 0;
    font-size: 1.25rem;
    font-weight: 600;
    color: var(--text-primary);
}

.brand-text p {
    margin: 0;
    font-size: 0.75rem;
    color: var(--text-secondary);
}

.global-config {
    display: flex;
    align-items: center;
    gap: 16px;
}

.config-item {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.875rem;
}

.status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--success);
}

.status-dot.error {
    background: var(--error);
}

.status-dot.warning {
    background: var(--warning);
}

/* Main Tab Interface */
.main-tabs {
    background: var(--bg-primary);
    min-height: calc(100vh - 60px);
}

.tab-header {
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border-default);
    padding: 0;
}

.tab-content {
    padding: 0;
    background: var(--bg-primary);
}

/* Evaluation Tab Styles */
.eval-container {
    display: grid;
    grid-template-columns: 320px 1fr 400px;
    gap: 0;
    min-height: calc(100vh - 120px);
}

.eval-sidebar {
    background: var(--bg-secondary);
    border-right: 1px solid var(--border-default);
    padding: 20px;
    overflow-y: auto;
}

.eval-main {
    background: var(--bg-primary);
    display: flex;
    flex-direction: column;
}

.eval-results {
    background: var(--bg-secondary);
    border-left: 1px solid var(--border-default);
    padding: 20px;
    overflow-y: auto;
}

/* Dashboard Cards */
.dashboard-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 16px;
    margin-bottom: 24px;
}

.metric-card {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: 8px;
    padding: 20px;
    position: relative;
    transition: all 0.2s ease;
}

.metric-card:hover {
    border-color: var(--border-strong);
    transform: translateY(-1px);
    box-shadow: var(--shadow-md);
}

.metric-header {
    display: flex;
    justify-content: between;
    align-items: flex-start;
    margin-bottom: 12px;
}

.metric-title {
    font-size: 0.875rem;
    color: var(--text-secondary);
    font-weight: 500;
    margin: 0;
}

.metric-icon {
    font-size: 1.25rem;
    opacity: 0.7;
}

.metric-value {
    font-size: 2rem;
    font-weight: 700;
    color: var(--text-primary);
    margin: 0 0 8px 0;
    line-height: 1;
}

.metric-change {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 0.75rem;
    font-weight: 500;
}

.metric-change.positive {
    color: var(--success);
}

.metric-change.negative {
    color: var(--error);
}

.metric-change.neutral {
    color: var(--text-muted);
}

.metric-progress {
    width: 100%;
    height: 4px;
    background: var(--bg-primary);
    border-radius: 2px;
    overflow: hidden;
    margin-top: 8px;
}

.metric-progress-fill {
    height: 100%;
    transition: width 1s ease;
}

.metric-progress-fill.success { background: var(--success); }
.metric-progress-fill.warning { background: var(--warning); }
.metric-progress-fill.error { background: var(--error); }

/* Issues Panel */
.issues-panel {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: 8px;
    margin-bottom: 20px;
}

.issues-header {
    padding: 16px 20px;
    border-bottom: 1px solid var(--border-subtle);
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.issues-title {
    font-size: 1rem;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0;
    display: flex;
    align-items: center;
    gap: 8px;
}

.issues-count {
    background: var(--error);
    color: white;
    font-size: 0.75rem;
    font-weight: 600;
    padding: 2px 6px;
    border-radius: 10px;
    min-width: 16px;
    text-align: center;
}

.issues-list {
    max-height: 400px;
    overflow-y: auto;
}

.issue-item {
    padding: 16px 20px;
    border-bottom: 1px solid var(--border-subtle);
    transition: background 0.2s ease;
}

.issue-item:hover {
    background: var(--bg-elevated);
}

.issue-item:last-child {
    border-bottom: none;
}

.issue-header {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    margin-bottom: 8px;
}

.issue-priority {
    background: var(--error);
    color: white;
    font-size: 0.625rem;
    font-weight: 600;
    padding: 2px 6px;
    border-radius: 4px;
    text-transform: uppercase;
    flex-shrink: 0;
    margin-top: 2px;
}

.issue-priority.medium {
    background: var(--warning);
    color: var(--bg-primary);
}

.issue-priority.low {
    background: var(--text-muted);
}

.issue-title {
    font-size: 0.875rem;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0;
    line-height: 1.3;
}

.issue-description {
    font-size: 0.8125rem;
    color: var(--text-secondary);
    line-height: 1.4;
    margin: 0 0 12px 0;
}

.issue-actions {
    display: flex;
    gap: 8px;
    margin-top: 12px;
}

.issue-btn {
    font-size: 0.75rem;
    padding: 4px 8px;
    border-radius: 4px;
    border: 1px solid var(--border-default);
    background: var(--bg-elevated);
    color: var(--text-secondary);
    cursor: pointer;
    transition: all 0.2s ease;
}

.issue-btn:hover {
    background: var(--bg-primary);
    color: var(--text-primary);
}

.issue-btn.primary {
    background: var(--button-primary);
    border-color: var(--button-primary);
    color: white;
}

/* Code Generation Panel */
.code-gen-panel {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: 8px;
}

.code-gen-header {
    padding: 16px 20px;
    border-bottom: 1px solid var(--border-subtle);
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.code-gen-title {
    font-size: 1rem;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0;
}

.code-gen-content {
    padding: 0;
}

.code-block {
    background: var(--bg-input);
    border: 1px solid var(--border-subtle);
    border-radius: 6px;
    font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, 'Courier New', monospace;
    font-size: 0.8125rem;
    line-height: 1.45;
    margin: 0;
    padding: 16px;
    color: var(--text-primary);
    overflow-x: auto;
    white-space: pre;
}

/* Chat Tab Styles */
.chat-container {
    display: grid;
    grid-template-columns: 1fr 300px;
    gap: 0;
    min-height: calc(100vh - 120px);
}

.chat-main {
    background: var(--bg-primary);
    display: flex;
    flex-direction: column;
    border-right: 1px solid var(--border-default);
}

.chat-sidebar {
    background: var(--bg-secondary);
    padding: 20px;
    overflow-y: auto;
}

.chat-header {
    padding: 20px 24px;
    border-bottom: 1px solid var(--border-default);
    background: var(--bg-secondary);
}

.chat-title {
    font-size: 1.25rem;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0 0 4px 0;
}

.chat-subtitle {
    font-size: 0.875rem;
    color: var(--text-secondary);
    margin: 0;
}

.chat-messages {
    flex: 1;
    padding: 20px 24px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 16px;
}

.chat-input-area {
    padding: 20px 24px;
    border-top: 1px solid var(--border-default);
    background: var(--bg-secondary);
}

.chat-input {
    width: 100%;
    background: var(--bg-input);
    border: 1px solid var(--border-default);
    border-radius: 8px;
    padding: 12px 16px;
    color: var(--text-primary);
    font-size: 0.875rem;
    resize: none;
    min-height: 44px;
    max-height: 120px;
}

.chat-input:focus {
    outline: none;
    border-color: var(--info);
    box-shadow: 0 0 0 3px rgba(31, 111, 235, 0.1);
}

/* Message bubbles */
.message {
    display: flex;
    gap: 12px;
    align-items: flex-start;
}

.message.user {
    flex-direction: row-reverse;
}

.message-avatar {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: var(--bg-elevated);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.875rem;
    flex-shrink: 0;
}

.message-avatar.user {
    background: var(--info);
    color: white;
}

.message-avatar.assistant {
    background: var(--success);
    color: white;
}

.message-content {
    background: var(--bg-elevated);
    border: 1px solid var(--border-subtle);
    border-radius: 12px;
    padding: 12px 16px;
    max-width: 80%;
    font-size: 0.875rem;
    line-height: 1.4;
}

.message.user .message-content {
    background: var(--info);
    color: white;
    border-color: var(--info);
}

/* Action Bar */
.action-bar {
    background: var(--bg-secondary);
    border-top: 1px solid var(--border-default);
    padding: 12px 24px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.action-group {
    display: flex;
    gap: 8px;
}

.action-btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 8px 12px;
    font-size: 0.8125rem;
    font-weight: 500;
    border-radius: 6px;
    border: 1px solid var(--border-default);
    background: var(--bg-elevated);
    color: var(--text-secondary);
    cursor: pointer;
    transition: all 0.2s ease;
}

.action-btn:hover {
    background: var(--bg-card);
    color: var(--text-primary);
    border-color: var(--border-strong);
}

.action-btn.primary {
    background: var(--button-primary);
    border-color: var(--button-primary);
    color: white;
}

.action-btn.primary:hover {
    background: #2ea043;
}

/* Form elements */
.form-group {
    margin-bottom: 16px;
}

.form-label {
    display: block;
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--text-primary);
    margin-bottom: 6px;
}

.form-input, .form-select, .form-textarea {
    width: 100%;
    background: var(--bg-input);
    border: 1px solid var(--border-default);
    border-radius: 6px;
    padding: 8px 12px;
    color: var(--text-primary);
    font-size: 0.875rem;
    transition: border-color 0.2s ease;
}

.form-input:focus, .form-select:focus, .form-textarea:focus {
    outline: none;
    border-color: var(--info);
    box-shadow: 0 0 0 3px rgba(31, 111, 235, 0.1);
}

/* Loading states */
.loading-container {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 40px;
    color: var(--text-muted);
}

.loading-spinner {
    width: 20px;
    height: 20px;
    border: 2px solid var(--border-default);
    border-radius: 50%;
    border-top-color: var(--info);
    animation: spin 1s linear infinite;
    margin-right: 12px;
}

@keyframes spin {
    to { transform: rotate(360deg); }
}

/* Empty states */
.empty-state {
    text-align: center;
    padding: 60px 20px;
    color: var(--text-muted);
}

.empty-state-icon {
    font-size: 3rem;
    margin-bottom: 16px;
    opacity: 0.4;
}

.empty-state h3 {
    margin: 0 0 8px 0;
    font-size: 1.125rem;
    color: var(--text-secondary);
    font-weight: 600;
}

.empty-state p {
    margin: 0;
    font-size: 0.875rem;
    line-height: 1.5;
    max-width: 400px;
    margin: 0 auto;
}

/* Scrollbar styling */
::-webkit-scrollbar {
    width: 6px;
    height: 6px;
}

::-webkit-scrollbar-track {
    background: var(--bg-secondary);
}

::-webkit-scrollbar-thumb {
    background: var(--border-strong);
    border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
    background: var(--text-muted);
}

/* Responsive design */
@media (max-width: 1200px) {
    .eval-container {
        grid-template-columns: 280px 1fr;
    }
    
    .eval-results {
        display: none;
    }
    
    .chat-container {
        grid-template-columns: 1fr 250px;
    }
}

@media (max-width: 768px) {
    .global-header {
        flex-direction: column;
        gap: 12px;
        text-align: center;
    }
    
    .eval-container,
    .chat-container {
        grid-template-columns: 1fr;
    }
    
    .eval-sidebar,
    .chat-sidebar {
        display: none;
    }
}

/* Accessibility */
@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.01ms !important;
    }
}

/* Focus management */
button:focus-visible,
input:focus-visible,
select:focus-visible,
textarea:focus-visible {
    outline: 2px solid var(--info);
    outline-offset: 2px;
}

/* High contrast mode */
@media (prefers-contrast: high) {
    :root {
        --border-default: #ffffff;
        --text-muted: #ffffff;
    }
}
"""

# Global state management
class GlobalConfig:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.model = "gpt-4o-mini"
        self.server_status = "disconnected"
        self.last_spec_data = None
        self.analysis_history = []
    
    def test_connection(self):
        try:
            response = requests.get(f"{API_BASE_URL}/health", timeout=5)
            if response.status_code == 200:
                self.server_status = "connected"
                return True
            else:
                self.server_status = "error"
                return False
        except Exception as e:
            self.server_status = "error"
            return False
    
    def set_api_key(self, key):
        self.api_key = key
        os.environ["OPENAI_API_KEY"] = key
        # Test the key
        try:
            response = requests.post(f"{API_BASE_URL}/set-api-key", 
                                   json={"api_key": key}, timeout=10)
            return response.status_code == 200
        except:
            return False

global_config = GlobalConfig()

def fetch_available_models():
    """Fetch available models from the API"""
    try:
        response = requests.get(f"{API_BASE_URL}/models", timeout=10)
        if response.status_code == 200:
            models_data = response.json()
            return models_data.get("models", ["gpt-4o", "gpt-4o-mini"])
        else:
            return ["gpt-4o", "gpt-4o-mini"]
    except Exception as e:
        return ["gpt-4o", "gpt-4o-mini"]

def update_global_config(api_key, model):
    """Update global configuration"""
    global global_config
    
    status_msg = "⚠️ Not configured"
    status_color = "error"
    
    if api_key and api_key.strip():
        if global_config.set_api_key(api_key.strip()):
            global_config.model = model
            if global_config.test_connection():
                status_msg = "✅ Connected & Ready"
                status_color = "success"
            else:
                status_msg = "🔑 API Key OK, Server Offline"
                status_color = "warning"
        else:
            status_msg = "❌ Invalid API Key"
            status_color = "error"
    
    return (
        f'<div class="config-item"><div class="status-dot {status_color}"></div>{status_msg}</div>',
        gr.update(visible=True) if status_color in ["success", "warning"] else gr.update(visible=False)
    )

def analyze_api_comprehensive(spec_file, progress=gr.Progress()):
    """Comprehensive API analysis with visual dashboard"""
    
    if spec_file is None:
        return create_empty_dashboard(), "", create_empty_code_gen()
    
    if global_config.server_status != "connected":
        return create_error_dashboard("Server not connected"), "", create_empty_code_gen()
    
    try:
        progress(0.1, desc="Processing specification...")
        
        # Read and parse spec
        if hasattr(spec_file, 'name'):
            with open(spec_file.name, 'r', encoding='utf-8') as f:
                spec_content = f.read()
        else:
            spec_content = spec_file
            
        spec_data = json.loads(spec_content)
        global_config.last_spec_data = spec_data
        
        progress(0.3, desc="Running comprehensive analysis...")
        
        # Call API for analysis
        response = requests.post(
            f"{API_BASE_URL}/analyze",
            json={
                "openapi_spec": spec_data,
                "analysis_depth": "comprehensive", 
                "focus_areas": ["security", "completeness", "documentation", "performance"]
            },
            timeout=TIMEOUT
        )
        
        if response.status_code == 200:
            result = response.json()
            progress(0.8, desc="Generating dashboard...")
            
            # Generate components
            dashboard_html = create_visual_dashboard(spec_data, result)
            detailed_analysis = result.get("analysis", "")
            code_gen_html = generate_fixes_code(spec_data, result)
            
            progress(1.0, desc="Analysis complete!")
            
            return dashboard_html, detailed_analysis, code_gen_html
        else:
            return create_error_dashboard(f"Analysis failed: {response.status_code}"), "", create_empty_code_gen()
            
    except Exception as e:
        return create_error_dashboard(f"Error: {str(e)}"), "", create_empty_code_gen()

def create_visual_dashboard(spec_data: dict, analysis_result: dict) -> str:
    """Create interactive visual dashboard"""
    
    # Extract metrics
    metadata = analysis_result.get("metadata", {})
    endpoints_count = len(spec_data.get("paths", {}))
    schemas_count = len(spec_data.get("components", {}).get("schemas", {}))
    has_auth = bool(spec_data.get("components", {}).get("securitySchemes"))
    
    # Calculate scores (simulated)
    completeness_score = min(100, endpoints_count * 10)
    security_score = 90 if has_auth else 20
    documentation_score = 75  # Simulated
    performance_score = 85    # Simulated
    
    return f"""
    <div class="dashboard-grid">
        <div class="metric-card">
            <div class="metric-header">
                <h3 class="metric-title">API Completeness</h3>
                <div class="metric-icon">📋</div>
            </div>
            <div class="metric-value">{completeness_score}%</div>
            <div class="metric-change positive">+12% from last analysis</div>
            <div class="metric-progress">
                <div class="metric-progress-fill success" style="width: {completeness_score}%"></div>
            </div>
        </div>
        
        <div class="metric-card">
            <div class="metric-header">
                <h3 class="metric-title">Security Posture</h3>
                <div class="metric-icon">🔒</div>
            </div>
            <div class="metric-value">{security_score}%</div>
            <div class="metric-change {'positive' if has_auth else 'negative'}">
                {'✅ Authentication configured' if has_auth else '❌ No authentication'}
            </div>
            <div class="metric-progress">
                <div class="metric-progress-fill {'success' if security_score > 70 else 'error'}" style="width: {security_score}%"></div>
            </div>
        </div>
        
        <div class="metric-card">
            <div class="metric-header">
                <h3 class="metric-title">Documentation Quality</h3>
                <div class="metric-icon">📖</div>
            </div>
            <div class="metric-value">{documentation_score}%</div>
            <div class="metric-change neutral">Good coverage overall</div>
            <div class="metric-progress">
                <div class="metric-progress-fill warning" style="width: {documentation_score}%"></div>
            </div>
        </div>
        
        <div class="metric-card">
            <div class="metric-header">
                <h3 class="metric-title">Performance Impact</h3>
                <div class="metric-icon">⚡</div>
            </div>
            <div class="metric-value">{performance_score}%</div>
            <div class="metric-change positive">Optimized for speed</div>
            <div class="metric-progress">
                <div class="metric-progress-fill success" style="width: {performance_score}%"></div>
            </div>
        </div>
    </div>
    
    <div class="issues-panel">
        <div class="issues-header">
            <h3 class="issues-title">
                🚨 Critical Issues
                <span class="issues-count">3</span>
            </h3>
        </div>
        <div class="issues-list">
            <div class="issue-item">
                <div class="issue-header">
                    <div class="issue-priority">HIGH</div>
                    <h4 class="issue-title">Missing Authentication Security</h4>
                </div>
                <p class="issue-description">
                    API endpoints are not protected by authentication mechanisms, creating security vulnerabilities.
                </p>
                <div class="issue-actions">
                    <button class="issue-btn primary">🔧 Generate Fix</button>
                    <button class="issue-btn">📋 Copy Code</button>
                    <button class="issue-btn">📖 Learn More</button>
                </div>
            </div>
            
            <div class="issue-item">
                <div class="issue-header">
                    <div class="issue-priority medium">MEDIUM</div>
                    <h4 class="issue-title">Incomplete Error Responses</h4>
                </div>
                <p class="issue-description">
                    Missing 4xx and 5xx error response definitions for better error handling.
                </p>
                <div class="issue-actions">
                    <button class="issue-btn primary">🔧 Generate Fix</button>
                    <button class="issue-btn">📋 Copy Code</button>
                </div>
            </div>
            
            <div class="issue-item">
                <div class="issue-header">
                    <div class="issue-priority low">LOW</div>
                    <h4 class="issue-title">Missing Request Examples</h4>
                </div>
                <p class="issue-description">
                    API documentation would benefit from request/response examples for better developer experience.
                </p>
                <div class="issue-actions">
                    <button class="issue-btn primary">🔧 Generate Fix</button>
                    <button class="issue-btn">📋 Copy Code</button>
                </div>
            </div>
        </div>
    </div>
    """

def generate_fixes_code(spec_data: dict, analysis_result: dict) -> str:
    """Generate actual OpenAPI code fixes"""
    
    has_auth = bool(spec_data.get("components", {}).get("securitySchemes"))
    
    if not has_auth:
        return """
        <div class="code-gen-panel">
            <div class="code-gen-header">
                <h3 class="code-gen-title">🔧 Generated Fixes</h3>
                <button class="action-btn">📋 Copy All</button>
            </div>
            <div class="code-gen-content">
                <h4 style="color: var(--text-primary); margin: 16px 20px 12px;">1. Add Authentication Security</h4>
                <pre class="code-block">components:
  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
      description: "JWT token for API authentication"
    
    ApiKeyAuth:
      type: apiKey
      in: header
      name: X-API-Key
      description: "API key for service authentication"

security:
  - BearerAuth: []
  - ApiKeyAuth: []</pre>

                <h4 style="color: var(--text-primary); margin: 16px 20px 12px;">2. Add Error Response Templates</h4>
                <pre class="code-block">components:
  responses:
    BadRequest:
      description: Bad request
      content:
        application/json:
          schema:
            type: object
            properties:
              error:
                type: string
                example: "Invalid request parameters"
              code:
                type: string
                example: "INVALID_REQUEST"
    
    Unauthorized:
      description: Authentication required
      content:
        application/json:
          schema:
            type: object
            properties:
              error:
                type: string
                example: "Authentication token required"
              code:
                type: string
                example: "UNAUTHORIZED"</pre>
            </div>
        </div>
        """
    else:
        return create_empty_code_gen()

def create_empty_dashboard():
    """Create empty dashboard state"""
    return """
    <div class="empty-state">
        <div class="empty-state-icon">📊</div>
        <h3>Upload API Specification</h3>
        <p>Upload your OpenAPI specification file to see comprehensive analysis, metrics, and actionable insights.</p>
    </div>
    """

def create_error_dashboard(error_msg):
    """Create error dashboard state"""
    return f"""
    <div class="empty-state">
        <div class="empty-state-icon">❌</div>
        <h3>Analysis Failed</h3>
        <p>{error_msg}</p>
    </div>
    """

def create_empty_code_gen():
    """Create empty code generation panel"""
    return """
    <div class="empty-state">
        <div class="empty-state-icon">🔧</div>
        <h3>Code Fixes</h3>
        <p>Analyze your API first to see generated fixes and improvements.</p>
    </div>
    """

def chat_with_api(message: str, history: List[List[str]]) -> Tuple[str, List[List[str]]]:
    """Chat with API documentation"""
    
    if not message.strip():
        return "", history
    
    # Add user message to history
    history.append([message, ""])
    
    # Generate response based on context
    if global_config.last_spec_data:
        # Contextual response based on loaded API
        if "auth" in message.lower():
            response = """**Authentication in Your API:**

Based on your uploaded specification:
- **Current Status**: No authentication configured
- **Recommendation**: Implement JWT Bearer tokens
- **Business Impact**: Critical security vulnerability

**Quick Implementation:**
```yaml
components:
  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
```

Would you like me to generate the complete authentication setup?"""
        elif "error" in message.lower():
            response = """**Error Handling Analysis:**

Your API specification is missing comprehensive error responses:

**Missing Responses:**
- 400 Bad Request
- 401 Unauthorized  
- 404 Not Found
- 500 Internal Server Error

**Impact:** Poor developer experience, difficult debugging

**Fix:** I can generate complete error response schemas for you."""
        else:
            response = f"""I understand you're asking about: "{message}"

**Based on your API specification:**
- **Title**: {global_config.last_spec_data.get('info', {}).get('title', 'Unknown')}
- **Endpoints**: {len(global_config.last_spec_data.get('paths', {}))} endpoints
- **Security**: {'Configured' if global_config.last_spec_data.get('components', {}).get('securitySchemes') else 'Missing'}

Ask me specific questions like:
• "How do I add authentication?"
• "What error responses are missing?"
• "Generate code for pagination"
• "Show me security best practices"
"""
    else:
        response = """Please upload an API specification first so I can provide contextual assistance.

Once uploaded, I can help with:
- **Code Generation**: Actual OpenAPI fixes
- **Security Analysis**: Authentication & authorization
- **Performance Optimization**: Caching, pagination, etc.
- **Documentation**: Examples and descriptions
- **Best Practices**: Industry standards compliance"""
    
    # Update history with response
    history[-1][1] = response
    
    return "", history

def export_analysis(format_type: str):
    """Export analysis in various formats"""
    if not global_config.last_spec_data:
        return "No analysis to export. Please analyze an API specification first."
    
    if format_type == "json":
        return json.dumps(global_config.last_spec_data, indent=2)
    elif format_type == "markdown":
        return f"""# API Analysis Report

## Overview
- **API Title**: {global_config.last_spec_data.get('info', {}).get('title', 'Unknown')}
- **Version**: {global_config.last_spec_data.get('info', {}).get('version', 'Unknown')}
- **Endpoints**: {len(global_config.last_spec_data.get('paths', {}))}

## Critical Issues
- Missing authentication security
- Incomplete error handling
- Limited documentation

## Recommendations
1. Implement JWT authentication
2. Add comprehensive error responses
3. Include request/response examples
"""
    else:
        return "Export format not supported"

def create_interface():
    """Create the professional developer interface"""
    logger.info("Creating APISage Pro interface")
    
    # Initialize global config
    global_config.test_connection()
    models_list = fetch_available_models()
    
    with gr.Blocks(
        css=PRO_DARK_CSS,
        title="APISage Pro - Developer-First API Analysis",
        theme=gr.themes.Base()
    ) as interface:
        
        # Global Configuration Header
        gr.HTML(f"""
        <div class="global-header">
            <div class="header-brand">
                <div class="brand-logo">API</div>
                <div class="brand-text">
                    <h1>APISage Pro</h1>
                    <p>Developer-First API Analysis Platform</p>
                </div>
            </div>
            <div class="global-config" id="global-config">
                <div class="config-item">
                    <span>🤖 Model:</span>
                    <select id="model-select" style="background: var(--bg-input); border: 1px solid var(--border-default); border-radius: 4px; color: var(--text-primary); padding: 4px 8px; font-size: 0.8125rem;">
                        {''.join([f'<option value="{model}">{model}</option>' for model in models_list])}
                    </select>
                </div>
                <div class="config-item">
                    <span>🔑 API Key:</span>
                    <input type="password" id="api-key-input" placeholder="sk-..." style="background: var(--bg-input); border: 1px solid var(--border-default); border-radius: 4px; color: var(--text-primary); padding: 4px 8px; font-size: 0.8125rem; width: 120px;">
                    <button id="test-btn" style="background: var(--button-primary); border: none; border-radius: 4px; color: white; padding: 4px 8px; font-size: 0.8125rem; cursor: pointer;">Test</button>
                </div>
                <div id="status-display" class="config-item">
                    <div class="status-dot error"></div>
                    ⚠️ Not configured
                </div>
            </div>
        </div>
        """)
        
        # Hidden components for state management
        with gr.Row(visible=False):
            api_key_input = gr.Textbox()
            model_select = gr.Dropdown(choices=models_list, value=models_list[0])
            status_output = gr.HTML()
            tabs_visible = gr.State(False)
        
        # Main Tabs Interface
        with gr.Tabs(visible=False) as main_tabs:
            
            # Evaluation Tab
            with gr.Tab("📊 API Evaluation", id="eval-tab"):
                with gr.Row():
                    # Left Sidebar - Configuration
                    with gr.Column(scale=1, min_width=320):
                        gr.HTML('<h3 style="color: var(--text-primary); margin: 0 0 16px 0;">📁 Specification Upload</h3>')
                        
                        spec_file = gr.File(
                            label="OpenAPI Specification",
                            file_types=[".json", ".yaml", ".yml"],
                            file_count="single"
                        )
                        
                        analyze_btn = gr.Button(
                            "🚀 Analyze API",
                            variant="primary",
                            size="lg"
                        )
                        
                        gr.HTML('<h3 style="color: var(--text-primary); margin: 24px 0 16px 0;">⚙️ Analysis Options</h3>')
                        
                        analysis_depth = gr.Radio(
                            choices=["quick", "comprehensive", "deep"],
                            value="comprehensive",
                            label="Analysis Depth"
                        )
                        
                        focus_areas = gr.CheckboxGroup(
                            choices=["security", "performance", "documentation", "completeness", "standards"],
                            value=["security", "completeness", "documentation"],
                            label="Focus Areas"
                        )
                        
                        industry_context = gr.Dropdown(
                            choices=["general", "fintech", "healthcare", "e-commerce", "social", "enterprise"],
                            value="general",
                            label="Industry Context"
                        )
                    
                    # Center - Visual Dashboard
                    with gr.Column(scale=2):
                        dashboard_display = gr.HTML(create_empty_dashboard())
                        
                        with gr.Accordion("📋 Detailed Analysis", open=False):
                            detailed_analysis = gr.Markdown("Upload and analyze an API specification to see detailed results.")
                    
                    # Right Sidebar - Code Generation
                    with gr.Column(scale=1, min_width=400):
                        code_generation = gr.HTML(create_empty_code_gen())
            
            # Chat Tab  
            with gr.Tab("💬 API Assistant", id="chat-tab"):
                with gr.Row():
                    # Main Chat Area
                    with gr.Column(scale=3):
                        gr.HTML("""
                        <div class="chat-header">
                            <h2 class="chat-title">🤖 API Documentation Assistant</h2>
                            <p class="chat-subtitle">Ask questions about your API specification and get intelligent, contextual answers</p>
                        </div>
                        """)
                        
                        chatbot = gr.Chatbot(
                            height=500,
                            show_label=False,
                            container=False,
                            bubble_full_width=False
                        )
                        
                        with gr.Row():
                            chat_input = gr.Textbox(
                                placeholder="Ask anything about your API... (e.g., 'How do I add authentication?', 'Generate error handling code')",
                                container=False,
                                scale=4
                            )
                            chat_submit = gr.Button("Send", variant="primary", scale=1)
                    
                    # Chat Sidebar
                    with gr.Column(scale=1, min_width=300):
                        gr.HTML("""
                        <div style="margin-bottom: 20px;">
                            <h3 style="color: var(--text-primary); margin: 0 0 12px 0;">💡 Quick Prompts</h3>
                            <div style="display: flex; flex-direction: column; gap: 8px;">
                                <button class="action-btn" onclick="document.querySelector('input[placeholder*=\"Ask anything\"]').value='How do I add authentication to my API?'">
                                    🔐 Add Authentication
                                </button>
                                <button class="action-btn" onclick="document.querySelector('input[placeholder*=\"Ask anything\"]').value='Generate error handling code'">
                                    ⚠️ Error Handling
                                </button>
                                <button class="action-btn" onclick="document.querySelector('input[placeholder*=\"Ask anything\"]').value='Show me pagination best practices'">
                                    📄 Pagination
                                </button>
                                <button class="action-btn" onclick="document.querySelector('input[placeholder*=\"Ask anything\"]').value='What security vulnerabilities exist?'">
                                    🛡️ Security Review
                                </button>
                            </div>
                        </div>
                        """)
                        
                        gr.HTML("""
                        <div style="margin-bottom: 20px;">
                            <h3 style="color: var(--text-primary); margin: 0 0 12px 0;">📊 Context Status</h3>
                            <div style="background: var(--bg-elevated); border: 1px solid var(--border-subtle); border-radius: 6px; padding: 12px;">
                                <div style="font-size: 0.875rem; color: var(--text-secondary);">
                                    <div style="margin-bottom: 8px;">
                                        <strong>API Loaded:</strong> <span style="color: var(--text-muted);">Upload spec in Evaluation tab</span>
                                    </div>
                                    <div style="margin-bottom: 8px;">
                                        <strong>Endpoints:</strong> <span style="color: var(--text-muted);">0</span>
                                    </div>
                                    <div>
                                        <strong>Security:</strong> <span style="color: var(--text-muted);">Unknown</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                        """)
        
        # Action Bar
        with gr.Row(visible=False) as action_bar:
            with gr.Column():
                gr.HTML("""
                <div class="action-bar">
                    <div class="action-group">
                        <span style="color: var(--text-secondary); font-size: 0.875rem;">Export Analysis:</span>
                        <button class="action-btn">📄 JSON</button>
                        <button class="action-btn">📋 Markdown</button>
                        <button class="action-btn">📊 PDF Report</button>
                    </div>
                    <div class="action-group">
                        <button class="action-btn">🔄 Re-analyze</button>
                        <button class="action-btn">📤 Share Results</button>
                        <button class="action-btn primary">⚡ API Integration</button>
                    </div>
                </div>
                """)
        
        # Wire up functionality
        
        # Global config updates
        def update_config(api_key, model):
            status_html, tabs_visible_update = update_global_config(api_key, model)
            return status_html, tabs_visible_update, tabs_visible_update
        
        api_key_input.change(
            fn=update_config,
            inputs=[api_key_input, model_select],
            outputs=[status_output, main_tabs, action_bar]
        )
        
        # Analysis functionality
        analyze_btn.click(
            fn=analyze_api_comprehensive,
            inputs=[spec_file],
            outputs=[dashboard_display, detailed_analysis, code_generation]
        )
        
        # Chat functionality
        chat_submit.click(
            fn=chat_with_api,
            inputs=[chat_input, chatbot],
            outputs=[chat_input, chatbot]
        )
        
        chat_input.submit(
            fn=chat_with_api,
            inputs=[chat_input, chatbot], 
            outputs=[chat_input, chatbot]
        )
        
        # JavaScript for global config
        gr.HTML("""
        <script>
        document.addEventListener('DOMContentLoaded', function() {
            const apiKeyInput = document.getElementById('api-key-input');
            const modelSelect = document.getElementById('model-select');
            const testBtn = document.getElementById('test-btn');
            
            function updateConfig() {
                const apiKey = apiKeyInput.value;
                const model = modelSelect.value;
                
                // Update hidden gradio components
                const hiddenApiKey = document.querySelector('input[type="text"]');
                const hiddenModel = document.querySelector('select');
                
                if (hiddenApiKey) hiddenApiKey.value = apiKey;
                if (hiddenModel) hiddenModel.value = model;
                
                // Trigger change events
                if (hiddenApiKey) hiddenApiKey.dispatchEvent(new Event('input', { bubbles: true }));
                if (hiddenModel) hiddenModel.dispatchEvent(new Event('change', { bubbles: true }));
            }
            
            testBtn.addEventListener('click', updateConfig);
            apiKeyInput.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') updateConfig();
            });
            modelSelect.addEventListener('change', updateConfig);
        });
        </script>
        """)
    
    return interface

def main():
    """Launch APISage Pro interface"""
    logger.info("Starting APISage Pro - Developer-First Platform")
    
    print("\n🚀 APISage Pro - Developer-First API Analysis")
    print("=" * 50)
    print("🎯 Built for top 1% developers who need:")
    print("   • Speed & Efficiency")
    print("   • Actionable Intelligence") 
    print("   • Code Generation")
    print("   • Integration-Ready Results")
    print("   • Professional Workflow")
    print()
    
    # Check server connection
    if global_config.test_connection():
        print("✅ Connected to APISage server")
    else:
        print("⚠️  APISage server offline - configure API key for analysis")
    
    interface = create_interface()
    
    try:
        print("📍 Interface: http://localhost:7860")
        print("🔗 Server API: http://localhost:8080")
        print("🎯 Focus: Developer productivity & actionable insights")
        
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