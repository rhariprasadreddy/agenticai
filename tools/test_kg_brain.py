import requests
import json

# Configuration - Adjust IPs if needed
KG_HOST = "http://192.168.2.69" 
ENDPOINTS = {
    "Diabetes": f"{KG_HOST}:9201/v1/diabetes/kg/check_foods",
    "Hypertension": f"{KG_HOST}:9202/v1/hypertension/kg/check_foods",
    "Lipids": f"{KG_HOST}:9203/v1/lipids/kg/check_foods",
    "Kidney": f"{KG_HOST}:9204/v1/kidney/kg/check_foods"
}

TEST_FOODS = ["Spinach", "Salt", "Banana", "Cake"]

print("=== TESTING MEDICAL KNOWLEDGE GRAPHS ===")

for name, url in ENDPOINTS.items():
    print(f"\n🔍 Testing {name} Graph...")
    try:
        response = requests.post(url, json={"foods": TEST_FOODS}, timeout=5)
        if response.status_code == 200:
            results = response.json().get("results", [])
            found_items = [r['food'] for r in results if r['status'] != 'UNKNOWN']
            
            if found_items:
                print(f"   ✅ SUCCESS. Validated: {found_items}")
            else:
                print(f"   ⚠️ WARNING: Connected, but all items returned UNKNOWN status.")
        else:
            print(f"   ❌ FAILED. Code: {response.status_code}")
    except Exception as e:
        print(f"   ❌ CONNECTION ERROR: {str(e)}")

print("\n=== KG CHECK COMPLETE ===")
