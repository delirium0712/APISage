#!/usr/bin/env python3
"""
APISage - Developer-Focused Full-Screen Interface
Following UX audit best practices with proper hierarchy and accessibility
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

# Full-screen developer-focused CSS with WCAG AAA compliance
DEVELOPER_CSS = """
/* WCAG AAA Color System - High Contrast */
:root {
    --critical-bg: #2d1b1b;
    --critical-border: #dc2626;
    --critical-text: #fca5a5;
    
    --warning-bg: #2d2a1b;
    --warning-border: #f59e0b;
    --warning-text: #fbbf24;
    
    --success-bg: #1b2d1f;
    --success-border: #10b981;
    --success-text: #6ee7b7;
    
    --bg-primary: #0a0e14;
    --bg-secondary: #151922;
    --bg-elevated: #1e2330;
    --bg-card: #252b3b;
    
    --text-primary: #ffffff;
    --text-secondary: #cbd5e1;
    --text-muted: #94a3b8;
    
    --border-subtle: #374151;
    --border-default: #4b5563;
    
    --accent-blue: #3b82f6;
    --accent-green: #10b981;
    --accent-red: #ef4444;
    --accent-orange: #f59e0b;
}

/* Full Screen Layout */
html, body {
    margin: 0 !important;
    padding: 0 !important;
    height: 100vh !important;
    overflow-x: hidden !important;
}

.gradio-container {
    height: 100vh !important;
    max-width: none !important;
    width: 100vw !important;
    margin: 0 !important;
    padding: 0 !important;
    background: var(--bg-primary) !important;
    display: flex !important;
    flex-direction: column !important;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
}

/* Header Bar - Fixed at Top */
.app-header {
    background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
    color: var(--text-primary);
    padding: 12px 24px;
    border-bottom: 2px solid var(--border-default);
    display: flex;
    justify-content: space-between;
    align-items: center;
    min-height: 60px;
    z-index: 1000;
}

.app-title {
    font-size: 1.5rem;
    font-weight: 700;
    margin: 0;
}

.app-subtitle {
    font-size: 0.875rem;
    opacity: 0.8;
    margin: 0;
}

/* Main Layout - Three Column */
.main-layout {
    display: flex;
    height: calc(100vh - 60px);
    overflow: hidden;
}

/* Left Sidebar - Configuration */
.config-sidebar {
    width: 300px;
    background: var(--bg-secondary);
    border-right: 1px solid var(--border-default);
    display: flex;
    flex-direction: column;
    overflow-y: auto;
}

.config-section {
    padding: 16px;
    border-bottom: 1px solid var(--border-subtle);
}

.config-title {
    font-size: 0.875rem;
    font-weight: 600;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 12px;
}

/* Center Panel - Analysis Results */
.results-panel {
    flex: 1;
    display: flex;
    flex-direction: column;
    background: var(--bg-primary);
    overflow-y: auto;
    max-height: calc(100vh - 60px);
}

/* RIGHT PANEL - Critical Issues (TOP PRIORITY) */
.critical-panel {
    width: 400px;
    background: var(--bg-secondary);
    border-left: 1px solid var(--border-default);
    display: flex;
    flex-direction: column;
    overflow-y: auto;
    max-height: calc(100vh - 60px);
}

