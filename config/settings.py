#!/usr/bin/env python3
"""
Gradio interface for APISage Enhanced OpenAPI Analysis - FIXED VERSION
Provides a user-friendly web interface for comprehensive API documentation analysis
"""

import json
import logging
import os
import time
from typing import Any, Dict, Optional, Tuple

import gradio as gr
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configuration from environment variables
API_BASE_URL = os.getenv("APISAGE_URL", "http://localhost:8080")
GRADIO_PORT = int(os.getenv("GRADIO_PORT", "7860"))
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", "10485760"))  # 10MB default
TIMEOUT_HEALTH = int(os.getenv("TIMEOUT_HEALTH", "30"))
TIMEOUT_API_KEY = int(os.getenv("TIMEOUT_API_KEY", "60"))
TIMEOUT_ANALYSIS = int(os.getenv("TIMEOUT_ANALYSIS", "600"))


def validate_openapi_spec(content: str) -> Tuple[bool, str]:
    """Validate OpenAPI specification format and structure"""
    try:
        if not content or not content.strip():
            return False, "Please provide an OpenAPI specification"

        # Check file size
        if len(content.encode("utf-8")) > MAX_FILE_SIZE:
            return (
                False,
                f"OpenAPI specification too large. Maximum size: {MAX_FILE_SIZE // 1024 // 1024}MB",
            )

        # Parse JSON
        spec_data = json.loads(content)

        # Basic OpenAPI validation
        if not isinstance(spec_data, dict):
            return False, "Invalid OpenAPI specification - must be a JSON object"

        if not spec_data.get("openapi"):
            return (
                False,
                "Invalid OpenAPI specification - missing 'openapi' version field",
            )

        if not spec_data.get("info"):
            return False, "Invalid OpenAPI specification - missing 'info' section"

        return True, "Valid OpenAPI specification"

    except json.JSONDecodeError as e:
        return False, f"Invalid JSON format: {str(e)}"
    except Exception as e:
        return False, f"Validation error: {str(e)}"


