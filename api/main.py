"""
AI-Powered API Analysis Service
Actually uses LLM to provide intelligent, context-aware analysis
"""

import json
import os
import time
from typing import Any, Dict, Optional

import structlog
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from infrastructure.llm_manager import LLMRequest, SimpleLLMManager, ModelConfig
from evaluation.llm_evaluator import LLMAnalysisEvaluator, EvaluationDashboard
from typing import List

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


def get_optimal_llm_params(model: str, base_max_tokens: int = 2000) -> Dict[str, Any]:
    """Get optimal LLM parameters for the specified model"""
    defaults = ModelConfig.get_model_defaults(model)

    # Scale max_tokens based on model capabilities
    optimal_max_tokens = defaults.get("max_tokens", base_max_tokens)

    # For o1 models, use higher max_tokens for reasoning tasks
    if ModelConfig.is_o1_model(model):
        optimal_max_tokens = max(optimal_max_tokens, base_max_tokens * 2)

    params = {
        "max_tokens": optimal_max_tokens,
        "model": model,
    }

    # Only add temperature for non-o1 models
    if defaults.get("temperature") is not None:
        params["temperature"] = defaults["temperature"]

    return params


# FastAPI app
app = FastAPI(
    title="APISage - AI-Powered OpenAPI Analysis",
    description="Intelligent API analysis using LLM for context-aware, specific feedback",
    version="3.0.0",
)


# Request/Response models
class AnalysisRequest(BaseModel):
    openapi_spec: Dict[str, Any]
    analysis_depth: Optional[
        str
    ] = "comprehensive"  # "quick", "standard", "comprehensive"
    focus_areas: Optional[
        list
    ] = None  # ["security", "performance", "documentation", etc.]


class AnalysisResponse(BaseModel):
    status: str
    analysis: str
    key_findings: Dict[str, Any]
    metadata: Dict[str, Any]


class APIKeyRequest(BaseModel):
    api_key: str


class APIKeyResponse(BaseModel):
    status: str
    message: str
    is_set: bool


class EvaluationRequest(BaseModel):
    openapi_spec: Dict[str, Any]
    llm_analysis: str
    analysis_context: Optional[Dict[str, Any]] = None


class EvaluationResponse(BaseModel):
    status: str
    overall_score: float
    metric_scores: Dict[str, float]
    detailed_feedback: str
    improvement_suggestions: List[str]
    evaluation_time: float
    evaluator_model: str


# Initialize LLM manager and evaluation system
llm_manager = SimpleLLMManager(model="o1-mini")  # Use o1-mini for optimal reasoning performance
evaluator = LLMAnalysisEvaluator(evaluator_model="o1-mini")  # Use same model for consistency  
evaluation_dashboard = EvaluationDashboard()


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "APISage AI-Powered Analysis",
        "llm_available": llm_manager.is_available(),
    }


@app.get("/models")
async def get_available_models():
    """Get list of available models"""
    print("DEBUG: Models endpoint called!")  # Debug print
    return {"models": ["gpt-4o", "gpt-4o-mini", "o1", "o1-mini", "o1-preview", "gpt-3.5-turbo"]}


@app.get("/test")
async def test_endpoint():
    """Simple test endpoint"""
    return {"message": "Test endpoint working"}


@app.post("/set-api-key", response_model=APIKeyResponse)
async def set_api_key(request: APIKeyRequest):
    """Set OpenAI API key"""
    try:
        os.environ["OPENAI_API_KEY"] = request.api_key

        if llm_manager.refresh_api_key():
            logger.info("API key set and validated successfully")
            return APIKeyResponse(
                status="success",
                message="API key set and validated successfully",
                is_set=True,
            )
        else:
            return APIKeyResponse(
                status="error", message="Failed to validate API key", is_set=False
            )

    except Exception as e:
        logger.error("API key setting failed", error=str(e))
        return APIKeyResponse(
            status="error", message=f"Failed to set API key: {str(e)}", is_set=False
        )


@app.get("/api-key-status")
async def get_api_key_status():
    """Get current API key status"""
    return {
        "is_set": bool(os.getenv("OPENAI_API_KEY")),
        "is_available": llm_manager.is_available(),
    }


