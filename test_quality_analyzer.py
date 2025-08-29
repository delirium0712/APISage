import asyncio
import os
from dotenv import load_dotenv
from agents.api_analyzer import APIAnalyzer
from config.settings import AgentConfig, SystemConfig
from infrastructure.backend_manager import BackendManager

# Load environment variables first
load_dotenv()

# This is a mock BackendManager for standalone testing.
# In the real app, this is initialized by the orchestrator.
class MockBackendManager:
    def __init__(self, system_config):
        from infrastructure.llm_manager import LLMManager
        self.llm_manager = LLMManager(system_config)

    async def initialize(self):
        await self.llm_manager.initialize()

    def get_connection(self, name: str):
        return None
    
    async def shutdown(self):
        pass

async def run_quality_analysis():
    """
    Runs the new LLM-powered API Analyzer to generate a quality report.
    """
    print("🚀 Initializing API Quality Analyzer...")
    
    # --- Configuration ---
    system_config = SystemConfig()
    agent_config = AgentConfig(name="api_quality_evaluator", model="gpt-3.5-turbo")
    
    print(f"🔑 OpenAI API Key loaded: {'YES' if os.getenv('OPENAI_API_KEY') else 'NO'}")
    print(f"🌐 Primary LLM Provider: {system_config.primary_llm_provider}")
    print(f"🤖 OpenAI Config: {system_config.llm_providers.get('openai', {})}")
    
    # --- Backend Setup ---
    # Use a mock backend manager for this test
    backend_manager = MockBackendManager(system_config)
    await backend_manager.initialize()
    
    # --- Agent Initialization ---
    analyzer = APIAnalyzer(
        config=agent_config,
        system_config=system_config,
        backend_manager=backend_manager
    )

    # --- API Documentation Content ---
    api_documentation_content = """
# Payment Processing API v2.1

## Overview
The Payment Processing API provides secure, scalable payment processing capabilities for e-commerce applications, subscription services, and digital marketplaces.

## Base URL
`https://api.payments.com/v2.1`

## Authentication
All API requests require authentication using API keys. Include the key in the Authorization header: `Authorization: Bearer <your_api_key>`

## Endpoints

### Process Payment
**POST** `/payments/process`
Process a new payment transaction. Lacks request body examples.

### Get Payment Details
**GET** `/payments/{payment_id}`
Retrieve detailed information about a specific payment. Missing error responses.
    """

    print("\n📝 Analyzing API Documentation...")
    print("-" * 30)
    
    # --- Run Analysis ---
    try:
        report = await analyzer.analyze_api_documentation(api_documentation_content)
        
        print("\n✅ API Quality Report Generated Successfully!")
        print("=" * 40)
        print(f"📊 Overall Score: {report.overall_score}/100 (Grade: {report.grade})")
        print(f"\n📝 Summary: {report.summary}")
        print("\n📋 Criteria Breakdown:")
        for criterion in report.criteria:
            print(f"  - {criterion.criterion}: {criterion.score}/100")
            print(f"    Reasoning: {criterion.reasoning}")
            
        print("\n🚀 Actionable Recommendations:")
        for item in report.action_items:
            print(f"  - [{item.priority}] {item.recommendation}")
            print(f"    Description: {item.description}")
        print("=" * 40)

    except Exception as e:
        print(f"\n❌ An error occurred during analysis: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await backend_manager.shutdown()

if __name__ == "__main__":
    # NOTE: Ensure your OPENAI_API_KEY is set in your environment variables.
    asyncio.run(run_quality_analysis())
