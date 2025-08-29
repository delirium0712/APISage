"""
Evaluator Agent for assessing RAG system performance and quality
"""

import json
import time
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import structlog
import asyncio

from config.settings import AgentConfig, SystemConfig
from infrastructure.backend_manager import BackendManager


@dataclass
class EvaluationMetric:
    """Represents an evaluation metric"""
    name: str
    value: float
    description: str = ""
    category: str = "general"  # "retrieval", "generation", "overall"
    higher_is_better: bool = True


@dataclass
class EvaluationResult:
    """Results of an evaluation run"""
    timestamp: datetime
    query: str
    expected_answer: Optional[str] = None
    actual_answer: str = ""
    retrieved_documents: List[Dict[str, Any]] = None
    metrics: List[EvaluationMetric] = None
    execution_time: float = 0.0
    success: bool = True
    error: Optional[str] = None
    
    def __post_init__(self):
        if self.retrieved_documents is None:
            self.retrieved_documents = []
        if self.metrics is None:
            self.metrics = []


@dataclass
class EvaluationSuite:
    """Collection of evaluation test cases"""
    name: str
    description: str
    test_cases: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.test_cases is None:
            self.test_cases = []


class RAGEvaluator:
    """
    Evaluates RAG system performance across multiple dimensions:
    - Retrieval accuracy and relevance
    - Answer quality and correctness
    - Response time and efficiency
    - System robustness
    """
    
    def __init__(self, config: AgentConfig, system_config: SystemConfig, backend_manager: BackendManager):
        self.config = config
        self.system_config = system_config
        self.backend_manager = backend_manager
        self.redis_client = self.backend_manager.get_connection("redis")
        self.llm_manager = self.backend_manager.llm_manager
        self.logger = structlog.get_logger(__name__).bind(agent=config.name)
        
        # Evaluation categories
        self.evaluation_categories = {
            "retrieval": ["precision", "recall", "relevance"],
            "generation": ["fluency", "coherence", "factuality"],
            "overall": ["accuracy", "completeness", "efficiency"]
        }
    
    async def evaluate_rag_system(self, 
                                rag_system,
                                evaluation_suite: EvaluationSuite,
                                include_detailed_metrics: bool = True) -> Dict[str, Any]:
        """
        Evaluate a RAG system using a test suite
        
        Args:
            rag_system: The RAG system to evaluate
            evaluation_suite: Test cases to run
            include_detailed_metrics: Whether to compute detailed metrics
            
        Returns:
            Comprehensive evaluation results
        """
        self.logger.info(
            "starting_rag_evaluation", 
            suite_name=evaluation_suite.name,
            test_cases_count=len(evaluation_suite.test_cases)
        )
        
        results = []
        start_time = time.time()
        
        for i, test_case in enumerate(evaluation_suite.test_cases):
            self.logger.info("evaluating_test_case", case_index=i, query=test_case.get("query", ""))
            
            result = await self._evaluate_single_query(
                rag_system, 
                test_case, 
                include_detailed_metrics
            )
            results.append(result)
        
        total_time = time.time() - start_time
        
        # Compute aggregate metrics
        aggregate_metrics = self._compute_aggregate_metrics(results)
        
        evaluation_summary = {
            "suite_name": evaluation_suite.name,
            "suite_description": evaluation_suite.description,
            "total_test_cases": len(evaluation_suite.test_cases),
            "successful_cases": sum(1 for r in results if r.success),
            "failed_cases": sum(1 for r in results if not r.success),
            "total_evaluation_time": total_time,
            "average_response_time": sum(r.execution_time for r in results) / len(results) if results else 0,
            "aggregate_metrics": aggregate_metrics,
            "detailed_results": [self._result_to_dict(r) for r in results],
            "timestamp": datetime.now().isoformat()
        }
        
        self.logger.info(
            "rag_evaluation_completed",
            total_cases=len(results),
            successful=evaluation_summary["successful_cases"],
            failed=evaluation_summary["failed_cases"],
            avg_response_time=evaluation_summary["average_response_time"]
        )
        
        return evaluation_summary
    
    async def _evaluate_single_query(self, 
                                   rag_system, 
                                   test_case: Dict[str, Any],
                                   include_detailed_metrics: bool) -> EvaluationResult:
        """Evaluate a single query against the RAG system"""
        query = test_case.get("query", "")
        expected_answer = test_case.get("expected_answer")
        context = test_case.get("context", [])  # Expected relevant documents
        
        start_time = time.time()
        
        try:
            # Query the RAG system
            response = await rag_system.query(query, include_sources=True)
            execution_time = time.time() - start_time
            
            actual_answer = response.get("answer", "")
            retrieved_docs = response.get("sources", [])
            
            # Compute metrics
            metrics = []
            
            if include_detailed_metrics:
                # Retrieval metrics
                if context:
                    retrieval_metrics = self._compute_retrieval_metrics(retrieved_docs, context)
                    metrics.extend(retrieval_metrics)
                
                # Generation metrics
                if expected_answer:
                    generation_metrics = self._compute_generation_metrics(actual_answer, expected_answer)
                    metrics.extend(generation_metrics)
                
                # Response time metric
                metrics.append(EvaluationMetric(
                    name="response_time",
                    value=execution_time,
                    description="Time taken to generate response",
                    category="efficiency",
                    higher_is_better=False
                ))
            
            result = EvaluationResult(
                timestamp=datetime.now(),
                query=query,
                expected_answer=expected_answer,
                actual_answer=actual_answer,
                retrieved_documents=retrieved_docs,
                metrics=metrics,
                execution_time=execution_time,
                success=True
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error("query_evaluation_failed", query=query, error=str(e))
            
            result = EvaluationResult(
                timestamp=datetime.now(),
                query=query,
                expected_answer=expected_answer,
                execution_time=execution_time,
                success=False,
                error=str(e)
            )
        
        return result
    
    def _compute_retrieval_metrics(self, 
                                 retrieved_docs: List[Dict[str, Any]], 
                                 expected_context: List[str]) -> List[EvaluationMetric]:
        """Compute retrieval quality metrics"""
        metrics = []
        
        if not retrieved_docs or not expected_context:
            return metrics
        
        # Extract content from retrieved docs for comparison
        retrieved_content = []
        for doc in retrieved_docs:
            content = doc.get("content", "")
            retrieved_content.append(content.lower())
        
        expected_content = [ctx.lower() for ctx in expected_context]
        
        # Compute precision: how many retrieved docs are relevant
        relevant_retrieved = 0
        for content in retrieved_content:
            for expected in expected_content:
                if self._text_similarity(content, expected) > 0.3:  # Simple similarity threshold
                    relevant_retrieved += 1
                    break
        
        precision = relevant_retrieved / len(retrieved_docs) if retrieved_docs else 0
        
        # Compute recall: how many expected docs were retrieved
        expected_retrieved = 0
        for expected in expected_content:
            for content in retrieved_content:
                if self._text_similarity(content, expected) > 0.3:
                    expected_retrieved += 1
                    break
        
        recall = expected_retrieved / len(expected_context) if expected_context else 0
        
        # F1 score
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        metrics.extend([
            EvaluationMetric("retrieval_precision", precision, "Precision of retrieved documents", "retrieval"),
            EvaluationMetric("retrieval_recall", recall, "Recall of expected documents", "retrieval"), 
            EvaluationMetric("retrieval_f1", f1, "F1 score for retrieval", "retrieval")
        ])
        
        return metrics
    
    def _compute_generation_metrics(self, 
                                  actual_answer: str, 
                                  expected_answer: str) -> List[EvaluationMetric]:
        """Compute answer generation quality metrics"""
        metrics = []
        
        if not actual_answer or not expected_answer:
            return metrics
        
        # Text similarity (simple word overlap)
        similarity = self._text_similarity(actual_answer.lower(), expected_answer.lower())
        
        # Answer length comparison
        length_ratio = len(actual_answer.split()) / len(expected_answer.split()) if expected_answer else 0
        
        # Completeness (how much of expected answer is covered)
        expected_words = set(expected_answer.lower().split())
        actual_words = set(actual_answer.lower().split())
        completeness = len(expected_words.intersection(actual_words)) / len(expected_words) if expected_words else 0
        
        metrics.extend([
            EvaluationMetric("answer_similarity", similarity, "Similarity to expected answer", "generation"),
            EvaluationMetric("answer_completeness", completeness, "Coverage of expected content", "generation"),
            EvaluationMetric("answer_length_ratio", length_ratio, "Length ratio vs expected", "generation", higher_is_better=False)
        ])
        
        return metrics
    
    def _text_similarity(self, text1: str, text2: str) -> float:
        """Simple text similarity based on word overlap"""
        if not text1 or not text2:
            return 0.0
        
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _compute_aggregate_metrics(self, results: List[EvaluationResult]) -> Dict[str, Any]:
        """Compute aggregate metrics across all results"""
        if not results:
            return {}
        
        successful_results = [r for r in results if r.success]
        
        if not successful_results:
            return {"success_rate": 0.0}
        
        aggregate = {
            "success_rate": len(successful_results) / len(results),
            "average_response_time": sum(r.execution_time for r in successful_results) / len(successful_results)
        }
        
        # Aggregate metric categories
        for category in self.evaluation_categories:
            category_metrics = []
            for result in successful_results:
                for metric in result.metrics:
                    if metric.category == category:
                        category_metrics.append(metric.value)
            
            if category_metrics:
                aggregate[f"{category}_average"] = sum(category_metrics) / len(category_metrics)
                aggregate[f"{category}_min"] = min(category_metrics)
                aggregate[f"{category}_max"] = max(category_metrics)
        
        return aggregate
    
    def _result_to_dict(self, result: EvaluationResult) -> Dict[str, Any]:
        """Convert EvaluationResult to dictionary"""
        return {
            "timestamp": result.timestamp.isoformat(),
            "query": result.query,
            "expected_answer": result.expected_answer,
            "actual_answer": result.actual_answer,
            "retrieved_documents_count": len(result.retrieved_documents),
            "metrics": [
                {
                    "name": m.name,
                    "value": m.value,
                    "description": m.description,
                    "category": m.category,
                    "higher_is_better": m.higher_is_better
                }
                for m in result.metrics
            ],
            "execution_time": result.execution_time,
            "success": result.success,
            "error": result.error
        }
    
    def create_evaluation_suite(self, name: str, description: str = "") -> EvaluationSuite:
        """Create a new evaluation suite"""
        return EvaluationSuite(name=name, description=description)
    
    def add_test_case(self, 
                     suite: EvaluationSuite,
                     query: str,
                     expected_answer: Optional[str] = None,
                     context: Optional[List[str]] = None,
                     metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add a test case to an evaluation suite"""
        test_case = {
            "query": query,
            "expected_answer": expected_answer,
            "context": context or [],
            "metadata": metadata or {}
        }
        suite.test_cases.append(test_case)
    
    async def benchmark_rag_system(self, 
                                 rag_system,
                                 queries: List[str],
                                 repetitions: int = 3) -> Dict[str, Any]:
        """
        Benchmark RAG system performance with repeated queries
        
        Args:
            rag_system: System to benchmark
            queries: List of queries to test
            repetitions: Number of times to repeat each query
            
        Returns:
            Benchmark results with timing statistics
        """
        self.logger.info("starting_benchmark", queries_count=len(queries), repetitions=repetitions)
        
        benchmark_results = []
        
        for query in queries:
            query_times = []
            
            for rep in range(repetitions):
                start_time = time.time()
                try:
                    await rag_system.query(query)
                    execution_time = time.time() - start_time
                    query_times.append(execution_time)
                except Exception as e:
                    self.logger.error("benchmark_query_failed", query=query, rep=rep, error=str(e))
                    continue
            
            if query_times:
                benchmark_results.append({
                    "query": query,
                    "repetitions": len(query_times),
                    "min_time": min(query_times),
                    "max_time": max(query_times),
                    "avg_time": sum(query_times) / len(query_times),
                    "all_times": query_times
                })
        
        # Overall statistics
        all_times = []
        for result in benchmark_results:
            all_times.extend(result["all_times"])
        
        benchmark_summary = {
            "queries_tested": len(queries),
            "total_executions": len(all_times),
            "overall_min_time": min(all_times) if all_times else 0,
            "overall_max_time": max(all_times) if all_times else 0,
            "overall_avg_time": sum(all_times) / len(all_times) if all_times else 0,
            "query_results": benchmark_results,
            "timestamp": datetime.now().isoformat()
        }
        
        self.logger.info(
            "benchmark_completed",
            total_executions=len(all_times),
            avg_time=benchmark_summary["overall_avg_time"]
        )
        
        return benchmark_summary