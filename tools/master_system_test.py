import requests
import json
import time

# ==========================================
# 🔧 CONFIGURATION: DUAL SERVER SETUP
# ==========================================
# Server A (Kaytus): Gateway, Orchestrator, Agents
KAYTUS_IP = "192.168.2.57"

# Server B (SMGAILAB): Knowledge Graphs, RAG, LLM
SMGAILAB_IP = "192.168.2.69"

TIMEOUT_SEC = 20
# ==========================================

PAYLOAD_PROFILE = {
    "patient_id": "test_user_ip",
    "age": 55,
    "gender": "Male",
    "location": "Singapore",
    "medical_record": {
        "condition": "Type 2 Diabetes",
        "current_meds": ["Metformin"]
    },
    "user_query": "Can I eat white rice?",
    "foods_to_check": ["White Rice", "Brown Rice"]
}

def print_header(title):
    print(f"\n{'='*60}\n🔎 {title}\n{'='*60}")

def test_endpoint(name, url, payload, expected_key=None):
    print(f"Testing {name}...")
    print(f"   Target: {url}")
    try:
        start = time.time()
        resp = requests.post(url, json=payload, timeout=TIMEOUT_SEC)
        duration = round(time.time() - start, 2)
        
        if resp.status_code == 200:
            data = resp.json()
            if expected_key and expected_key not in str(data):
                print(f"   ⚠️  WARNING: 200 OK, but missing data '{expected_key}'")
            else:
                print(f"   ✅ SUCCESS ({duration}s)")
        elif resp.status_code == 405:
             print(f"   ✅ SUCCESS (Server Alive - 405 Method Not Allowed)")
        else:
            print(f"   ❌ FAILED: Status {resp.status_code}")
    except Exception as e:
        print(f"   ❌ CONNECTION ERROR: {str(e)}")

# --- EXECUTION ---

# 1. KAYTUS CHECKS (Orchestrator & Agents)
print_header(f"SERVER A (KAYTUS {KAYTUS_IP})")
test_endpoint("Orchestrator", f"http://{KAYTUS_IP}:8081/run-pipeline", PAYLOAD_PROFILE, "meal_plan")

# Check Agent A1 directly
p_a1 = PAYLOAD_PROFILE.copy()
p_a1["ailments"] = ["Type 2 Diabetes"]
test_endpoint("Agent A1 (Rules)", f"http://{KAYTUS_IP}:9001/diet-rules", p_a1, "guidelines")

# Check Agent A4 (Safety) - This tests if Kaytus can reach SMGAILAB internally
p_a4 = {
    "patient_id": "test", 
    "medical_record": PAYLOAD_PROFILE["medical_record"], 
    "foods_to_check": ["Cake", "Spinach"]
}
test_endpoint("Agent A4 (Pharmacist)", f"http://{KAYTUS_IP}:9004/conflicts", p_a4, "interactions")


# 2. SMGAILAB CHECKS (Backend)
print_header(f"SERVER B (SMGAILAB {SMGAILAB_IP})")

# Check LLM
test_endpoint("LLM Health", f"http://{SMGAILAB_IP}:8080/docs", {}, "")

# Check RAG
rag_payload = {"query": "dietary guidelines"}
test_endpoint("RAG Diabetes", f"http://{SMGAILAB_IP}:9101/v1/diabetes/search", rag_payload, "hits")

# Check KG
kg_payload = {"foods": ["Spinach", "Cake"]}
test_endpoint("KG Diabetes", f"http://{SMGAILAB_IP}:9201/v1/diabetes/kg/check_foods", kg_payload, "results")

print("\n✅ DISTRIBUTED SYSTEM TEST COMPLETE")