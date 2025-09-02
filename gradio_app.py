#!/usr/bin/env python3
"""
APISage - Clean, Focused API Analysis Interface with Proper Logging
Purpose: Display comprehensive LLM analysis results clearly
"""

import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import Any, Dict, Optional

import gradio as gr
import requests


# Configure logging
def setup_logging():
    """Setup comprehensive logging for the application"""
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)

    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            # File handler for all logs
            logging.FileHandler(
                f"logs/apisage_gradio_{datetime.now().strftime('%Y%m%d')}.log"
            ),
            # Console handler for INFO and above
            logging.StreamHandler(sys.stdout),
        ],
    )

    # Create specific loggers
    app_logger = logging.getLogger("apisage.gradio")
    api_logger = logging.getLogger("apisage.api_client")
    analysis_logger = logging.getLogger("apisage.analysis")

    return app_logger, api_logger, analysis_logger


# Initialize loggers
app_logger, api_logger, analysis_logger = setup_logging()

# Professional dark theme color scheme
FOCUSED_CSS = """
:root {
    --primary: #3b82f6;
    --primary-light: #60a5fa;
    --primary-dark: #1e40af;
    --success: #10b981;
    --warning: #f59e0b;
    --danger: #ef4444;
    
    --bg-main: #0f172a;
    --bg-card: #1e293b;
    --bg-code: #161b22;
    --bg-elevated: #262c36;
    --text-primary: #e6edf3;
    --text-secondary: #8b949e;
    --text-muted: #6e7681;
    --border: #30363d;
    --border-light: #21262d;
    --shadow: 0 4px 6px -1px rgb(0 0 0 / 0.3);
    --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.4);
}

/* More specific overrides */
.gradio-container {
    background-color: var(--bg-main) !important;
}

.gradio-container .gr-panel {
    background-color: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
}

.gradio-container .gr-form {
    background-color: var(--bg-main) !important;
    border: none !important;
    box-shadow: none !important;
}

/* Header */
.app-header {
    background: linear-gradient(135deg, var(--primary-dark) 0%, var(--primary) 100%);
    color: white;
    padding: 2rem;
    border-radius: 12px;
    text-align: center;
    margin-bottom: 2rem;
    box-shadow: var(--shadow-lg);
}

.app-header h1 {
    margin: 0;
    font-size: 2.25rem;
    font-weight: 700;
}

.app-header p {
    margin: 0.5rem 0 0 0;
    opacity: 0.9;
    font-size: 1rem;
}

/* Analysis results container */
.analysis-container {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.5rem;
    margin: 1rem 0;
    box-shadow: var(--shadow);
}

.analysis-section {
    margin-bottom: 2rem;
    padding-bottom: 1.5rem;
    border-bottom: 1px solid var(--border);
}

.analysis-section:last-child {
    border-bottom: none;
    margin-bottom: 0;
}

.section-title {
    color: var(--primary-light);
    font-size: 1.25rem;
    font-weight: 600;
    margin-bottom: 1rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.analysis-content {
    color: var(--text-primary);
    line-height: 1.6;
    white-space: pre-wrap;
}

/* Code blocks - dark theme */
pre, code {
    background: var(--bg-code) !important;
    border: 1px solid var(--border) !important;
    border-radius: 6px !important;
    padding: 1rem !important;
    font-family: 'Monaco', 'Menlo', 'Fira Code', monospace !important;
    font-size: 0.875rem !important;
    overflow-x: auto !important;
    color: var(--text-primary) !important;
}

/* Text areas and inputs - dark theme */
.gradio-container textarea,
.gradio-container input[type="text"],
.gradio-container input[type="password"],
.gradio-container .gr-textbox textarea,
.gradio-container .gr-textbox input {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    color: var(--text-primary) !important;
}

.gradio-container textarea:focus,
.gradio-container input:focus {
    border-color: var(--primary) !important;
    box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2) !important;
}

/* Status indicators */
.status-success { color: var(--success); }
.status-warning { color: var(--warning); }
.status-danger { color: var(--danger); }

/* Input area */
.input-section {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.5rem;
    box-shadow: var(--shadow);
}

/* Progress indicator */
.progress-container {
    background: var(--bg-code);
    border-radius: 8px;
    height: 6px;
    overflow: hidden;
    margin: 1rem 0;
}

.progress-bar {
    height: 100%;
    background: linear-gradient(90deg, var(--primary) 0%, var(--primary-light) 100%);
    transition: width 0.5s ease;
}

/* Buttons */
.analyze-button {
    background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%);
    color: white;
    border: none;
    padding: 12px 24px;
    border-radius: 8px;
    font-weight: 600;
    cursor: pointer;
    transition: transform 0.2s ease;
    box-shadow: var(--shadow);
}

.analyze-button:hover {
    transform: translateY(-1px);
}

/* Configuration panel - dark theme */
.config-panel {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.5rem;
    margin-bottom: 1rem;
    box-shadow: var(--shadow);
    color: var(--text-primary);
}

.config-panel h3 {
    color: var(--text-primary);
    margin: 0 0 1rem 0;
}

/* Dark theme tabs - more aggressive */
.gradio-container .gr-tab-nav,
.gradio-container .gr-tab-nav button,
.gradio-container .gr-tabs,
.gradio-container .gr-tabitem,
.gradio-container [role="tablist"],
.gradio-container [role="tab"],
.gradio-container [role="tabpanel"] {
    background: var(--bg-card) !important;
    background-color: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    color: var(--text-primary) !important;
}

.gradio-container .gr-tab-nav button.selected,
.gradio-container [role="tab"][aria-selected="true"] {
    background: var(--primary) !important;
    background-color: var(--primary) !important;
    color: white !important;
    border-color: var(--primary) !important;
}

/* Force all content areas to be dark */
.gradio-container .gr-tabitem > *,
.gradio-container [role="tabpanel"] > *,
.gradio-container .gr-box > *,
.gradio-container .gr-form > * {
    background: var(--bg-main) !important;
    background-color: var(--bg-main) !important;
    color: var(--text-primary) !important;
}

/* Dark theme buttons */
.gradio-container button {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    color: var(--text-primary) !important;
}

.gradio-container button[variant="primary"] {
    background: var(--primary) !important;
    color: white !important;
    border: 1px solid var(--primary) !important;
}

/* Markdown analysis styling */
.analysis-markdown {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    padding: 1.5rem !important;
    color: var(--text-primary) !important;
}

.analysis-markdown h1,
.analysis-markdown h2,
.analysis-markdown h3,
.analysis-markdown h4,
.analysis-markdown h5,
.analysis-markdown h6 {
    color: var(--primary-light) !important;
    border-bottom: 1px solid var(--border) !important;
    padding-bottom: 0.5rem !important;
    margin-bottom: 1rem !important;
}

.analysis-markdown code {
    background: var(--bg-code) !important;
    border: 1px solid var(--border) !important;
    border-radius: 4px !important;
    padding: 0.25rem 0.5rem !important;
    font-family: 'Monaco', 'Menlo', 'Fira Code', monospace !important;
    color: var(--text-primary) !important;
}

.analysis-markdown pre {
    background: var(--bg-code) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    padding: 1rem !important;
    overflow-x: auto !important;
}

.analysis-markdown pre code {
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
}

.analysis-markdown ul,
.analysis-markdown ol {
    color: var(--text-primary) !important;
}

.analysis-markdown li {
    margin-bottom: 0.5rem !important;
}

.analysis-markdown strong {
    color: var(--primary-light) !important;
}

.analysis-markdown blockquote {
    border-left: 4px solid var(--primary) !important;
    padding-left: 1rem !important;
    margin-left: 0 !important;
    color: var(--text-secondary) !important;
}

/* Score Display Styling */
.score-display {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    padding: 1rem !important;
    text-align: center !important;
}

.score-circle {
    width: 120px;
    height: 120px;
    border-radius: 50%;
    background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    margin: 0 auto;
    box-shadow: var(--shadow-lg);
}

.score-number {
    font-size: 2rem;
    font-weight: 700;
    color: white;
    line-height: 1;
}

.score-label {
    font-size: 0.875rem;
    color: white;
    opacity: 0.9;
    margin-top: 0.25rem;
}

/* Score Breakdown Styling */
.score-breakdown {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    padding: 1.5rem !important;
}

.score-item {
    display: flex;
    align-items: center;
    margin-bottom: 1rem;
    gap: 1rem;
}

.score-item:last-child {
    margin-bottom: 0;
}

.score-item .score-label {
    min-width: 100px;
    font-weight: 600;
    color: var(--text-primary);
}

.score-bar {
    flex: 1;
    height: 8px;
    background: var(--bg-code);
    border-radius: 4px;
    overflow: hidden;
    position: relative;
}

.score-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--primary) 0%, var(--primary-light) 100%);
    border-radius: 4px;
    transition: width 0.5s ease;
}

.score-value {
    min-width: 50px;
    text-align: right;
    font-weight: 600;
    color: var(--text-primary);
}

/* Issues Display Styling */
.issues-display {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    padding: 1.5rem !important;
    margin-bottom: 1rem !important;
}

.issues-container {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.5rem;
    margin: 1rem 0;
    box-shadow: var(--shadow);
}

.issues-content {
    color: var(--text-primary);
    line-height: 1.6;
}

.issue-item {
    background: var(--bg-code);
    border-left: 4px solid var(--danger);
    padding: 1rem;
    margin: 1rem 0;
    border-radius: 0 8px 8px 0;
}

.issue-item.high {
    border-left-color: var(--danger);
}

.issue-item.medium {
    border-left-color: var(--warning);
}

.issue-item.low {
    border-left-color: var(--primary);
}

.issue-title {
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 0.5rem;
}

.issue-location {
    font-family: monospace;
    background: var(--bg-main);
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    font-size: 0.875rem;
    color: var(--primary-light);
}

.issue-impact {
    color: var(--text-secondary);
    font-size: 0.875rem;
    margin: 0.5rem 0;
}

.issue-fix {
    color: var(--success);
    font-size: 0.875rem;
    font-weight: 500;
}

/* Token Usage Display Styling */
.token-usage-display {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    padding: 1.5rem !important;
    margin-bottom: 1rem !important;
}

.token-usage-container {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.5rem;
    margin: 1rem 0;
    box-shadow: var(--shadow);
}

.token-content {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
    margin-top: 1rem;
}

.token-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.75rem;
    background: var(--bg-code);
    border-radius: 8px;
    border-left: 4px solid var(--primary);
}

.token-label {
    font-weight: 600;
    color: var(--text-primary);
}

.token-value {
    font-weight: 700;
    color: var(--primary-light);
    font-family: monospace;
}

/* Progress indicators */
.progress-step {
    display: flex;
    align-items: center;
    margin: 0.5rem 0;
    padding: 0.5rem;
    background: var(--bg-code);
    border-radius: 8px;
    border-left: 4px solid var(--primary);
}

.progress-step.completed {
    border-left-color: var(--success);
}

.progress-step.error {
    border-left-color: var(--danger);
}

.progress-step .step-icon {
    margin-right: 0.75rem;
    font-size: 1.25rem;
}

.progress-step .step-text {
    flex: 1;
    color: var(--text-primary);
}

.progress-step .step-time {
    font-size: 0.875rem;
    color: var(--text-secondary);
}
"""