def check_server_health() -> Tuple[bool, str]:
    """Check if the APISage server is running"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=TIMEOUT_HEALTH)
        if response.status_code == 200:
            return True, "✅ APISage server is running and healthy"
        else:
            return False, f"❌ Server responded with status {response.status_code}"
    except requests.exceptions.RequestException as e:
        logger.error(f"Server health check failed: {e}")
        return False, f"❌ Cannot connect to APISage server: {str(e)}"


def set_openai_api_key(api_key: str) -> str:
    """Set OpenAI API key for enhanced analysis"""
    if not api_key or not api_key.strip():
        return "⚠️ Please enter a valid OpenAI API key"

    # Basic API key format validation
    api_key = api_key.strip()
    if not api_key.startswith("sk-") or len(api_key) < 20:
        return "⚠️ Invalid API key format. OpenAI API keys should start with 'sk-'"

    try:
        response = requests.post(
            f"{API_BASE_URL}/set-api-key",
            json={"api_key": api_key},
            timeout=TIMEOUT_API_KEY,
        )

        if response.status_code == 200:
            result = response.json()
            if result.get("status") == "success":
                logger.info("OpenAI API key set successfully")
                return "✅ OpenAI API key set successfully! Enhanced analysis is now available."
            else:
                error_msg = result.get("message", "Unknown error")
                logger.warning(f"Failed to set API key: {error_msg}")
                return f"⚠️ Failed to set API key: {error_msg}"
        else:
            logger.error(f"API key setting failed with status {response.status_code}")
            return f"❌ Failed to set API key. Server responded with status {response.status_code}"

    except requests.exceptions.RequestException as e:
        logger.error(f"Network error setting API key: {e}")
        return f"❌ Failed to set API key: {str(e)}"


def analyze_openapi_spec(spec_content: str) -> Tuple[str, str, str, str]:
    """
    Analyze OpenAPI specification and return formatted results
    Returns: (status, overview, detailed_analysis, action_items)
    """
    logger.info(f"Starting analysis, spec_size={len(spec_content)}")

    # Validate input first
    is_valid, validation_message = validate_openapi_spec(spec_content)
    if not is_valid:
        return (f"❌ Error: {validation_message}", "", "", "")

    try:
        # Try different analysis endpoints in order of preference
        analysis_endpoints = [
            "/analyze/detailed",  # Most comprehensive
            "/analyze",  # Basic analysis
        ]

        analysis_result = None
        endpoint_used = None

        for endpoint in analysis_endpoints:
            try:
                logger.info(f"Trying endpoint: {endpoint}")
                response = requests.post(
                    f"{API_BASE_URL}{endpoint}",
                    json={"content": spec_content.strip()},
                    timeout=TIMEOUT_ANALYSIS,
                )

                logger.info(f"Response status: {response.status_code}")

                if response.status_code == 200:
                    result = response.json()
                    logger.info(
                        f"Response keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}"
                    )

                    # Try multiple ways to extract the analysis data
                    analysis_result = (
                        result.get("result")
                        or result.get("analysis")
                        or result.get("data")
                        or result
                    )

                    if analysis_result and isinstance(analysis_result, dict):
                        endpoint_used = endpoint
                        logger.info(f"Successfully got analysis from {endpoint}")
                        break
                    else:
                        logger.warning(f"No valid analysis data from {endpoint}")

            except requests.exceptions.Timeout:
                logger.warning(f"Timeout on {endpoint}, trying next...")
                continue
            except Exception as e:
                logger.warning(f"Error on {endpoint}: {e}, trying next...")
                continue

        if not analysis_result:
            logger.error("No analysis results from any endpoint")
            return (
                "❌ No analysis results received from server. Check server logs for details.",
                "",
                "",
                "",
            )

        logger.info(f"Using analysis result from {endpoint_used}")
        return format_analysis_results(analysis_result, endpoint_used)

    except requests.exceptions.Timeout:
        logger.error("Analysis request timed out")
        return (
            "⏱️ Analysis timed out after 10 minutes. The specification might be very complex.",
            "",
            "",
            "",
        )
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error during analysis: {e}")
        return (f"❌ Network error during analysis: {str(e)}", "", "", "")
    except Exception as e:
        logger.error(f"Unexpected error during analysis: {e}")
        return (f"❌ Unexpected error: {str(e)}", "", "", "")


def format_analysis_results(
    analysis: Dict[str, Any], endpoint_used: str = "unknown"
) -> Tuple[str, str, str, str]:
    """
    Formats the analysis results from both simple and detailed API responses.
    """
    logger.info(
        f"Formatting results from {endpoint_used}, keys: {list(analysis.keys()) if isinstance(analysis, dict) else 'Not a dict'}"
    )

    # Check if this is a detailed analysis response
    if "executive_briefing" in analysis or "detailed_sections" in analysis:
        logger.info("Using detailed analysis formatter")
        return format_detailed_analysis_results(analysis, endpoint_used)

    # Handle simple analysis response (fallback)
    logger.info("Using simple analysis formatter")

    # Extract data with defaults - be more flexible with key names
    score = analysis.get("score", analysis.get("overall_score", 0))
    grade = analysis.get("grade", analysis.get("overall_grade", "N/A"))
    summary = (
        analysis.get("summary")
        or analysis.get("overview")
        or analysis.get("description")
        or "Analysis completed successfully."
    )

    # Handle different issue formats
    issues = []
    if "issues" in analysis:
        issues = analysis["issues"]
    elif "validation_issues" in analysis:
        issues = analysis["validation_issues"]
    elif "problems" in analysis:
        issues = analysis["problems"]

    # Handle different recommendation formats
    recommendations = []
    if "recommendations" in analysis:
        recommendations = analysis["recommendations"]
    elif "suggestions" in analysis:
        recommendations = analysis["suggestions"]
    elif "improvements" in analysis:
        recommendations = analysis["improvements"]

    analysis_method = analysis.get(
        "analysis_method", analysis.get("method", "rule_based")
    )

    # 1. Create Status Message
    status = f"✅ Analysis Complete! | Score: {score}/100 ({grade}) | Method: {analysis_method.replace('_', ' ').title()} | Endpoint: {endpoint_used}"

    # 2. Create Overview Markdown
    overview_md = f"""# 📊 Analysis Overview

