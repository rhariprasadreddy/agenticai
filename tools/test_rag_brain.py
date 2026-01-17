import requests

RAG_HOST = "http://192.168.2.69"
ENDPOINTS = {
    "Diabetes": (f"{RAG_HOST}:9101/v1/diabetes/search", "sugar intake"),
    "Hypertension": (f"{RAG_HOST}:9103/v1/hypertension/search", "sodium limit"),
    "Lipids": (f"{RAG_HOST}:9102/v1/lipids/search", "saturated fat"),
    "Kidney": (f"{RAG_HOST}:9104/v1/kidney/search", "potassium")
}

print("=== TESTING RAG RETRIEVAL SYSTEMS ===")

for name, (url, query) in ENDPOINTS.items():
    print(f"\n🔍 Testing {name} RAG (Query: '{query}')...")
    try:
        response = requests.post(url, json={"query": query}, timeout=8)
        if response.status_code == 200:
            hits = response.json().get("hits", [])
            if hits:
                top_text = hits[0].get("text", "")[:60].replace("\n", " ")
                print(f"   ✅ SUCCESS. Found {len(hits)} docs. Snippet: '{top_text}...'")
            else:
                print(f"   ⚠️ WARNING: Connected, but found 0 documents.")
        else:
            print(f"   ❌ FAILED. Code: {response.status_code}")
    except Exception as e:
        print(f"   ❌ CONNECTION ERROR: {str(e)}")

print("\n=== RAG CHECK COMPLETE ===")