def analyze_api_comprehensive(
    spec_text: str,
    provider: str = "OpenAI",
    model: str = "gpt-4o-mini",
    api_key: str = "",
):
    """Comprehensive API analysis with real-time LLM call visibility"""

    analysis_logger.info(
        f"Starting API analysis - Provider: {provider}, Model: {model}"
    )
    start_time = time.time()

    # Set API key if provided
    if api_key and api_key.strip():
        os.environ["OPENAI_API_KEY"] = api_key.strip()
        app_logger.info("API key updated from user input")

    # Step 1: Initial setup
    yield create_llm_status_display("🔍 Analyzing OpenAPI specification...", "", "")
    analysis_logger.info("Starting OpenAPI specification analysis")

    try:
        # Parse the OpenAPI spec
        spec_data = json.loads(spec_text)
        api_title = spec_data.get("info", {}).get("title", "Unknown")
        api_version = spec_data.get("info", {}).get("version", "Unknown")
        endpoints_count = len(spec_data.get("paths", {}))

        analysis_logger.info(
            f"Parsed OpenAPI spec - Title: {api_title}, Version: {api_version}, Endpoints: {endpoints_count}"
        )

        # Step 2: Show API parsed
        yield create_llm_status_display(
            f"✅ OpenAPI Parsed: {api_title} v{api_version} ({endpoints_count} endpoints)",
            "🤖 Preparing LLM request...",
            "",
        )

        # Prepare request payload
        request_payload = {
            "openapi_spec": spec_data,
            "analysis_depth": "comprehensive",
            "focus_areas": [
                "security",
                "performance",
                "documentation",
                "best_practices",
                "error_handling",
            ],
        }

        api_logger.info(
            f"Sending analysis request to backend - Spec size: {len(spec_text)} chars"
        )

        # Step 3: Show backend call
        yield create_llm_status_display(
            f"✅ OpenAPI Parsed: {api_title} v{api_version} ({endpoints_count} endpoints)",
            f"📡 Calling Backend API at localhost:8080/analyze",
            f"🔄 Payload: {len(json.dumps(request_payload))} chars | Model: {model}",
        )

        # Call the AI backend
        response = requests.post(
            "http://localhost:8080/analyze", json=request_payload, timeout=120
        )

        api_logger.info(
            f"Received response from backend - Status: {response.status_code}, Size: {len(response.text)} chars"
        )

        # Step 4: Show LLM response received
        if response.status_code == 200:
            yield create_llm_status_display(
                f"✅ OpenAPI Parsed: {api_title} v{api_version} ({endpoints_count} endpoints)",
                f"✅ Backend Response: {response.status_code} ({len(response.text)} chars)",
                f"🤖 LLM Call Successful | Processing results...",
            )

            ai_result = response.json()
            analysis_logger.info("Successfully received AI analysis results")

            # Log analysis metadata
            metadata = ai_result.get("metadata", {})
            analysis_logger.info(
                f"Analysis metadata - Model: {metadata.get('model_used', 'Unknown')}, "
                f"Endpoints analyzed: {metadata.get('endpoints_count', 0)}"
            )

            # Step 5: Show final results
            yield create_llm_status_display(
                f"✅ OpenAPI Parsed: {api_title} v{api_version} ({endpoints_count} endpoints)",
                f"✅ Backend Response: {response.status_code} ({len(response.text)} chars)",
                f"✅ LLM Analysis Complete | Model: {metadata.get('model_used', 'Unknown')} | Tokens: {metadata.get('total_tokens', 0)}",
            )

            # Format the complete analysis
            (
                status_html,
                score_html,
                score_breakdown_html,
                token_usage_html,
                issues_html,
                markdown_analysis,
            ) = format_comprehensive_analysis(ai_result, spec_data)

            # Calculate processing time
            processing_time = time.time() - start_time
            analysis_logger.info(
                f"Analysis completed successfully in {processing_time:.2f} seconds"
            )

            time.sleep(1)  # Show status for a moment
            yield status_html, score_html, score_breakdown_html, token_usage_html, issues_html, markdown_analysis

        else:
            error_msg = (
                f"Backend returned error {response.status_code}: {response.text}"
            )
            api_logger.error(error_msg)

            yield create_llm_status_display(
                f"✅ OpenAPI Parsed: {api_title} v{api_version} ({endpoints_count} endpoints)",
                f"❌ Backend Error: {response.status_code}",
                f"❌ LLM Call Failed: {response.text[:100]}...",
            )

            time.sleep(2)
            error_html = f"""
            <div class="analysis-container">
                <div class="section-title status-danger">❌ Analysis Failed</div>
                <div class="analysis-content">
                    Error {response.status_code}: {response.text}
                    
                    Please check:
                    1. API key is set correctly
                    2. Backend server is running
                    3. OpenAPI specification is valid
                </div>
            </div>
            """
            error_markdown = f"""# ❌ Analysis Failed

**Error {response.status_code}:** {response.text}

## Troubleshooting Steps
1. API key is set correctly
2. Backend server is running
3. OpenAPI specification is valid
"""
            # Return empty/default values for other components
            yield error_html, "", "", "", "", error_markdown

    except requests.exceptions.ConnectionError as e:
        api_logger.error(f"Connection error to backend: {str(e)}")
        yield create_llm_status_display(
            "❌ OpenAPI Parsing Failed",
            "❌ Backend Unavailable",
            "❌ Cannot connect to localhost:8080",
        )
        time.sleep(2)
        error_html = f"""
        <div class="analysis-container">
            <div class="section-title status-warning">⚠️ Backend Unavailable</div>
            <div class="analysis-content">
                Cannot connect to the AI analysis backend.
                
                Please start the FastAPI server:
                <pre>python -m api.main</pre>
            </div>
        </div>
        """
        error_markdown = f"""# ⚠️ Backend Unavailable

Cannot connect to the AI analysis backend.

## Solution
Please start the FastAPI server:
```bash
python -m api.main
```
"""
        yield error_html, "", "", "", "", error_markdown
    except json.JSONDecodeError as e:
        analysis_logger.error(f"JSON parsing error: {str(e)}")
        yield create_llm_status_display(
            "❌ JSON Parsing Failed", f"❌ Invalid JSON: {str(e)[:50]}...", ""
        )
        time.sleep(2)
        error_html = f"""
        <div class="analysis-container">
            <div class="section-title status-danger">❌ Invalid JSON</div>
            <div class="analysis-content">
                Error parsing OpenAPI specification: {str(e)}
                
                Please check your JSON syntax.
            </div>
        </div>
        """
        error_markdown = f"""# ❌ Invalid JSON

**Error parsing OpenAPI specification:** {str(e)}

## Solution
Please check your JSON syntax and ensure it's valid.
"""
        yield error_html, "", "", "", "", error_markdown
    except Exception as e:
        analysis_logger.error(
            f"Unexpected error during analysis: {str(e)}", exc_info=True
        )
        yield create_llm_status_display(
            "❌ Analysis Failed", f"❌ Unexpected Error: {str(e)[:50]}...", ""
        )
        time.sleep(2)
        error_html = f"""
        <div class="analysis-container">
            <div class="section-title status-danger">❌ Analysis Error</div>
            <div class="analysis-content">
                Unexpected error: {str(e)}
            </div>
        </div>
        """
        error_markdown = f"""# ❌ Analysis Error

**Unexpected error:** {str(e)}

Please try again or check the server logs for more details.
"""
        yield error_html, "", "", "", "", error_markdown