**Overall Score:** {score}/100
**Grade:** {grade}
**Analysis Method:** {analysis_method.replace('_', ' ').title()}
**API Endpoint Used:** {endpoint_used}

---

### 📝 Summary
{summary}

---

### 📉 At a Glance
- **Issues Found:** {len(issues)}
- **Recommendations:** {len(recommendations)}

### 📋 Analysis Details
- **Server Response Keys:** {', '.join(analysis.keys()) if isinstance(analysis, dict) else 'N/A'}
- **Analysis Timestamp:** {analysis.get('timestamp', 'N/A')}
"""

    # 3. Create Detailed Analysis Markdown (for issues)
    detailed_md = "# 🔍 Detailed Findings\n\n"
    if not issues:
        detailed_md += "✅ No specific issues were found. Well done!"
    else:
        # Sort issues by severity if severity field exists
        try:
            severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
            sorted_issues = sorted(
                issues, key=lambda i: severity_order.get(i.get("severity", "LOW"), 4)
            )
        except:
            sorted_issues = issues

        for i, issue in enumerate(sorted_issues, 1):
            if isinstance(issue, dict):
                severity = issue.get("severity", "INFO")
                message = issue.get(
                    "message", issue.get("description", "No details provided.")
                )
                location = issue.get("location", issue.get("path"))
                fix = issue.get("fix", issue.get("solution"))
                rule_name = issue.get("rule_name", issue.get("rule", issue.get("type")))

                emoji = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🔵"}.get(
                    severity, "⚪"
                )

                detailed_md += f"### {emoji} Issue #{i}: {rule_name or severity}\n\n"
                detailed_md += f"**Description:** {message}\n\n"
                if location:
                    detailed_md += f"**Location:** `{location}`\n\n"
                if fix:
                    detailed_md += f"**Suggested Fix:** {fix}\n\n"
            else:
                # Handle string issues
                detailed_md += f"{i}. {issue}\n\n"

            detailed_md += "---\n\n"

    # 4. Create Action Items Markdown (for recommendations)
    action_md = "# 🗺️ Action Roadmap\n\n"
    if not recommendations:
        action_md += (
            "✅ No specific recommendations were provided. The API is in good shape!"
        )
    else:
        action_md += "### Top Recommendations to Improve Your API\n\n"
        for i, rec in enumerate(recommendations, 1):
            if isinstance(rec, dict):
                title = rec.get("title", rec.get("name", f"Recommendation {i}"))
                description = rec.get("description", rec.get("details", ""))
                priority = rec.get("priority", rec.get("severity", ""))

                action_md += f"{i}. **{title}**"
                if priority:
                    action_md += f" ({priority})"
                action_md += "\n"
                if description:
                    action_md += f"   {description}\n"
            else:
                action_md += f"{i}. {rec}\n"
            action_md += "\n"

    return status, overview_md, detailed_md, action_md


def format_detailed_analysis_results(
    analysis: Dict[str, Any], endpoint_used: str = "unknown"
) -> Tuple[str, str, str, str]:
    """
    Formats the detailed analysis results from the enhanced evaluator.
    """
    logger.info("Formatting detailed analysis results")

    # Extract detailed analysis components
    executive_briefing = analysis.get(
        "executive_briefing", "No executive briefing available."
    )
    detailed_sections = analysis.get("detailed_sections", {})
    action_plan = analysis.get("action_plan", {})

    # 1. Create Status Message - Enhanced for detailed analysis
    status = f"✅ Comprehensive Analysis Complete! | Method: DEEP Framework | Endpoint: {endpoint_used}"

    # 2. Create Overview from Executive Briefing
    overview_md = executive_briefing

    # 3. Create Detailed Analysis by combining all detailed sections
    detailed_md = ""

    # Add architecture analysis
    if "architecture" in detailed_sections:
        detailed_md += detailed_sections["architecture"]
        detailed_md += "\n\n---\n\n"

    # Add security analysis
    if "security" in detailed_sections:
        detailed_md += detailed_sections["security"]
        detailed_md += "\n\n---\n\n"

    # Add developer experience analysis
    if "developer_experience" in detailed_sections:
        detailed_md += detailed_sections["developer_experience"]
        detailed_md += "\n\n---\n\n"

    # Add performance analysis
    if "performance" in detailed_sections:
        detailed_md += detailed_sections["performance"]
        detailed_md += "\n\n---\n\n"

    # Remove trailing separator
    detailed_md = detailed_md.rstrip("\n\n---\n\n")

    if not detailed_md.strip():
        detailed_md = "# 🔍 Detailed Analysis\n\n*Detailed analysis sections are being prepared. This may occur when the LLM is unavailable or the analysis is still processing.*"

    # 4. Create Action Items from Action Plan
    action_md = "# 🗺️ Strategic Action Plan\n\n"

    if action_plan:
        # Quick wins
        quick_wins = action_plan.get("quick_wins", [])
        if quick_wins:
            action_md += "## 🚀 Quick Wins (1-2 weeks)\n"
            action_md += "*High impact, low effort improvements you can implement immediately.*\n\n"
            for i, win in enumerate(quick_wins, 1):
                if isinstance(win, dict):
                    task = win.get("task", "Unknown task")
                    rationale = win.get("detailed_rationale", "")
                    implementation = win.get("implementation_guide", "")
                    outcome = win.get("expected_outcome", "")

                    action_md += f"### {i}. {task}\n\n"
                    if rationale:
                        action_md += f"**Why this matters:** {rationale}\n\n"
                    if implementation:
                        action_md += f"**How to implement:** {implementation}\n\n"
                    if outcome:
                        action_md += f"**Expected outcome:** {outcome}\n\n"
                else:
                    action_md += f"{i}. {win}\n"
            action_md += "\n---\n\n"

        # Medium term improvements
        medium_term = action_plan.get("medium_term", [])
        if medium_term:
            action_md += "## 📈 Medium-Term Improvements (1-3 months)\n"
            action_md += (
                "*Substantial improvements requiring more planning and resources.*\n\n"
            )
            for i, improvement in enumerate(medium_term, 1):
                if isinstance(improvement, dict):
                    task = improvement.get("task", "Unknown task")
                    rationale = improvement.get("detailed_rationale", "")
                    phases = improvement.get("implementation_phases", [])
                    resources = improvement.get("resource_requirements", "")

                    action_md += f"### {i}. {task}\n\n"
                    if rationale:
                        action_md += f"**Strategic value:** {rationale}\n\n"
                    if phases:
                        action_md += "**Implementation phases:**\n"
                        for phase in phases:
                            action_md += f"- {phase}\n"
                        action_md += "\n"
                    if resources:
                        action_md += f"**Resource requirements:** {resources}\n\n"
                else:
                    action_md += f"{i}. {improvement}\n"
            action_md += "\n---\n\n"

        # Strategic initiatives
        strategic = action_plan.get("strategic", [])
        if strategic:
            action_md += "## 🎯 Strategic Initiatives (3-12 months)\n"
            action_md += (
                "*Long-term transformational changes for competitive advantage.*\n\n"
            )
            for i, initiative in enumerate(strategic, 1):
                if isinstance(initiative, dict):
                    name = initiative.get("initiative", "Unknown initiative")
                    business_case = initiative.get("business_case", "")
                    technical_requirements = initiative.get(
                        "technical_requirements", ""
                    )
                    success_criteria = initiative.get("success_criteria", "")

                    action_md += f"### {i}. {name}\n\n"
                    if business_case:
                        action_md += f"**Business case:** {business_case}\n\n"
                    if technical_requirements:
                        action_md += (
                            f"**Technical requirements:** {technical_requirements}\n\n"
                        )
                    if success_criteria:
                        action_md += f"**Success criteria:** {success_criteria}\n\n"
                else:
                    action_md += f"{i}. {initiative}\n"

    if not action_plan:
        action_md += "*Action plan is being generated. This comprehensive roadmap will include quick wins, medium-term improvements, and strategic initiatives.*"

    return status, overview_md, detailed_md, action_md


def get_server_logs() -> str:
    """Get server logs from the running server"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=TIMEOUT_HEALTH)
        if response.status_code == 200:
            health_data = response.json()

            logs_info = f"""# 📋 Server Status & Logs

## 🏥 Health Check
- **Status:** {health_data.get('status', 'Unknown')}
- **Timestamp:** {health_data.get('timestamp', 'Unknown')}

## 🔧 Components Status
"""

            components = health_data.get("components", {})
            for component, status in components.items():
                emoji = (
                    "✅"
                    if status == "healthy"
                    else "❌"
                    if status == "unavailable"
                    else "⚠️"
                )
                logs_info += f"- **{component}:** {emoji} {status}\n"

            logs_info += f"\n## 📊 System Info\n"
            logs_info += f"- **Model:** {health_data.get('model', 'Unknown')}\n"
            logs_info += f"- **Message:** {health_data.get('message', 'Unknown')}\n"

            logs_info += f"\n## 📝 Recent Activity\n"
            logs_info += "*Note: Detailed server logs are available in the terminal where the server is running.*\n"
            logs_info += "*To see real-time logs, run the server with:*\n"
            logs_info += "```\npoetry run uvicorn api.main:app --host 0.0.0.0 --port 8080 --reload\n```"

            return logs_info
        else:
            return f"❌ Failed to get server logs. Server responded with status {response.status_code}"

    except requests.exceptions.RequestException as e:
        return f"❌ Cannot connect to server for logs: {str(e)}\n\nMake sure the APISage server is running with:\n```bash\npoetry run uvicorn api.main:app --host 0.0.0.0 --port 8080 --reload\n```"


