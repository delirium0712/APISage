#!/bin/bash
# Demo Script: Intelligent API Analysis

echo "🔍 Intelligent API Analysis Demo"
echo "================================"
echo

echo "Analyzing Stripe API documentation..."
curl -s -X POST "http://localhost:8000/documents/analyze-api" \
-H "Content-Type: application/json" \
-d '{
  "content": "# Stripe API\n\nThe Stripe API is organized around REST. Our API has predictable resource-oriented URLs, accepts form-encoded request bodies, returns JSON-encoded responses.\n\n## Authentication\nAuthenticate using API keys in the Authorization header.\n\n## Core Resources\n\n### Charges\n- POST /v1/charges - Create a charge\n- GET /v1/charges/{id} - Retrieve a charge\n- POST /v1/charges/{id}/capture - Capture a charge\n\n### Customers\n- POST /v1/customers - Create a customer\n- GET /v1/customers/{id} - Retrieve a customer\n- POST /v1/customers/{id} - Update a customer",
  "source_url": "https://stripe.com/docs/api"
}' | jq '.result | {title, base_url, endpoints: .endpoints[0:3]}'

echo
echo "✅ Extracted structured API information with endpoints, authentication, and parameters!"