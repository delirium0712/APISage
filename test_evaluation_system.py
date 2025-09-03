#!/usr/bin/env python3
"""
Test script for the LLM evaluation system
Demonstrates how to evaluate API analysis quality
"""

import json
import asyncio
import requests

# Sample API spec for testing
SAMPLE_SPEC = {
    "openapi": "3.0.0",
    "info": {
        "title": "User Management API",
        "version": "1.0.0",
        "description": "A basic API for managing users"
    },
    "paths": {
        "/users": {
            "get": {
                "summary": "List users",
                "responses": {
                    "200": {
                        "description": "List of users",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "array",
                                    "items": {"$ref": "#/components/schemas/User"}
                                }
                            }
                        }
                    }
                }
            }
        }
    },
    "components": {
        "schemas": {
            "User": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"}
                }
            }
        }
    }
}

# Example of a GOOD analysis (should score highly)
GOOD_ANALYSIS = """
## API Score Breakdown
**Overall Score:** 65/100
- **Completeness:** 40/100 - Missing essential CRUD operations (POST, PUT, DELETE for /users)
- **Documentation:** 70/100 - Basic documentation present but lacks examples
- **Security:** 50/100 - No authentication configured
- **Usability:** 80/100 - Clean, simple structure
- **Standards Compliance:** 85/100 - Follows OpenAPI 3.0 standards

## Executive Summary
This User Management API provides basic user listing functionality but lacks essential CRUD operations. The GET /users endpoint is well-structured but missing pagination for scalability.

## Critical Issues (Priority Order)
1. **Issue:** Missing user creation endpoint
   - **Location:** No POST /users endpoint defined
   - **Impact:** Cannot create new users, severely limiting API functionality
   - **Fix:** Add POST /users with request body schema
   - **Priority:** High - Essential for user management

2. **Issue:** No authentication configured
   - **Location:** No security schemes or endpoint-level security
   - **Impact:** Unprotected access to user data
   - **Fix:** Add JWT or API key authentication
   - **Priority:** High - Security vulnerability

## Specific Recommendations
1. **Add POST /users endpoint:**
```yaml
/users:
  post:
    summary: Create a new user
    requestBody:
      required: true
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/User'
```

2. **Add pagination to GET /users:**
```yaml
parameters:
  - name: limit
    in: query
    schema:
      type: integer
      default: 20
```
"""

# Example of a BAD analysis (should score poorly)
BAD_ANALYSIS = """
## API Analysis
This API looks good overall. It follows REST principles and best practices.

## Recommendations
- Implement proper authentication
- Add error handling
- Use pagination for large datasets
- Follow OpenAPI standards
- Add comprehensive documentation
- Implement rate limiting
- Use HTTPS
- Add logging and monitoring
- Consider caching strategies
- Implement input validation

## Security
The API should have proper security measures in place.

## Performance
Consider performance optimizations like caching and CDN usage.

## Conclusion
This is a well-designed API that follows industry standards.
"""

