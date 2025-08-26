#!/bin/bash
# Demo Script: System Health & Monitoring

echo "🏥 RAG System Health Monitoring Demo"
echo "===================================="
echo

echo "1. System Status Overview:"
curl -s http://localhost:8000/status | jq '.'
echo

echo "2. Detailed Health Check:"
curl -s http://localhost:8000/health | jq '.components[] | {name, type, status, healthy}'
echo

echo "3. Component Debug Info:"
curl -s http://localhost:8000/debug/components | jq 'keys'
echo

echo "✅ System is running with comprehensive monitoring!"