def get_analysis_logs() -> str:
    """Get recent analysis logs by making a test request"""
    try:
        test_spec = '{"openapi": "3.0.0", "info": {"title": "Test", "version": "1.0.0"}, "paths": {"/test": {"get": {"responses": {"200": {"description": "OK"}}}}}}'

        response = requests.post(
            f"{API_BASE_URL}/analyze",
            json={"content": test_spec},
            timeout=TIMEOUT_ANALYSIS,
        )

        if response.status_code == 200:
            result = response.json()
            analysis = result.get("result", result.get("analysis", result))

            log_info = "# 🔍 Analysis Logs\n\n"
            log_info += "## 📊 Test Analysis Result\n"
            log_info += f"- **Status:** Success ✅\n"
            log_info += f"- **Response Keys:** {', '.join(result.keys()) if isinstance(result, dict) else 'N/A'}\n"

            if isinstance(analysis, dict):
                log_info += f"- **Analysis Keys:** {', '.join(analysis.keys())}\n"
                log_info += f"- **Validation Issues:** {len(analysis.get('validation_issues', analysis.get('issues', [])))}\n"
                log_info += f"- **Grade:** {analysis.get('grade', 'N/A')}\n"

            log_info += "\n## 💡 Note\n"
            log_info += "*Detailed server logs with step-by-step execution are available in the terminal running the server.*\n"
            log_info += "*Check the server terminal for verbose logging output during analysis.*"

            return log_info
        else:
            return f"❌ Test analysis request failed with status {response.status_code}: {response.text}"

    except Exception as e:
        return f"❌ Failed to get analysis logs: {str(e)}"


