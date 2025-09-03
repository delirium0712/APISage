"""
LLM Response Quality Evaluator for APISage
Evaluates the quality and accuracy of API analysis responses
"""

import json
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
import structlog
import time

from infrastructure.llm_manager import SimpleLLMManager, LLMRequest

logger = structlog.get_logger()


class EvaluationMetric(Enum):
    """Different metrics for evaluating LLM analysis quality"""
    ACCURACY = "accuracy"           # How accurate are the findings?
    SPECIFICITY = "specificity"     # Are recommendations specific to this API?
    COMPLETENESS = "completeness"   # Did it catch all major issues?
    ACTIONABILITY = "actionability" # Are recommendations actionable?
    COHERENCE = "coherence"         # Is the analysis logical and well-structured?


@dataclass
class EvaluationResult:
    """Result of evaluating an LLM analysis"""
    overall_score: float  # 0-100
    metric_scores: Dict[str, float]
    detailed_feedback: str
    improvement_suggestions: List[str]
    evaluation_time: float
    evaluator_model: str


class LLMAnalysisEvaluator:
    """
    Evaluates the quality of LLM-generated API analysis
    Uses LLM-as-Judge approach with structured evaluation
    """
    
    def __init__(self, evaluator_model: str = "o1-mini"):
        """Initialize with a model optimized for evaluation tasks"""
        self.evaluator_llm = SimpleLLMManager(model=evaluator_model)
        self.logger = logger.bind(component="llm_evaluator")
        
    async def evaluate_analysis(
        self, 
        api_spec: Dict[str, Any],
        llm_analysis: str,
        analysis_context: Dict[str, Any] = None
    ) -> EvaluationResult:
        """
        Evaluate the quality of an LLM-generated API analysis
        
        Args:
            api_spec: The original OpenAPI specification
            llm_analysis: The LLM-generated analysis to evaluate
            analysis_context: Additional context about the analysis
            
        Returns:
            EvaluationResult with scores and feedback
        """
        start_time = time.time()
        
        try:
            # Create evaluation prompt
            evaluation_prompt = self._create_evaluation_prompt(
                api_spec, llm_analysis, analysis_context
            )
            
            # Get evaluation from LLM
            evaluation_response = await self._get_evaluation_response(evaluation_prompt)
            
            # Parse evaluation results
            result = self._parse_evaluation_response(evaluation_response)
            result.evaluation_time = time.time() - start_time
            result.evaluator_model = self.evaluator_llm.default_model
            
            self.logger.info(
                "Analysis evaluation completed",
                overall_score=result.overall_score,
                evaluation_time=result.evaluation_time
            )
            
            return result
            
        except Exception as e:
            self.logger.error("Evaluation failed", error=str(e))
            # Return fallback evaluation
            return EvaluationResult(
                overall_score=50.0,  # Neutral score when evaluation fails
                metric_scores={metric.value: 50.0 for metric in EvaluationMetric},
                detailed_feedback="Evaluation service unavailable",
                improvement_suggestions=["Check evaluation service configuration"],
                evaluation_time=time.time() - start_time,
                evaluator_model=self.evaluator_llm.default_model
            )
    
    def _create_evaluation_prompt(
        self, 
        api_spec: Dict[str, Any], 
        llm_analysis: str,
        context: Dict[str, Any] = None
    ) -> str:
        """Create a comprehensive evaluation prompt"""
        
        # Extract key info from the API spec for context
        api_info = api_spec.get("info", {})
        paths = api_spec.get("paths", {})
        
        # Count actual features in the spec
        endpoint_count = len(paths)
        has_auth = bool(api_spec.get("security") or any(
            "security" in str(methods) for methods in paths.values()
        ))
        has_error_responses = any(
            any(status.startswith(("4", "5")) for status in method.get("responses", {}).keys())
            for methods in paths.values()
            for method in methods.values()
        )
        
        prompt = f"""You are an expert API analysis evaluator. Your job is to evaluate the QUALITY and ACCURACY of an LLM-generated API analysis.

## ORIGINAL API SPECIFICATION FACTS:
- API Title: {api_info.get("title", "Unknown")}
- Description: {api_info.get("description", "No description")}
- Total Endpoints: {endpoint_count}
- Has Authentication: {has_auth}
- Has Error Responses: {has_error_responses}
- Actual Endpoints: {list(paths.keys()) if paths else "None"}

## LLM ANALYSIS TO EVALUATE:
{llm_analysis}

## EVALUATION CRITERIA:

### 1. ACCURACY (0-100)
- Does the analysis correctly identify what exists in the API?
- Are the findings factually correct based on the spec?
- Does it avoid mentioning features that don't exist?
- Does it correctly identify missing features?

### 2. SPECIFICITY (0-100)  
- Are recommendations specific to THIS API, not generic advice?
- Does it reference actual endpoint names and paths?
- Are code examples relevant to this API's structure?
- Does it avoid generic "implement best practices" advice?

### 3. COMPLETENESS (0-100)
- Did it identify major architectural issues?
- Are security, performance, and DX aspects covered?
- Did it catch critical missing endpoints for this API's purpose?
- Are the most important issues prioritized correctly?

### 4. ACTIONABILITY (0-100)
- Can a developer immediately act on the recommendations?
- Are fixes specific with code examples?
- Is the implementation path clear?
- Are recommendations prioritized by effort/impact?

### 5. COHERENCE (0-100)
- Is the analysis well-structured and logical?
- Do conclusions follow from the evidence?
- Is the writing clear and professional?
- Are scores/ratings consistent with findings?

## REQUIRED OUTPUT FORMAT (JSON ONLY):
{{
    "overall_score": 85.0,
    "accuracy": 90.0,
    "specificity": 80.0,
    "completeness": 85.0,
    "actionability": 88.0,
    "coherence": 82.0,
    "strengths": [
        "Correctly identified missing POST /users endpoint",
        "Provided specific code examples for this API",
        "Accurately assessed security risk level"
    ],
    "weaknesses": [
        "Mentioned rate limiting without justification for this API",
        "Generic advice about documentation best practices",
        "Missed critical pagination issue on GET /users"
    ],
    "improvement_suggestions": [
        "Focus more on API-specific issues, less on generic patterns",
        "Provide more detailed error response examples",
        "Better prioritization of critical vs nice-to-have fixes"
    ],
    "critical_errors": [
        "Mentioned features that don't exist in the spec",
        "Provided wrong endpoint names or methods"
    ]
}}

IMPORTANT: Be highly critical. Only give high scores (80+) for genuinely excellent analysis that is accurate, specific, and actionable."""
        
        return prompt
    
    async def _get_evaluation_response(self, prompt: str) -> str:
        """Get evaluation response from LLM with proper error handling"""
        
        llm_request = LLMRequest(
            prompt=prompt,
            max_tokens=2000,
            temperature=0.1  # Low temperature for consistent evaluation
        )
        
        try:
            result = await self.evaluator_llm.generate(llm_request)
            if result and result.content:
                return result.content
            else:
                raise Exception("Empty response from evaluator LLM")
                
        except Exception as e:
            self.logger.error("Evaluator LLM request failed", error=str(e))
            # Return structured fallback response
            return json.dumps({
                "overall_score": 50.0,
                "accuracy": 50.0,
                "specificity": 50.0,
                "completeness": 50.0,
                "actionability": 50.0,
                "coherence": 50.0,
                "strengths": ["Evaluation service unavailable"],
                "weaknesses": ["Cannot assess - evaluator offline"],
                "improvement_suggestions": ["Restore evaluation service"],
                "critical_errors": []
            })
    
    def _parse_evaluation_response(self, response: str) -> EvaluationResult:
        """Parse the evaluation response into structured result"""
        
        try:
            # Try to extract JSON from response
            eval_data = json.loads(response)
            
            return EvaluationResult(
                overall_score=float(eval_data.get("overall_score", 50.0)),
                metric_scores={
                    EvaluationMetric.ACCURACY.value: float(eval_data.get("accuracy", 50.0)),
                    EvaluationMetric.SPECIFICITY.value: float(eval_data.get("specificity", 50.0)),
                    EvaluationMetric.COMPLETENESS.value: float(eval_data.get("completeness", 50.0)),
                    EvaluationMetric.ACTIONABILITY.value: float(eval_data.get("actionability", 50.0)),
                    EvaluationMetric.COHERENCE.value: float(eval_data.get("coherence", 50.0))
                },
                detailed_feedback=self._format_detailed_feedback(eval_data),
                improvement_suggestions=eval_data.get("improvement_suggestions", []),
                evaluation_time=0.0,  # Will be set by caller
                evaluator_model=""     # Will be set by caller
            )
            
        except json.JSONDecodeError as e:
            self.logger.warning("Failed to parse evaluation JSON", error=str(e), response=response[:200])
            # Return fallback result
            return EvaluationResult(
                overall_score=50.0,
                metric_scores={metric.value: 50.0 for metric in EvaluationMetric},
                detailed_feedback="Evaluation parsing failed",
                improvement_suggestions=["Fix evaluation response format"],
                evaluation_time=0.0,
                evaluator_model=""
            )
    
    def _format_detailed_feedback(self, eval_data: Dict[str, Any]) -> str:
        """Format evaluation data into readable feedback"""
        
        strengths = eval_data.get("strengths", [])
        weaknesses = eval_data.get("weaknesses", [])
        critical_errors = eval_data.get("critical_errors", [])
        
        feedback = "## Evaluation Results\n\n"
        
        if strengths:
            feedback += "### ✅ Strengths:\n"
            for strength in strengths:
                feedback += f"- {strength}\n"
            feedback += "\n"
        
        if weaknesses:
            feedback += "### ⚠️ Areas for Improvement:\n"
            for weakness in weaknesses:
                feedback += f"- {weakness}\n"
            feedback += "\n"
        
        if critical_errors:
            feedback += "### 🚨 Critical Issues:\n"
            for error in critical_errors:
                feedback += f"- {error}\n"
            feedback += "\n"
        
        return feedback


