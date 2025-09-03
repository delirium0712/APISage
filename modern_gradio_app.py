#!/usr/bin/env python3
"""
APISage - Modern Professional Interface
Redesigned based on comprehensive UX evaluation
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

# Check server connectivity on startup
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

# Modern Professional CSS - Light Theme with Accessibility
MODERN_CSS = """
/* WCAG AAA Compliant Color System */
:root {
    /* Light theme - high contrast */
    --bg-primary: #ffffff;
    --bg-secondary: #f8fafc;
    --bg-elevated: #f1f5f9;
    --bg-card: #ffffff;
    
    /* Text colors - high contrast ratios */
    --text-primary: #1e293b;
    --text-secondary: #475569;
    --text-muted: #64748b;
    --text-accent: #0f172a;
    
    /* Semantic colors */
    --critical: #dc2626;
    --critical-bg: #fef2f2;
    --critical-border: #fecaca;
    
    --warning: #d97706;
    --warning-bg: #fffbeb;
    --warning-border: #fed7aa;
    
    --success: #059669;
    --success-bg: #f0fdf4;
    --success-border: #bbf7d0;
    
    --info: #0284c7;
    --info-bg: #f0f9ff;
    --info-border: #bae6fd;
    
    /* UI elements */
    --border-light: #e2e8f0;
    --border-default: #cbd5e1;
    --border-strong: #94a3b8;
    
    /* Shadows */
    --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
    --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
    --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1);
}

/* Global Reset and Base Styles */
* {
    box-sizing: border-box;
}

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

/* Header */
.app-header {
    background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
    border-bottom: 2px solid var(--border-default);
    padding: 20px 32px;
    box-shadow: var(--shadow-sm);
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
    width: 40px;
    height: 40px;
    background: linear-gradient(135deg, var(--info) 0%, #0ea5e9 100%);
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-weight: 800;
    font-size: 1.25rem;
}

.brand-info h1 {
    margin: 0;
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--text-accent);
}

.brand-info p {
    margin: 0;
    font-size: 0.875rem;
    color: var(--text-secondary);
}

.header-status {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 16px;
    background: var(--success-bg);
    border: 1px solid var(--success-border);
    border-radius: 6px;
    font-size: 0.875rem;
    color: var(--success);
}

/* Critical Alert Banner */
.critical-alert {
    background: var(--critical-bg);
    border: 2px solid var(--critical);
    border-radius: 12px;
    margin: 24px;
    padding: 20px;
    display: flex;
    align-items: flex-start;
    gap: 12px;
    box-shadow: var(--shadow-md);
    animation: pulse-border 2s infinite;
}

.critical-alert.no-issues {
    background: var(--success-bg);
    border-color: var(--success);
    animation: none;
}

.alert-icon {
    font-size: 1.5rem;
    margin-top: 2px;
}

.alert-content h3 {
    margin: 0 0 8px 0;
    font-size: 1.125rem;
    font-weight: 700;
    color: var(--critical);
}

.alert-content.success h3 {
    color: var(--success);
}

.alert-description {
    margin: 0;
    color: var(--text-secondary);
    font-size: 0.925rem;
    line-height: 1.5;
}

@keyframes pulse-border {
    0%, 100% { border-color: var(--critical); }
    50% { border-color: #f87171; }
}

/* Main Layout Grid */
.main-container {
    display: grid;
    grid-template-columns: 320px 1fr 400px;
    gap: 24px;
    padding: 24px;
    min-height: calc(100vh - 120px);
}

/* Left Sidebar - Configuration */
.config-panel {
    background: var(--bg-card);
    border: 1px solid var(--border-light);
    border-radius: 12px;
    padding: 24px;
    height: fit-content;
    box-shadow: var(--shadow-sm);
}

.config-section {
    margin-bottom: 24px;
}

.config-section:last-child {
    margin-bottom: 0;
}

.section-title {
    font-size: 0.875rem;
    font-weight: 600;
    color: var(--text-accent);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 6px;
}

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

/* Center Panel - Results */
.results-panel {
    background: var(--bg-card);
    border: 1px solid var(--border-light);
    border-radius: 12px;
    box-shadow: var(--shadow-sm);
    overflow: hidden;
}

.results-header {
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border-light);
    padding: 20px 24px;
}

.results-title {
    margin: 0;
    font-size: 1.25rem;
    font-weight: 700;
    color: var(--text-accent);
}

.results-subtitle {
    margin: 4px 0 0 0;
    font-size: 0.875rem;
    color: var(--text-secondary);
}

.results-content {
    padding: 24px;
    max-height: calc(100vh - 300px);
    overflow-y: auto;
}

/* Metrics Dashboard */
.metrics-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 16px;
    margin-bottom: 32px;
}

.metric-card {
    background: var(--bg-elevated);
    border: 1px solid var(--border-light);
    border-radius: 8px;
    padding: 20px;
    text-align: center;
    position: relative;
    overflow: hidden;
}

.metric-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: var(--info);
}

.metric-card.critical::before { background: var(--critical); }
.metric-card.warning::before { background: var(--warning); }
.metric-card.success::before { background: var(--success); }

.metric-value {
    font-size: 2.25rem;
    font-weight: 900;
    color: var(--text-accent);
    margin-bottom: 4px;
    line-height: 1;
}

.metric-label {
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--text-secondary);
    margin-bottom: 8px;
}

.metric-context {
    font-size: 0.75rem;
    color: var(--text-muted);
    background: rgba(0, 0, 0, 0.05);
    border-radius: 4px;
    padding: 4px 8px;
    display: inline-block;
}

/* Right Panel - Action Items */
.action-panel {
    background: var(--bg-card);
    border: 1px solid var(--border-light);
    border-radius: 12px;
    box-shadow: var(--shadow-sm);
    height: fit-content;
}

