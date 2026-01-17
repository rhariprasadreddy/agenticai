import logging
import requests
import json
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("orchestrator")

app = FastAPI(title="MCP Orchestrator")

KAYTUS_IP = "192.168.2.57"

# Standard Service Map
SERVICES = {
    "A1": f"http://{KAYTUS_IP}:9001/diet-rules",
    "A3": f"http://{KAYTUS_IP}:9003/targets",
    "A5": f"http://{KAYTUS_IP}:9005/plan"
}

class MedicalRecord(BaseModel):
    condition: str
    current_meds: List[str]

class UserRequest(BaseModel):
    patient_id: str
    age: int
    gender: str
    location: str
    medical_record: MedicalRecord
    user_query: str

def validate_safety(plan_json, avoid_list):
    """
    Scans the JSON plan for any forbidden items.
    """
    warnings = []
    avoid_normalized = [x.lower() for x in avoid_list]
    
    # Recursive search for strings in the JSON
    def scan(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                scan(v)
        elif isinstance(obj, list):
            for item in obj:
                scan(item)
        elif isinstance(obj, str):
            text = obj.lower()
            for bad in avoid_normalized:
                # Logic: If strict avoid word (e.g. "potato") appears in ingredient ("potatoes")
                if bad in text: 
                    warnings.append(f"⚠️ SAFETY VIOLATION: '{bad}' detected in '{obj}'")
    
    scan(plan_json)
    return list(set(warnings))

@app.post("/run-pipeline")
async def run_pipeline(request: UserRequest):
    state = {"guidelines": [], "avoid": []}
    
    # --- STEP 1: CONSULT LEGISLATOR (A1) ---
    try:
        # Pass all ailments to A1
        payload_a1 = request.dict()
        # Ensure list format for A1
        payload_a1["ailments"] = [request.medical_record.condition] 
        if "Lipids" in request.user_query: payload_a1["ailments"].append("Cholesterol")
        
        r1 = requests.post(SERVICES["A1"], json=payload_a1, timeout=10)
        if r1.status_code == 200:
            data = r1.json()
            state["guidelines"] = data.get("guidelines", [])
            state["avoid"] = data.get("avoid_foods", [])
    except Exception as e:
        logger.error(f"A1 Error: {e}")

    # --- STEP 2: CONSULT PLANNER (A5) ---
    # We construct a prompt that explicitly forbids the 'avoid' items
    avoid_str = ", ".join(state["avoid"])
    
    payload_a5 = {
        "patient_id": request.patient_id,
        "medical_record": request.medical_record.dict(),
        "diet_rules": state["guidelines"],
        "clinical_guidelines": [f"STRICTLY EXCLUDE: {avoid_str}"], # Strong Instruction
        "nutritional_targets": {}, 
        "feedback": f"Location context: {request.location}"
    }
    
    plan_result = {}
    try:
        r5 = requests.post(SERVICES["A5"], json=payload_a5, timeout=120)
        if r5.status_code == 200:
            plan_result = r5.json()
        else:
            plan_result = {"meal_plan": "Error generating plan."}
    except Exception as e:
        plan_result = {"meal_plan": f"Connection Error: {e}"}

    # --- STEP 3: POLICE CHECK (Orchestrator) ---
    if "meal_plan" in plan_result and isinstance(plan_result["meal_plan"], dict):
        plan_result["warnings"] = validate_safety(plan_result["meal_plan"], state["avoid"])
    else:
        plan_result["warnings"] = []

    return plan_result