def extract_scores_from_analysis(analysis_text: str) -> dict:
    """Extract scores from the analysis text"""
    import re

    scores = {
        "overall": 0,
        "completeness": 0,
        "documentation": 0,
        "security": 0,
        "usability": 0,
        "standards": 0,
    }

    # Extract overall score
    overall_match = re.search(r"Overall Score.*?(\d+)/100", analysis_text)
    if overall_match:
        scores["overall"] = int(overall_match.group(1))

    # Extract individual scores
    score_patterns = {
        "completeness": r"Completeness.*?(\d+)/100",
        "documentation": r"Documentation.*?(\d+)/100",
        "security": r"Security.*?(\d+)/100",
        "usability": r"Usability.*?(\d+)/100",
        "standards": r"Standards.*?(\d+)/100",
    }

    for key, pattern in score_patterns.items():
        match = re.search(pattern, analysis_text)
        if match:
            scores[key] = int(match.group(1))

    return scores


def extract_critical_issues(analysis_text: str) -> list:
    """Extract critical issues from the analysis text"""
    import re

    issues = []

    # Look for issue patterns in the analysis
    issue_pattern = r"(\d+)\.\s*\*\*Issue:\*\*\s*([^\n]+)\s*\n\s*-\s*\*\*Location:\*\*\s*([^\n]+)\s*\n\s*-\s*\*\*Impact:\*\*\s*([^\n]+)\s*\n\s*-\s*\*\*Fix:\*\*\s*([^\n]+)\s*\n\s*-\s*\*\*Priority:\*\*\s*([^\n]+)"

    matches = re.findall(issue_pattern, analysis_text, re.MULTILINE | re.DOTALL)

    for match in matches:
        issue_num, issue_desc, location, impact, fix, priority = match
        issues.append(
            {
                "number": issue_num,
                "description": issue_desc.strip(),
                "location": location.strip(),
                "impact": impact.strip(),
                "fix": fix.strip(),
                "priority": priority.strip().lower(),
            }
        )

    return issues


