#!/bin/bash
# Demo Script: Auto Code Generation

echo "⚡ Auto Code Generation Demo"
echo "============================"
echo

echo "Generating Python client for Stripe API..."
response=$(curl -s -X POST "http://localhost:8000/code/generate" \
-H "Content-Type: application/json" \
-d '{
  "api_doc": {
    "title": "Stripe API",
    "base_url": "https://api.stripe.com",
    "endpoints": [
      {"method": "POST", "path": "/v1/charges", "description": "Create a charge"},
      {"method": "GET", "path": "/v1/charges/{id}", "description": "Retrieve a charge"},
      {"method": "POST", "path": "/v1/customers", "description": "Create a customer"}
    ]
  },
  "language": "python",
  "template_name": "http_client"
}')

echo "Generated Client Class:"
echo "$response" | jq -r '.result.code' | head -20
echo "..."
echo

echo "Dependencies:"
echo "$response" | jq -r '.result.dependencies[]'
echo

echo "Usage Example:"
echo "$response" | jq -r '.result.usage_example'
echo

echo "✅ Production-ready client code generated with proper error handling and authentication!"