def test_evaluation_system():
    """Test the complete evaluation system"""
    
    print("🧪 Testing LLM Evaluation System")
    print("=" * 50)
    
    # Test 1: Evaluate a good analysis
    print("\n📊 Test 1: Evaluating GOOD Analysis")
    print("-" * 40)
    
    good_evaluation_request = {
        "openapi_spec": SAMPLE_SPEC,
        "llm_analysis": GOOD_ANALYSIS,
        "analysis_context": {
            "analysis_depth": "comprehensive",
            "focus_areas": ["completeness", "security"],
            "api_title": "User Management API"
        }
    }
    
    try:
        response = requests.post(
            "http://localhost:8080/evaluate-analysis",
            json=good_evaluation_request,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Evaluation successful!")
            print(f"Overall Score: {result['overall_score']:.1f}/100")
            print(f"Metric Scores:")
            for metric, score in result['metric_scores'].items():
                print(f"  - {metric}: {score:.1f}/100")
            print(f"Evaluation Time: {result['evaluation_time']:.2f}s")
            print(f"Evaluator Model: {result['evaluator_model']}")
        else:
            print(f"❌ Evaluation failed: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
    
    # Test 2: Evaluate a bad analysis
    print("\n📊 Test 2: Evaluating BAD Analysis")
    print("-" * 40)
    
    bad_evaluation_request = {
        "openapi_spec": SAMPLE_SPEC,
        "llm_analysis": BAD_ANALYSIS,
        "analysis_context": {
            "analysis_depth": "comprehensive",
            "api_title": "User Management API"
        }
    }
    
    try:
        response = requests.post(
            "http://localhost:8080/evaluate-analysis",
            json=bad_evaluation_request,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Evaluation successful!")
            print(f"Overall Score: {result['overall_score']:.1f}/100")
            print(f"Metric Scores:")
            for metric, score in result['metric_scores'].items():
                print(f"  - {metric}: {score:.1f}/100")
            print(f"Improvement Suggestions:")
            for suggestion in result['improvement_suggestions'][:3]:
                print(f"  - {suggestion}")
        else:
            print(f"❌ Evaluation failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
    
    # Test 3: Check evaluation metrics dashboard
    print("\n📈 Test 3: Evaluation Dashboard Metrics")
    print("-" * 40)
    
    try:
        response = requests.get("http://localhost:8080/evaluation-metrics")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Dashboard accessible!")
            
            if result['metrics'].get('total_evaluations', 0) > 0:
                metrics = result['metrics']
                print(f"Total Evaluations: {metrics['total_evaluations']}")
                print(f"Average Score: {metrics['average_score']:.1f}")
                print(f"Score Trend: {metrics['score_trend']}")
                print(f"Metric Averages:")
                for metric, avg in metrics.get('metric_averages', {}).items():
                    print(f"  - {metric}: {avg:.1f}")
            else:
                print("No evaluations recorded yet in dashboard")
                
            print(f"Evaluator Model: {result['dashboard_info']['evaluator_model']}")
            
        else:
            print(f"❌ Dashboard access failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Dashboard test failed: {str(e)}")
    
    # Test 4: Full analysis with evaluation
    print("\n🔄 Test 4: Analysis + Evaluation Combined")
    print("-" * 40)
    
    analysis_request = {
        "openapi_spec": SAMPLE_SPEC,
        "analysis_depth": "comprehensive",
        "focus_areas": ["security", "completeness"]
    }
    
    try:
        response = requests.post(
            "http://localhost:8080/analyze-with-evaluation",
            json=analysis_request,
            timeout=120  # Longer timeout as this does both analysis and evaluation
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Combined analysis + evaluation successful!")
            
            analysis = result['analysis']
            evaluation = result['evaluation']
            
            print(f"\nAnalysis Results:")
            print(f"  - API Title: {analysis['metadata']['api_title']}")
            print(f"  - Endpoints: {analysis['metadata']['endpoints_count']}")
            print(f"  - Analysis Time: {analysis['metadata']['analysis_time']:.2f}s")
            print(f"  - Model Used: {analysis['metadata']['model_used']}")
            
            print(f"\nEvaluation Results:")
            print(f"  - Overall Score: {evaluation['overall_score']:.1f}/100")
            print(f"  - Evaluation Time: {evaluation['evaluation_time']:.2f}s")
            print(f"  - Top Metric: {max(evaluation['metric_scores'].items(), key=lambda x: x[1])}")
            
            print(f"\nSystem Performance:")
            total_time = analysis['metadata']['analysis_time'] + evaluation['evaluation_time']
            print(f"  - Total Processing Time: {total_time:.2f}s")
            print(f"  - Analysis Quality Score: {evaluation['overall_score']:.1f}/100")
            
        else:
            print(f"❌ Combined test failed: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Combined test failed: {str(e)}")
    
    print("\n🎉 Evaluation System Test Complete!")
    print("=" * 50)
    print("\nKey Features Demonstrated:")
    print("✅ Individual analysis evaluation")
    print("✅ Quality metrics scoring (5 dimensions)")  
    print("✅ Performance tracking dashboard")
    print("✅ Combined analysis + evaluation workflow")
    print("✅ Improvement suggestions generation")
    print("✅ LLM-as-Judge evaluation approach")


if __name__ == "__main__":
    test_evaluation_system()