def format_comprehensive_analysis(ai_result: dict, spec_data: dict) -> tuple:
    """Format the complete AI analysis for display - returns (status_html, score_html, score_breakdown_html, token_usage_html, issues_html, markdown_analysis)"""

    analysis = ai_result.get("analysis", "")
    key_findings = ai_result.get("key_findings", {})
    metadata = ai_result.get("metadata", {})

    # Extract API info
    api_info = spec_data.get("info", {})
    api_title = api_info.get("title", "Unknown API")
    api_version = api_info.get("version", "Unknown")
    endpoints_count = len(spec_data.get("paths", {}))

    # Extract scores from analysis
    scores = extract_scores_from_analysis(analysis)

    # Extract critical issues
    critical_issues = extract_critical_issues(analysis)

    # Create status HTML
    status_html = f"""
    <div class="analysis-container">
        <div class="section-title">✅ Analysis Complete</div>
        <div class="analysis-content">
            <strong>API:</strong> {api_title} v{api_version} ({endpoints_count} endpoints)<br>
            <strong>Model:</strong> {metadata.get('model_used', 'Unknown')}<br>
            <strong>Analysis Time:</strong> {metadata.get('analysis_time', 'Unknown')}<br>
            <strong>Critical Issues Found:</strong> {len(critical_issues)}
        </div>
    </div>
    """

    # Create score HTML
    score_html = f"""
    <div class="score-container">
        <div class="score-circle">
            <div class="score-number">{scores['overall']}</div>
            <div class="score-label">Overall</div>
        </div>
    </div>
    """

    # Create score breakdown HTML
    score_breakdown_html = f"""
    <div class="score-breakdown">
        <div class="score-item">
            <span class="score-label">Completeness</span>
            <div class="score-bar">
                <div class="score-fill" style="width: {scores['completeness']}%"></div>
            </div>
            <span class="score-value">{scores['completeness']}/100</span>
        </div>
        <div class="score-item">
            <span class="score-label">Documentation</span>
            <div class="score-bar">
                <div class="score-fill" style="width: {scores['documentation']}%"></div>
            </div>
            <span class="score-value">{scores['documentation']}/100</span>
        </div>
        <div class="score-item">
            <span class="score-label">Security</span>
            <div class="score-bar">
                <div class="score-fill" style="width: {scores['security']}%"></div>
            </div>
            <span class="score-value">{scores['security']}/100</span>
        </div>
        <div class="score-item">
            <span class="score-label">Usability</span>
            <div class="score-bar">
                <div class="score-fill" style="width: {scores['usability']}%"></div>
            </div>
            <span class="score-value">{scores['usability']}/100</span>
        </div>
        <div class="score-item">
            <span class="score-label">Standards</span>
            <div class="score-bar">
                <div class="score-fill" style="width: {scores['standards']}%"></div>
            </div>
            <span class="score-value">{scores['standards']}/100</span>
        </div>
    </div>
    """

    # Create token usage HTML
    token_usage_html = f"""
    <div class="token-usage-container">
        <div class="section-title">🔢 Token Usage & Performance</div>
        <div class="token-content">
            <div class="token-item">
                <span class="token-label">Prompt Tokens:</span>
                <span class="token-value">{metadata.get('prompt_tokens', 0):,}</span>
            </div>
            <div class="token-item">
                <span class="token-label">Completion Tokens:</span>
                <span class="token-value">{metadata.get('completion_tokens', 0):,}</span>
            </div>
            <div class="token-item">
                <span class="token-label">Total Tokens:</span>
                <span class="token-value">{metadata.get('total_tokens', 0):,}</span>
            </div>
            <div class="token-item">
                <span class="token-label">Analysis Time:</span>
                <span class="token-value">{metadata.get('analysis_time', 0):.2f}s</span>
            </div>
            <div class="token-item">
                <span class="token-label">Model Used:</span>
                <span class="token-value">{metadata.get('model_used', 'Unknown')}</span>
            </div>
            <div class="token-item">
                <span class="token-label">API Endpoints:</span>
                <span class="token-value">{metadata.get('endpoints_count', 0)}</span>
            </div>
        </div>
    </div>
    """

    # Create critical issues HTML
    if critical_issues:
        issues_html = f"""
        <div class="issues-container">
            <div class="section-title">🚨 Critical Issues ({len(critical_issues)} found)</div>
            <div class="issues-content">
        """

        for issue in critical_issues[:5]:  # Show top 5 issues
            priority_class = issue["priority"]
            issues_html += f"""
                <div class="issue-item {priority_class}">
                    <div class="issue-title">Issue #{issue['number']}: {issue['description']}</div>
                    <div class="issue-location">📍 {issue['location']}</div>
                    <div class="issue-impact">💥 Impact: {issue['impact']}</div>
                    <div class="issue-fix">🔧 Fix: {issue['fix']}</div>
                </div>
            """

        if len(critical_issues) > 5:
            issues_html += f"""
                <div style="text-align: center; margin-top: 1rem; color: var(--text-secondary);">
                    ... and {len(critical_issues) - 5} more issues (see detailed analysis below)
                </div>
            """

        issues_html += """
            </div>
        </div>
        """
    else:
        issues_html = """
        <div class="issues-container">
            <div class="section-title">🚨 Critical Issues</div>
            <div class="issues-content">
                <p>No critical issues found! 🎉</p>
            </div>
        </div>
        """

    # Create markdown analysis with proper formatting
    markdown_analysis = f"""# 🤖 AI Analysis Results

## 📋 API Overview
- **Title:** {api_title}
- **Version:** {api_version}
- **Endpoints:** {endpoints_count}
- **Analysis Model:** {metadata.get('model_used', 'Unknown')}
- **Overall Score:** {scores['overall']}/100

---

{analysis}

---

## 🔍 Key Findings Summary
- **Critical Issues:** {len(critical_issues)}
- **Security Issues:** {key_findings.get('security_issues_count', 0)}
- **Has Authentication:** {'✅ Yes' if key_findings.get('has_authentication', False) else '❌ No'}
- **Documentation Quality:** {key_findings.get('documentation_quality', 'Unknown').title()}
"""

    return (
        status_html,
        score_html,
        score_breakdown_html,
        token_usage_html,
        issues_html,
        markdown_analysis,
    )


