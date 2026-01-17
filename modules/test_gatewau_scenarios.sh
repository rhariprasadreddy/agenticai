#!/bin/bash
# File: ~/agenticai/modules/test_gateway_scenarios.sh
# Targets MCP-Gateway (Port 8080)

URL="http://localhost:8080/run-pipeline"
echo "Testing MCP Gateway (Public Entry Point) at $URL..."
echo "---------------------------------------------------"

# 1. Healthy User (Banana Request)
echo "1. Healthy User Requesting Bananas (Should Allow):"
curl -s -X POST "$URL" -H "Content-Type: application/json" -d '{
    "patient_id": "test_gateway_01", "age": 25, "gender": "male", "location": "Singapore",
    "ailments": [], "medical_record": {},
    "query": "I want a banana smoothie."
}' | jq '.final_plan, .safety_notes'
echo "---------------------------------------------------"

# 2. Sick User (Safety Check)
echo "2. Hypertensive User on Lisinopril Requesting Bananas (Should BLOCK):"
curl -s -X POST "$URL" -H "Content-Type: application/json" -d '{
    "patient_id": "test_gateway_02", "age": 55, "gender": "female", "location": "Singapore",
    "ailments": ["Hypertension"], 
    "medical_record": {"current_meds": ["Lisinopril"]},
    "query": "I want a banana smoothie."
}' | jq '.final_plan, .safety_notes'
echo "---------------------------------------------------"
