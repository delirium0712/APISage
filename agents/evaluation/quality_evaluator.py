"""
API Documentation Quality Evaluator
Uses LLM to evaluate API documentation quality across multiple dimensions
"""

import json
import asyncio
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
import structlog


@dataclass
class QualityCriteria:
    """Quality evaluation criteria"""
    name: str
    weight: float
    description: str
    evaluation_function: str


class APIDocQualityEvaluator:
    """Evaluates API documentation quality across multiple dimensions"""
    
    def __init__(self, llm_client):
        self.llm = llm_client
        self.logger = structlog.get_logger(agent="quality_evaluator")
        
        # Define evaluation criteria with weights
        self.evaluation_criteria = {
            "completeness": {
                "weight": 0.25,
                "description": "How complete is the API documentation",
                "evaluator": self.evaluate_completeness
            },
            "clarity": {
                "weight": 0.20,
                "description": "How clear and understandable is the documentation",
                "evaluator": self.evaluate_clarity
            },
            "examples": {
                "weight": 0.15,
                "description": "Quality and coverage of examples",
                "evaluator": self.evaluate_examples
            },
            "error_handling": {
                "weight": 0.15,
                "description": "Documentation of error scenarios and responses",
                "evaluator": self.evaluate_error_handling
            },
            "consistency": {
                "weight": 0.10,
                "description": "Consistency in formatting and structure",
                "evaluator": self.evaluate_consistency
            },
            "versioning": {
                "weight": 0.05,
                "description": "Version management and change documentation",
                "evaluator": self.evaluate_versioning
            },
            "security": {
                "weight": 0.05,
                "description": "Security documentation and examples",
                "evaluator": self.evaluate_security
            },
            "performance": {
                "weight": 0.05,
                "description": "Performance considerations and limits",
                "evaluator": self.evaluate_performance_docs
            }
        }
    
    async def evaluate_documentation(self, parsed_doc: Dict) -> Dict[str, Any]:
        """Comprehensive quality evaluation"""
        
        try:
            # Run all evaluations in parallel
            evaluation_tasks = []
            for criterion, config in self.evaluation_criteria.items():
                evaluator = config["evaluator"]
                task = evaluator(parsed_doc)
                evaluation_tasks.append((criterion, task))
            
            results = {}
            for criterion, task in evaluation_tasks:
                try:
                    score, details = await task
                    results[criterion] = {
                        "score": score,  # 0-100
                        "details": details,
                        "weight": self.evaluation_criteria[criterion]["weight"],
                        "recommendations": await self.generate_recommendations(
                            criterion, score, details
                        )
                    }
                except Exception as e:
                    self.logger.error(f"evaluation_failed_for_{criterion}", error=str(e))
                    results[criterion] = {
                        "score": 0,
                        "details": {"error": str(e)},
                        "weight": self.evaluation_criteria[criterion]["weight"],
                        "recommendations": ["Evaluation failed - check logs"]
                    }
            
            # Calculate weighted overall score
            overall_score = self._calculate_weighted_score(results)
            
            # Generate executive summary
            summary = await self.generate_quality_summary(results, overall_score)
            
            # Prioritize improvements
            improvement_priority = self._prioritize_improvements(results)
            
            return {
                "overall_score": overall_score,
                "grade": self._calculate_grade(overall_score),
                "criteria_scores": results,
                "summary": summary,
                "improvement_priority": improvement_priority,
                "evaluation_timestamp": self._get_timestamp()
            }
            
        except Exception as e:
            self.logger.error("quality_evaluation_failed", error=str(e))
            return {
                "error": str(e),
                "overall_score": 0,
                "grade": "F"
            }
    
    async def evaluate_completeness(self, doc: Dict) -> Tuple[float, Dict]:
        """Evaluate if all endpoints have complete documentation"""
        
        total_endpoints = len(doc.get("endpoints", []))
        if total_endpoints == 0:
            return 0.0, {"error": "No endpoints found"}
        
        issues = []
        complete_endpoints = 0
        
        for endpoint in doc.get("endpoints", []):
            completeness_checks = {
                "has_summary": bool(endpoint.get("summary")),
                "has_description": bool(endpoint.get("description")),
                "has_parameters_doc": self._check_parameters_documentation(endpoint),
                "has_response_doc": bool(endpoint.get("responses")),
                "has_examples": bool(endpoint.get("examples")),
                "has_error_responses": self._check_error_responses(endpoint),
                "has_tags": bool(endpoint.get("tags"))
            }
            
            if all(completeness_checks.values()):
                complete_endpoints += 1
            else:
                issues.append({
                    "endpoint": f"{endpoint.get('method', '')} {endpoint.get('path', '')}",
                    "missing": [k for k, v in completeness_checks.items() if not v]
                })
        
        score = (complete_endpoints / total_endpoints) * 100
        
        return score, {
            "total_endpoints": total_endpoints,
            "complete_endpoints": complete_endpoints,
            "completeness_percentage": score,
            "issues": issues[:10]  # Top 10 issues
        }
    
    def _check_parameters_documentation(self, endpoint: Dict) -> bool:
        """Check if parameters are properly documented"""
        parameters = endpoint.get("parameters", [])
        if not parameters:
            return True  # No parameters to document
        
        for param in parameters:
            if not param.get("description"):
                return False
        return True
    
    def _check_error_responses(self, endpoint: Dict) -> bool:
        """Check if error responses are documented"""
        responses = endpoint.get("responses", {})
        for code in responses.keys():
            try:
                if int(code) >= 400:
                    return True
            except ValueError:
                continue
        return False
    
    async def evaluate_clarity(self, doc: Dict) -> Tuple[float, Dict]:
        """Evaluate clarity and understandability of documentation"""
        
        if not self.llm:
            return 50.0, {"note": "LLM not available for clarity evaluation"}
        
        try:
            # Use LLM to evaluate clarity
            prompt = f"""
            Evaluate the clarity of this API documentation on a scale of 0-100.
            
            API Title: {doc.get('title', 'Unknown')}
            Description: {doc.get('description', 'No description')[:500]}
            
            Consider:
            1. Language clarity and readability
            2. Technical accuracy
            3. Logical organization
            4. Use of proper terminology
            
            Return only the numeric score (0-100).
            """
            
            response = await self.llm.evaluate(prompt)
            score = float(response.strip())
            
            return score, {
                "evaluation_method": "llm_assessment",
                "prompt_used": prompt[:200] + "...",
                "llm_response": response
            }
            
        except Exception as e:
            self.logger.error("clarity_evaluation_failed", error=str(e))
            return 50.0, {"error": str(e)}
    
    async def evaluate_examples(self, doc: Dict) -> Tuple[float, Dict]:
        """Evaluate quality and coverage of examples"""
        
        endpoints = doc.get("endpoints", [])
        if not endpoints:
            return 0.0, {"error": "No endpoints to evaluate"}
        
        endpoints_with_examples = 0
        example_quality_scores = []
        
        for endpoint in endpoints:
            examples = endpoint.get("examples", [])
            if examples:
                endpoints_with_examples += 1
                
                # Evaluate example quality
                quality_score = self._evaluate_example_quality(endpoint, examples)
                example_quality_scores.append(quality_score)
        
        coverage_score = (endpoints_with_examples / len(endpoints)) * 100
        quality_score = sum(example_quality_scores) / len(example_quality_scores) if example_quality_scores else 0
        
        # Weighted score: 60% coverage, 40% quality
        final_score = (coverage_score * 0.6) + (quality_score * 0.4)
        
        return final_score, {
            "endpoints_with_examples": endpoints_with_examples,
            "total_endpoints": len(endpoints),
            "coverage_percentage": coverage_score,
            "average_example_quality": quality_score,
            "example_quality_scores": example_quality_scores
        }
    
    def _evaluate_example_quality(self, endpoint: Dict, examples: List) -> float:
        """Evaluate the quality of examples for a specific endpoint"""
        if not examples:
            return 0.0
        
        quality_score = 0.0
        max_score = 100.0
        
        # Check for realistic data
        if any("example" in str(ex).lower() or "sample" in str(ex).lower() for ex in examples):
            quality_score += 25
        
        # Check for multiple examples
        if len(examples) > 1:
            quality_score += 25
        
        # Check for error examples
        if any("error" in str(ex).lower() or "400" in str(ex) or "500" in str(ex) for ex in examples):
            quality_score += 25
        
        # Check for complete request/response pairs
        if any("request" in str(ex).lower() and "response" in str(ex).lower() for ex in examples):
            quality_score += 25
        
        return quality_score
    
    async def evaluate_error_handling(self, doc: Dict) -> Tuple[float, Dict]:
        """Evaluate error handling documentation"""
        
        endpoints = doc.get("endpoints", [])
        if not endpoints:
            return 0.0, {"error": "No endpoints to evaluate"}
        
        endpoints_with_errors = 0
        error_documentation_scores = []
        
        for endpoint in endpoints:
            responses = endpoint.get("responses", {})
            error_responses = {}
            
            for code, response in responses.items():
                try:
                    if int(code) >= 400:
                        error_responses[code] = response
                except ValueError:
                    continue
            
            if error_responses:
                endpoints_with_errors += 1
                score = self._evaluate_error_response_quality(error_responses)
                error_documentation_scores.append(score)
        
        coverage_score = (endpoints_with_errors / len(endpoints)) * 100
        quality_score = sum(error_documentation_scores) / len(error_documentation_scores) if error_documentation_scores else 0
        
        final_score = (coverage_score * 0.7) + (quality_score * 0.3)
        
        return final_score, {
            "endpoints_with_error_docs": endpoints_with_errors,
            "total_endpoints": len(endpoints),
            "coverage_percentage": coverage_score,
            "average_error_doc_quality": quality_score
        }
    
    def _evaluate_error_response_quality(self, error_responses: Dict) -> float:
        """Evaluate the quality of error response documentation"""
        score = 0.0
        
        for code, response in error_responses.items():
            # Check for description
            if response.get("description"):
                score += 20
            
            # Check for schema
            if response.get("content") and response["content"].get("application/json"):
                score += 20
            
            # Check for examples
            if response.get("examples"):
                score += 20
            
            # Check for headers
            if response.get("headers"):
                score += 20
        
        return min(score, 100.0)
    
    async def evaluate_consistency(self, doc: Dict) -> Tuple[float, Dict]:
        """Evaluate consistency in formatting and structure"""
        
        endpoints = doc.get("endpoints", [])
        if not endpoints:
            return 0.0, {"error": "No endpoints to evaluate"}
        
        consistency_checks = {
            "method_formatting": self._check_method_formatting(endpoints),
            "path_formatting": self._check_path_formatting(endpoints),
            "parameter_structure": self._check_parameter_structure(endpoints),
            "response_structure": self._check_response_structure(endpoints)
        }
        
        score = sum(consistency_checks.values()) / len(consistency_checks) * 100
        
        return score, {
            "consistency_checks": consistency_checks,
            "overall_consistency": score
        }
    
    def _check_method_formatting(self, endpoints: List) -> float:
        """Check consistency in HTTP method formatting"""
        methods = [endpoint.get("method", "").upper() for endpoint in endpoints]
        unique_methods = set(methods)
        return 1.0 if len(unique_methods) == len(methods) else 0.5
    
    def _check_path_formatting(self, endpoints: List) -> float:
        """Check consistency in path formatting"""
        paths = [endpoint.get("path", "") for endpoint in endpoints]
        # Check if all paths start with /
        consistent_paths = all(path.startswith("/") for path in paths if path)
        return 1.0 if consistent_paths else 0.5
    
    def _check_parameter_structure(self, endpoints: List) -> float:
        """Check consistency in parameter structure"""
        # This is a simplified check - could be more sophisticated
        return 0.8  # Placeholder
    
    def _check_response_structure(self, endpoints: List) -> float:
        """Check consistency in response structure"""
        # This is a simplified check - could be more sophisticated
        return 0.8  # Placeholder
    
    async def evaluate_versioning(self, doc: Dict) -> Tuple[float, Dict]:
        """Evaluate version management and change documentation"""
        
        score = 0.0
        details = {}
        
        # Check for version in info
        if doc.get("version"):
            score += 50
            details["has_version"] = True
        else:
            details["has_version"] = False
        
        # Check for version in paths
        paths = doc.get("paths", {})
        versioned_paths = any("/v" in path for path in paths.keys())
        if versioned_paths:
            score += 30
            details["has_versioned_paths"] = True
        else:
            details["has_versioned_paths"] = False
        
        # Check for changelog or migration info
        description = doc.get("description", "")
        has_changelog = any(word in description.lower() for word in ["changelog", "migration", "version", "deprecated"])
        if has_changelog:
            score += 20
            details["has_changelog_info"] = True
        else:
            details["has_changelog_info"] = False
        
        return score, details
    
    async def evaluate_security(self, doc: Dict) -> Tuple[float, Dict]:
        """Evaluate security documentation and examples"""
        
        score = 0.0
        details = {}
        
        # Check for security schemes
        components = doc.get("components", {})
        security_schemes = components.get("securitySchemes", {})
        if security_schemes:
            score += 40
            details["has_security_schemes"] = True
            details["security_types"] = list(security_schemes.keys())
        else:
            details["has_security_schemes"] = False
        
        # Check for security requirements on endpoints
        endpoints = doc.get("endpoints", [])
        secured_endpoints = sum(1 for endpoint in endpoints if endpoint.get("security"))
        if secured_endpoints > 0:
            score += 30
            details["secured_endpoints"] = secured_endpoints
            details["total_endpoints"] = len(endpoints)
        else:
            details["secured_endpoints"] = 0
        
        # Check for security examples
        has_security_examples = any("auth" in str(endpoint.get("examples", [])).lower() for endpoint in endpoints)
        if has_security_examples:
            score += 30
            details["has_security_examples"] = True
        else:
            details["has_security_examples"] = False
        
        return score, details
    
    async def evaluate_performance_docs(self, doc: Dict) -> Tuple[float, Dict]:
        """Evaluate performance considerations and limits documentation"""
        
        score = 0.0
        details = {}
        
        description = doc.get("description", "").lower()
        endpoints = doc.get("endpoints", [])
        
        # Check for rate limiting info
        has_rate_limits = any(word in description for word in ["rate limit", "throttling", "quota"])
        if has_rate_limits:
            score += 40
            details["has_rate_limit_info"] = True
        else:
            details["has_rate_limit_info"] = False
        
        # Check for timeout info
        has_timeouts = any(word in description for word in ["timeout", "deadline", "ttl"])
        if has_timeouts:
            score += 30
            details["has_timeout_info"] = True
        else:
            details["has_timeout_info"] = False
        
        # Check for pagination info
        has_pagination = any(word in description for word in ["pagination", "cursor", "page"])
        if has_pagination:
            score += 30
            details["has_pagination_info"] = True
        else:
            details["has_pagination_info"] = False
        
        return score, details
    
    async def generate_recommendations(self, criterion: str, score: float, details: Dict) -> List[str]:
        """Generate improvement recommendations based on score and details"""
        
        recommendations = []
        
        if criterion == "completeness" and score < 80:
            if details.get("endpoints_without_summaries", 0) > 0:
                recommendations.append("Add summaries to all endpoints")
            if details.get("endpoints_without_descriptions", 0) > 0:
                recommendations.append("Add detailed descriptions to all endpoints")
            if details.get("endpoints_without_examples", 0) > 0:
                recommendations.append("Add examples for all endpoints")
        
        elif criterion == "examples" and score < 70:
            recommendations.append("Increase example coverage across endpoints")
            recommendations.append("Include both success and error examples")
            recommendations.append("Add examples for different parameter combinations")
        
        elif criterion == "error_handling" and score < 60:
            recommendations.append("Document error responses for all endpoints")
            recommendations.append("Include error response schemas")
            recommendations.append("Add examples of common error scenarios")
        
        elif criterion == "security" and score < 50:
            recommendations.append("Define security schemes in components")
            recommendations.append("Apply security requirements to endpoints")
            recommendations.append("Include authentication examples")
        
        # Generic recommendations for low scores
        if score < 50:
            recommendations.append(f"Focus on improving {criterion} as it has the lowest score")
        elif score < 70:
            recommendations.append(f"Consider enhancing {criterion} for better documentation quality")
        
        return recommendations if recommendations else ["No specific recommendations at this time"]
    
    async def generate_quality_summary(self, results: Dict, overall_score: float) -> str:
        """Generate executive summary of quality evaluation"""
        
        if not self.llm:
            return self._generate_basic_summary(results, overall_score)
        
        try:
            # Use LLM to generate summary
            prompt = f"""
            Generate a concise executive summary of this API documentation quality evaluation.
            
            Overall Score: {overall_score}/100
            Grade: {self._calculate_grade(overall_score)}
            
            Criteria Scores:
            {json.dumps({k: v['score'] for k, v in results.items()}, indent=2)}
            
            Provide a 2-3 sentence summary highlighting:
            1. Overall assessment
            2. Key strengths
            3. Main areas for improvement
            
            Keep it professional and actionable.
            """
            
            summary = await self.llm.evaluate(prompt)
            return summary.strip()
            
        except Exception as e:
            self.logger.error("summary_generation_failed", error=str(e))
            return self._generate_basic_summary(results, overall_score)
    
    def _generate_basic_summary(self, results: Dict, overall_score: float) -> str:
        """Generate basic summary without LLM"""
        
        grade = self._calculate_grade(overall_score)
        
        # Find top and bottom criteria
        sorted_criteria = sorted(results.items(), key=lambda x: x[1]['score'])
        top_criteria = sorted_criteria[-2:] if len(sorted_criteria) >= 2 else sorted_criteria
        bottom_criteria = sorted_criteria[:2] if len(sorted_criteria) >= 2 else sorted_criteria
        
        summary = f"API Documentation Quality: {overall_score}/100 ({grade})"
        
        if top_criteria:
            summary += f". Strongest areas: {', '.join([c[0] for c in top_criteria])}"
        
        if bottom_criteria:
            summary += f". Areas for improvement: {', '.join([c[0] for c in bottom_criteria])}"
        
        return summary
    
    def _calculate_weighted_score(self, results: Dict) -> float:
        """Calculate weighted overall score"""
        
        total_weighted_score = 0.0
        total_weight = 0.0
        
        for criterion, data in results.items():
            weight = data.get("weight", 0)
            score = data.get("score", 0)
            
            total_weighted_score += score * weight
            total_weight += weight
        
        return total_weighted_score / total_weight if total_weight > 0 else 0.0
    
    def _calculate_grade(self, score: float) -> str:
        """Convert numeric score to letter grade"""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"
    
    def _prioritize_improvements(self, results: Dict) -> List[str]:
        """Prioritize improvements based on scores and weights"""
        
        # Calculate improvement potential (weight * (100 - score))
        improvement_scores = {}
        for criterion, data in results.items():
            weight = data.get("weight", 0)
            score = data.get("score", 0)
            improvement_potential = weight * (100 - score)
            improvement_scores[criterion] = improvement_potential
        
        # Sort by improvement potential (highest first)
        sorted_improvements = sorted(improvement_scores.items(), 
                                   key=lambda x: x[1], reverse=True)
        
        return [criterion for criterion, _ in sorted_improvements]
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.utcnow().isoformat()
