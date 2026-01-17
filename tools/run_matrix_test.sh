#!/bin/bash

# Configuration
ORCH_URL="http://192.168.2.57:8081/run-pipeline"

echo "========================================================"
echo "🧪 TEST 1: The 'Singaporean Diabetic' (Standard Path)"
echo "   GOAL: Verify local context (Singapore) & Diabetes rules"
echo "========================================================"
curl -s -X POST "$ORCH_URL" \
     -H "Content-Type: application/json" \
     -d '{
           "patient_id": "test_sg_diabetic",
           "age": 55,
           "gender": "Male",
           "location": "Singapore",
           "medical_record": {
             "condition": "Type 2 Diabetes",
             "current_meds": ["Metformin"]
           },
           "user_query": "I want a local hawker style lunch."
         }' | python3 -m json.tool

echo ""
echo "========================================================"
echo "🧪 TEST 2: The 'Indian Kidney Patient' (The Safety Trap)"
echo "   GOAL: Trigger Agent A4 (Safety) - Bananas + Lisinopril"
echo "   EXPECTATION: Look for 'SAFETY WARNINGS DETECTED' in output"
echo "========================================================"
curl -s -X POST "$ORCH_URL" \
     -H "Content-Type: application/json" \
     -d '{
           "patient_id": "test_in_ckd",
           "age": 65,
           "gender": "Female",
           "location": "India",
           "medical_record": {
             "condition": "Chronic Kidney Disease",
             "current_meds": ["Lisinopril"]
           },
           "user_query": "Can I eat Bananas and Spinach curry?"
         }' | python3 -m json.tool

echo ""
echo "========================================================"
echo "�� TEST 3: The 'American Hypertensive' (The Salt Trap)"
echo "   GOAL: Verify Sodium restriction logic (USA Context)"
echo "========================================================"
curl -s -X POST "$ORCH_URL" \
     -H "Content-Type: application/json" \
     -d '{
           "patient_id": "test_us_htn",
           "age": 40,
           "gender": "Male",
           "location": "USA",
           "medical_record": {
             "condition": "Hypertension",
             "current_meds": ["Amlodipine"]
           },
           "user_query": "Can I have potato chips and salted nuts?"
         }' | python3 -m json.tool

echo ""
echo "✅ MATRIX TEST COMPLETE"
