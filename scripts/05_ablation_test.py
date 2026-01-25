import requests
import json
import time

# CHANGED: Use Localhost to avoid firewall/routing issues
URL = "http://127.0.0.1:8081/run-pipeline"

TEST_CASE = {
    "condition": "Chronic Kidney Disease",
    "query": "I want a fruit salad.",
    "must_avoid": ["banana", "orange", "spinach", "tomato", "potato"],
    "must_include_context": ["leached", "low potassium", "renal"]
}

MODES = [
    {"name": "Test C: Agent Only (Baseline)", "rag": False, "kg": False},
    {"name": "Test B: Agent + RAG",           "rag": True,  "kg": False},
    {"name": "Test A: Agent + RAG + KG",      "rag": True,  "kg": True}
]

print("=== ABLATION TESTING: ACCURACY ANALYSIS ===\n")

for mode in MODES:
    print(f"--- Running {mode['name']} ---")
    payload = {
        "patient_id": "test_01",
        "age": 60, "gender": "Male", "location": "Singapore",
        "medical_record": {"condition": TEST_CASE["condition"], "current_meds": []},
        "user_query": TEST_CASE["query"],
        "enable_rag": mode["rag"],
        "enable_kg": mode["kg"]
    }

    start = time.time()
    try:
        response = requests.post(URL, json=payload, timeout=120)
        duration = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            plan_text = str(data.get("meal_plan", "")).lower()
            
            # SCORING
            score = 0
            reasons = []

            # 1. Format (20%)
            if "breakfast" in plan_text and "lunch" in plan_text: score += 20
            else: reasons.append("Format Fail")

            # 2. Safety (40%)
            violations = [bad for bad in TEST_CASE["must_avoid"] if bad in plan_text]
            if not violations: score += 40
            else: reasons.append(f"Safety Fail ({violations})")

            # 3. Context (40%)
            if mode["rag"]:
                if any(good in plan_text for good in TEST_CASE["must_include_context"]): score += 40
                else: reasons.append("Context Fail")
            else:
                score += 10 # Baseline pity points

            print(f"⏱ Time: {duration:.2f}s")
            print(f"📊 ACCURACY: {score}%")
            if reasons: print(f"   Issues: {reasons}")

        else:
            print(f"✘ FAIL: HTTP {response.status_code}")

    except Exception as e:
        print(f"✘ Error: {e}")
    print("\n")
