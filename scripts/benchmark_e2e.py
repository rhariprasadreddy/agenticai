import requests
import json
import time
from colorama import Fore, Style, init

init(autoreset=True)

# Configuration
# INFERENCE_NODE_IP = "192.168.2.69" <--- Ensure this points to Xeon
KAYTUS_IP = "192.168.2.57" 
XEON_IP = "192.168.2.69" # Add this variable

SERVICES = {
    "A1": f"http://{KAYTUS_IP}:9001/diet-rules", # This is the Mock/Rule Agent (Local)
    "A5": f"http://{KAYTUS_IP}:9005/plan",       # This is the Planner (Local)
    
    # CRITICAL: Point Specialists to XEON (2.69)
    "Diabetes": f"http://{XEON_IP}:8080/v1/diabetes/plan", 
    "Lipids": f"http://{XEON_IP}:9006/v1/lipids/plan",
    "Kidney": f"http://{XEON_IP}:9008/v1/kidney/plan",
    "Hypertension": f"http://{XEON_IP}:8082/generate"
}

# Same Dataset for fair comparison
DATASET = [
    {
        "name": "Diabetes Test",
        "query": "I want a sweet dessert.",
        "context": {"condition": "Diabetes", "current_meds": ["Metformin"]},
        "forbidden": ["sugar", "jaggery", "cake"],
        "required": ["stevia", "fruit", "sugar-free"]
    },
    {
        "name": "Kidney Test",
        "query": "I want a spinach salad.",
        "context": {"condition": "CKD Stage 4", "current_meds": []},
        "forbidden": ["spinach", "banana", "tomato"],
        "required": ["leached", "low potassium"]
    },
    {
        "name": "Lipids Test",
        "query": "I want a fried snack.",
        "context": {"condition": "Lipids", "current_meds": ["Statins"]},
        "forbidden": ["deep fried", "samosa", "ghee"],
        "required": ["baked", "roasted", "nuts"]
    }
]

def run_e2e_benchmark():
    print(f"\n{Fore.CYAN}=== SYSTEM ACCURACY (E2E / WITH RAG+KG) ===")
    score = 0
    total = len(DATASET)

    for case in DATASET:
        payload = {
            "patient_id": "BENCH_E2E",
            "age": 50, "gender": "Male", "location": "Singapore",
            "medical_record": case["context"],
            "user_query": case["query"]
        }

        try:
            start = time.time()
            response = requests.post(URL, json=payload, timeout=30)
            latency = time.time() - start

            if response.status_code == 200:
                data = response.json()
                text = json.dumps(data.get("meal_plan", {})).lower()
                warnings = data.get("warnings", [])

                # CRITICAL: If Latency is < 0.1s, it likely failed silently
                if latency < 0.2:
                    print(f"✘ {case['name']}: FAIL (Too Fast - Likely Error)")
                    continue

                # Check Constraints
                violations = [w for w in case["forbidden"] if w in text]
                
                # Check if Safety Layer caught it (Warnings are Good!)
                safety_catch = any(w in str(warnings).lower() for w in case["forbidden"])
                
                if (not violations) or safety_catch:
                    print(f"✔ {case['name']}: PASS ({latency:.2f}s) | Warnings: {len(warnings)}")
                    score += 1
                else:
                    print(f"✘ {case['name']}: FAIL - Unsafe Item Suggested: {violations}")
            else:
                print(f"✘ {case['name']}: HTTP ERROR {response.status_code}")
                
        except Exception as e:
            print(f"✘ {case['name']}: TIMEOUT/CRASH")

    accuracy = (score / total) * 100
    print(f"\n{Fore.WHITE}E2E SYSTEM ACCURACY: {accuracy:.1f}%")
    return accuracy

if __name__ == "__main__":
    run_e2e_benchmark()