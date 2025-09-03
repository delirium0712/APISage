#!/usr/bin/env python3
"""
Agentic Orchestration System for APISage
Multi-agent collaborative API analysis inspired by TheAgentic approach
"""

import asyncio
import json
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import structlog

from infrastructure.llm_manager import SimpleLLMManager, LLMRequest

logger = structlog.get_logger(__name__)


class AgentRole(Enum):
    """Specialized agent roles for API analysis"""
    SECURITY_ANALYST = "security_analyst"
    PERFORMANCE_ENGINEER = "performance_engineer"  
    DOCUMENTATION_REVIEWER = "documentation_reviewer"
    STANDARDS_AUDITOR = "standards_auditor"
    UX_RESEARCHER = "ux_researcher"
    INTEGRATION_SPECIALIST = "integration_specialist"


@dataclass
class AgentResult:
    """Result from individual agent analysis"""
    agent_role: str
    findings: List[Dict[str, Any]]
    score: float  # 0-100
    confidence: float  # 0-1
    processing_time: float
    token_usage: int


@dataclass 
class OrchestrationResult:
    """Combined result from all agents"""
    overall_score: float
    agent_results: Dict[str, AgentResult]
    consensus_findings: List[Dict[str, Any]]
    collaboration_insights: List[str]
    total_processing_time: float
    total_tokens: int
    agent_agreement_score: float  # How much agents agreed