def load_sample_openapi_spec() -> str:
    """Load a sample OpenAPI specification for testing"""

    sample_spec = {
        "openapi": "3.0.0",
        "info": {
            "title": "Sample E-commerce API",
            "version": "1.2.0",
            "description": "A comprehensive e-commerce API for managing products, orders, and customers",
            "contact": {
                "name": "API Support Team",
                "email": "api-support@example.com",
                "url": "https://example.com/support",
            },
            "license": {"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
        },
        "servers": [
            {"url": "https://api.example.com/v1", "description": "Production server"}
        ],
        "security": [{"BearerAuth": []}],
        "paths": {
            "/products": {
                "get": {
                    "summary": "List all products",
                    "description": "Retrieve a paginated list of products with optional filtering",
                    "tags": ["Products"],
                    "parameters": [
                        {
                            "name": "limit",
                            "in": "query",
                            "description": "Maximum number of products to return",
                            "required": False,
                            "schema": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 100,
                                "default": 20,
                            },
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "List of products retrieved successfully",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "products": {
                                                "type": "array",
                                                "items": {
                                                    "$ref": "#/components/schemas/Product"
                                                },
                                            }
                                        },
                                    }
                                }
                            },
                        }
                    },
                }
            }
        },
        "components": {
            "securitySchemes": {
                "BearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                }
            },
            "schemas": {
                "Product": {
                    "type": "object",
                    "required": ["id", "name", "price"],
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "Unique product identifier",
                            "example": "prod_123",
                        },
                        "name": {
                            "type": "string",
                            "description": "Product name",
                            "example": "Wireless Headphones",
                        },
                        "price": {
                            "type": "number",
                            "format": "decimal",
                            "minimum": 0,
                            "description": "Product price in USD",
                            "example": 99.99,
                        },
                    },
                }
            },
        },
    }

    return json.dumps(sample_spec, indent=2)