.action-header {
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border-light);
    padding: 20px 24px;
    border-radius: 12px 12px 0 0;
}

.action-title {
    margin: 0;
    font-size: 1.125rem;
    font-weight: 700;
    color: var(--text-accent);
}

.action-subtitle {
    margin: 4px 0 0 0;
    font-size: 0.8125rem;
    color: var(--text-secondary);
}

.action-content {
    padding: 20px;
    max-height: calc(100vh - 400px);
    overflow-y: auto;
}

/* Action Cards */
.action-card {
    background: var(--bg-elevated);
    border: 1px solid var(--border-light);
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 16px;
    position: relative;
    transition: all 0.2s ease;
}

.action-card:hover {
    box-shadow: var(--shadow-md);
    border-color: var(--border-default);
}

.action-card:last-child {
    margin-bottom: 0;
}

.priority-badge {
    position: absolute;
    top: -8px;
    right: 12px;
    background: var(--critical);
    color: white;
    font-size: 0.75rem;
    font-weight: 600;
    padding: 4px 8px;
    border-radius: 12px;
    box-shadow: var(--shadow-sm);
}

.priority-badge.high { background: var(--warning); }
.priority-badge.medium { background: var(--info); }
.priority-badge.low { background: var(--text-muted); }

.action-card-title {
    font-size: 0.925rem;
    font-weight: 600;
    color: var(--text-accent);
    margin-bottom: 8px;
    padding-right: 60px;
}

.action-description {
    font-size: 0.8125rem;
    color: var(--text-secondary);
    line-height: 1.4;
    margin-bottom: 12px;
}

.action-steps {
    background: rgba(0, 0, 0, 0.02);
    border-radius: 6px;
    padding: 12px;
}

.action-steps-title {
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--text-accent);
    margin-bottom: 6px;
    text-transform: uppercase;
    letter-spacing: 0.025em;
}

.action-steps ol {
    margin: 0;
    padding-left: 16px;
    font-size: 0.8125rem;
    color: var(--text-secondary);
}

.action-steps li {
    margin-bottom: 4px;
}

/* Analysis Section */
.analysis-section {
    border-top: 1px solid var(--border-light);
    margin-top: 32px;
    padding-top: 32px;
}

.section-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 20px;
}

.section-header h3 {
    margin: 0;
    font-size: 1.125rem;
    font-weight: 700;
    color: var(--text-accent);
}

.section-badge {
    background: var(--info-bg);
    color: var(--info);
    font-size: 0.75rem;
    font-weight: 600;
    padding: 4px 8px;
    border-radius: 4px;
    border: 1px solid var(--info-border);
}

/* Analysis Cards */
.analysis-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 16px;
}

.analysis-card {
    background: var(--bg-elevated);
    border: 1px solid var(--border-light);
    border-radius: 8px;
    padding: 20px;
    transition: all 0.2s ease;
}

.analysis-card:hover {
    box-shadow: var(--shadow-md);
    transform: translateY(-1px);
}

.analysis-card-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 12px;
}

.analysis-icon {
    font-size: 1.25rem;
}

.analysis-card-title {
    font-size: 1rem;
    font-weight: 600;
    color: var(--text-accent);
    margin: 0;
}

.analysis-value {
    font-size: 1.75rem;
    font-weight: 800;
    color: var(--text-accent);
    margin-bottom: 8px;
}

.analysis-benchmark {
    font-size: 0.8125rem;
    color: var(--text-secondary);
    margin-bottom: 12px;
    padding: 8px;
    background: rgba(0, 0, 0, 0.02);
    border-radius: 4px;
}

.analysis-status {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 0.8125rem;
    font-weight: 500;
    padding: 4px 8px;
    border-radius: 4px;
}

.status-good {
    background: var(--success-bg);
    color: var(--success);
    border: 1px solid var(--success-border);
}

.status-warning {
    background: var(--warning-bg);
    color: var(--warning);
    border: 1px solid var(--warning-border);
}

.status-critical {
    background: var(--critical-bg);
    color: var(--critical);
    border: 1px solid var(--critical-border);
}

/* Loading and States */
.loading-spinner {
    display: inline-block;
    width: 20px;
    height: 20px;
    border: 2px solid var(--border-light);
    border-radius: 50%;
    border-top-color: var(--info);
    animation: spin 1s ease-in-out infinite;
}

@keyframes spin {
    to { transform: rotate(360deg); }
}

.empty-state {
    text-align: center;
    padding: 48px 24px;
    color: var(--text-muted);
}

.empty-state-icon {
    font-size: 3rem;
    margin-bottom: 16px;
    opacity: 0.5;
}

.empty-state h3 {
    margin: 0 0 8px 0;
    font-size: 1.125rem;
    color: var(--text-secondary);
}

.empty-state p {
    margin: 0;
    font-size: 0.925rem;
}

/* Buttons */
.btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 10px 16px;
    font-size: 0.875rem;
    font-weight: 500;
    text-decoration: none;
    border-radius: 6px;
    border: 1px solid;
    cursor: pointer;
    transition: all 0.2s ease;
}

.btn-primary {
    background: var(--info);
    border-color: var(--info);
    color: white;
}

.btn-primary:hover {
    background: #0369a1;
    border-color: #0369a1;
}

.btn-secondary {
    background: var(--bg-card);
    border-color: var(--border-default);
    color: var(--text-primary);
}

.btn-secondary:hover {
    background: var(--bg-elevated);
    border-color: var(--border-strong);
}

