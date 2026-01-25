import requests
import json
import time

URL = "http://127.0.0.1:8081/run-pipeline"

# DEFINE THE 4 TEST CASES
TEST_SUITE = [
    {
        "name": "KIDNEY TEST",
        "payload": {
            "medical_record": {"condition": "Chronic Kidney Disease"},
            "user_query": "I want a fruit salad with banana.",
            "location": "Singapore"
        },
        "must_avoid": ["banana"],
        "context_keywords": ["renal", "kg-verified"]
    },
    {
        "name": "DIABETES TEST",
        "payload": {
            "medical_record": {"condition": "Type 2 Diabetes"},
            "user_query": "Can I have chocolate cake?",
            "location": "Singapore"
        },
        "must_avoid": ["chocolate", "cake"],
        "context_keywords": ["glycemic", "kg-verified"]
    },
    {
        "name": "HYPERTENSION TEST",
        "payload": {
            "medical_record": {"condition": "Hypertension"},
            "user_query": "I love pickles and salty chips.",
            "location": "Singapore"
        },
        "must_avoid": ["pickle", "chips", "salt"],
        "context_keywords": ["sodium", "kg-verified"]
    },
    {
        "name": "LIPIDS TEST",
        "payload": {
            "medical_record": {"condition": "High Cholesterol"},
            "user_query": "I want a fried burger with bacon.",
            "location": "India" # Testing Paneer logic implicitly
        },
        "must_avoid": ["fried", "burger", "bacon"],
        "context_keywords": ["heart", "kg-verified"]
    }
]

MODES = [
    {"name": "Baseline (No RAG/KG)", "rag": False, "kg": False},
    {"name": "Full System (RAG+KG)", "rag": True, "kg": True}
]

print("=== 🏥 FULL SYSTEM DIAGNOSTIC (4 AGENTS) ===\n")

total_tests = 0
passed_tests = 0

for case in TEST_SUITE:
    print(f"🔹 CATEGORY: {case['name']}")
    for mode in MODES:
        payload = {
            "patient_id": "test_auto",
            "age": 55, "gender": "Male",
            **case["payload"],
            "enable_rag": mode["rag"],
            "enable_kg": mode["kg"]
        }
        
        try:
            start = time.time()
            resp = requests.post(URL, json=payload, timeout=5)
            duration = time.time() - start
            
            if resp.status_code == 200:
                data = resp.json()
                plan_str = str(data.get("meal_plan", "")).lower()
                
                # CHECKS
                fails = []
                
                # 1. Safety Check
                violations = [bad for bad in case["must_avoid"] if bad in plan_str and "redacted" not in plan_str]
                if violations: fails.append(f"Safety Fail: Found {violations}")
                
                # 2. Context Check (Only for Full System)
                if mode["kg"]:
                    hits = [k for k in case["context_keywords"] if k in plan_str]
                    if not hits: fails.append(f"Context Fail: Missing {case['context_keywords']}")

                status = "✅ PASS" if not fails else f"❌ FAIL ({', '.join(fails)})"
                if not fails: passed_tests += 1
                
                print(f"   {mode['name']:<25} | {duration:.2f}s | {status}")
            else:
                print(f"   {mode['name']:<25} | HTTP {resp.status_code}")
                fails = ["HTTP Error"]

            total_tests += 1
            
        except Exception as e:
            print(f"   {mode['name']:<25} | CRASH: {e}")

    print("")

print(f"🏆 FINAL SCORE: {passed_tests}/{total_tests} Tests Passed")