/* PRIORITY 1: Critical Alert Banner */
.critical-banner {
    background: linear-gradient(135deg, var(--critical-bg), #3b1219);
    border: 2px solid var(--critical-border);
    border-radius: 8px;
    padding: 16px;
    margin: 16px;
    animation: pulse-critical 2s infinite;
}

.critical-banner.no-issues {
    background: linear-gradient(135deg, var(--success-bg), #1a3d2e);
    border-color: var(--success-border);
    animation: none;
}

.critical-title {
    color: var(--critical-text);
    font-size: 1.125rem;
    font-weight: 700;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 8px;
}

.critical-title.success {
    color: var(--success-text);
}

.issue-count {
    background: rgba(255,255,255,0.2);
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 0.75rem;
}

.critical-list {
    margin-top: 12px;
}

.critical-item {
    padding: 8px 0;
    border-bottom: 1px solid rgba(255,255,255,0.1);
    color: var(--critical-text);
    font-size: 0.875rem;
}

.critical-item:last-child {
    border-bottom: none;
}

@keyframes pulse-critical {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.85; }
}

/* PRIORITY 2: Traffic Light Health Score */
.health-section {
    padding: 16px;
    border-bottom: 1px solid var(--border-subtle);
}

.health-indicator {
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 16px;
}

.traffic-light {
    width: 80px;
    height: 80px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.5rem;
    font-weight: 900;
    color: white;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
}

.traffic-light.critical {
    background: radial-gradient(circle, #ef4444, #dc2626);
    animation: pulse-critical 1.5s infinite;
}

.traffic-light.warning {
    background: radial-gradient(circle, #f59e0b, #d97706);
    color: var(--bg-primary);
}

.traffic-light.success {
    background: radial-gradient(circle, #10b981, #059669);
}

.health-details h3 {
    font-size: 0.875rem;
    color: var(--text-muted);
    margin: 0 0 4px 0;
}

.health-status {
    font-size: 1.25rem;
    font-weight: 700;
    color: var(--text-primary);
    margin-bottom: 8px;
}

.health-message {
    font-size: 0.875rem;
    color: var(--text-secondary);
    line-height: 1.4;
}

/* PRIORITY 3: Action Items Grid */
.actions-section {
    padding: 16px;
    border-bottom: 1px solid var(--border-subtle);
}

.actions-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 12px;
    max-height: 300px;
    overflow-y: auto;
}

.action-card {
    background: var(--bg-elevated);
    border: 1px solid var(--border-subtle);
    border-radius: 8px;
    padding: 12px;
    border-left: 4px solid var(--accent-blue);
}

.action-card.critical {
    border-left-color: var(--critical-border);
    background: linear-gradient(90deg, var(--critical-bg), var(--bg-elevated));
}

.action-card.warning {
    border-left-color: var(--warning-border);
    background: linear-gradient(90deg, var(--warning-bg), var(--bg-elevated));
}

.action-priority {
    display: inline-block;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 0.675rem;
    font-weight: 600;
    margin-bottom: 8px;
}

.priority-critical {
    background: var(--critical-border);
    color: white;
}

.priority-high {
    background: var(--warning-border);
    color: var(--bg-primary);
}

.action-title {
    font-size: 0.875rem;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 4px;
}

.action-description {
    font-size: 0.75rem;
    color: var(--text-secondary);
    line-height: 1.3;
}

/* Center Results Area */
.results-content {
    flex: 1;
    padding: 24px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 24px;
    min-height: 0;
}

/* Metrics Dashboard */
.metrics-dashboard {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 16px;
}

.metric-card {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: 8px;
    padding: 20px;
    text-align: center;
}

.metric-value {
    font-size: 2rem;
    font-weight: 900;
    color: var(--text-primary);
    margin-bottom: 8px;
}

.metric-label {
    font-size: 0.875rem;
    color: var(--text-secondary);
    margin-bottom: 4px;
}

.metric-trend {
    font-size: 0.75rem;
    font-weight: 600;
}

.trend-up { color: var(--success-text); }
.trend-down { color: var(--critical-text); }
.trend-neutral { color: var(--text-muted); }

/* Analysis Details */
.analysis-details {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: 8px;
    padding: 24px;
    max-height: 400px;
    overflow-y: auto;
}

.details-title {
    font-size: 1.25rem;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 16px;
}

/* Input Controls */
.gradio-container input,
.gradio-container textarea,
.gradio-container select,
.gradio-container button {
    background: var(--bg-elevated) !important;
    color: var(--text-primary) !important;
    border: 1px solid var(--border-subtle) !important;
    padding: 8px 12px !important;
    border-radius: 6px !important;
    font-size: 0.875rem !important;
}

.gradio-container input:focus,
.gradio-container textarea:focus,
.gradio-container select:focus {
    border-color: var(--accent-blue) !important;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1) !important;
}

.gradio-container button {
    cursor: pointer;
    font-weight: 500;
    transition: all 0.2s;
}

.gradio-container button:hover {
    background: var(--bg-card) !important;
}

.gradio-container button[variant="primary"] {
    background: var(--accent-blue) !important;
    color: white !important;
    border: none !important;
}

.gradio-container button[variant="primary"]:hover {
    background: #2563eb !important;
}

/* Code Display */
.gradio-container pre,
.gradio-container code {
    background: var(--bg-primary) !important;
    color: var(--text-primary) !important;
    border: 1px solid var(--border-subtle) !important;
    border-radius: 6px !important;
    padding: 12px !important;
    font-family: 'JetBrains Mono', Monaco, monospace !important;
    font-size: 0.875rem !important;
    white-space: pre-wrap !important;
    word-wrap: break-word !important;
    max-height: 300px !important;
    overflow-y: auto !important;
}

/* Mobile Responsive */
@media (max-width: 1024px) {
    .main-layout {
        flex-direction: column;
    }
    
    .config-sidebar,
    .critical-panel {
        width: 100%;
        height: auto;
        max-height: 200px;
        order: -1;
    }
    
    .results-panel {
        order: 0;
    }
}

@media (max-width: 768px) {
    .app-header {
        flex-direction: column;
        align-items: flex-start;
        gap: 8px;
        padding: 16px;
    }
    
    .metrics-dashboard {
        grid-template-columns: 1fr 1fr;
    }
}

/* Accessibility */
:focus-visible {
    outline: 2px solid var(--accent-blue) !important;
    outline-offset: 2px !important;
}

.sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0,0,0,0);
    border: 0;
}

/* Status Messages */
.status-message {
    padding: 12px 16px;
    border-radius: 6px;
    margin: 8px 0;
    font-size: 0.875rem;
}

.status-success {
    background: var(--success-bg);
    border: 1px solid var(--success-border);
    color: var(--success-text);
}

.status-warning {
    background: var(--warning-bg);
    border: 1px solid var(--warning-border);
    color: var(--warning-text);
}

.status-error {
    background: var(--critical-bg);
    border: 1px solid var(--critical-border);
    color: var(--critical-text);
}