def create_llm_status_display(step1: str, step2: str, step3: str) -> str:
    """Create real-time LLM call status display"""
    return f"""
    <div class="analysis-container">
        <div class="section-title">🤖 Real-Time LLM Call Status</div>
        <div class="analysis-content">
            <div style="margin-bottom: 1rem; padding: 1rem; background: var(--bg-code); border-radius: 8px;">
                <strong>📋 Step 1:</strong> {step1}
            </div>
            {f'<div style="margin-bottom: 1rem; padding: 1rem; background: var(--bg-code); border-radius: 8px;"><strong>📡 Step 2:</strong> {step2}</div>' if step2 else ''}
            {f'<div style="margin-bottom: 1rem; padding: 1rem; background: var(--bg-code); border-radius: 8px;"><strong>🤖 Step 3:</strong> {step3}</div>' if step3 else ''}
        </div>
        <div style="margin-top: 1rem; padding: 0.5rem; background: var(--primary-light); color: white; border-radius: 6px; text-align: center;">
            <strong>🔍 Watching LLM Calls in Real-Time</strong>
        </div>
    </div>
    """


def create_progress_display(percentage: int, message: str) -> str:
    """Create progress display"""
    return f"""
    <div class="analysis-container">
        <div class="section-title">🔄 Analysis Progress</div>
        <div class="progress-container">
            <div class="progress-bar" style="width: {percentage}%"></div>
        </div>
        <div class="analysis-content">{message} ({percentage}%)</div>
    </div>
    """


