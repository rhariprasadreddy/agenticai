import requests
import json

# CONFIG
XEON_IP = "192.168.2.69"
AGENT_URL = f"http://{XEON_IP}:8080/v1/diabetes/plan" # Diabetes Agent
RAG_URL = f"http://{XEON_IP}:9101/v1/diabetes/search"

print("=== DEBUGGING ORCHESTRATOR LOGIC ===\n")

# 1. TEST RAG CALL
print(f"1. Testing RAG Call to {RAG_URL}...")
rag_payload = {"query": "vegetarian indian diet", "top_k": 3}
try:
    r_rag = requests.post(RAG_URL, json=rag_payload, timeout=5)
    if r_rag.status_code == 200:
        print("✔ RAG Success")
        context = " ".join([r.get("content", "") for r in r_rag.json().get("results", [])])
        print(f"   Context Snippet: {context[:50]}...")
    else:
        print(f"✘ RAG Failed: {r_rag.status_code} - {r_rag.text}")
        context = "No context"
except Exception as e:
    print(f"✘ RAG Error: {e}")
    context = "No context"

print("-" * 30)

# 2. TEST AGENT CALL (The one giving 422)
print(f"2. Testing Agent Call to {AGENT_URL}...")
# This matches the EXACT payload structure from our updated main.py
agent_payload = {
    "text": f"User: Veg Indian. Context: {context}. Output JSON."
}
print(f"   Sending Payload keys: {list(agent_payload.keys())}")

try:
    r_agent = requests.post(AGENT_URL, json=agent_payload, timeout=30)
    if r_agent.status_code == 200:
        print("✔ Agent Success")
        print(f"   Response Snippet: {str(r_agent.json())[:50]}...")
    else:
        print(f"✘ Agent Failed: {r_agent.status_code}")
        print(f"   Error Detail: {r_agent.text}")
except Exception as e:
    print(f"✘ Agent Error: {e}")
