"""
API Quality Analyzer Agent - Uses an LLM to evaluate API documentation.
"""
import json
import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
import structlog

from config.settings import AgentConfig, SystemConfig
from infrastructure.backend_manager import BackendManager
from infrastructure.llm_manager import LLMManager, LLMRequest

# --- New Data Structures for Quality Reporting ---

@dataclass
class QualityCriterion:
    """Represents a single criterion in the quality report."""
    criterion: str
    score: int  # Score from 0-100
    reasoning: str

@dataclass
class ActionItem:
    """Represents a single actionable recommendation."""
    recommendation: str
    priority: str  # e.g., "High", "Medium", "Low"
    description: str

@dataclass
class APIQualityReport:
    """Structured report of the API documentation quality."""
    overall_score: int
    grade: str  # A, B, C, D, F
    summary: str
    criteria: List[QualityCriterion] = field(default_factory=list)
    action_items: List[ActionItem] = field(default_factory=list)

class APIAnalyzer:
    """
    Uses an LLM to analyze API documentation, provide a quality score,
    and generate actionable recommendations for improvement.
    """
    
    def __init__(self, config: AgentConfig, system_config: SystemConfig, backend_manager: BackendManager):
        self.config = config
        self.system_config = system_config
        self.backend_manager = backend_manager
        self.logger = structlog.get_logger(__name__).bind(agent=config.name)
        
    async def analyze_api_documentation(self, content: str) -> APIQualityReport:
        """
        Orchestrates the LLM-based analysis of the API documentation.
        """
        self.logger.info("starting_api_quality_analysis")

        prompt = self._build_evaluation_prompt(content)
        
        try:
            # Create a structured LLMRequest
            llm_request = LLMRequest(
                prompt=prompt,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature
            )

            llm_response = await self.backend_manager.llm_manager.generate(llm_request)
            
            # The response object has a 'content' attribute
            report_data = self._parse_llm_response(llm_response.content if llm_response else "")
            
            if not report_data:
                self.logger.error("failed_to_parse_llm_response")
                return self._generate_fallback_report()

            report = self._create_report_from_data(report_data)
            self.logger.info("api_quality_analysis_completed", score=report.overall_score)
            return report
            
        except Exception as e:
            self.logger.error("api_analysis_llm_call_failed", error=str(e))
            return self._generate_fallback_report()

    def _build_evaluation_prompt(self, content: str) -> str:
        """Creates an enhanced prompt for comprehensive API documentation evaluation."""
        
        prompt = f"""<role>
You are a senior API documentation expert with 10+ years of experience in technical writing, 
developer experience, and API design. You specialize in evaluating documentation quality 
from both technical accuracy and developer usability perspectives.
</role>

<task>
Conduct a comprehensive evaluation of the provided API documentation. Analyze it through 
the lens of a developer who needs to integrate with this API for the first time.
</task>

<evaluation_framework>
## Core Evaluation Criteria (Weight: 60%)

1. **Completeness & Coverage** (0-100)
   - All endpoints documented with HTTP methods, paths, and descriptions
   - Request/response schemas with data types and constraints
   - Query parameters, path parameters, and request body specifications
   - Response status codes and their meanings
   - Rate limiting and quota information

2. **Clarity & Usability** (0-100)
   - Clear, concise descriptions without ambiguity
   - Logical organization and navigation structure
   - Consistent terminology and naming conventions
   - Progressive disclosure (basic → advanced concepts)
   - Target audience appropriateness

3. **Authentication & Security** (0-100)
   - Authentication methods clearly explained
   - Authorization scopes/permissions documented
   - Security best practices and considerations
   - API key/token management guidance
   - HTTPS/TLS requirements specified

4. **Examples & Code Samples** (0-100)
   - Working code examples in multiple languages
   - Complete request/response examples with real data
   - Common use case demonstrations
   - Error handling examples
   - SDK/library usage examples (if applicable)

## Advanced Evaluation Criteria (Weight: 40%)

5. **Error Handling & Troubleshooting** (0-100)
   - Comprehensive error code documentation
   - Clear error message formats
   - Troubleshooting guides for common issues
   - Recovery strategies for failures
   - Debug/verbose mode documentation

6. **Developer Experience** (0-100)
   - Quick start guide or getting started section
   - Interactive documentation (e.g., try-it-out features)
   - Changelog and versioning information
   - Migration guides for breaking changes
   - Testing sandbox/environment details

7. **Technical Accuracy** (0-100)
   - Correct HTTP semantics and REST principles
   - Accurate data type specifications
   - Valid JSON/XML schema definitions
   - Consistency between docs and actual API behavior
   - Up-to-date with latest API version

8. **Supporting Resources** (0-100)
   - API reference completeness
   - Conceptual/architectural documentation
   - Glossary of terms
   - FAQ section
   - Community resources and support channels
</evaluation_framework>

<scoring_rubric>
Score each criterion using this scale:
- 90-100: Exceptional - Industry-leading quality, could serve as a best practice example
- 80-89: Excellent - Comprehensive and well-executed with minor gaps
- 70-79: Good - Solid documentation with some areas for improvement
- 60-69: Adequate - Meets basic needs but lacks polish or depth
- 50-59: Below Average - Significant gaps that impact usability
- 0-49: Poor - Major deficiencies that would frustrate developers

Grade Mapping:
- A (90-100): Outstanding documentation that exceeds industry standards
- B (80-89): Strong documentation that serves developers well
- C (70-79): Acceptable documentation with room for improvement
- D (60-69): Marginal documentation that needs significant work
- F (0-59): Failing documentation that requires major overhaul
</scoring_rubric>

<output_specification>
Provide your evaluation as a valid JSON object with this exact structure:

```json
{{
  "overall_score": <weighted average score 0-100>,
  "grade": "<letter grade based on overall_score>",
  "evaluation_date": "<current date in ISO format>",
  "api_type": "<detected API type: REST, GraphQL, SOAP, gRPC, etc.>",
  
  "executive_summary": {{
    "one_line": "<single sentence capturing the documentation's overall state>",
    "paragraph": "<3-4 sentence paragraph summarizing key findings>",
    "primary_strength": "<the documentation's strongest aspect>",
    "primary_weakness": "<the most critical area needing improvement>"
  }},
  
  "detailed_scores": {{
    "core_criteria": [
      {{
        "criterion": "<criterion name>",
        "score": <0-100>,
        "weight": <percentage weight>,
        "findings": "<specific observations about this criterion>",
        "evidence": ["<specific example from docs>", "<another example>"]
      }}
    ],
    "advanced_criteria": [
      {{
        "criterion": "<criterion name>",
        "score": <0-100>,
        "weight": <percentage weight>,
        "findings": "<specific observations about this criterion>",
        "evidence": ["<specific example from docs>", "<another example>"]
      }}
    ]
  }},
  
  "strengths": [
    {{
      "area": "<strength area>",
      "description": "<what's done well>",
      "impact": "<how this helps developers>"
    }}
  ],
  
  "weaknesses": [
    {{
      "area": "<weakness area>",
      "description": "<what's lacking or problematic>",
      "impact": "<how this hinders developers>",
      "severity": "<Critical|High|Medium|Low>"
    }}
  ],
  
  "action_items": [
    {{
      "recommendation": "<specific, actionable improvement>",
      "priority": "<Critical|High|Medium|Low>",
      "effort": "<estimated effort: Small|Medium|Large>",
      "impact": "<expected improvement in developer experience>",
      "implementation_notes": "<specific guidance on how to implement>"
    }}
  ],
  
  "competitive_comparison": {{
    "benchmark": "<how this compares to industry standards>",
    "similar_apis": "<comparison to similar well-known APIs>",
    "maturity_level": "<Emerging|Developing|Mature|Leading>"
  }},
  
  "metadata": {{
    "total_endpoints_documented": <number or null if not applicable>,
    "example_count": <number of code examples found>,
    "error_codes_documented": <number>,
    "supported_languages": ["<language>"],
    "has_interactive_docs": <boolean>,
    "has_sdk": <boolean>,
    "last_updated": "<detected last update date or null>"
  }}
}}
```
</output_specification>

<analysis_instructions>
1. First, quickly scan the documentation to understand its structure and scope
2. Evaluate each criterion systematically, looking for specific evidence
3. Consider the documentation from a new developer's perspective
4. Balance technical accuracy with practical usability
5. Provide specific, actionable feedback rather than generic observations
6. Prioritize recommendations based on developer impact
7. Be fair but critical - good documentation is crucial for API adoption
</analysis_instructions>

<documentation_to_evaluate>
{content}
</documentation_to_evaluate>

<important_notes>
- Focus on constructive criticism that leads to actionable improvements
- Consider different developer personas (beginner, intermediate, expert)
- Account for the API's complexity and domain when scoring
- If certain criteria are not applicable, note this in the findings
- Ensure JSON output is valid and properly escaped
</important_notes>"""
        return prompt.strip()

    def _parse_llm_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Safely parses the JSON response from the LLM."""
        try:
            # Clean the response by finding the JSON object
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
            self.logger.warning("no_json_object_found_in_llm_response")
            return None
        except json.JSONDecodeError as e:
            self.logger.error("llm_response_json_decode_error", error=str(e), response=response)
            return None

    def _create_report_from_data(self, data: Dict[str, Any]) -> APIQualityReport:
        """Populates the APIQualityReport dataclass from the parsed JSON data."""
        return APIQualityReport(
            overall_score=data.get("overall_score", 0),
            grade=data.get("grade", "N/A"),
            summary=data.get("summary", "No summary provided."),
            criteria=[QualityCriterion(**c) for c in data.get("criteria", [])],
            action_items=[ActionItem(**a) for a in data.get("action_items", [])]
        )

    def _generate_fallback_report(self) -> APIQualityReport:
        """Creates a default report in case of an error."""
        return APIQualityReport(
            overall_score=0,
            grade="Error",
            summary="An error occurred while analyzing the documentation. Unable to generate a report.",
            criteria=[],
            action_items=[]
        )

    def to_dict(self, report: APIQualityReport) -> Dict[str, Any]:
        """Converts the APIQualityReport object to a dictionary for API responses."""
        return {
            "overall_score": report.overall_score,
            "grade": report.grade,
            "summary": report.summary,
            "criteria": [c.__dict__ for c in report.criteria],
            "action_items": [a.__dict__ for a in report.action_items]
        }