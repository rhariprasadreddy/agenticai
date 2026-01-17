import requests
import os
import sys

# Smart Path Detection
POSSIBLE_PATHS = [
    os.path.expanduser("~/agenticai/data/processed_rag/diabetes_guidelines.txt"),
    "data/processed_rag/diabetes_guidelines.txt",
    "../data/processed_rag/diabetes_guidelines.txt",
    "/home/agenticai/agenticai/data/processed_rag/diabetes_guidelines.txt"
]

FILE_PATH = None
for p in POSSIBLE_PATHS:
    if os.path.exists(p):
        FILE_PATH = p
        break

API_URL = "http://localhost:9101/v1/diabetes/index"

def ingest():
    if not FILE_PATH:
        print(f"❌ Error: Could not find diabetes_guidelines.txt.")
        print(f"   Checked locations: {POSSIBLE_PATHS}")
        return

    print(f"🔹 Found data at: {FILE_PATH}")
    with open(FILE_PATH, "r", encoding="utf-8") as f:
        text = f.read()

    # Split into chunks (paragraphs)
    chunks = [c.strip() for c in text.split('\n\n') if c.strip()]
    print(f"🔹 Found {len(chunks)} paragraphs. Sending to RAG Brain...")

    # Prepare payload
    docs = []
    for i, chunk in enumerate(chunks):
        docs.append({
            "id": i,
            "title": "Guidelines (SG/India)",
            "text": chunk,
            "source": "HealthHub/ICMR"
        })

    # Send to RAG Service
    try:
        response = requests.post(API_URL, json={"docs": docs})
        if response.status_code == 200:
            print("✅ Success! Data ingested.")
        else:
            print(f"❌ Failed. Status: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    ingest()