def create_analysis_prompt(
    spec: Dict[str, Any], analysis_depth: str, focus_areas: list = None
) -> str:
    """Create a detailed prompt for LLM analysis with specific, actionable feedback"""

    # Extract detailed information for specific analysis
    paths = spec.get("paths", {})
    components = spec.get("components", {})
    info = spec.get("info", {})

    # Count actual endpoints and methods
    endpoint_count = len(paths)
    total_methods = sum(len(methods) for methods in paths.values())

    # Analyze what's actually in the spec
    has_authentication = bool(
        spec.get("security")
        or any(
            any("security" in method for method in methods.values())
            for methods in paths.values()
        )
    )

    has_error_responses = any(
        any(
            status.startswith(("4", "5"))
            for status in method.get("responses", {}).keys()
        )
        for methods in paths.values()
        for method in methods.values()
    )

    has_pagination = any(
        any(
            param.get("name") in ["limit", "offset", "page", "cursor"]
            for param in method.get("parameters", [])
        )
        for methods in paths.values()
        for method in methods.values()
    )

    # Build the prompt with specific analysis requirements
    prompt = f"""You are an expert API architect conducting a thorough technical review. 
Analyze THIS SPECIFIC API and provide actionable, specific feedback.

## API SPECIFICATION ANALYSIS
**API Title:** {info.get("title", "Unknown")}
**Version:** {info.get("version", "Unknown")}
**Description:** {info.get("description", "No description provided")}
**Total Endpoints:** {endpoint_count}
**Total HTTP Methods:** {total_methods}
**Has Authentication:** {has_authentication}
**Has Error Responses:** {has_error_responses}
**Has Pagination:** {has_pagination}

## ACTUAL ENDPOINTS FOUND:
{json.dumps({path: list(methods.keys()) for path, methods in paths.items()}, indent=2)}

## FULL SPECIFICATION:
{json.dumps(spec, indent=2)[:10000]}

## ANALYSIS REQUIREMENTS:
- **CRITICAL:** Reference specific lines, paths, and components from the actual spec
- **CRITICAL:** Only mention features that actually exist or are actually missing
- **CRITICAL:** Provide specific code examples for THIS API
- **CRITICAL:** Avoid generic advice that applies to any API

## REQUIRED OUTPUT FORMAT:

### 📊 API Score Breakdown
**Overall Score:** [X/100]
- **Completeness:** [X/100] - [Specific assessment of what's missing]
- **Documentation:** [X/100] - [Specific documentation issues found]
- **Security:** [X/100] - [Specific security gaps identified]
- **Usability:** [X/100] - [Specific developer experience issues]
- **Standards Compliance:** [X/100] - [Specific OpenAPI/REST violations]

### 🎯 Executive Summary
[2-3 sentences about THIS SPECIFIC API's current state and main issues]

### 🚨 Critical Issues (Priority Order)
1. **Issue:** [Specific problem with exact location]
   - **Location:** [Exact path/component/line reference]
   - **Impact:** [Why this specific issue matters for THIS API]
   - **Fix:** [Specific solution with code example]
   - **Priority:** [High/Medium/Low with justification]

2. **Issue:** [Next specific problem]
   - **Location:** [Exact reference]
   - **Impact:** [Specific impact]
   - **Fix:** [Specific solution]
   - **Priority:** [High/Medium/Low]

### 🔍 Detailed Analysis

#### Missing Endpoints Analysis
[Based on the API description and purpose, what endpoints are missing?]
- **Missing:** [Specific endpoint that should exist]
- **Reason:** [Why this endpoint is needed for THIS API]
- **Implementation:** [Specific OpenAPI spec for the missing endpoint]

#### Parameter & Response Analysis
[Analyze actual parameters and responses in the spec]
- **Missing Parameters:** [Specific parameters missing from actual endpoints]
- **Incomplete Responses:** [Specific response schemas that are incomplete]
- **Error Handling:** [Specific error responses that are missing]

#### Schema Analysis
[Analyze the actual schemas defined]
- **Incomplete Schemas:** [Specific fields missing from actual schemas]
- **Type Issues:** [Specific type problems in actual schemas]
- **Validation Missing:** [Specific validation rules missing]

### 💡 Specific Recommendations
[Ordered by impact and effort for THIS API]

#### High Impact, Low Effort
1. **Fix:** [Specific fix for THIS API]
   - **Code Example:** [Actual OpenAPI spec addition]
   - **Impact:** [Why this helps THIS specific API]

#### Medium Impact, Medium Effort
1. **Add:** [Specific addition for THIS API]
   - **Implementation:** [Specific code example]
   - **Benefit:** [Specific benefit for THIS API]

### 🛠️ Code Examples
[Provide actual OpenAPI spec additions/modifications for THIS API]

```yaml
# Example: Adding missing endpoint for THIS API
{paths[list(paths.keys())[0]] if paths else "No endpoints to reference"}:
  # Add specific missing method with actual implementation
```

### 📋 Action Items Checklist
- [ ] [Specific action item 1 for THIS API]
- [ ] [Specific action item 2 for THIS API]
- [ ] [Specific action item 3 for THIS API]

## CRITICAL REMINDERS:
1. **NEVER** mention features that don't exist in the spec
2. **ALWAYS** reference specific paths, methods, and components
3. **ONLY** provide recommendations relevant to THIS API's purpose
4. **INCLUDE** actual code examples for THIS API's structure
5. **AVOID** generic advice like "implement rate limiting" unless specifically relevant

Focus on what THIS API actually needs based on its description and current implementation.
"""

    return prompt


