#!/usr/bin/env python3
"""
Fixed Multi-Page Gradio UI for APISage - Real LLM Integration Working
"""

import os
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import gradio as gr

# Import APISage components for real LLM analysis
from agents.api_analyzer import APIAnalyzer
from config.settings import AgentConfig, SystemConfig


def create_working_interface():
    """Create working multi-page Gradio interface with real LLM integration"""
    
    with gr.Blocks(
        title="APISage - API Documentation Quality Analyzer",
        theme=gr.themes.Soft(),
        css="""
        .gradio-container { 
            max-width: 1200px !important; 
            margin: 0 auto; 
        }
        .main-header {
            text-align: center;
            background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
            padding: 2rem; 
            border-radius: 15px; 
            margin-bottom: 2rem; 
            color: white;
            box-shadow: 0 8px 25px rgba(99, 102, 241, 0.3);
        }
        .page-section {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(99, 102, 241, 0.2);
            border-radius: 12px; 
            padding: 2rem; 
            margin: 1rem 0;
            backdrop-filter: blur(10px);
        }
        
        /* Enhanced loading animations */
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        
        .loading-spinner {
            animation: spin 2s linear infinite;
            display: inline-block;
        }
        
        .pulse-text {
            animation: pulse 2s ease-in-out infinite;
        }
        
        .fade-in {
            animation: fadeIn 0.8s ease-out;
        }
        
        /* Enhanced button styling */
        .primary-button {
            background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
            border: none !important;
            color: white !important;
            font-weight: 600 !important;
            transition: all 0.3s ease !important;
        }
        
        .primary-button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 8px 25px rgba(99, 102, 241, 0.4) !important;
        }
        
        .primary-button:disabled {
            opacity: 0.6 !important;
            cursor: not-allowed !important;
            transform: none !important;
        }
        
        /* Status indicators */
        .status-success {
            color: #10b981 !important;
            font-weight: 600 !important;
        }
        
        .status-error {
            color: #ef4444 !important;
            font-weight: 600 !important;
        }
        
        .status-info {
            color: #3b82f6 !important;
            font-weight: 600 !important;
        }
        
        /* Progress bar styling */
        .progress-container {
            background: rgba(99, 102, 241, 0.1);
            border-radius: 10px;
            padding: 1rem;
            margin: 1rem 0;
        }
        """
    ) as interface:
        
        # Header
        gr.HTML("""
        <div class="main-header">
            <h1>🚀 APISage - API Documentation Quality Analyzer</h1>
            <p style="font-size: 1.2rem; margin: 0; opacity: 0.9;">
                Upload your API documentation and get comprehensive quality analysis
            </p>
            <p style="font-size: 1rem; margin: 0.5rem 0 0 0; opacity: 0.8;">
                Real AI Analysis - Powered by APISage LLM Engine
            </p>
        </div>
        """)
        
        # Analysis state
        analysis_state = gr.State({"is_running": False, "current_session": None})
        
        # Multi-page tabs
        with gr.Tabs() as tabs:
            
            # Page 1: Upload
            with gr.Tab("📄 Upload & Input", id="upload_tab"):
                with gr.Row():
                    with gr.Column():
                        gr.HTML('<h2>📁 File Upload</h2>')
                        file_upload = gr.File(
                            label="Choose Documentation File",
                            file_types=[".md", ".json", ".yaml", ".yml", ".txt"],
                            elem_classes=["page-section"]
                        )
                        file_status = gr.HTML("📄 Ready for file upload", elem_classes=["status-info"])
                    
                    with gr.Column():
                        gr.HTML('<h2>✏️ Text Input</h2>')
                        manual_input = gr.Textbox(
                            label="Paste Documentation",
                            placeholder="Paste your API documentation here...",
                            lines=15,
                            elem_classes=["page-section"]
                        )
                        text_status = gr.HTML("✏️ Ready for text input", elem_classes=["status-info"])
                
                # Input validation
                input_validation = gr.HTML("", elem_classes=["status-info"])
            
            # Page 2: Configuration
            with gr.Tab("⚙️ Configuration", id="config_tab"):
                with gr.Row():
                    with gr.Column():
                        gr.HTML('<h2>🤖 LLM Provider</h2>')
                        provider_choice = gr.Dropdown(
                            choices=[
                                ("OpenAI GPT", "openai"),
                                ("Anthropic Claude", "anthropic"),
                                ("Google Gemini", "google"),
                                ("Ollama Local", "ollama")
                            ],
                            value="openai",
                            label="Select Provider"
                        )
                        
                        openai_api_key = gr.Textbox(
                            label="OpenAI API Key",
                            type="password",
                            value=os.getenv("OPENAI_API_KEY", ""),
                            placeholder="sk-..."
                        )
                        
                        openai_model = gr.Dropdown(
                            choices=[
                                ("GPT-4o Mini", "gpt-4o-mini"),
                                ("GPT-4o", "gpt-4o"),
                                ("GPT-4 Turbo", "gpt-4-turbo")
                            ],
                            value="gpt-4o-mini",
                            label="Model"
                        )
                        
                        # API key validation
                        api_key_status = gr.HTML("", elem_classes=["status-info"])
                    
                    with gr.Column():
                        gr.HTML('<h2>🎛️ Analysis Settings</h2>')
                        temperature = gr.Slider(
                            minimum=0, maximum=1, value=0.7, step=0.1,
                            label="Temperature"
                        )
                        max_tokens = gr.Slider(
                            minimum=500, maximum=4000, value=2000, step=100,
                            label="Max Tokens"
                        )
                        
                        # Configuration validation
                        config_validation = gr.HTML("", elem_classes=["status-info"])
                        
                        analyze_btn = gr.Button(
                            "🔍 Analyze Documentation",
                            variant="primary", 
                            size="lg",
                            elem_classes=["primary-button"]
                        )
            
            # Page 3: Results
            with gr.Tab("📊 Results", id="results_tab"):
                # Progress indicator
                progress_container = gr.HTML("", visible=False)
                
                # Status and results
                status_text = gr.HTML("Ready to analyze", elem_classes=["status-info"])
                
                with gr.Row():
                    overall_score = gr.Number(label="Overall Score", interactive=False)
                    grade = gr.Textbox(label="Grade", interactive=False)
                
                summary_text = gr.Textbox(
                    label="Summary", 
                    lines=4, 
                    interactive=False
                )
                
                with gr.Tabs():
                    with gr.Tab("📊 Criteria"):
                        criteria_results = gr.HTML()
                    
                    with gr.Tab("💡 Recommendations"):
                        recommendations = gr.HTML()
                    
                    with gr.Tab("📄 Raw Data"):
                        raw_output = gr.JSON()
                
                # Action buttons
                with gr.Row():
                    download_btn = gr.DownloadButton(
                        "📥 Download Report", 
                        visible=False
                    )
                    reset_btn = gr.Button(
                        "🔄 New Analysis", 
                        variant="secondary",
                        visible=False
                    )
        
        # Helper functions
        def get_progress_response(message: str, progress: int) -> Tuple:
            """Generate progress response"""
            progress_html = f"""
            <div class="progress-container fade-in">
                <div style="text-align: center; padding: 2rem;">
                    <div class="loading-spinner" style="font-size: 4rem;">⏳</div>
                    <h2 class="pulse-text">{message}</h2>
                    <div style="background: rgba(99, 102, 241, 0.2); height: 8px; border-radius: 4px; margin: 1rem 0;">
                        <div style="background: linear-gradient(135deg, #6366f1, #8b5cf6); height: 100%; border-radius: 4px; width: {progress}%; transition: width 0.5s ease;"></div>
                    </div>
                    <p>Progress: {progress}%</p>
                </div>
            </div>
            """
            
            return (
                progress_html,  # progress_container
                message,        # status_text
                0,             # overall_score
                "",            # grade
                "",            # summary_text
                "",            # criteria_results
                "",            # recommendations
                {},            # raw_output
                gr.update(visible=False),  # download_btn
                gr.update(visible=False)   # reset_btn
            )
        
        def get_success_response(score: int, grade: str, summary: str, criteria: str, recommendations: str, raw_data: dict) -> Tuple:
            """Generate success response"""
            return (
                gr.update(visible=False),  # progress_container
                f"✅ Analysis Complete! Score: {score}/100",  # status_text
                score,                     # overall_score
                grade,                     # grade
                summary,                   # summary_text
                criteria,                  # criteria_results
                recommendations,           # recommendations
                raw_data,                  # raw_output
                gr.update(visible=True),   # download_btn
                gr.update(visible=True)    # reset_btn
            )
        
        def get_error_response(message: str) -> Tuple:
            """Generate error response"""
            error_html = f"""
            <div class="progress-container fade-in">
                <div style="text-align: center; padding: 2rem;">
                    <div style="font-size: 4rem; color: #ef4444;">❌</div>
                    <h2 style="color: #ef4444;">{message}</h2>
                    <p>Please check your input and try again.</p>
                </div>
            </div>
            """
            
            return (
                error_html,                # progress_container
                message,                   # status_text
                0,                         # overall_score
                "",                        # grade
                "",                        # summary_text
                "",                        # criteria_results
                "",                        # recommendations
                {},                        # raw_output
                gr.update(visible=False),  # download_btn
                gr.update(visible=False)   # reset_btn
            )
        
        def generate_criteria_html_from_llm(analysis_result: dict) -> str:
            """Generate criteria HTML from real LLM analysis"""
            try:
                criteria = analysis_result.get('criteria', {})
                overall_score = analysis_result.get('overall_score', 0)
                
                html_parts = [f"""
                <div class="fade-in" style="padding: 1rem;">
                    <h3>📊 AI Analysis Results</h3>
                    <div style="margin: 1rem 0; padding: 1rem; border-left: 4px solid #8b5cf6; background: rgba(139, 92, 246, 0.1);">
                        <strong>Overall Score: {overall_score}/100</strong>
                        <p>AI-powered evaluation of your API documentation</p>
                    </div>
                """]
                
                # Add each criteria with color coding based on score
                for criterion_name, criterion_data in criteria.items():
                    if isinstance(criterion_data, dict):
                        score = criterion_data.get('score', 0)
                        description = criterion_data.get('description', 'No description available')
                        
                        # Color coding based on score
                        if score >= 80:
                            color = "#10b981"  # Green
                            bg_color = "rgba(16, 185, 129, 0.1)"
                        elif score >= 60:
                            color = "#f59e0b"  # Yellow
                            bg_color = "rgba(245, 158, 11, 0.1)"
                        else:
                            color = "#ef4444"  # Red
                            bg_color = "rgba(239, 68, 68, 0.1)"
                        
                        html_parts.append(f"""
                        <div style="margin: 1rem 0; padding: 1rem; border-left: 4px solid {color}; background: {bg_color};">
                            <strong>{criterion_name.replace('_', ' ').title()}: {score}/100</strong>
                            <p>{description}</p>
                        </div>
                        """)
                
                html_parts.append("</div>")
                return "".join(html_parts)
                
            except Exception as e:
                return f"""
                <div class="fade-in" style="padding: 1rem;">
                    <h3>📊 Analysis Results</h3>
                    <p>Error processing criteria: {str(e)}</p>
                </div>
                """
        
        def generate_recommendations_html_from_llm(analysis_result: dict) -> str:
            """Generate recommendations HTML from real LLM analysis"""
            try:
                recommendations = analysis_result.get('recommendations', [])
                
                if not recommendations:
                    return """
                    <div class="fade-in" style="padding: 1rem;">
                        <h3>💡 Recommendations</h3>
                        <p>No specific recommendations available from the analysis.</p>
                    </div>
                    """
                
                html_parts = ["""
                <div class="fade-in" style="padding: 1rem;">
                    <h3>💡 AI-Generated Recommendations</h3>
                """]
                
                # Priority colors
                priority_colors = {
                    'high': ('#ef4444', 'rgba(239, 68, 68, 0.1)'),
                    'medium': ('#f59e0b', 'rgba(245, 158, 11, 0.1)'),
                    'low': ('#10b981', 'rgba(16, 185, 129, 0.1)')
                }
                
                for i, rec in enumerate(recommendations):
                    if isinstance(rec, dict):
                        priority = rec.get('priority', 'medium').lower()
                        title = rec.get('title', f'Recommendation {i+1}')
                        description = rec.get('description', 'No description available')
                        
                        color, bg_color = priority_colors.get(priority, priority_colors['medium'])
                        
                        html_parts.append(f"""
                        <div style="margin: 1rem 0; padding: 1rem; border-left: 4px solid {color}; background: {bg_color};">
                            <strong>{'🚨' if priority == 'high' else '⚡' if priority == 'medium' else '✅'} {priority.title()} Priority</strong>
                            <p><strong>{title}</strong></p>
                            <p>{description}</p>
                        </div>
                        """)
                    elif isinstance(rec, str):
                        html_parts.append(f"""
                        <div style="margin: 1rem 0; padding: 1rem; border-left: 4px solid #3b82f6; background: rgba(59, 130, 246, 0.1);">
                            <p>{rec}</p>
                        </div>
                        """)
                
                html_parts.append("</div>")
                return "".join(html_parts)
                
            except Exception as e:
                return f"""
                <div class="fade-in" style="padding: 1rem;">
                    <h3>💡 Recommendations</h3>
                    <p>Error processing recommendations: {str(e)}</p>
                </div>
                """
        
        # Enhanced analysis function with REAL LLM integration
        def analyze_documentation(file_input, manual_text, provider, api_key, model, temp, max_tok, state):
            """Enhanced analysis function with REAL LLM integration"""
            
            # Prevent multiple simultaneous analyses
            if state.get("is_running", False):
                return get_error_response("Analysis already in progress. Please wait.")
            
            try:
                # Set running state
                state["is_running"] = True
                state["current_session"] = f"session_{int(time.time())}"
                
                # Initial validation
                if not file_input and not manual_text.strip():
                    return get_error_response("❌ Please provide documentation via upload or text input")
                
                if not api_key.strip():
                    return get_error_response("❌ Please provide OpenAI API key in Configuration tab")
                
                # Progress updates with yield
                yield get_progress_response("📝 Processing input...", 0)
                
                # Get content
                if file_input:
                    content = Path(file_input.name).read_text(encoding='utf-8')
                    content_source = f"File: {file_input.name}"
                else:
                    content = manual_text.strip()
                    content_source = "Manual input"
                
                yield get_progress_response(f"🔍 Analyzing {len(content)} characters...", 25)
                
                # Initialize APISage analyzer with real LLM
                yield get_progress_response(f"🤖 Initializing APISage LLM engine...", 40)
                
                try:
                    # Set environment variable for API key
                    os.environ["OPENAI_API_KEY"] = api_key
                    
                    # Initialize the analyzer with proper configuration
                    agent_config = AgentConfig(
                        name="api_analyzer",
                        model=model,
                        temperature=temp,
                        max_tokens=max_tok
                    )
                    
                    system_config = SystemConfig()
                    
                    # Initialize the analyzer (we'll use the simplified version for now)
                    analyzer = APIAnalyzer(agent_config, system_config, None)
                    
                    yield get_progress_response(f"🤖 Running AI analysis with {model}...", 60)
                    
                    # Run REAL LLM analysis using the synchronous method
                    analysis_result = analyzer.analyze_documentation(
                        content=content,
                        model=model,
                        temperature=temp,
                        max_tokens=max_tok
                    )
                    
                    yield get_progress_response("📊 Processing AI results...", 80)
                    
                    # Extract results from LLM analysis
                    if analysis_result and isinstance(analysis_result, dict):
                        # Extract score and grade
                        overall_score = analysis_result.get('overall_score', 0)
                        grade_val = analysis_result.get('grade', 'N/A')
                        summary = analysis_result.get('summary', f"Analysis complete for {content_source}.")
                        
                        # Generate HTML from real LLM results
                        criteria_html = generate_criteria_html_from_llm(analysis_result)
                        recommendations_html = generate_recommendations_html_from_llm(analysis_result)
                        
                        raw_data = {
                            "score": overall_score,
                            "grade": grade_val,
                            "summary": summary,
                            "analysis_complete": True,
                            "session_id": state["current_session"],
                            "timestamp": time.time(),
                            "llm_analysis": analysis_result
                        }
                        
                        # Final success response with REAL LLM data
                        yield get_success_response(overall_score, grade_val, summary, criteria_html, recommendations_html, raw_data)
                    else:
                        # Fallback if LLM analysis fails
                        yield get_error_response("❌ LLM analysis failed to return valid results")
                        
                except Exception as llm_error:
                    yield get_error_response(f"❌ LLM Analysis Error: {str(llm_error)}")
                
            except Exception as e:
                yield get_error_response(f"❌ Error during analysis: {str(e)}")
            finally:
                # Reset running state
                state["is_running"] = False
        
        def handle_file_upload(file):
            """Handle file upload and clear text input"""
            if file:
                return None, f"✅ File uploaded: {file.name}", "success"
            return gr.update(), "📄 Ready for file upload", "info"
        
        def handle_text_input(text):
            """Handle text input and clear file upload"""
            if text.strip():
                return None, f"✅ Text input provided ({len(text)} characters)", "success"
            return gr.update(), "✏️ Ready for text input", "info"
        
        def validate_api_key(api_key):
            """Validate API key format"""
            if not api_key.strip():
                return "❌ API key is required"
            if not api_key.strip().startswith("sk-"):
                return "⚠️ API key should start with 'sk-'"
            if len(api_key.strip()) < 20:
                return "⚠️ API key seems too short"
            return "✅ API key looks valid"
        
        def reset_analysis(state):
            """Reset analysis state and clear results"""
            state["is_running"] = False
            state["current_session"] = None
            
            return (
                gr.update(visible=False),  # progress_container
                "Ready for new analysis",  # status_text
                0,                         # overall_score
                "",                        # grade
                "",                        # summary_text
                "",                        # criteria_results
                "",                        # recommendations
                {},                        # raw_output
                gr.update(visible=False),  # download_btn
                gr.update(visible=False)   # reset_btn
            )
        
        # Event handlers
        file_upload.upload(
            handle_file_upload,
            inputs=[file_upload],
            outputs=[manual_input, file_status, input_validation]
        )
        
        manual_input.change(
            handle_text_input,
            inputs=[manual_input],
            outputs=[file_upload, text_status, input_validation]
        )
        
        # API key validation
        openai_api_key.change(
            validate_api_key,
            inputs=[openai_api_key],
            outputs=[api_key_status]
        )
        
        # Analysis button
        analyze_btn.click(
            lambda: (gr.update(visible=True), "🔄 Starting analysis..."),
            outputs=[progress_container, status_text]
        ).then(
            analyze_documentation,
            inputs=[
                file_upload, manual_input, provider_choice,
                openai_api_key, openai_model, temperature, max_tokens, analysis_state
            ],
            outputs=[
                progress_container, status_text, overall_score, grade, summary_text,
                criteria_results, recommendations, raw_output, download_btn, reset_btn
            ]
        )
        
        # Reset button
        reset_btn.click(
            reset_analysis,
            inputs=[analysis_state],
            outputs=[
                progress_container, status_text, overall_score, grade, summary_text,
                criteria_results, recommendations, raw_output, download_btn, reset_btn
            ]
        )
    
    return interface


def main():
    """Launch the working UI"""
    interface = create_working_interface()
    
    # Launch with proper configuration
    interface.launch(
        server_name="0.0.0.0",
        server_port=7861,
        share=False,
        show_error=True,
        quiet=False
    )


if __name__ == "__main__":
    main()
