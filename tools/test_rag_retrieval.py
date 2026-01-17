import requests

# Configuration
RAG_HOST = "http://192.168.2.69"
ENDPOINTS = {
    "Diabetes RAG": f"{RAG_HOST}:9101/v1/diabetes/search",
    "Hypertension RAG": f"{RAG_HOST}:9103/v1/hypertension/search",
    "Lipids RAG": f"{RAG_HOST}:9102/v1/lipids/search", 
    "Kidney RAG": f"{RAG_HOST}:9104/v1/kidney/search"
}

# Queries specific to each domain to test retrieval quality
QUERIES = {
    "Diabetes RAG": "sugar intake guidelines",
    "Hypertension RAG": "sodium limits daily",
    "Lipids RAG": "saturated fat recommendations",
    "Kidney RAG": "potassium restriction stages"
}

print("=== TESTING RAG RETRIEVAL SYSTEMS ===")

for name, url in ENDPOINTS.items():
    print(f"\nTesting {name}...")
    query_text = QUERIES.get(name, "dietary guidelines")
    
    try:
        payload = {"query": query_text}
        # Note: Some services might use /rag/query, adjust if needed based on your grep results
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            hits = data.get("hits", []) or data.get("results", [])
            if len(hits) > 0:
                top_hit = hits[0].get("text", "")[:100].replace("\n", " ")
                print(f"✅ SUCCESS. Retrieved {len(hits)} documents.")
                print(f"   Top Hit Snippet: '{top_hit}...'")
            else:
                print(f"⚠️ WARNING: Service replied, but found NO documents.")
        else:
            print(f"❌ FAILED. Status Code: {response.status_code}")
    except Exception as e:
        print(f"❌ CONNECTION ERROR: {str(e)}")

print("\n=== RAG DIAGNOSTIC COMPLETE ===")
