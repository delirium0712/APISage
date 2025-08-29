#!/usr/bin/env python3

import asyncio
from agents.api_analyzer import APIAnalyzer, APIDocumentation
from config.settings import AgentConfig, SystemConfig

async def test_api_analyzer():
    # Create minimal config
    agent_config = AgentConfig(
        name="test_analyzer",
        model="gpt-3.5-turbo",
        temperature=0.7,
        max_tokens=1000
    )

    system_config = SystemConfig()

    # Create analyzer
    analyzer = APIAnalyzer(agent_config, system_config)

    # Test content
    test_content = """# Payment Processing API v2.1

## Overview
The Payment Processing API provides secure, scalable payment processing capabilities.

## Base URL
```
https://api.payments.com/v2.1
```

## Authentication
All API requests require authentication using API keys. Include the key in the Authorization header:
```
Authorization: Bearer <your_api_key>
```

## Endpoints

### Process Payment

**POST** `/payments/process`

Process a new payment transaction.

### Get Payment Details

**GET** `/payments/{payment_id}`

Retrieve detailed information about a specific payment.

### List Payments

**GET** `/payments`

Retrieve a paginated list of payments.

## Rate Limiting

- **Standard Plan**: 1,000 requests per minute
- **Professional Plan**: 10,000 requests per minute
- **Enterprise Plan**: 100,000 requests per minute"""

    print("Testing API Analyzer...")
    print("Input content:")
    print(test_content[:200] + "...")
    print()

    try:
        result = await analyzer.analyze_api_documentation(test_content)
        print("✅ Analysis completed!")
        print(f"Title: {result.title}")
        print(f"Version: {result.version}")
        print(f"Base URL: {result.base_url}")
        print(f"Endpoints found: {len(result.endpoints)}")
        print()

        for i, endpoint in enumerate(result.endpoints, 1):
            print(f"Endpoint {i}:")
            print(f"  Method: {endpoint.method}")
            print(f"  Path: {endpoint.path}")
            print(f"  Description: {endpoint.description}")
            print()

        print(f"Authentication methods: {len(result.authentication)}")
        for auth in result.authentication:
            print(f"  - {auth.type}: {auth.description[:50]}...")

        print(f"Rate limits: {result.rate_limits}")
        if result.rate_limits:
            if 'all_tiers' in result.rate_limits:
                print("  All tiers:")
                for tier in result.rate_limits['all_tiers']:
                    print(f"    - {tier}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_api_analyzer())
