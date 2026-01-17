import requests
import json

# Configuration
KG_HOST = "http://192.168.2.69" # Inference Server IP
ENDPOINTS = {
    "Diabetes": f"{KG_HOST}:9201/v1/diabetes/kg/check_foods",
    "Hypertension": f"{KG_HOST}:9202/v1/hypertension/kg/check_foods",
    "Lipids": f"{KG_HOST}:9203/v1/lipids/kg/check_foods",
    "Kidney": f"{KG_HOST}:9204/v1/kidney/kg/check_foods"
}

TEST_PAYLOAD = {"foods": ["Spinach", "Salt", "Cake"]}

print("=== TESTING MEDICAL KNOWLEDGE GRAPHS ===")

for name, url in ENDPOINTS.items():
    print(f"\nTesting {name} Graph at {url}...")
    try:
        response = requests.post(url, json=TEST_PAYLOAD, timeout=5)
        if response.status_code == 200:
            data = response.json()
            # Check if we got results
            results = data.get("results", [])
            if len(results) > 0:
                print(f"✅ SUCCESS. Found data for: {[r['food'] for r in results]}")
            else:
                print(f"⚠️ WARNING: Service replied, but graph seems empty (Unknown status).")
        else:
            print(f"❌ FAILED. Status Code: {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"❌ CONNECTION ERROR: {str(e)}")

print("\n=== KG DIAGNOSTIC COMPLETE ===")