def get_server_logs():
    """Get recent server logs"""
    try:
        log_file = f"logs/apisage_gradio_{datetime.now().strftime('%Y%m%d')}.log"
        if os.path.exists(log_file):
            with open(log_file, "r") as f:
                lines = f.readlines()
                # Get last 50 lines
                recent_lines = lines[-50:] if len(lines) > 50 else lines
                return "".join(recent_lines)
        else:
            return "No log file found. Start some analysis to generate logs."
    except Exception as e:
        return f"Error reading logs: {str(e)}"


def clear_log_display():
    """Clear the log display"""
    return "Log display cleared. Click 'Refresh Logs' to reload."


def load_sample_spec():
    """Load a comprehensive sample OpenAPI specification"""
    app_logger.info("Loading sample OpenAPI specification")
    sample = {
        "openapi": "3.0.0",
        "info": {
            "title": "User Management API",
            "version": "2.1.0",
            "description": "A comprehensive API for managing users, authentication, and profiles",
        },
        "servers": [
            {"url": "https://api.example.com/v2", "description": "Production server"},
            {
                "url": "https://staging-api.example.com/v2",
                "description": "Staging server",
            },
        ],
        "paths": {
            "/users": {
                "get": {
                    "summary": "List all users",
                    "security": [{"bearerAuth": []}],
                    "parameters": [
                        {
                            "name": "limit",
                            "in": "query",
                            "schema": {"type": "integer", "maximum": 100},
                        },
                        {
                            "name": "offset",
                            "in": "query",
                            "schema": {"type": "integer"},
                        },
                    ],
                    "responses": {
                        "200": {
                            "description": "List of users",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "users": {
                                                "type": "array",
                                                "items": {
                                                    "$ref": "#/components/schemas/User"
                                                },
                                            },
                                            "total": {"type": "integer"},
                                            "limit": {"type": "integer"},
                                            "offset": {"type": "integer"},
                                        },
                                    }
                                }
                            },
                        },
                        "401": {"description": "Unauthorized"},
                        "403": {"description": "Forbidden"},
                        "500": {"description": "Internal server error"},
                    },
                },
                "post": {
                    "summary": "Create a new user",
                    "security": [{"bearerAuth": []}],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/CreateUser"}
                            }
                        },
                    },
                    "responses": {
                        "201": {
                            "description": "User created",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/User"}
                                }
                            },
                        },
                        "400": {"description": "Bad request"},
                        "401": {"description": "Unauthorized"},
                        "409": {"description": "User already exists"},
                    },
                },
            }
        },
        "components": {
            "schemas": {
                "User": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string", "format": "uuid"},
                        "email": {"type": "string", "format": "email"},
                        "name": {"type": "string"},
                        "created_at": {"type": "string", "format": "date-time"},
                        "status": {
                            "type": "string",
                            "enum": ["active", "inactive", "suspended"],
                        },
                    },
                    "required": ["id", "email", "name", "created_at", "status"],
                },
                "CreateUser": {
                    "type": "object",
                    "properties": {
                        "email": {"type": "string", "format": "email"},
                        "name": {"type": "string", "minLength": 1, "maxLength": 100},
                        "password": {"type": "string", "minLength": 8},
                    },
                    "required": ["email", "name", "password"],
                },
            },
            "securitySchemes": {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                }
            },
        },
    }
    return json.dumps(sample, indent=2)


