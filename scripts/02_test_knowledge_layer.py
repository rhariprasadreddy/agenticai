import requests
import json
import time

# XEON Server IP
XEON_IP = "192.168.2.69"

# CORRECTED: Using specific endpoints found in your grep output
RAG_CONFIG = {
    "Diabetes":     {"port": 9101, "endpoint": "/v1/diabetes/search"},
    "Lipids":       {"port": 9102, "endpoint": "/v1/lipids/search"},
    "Hypertension": {"port": 9103, "endpoint": "/v1/hypertension/search"},
    "Kidney":       {"port": 9104, "endpoint": "/v1/kidney/search"}
}

print("=== KNOWLEDGE LAYER TESTS (Gateway -> Xeon) ===\n")

for name, config in RAG_CONFIG.items():
    url = f"http://{XEON_IP}:{config['port']}{config['endpoint']}"
    print(f"Testing {name} RAG at {url}...")
    
    # Payload matches the 'SearchResponse' model found in grep
    payload = {"query": "diet plan", "top_k": 3}
    
    try:
        start = time.time()
        response = requests.post(url, json=payload, timeout=10)
        duration = time.time() - start
        
        if response.status_code == 200:
            print(f"✔ PASS: {name} responded in {duration:.2f}s")
        else:
            print(f"✘ FAIL: {name} returned {response.status_code}")
            print(f"  Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print(f"✘ FAIL: Connection Refused to {name} (Port {config['port']})")
    except Exception as e:
        print(f"✘ FAIL: Error {e}")

    print("-" * 30)