class EvaluationDashboard:
    """Dashboard for tracking evaluation metrics over time"""
    
    def __init__(self):
        self.evaluation_history: List[Dict[str, Any]] = []
        self.logger = logger.bind(component="evaluation_dashboard")
    
    def record_evaluation(self, result: EvaluationResult, context: Dict[str, Any] = None):
        """Record an evaluation result for tracking"""
        
        record = {
            "timestamp": time.time(),
            "overall_score": result.overall_score,
            "metric_scores": result.metric_scores,
            "evaluation_time": result.evaluation_time,
            "evaluator_model": result.evaluator_model,
            "context": context or {}
        }
        
        self.evaluation_history.append(record)
        
        self.logger.info(
            "Evaluation recorded",
            score=result.overall_score,
            total_evaluations=len(self.evaluation_history)
        )
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get overall performance metrics"""
        
        if not self.evaluation_history:
            return {"message": "No evaluations recorded yet"}
        
        recent_evaluations = self.evaluation_history[-10:]  # Last 10 evaluations
        
        metrics = {
            "total_evaluations": len(self.evaluation_history),
            "average_score": sum(e["overall_score"] for e in recent_evaluations) / len(recent_evaluations),
            "score_trend": self._calculate_trend(),
            "metric_averages": self._calculate_metric_averages(recent_evaluations),
            "evaluation_frequency": len(self.evaluation_history) / max(1, (time.time() - self.evaluation_history[0]["timestamp"]) / 86400),  # per day
        }
        
        return metrics
    
    def _calculate_trend(self) -> str:
        """Calculate if scores are trending up, down, or stable"""
        
        if len(self.evaluation_history) < 5:
            return "insufficient_data"
        
        recent_5 = [e["overall_score"] for e in self.evaluation_history[-5:]]
        earlier_5 = [e["overall_score"] for e in self.evaluation_history[-10:-5]]
        
        if not earlier_5:
            return "insufficient_data"
        
        recent_avg = sum(recent_5) / len(recent_5)
        earlier_avg = sum(earlier_5) / len(earlier_5)
        
        if recent_avg > earlier_avg + 5:
            return "improving"
        elif recent_avg < earlier_avg - 5:
            return "declining"
        else:
            return "stable"
    
    def _calculate_metric_averages(self, evaluations: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate averages for each evaluation metric"""
        
        metric_totals = {}
        for evaluation in evaluations:
            for metric, score in evaluation["metric_scores"].items():
                if metric not in metric_totals:
                    metric_totals[metric] = []
                metric_totals[metric].append(score)
        
        return {
            metric: sum(scores) / len(scores)
            for metric, scores in metric_totals.items()
        }