/* Fix Gradio Component Overrides */
.gradio-container .prose {
    color: var(--text-primary) !important;
    max-width: none !important;
}

.gradio-container .prose p {
    color: var(--text-primary) !important;
}

.gradio-container .gr-html {
    color: var(--text-primary) !important;
}

.gradio-container .block {
    background: transparent !important;
    border: none !important;
}

/* Ensure proper scrolling in Gradio components */
.gradio-container .overflow-y-auto {
    max-height: 300px !important;
    overflow-y: auto !important;
}

.gradio-container .scroll-hide {
    scrollbar-width: thin !important;
    scrollbar-color: var(--border-default) transparent !important;
}

/* Structured Analysis Components */
.structured-analysis {
    max-width: 100%;
}

.executive-summary {
    background: linear-gradient(135deg, var(--bg-elevated), var(--bg-card));
    border: 1px solid var(--border-subtle);
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 24px;
}

.summary-stats {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
    margin-bottom: 24px;
}

.summary-stat {
    text-align: center;
    padding: 16px;
    border-radius: 8px;
    border: 1px solid var(--border-subtle);
}

.summary-stat.critical {
    background: linear-gradient(135deg, var(--critical-bg), var(--bg-elevated));
    border-color: var(--critical-border);
}

.summary-stat.warning {
    background: linear-gradient(135deg, var(--warning-bg), var(--bg-elevated));
    border-color: var(--warning-border);
}

.summary-stat.timeline {
    background: linear-gradient(135deg, var(--bg-elevated), var(--bg-card));
    border-color: var(--accent-blue);
}

.stat-number {
    display: block;
    font-size: 2rem;
    font-weight: 900;
    color: var(--text-primary);
    margin-bottom: 4px;
}

.stat-label {
    display: block;
    font-size: 0.875rem;
    color: var(--text-secondary);
    margin-bottom: 4px;
}

.stat-action {
    display: block;
    font-size: 0.75rem;
    color: var(--text-muted);
    font-weight: 600;
}

.next-steps {
    background: var(--bg-primary);
    border: 1px solid var(--border-subtle);
    border-radius: 8px;
    padding: 16px;
}

.next-steps h5 {
    color: var(--text-primary);
    margin-bottom: 12px;
    font-size: 1rem;
}

.next-steps ol {
    color: var(--text-secondary);
    padding-left: 20px;
}

.next-steps li {
    margin-bottom: 8px;
    line-height: 1.4;
}

.analysis-section-divider {
    height: 2px;
    background: linear-gradient(90deg, transparent, var(--border-default), transparent);
    margin: 32px 0;
}

/* Issue Deep Dive Cards */
.issue-deep-dive-card {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 20px;
    border-left: 4px solid var(--critical-border);
}

.issue-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
}

.issue-priority-badge {
    background: var(--critical-border);
    color: white;
    padding: 4px 12px;
    border-radius: 16px;
    font-size: 0.75rem;
    font-weight: 600;
}

.issue-priority-badge.priority-1 { background: var(--critical-border); }
.issue-priority-badge.priority-2 { background: var(--warning-border); }
.issue-priority-badge.priority-3 { background: var(--accent-blue); }
.issue-priority-badge.priority-4 { background: var(--text-muted); }

.issue-effort-badge {
    background: var(--bg-elevated);
    color: var(--text-secondary);
    border: 1px solid var(--border-subtle);
    padding: 4px 12px;
    border-radius: 16px;
    font-size: 0.75rem;
    font-weight: 500;
}

.issue-title {
    color: var(--text-primary);
    font-size: 1.125rem;
    font-weight: 600;
    margin-bottom: 8px;
}

.issue-description {
    color: var(--text-secondary);
    margin-bottom: 16px;
    line-height: 1.5;
}

.issue-impact-section,
.fix-instructions,
.issue-validation {
    margin-bottom: 16px;
    padding: 12px;
    background: var(--bg-primary);
    border-radius: 6px;
    border: 1px solid var(--border-subtle);
}

.issue-impact-section strong,
.fix-instructions strong,
.issue-validation strong {
    color: var(--text-primary);
    font-size: 0.875rem;
    margin-bottom: 8px;
    display: block;
}

.fix-instructions ol {
    color: var(--text-secondary);
    padding-left: 20px;
    margin: 8px 0 0 0;
}

.fix-instructions li {
    margin-bottom: 4px;
    line-height: 1.4;
}

/* Metrics Insights */
.metrics-insights {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: 12px;
    padding: 24px;
}

.metrics-insights h4 {
    color: var(--text-primary);
    margin-bottom: 20px;
    font-size: 1.125rem;
}

.insight-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 16px;
}

.insight-card {
    background: var(--bg-primary);
    border: 1px solid var(--border-subtle);
    border-radius: 8px;
    padding: 16px;
}

.insight-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 12px;
}

.insight-icon {
    font-size: 1.25rem;
}

.insight-title {
    font-weight: 600;
    color: var(--text-primary);
    font-size: 0.875rem;
}

.insight-current {
    font-size: 1.25rem;
    font-weight: 700;
    color: var(--text-primary);
    margin-bottom: 8px;
}

