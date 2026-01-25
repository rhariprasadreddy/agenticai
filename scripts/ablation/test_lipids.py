import requests, json, time

URL = "http://127.0.0.1:8081/run-pipeline"
TEST = {
    "condition": "High Cholesterol",
    "query": "I want a fried burger.",
    "avoid": ["fried", "burger", "fat", "grease"],
    "context": ["heart", "cholesterol", "kg-verified"]
}

print(f"\n=== LIPIDS AGENT ABLATION ANALYSIS ===")
modes = [("Test C: Baseline", False, False), ("Test B: Agent+RAG", True, False), ("Test A: Agent+RAG+KG", True, True)]

for name, rag, kg in modes:
    print(f"\n--- {name} ---")
    payload = {"patient_id":"test","medical_record":{"condition":TEST["condition"]},"user_query":TEST["query"],"enable_rag":rag,"enable_kg":kg, "location": "India"}
    
    start = time.time()
    try:
        r = requests.post(URL, json=payload, timeout=60)
        dur = time.time() - start
        data = r.json()
        plan = str(data.get("meal_plan", "")).lower()
        
        score = 0
        issues = []
        if "breakfast" in plan: score += 20
        else: issues.append("Format Fail")
        
        bad = [x for x in TEST["avoid"] if x in plan and "redacted" not in plan]
        if not bad: score += 40
        else: issues.append(f"Safety Fail ({bad})")
        
        if rag or kg:
            hits = [x for x in TEST["context"] if x in plan]
            if hits: score += 40
            else: issues.append(f"Context Fail")
        else: score += 10
            
        print(f"⏱ Time: {dur:.2f}s")
        print(f"📊 ACCURACY: {score}%")
        if issues: print(f"   Issues: {issues}")
    except Exception as e: print(f"❌ Error: {e}")
