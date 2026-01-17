import requests
import json
import re
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, Any, List

app = FastAPI(title="A5: Planner")

LLM_URL = "http://192.168.2.69:8080/generate"

class PlanRequest(BaseModel):
    patient_id: str
    medical_record: Dict
    diet_rules: List[str] = [] 
    clinical_guidelines: List[str] = []
    nutritional_targets: Any = {}
    feedback: str = ""

def clean_json(text):
    text = text.replace("```json", "").replace("```", "").strip()
    match = re.search(r"(\{.*\})", text, re.DOTALL)
    return match.group(1) if match else text

@app.post("/plan")
def generate_plan(req: PlanRequest):
    # Constructing a "Negative Constraint" Prompt
    restrictions = " ".join(req.clinical_guidelines)
    location = req.feedback
    
    prompt = f"""<|im_start|>system
You are a Clinical Dietitian for a patient in {location}.
Your PRIMARY directive is Clinical Safety.

STRICT RESTRICTIONS:
{restrictions}

Task: Create a 1-day meal plan.
1. If a food is in the RESTRICTIONS list, you MUST NOT include it.
2. Substitute dangerous ingredients (e.g., Use 'Cauliflower Rice' instead of 'White Rice' for Diabetes).
3. Output strictly valid JSON.

Format:
{{
  "meal_plan": {{
    "breakfast": {{ "dish": "...", "ingredients": ["..."], "portion": "...", "benefit": "..." }},
    "lunch": {{ ... }},
    "dinner": {{ ... }}
  }}
}}
<|im_end|>
<|im_start|>user
Condition: {req.medical_record.get('condition')}
Meds: {req.medical_record.get('current_meds')}
Generate Safe Plan.
<|im_end|>
<|im_start|>assistant
"""
    
    payload = {"prompt": prompt, "max_tokens": 3000, "temperature": 0.1, "stop": ["<|im_end|>"]}
    
    try:
        r = requests.post(LLM_URL, json=payload, timeout=90)
        if r.status_code == 200:
            raw = r.json().get("generated_text", [""])[0] if "generated_text" in r.json() else r.json().get("reply", "")
            try:
                return json.loads(clean_json(raw))
            except:
                return {"meal_plan": "Error parsing JSON."}
    except Exception as e:
        return {"meal_plan": f"Error: {e}"}