import os
import requests
import logging
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("A1-Rules")

app = FastAPI(title="A1: Diet Rules (RAG Integrated)")

# CONFIG: Connect to your specific Knowledge Graph / RAG Agents
# These match the ports in your docker-compose
RAG_CONFIG = {
    "Diabetes": "http://192.168.2.69:9101/query",
    "Cholesterol": "http://192.168.2.69:9102/query",
    "Hypertension": "http://192.168.2.69:9103/query",
    "Kidney": "http://192.168.2.69:9104/query",
}

class PatientData(BaseModel):
    patient_id: str
    medical_record: Dict
    ailments: List[str]

def query_rag_agent(url, ailment):
    """
    Standardized Interface to query the Disease-Specific RAG Agents.
    """
    query_payload = {
        "text": f"What are the strict dietary restrictions and foods to avoid for {ailment}?",
        "top_k": 5
    }
    
    try:
        logger.info(f"🔌 Connecting to RAG Agent at {url}...")
        response = requests.post(url, json=query_payload, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            # ASSUMPTION: Your RAG Agent returns a dict with 'documents' or 'answer'
            # We treat the text returned by RAG as the source of truth.
            return data.get("answer") or data.get("response") or str(data)
    except Exception as e:
        logger.error(f"❌ Connection Failed to {url}: {e}")
    
    return None

@app.post("/diet-rules")
def get_rules(data: PatientData):
    rules = []
    avoid_foods = []

    # 1. Iterate through diagnosed ailments
    for ailment in data.ailments:
        rag_url = None
        
        # 2. Map Ailment to RAG Node
        if "Diabetes" in ailment: rag_url = RAG_CONFIG["Diabetes"]
        elif "Cholesterol" in ailment or "Lipids" in ailment: rag_url = RAG_CONFIG["Cholesterol"]
        elif "Hypertension" in ailment or "Blood Pressure" in ailment: rag_url = RAG_CONFIG["Hypertension"]
        elif "Kidney" in ailment or "CKD" in ailment: rag_url = RAG_CONFIG["Kidney"]

        # 3. Fetch from Knowledge Graph / RAG
        if rag_url:
            rag_insight = query_rag_agent(rag_url, ailment)
            if rag_insight:
                rules.append(f"GUIDELINE ({ailment}): {rag_insight[:200]}...") # Keep it concise
        
        # 4. HARD FALLBACKS (Crucial for Safety until RAG is perfect)
        # Even with RAG, we need a safety layer for critical rules if RAG is vague.
        if "Kidney" in ailment or "CKD" in ailment:
            avoid_foods.extend(["Spinach", "Potatoes", "Tomatoes", "Bananas", "Red Meat", "Dairy"])
            rules.append("CRITICAL: Low Potassium, Low Phosphorus.")
        
        if "Diabetes" in ailment:
            avoid_foods.extend(["Sugar", "White Rice", "Refined Flour", "Fruit Juice", "Sweets"])
            rules.append("CRITICAL: Low Glycemic Index.")

        if "Hypertension" in ailment:
            avoid_foods.extend(["Salt", "Pickles", "Canned Soup", "Processed Meat", "Soy Sauce"])
    
    # Deduplicate
    return {
        "guidelines": list(set(rules)),
        "avoid_foods": list(set(avoid_foods))
    }