#!/bin/bash

echo "🚀 Testing Full Pipeline (UI -> Orchestrator -> A5 -> OpenVINO)..."

# Sending a request to the Orchestrator (Port 8081)
# mimicking the UI payload
curl -X POST "http://localhost:8081/run-pipeline" \
     -H "Content-Type: application/json" \
     -d '{
           "patient_id": "test_patient_01",
           "age": 45,
           "gender": "Male",
           "location": "Singapore",
           "medical_record": {
             "condition": "Type 2 Diabetes",
             "current_meds": ["Metformin"]
           },
           "user_query": "Generate a plan"
         }' | jq .