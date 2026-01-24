import requests
import json
import time

# Define the targets
AGENTS = {
    "Diabetes":     {"url": "http://192.168.2.69:8080/v1/diabetes/plan",     "payload": {"text": "I am a diabetic patient, vegetarian."}},
    "Hypertension": {"url": "http://192.168.2.69:8082/v1/hypertension/plan", "payload": {"text": "I have high blood pressure."}},
    "Lipids":       {"url": "http://192.168.2.69:9006/v1/lipids/plan",       "payload": {"text": "I have high cholesterol."}},
    "Kidney":       {"url": "http://192.168.2.69:9008/v1/kidney/plan",       "payload": {"text": "I have stage 3 CKD."}}
}

print("=== RAW MODEL TESTS (Gateway -> Xeon) ===\n")

for name, data in AGENTS.items():
    print(f"Testing {name} at {data['url']}...")
    try:
        start_time = time.time()
        # The fix: Sending json=data['payload'] which matches {"text": "..."}
        response = requests.post(data['url'], json=data['payload'], timeout=30)
        duration = time.time() - start_time
        
        if response.status_code == 200:
            print(f"✔ PASS: Valid Response in {duration:.2f}s")
            # Optional: Print first 50 chars to verify content
            # print(f"  Response: {response.json().get('plan', '')[:50]}...")
        else:
            print(f"✘ FAIL: Status {response.status_code}")
            print(f"  Error: {response.text}")
            
    except Exception as e:
        print(f"✘ FAIL: Connection Error. {e}")
    print("-" * 30)