def parse_llm_response(llm_response: str) -> Dict[str, Any]:
    """Parse the LLM response into structured format"""

    # Extract sections from the markdown response
    sections = {}
    current_section = None
    current_content = []

    for line in llm_response.split("\n"):
        if line.startswith("## "):
            if current_section:
                sections[current_section] = "\n".join(current_content)
            current_section = line[3:].strip().lower().replace(" ", "_")
            current_content = []
        elif current_section:
            current_content.append(line)

    if current_section:
        sections[current_section] = "\n".join(current_content)

    # Extract key findings
    key_findings = {
        "critical_issues_count": llm_response.count("Critical:")
        + llm_response.count("CRITICAL"),
        "security_issues_count": llm_response.count("Security:")
        + llm_response.count("vulnerability"),
        "has_authentication": "authentication" in llm_response.lower()
        and "missing" not in llm_response.lower(),
        "documentation_quality": "good"
        if "good documentation" in llm_response.lower()
        else "needs improvement",
    }

    return {"sections": sections, "key_findings": key_findings}


@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_api(request: AnalysisRequest):
    """AI-powered API analysis using LLM"""

    start_time = time.time()

    try:
        # Check if LLM is available
        if not llm_manager.is_available():
            raise HTTPException(
                status_code=503,
                detail="LLM service not available. Please set your OpenAI API key first.",
            )

        # Create the analysis prompt
        prompt = create_analysis_prompt(
            request.openapi_spec, request.analysis_depth, request.focus_areas
        )

        logger.info(
            "Starting LLM analysis",
            analysis_depth=request.analysis_depth,
            focus_areas=request.focus_areas,
        )

        # Create LLM request
        llm_request = LLMRequest(
            prompt=prompt,
            max_tokens=4000,
            temperature=0.3,  # Lower temperature for more consistent analysis
        )

        # Get analysis from LLM with token usage
        llm_result = await llm_manager.generate(llm_request)

        if not llm_result or not llm_result.content:
            raise HTTPException(
                status_code=500, detail="Failed to generate analysis from LLM"
            )

        llm_response = llm_result.content
        token_usage = llm_result.usage if llm_result.usage else {}

        # Parse the response
        parsed_response = parse_llm_response(llm_response)

        # Create response
        return AnalysisResponse(
            status="success",
            analysis=llm_response,
            key_findings=parsed_response["key_findings"],
            metadata={
                "api_title": request.openapi_spec.get("info", {}).get(
                    "title", "Unknown"
                ),
                "api_version": request.openapi_spec.get("info", {}).get(
                    "version", "Unknown"
                ),
                "endpoints_count": len(request.openapi_spec.get("paths", {})),
                "analysis_depth": request.analysis_depth,
                "focus_areas": request.focus_areas or ["all"],
                "model_used": llm_manager.default_model,
                "prompt_tokens": token_usage.get("prompt_tokens", 0),
                "completion_tokens": token_usage.get("completion_tokens", 0),
                "total_tokens": token_usage.get("total_tokens", 0),
                "analysis_time": time.time() - start_time,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Analysis failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.post("/analyze-specific-aspect")
async def analyze_specific_aspect(
    spec: Dict[str, Any], aspect: str, context: Optional[str] = None
):
    """Analyze a specific aspect of the API in detail"""

    if not llm_manager.is_available():
        raise HTTPException(status_code=503, detail="LLM service not available")

    aspects_prompts = {
        "security": "Perform a detailed security audit of this API. Look for authentication issues, authorization problems, data exposure risks, injection vulnerabilities, and OWASP Top 10 issues.",
        "performance": "Analyze performance implications of this API design. Look for N+1 query risks, missing pagination, large payload issues, caching opportunities, and rate limiting needs.",
        "documentation": "Evaluate the documentation quality. Check for missing descriptions, unclear parameters, absent examples, and developer experience issues.",
        "breaking_changes": "Identify potential breaking changes if this API evolves. What design decisions might cause problems later?",
        "best_practices": "Compare this API against REST best practices, OpenAPI standards, and industry conventions. Be specific about violations.",
        "usability": "Evaluate from a developer's perspective. How easy is it to integrate with this API? What's frustrating? What's missing?",
    }

    prompt = f"""
    Expert Analysis Required: {aspect}
    
    Context: {context if context else "General analysis"}
    
    {aspects_prompts.get(aspect, f"Analyze the {aspect} aspect of this API")}
    
    API Specification:
    {json.dumps(spec, indent=2)[:6000]}
    
    Provide specific, actionable feedback with examples. Reference actual endpoints and schemas.
    Format your response with clear sections and bullet points.
    """

    # Get optimal parameters for the current model
    current_model = llm_manager.default_model
    optimal_params = get_optimal_llm_params(current_model, base_max_tokens=2000)

    llm_request = LLMRequest(
        prompt=prompt,
        model=current_model,
        **optimal_params
    )

    response = await llm_manager.generate_response(llm_request)

    return {"aspect": aspect, "analysis": response, "context": context}


@app.post("/compare-with-standard")
async def compare_with_standard(spec: Dict[str, Any], standard: str = "REST"):
    """Compare the API with industry standards"""

    if not llm_manager.is_available():
        raise HTTPException(status_code=503, detail="LLM service not available")

    prompt = f"""
    Compare this API specification against {standard} standards and best practices.
    
    API Specification:
    {json.dumps(spec, indent=2)[:6000]}
    
    Provide a detailed comparison:
    1. What {standard} principles does this API follow well?
    2. What {standard} principles does it violate?
    3. Specific examples of violations with fixes
    4. Overall compliance score (0-100)
    5. Priority fixes to improve compliance
    
    Be specific and reference actual endpoints, not generic advice.
    """

    # Get optimal parameters for the current model
    current_model = llm_manager.default_model
    optimal_params = get_optimal_llm_params(current_model, base_max_tokens=2000)

    llm_request = LLMRequest(
        prompt=prompt,
        model=current_model,
        **optimal_params
    )

    response = await llm_manager.generate_response(llm_request)

    return {"standard": standard, "comparison": response}


@app.post("/suggest-improvements")
async def suggest_improvements(spec: Dict[str, Any], goal: str):
    """Get AI-powered improvement suggestions for specific goals"""

    if not llm_manager.is_available():
        raise HTTPException(status_code=503, detail="LLM service not available")

    prompt = f"""
    Goal: {goal}
    
    Current API Specification:
    {json.dumps(spec, indent=2)[:6000]}
    
    Provide specific improvements to achieve this goal:
    1. What needs to change?
    2. Provide actual code/specification examples
    3. Explain the impact of each change
    4. Prioritize changes by impact
    5. Estimate implementation effort
    
    Focus on THIS specific API, not generic improvements.
    """

    # Get optimal parameters for the current model
    current_model = llm_manager.default_model
    optimal_params = get_optimal_llm_params(current_model, base_max_tokens=2500)

    llm_request = LLMRequest(
        prompt=prompt,
        model=current_model,
        **optimal_params
    )

    response = await llm_manager.generate_response(llm_request)

    return {"goal": goal, "improvements": response}


@app.post("/evaluate-analysis", response_model=EvaluationResponse)
async def evaluate_analysis(request: EvaluationRequest):
    """Evaluate the quality of an LLM-generated API analysis"""
    
    try:
        # Evaluate the analysis
        evaluation_result = await evaluator.evaluate_analysis(
            api_spec=request.openapi_spec,
            llm_analysis=request.llm_analysis,
            analysis_context=request.analysis_context
        )
        
        # Record evaluation for dashboard
        evaluation_dashboard.record_evaluation(
            evaluation_result,
            context=request.analysis_context
        )
        
        logger.info(
            "Analysis evaluation completed",
            overall_score=evaluation_result.overall_score,
            evaluation_time=evaluation_result.evaluation_time
        )
        
        return EvaluationResponse(
            status="success",
            overall_score=evaluation_result.overall_score,
            metric_scores=evaluation_result.metric_scores,
            detailed_feedback=evaluation_result.detailed_feedback,
            improvement_suggestions=evaluation_result.improvement_suggestions,
            evaluation_time=evaluation_result.evaluation_time,
            evaluator_model=evaluation_result.evaluator_model
        )
        
    except Exception as e:
        logger.error("Evaluation failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail=f"Evaluation failed: {str(e)}"
        )


@app.get("/evaluation-metrics")
async def get_evaluation_metrics():
    """Get overall evaluation performance metrics"""
    
    try:
        metrics = evaluation_dashboard.get_performance_metrics()
        
        return {
            "status": "success",
            "metrics": metrics,
            "dashboard_info": {
                "total_evaluations": len(evaluation_dashboard.evaluation_history),
                "evaluator_model": evaluator.evaluator_llm.default_model
            }
        }
        
    except Exception as e:
        logger.error("Failed to get evaluation metrics", error=str(e))
        return {
            "status": "error",
            "message": f"Failed to get metrics: {str(e)}",
            "metrics": {}
        }


@app.post("/analyze-with-evaluation", response_model=Dict[str, Any])
async def analyze_with_evaluation(request: AnalysisRequest):
    """
    Perform API analysis AND evaluate the quality of the analysis
    Returns both the analysis and its evaluation
    """
    
    try:
        # First, perform the standard analysis
        analysis_response = await analyze_api(request)
        
        # Then evaluate the analysis quality
        evaluation_request = EvaluationRequest(
            openapi_spec=request.openapi_spec,
            llm_analysis=analysis_response.analysis,
            analysis_context={
                "analysis_depth": request.analysis_depth,
                "focus_areas": request.focus_areas,
                "api_title": analysis_response.metadata.get("api_title"),
                "endpoints_count": analysis_response.metadata.get("endpoints_count")
            }
        )
        
        evaluation_response = await evaluate_analysis(evaluation_request)
        
        # Combine results
        return {
            "status": "success",
            "analysis": {
                "content": analysis_response.analysis,
                "key_findings": analysis_response.key_findings,
                "metadata": analysis_response.metadata
            },
            "evaluation": {
                "overall_score": evaluation_response.overall_score,
                "metric_scores": evaluation_response.metric_scores,
                "detailed_feedback": evaluation_response.detailed_feedback,
                "improvement_suggestions": evaluation_response.improvement_suggestions,
                "evaluation_time": evaluation_response.evaluation_time,
                "evaluator_model": evaluation_response.evaluator_model
            }
        }
        
    except Exception as e:
        logger.error("Analysis with evaluation failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Analysis with evaluation failed: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