/* Responsive Design */
@media (max-width: 1200px) {
    .main-container {
        grid-template-columns: 280px 1fr;
        grid-template-areas: 
            "config results"
            "actions actions";
    }
    
    .config-panel { grid-area: config; }
    .results-panel { grid-area: results; }
    .action-panel { 
        grid-area: actions;
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
    
    .metrics-grid {
        grid-template-columns: repeat(2, 1fr);
    }
}

/* Accessibility Enhancements */
@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.01ms !important;
    }
}

/* Focus styles for keyboard navigation */
button:focus,
input:focus,
select:focus,
textarea:focus,
.btn:focus {
    outline: 2px solid var(--info);
    outline-offset: 2px;
}

/* High contrast mode support */
@media (prefers-contrast: high) {
    :root {
        --border-light: #000000;
        --border-default: #000000;
        --text-muted: #000000;
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

def analyze_api_spec(
    spec_file,
    analysis_depth: str,
    focus_areas: List[str],
    custom_requirements: str,
    model: str,
    progress=gr.Progress()
) -> Tuple[str, str, str]:
    """Analyze API specification and return comprehensive results"""
    
    if spec_file is None:
        return (
            create_empty_state(),
            create_empty_action_panel(),
            create_critical_alert("warning", "Upload Required", 
                                "Please upload an OpenAPI specification file to begin analysis.")
        )
    
    try:
        progress(0.1, desc="Processing file...")
        
        # Read and parse the spec file
        if hasattr(spec_file, 'name'):
            with open(spec_file.name, 'r', encoding='utf-8') as f:
                spec_content = f.read()
        else:
            spec_content = spec_file
            
        spec_data = json.loads(spec_content)
        
        progress(0.3, desc="Preparing analysis request...")
        
        # Prepare analysis request matching the server API
        analysis_request = {
            "openapi_spec": spec_data,
            "analysis_depth": analysis_depth,
            "focus_areas": focus_areas or []
        }
        
        progress(0.5, desc="Running AI analysis...")
        
        # Call the actual server analyze endpoint
        response = requests.post(
            f"{API_BASE_URL}/analyze",
            json=analysis_request,
            timeout=TIMEOUT
        )
        
        if response.status_code == 200:
            result = response.json()
            
            progress(0.8, desc="Processing results...")
            
            # Extract data from the actual API response structure
            analysis_content = result.get("analysis", "")
            key_findings = result.get("key_findings", {})
            metadata = result.get("metadata", {})
            
            # Parse the analysis content to extract issues
            issues = extract_issues_from_analysis(analysis_content, key_findings)
            
            progress(1.0, desc="Analysis complete!")
            
            # Generate UI components
            metrics_html = create_metrics_dashboard(spec_data, metadata, issues, analysis_content)
            actions_html = create_action_panel(issues, spec_data, analysis_content)
            alert_html = create_critical_alert_from_issues(issues)
            
            return metrics_html, actions_html, alert_html
            
        else:
            error_msg = f"Analysis failed: {response.status_code} - {response.text}"
            logger.error(error_msg)
            return (
                create_error_state("Analysis Error", error_msg),
                create_empty_action_panel(),
                create_critical_alert("error", "Analysis Failed", error_msg)
            )
            
    except json.JSONDecodeError:
        error_msg = "Invalid JSON format in specification file"
        return (
            create_error_state("Format Error", error_msg),
            create_empty_action_panel(),
            create_critical_alert("error", "Format Error", error_msg)
        )
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(f"Analysis error: {e}")
        return (
            create_error_state("System Error", error_msg),
            create_empty_action_panel(),
            create_critical_alert("error", "System Error", error_msg)
        )

def create_critical_alert(alert_type: str, title: str, message: str) -> str:
    """Create critical alert banner"""
    
    icons = {
        "critical": "🚨",
        "warning": "⚠️", 
        "success": "✅",
        "info": "ℹ️",
        "error": "❌"
    }
    
    css_class = "no-issues" if alert_type == "success" else ""
    text_class = "success" if alert_type == "success" else ""
    
    return f"""
    <div class="critical-alert {css_class}">
        <div class="alert-icon">{icons.get(alert_type, "ℹ️")}</div>
        <div class="alert-content {text_class}">
            <h3>{title}</h3>
            <p class="alert-description">{message}</p>
        </div>
    </div>
    """

def create_critical_alert_from_issues(issues: List[dict]) -> str:
    """Create alert based on issues analysis"""
    
    critical_issues = [i for i in issues if i.get('severity') == 'critical']
    
    if not critical_issues:
        return create_critical_alert(
            "success", 
            "No Critical Issues Found", 
            "Your API specification meets basic quality standards. Review the recommendations below for further improvements."
        )
    
    count = len(critical_issues)
    return create_critical_alert(
        "critical",
        f"{count} Critical Issue{'s' if count > 1 else ''} Detected",
        f"Immediate attention required. These issues could impact security, functionality, or user experience. Address them before deployment."
    )

def extract_issues_from_analysis(analysis_content: str, key_findings: dict) -> List[dict]:
    """Extract structured issues from the LLM analysis response"""
    
    issues = []
    
    # Extract critical issues count from key findings
    critical_count = key_findings.get('critical_issues_count', 0)
    security_issues = key_findings.get('security_issues_count', 0)
    
    # Parse the analysis text to extract specific issues
    lines = analysis_content.split('\n')
    current_issue = None
    
    for line in lines:
        line = line.strip()
        
        # Look for issue markers
        if line.startswith('1. **Issue:**') or line.startswith('2. **Issue:**') or line.startswith('3. **Issue:**'):
            if current_issue:
                issues.append(current_issue)
            
            # Extract issue title
            issue_title = line.split('**Issue:**', 1)[-1].strip()
            current_issue = {
                'title': issue_title,
                'severity': 'critical' if 'security' in issue_title.lower() or 'authentication' in issue_title.lower() else 'high',
                'description': '',
                'impact': '',
                'location': '',
                'fix': ''
            }
        
        elif current_issue and line.startswith('- **Location:**'):
            current_issue['location'] = line.split('**Location:**', 1)[-1].strip()
        elif current_issue and line.startswith('- **Impact:**'):
            current_issue['impact'] = line.split('**Impact:**', 1)[-1].strip()
        elif current_issue and line.startswith('- **Fix:**'):
            current_issue['fix'] = line.split('**Fix:**', 1)[-1].strip()
    
    # Add the last issue if any
    if current_issue:
        issues.append(current_issue)
    
    # If no issues were parsed, create default ones based on key findings
    if not issues and critical_count > 0:
        if security_issues > 0:
            issues.append({
                'title': 'Security Configuration Missing',
                'severity': 'critical',
                'description': 'API lacks proper authentication and authorization mechanisms',
                'impact': 'Potential security vulnerabilities and unauthorized access',
                'location': 'Global security configuration',
                'fix': 'Implement authentication schemes and apply security requirements'
            })
        
        issues.append({
            'title': 'Incomplete API Implementation', 
            'severity': 'high',
            'description': 'Missing essential endpoints or response definitions',
            'impact': 'Limited API functionality and poor developer experience',
            'location': 'Endpoints and responses',
            'fix': 'Add missing CRUD operations and comprehensive error handling'
        })
    
    return issues


def create_metrics_dashboard(spec_data: dict, metadata: dict, issues: List[dict], analysis_content: str = "") -> str:
    """Create comprehensive metrics dashboard"""
    
    # Calculate metrics
    paths = spec_data.get('paths', {})
    endpoints_count = len([method for path_methods in paths.values() 
                          for method in path_methods.keys() 
                          if method.lower() in ['get', 'post', 'put', 'patch', 'delete']])
    
    schemas_count = len(spec_data.get('components', {}).get('schemas', {}))
    has_security = bool(spec_data.get('components', {}).get('securitySchemes'))
    
    critical_count = len([i for i in issues if i.get('severity') == 'critical'])
    total_issues = len(issues)
    
    # Create metric cards
    metrics_html = f"""
    <div class="metrics-grid">
        <div class="metric-card {get_metric_status('endpoints', endpoints_count)}">
            <div class="metric-value">{endpoints_count}</div>
            <div class="metric-label">API Endpoints</div>
            <div class="metric-context">Industry avg: 8-15</div>
        </div>
        
        <div class="metric-card {get_metric_status('security', has_security)}">
            <div class="metric-value">{'✓' if has_security else '✗'}</div>
            <div class="metric-label">Security</div>
            <div class="metric-context">{'Configured' if has_security else 'Missing'}</div>
        </div>
        
        <div class="metric-card {get_metric_status('schemas', schemas_count)}">
            <div class="metric-value">{schemas_count}</div>
            <div class="metric-label">Data Models</div>
            <div class="metric-context">Well-structured: 5+</div>
        </div>
        
        <div class="metric-card {get_metric_status('issues', critical_count)}">
            <div class="metric-value">{critical_count}</div>
            <div class="metric-label">Critical Issues</div>
            <div class="metric-context">Target: 0</div>
        </div>
    </div>
    """
    
    # Add analysis breakdown
    analysis_html = f"""
    <div class="analysis-section">
        <div class="section-header">
            <h3>📊 Detailed Analysis</h3>
            <div class="section-badge">Comprehensive</div>
        </div>
        
        <div class="analysis-grid">
            <div class="analysis-card">
                <div class="analysis-card-header">
                    <span class="analysis-icon">🔗</span>
                    <h4 class="analysis-card-title">API Coverage</h4>
                </div>
                <div class="analysis-value">{endpoints_count}</div>
                <div class="analysis-benchmark">
                    <strong>Benchmark:</strong> Well-designed APIs typically have 8-15 core endpoints
                    covering essential CRUD operations and business logic.
                </div>
                <div class="analysis-status {get_analysis_status_class('endpoints', endpoints_count)}">
                    {get_analysis_status_text('endpoints', endpoints_count)}
                </div>
            </div>
            
            <div class="analysis-card">
                <div class="analysis-card-header">
                    <span class="analysis-icon">🔒</span>
                    <h4 class="analysis-card-title">Security Posture</h4>
                </div>
                <div class="analysis-value">{'Secure' if has_security else 'At Risk'}</div>
                <div class="analysis-benchmark">
                    <strong>Requirement:</strong> All production APIs must implement authentication
                    and authorization mechanisms to protect sensitive data.
                </div>
                <div class="analysis-status {get_analysis_status_class('security', has_security)}">
                    {get_analysis_status_text('security', has_security)}
                </div>
            </div>
            
            <div class="analysis-card">
                <div class="analysis-card-header">
                    <span class="analysis-icon">📋</span>
                    <h4 class="analysis-card-title">Data Structure</h4>
                </div>
                <div class="analysis-value">{schemas_count}</div>
                <div class="analysis-benchmark">
                    <strong>Best Practice:</strong> Complex APIs benefit from 5+ well-defined schemas
                    to ensure consistent data modeling and validation.
                </div>
                <div class="analysis-status {get_analysis_status_class('schemas', schemas_count)}">
                    {get_analysis_status_text('schemas', schemas_count)}
                </div>
            </div>
            
            <div class="analysis-card">
                <div class="analysis-card-header">
                    <span class="analysis-icon">🎯</span>
                    <h4 class="analysis-card-title">Quality Score</h4>
                </div>
                <div class="analysis-value">{calculate_quality_score(endpoints_count, has_security, schemas_count, critical_count)}</div>
                <div class="analysis-benchmark">
                    <strong>Target:</strong> Aim for 80+ to meet enterprise standards.
                    Score based on completeness, security, and issue severity.
                </div>
                <div class="analysis-status {get_quality_status_class(calculate_quality_score(endpoints_count, has_security, schemas_count, critical_count))}">
                    {get_quality_status_text(calculate_quality_score(endpoints_count, has_security, schemas_count, critical_count))}
                </div>
            </div>
        </div>
    </div>
    """
    
    return metrics_html + analysis_html

def create_action_panel(issues: List[dict], spec_data: dict, analysis_content: str = "") -> str:
    """Create actionable guidance panel"""
    
    if not issues:
        return f"""
        <div class="empty-state">
            <div class="empty-state-icon">🎉</div>
            <h3>Excellent Work!</h3>
            <p>No immediate action items detected. Your API specification follows best practices.</p>
        </div>
        """
    
    # Sort issues by priority
    priority_map = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
    sorted_issues = sorted(issues, key=lambda x: priority_map.get(x.get('severity', 'low'), 3))
    
    action_cards = ""
    for i, issue in enumerate(sorted_issues[:6]):  # Top 6 issues
        priority_num = i + 1
        severity = issue.get('severity', 'medium')
        title = issue.get('title', 'Issue')
        description = issue.get('description', 'Description not available')
        
        # Generate specific action steps
        steps = generate_action_steps(title, issue)
        
        action_cards += f"""
        <div class="action-card">
            <div class="priority-badge {severity}">{priority_num}</div>
            <h4 class="action-card-title">{title}</h4>
            <p class="action-description">{description}</p>
            <div class="action-steps">
                <div class="action-steps-title">Action Steps</div>
                <ol>
                    {steps}
                </ol>
            </div>
        </div>
        """
    
    return f"""
    <div class="action-content">
        {action_cards}
    </div>
    """

def generate_action_steps(title: str, issue: dict) -> str:
    """Generate specific action steps for an issue"""
    
    steps_map = {
        "Authentication": [
            "Add securitySchemes to components section",
            "Define Bearer token or API key authentication", 
            "Apply security requirements to all endpoints",
            "Test authentication flow with sample requests"
        ],
        "Error Handling": [
            "Add 400 (Bad Request) response definitions",
            "Include 401 (Unauthorized) for protected endpoints",
            "Define 404 (Not Found) for resource endpoints", 
            "Add 500 (Server Error) with error schema"
        ],
        "CRUD Operations": [
            "Identify missing resource operations",
            "Add POST endpoints for resource creation",
            "Include PUT/PATCH for resource updates",
            "Add DELETE operations where appropriate"
        ],
        "Documentation": [
            "Add detailed descriptions to all endpoints",
            "Include request/response examples",
            "Document query parameters and headers",
            "Add comprehensive schema descriptions"
        ],
        "Validation": [
            "Define request body schemas with validation rules",
            "Add required field specifications", 
            "Include format validation (email, UUID, etc.)",
            "Set appropriate min/max values for numbers"
        ]
    }
    
    # Find matching steps or use generic ones
    for key in steps_map:
        if key.lower() in title.lower():
            return "".join([f"<li>{step}</li>" for step in steps_map[key]])
    
    # Generic fallback steps
    generic_steps = [
        "Review the specific issue in your OpenAPI specification",
        "Apply the recommended fix following OpenAPI 3.0 standards", 
        "Validate changes using an OpenAPI validator",
        "Re-run analysis to confirm the issue is resolved"
    ]
    
    return "".join([f"<li>{step}</li>" for step in generic_steps])

# Helper functions for metrics
def get_metric_status(metric_type: str, value) -> str:
    """Get CSS class for metric status"""
    
    if metric_type == 'endpoints':
        if value >= 8: return 'success'
        elif value >= 4: return 'warning'
        else: return 'critical'
    elif metric_type == 'security':
        return 'success' if value else 'critical'
    elif metric_type == 'schemas':
        if value >= 5: return 'success'
        elif value >= 2: return 'warning' 
        else: return 'critical'
    elif metric_type == 'issues':
        if value == 0: return 'success'
        elif value <= 2: return 'warning'
        else: return 'critical'
    
    return 'info'

def get_analysis_status_class(metric_type: str, value) -> str:
    """Get status class for analysis cards"""
    status = get_metric_status(metric_type, value)
    return f"status-{status}" if status != 'info' else 'status-warning'

def get_analysis_status_text(metric_type: str, value) -> str:
    """Get status text for analysis cards"""
    
    if metric_type == 'endpoints':
        if value >= 8: return "✅ Good coverage"
        elif value >= 4: return "⚠️ Consider adding more endpoints"
        else: return "🔴 Insufficient API coverage"
    elif metric_type == 'security':
        return "✅ Security configured" if value else "🔴 Authentication required"
    elif metric_type == 'schemas':
        if value >= 5: return "✅ Well-structured data models"
        elif value >= 2: return "⚠️ Consider more detailed schemas"
        else: return "🔴 Add schema definitions"
    
    return "Review recommended"

def calculate_quality_score(endpoints: int, has_security: bool, schemas: int, critical_issues: int) -> int:
    """Calculate overall quality score"""
    
    score = 0
    
    # Endpoints (25 points max)
    if endpoints >= 10: score += 25
    elif endpoints >= 6: score += 20
    elif endpoints >= 3: score += 15
    else: score += 5
    
    # Security (25 points max)  
    if has_security: score += 25
    
    # Schemas (20 points max)
    if schemas >= 5: score += 20
    elif schemas >= 3: score += 15
    elif schemas >= 1: score += 10
    
    # Issues penalty (30 points max deduction)
    score -= min(critical_issues * 10, 30)
    
    return max(0, min(100, score))

def analyze_specific_aspect(spec_data: dict, aspect: str, context: str = ""):
    """Analyze a specific aspect of the API"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/analyze-specific-aspect",
            json={
                "spec": spec_data,
                "aspect": aspect,
                "context": context
            },
            timeout=TIMEOUT
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get("analysis", "Analysis failed")
        else:
            return f"Analysis failed: {response.status_code}"
            
    except Exception as e:
        return f"Error: {str(e)}"

def compare_with_standard(spec_data: dict, standard: str = "REST"):
    """Compare API with industry standards"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/compare-with-standard",
            json={
                "spec": spec_data, 
                "standard": standard
            },
            timeout=TIMEOUT
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get("comparison", "Comparison failed")
        else:
            return f"Comparison failed: {response.status_code}"
            
    except Exception as e:
        return f"Error: {str(e)}"

def get_improvement_suggestions(spec_data: dict, goal: str):
    """Get AI-powered improvement suggestions"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/suggest-improvements",
            json={
                "spec": spec_data,
                "goal": goal
            },
            timeout=TIMEOUT
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get("improvements", "No suggestions available")
        else:
            return f"Suggestions failed: {response.status_code}"
            
    except Exception as e:
        return f"Error: {str(e)}"

def analyze_with_evaluation(spec_data: dict, analysis_depth: str, focus_areas: List[str]):
    """Perform analysis with quality evaluation"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/analyze-with-evaluation",
            json={
                "openapi_spec": spec_data,
                "analysis_depth": analysis_depth,
                "focus_areas": focus_areas or []
            },
            timeout=TIMEOUT * 2  # Longer timeout for combined analysis
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Analysis failed: {response.status_code}"}
            
    except Exception as e:
        return {"error": f"Error: {str(e)}"}

def get_evaluation_metrics():
    """Get evaluation system performance metrics"""
    try:
        response = requests.get(f"{API_BASE_URL}/evaluation-metrics")
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Failed to get metrics: {response.status_code}"}
            
    except Exception as e:
        return {"error": f"Error: {str(e)}"}

def get_quality_status_class(score: int) -> str:
    """Get quality score status class"""
    if score >= 80: return 'status-good'
    elif score >= 60: return 'status-warning'
    else: return 'status-critical'

def get_quality_status_text(score: int) -> str:
    """Get quality score status text"""
    if score >= 80: return "✅ Enterprise ready"
    elif score >= 60: return "⚠️ Needs improvement" 
    else: return "🔴 Significant issues"

def create_empty_state() -> str:
    """Create empty state for results panel"""
    return f"""
    <div class="empty-state">
        <div class="empty-state-icon">📋</div>
        <h3>Ready to Analyze</h3>
        <p>Upload your OpenAPI specification to get started with comprehensive API analysis.</p>
    </div>
    """

def create_empty_action_panel() -> str:
    """Create empty state for action panel"""
    return f"""
    <div class="empty-state">
        <div class="empty-state-icon">🎯</div>
        <h3>Action Items</h3>
        <p>Prioritized recommendations will appear here after analysis.</p>
    </div>
    """

def create_error_state(title: str, message: str) -> str:
    """Create error state display"""
    return f"""
    <div class="empty-state">
        <div class="empty-state-icon">❌</div>
        <h3>{title}</h3>
        <p>{message}</p>
    </div>
    """

def create_evaluation_display(evaluation: dict) -> str:
    """Create evaluation metrics display"""
    
    overall_score = evaluation.get('overall_score', 0)
    metric_scores = evaluation.get('metric_scores', {})
    suggestions = evaluation.get('improvement_suggestions', [])
    eval_time = evaluation.get('evaluation_time', 0)
    
    # Create metric cards
    metric_cards = ""
    for metric, score in metric_scores.items():
        status_class = get_quality_status_class(score)
        metric_cards += f"""
        <div class="analysis-card">
            <div class="analysis-card-header">
                <span class="analysis-icon">📊</span>
                <h4 class="analysis-card-title">{metric.replace('_', ' ').title()}</h4>
            </div>
            <div class="analysis-value">{score:.1f}/100</div>
            <div class="analysis-status {status_class}">
                {get_quality_status_text(score)}
            </div>
        </div>
        """
    
    # Create suggestions list
    suggestions_html = ""
    for i, suggestion in enumerate(suggestions[:5]):
        suggestions_html += f"<li>{suggestion}</li>"
    
    return f"""
    <div class="health-overview">
        <div class="health-header">
            <div class="health-score">
                <div class="score-circle">{overall_score:.0f}</div>
                <div class="score-info">
                    <h2>Analysis Quality Score</h2>
                    <div class="score-subtitle">AI Analysis Evaluation</div>
                </div>
            </div>
            <div class="benchmark-info">
                <div>Evaluation Time: <strong>{eval_time:.1f}s</strong></div>
                <div>Model: <strong>o1-mini</strong></div>
            </div>
        </div>
        
        <div class="analysis-grid">
            {metric_cards}
        </div>
        
        {f'''<div class="action-plan">
            <h3>💡 Improvement Suggestions</h3>
            <ol>{suggestions_html}</ol>
        </div>''' if suggestions else ''}
    </div>
    """

def create_interface():
    """Create the modern professional interface"""
    logger.info("Creating modern professional interface")
    
    # Fetch available models
    models_list, default_model = fetch_available_models()
    logger.info(f"Available models: {models_list}")
    
    with gr.Blocks(
        css=MODERN_CSS,
        title="APISage - Modern API Analysis Platform",
        theme=gr.themes.Base()
    ) as interface:
        
        # Header
        gr.HTML(f"""
        <div class="app-header">
            <div class="brand-section">
                <div class="app-logo">AS</div>
                <div class="brand-info">
                    <h1>APISage</h1>
                    <p>Modern API Analysis Platform</p>
                </div>
            </div>
            <div class="header-status">
                <span class="loading-spinner"></span>
                System Ready
            </div>
        </div>
        """)
        
        # Main container
        with gr.Row():
            with gr.Column(scale=1, min_width=320):
                # Configuration Panel
                gr.HTML('<div class="section-title">⚙️ Configuration</div>')
                
                with gr.Group():
                    spec_file = gr.File(
                        label="OpenAPI Specification",
                        file_types=[".json", ".yaml", ".yml"],
                        file_count="single"
                    )
                    
                    analysis_depth = gr.Radio(
                        choices=["quick", "standard", "comprehensive"],
                        value="comprehensive",
                        label="Analysis Depth"
                    )
                    
                    focus_areas = gr.CheckboxGroup(
                        choices=["security", "performance", "documentation", "completeness", "standards"],
                        value=["security", "completeness"],
                        label="Focus Areas"
                    )
                    
                    model = gr.Dropdown(
                        choices=models_list,
                        value=default_model,
                        label="AI Model"
                    )
                    
                    custom_requirements = gr.Textbox(
                        label="Custom Requirements",
                        placeholder="Any specific requirements or concerns...",
                        lines=3
                    )
                    
                    # Advanced Analysis Options
                    with gr.Accordion("🔬 Advanced Analysis", open=False):
                        aspect_analysis = gr.Dropdown(
                            choices=["security", "performance", "documentation", "breaking_changes", "best_practices", "usability"],
                            label="Specific Aspect Analysis",
                            value=None
                        )
                        
                        standard_comparison = gr.Dropdown(
                            choices=["REST", "GraphQL", "gRPC", "OpenAPI"],
                            label="Compare with Standard",
                            value="REST"
                        )
                        
                        improvement_goal = gr.Textbox(
                            label="Improvement Goal",
                            placeholder="e.g., 'Make this API production-ready'",
                            lines=2
                        )
                        
                        enable_evaluation = gr.Checkbox(
                            label="Enable Quality Evaluation",
                            value=True,
                            info="Evaluate the quality of the AI analysis"
                        )
                    
                    analyze_btn = gr.Button(
                        "🚀 Analyze API",
                        variant="primary",
                        size="lg"
                    )
                    
                    # Advanced analysis buttons
                    with gr.Row():
                        aspect_btn = gr.Button("🔍 Aspect Analysis", size="sm")
                        compare_btn = gr.Button("📊 Compare Standards", size="sm")
                        improve_btn = gr.Button("💡 Get Suggestions", size="sm")
            
            with gr.Column(scale=2, min_width=600):
                # Results Panel  
                gr.HTML('<div class="results-header"><h2 class="results-title">Analysis Results</h2><p class="results-subtitle">Comprehensive insights and recommendations</p></div>')
                
                results_display = gr.HTML(create_empty_state())
            
            with gr.Column(scale=1, min_width=400):
                # Action Panel with Tabs
                with gr.Tabs():
                    with gr.Tab("🎯 Action Items"):
                        action_display = gr.HTML(create_empty_action_panel())
                    
                    with gr.Tab("📈 Quality Metrics"):
                        evaluation_display = gr.HTML("<div class='empty-state'><h3>Quality Evaluation</h3><p>Enable evaluation to see quality metrics</p></div>")
                    
                    with gr.Tab("🔧 Advanced Analysis"):
                        advanced_display = gr.HTML("<div class='empty-state'><h3>Advanced Analysis</h3><p>Use advanced analysis buttons for detailed insights</p></div>")
        
        # Critical Alert (full width)
        alert_display = gr.HTML(create_critical_alert("info", "Welcome", "Upload an OpenAPI specification to begin comprehensive analysis."))
        
        # Add footer with system status
        gr.HTML("""
        <div style="margin-top: 2rem; padding: 1rem; background: var(--bg-elevated); border-radius: 8px; text-align: center; font-size: 0.875rem; color: var(--text-muted);">
            <strong>APISage v3.0</strong> | AI-Powered API Analysis | 
            <span id="system-status">🟢 System Ready</span> | 
            Server: localhost:8080
        </div>
        """)
        
        # Enhanced analysis function that handles evaluation
        def enhanced_analyze(spec_file, analysis_depth, focus_areas, custom_requirements, model, enable_eval):
            """Enhanced analysis with optional evaluation"""
            if spec_file is None:
                return (
                    create_empty_state(),
                    create_empty_action_panel(),
                    create_critical_alert("warning", "Upload Required", "Please upload an OpenAPI specification file to begin analysis."),
                    "<div class='empty-state'><h3>Quality Evaluation</h3><p>Upload a file and enable evaluation</p></div>"
                )
            
            try:
                # Read spec file
                if hasattr(spec_file, 'name'):
                    with open(spec_file.name, 'r', encoding='utf-8') as f:
                        spec_content = f.read()
                else:
                    spec_content = spec_file
                    
                spec_data = json.loads(spec_content)
                
                if enable_eval:
                    # Use analyze-with-evaluation endpoint
                    result = analyze_with_evaluation(spec_data, analysis_depth, focus_areas)
                    
                    if "error" not in result:
                        analysis_content = result["analysis"]["content"]
                        key_findings = result["analysis"]["key_findings"]
                        metadata = result["analysis"]["metadata"]
                        evaluation = result["evaluation"]
                        
                        # Extract issues and create displays
                        issues = extract_issues_from_analysis(analysis_content, key_findings)
                        
                        metrics_html = create_metrics_dashboard(spec_data, metadata, issues, analysis_content)
                        actions_html = create_action_panel(issues, spec_data, analysis_content)
                        alert_html = create_critical_alert_from_issues(issues)
                        
                        # Create evaluation display
                        eval_html = create_evaluation_display(evaluation)
                        
                        return metrics_html, actions_html, alert_html, eval_html
                    else:
                        error_msg = result["error"]
                        return (
                            create_error_state("Analysis Error", error_msg),
                            create_empty_action_panel(),
                            create_critical_alert("error", "Analysis Failed", error_msg),
                            "<div class='empty-state'><h3>Evaluation Failed</h3></div>"
                        )
                else:
                    # Use regular analysis
                    return analyze_api_spec(spec_file, analysis_depth, focus_areas, custom_requirements, model) + ("<div class='empty-state'><h3>Quality Evaluation</h3><p>Enable evaluation to see quality metrics</p></div>",)
                    
            except Exception as e:
                error_msg = f"Error: {str(e)}"
                return (
                    create_error_state("System Error", error_msg),
                    create_empty_action_panel(),
                    create_critical_alert("error", "System Error", error_msg),
                    "<div class='empty-state'><h3>Evaluation Failed</h3></div>"
                )
        
        # Wire up the enhanced analysis function
        analyze_btn.click(
            fn=enhanced_analyze,
            inputs=[spec_file, analysis_depth, focus_areas, custom_requirements, model, enable_evaluation],
            outputs=[results_display, action_display, alert_display, evaluation_display]
        )
        
        # Advanced analysis functions
        def handle_aspect_analysis(spec_file, aspect):
            if spec_file is None or aspect is None:
                return "<div class='empty-state'><h3>Aspect Analysis</h3><p>Upload a file and select an aspect</p></div>"
            
            try:
                if hasattr(spec_file, 'name'):
                    with open(spec_file.name, 'r', encoding='utf-8') as f:
                        spec_content = f.read()
                else:
                    spec_content = spec_file
                    
                spec_data = json.loads(spec_content)
                analysis_result = analyze_specific_aspect(spec_data, aspect)
                
                return f"<div class='analysis-card'><h3>🔍 {aspect.title()} Analysis</h3><pre style='white-space: pre-wrap; font-family: inherit;'>{analysis_result}</pre></div>"
                
            except Exception as e:
                return f"<div class='empty-state'><h3>Analysis Failed</h3><p>{str(e)}</p></div>"
        
        def handle_standard_comparison(spec_file, standard):
            if spec_file is None:
                return "<div class='empty-state'><h3>Standards Comparison</h3><p>Upload a file first</p></div>"
            
            try:
                if hasattr(spec_file, 'name'):
                    with open(spec_file.name, 'r', encoding='utf-8') as f:
                        spec_content = f.read()
                else:
                    spec_content = spec_file
                    
                spec_data = json.loads(spec_content)
                comparison_result = compare_with_standard(spec_data, standard)
                
                return f"<div class='analysis-card'><h3>📊 {standard} Compliance</h3><pre style='white-space: pre-wrap; font-family: inherit;'>{comparison_result}</pre></div>"
                
            except Exception as e:
                return f"<div class='empty-state'><h3>Comparison Failed</h3><p>{str(e)}</p></div>"
        
        def handle_improvement_suggestions(spec_file, goal):
            if spec_file is None or not goal.strip():
                return "<div class='empty-state'><h3>Improvement Suggestions</h3><p>Upload a file and specify a goal</p></div>"
            
            try:
                if hasattr(spec_file, 'name'):
                    with open(spec_file.name, 'r', encoding='utf-8') as f:
                        spec_content = f.read()
                else:
                    spec_content = spec_file
                    
                spec_data = json.loads(spec_content)
                suggestions_result = get_improvement_suggestions(spec_data, goal)
                
                return f"<div class='analysis-card'><h3>💡 Improvement Suggestions</h3><pre style='white-space: pre-wrap; font-family: inherit;'>{suggestions_result}</pre></div>"
                
            except Exception as e:
                return f"<div class='empty-state'><h3>Suggestions Failed</h3><p>{str(e)}</p></div>"
        
        # Wire up advanced analysis buttons
        aspect_btn.click(
            fn=handle_aspect_analysis,
            inputs=[spec_file, aspect_analysis],
            outputs=advanced_display
        )
        
        compare_btn.click(
            fn=handle_standard_comparison, 
            inputs=[spec_file, standard_comparison],
            outputs=advanced_display
        )
        
        improve_btn.click(
            fn=handle_improvement_suggestions,
            inputs=[spec_file, improvement_goal],
            outputs=advanced_display
        )
    
    return interface

def main():
    """Launch the modern interface"""
    logger.info("Starting APISage Modern Platform v3.0")
    
    # Check server connectivity
    if not check_server_connection():
        logger.warning("APISage server is not available - some features may not work")
        print("⚠️  Warning: APISage server (localhost:8080) is not available")
        print("   Some analysis features may not work properly")
        print("   Make sure the server is running with: poetry run python -m api.main")
    else:
        logger.info("✅ Successfully connected to APISage server")
        print("✅ Connected to APISage server")
    
    interface = create_interface()
    
    try:
        print("\n🚀 Launching APISage Modern Interface...")
        print("📍 Interface will be available at: http://localhost:7860")
        print("🔗 Server API available at: http://localhost:8080")
        
        interface.launch(
            server_name="0.0.0.0",
            server_port=7860,
            share=False,
            show_error=True,
            quiet=False,
            inbrowser=True  # Auto-open browser
        )
    except Exception as e:
        logger.error(f"Failed to launch interface: {e}")
        raise

if __name__ == "__main__":
    main()