def create_interface():
    """Create the focused analysis interface"""

    app_logger.info("Creating Gradio interface")

    with gr.Blocks(
        title="APISage - AI-Powered API Analysis",
        theme=gr.themes.Base(
            primary_hue="blue",
            secondary_hue="slate",
            neutral_hue="slate",
            font=("Inter", "sans-serif"),
        ).set(
            body_background_fill="var(--bg-main)",
            body_text_color="var(--text-primary)",
            background_fill_primary="var(--bg-card)",
            background_fill_secondary="var(--bg-elevated)",
            border_color_primary="var(--border)",
            button_primary_background_fill="var(--primary)",
            button_primary_text_color="white",
            button_secondary_background_fill="var(--bg-elevated)",
            button_secondary_text_color="var(--text-primary)",
        ),
        css=FOCUSED_CSS,
    ) as app:
        # Header
        gr.HTML(
            """
        <div class="app-header">
            <h1>🚀 APISage</h1>
            <p>Comprehensive AI-Powered OpenAPI Analysis</p>
        </div>
        """
        )

        with gr.Row():
            # Input column
            with gr.Column(scale=1):
                gr.HTML('<div class="config-panel"><h3>🔧 Configuration</h3></div>')

                # Simple configuration
                with gr.Blocks():
                    with gr.Row():
                        provider = gr.Dropdown(
                            choices=["OpenAI", "Anthropic"],
                            value="OpenAI",
                            label="Provider",
                            scale=1,
                        )
                        model = gr.Dropdown(
                            choices=["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"],
                            value="gpt-4o-mini",
                            label="Model",
                            scale=1,
                        )

                        api_key = gr.Textbox(
                            label="API Key",
                            type="password",
                            placeholder="Enter your API key...",
                            value="",
                        )

                gr.HTML(
                    '<div class="config-panel"><h3>📝 OpenAPI Specification</h3></div>'
                )

                # OpenAPI input
                spec_input = gr.Code(
                    label="",
                    language="json",
                    value='{"openapi": "3.0.0", "info": {"title": "Your API", "version": "1.0.0"}}',
                    lines=20,
                )

                # Action buttons
                with gr.Row():
                    analyze_btn = gr.Button(
                        "🤖 Analyze API",
                        variant="primary",
                        elem_classes=["analyze-button"],
                        scale=2,
                    )
                    sample_btn = gr.Button(
                        "📋 Load Sample", variant="secondary", scale=1
                    )

            # Results column
            with gr.Column(scale=2):
                with gr.Tabs() as tabs:
                    with gr.Tab("📊 Analysis Results", id=0):
                        # Status display
                        analysis_status = gr.HTML(
                            value="""
                            <div class="analysis-container">
                                <div class="section-title">🎯 Ready for Analysis</div>
                                <div class="analysis-content">
                                    1. Configure your AI provider and model
                                    2. Enter your API key
                                    3. Paste your OpenAPI specification
                                    4. Click "🤖 Analyze API" to get comprehensive analysis
                                </div>
                            </div>
                            """
                        )

                        # Score breakdown section
                        with gr.Row():
                            with gr.Column(scale=1):
                                overall_score = gr.HTML(
                                    value="""
                                    <div class="score-container">
                                        <div class="score-circle">
                                            <div class="score-number">--</div>
                                            <div class="score-label">Overall</div>
                                        </div>
                                    </div>
                                    """,
                                    elem_classes=["score-display"],
                                )

                            with gr.Column(scale=3):
                                score_breakdown = gr.HTML(
                                    value="""
                                    <div class="score-breakdown">
                                        <div class="score-item">
                                            <span class="score-label">Completeness</span>
                                            <div class="score-bar">
                                                <div class="score-fill" style="width: 0%"></div>
                                            </div>
                                            <span class="score-value">--/100</span>
                                        </div>
                                        <div class="score-item">
                                            <span class="score-label">Documentation</span>
                                            <div class="score-bar">
                                                <div class="score-fill" style="width: 0%"></div>
                                            </div>
                                            <span class="score-value">--/100</span>
                                        </div>
                                        <div class="score-item">
                                            <span class="score-label">Security</span>
                                            <div class="score-bar">
                                                <div class="score-fill" style="width: 0%"></div>
                                            </div>
                                            <span class="score-value">--/100</span>
                                        </div>
                                        <div class="score-item">
                                            <span class="score-label">Usability</span>
                                            <div class="score-bar">
                                                <div class="score-fill" style="width: 0%"></div>
                                            </div>
                                            <span class="score-value">--/100</span>
                                        </div>
                                        <div class="score-item">
                                            <span class="score-label">Standards</span>
                                            <div class="score-bar">
                                                <div class="score-fill" style="width: 0%"></div>
                                            </div>
                                            <span class="score-value">--/100</span>
                                        </div>
                                    </div>
                                    """,
                                    elem_classes=["score-breakdown"],
                                )

                        # Token usage section
                        token_usage = gr.HTML(
                            value="""
                            <div class="token-usage-container">
                                <div class="section-title">🔢 Token Usage</div>
                                <div class="token-content">
                                    <div class="token-item">
                                        <span class="token-label">Prompt Tokens:</span>
                                        <span class="token-value">--</span>
                                    </div>
                                    <div class="token-item">
                                        <span class="token-label">Completion Tokens:</span>
                                        <span class="token-value">--</span>
                                    </div>
                                    <div class="token-item">
                                        <span class="token-label">Total Tokens:</span>
                                        <span class="token-value">--</span>
                                    </div>
                                    <div class="token-item">
                                        <span class="token-label">Analysis Time:</span>
                                        <span class="token-value">--</span>
                                    </div>
                                </div>
                            </div>
                            """,
                            elem_classes=["token-usage-display"],
                        )

                        # Critical issues section
                        critical_issues = gr.HTML(
                            value="""
                            <div class="issues-container">
                                <div class="section-title">🚨 Critical Issues</div>
                                <div class="issues-content">
                                    <p>No analysis performed yet. Critical issues will appear here after analysis.</p>
                                </div>
                            </div>
                            """,
                            elem_classes=["issues-display"],
                        )

                        # Markdown analysis output
                        analysis_output = gr.Markdown(
                            value="*Detailed analysis results will appear here after processing...*",
                            elem_classes=["analysis-markdown"],
                        )

                    with gr.Tab("📝 Server Logs", id=1):
                        with gr.Blocks():
                            with gr.Row():
                                refresh_logs_btn = gr.Button(
                                    "🔄 Refresh Logs", variant="secondary", scale=1
                                )
                                clear_logs_btn = gr.Button(
                                    "🗑️ Clear Display", variant="secondary", scale=1
                                )

                                server_logs = gr.Textbox(
                                    label="Real-Time Server Logs",
                                    value="Click 'Refresh Logs' to see server activity...",
                                    lines=25,
                                    max_lines=25,
                                    interactive=False,
                                    show_copy_button=True,
                                )

        # Connect events with logging
        def analysis_wrapper(spec_text, provider, model, api_key):
            """Wrapper to consume the generator and return the final analysis."""
            app_logger.info(
                f"Analysis button clicked - Provider: {provider}, Model: {model}, "
                f"Spec length: {len(spec_text)} chars, API key provided: {bool(api_key)}"
            )

            final_status = None
            final_score = None
            final_breakdown = None
            final_token_usage = None
            final_issues = None
            final_analysis = None

            for output in analyze_api_comprehensive(
                spec_text, provider, model, api_key
            ):
                if isinstance(output, tuple) and len(output) == 6:
                    (
                        final_status,
                        final_score,
                        final_breakdown,
                        final_token_usage,
                        final_issues,
                        final_analysis,
                    ) = output
                elif isinstance(output, tuple) and len(output) == 5:
                    # Handle previous format
                    (
                        final_status,
                        final_score,
                        final_breakdown,
                        final_issues,
                        final_analysis,
                    ) = output
                    final_token_usage = ""
                elif isinstance(output, tuple) and len(output) == 2:
                    # Handle legacy format
                    final_status, final_analysis = output
                    final_score = ""
                    final_breakdown = ""
                    final_token_usage = ""
                    final_issues = ""
                else:
                    # Handle single output format
                    final_status = output
                    final_score = ""
                    final_breakdown = ""
                    final_token_usage = ""
                    final_issues = ""
                    final_analysis = (
                        "*Analysis results will appear here after processing...*"
                    )

            return (
                final_status,
                final_score,
                final_breakdown,
                final_token_usage,
                final_issues,
                final_analysis,
            )

        def log_sample_click():
            """Wrapper to log sample button clicks"""
            app_logger.info("Sample button clicked")
            return load_sample_spec()

        analyze_btn.click(
            fn=analysis_wrapper,
            inputs=[spec_input, provider, model, api_key],
            outputs=[
                analysis_status,
                overall_score,
                score_breakdown,
                token_usage,
                critical_issues,
                analysis_output,
            ],
        )

        sample_btn.click(fn=log_sample_click, outputs=[spec_input])

        # Log viewer events
        refresh_logs_btn.click(fn=get_server_logs, outputs=[server_logs])

        clear_logs_btn.click(fn=clear_log_display, outputs=[server_logs])

    app_logger.info("Gradio interface created successfully")
    return app


if __name__ == "__main__":
    app_logger.info("Starting APISage Gradio application")

    try:
        app = create_interface()
        app_logger.info("Launching Gradio server on port 7860")

        app.launch(
            server_name="0.0.0.0", server_port=7860, share=False, show_error=True
        )
    except Exception as e:
        app_logger.error(f"Failed to start application: {str(e)}", exc_info=True)
        sys.exit(1)
