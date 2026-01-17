#!/bin/bash
# File: ~/agenticai/modules/test_orchestrator_functions.sh
# Targets Orchestrator (Port 8081)

URL="http://localhost:8081/run-pipeline"
echo "Testing Orchestrator Logic Core at $URL..."

# 1. Schema Validation Test (Missing Fields)
echo "1. Testing Invalid Schema (Should fail gracefully):"
curl -s -X POST "$URL" -H "Content-Type: application/json" -d '{
    "patient_id": "bad_request"
    # Missing ailments, age, etc.
}' | jq .
echo "---------------------------------------------------"

# 2. Logic Routing Test (Kidney Logic)
echo "2. Testing Kidney Agent Routing (Should trigger A3 Math + A2 Restrictions):"
curl -s -X POST "$URL" -H "Content-Type: application/json" -d '{
    "patient_id": "logic_check", "age": 60, "gender": "male", "location": "India",
    "ailments": ["Chronic Kidney Disease"],
    "medical_record": {"creatinine": 2.5},
    "query": "Can I eat high protein steak?"
}' | jq '.final_plan'
echo "---------------------------------------------------"