class SpecializedAgent:
    """Base class for specialized API analysis agents"""
    
    def __init__(self, role: AgentRole, llm_manager: SimpleLLMManager):
        self.role = role
        self.llm_manager = llm_manager
        self.logger = logger.bind(agent_role=role.value)
        
    async def analyze(self, api_spec: Dict[str, Any], focus_context: Dict[str, Any] = None) -> AgentResult:
        """Analyze API spec from this agent's specialized perspective"""
        start_time = time.time()
        
        prompt = self._create_specialized_prompt(api_spec, focus_context)
        
        # Use efficient model parameters
        llm_request = LLMRequest(
            prompt=prompt,
            max_tokens=1500,  # Focused analysis per agent
            temperature=0.2   # Consistent analysis
        )
        
        try:
            response = await self.llm_manager.generate_response(llm_request)
            
            # Parse agent response
            findings, score, confidence = self._parse_agent_response(response)
            
            result = AgentResult(
                agent_role=self.role.value,
                findings=findings,
                score=score,
                confidence=confidence,
                processing_time=time.time() - start_time,
                token_usage=len(prompt.split()) + len(response.split())  # Approximate
            )
            
            self.logger.info(
                "Agent analysis complete",
                score=score,
                confidence=confidence,
                findings_count=len(findings)
            )
            
            return result
            
        except Exception as e:
            self.logger.error("Agent analysis failed", error=str(e))
            return self._fallback_result(time.time() - start_time)
    
    def _create_specialized_prompt(self, api_spec: Dict[str, Any], context: Dict[str, Any] = None) -> str:
        """Create role-specific analysis prompt"""
        
        base_info = self._extract_api_info(api_spec)
        role_prompts = {
            AgentRole.SECURITY_ANALYST: f"""You are a cybersecurity expert analyzing API security.

API TO ANALYZE: {json.dumps(base_info, indent=2)}

Focus on:
- Authentication/authorization mechanisms
- Input validation and injection risks  
- Rate limiting and abuse prevention
- Data exposure and privacy concerns
- CORS and cross-origin security

Provide JSON response:
{{
    "findings": [
        {{
            "type": "security_vulnerability|best_practice|missing_protection",
            "severity": "critical|high|medium|low", 
            "title": "Specific issue title",
            "description": "Detailed technical explanation",
            "location": "endpoint or global",
            "fix": "Specific implementation steps",
            "code_example": "Working code solution"
        }}
    ],
    "security_score": 85,
    "confidence": 0.9
}}""",

            AgentRole.PERFORMANCE_ENGINEER: f"""You are a performance optimization expert.

API TO ANALYZE: {json.dumps(base_info, indent=2)}

Focus on:
- Response time optimization opportunities
- Caching strategies and implementation
- Pagination and data loading efficiency
- Database query optimization hints
- Scalability bottlenecks

Provide JSON response:
{{
    "findings": [
        {{
            "type": "performance_issue|optimization|scalability_concern",
            "impact": "critical|high|medium|low",
            "title": "Performance issue",
            "description": "Technical analysis", 
            "location": "specific endpoint",
            "fix": "Optimization steps",
            "expected_improvement": "quantified benefit"
        }}
    ],
    "performance_score": 75,
    "confidence": 0.8
}}""",

            AgentRole.DOCUMENTATION_REVIEWER: f"""You are a technical writing expert reviewing API documentation.

API TO ANALYZE: {json.dumps(base_info, indent=2)}

Focus on:
- Clarity and completeness of descriptions
- Code examples and usage samples
- Error response documentation  
- Parameter descriptions and constraints
- Developer onboarding experience

Provide JSON response:
{{
    "findings": [
        {{
            "type": "missing_docs|unclear_description|missing_examples",
            "priority": "critical|high|medium|low",
            "title": "Documentation issue",
            "description": "What's missing or unclear",
            "location": "specific endpoint or global",
            "fix": "Specific documentation to add",
            "example": "Sample documentation text"
        }}
    ],
    "documentation_score": 70,
    "confidence": 0.9
}}"""
        }
        
        return role_prompts.get(self.role, "Generic analysis prompt")
    
    def _extract_api_info(self, api_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Extract key API information for analysis"""
        return {
            "title": api_spec.get("info", {}).get("title", "Unknown API"),
            "version": api_spec.get("info", {}).get("version", "Unknown"),
            "endpoints": list(api_spec.get("paths", {}).keys()),
            "has_security": bool(api_spec.get("security") or api_spec.get("components", {}).get("securitySchemes")),
            "endpoint_count": len(api_spec.get("paths", {})),
            "schema_count": len(api_spec.get("components", {}).get("schemas", {}))
        }
    
    def _parse_agent_response(self, response: str) -> tuple:
        """Parse agent response into structured data"""
        try:
            data = json.loads(response)
            findings = data.get("findings", [])
            
            # Extract score based on agent type
            score_keys = ["security_score", "performance_score", "documentation_score", "standards_score", "usability_score"]
            score = next((data.get(key, 70) for key in score_keys if key in data), 70)
            
            confidence = data.get("confidence", 0.7)
            
            return findings, float(score), float(confidence)
            
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Failed to parse agent response", error=str(e))
            # Fallback parsing from text
            return self._fallback_text_parsing(response)
    
    def _fallback_text_parsing(self, response: str) -> tuple:
        """Fallback text parsing when JSON fails"""
        # Extract basic findings from text
        findings = [{"type": "analysis", "title": "Agent Analysis", "description": response[:500]}]
        score = 65.0  # Neutral score
        confidence = 0.5  # Low confidence for fallback
        
        return findings, score, confidence
    
    def _fallback_result(self, processing_time: float) -> AgentResult:
        """Fallback result when agent fails"""
        return AgentResult(
            agent_role=self.role.value,
            findings=[{"type": "error", "title": "Analysis Failed", "description": "Agent encountered an error"}],
            score=50.0,
            confidence=0.1,
            processing_time=processing_time,
            token_usage=0
        )


class AgenticOrchestrator:
    """Orchestrates multiple specialized agents for comprehensive API analysis"""
    
    def __init__(self, llm_manager: SimpleLLMManager):
        self.llm_manager = llm_manager
        self.agents = {
            role: SpecializedAgent(role, llm_manager) 
            for role in AgentRole
        }
        self.logger = logger.bind(component="agentic_orchestrator")
    
    async def collaborative_analysis(
        self, 
        api_spec: Dict[str, Any], 
        focus_areas: List[str] = None,
        parallel: bool = True
    ) -> OrchestrationResult:
        """
        Orchestrate collaborative analysis across multiple agents
        
        Args:
            api_spec: OpenAPI specification to analyze
            focus_areas: Specific areas to focus on (filters agents)
            parallel: Whether to run agents in parallel (faster) or sequential (cheaper)
        """
        start_time = time.time()
        
        # Filter agents based on focus areas
        active_agents = self._select_agents(focus_areas)
        
        self.logger.info(
            "Starting collaborative analysis",
            active_agents=[agent.role.value for agent in active_agents],
            parallel=parallel
        )
        
        # Run agent analysis
        if parallel:
            # Parallel execution - faster but uses more tokens simultaneously
            agent_results = await asyncio.gather(*[
                agent.analyze(api_spec) for agent in active_agents
            ])
        else:
            # Sequential execution - slower but more token-efficient
            agent_results = []
            for agent in active_agents:
                result = await agent.analyze(api_spec)
                agent_results.append(result)
                await asyncio.sleep(0.1)  # Small delay to prevent rate limiting
        
        # Aggregate results
        orchestration_result = await self._aggregate_agent_results(
            agent_results, time.time() - start_time
        )
        
        self.logger.info(
            "Collaborative analysis complete",
            overall_score=orchestration_result.overall_score,
            agents_used=len(agent_results),
            total_time=orchestration_result.total_processing_time
        )
        
        return orchestration_result
    
    def _select_agents(self, focus_areas: List[str] = None) -> List[SpecializedAgent]:
        """Select appropriate agents based on focus areas"""
        
        if not focus_areas:
            # Use all agents for comprehensive analysis
            return list(self.agents.values())
        
        # Map focus areas to agent roles
        agent_mapping = {
            "security": [AgentRole.SECURITY_ANALYST],
            "performance": [AgentRole.PERFORMANCE_ENGINEER],
            "documentation": [AgentRole.DOCUMENTATION_REVIEWER],
            "standards": [AgentRole.STANDARDS_AUDITOR],
            "completeness": [AgentRole.INTEGRATION_SPECIALIST],
            "usability": [AgentRole.UX_RESEARCHER]
        }
        
        selected_roles = set()
        for area in focus_areas:
            selected_roles.update(agent_mapping.get(area, []))
        
        return [self.agents[role] for role in selected_roles if role in self.agents]
    
    async def _aggregate_agent_results(
        self, 
        agent_results: List[AgentResult], 
        total_time: float
    ) -> OrchestrationResult:
        """Aggregate individual agent results into comprehensive analysis"""
        
        # Calculate overall metrics
        scores = [result.score for result in agent_results if result.confidence > 0.3]
        overall_score = sum(scores) / len(scores) if scores else 50.0
        
        # Calculate agent agreement (how similar their scores are)
        if len(scores) > 1:
            score_variance = sum((s - overall_score) ** 2 for s in scores) / len(scores)
            agreement_score = max(0, 100 - score_variance)  # Higher variance = lower agreement
        else:
            agreement_score = 100.0
        
        # Consolidate findings across agents
        all_findings = []
        for result in agent_results:
            all_findings.extend(result.findings)
        
        # Generate collaboration insights
        insights = await self._generate_collaboration_insights(agent_results)
        
        # Build result dictionary
        results_dict = {
            result.agent_role: result for result in agent_results
        }
        
        return OrchestrationResult(
            overall_score=overall_score,
            agent_results=results_dict,
            consensus_findings=all_findings,
            collaboration_insights=insights,
            total_processing_time=total_time,
            total_tokens=sum(result.token_usage for result in agent_results),
            agent_agreement_score=agreement_score
        )
    
    async def _generate_collaboration_insights(
        self, 
        agent_results: List[AgentResult]
    ) -> List[str]:
        """Generate insights from agent collaboration patterns"""
        
        insights = []
        
        # Analyze confidence patterns
        high_confidence_agents = [r for r in agent_results if r.confidence > 0.8]
        if high_confidence_agents:
            insights.append(f"{len(high_confidence_agents)} agents showed high confidence in their analysis")
        
        # Analyze score patterns
        scores = [r.score for r in agent_results]
        if max(scores) - min(scores) > 30:
            insights.append("Significant disagreement between agents suggests complex API requiring detailed review")
        
        # Analyze finding types
        critical_findings = sum(1 for result in agent_results 
                              for finding in result.findings 
                              if finding.get("severity") == "critical" or finding.get("priority") == "critical")
        
        if critical_findings > 0:
            insights.append(f"Found {critical_findings} critical issues requiring immediate attention")
        
        return insights


# Factory function for easy integration
def create_agentic_orchestrator(llm_manager: SimpleLLMManager = None) -> AgenticOrchestrator:
    """Create orchestrator with default configuration"""
    if llm_manager is None:
        llm_manager = SimpleLLMManager(model="gpt-4o-mini")  # Cost-efficient for multi-agent
    
    return AgenticOrchestrator(llm_manager)