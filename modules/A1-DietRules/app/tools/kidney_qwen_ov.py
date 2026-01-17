import os
import requests
import logging
import json

# Setup Logger
logger = logging.getLogger(__name__)

# CONFIG
# Default to empty string if not set, handled in logic
RAG_URL = os.getenv("KIDNEY_RAG_URL", "http://192.168.2.69:9104")
OV_URL = os.getenv("KIDNEY_OV_URL", "http://192.168.2.69:8080")

def call_kidney_qwen(prompt: str) -> str:
    """
    Safe Kidney Agent: Tries RAG first, falls back to pure LLM if RAG fails.
    """
    evidence_text = ""
    
    # 1. Try RAG (Vector Search)
    try:
        # Extract a search term from the prompt (simple heuristic)
        # We assume the prompt contains "Patient Profile..."
        rag_payload = {"query": "Kidney CKD diet restrictions potassium phosphorus", "top_k": 3}
        
        logger.info(f"Connecting to Kidney RAG at {RAG_URL}...")
        resp = requests.post(f"{RAG_URL}/v1/kidney/search", json=rag_payload, timeout=5)
        
        if resp.status_code == 200:
            hits = resp.json().get("hits", [])
            if hits:
                evidence_text = "\nEVIDENCE FROM GUIDELINES:\n" + "\n".join([f"- {h['text'][:300]}..." for h in hits])
    except Exception as e:
        logger.warning(f"Kidney RAG failed (proceeding without it): {e}")
        evidence_text = "\n(Note: RAG Guidelines unavailable, using general medical knowledge.)"

    # 2. Call Qwen (Inference)
    full_prompt = (
        f"You are a Renal Dietitian. {prompt}\n"
        f"Strictly limit Potassium, Phosphorus, and Sodium.\n"
        f"{evidence_text}\n"
        f"Provide a 1-day meal plan with 'Breakfast', 'Lunch', 'Dinner' sections."
    )

    try:
        payload = {"prompt": full_prompt, "max_new_tokens": 400, "temperature": 0.3}
        logger.info(f"Sending prompt to Qwen at {OV_URL}...")
        r = requests.post(f"{OV_URL}/generate", json=payload, timeout=60)
        r.raise_for_status()
        
        # Extract text (Flexible parsing for different API shapes)
        data = r.json()
        output = data.get("generated_text", "") or data.get("text", "") or data.get("reply", "") or str(data)
        
        # Clean up tags if present
        return output.replace("<|im_start|>", "").replace("<|im_end|>", "")

    except Exception as e:
        logger.error(f"Kidney Qwen Inference failed: {e}")
        return "Error: Unable to generate Kidney advice due to inference server timeout."
