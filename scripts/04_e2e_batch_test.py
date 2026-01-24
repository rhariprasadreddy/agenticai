import requests
import time
import json

# CORRECTED URL: Pointing to Orchestrator on Port 8081
URL = "http://192.168.2.57:8081/run-pipeline"

SCENARIOS = [
    {
        "name": "Diabetes (Veg/Indian)",
        "payload": {
            "patient_id": "p001",
            "age": 45, "gender": "Male", "location": "India",
            "medical_record": {"condition": "Diabetes", "current_meds": ["Metformin"]},
            "user_query": "I am vegetarian and want Indian food."
        },
        "must_avoid": ["sugar", "jaggery", "sweets"],
        "expect_context": ["roti", "dal", "paneer"]
    },
    {
        "name": "Renal (Stage 4)",
        "payload": {
            "patient_id": "p002",
            "age": 60, "gender": "Female", "location": "Singapore",
            "medical_record": {"condition": "Kidney", "current_meds": ["Renal Caps"]},
            "user_query": "I have Stage 4 CKD. What can I eat?"
        },
        "must_avoid": ["banana", "spinach", "tomato"],
        "expect_context": ["leached", "white rice"]
    },
    {
        "name": "Lipids (High Chol)",
        "payload": {
            "patient_id": "p003",
            "age": 50, "gender": "Male", "location": "US",
            "medical_record": {"condition": "Lipids", "current_meds": ["Atorvastatin"]},
            "user_query": "I love fried food but have high cholesterol."
        },
        "must_avoid": ["butter", "ghee", "fried"],
        "expect_context": ["oats", "fiber"]
    },
    {
        "name": "Hypertension (High BP)",
        "payload": {
            "patient_id": "p004",
            "age": 55, "gender": "Female", "location": "UK",
            "medical_record": {"condition": "Hypertension", "current_meds": ["Lisinopril"]},
            "user_query": "I have high blood pressure. Can I eat pickles?"
        },
        "must_avoid": ["salt", "sodium", "pickle", "processed"],
        "expect_context": ["dash", "potassium", "fruits"]
    }
]

print("=== E2E ORCHESTRATION TESTS ===\n")

for sc in SCENARIOS:
    print(f"--- Running {sc['name']} ---")
    start = time.time()
    
    try:
        # TIMEOUT increased to 90s for full Agent+RAG+KG cycle
        response = requests.post(URL, json=sc['payload'], timeout=90)
        duration = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            
            # Check for Orchestrator-level errors
            if "error" in data:
                print(f"✘ FAIL: Orchestrator Error: {data['error']}")
            elif "meal_plan" not in data:
                print(f"✘ FAIL: Invalid Response Structure: {data.keys()}")
            else:
                plan_text = str(data.get("meal_plan", "")).lower()
                warnings = data.get("warnings", [])
                
                # Validation
                safe = all(bad not in plan_text for bad in sc['must_avoid'])
                context = any(good in plan_text for good in sc['expect_context'])
                
                if safe and not warnings:
                    print(f"✔ Safety Layer: Clean")
                else:
                    print(f"⚠ Safety Warnings: {warnings}")
                    
                if context:
                    print(f"✔ Context: Found expected keywords {sc['expect_context']}")
                else:
                    print(f"⚠ Context: Missing keywords {sc['expect_context']}")
                    
                print(f"⏱ Time: {duration:.2f}s")
                # Debug: Print a snippet of the real plan
                print(f"📝 Plan Snippet: {str(data['meal_plan'])[:150]}...")

        else:
            print(f"✘ FAIL: HTTP {response.status_code}")
            print(f"  Response: {response.text}")

    except Exception as e:
        print(f"✘ FAIL: Connection Error: {e}")
    
    print("")