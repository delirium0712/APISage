#!/usr/bin/env python3
"""Test the score extraction function"""

def extract_scores_from_analysis(analysis_text):
    """Extract scores from LLM analysis text"""
    scores = {
        'overall': 75,  # Default
        'completeness': 70,
        'documentation': 65,
        'security': 60,
        'usability': 70,
        'standards': 65
    }
    
    # Try to extract actual scores from analysis
    import re
    
    # Pattern for "Overall Score:** 30/100"
    overall_match = re.search(r'overall score:\*?\*?\s*(\d+)/100', analysis_text, re.IGNORECASE)
    if overall_match:
        scores['overall'] = int(overall_match.group(1))
    
    # Pattern for "- **Completeness:** 20/100"
    completeness_match = re.search(r'\*?\*?completeness:\*?\*?\s*(\d+)/100', analysis_text, re.IGNORECASE)
    if completeness_match:
        scores['completeness'] = int(completeness_match.group(1))
    
    documentation_match = re.search(r'\*?\*?documentation:\*?\*?\s*(\d+)/100', analysis_text, re.IGNORECASE)
    if documentation_match:
        scores['documentation'] = int(documentation_match.group(1))
    
    security_match = re.search(r'\*?\*?security:\*?\*?\s*(\d+)/100', analysis_text, re.IGNORECASE)
    if security_match:
        scores['security'] = int(security_match.group(1))
    
    usability_match = re.search(r'\*?\*?usability:\*?\*?\s*(\d+)/100', analysis_text, re.IGNORECASE)
    if usability_match:
        scores['usability'] = int(usability_match.group(1))
    
    standards_match = re.search(r'\*?\*?standards[^:]*:\*?\*?\s*(\d+)/100', analysis_text, re.IGNORECASE)
    if standards_match:
        scores['standards'] = int(standards_match.group(1))
    
    return scores

# Test data from actual API response
test_analysis = """### 📊 API Score Breakdown
**Overall Score:** 30/100
- **Completeness:** 20/100 - The API lacks essential endpoints and features such as authentication, error responses, and pagination.
- **Documentation:** 10/100 - There is no description provided for the API, which is critical for understanding its purpose.
- **Security:** 0/100 - The API has no authentication mechanisms, exposing it to potential misuse.
- **Usability:** 40/100 - The single endpoint is usable but lacks necessary features like error handling and response schemas.
- **Standards Compliance:** 50/100 - The API follows basic OpenAPI structure but fails to provide detailed responses and descriptions."""

# Test the extraction
scores = extract_scores_from_analysis(test_analysis)
print("Extracted Scores:")
print(f"Overall: {scores['overall']}/100")
print(f"Completeness: {scores['completeness']}/100")
print(f"Documentation: {scores['documentation']}/100")
print(f"Security: {scores['security']}/100")
print(f"Usability: {scores['usability']}/100")
print(f"Standards: {scores['standards']}/100")

# Test expected outputs
expected = {
    'overall': 30,
    'completeness': 20,
    'documentation': 10,
    'security': 0,
    'usability': 40,
    'standards': 50
}

print("\nTest Results:")
for key in expected:
    if scores[key] == expected[key]:
        print(f"✅ {key}: {scores[key]} (correct)")
    else:
        print(f"❌ {key}: {scores[key]}, expected {expected[key]}")