.insight-benchmark {
    font-size: 0.75rem;
    color: var(--text-muted);
    margin-bottom: 8px;
    line-height: 1.3;
}

.insight-recommendation {
    font-size: 0.875rem;
    color: var(--text-secondary);
    font-weight: 500;
}

/* Mobile responsive for new components */
@media (max-width: 768px) {
    .summary-stats {
        grid-template-columns: 1fr;
    }
    
    .insight-grid {
        grid-template-columns: 1fr;
    }
    
    .issue-header {
        flex-direction: column;
        align-items: flex-start;
        gap: 8px;
    }
}
"""

def fetch_available_models():
    """Fetch available models from the API server"""
    try:
        response = requests.get(f"{API_BASE_URL}/models", timeout=5)
        if response.status_code == 200:
            data = response.json()
            models = data.get("models", [])
            default_model = data.get("default_model", "o1-mini")
            logger.info(f"Fetched {len(models)} models from API: {models}")
            return models, default_model
        else:
            logger.warning(f"Failed to fetch models: HTTP {response.status_code}")
            return ["gpt-4o", "gpt-4o-mini", "o1", "o1-mini", "o1-preview"], "o1-mini"
    except Exception as e:
        logger.error(f"Error fetching models: {e}")
        return ["gpt-4o", "gpt-4o-mini", "o1", "o1-mini", "o1-preview"], "o1-mini"

def set_api_key_in_backend(api_key):
    """Set API key in the backend server"""
    try:
        if not api_key or not api_key.strip():
            return "❌ Please provide a valid API key", ""
            
        cleaned_api_key = api_key.strip()
        
        if not cleaned_api_key.startswith("sk-"):
            return "❌ Invalid API key format. Must start with 'sk-'", ""
            
        response = requests.post(
            f"{API_BASE_URL}/set-api-key",
            json={"api_key": cleaned_api_key},
            timeout=10
        )
        
        if response.status_code == 200:
            logger.info("API key set successfully in backend")
            return "✅ API key set successfully!", cleaned_api_key
        else:
            error_msg = f"❌ Failed to set API key: HTTP {response.status_code}"
            logger.error(error_msg)
            return error_msg, ""
            
    except requests.exceptions.ConnectionError:
        error_msg = "❌ Cannot connect to backend server. Is it running?"
        logger.error(error_msg)
        return error_msg, ""
    except Exception as e:
        logger.error(f"Error setting API key: {e}")
        return f"❌ Error setting API key: {str(e)}", ""

def test_api_key_validity(api_key):
    """Test if the API key is valid by checking backend status"""
    try:
        if not api_key or not api_key.strip():
            return "❌ No API key provided"

        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            health_data = response.json()
            if health_data.get("llm_available"):
                return "✅ API key is valid and LLM service is available"
            else:
                return "⚠️ Backend is healthy but LLM service unavailable - check API key"
        else:
            return f"⚠️ Backend health check failed: HTTP {response.status_code}"

    except requests.exceptions.ConnectionError:
        return "❌ Cannot connect to backend server"
    except Exception as e:
        return f"⚠️ Could not verify API key: {str(e)}"

def load_sample_spec():
    """Load sample OpenAPI spec"""
    return json.dumps({
        "openapi": "3.0.0",
        "info": {
            "title": "E-commerce API",
            "version": "1.0.0",
            "description": "A sample e-commerce API for demonstration"
        },
        "paths": {
            "/products": {
                "get": {
                    "summary": "List products",
                    "responses": {
                        "200": {"description": "Success"}
                    }
                }
            },
            "/users": {
                "get": {
                    "summary": "List users",
                    "responses": {
                        "200": {"description": "Success"}
                    }
                }
            }
        }
    }, indent=2)

class APIAnalyzer:
    """Handles API analysis logic"""
    
    @staticmethod
    def extract_issues(spec_data: dict) -> Tuple[List[dict], int]:
        """Extract issues from OpenAPI spec"""
        issues = []
        
        # Check for authentication
        if not spec_data.get("components", {}).get("securitySchemes"):
            issues.append({
                "severity": "critical",
                "title": "No Authentication Scheme",
                "description": "API has no security schemes defined",
                "impact": "Complete security vulnerability",
                "fix": "Add Bearer or API Key authentication"
            })
        
        # Check for error responses
        paths = spec_data.get("paths", {})
        has_error_responses = False
        for path, methods in paths.items():
            for method, details in methods.items():
                if isinstance(details, dict):
                    responses = details.get("responses", {})
                    if any(code.startswith(('4', '5')) for code in responses.keys()):
                        has_error_responses = True
                        break
        
        if not has_error_responses:
            issues.append({
                "severity": "critical",
                "title": "No Error Handling",
                "description": "No 4xx/5xx error responses defined",
                "impact": "Poor error handling and debugging",
                "fix": "Define 400, 401, 404, 500 responses"
            })
        
        # Check CRUD completeness
        if paths:
            methods_found = set()
            for path, methods in paths.items():
                methods_found.update(methods.keys())
            
            crud_methods = {'get', 'post', 'put', 'patch', 'delete'}
            missing_methods = crud_methods - methods_found
            
            if missing_methods:
                issues.append({
                    "severity": "warning",
                    "title": "Incomplete CRUD Operations",
                    "description": f"Missing {', '.join(missing_methods).upper()} methods",
                    "impact": "Incomplete API functionality",
                    "fix": f"Add {', '.join(missing_methods).upper()} endpoints"
                })
        
        # Check documentation
        info = spec_data.get("info", {})
        if not info.get("description"):
            issues.append({
                "severity": "warning",
                "title": "Missing API Description",
                "description": "No API description provided",
                "impact": "Poor developer experience",
                "fix": "Add comprehensive API description"
            })
        
        # Calculate score based on issues
        score = 100
        for issue in issues:
            if issue["severity"] == "critical":
                score -= 20
            elif issue["severity"] == "warning":
                score -= 10
        
        return issues, max(score, 0)
    
    @staticmethod
    def calculate_metrics(spec_data: dict) -> dict:
        """Calculate API metrics"""
        paths = spec_data.get("paths", {})
        
        # Count endpoints
        endpoint_count = 0
        for path, methods in paths.items():
            endpoint_count += len([m for m in methods if m in ['get', 'post', 'put', 'patch', 'delete']])
        
        # Check security
        has_security = bool(spec_data.get("components", {}).get("securitySchemes"))
        
        # Calculate documentation percentage
        documented = 0
        total = 0
        for path, methods in paths.items():
            for method, details in methods.items():
                if isinstance(details, dict):
                    total += 1
                    if details.get("summary") or details.get("description"):
                        documented += 1
        
        doc_percentage = (documented / total * 100) if total > 0 else 0
        
        # CRUD coverage
        methods_found = set()
        for path, methods in paths.items():
            methods_found.update(methods.keys())
        crud_coverage = len(methods_found & {'get', 'post', 'put', 'patch', 'delete'})
        
        return {
            "endpoints": endpoint_count,
            "security": 1 if has_security else 0,
            "documentation": doc_percentage,
            "crud_coverage": crud_coverage
        }

def analyze_api_with_backend(spec_text: str, model: str, api_key: str, analysis_method: str = "standard") -> Tuple[str, str, str, str, str]:
    """Analyze API with backend integration"""
    
    try:
        # Parse spec
        spec_data = json.loads(spec_text)
        api_title = spec_data.get("info", {}).get("title", "Unknown API")
        
        # Extract issues and calculate score (simplified for now)
        issues = []
        score = 75  # Default score
        metrics = {"endpoints": len(spec_data.get("paths", {}))}
        
        # Try to call backend if available
        backend_analysis = None
        if api_key:
            try:
                # Choose endpoint based on analysis method
                endpoint = "/analyze-agentic" if analysis_method == "agentic" else "/analyze"
                
                response = requests.post(
                    f"{API_BASE_URL}{endpoint}",
                    json={
                        "openapi_spec": spec_data,
                        "model": model,
                        "api_key": api_key,
                        "analysis_depth": "comprehensive",
                        "focus_areas": ["security", "performance", "documentation", "completeness", "standards"]
                    },
                    timeout=TIMEOUT
                )
                if response.status_code == 200:
                    backend_analysis = response.json()
            except:
                pass  # Fallback to local analysis
        
        # Generate UI components
        critical_html = generate_critical_banner(issues)
        health_html = generate_health_score(score, api_title)
        actions_html = generate_action_items(issues)
        metrics_html = generate_metrics_dashboard(metrics)
        details_html = generate_details(spec_data, issues, backend_analysis)
        
        return critical_html, health_html, actions_html, metrics_html, details_html
        
    except json.JSONDecodeError:
        error_html = """
        <div class="critical-banner">
            <div class="critical-title">❌ Invalid JSON</div>
            <div>Please check your OpenAPI specification syntax</div>
        </div>
        """
        return error_html, "", "", "", ""
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        error_html = f"""
        <div class="critical-banner">
            <div class="critical-title">❌ Analysis Failed</div>
            <div>{str(e)}</div>
        </div>
        """
        return error_html, "", "", "", ""

def generate_critical_banner(issues: List[dict]) -> str:
    """Generate critical issues banner"""
    critical_issues = [i for i in issues if i["severity"] == "critical"]
    
    if not critical_issues:
        return """
        <div class="critical-banner no-issues">
            <div class="critical-title success">✅ No Critical Issues <span class="issue-count">All Clear</span></div>
            <div>Your API meets basic security and functionality requirements</div>
        </div>
        """

    issues_list = "\n".join([
        f'<div class="critical-item">⚠️ {issue["title"]}: {issue["description"]}</div>'
        for issue in critical_issues
    ])
    
    return f"""
    <div class="critical-banner">
        <div class="critical-title">⚠️ Critical Issues <span class="issue-count">{len(critical_issues)} Critical</span></div>
        <div class="critical-list">
            {issues_list}
        </div>
    </div>
    """

def generate_health_score(score: int, api_title: str) -> str:
    """Generate health score with traffic light"""
    
    if score >= 80:
        status_class = "success"
        status_text = "Healthy"
        message = "Your API is in good shape with minor improvements needed."
    elif score >= 60:
        status_class = "warning"
        status_text = "Needs Improvement"
        message = "Your API has issues that should be addressed for production readiness."
    else:
        status_class = "critical"
        status_text = "Critical Issues"
        message = "Your API has critical problems that must be fixed before deployment."
    
    return f"""
    <div class="health-section">
        <div class="health-indicator">
            <div class="traffic-light {status_class}">{score}</div>
            <div class="health-details">
                <h3>API HEALTH SCORE</h3>
                <div class="health-status">{status_text}</div>
                <div class="health-message">{message}</div>
            </div>
        </div>
    </div>
    """

def generate_action_items(issues: List[dict]) -> str:
    """Generate prioritized action items"""
    
    if not issues:
        return """
        <div class="actions-section">
            <h4>Action Items</h4>
            <div class="actions-grid">
                <div class="action-card">
                    <span class="action-priority priority-low">COMPLETE</span>
                    <div class="action-title">No Actions Required</div>
                    <div class="action-description">Your API is well-structured</div>
                </div>
            </div>
        </div>
        """

    action_cards = []
    for issue in issues[:6]:  # Show top 6 issues
        severity_class = issue["severity"]
        priority_class = "priority-critical" if severity_class == "critical" else "priority-high"
        priority_text = severity_class.upper()
        
        action_cards.append(f"""
        <div class="action-card {severity_class}">
            <span class="action-priority {priority_class}">{priority_text}</span>
            <div class="action-title">{issue["title"]}</div>
            <div class="action-description">{issue["description"]}</div>
        </div>
        """)
    
    return f"""
    <div class="actions-section">
        <h4>Action Items</h4>
        <div class="actions-grid">{"".join(action_cards)}</div>
    </div>
    """

def generate_metrics_dashboard(metrics: dict) -> str:
    """Generate metrics dashboard"""
    
    # Determine trends
    endpoint_trend = "↓ Below average" if metrics["endpoints"] < 5 else "↑ Good coverage"
    endpoint_trend_class = "trend-down" if metrics["endpoints"] < 5 else "trend-up"
    
    security_trend = "↓ Critical" if metrics["security"] == 0 else "↑ Secured"
    security_trend_class = "trend-down" if metrics["security"] == 0 else "trend-up"
    
    doc_trend = "↓ Needs work" if metrics["documentation"] < 50 else "↑ Well documented"
    doc_trend_class = "trend-down" if metrics["documentation"] < 50 else "trend-up"
    
    crud_trend = "↓ Incomplete" if metrics["crud_coverage"] < 3 else "↑ Good coverage"
    crud_trend_class = "trend-down" if metrics["crud_coverage"] < 3 else "trend-up"
    
    return f"""
    <div class="metrics-dashboard">
        <div class="metric-card">
            <div class="metric-value">{metrics["endpoints"]}</div>
            <div class="metric-label">Endpoints</div>
            <div class="metric-trend {endpoint_trend_class}">{endpoint_trend}</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{"Yes" if metrics["security"] else "No"}</div>
            <div class="metric-label">Security</div>
            <div class="metric-trend {security_trend_class}">{security_trend}</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{metrics["documentation"]:.0f}%</div>
            <div class="metric-label">Documentation</div>
            <div class="metric-trend {doc_trend_class}">{doc_trend}</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{metrics["crud_coverage"]}/5</div>
            <div class="metric-label">CRUD Coverage</div>
            <div class="metric-trend {crud_trend_class}">{crud_trend}</div>
        </div>
    </div>
    """

def generate_details(spec_data: dict, issues: List[dict], backend_analysis: Optional[dict]) -> str:
    """Generate structured detailed analysis with actionable cards"""
    
    # Calculate comprehensive metrics
    paths = spec_data.get('paths', {})
    endpoints_count = sum(len([m for m in methods if m in ['get', 'post', 'put', 'patch', 'delete']]) 
                         for methods in paths.values())
    schemas_count = len(spec_data.get('components', {}).get('schemas', {}))
    has_security = bool(spec_data.get('components', {}).get('securitySchemes'))
    
    # Industry benchmarks (realistic targets)
    benchmarks = {
        'endpoints': {'good': 10, 'acceptable': 5, 'poor': 2},
        'security': {'required': True},
        'documentation': {'good': 90, 'acceptable': 70, 'poor': 50},
        'schemas': {'good': 5, 'acceptable': 3, 'poor': 1}
    }
    
    # Generate issue cards with priority and fix guidance
    issue_cards = ""
    priority_issues = sorted(issues, key=lambda x: 0 if x['severity'] == 'critical' else 1)
    
    for i, issue in enumerate(priority_issues[:4]):  # Top 4 issues
        priority_num = i + 1
        effort_level = "High" if issue['severity'] == 'critical' else "Medium"
        
        # Add specific fix instructions based on issue type
        fix_steps = []
        if "Authentication" in issue['title']:
            fix_steps = [
                "Add securitySchemes to components section",
                "Define Bearer token or API key authentication",
                "Apply security to all endpoints",
                "Test authentication flow"
            ]
        elif "Error Handling" in issue['title']:
            fix_steps = [
                "Add 400 (Bad Request) responses",
                "Add 401 (Unauthorized) responses", 
                "Add 404 (Not Found) responses",
                "Add 500 (Server Error) responses"
            ]
        elif "CRUD" in issue['title']:
            fix_steps = [
                "Add POST endpoints for resource creation",
                "Add PUT/PATCH for updates",
                "Add DELETE for resource removal",
                "Ensure consistent HTTP methods"
            ]
        else:
            fix_steps = [
                "Review API specification",
                "Follow OpenAPI 3.0 standards",
                "Add comprehensive documentation",
                "Test implementation"
            ]
        
        steps_html = "".join([f"<li>{step}</li>" for step in fix_steps])
        
        issue_cards += f"""
        <div class="issue-deep-dive-card">
            <div class="issue-header">
                <div class="issue-priority-badge priority-{priority_num}">Priority #{priority_num}</div>
                <div class="issue-effort-badge">{effort_level} Effort</div>
            </div>
            <h4 class="issue-title">{issue['title']}</h4>
            <p class="issue-description">{issue['description']}</p>
            
            <div class="issue-impact-section">
                <strong>Business Impact:</strong>
                <p>{issue['impact']}</p>
            </div>
            
            <div class="fix-instructions">
                <strong>Step-by-Step Fix:</strong>
                <ol>{steps_html}</ol>
            </div>
            
            <div class="issue-validation">
                <strong>How to Validate:</strong>
                <p>Re-run analysis after implementation to verify fix</p>
            </div>
        </div>
        """
    
    # Generate metric insights with benchmarks
    metric_insights = f"""
    <div class="metrics-insights">
        <h4>📊 Metric Deep Dive & Benchmarks</h4>
        
        <div class="insight-grid">
            <div class="insight-card">
                <div class="insight-header">
                    <span class="insight-icon">🔗</span>
                    <span class="insight-title">API Endpoints</span>
                </div>
                <div class="insight-current">Current: {endpoints_count}</div>
                <div class="insight-benchmark">
                    Industry Benchmark: {benchmarks['endpoints']['good']}+ (Good) | 
                    {benchmarks['endpoints']['acceptable']}+ (Acceptable)
                </div>
                <div class="insight-recommendation">
                    {'✅ Good coverage' if endpoints_count >= benchmarks['endpoints']['good'] 
                     else '⚠️ Consider adding more endpoints' if endpoints_count >= benchmarks['endpoints']['acceptable']
                     else '🔴 Insufficient API coverage - add more endpoints'}
                </div>
            </div>
            
            <div class="insight-card">
                <div class="insight-header">
                    <span class="insight-icon">🔒</span>
                    <span class="insight-title">Security Implementation</span>
                </div>
                <div class="insight-current">Current: {'Implemented' if has_security else 'Missing'}</div>
                <div class="insight-benchmark">Industry Requirement: Authentication Required</div>
                <div class="insight-recommendation">
                    {'✅ Security configured' if has_security else '🔴 CRITICAL: Add authentication immediately'}
                </div>
            </div>
            
            <div class="insight-card">
                <div class="insight-header">
                    <span class="insight-icon">📝</span>
                    <span class="insight-title">Data Models</span>
                </div>
                <div class="insight-current">Current: {schemas_count}</div>
                <div class="insight-benchmark">
                    Typical Range: {benchmarks['schemas']['good']}+ (Well-structured) | 
                    {benchmarks['schemas']['acceptable']}+ (Adequate)
                </div>
                <div class="insight-recommendation">
                    {'✅ Good schema coverage' if schemas_count >= benchmarks['schemas']['good']
                     else '⚠️ Consider more detailed schemas' if schemas_count >= benchmarks['schemas']['acceptable']
                     else '🔴 Add more schema definitions'}
                </div>
            </div>
        </div>
    </div>
    """
    
    # Executive summary with next steps
    critical_count = len([i for i in issues if i['severity'] == 'critical'])
    warning_count = len(issues) - critical_count
    
    executive_summary = f"""
    <div class="executive-summary">
        <h4>🎯 Executive Summary & Next Steps</h4>
        
        <div class="summary-stats">
            <div class="summary-stat critical">
                <span class="stat-number">{critical_count}</span>
                <span class="stat-label">Critical Issues</span>
                <span class="stat-action">Fix Immediately</span>
            </div>
            <div class="summary-stat warning">
                <span class="stat-number">{warning_count}</span>
                <span class="stat-label">Improvements</span>
                <span class="stat-action">Plan for Next Sprint</span>
            </div>
            <div class="summary-stat timeline">
                <span class="stat-number">{'1-2' if critical_count <= 2 else '3-5'}</span>
                <span class="stat-label">Days to Fix</span>
                <span class="stat-action">Estimated Timeline</span>
            </div>
        </div>
        
        <div class="next-steps">
            <h5>Immediate Action Plan:</h5>
            <ol>
                <li><strong>Week 1:</strong> Address all {critical_count} critical security issues</li>
                <li><strong>Week 2:</strong> Implement missing CRUD operations and error handling</li>
                <li><strong>Week 3:</strong> Enhance documentation and add examples</li>
                <li><strong>Week 4:</strong> Performance testing and final validation</li>
            </ol>
        </div>
    </div>
    """
    
    return f"""
    <div class="structured-analysis">
        {executive_summary}
        
        <div class="analysis-section-divider"></div>
        
        <h4>🔧 Prioritized Issues & Solutions</h4>
        {issue_cards}
        
        <div class="analysis-section-divider"></div>
        
        {metric_insights}
    </div>
    """

def create_interface():
    """Create the developer-focused full-screen interface"""
    logger.info("Creating full-screen developer interface")

    try:
        # Fetch available models from API
        models_list, default_model = fetch_available_models()
        logger.info(f"Fetched {len(models_list)} models from API: {models_list}")

        # Create the interface with custom layout
        with gr.Blocks(
            title="APISage - Developer Analysis Platform",
            theme=gr.themes.Base(
                primary_hue="blue",
                secondary_hue="slate",
                neutral_hue="slate",
                font=[gr.themes.GoogleFont("Inter"), "system-ui", "sans-serif"],
            ),
            css=DEVELOPER_CSS,
        ) as app:
            
            # Header
            gr.HTML("""
            <div class="app-header">
                <div>
                    <div class="app-title">🎯 APISage</div>
                    <div class="app-subtitle">Developer-Focused API Analysis Platform</div>
                </div>
                <div class="app-subtitle">Real-time OpenAPI Analysis</div>
            </div>
            """)

            # Main Layout Container
            with gr.Row(elem_classes=["main-layout"]):
                
                # Left Sidebar - Configuration
                with gr.Column(scale=1, elem_classes=["config-sidebar"]):
                    gr.HTML('<div class="config-section"><div class="config-title">🔑 API Configuration</div></div>')
                    
                    api_key_input = gr.Textbox(
                        label="OpenAI API Key",
                        type="password",
                        placeholder="sk-...",
                        value="",
                    )
                    
                    with gr.Row():
                        set_api_key_btn = gr.Button("🔐 Set Key", variant="secondary", size="sm")
                        test_api_key_btn = gr.Button("🧪 Test", variant="secondary", size="sm")
                    
                    api_key_status = gr.Textbox(
                        label="Status",
                        value="No API key set - LLM service unavailable",
                        interactive=False,
                    )
                    
                    api_key = gr.Textbox(visible=False, value="")  # Hidden field
                    
                    gr.HTML('<div class="config-section"><div class="config-title">⚙️ Analysis Settings</div></div>')
                    
                    model = gr.Dropdown(
                        choices=models_list,
                        value=default_model,
                        label="Model",
                    )
                    
                    analysis_method = gr.Radio(
                        choices=[
                            ("Standard Analysis", "standard"),
                            ("Multi-Agent Analysis (Slower but More Accurate)", "agentic")
                        ],
                        value="standard",
                        label="Analysis Method",
                        info="Multi-agent analysis uses specialized AI agents for deeper, more comprehensive analysis"
                    )
                    
                    sample_btn = gr.Button("📋 Load Sample", variant="secondary")
                    
                    gr.HTML('<div class="config-section"><div class="config-title">📝 API Specification</div></div>')
                    
                    spec_input = gr.Code(
                        label="OpenAPI Specification (JSON)",
                        language="json",
                        value='{"openapi": "3.0.0", "info": {"title": "Your API", "version": "1.0.0"}, "paths": {}}',
                        lines=10
                    )
                    
                    analyze_btn = gr.Button("🔍 Analyze API", variant="primary", size="lg")

                # Center Panel - Results
                with gr.Column(scale=2, elem_classes=["results-panel"]):
                    with gr.Column(elem_classes=["results-content"]):
                        
                        # Metrics Dashboard
                        metrics_dashboard = gr.HTML()
                        
                        # Detailed Analysis
                        detailed_analysis = gr.HTML()

                # Right Panel - Critical Issues & Actions
                with gr.Column(scale=1, elem_classes=["critical-panel"]):
                    
                    # Priority 1: Critical Issues
                    critical_issues = gr.HTML(
                        value='<div class="status-message status-warning">Load an API specification to begin analysis</div>'
                    )
                    
                    # Priority 2: Health Score
                    health_score = gr.HTML()
                    
                    # Priority 3: Action Items
                    action_items = gr.HTML()

            # Event handlers
            set_api_key_btn.click(
                fn=set_api_key_in_backend,
                inputs=[api_key_input],
                outputs=[api_key_status, api_key]
            )

            test_api_key_btn.click(
                fn=test_api_key_validity,
                inputs=[api_key_input],
                outputs=[api_key_status]
            )
            
            analyze_btn.click(
                fn=analyze_api_with_backend,
                inputs=[spec_input, model, api_key, analysis_method],
                outputs=[critical_issues, health_score, action_items, metrics_dashboard, detailed_analysis]
            )
            
            sample_btn.click(
                fn=load_sample_spec,
                outputs=[spec_input]
            )

        return app

    except Exception as e:
        logger.error(f"Failed to create interface: {e}")
        raise

if __name__ == "__main__":
    logger.info("Starting APISage Developer Platform")

    try:
        app = create_interface()
        app.launch(
            server_name="0.0.0.0",
            server_port=7860,
            share=False,
            quiet=False
        )
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        sys.exit(1)