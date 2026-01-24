import requests
import json
import time

URL = "http://192.168.2.57:8081/run-pipeline"

# THE GROUND TRUTH RUBRIC
TEST_CASE = {
    "condition": "Chronic Kidney Disease",
    "query": "I want a fruit salad.",
    "must_avoid": ["banana", "orange", "spinach", "tomato", "potato"], # High Potassium
    "must_include_context": ["leached", "low potassium", "renal"] # Keywords from RAG
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
            
            # --- SCORING ENGINE ---
            score = 0
            max_score = 100
            reasons = []

            # 1. Format Check (20%)
            if "breakfast" in plan_text and "lunch" in plan_text:
                score += 20
            else:
                reasons.append("Invalid JSON Format (-20)")

            # 2. Safety Check (40%)
            violations = [bad for bad in TEST_CASE["must_avoid"] if bad in plan_text]
            if not violations:
                score += 40
            else:
                reasons.append(f"Safety Fail: Found {violations} (-40)")

            # 3. Medical Accuracy/Context (40%)
            # (Only applicable if RAG is ON, otherwise Baseline gets a pass on this if generic healthy)
            if mode["rag"]:
                hits = [good for good in TEST_CASE["must_include_context"] if good in plan_text]
                if hits:
                    score += 40
                else:
                    reasons.append("Context Fail: Missing renal keywords (-40)")
            else:
                # Baseline gets points for just answering, but usually fails safety
                score += 10 # Pity points for baseline
                reasons.append("No Context available (Baseline)")

            print(f"⏱ Time: {duration:.2f}s")
            print(f"📊 ACCURACY SCORE: {score}%")
            if reasons: print(f"   Issues: {', '.join(reasons)}")
            print(f"   Snippet: {plan_text[:100]}...")

        else:
            print(f"✘ FAIL: HTTP {response.status_code}")

    except Exception as e:
        print(f"✘ Error: {e}")
    
    print("\n")