def create_gradio_interface():
    """Create and configure the Gradio interface"""

    custom_css = """
    .gradio-container {
        max-width: 1200px !important;
    }
    .header-text {
        text-align: center;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    """

    with gr.Blocks(css=custom_css, title="APISage Enhanced Analysis - FIXED") as app:
        gr.HTML(
            """
        <div class="header-text">
            <h1>🎯 APISage Enhanced OpenAPI Analysis - FIXED VERSION</h1>
            <p>Fixed response parsing and error handling for reliable analysis</p>
        </div>
        """
        )

        # Server status check
        with gr.Row():
            server_status = gr.Textbox(
                label="🔧 Server Status",
                value="Checking server status...",
                interactive=False,
            )
            check_btn = gr.Button("🔄 Check Server", size="sm")

        # API Key configuration
        with gr.Row():
            with gr.Column(scale=3):
                api_key_input = gr.Textbox(
                    label="🔑 OpenAI API Key (Optional)",
                    placeholder="sk-...",
                    type="password",
                    info="Provide your OpenAI API key for enhanced analysis",
                )
            with gr.Column(scale=1):
                set_key_btn = gr.Button("🔐 Set API Key", size="sm")

        api_key_status = gr.Textbox(
            label="API Key Status",
            value="No API key set - will use rule-based analysis",
            interactive=False,
        )

        # Main analysis interface
        with gr.Row():
            with gr.Column(scale=1):
                spec_input = gr.Textbox(
                    label="📄 OpenAPI 3.0 Specification (JSON)",
                    placeholder="Paste your OpenAPI 3.0 JSON specification here...",
                    lines=15,
                    max_lines=25,
                    info="Provide a valid OpenAPI 3.0 JSON specification for analysis",
                )

                with gr.Row():
                    analyze_btn = gr.Button(
                        "🚀 Analyze OpenAPI Spec", variant="primary", size="lg"
                    )
                    sample_btn = gr.Button("📋 Load Sample Spec", variant="secondary")
                    clear_btn = gr.Button("🧹 Clear", variant="secondary")

        # Results section
        with gr.Row():
            analysis_status = gr.Textbox(
                label="📊 Analysis Status", interactive=False, lines=2
            )

        with gr.Tabs():
            with gr.TabItem("📈 Overview"):
                overview_output = gr.Markdown(
                    label="Analysis Overview",
                    value="*No analysis performed yet. Please provide an OpenAPI specification and click 'Analyze'.*",
                )

            with gr.TabItem("🔍 Detailed Analysis"):
                detailed_output = gr.Markdown(
                    label="Detailed Analysis Results",
                    value="*Detailed analysis will appear here after processing.*",
                )

            with gr.TabItem("🗺️ Action Items"):
                actions_output = gr.Markdown(
                    label="Action Items & Roadmap",
                    value="*Action items and improvement roadmap will appear here.*",
                )

            with gr.TabItem("📋 Server Logs"):
                logs_output = gr.Markdown(
                    label="Server Status & Logs",
                    value="*Server logs and status information will appear here.*",
                )
                with gr.Row():
                    refresh_logs_btn = gr.Button("🔄 Refresh Logs", size="sm")
                    analysis_logs_btn = gr.Button("🔍 Show Analysis Logs", size="sm")

        # Event handlers
        def on_check_server():
            is_healthy, message = check_server_health()
            return message

        def on_set_api_key(api_key):
            return set_openai_api_key(api_key)

        def on_analyze(spec_content):
            return analyze_openapi_spec(spec_content)

        def on_load_sample():
            return load_sample_openapi_spec()

        def on_clear():
            return "", "", "", "", "", get_server_logs()

        def on_refresh_logs():
            return get_server_logs()

        def on_show_analysis_logs():
            return get_analysis_logs()

        # Connect event handlers
        check_btn.click(fn=on_check_server, outputs=[server_status])

        set_key_btn.click(
            fn=on_set_api_key, inputs=[api_key_input], outputs=[api_key_status]
        )

        analyze_btn.click(
            fn=on_analyze,
            inputs=[spec_input],
            outputs=[analysis_status, overview_output, detailed_output, actions_output],
            show_progress=True,
        )

        sample_btn.click(fn=on_load_sample, outputs=[spec_input])

        clear_btn.click(
            fn=on_clear,
            outputs=[
                spec_input,
                analysis_status,
                overview_output,
                detailed_output,
                actions_output,
                logs_output,
            ],
        )

        refresh_logs_btn.click(fn=on_refresh_logs, outputs=[logs_output])

        analysis_logs_btn.click(fn=on_show_analysis_logs, outputs=[logs_output])

        # Initial server status check
        app.load(fn=on_check_server, outputs=[server_status])

        # Initial logs load
        app.load(fn=on_refresh_logs, outputs=[logs_output])

    return app


def main():
    """Main function to start the Gradio interface"""

    print("🎯 Starting APISage Enhanced Analysis - Gradio Interface (FIXED)")
    print("=" * 60)

    # Check if server is running
    is_healthy, message = check_server_health()
    if not is_healthy:
        print(f"\n⚠️  Warning: {message}")
        print("\nPlease make sure the APISage server is running:")
        print("  poetry run uvicorn api.main:app --host 0.0.0.0 --port 8080 --reload")
        print(
            "\nThe Gradio interface will still start, but analysis won't work until the server is available.\n"
        )
    else:
        print(f"\n✅ {message}")
        print(f"🌐 Starting Gradio interface on http://localhost:{GRADIO_PORT}")

    # Create and launch the interface
    app = create_gradio_interface()

    try:
        app.launch(
            server_name="0.0.0.0",
            server_port=GRADIO_PORT,
            share=False,
            show_error=True,
            quiet=False,
            favicon_path=None,
            ssl_verify=False,
        )
    except KeyboardInterrupt:
        print("\n👋 Gradio interface stopped by user")
    except Exception as e:
        print(f"\n❌ Failed to start Gradio interface: {e}")


if __name__ == "__main__":
    main()
