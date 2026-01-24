import logging
import requests
import json
import re
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Union, Optional

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("orchestrator")

app = FastAPI(title="Condition-Aware Diet Orchestrator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CONFIGURATION ---
KAYTUS_IP = "192.168.2.57"
XEON_IP = "192.168.2.69"

A1_SERVICE = f"http://{KAYTUS_IP}:9001/diet-rules"

SERVICES = {
    "Diabetes": {
        "agent": f"http://{XEON_IP}:8080/v1/diabetes/plan",
        "rag":   f"http://{XEON_IP}:9101/v1/diabetes/search",
        "kg":    f"http://{XEON_IP}:9201/v1/diabetes/graph"
    },
    "Hypertension": {
        "agent": f"http://{XEON_IP}:8082/v1/hypertension/plan",
        "rag":   f"http://{XEON_IP}:9103/v1/hypertension/search",
        "kg":    f"http://{XEON_IP}:9202/v1/hypertension/graph"
    },
    "Lipids": {
        "agent": f"http://{XEON_IP}:9006/v1/lipids/plan",
        "rag":   f"http://{XEON_IP}:9102/v1/lipids/search",
        "kg":    f"http://{XEON_IP}:9203/v1/lipids/graph"
    },
    "Kidney": {
        "agent": f"http://{XEON_IP}:9008/v1/kidney/plan",
        "rag":   f"http://{XEON_IP}:9104/v1/kidney/search",
        "kg":    f"http://{XEON_IP}:9204/v1/kidney/graph"
    }
}

CONDITION_MAP = {
    "High Cholesterol": "Lipids", "Cholesterol": "Lipids",
    "Chronic Kidney Disease": "Kidney", "Renal": "Kidney", "Kidney Failure": "Kidney",
    "High Blood Pressure": "Hypertension", "Hypertension": "Hypertension",
    "Type 2 Diabetes": "Diabetes", "Diabetes": "Diabetes", "Diabetes Type 2": "Diabetes"
}

class MedicalRecord(BaseModel):
    condition: Union[str, List[str]]
    current_meds: List[str]

class UserRequest(BaseModel):
    patient_id: str
    age: int
    gender: str
    location: str
    medical_record: MedicalRecord
    user_query: str
    # ABLATION FLAGS (Default to True for normal operation)
    enable_rag: Optional[bool] = True
    enable_kg: Optional[bool] = True

# --- PARSING ---
def clean_json_text(text: str) -> str:
    match = re.search(r"```(?:json)?(.*?)```", text, re.DOTALL)
    if match: text = match.group(1)
    first_brace = text.find("{")
    if first_brace != -1: text = text[first_brace:]
    return text.strip()

def repair_agent_output(raw_output: Any) -> Dict:
    if isinstance(raw_output, dict): return raw_output
    text = str(raw_output)
    clean_text = clean_json_text(text)
    try: return json.loads(clean_text)
    except: pass
    try:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end != -1: return json.loads(text[start:end])
    except: pass
    return {"meal_plan": {"guidelines": text[:1500]}, "warnings": ["⚠️ Parsing Error"]}

def validate_safety(plan_json, avoid_list):
    warnings = []
    avoid_normalized = [x.lower() for x in avoid_list]
    def scan(obj):
        if isinstance(obj, dict):
            for v in obj.values(): scan(v)
        elif isinstance(obj, list):
            for item in obj: scan(item)
        elif isinstance(obj, str):
            text = obj.lower()
            for bad in avoid_normalized:
                if bad in text: warnings.append(f"⚠️ SAFETY VIOLATION: '{bad}' detected.")
    scan(plan_json)
    return list(set(warnings))

@app.post("/run-pipeline")
async def run_pipeline(request: UserRequest):
    state = {"guidelines": [], "avoid": []}
    
    # 1. NORMALIZE
    raw_input = request.medical_record.condition
    if isinstance(raw_input, str): raw_list = [c.strip() for c in raw_input.split(",")]
    else: raw_list = raw_input
    
    active_conditions = []
    for item in raw_list:
        mapped = CONDITION_MAP.get(item, item)
        if mapped in SERVICES: active_conditions.append(mapped)
    
    if not active_conditions: return {"error": "No specialist found"}
    
    # 2. RULE AGENT (A1) - Always Active for Safety
    combined_avoid = set()
    for cond in active_conditions:
        try:
            payload_a1 = request.dict(); payload_a1["ailments"] = [cond]
            r1 = requests.post(A1_SERVICE, json=payload_a1, timeout=5)
            if r1.status_code == 200: combined_avoid.update(r1.json().get("avoid_foods", []))
        except: pass
    state["avoid"] = list(combined_avoid)
    avoid_str = ", ".join(state["avoid"])

    # Select Primary Specialist
    primary_condition = active_conditions[0]
    if "Kidney" in active_conditions: primary_condition = "Kidney"
    elif "Diabetes" in active_conditions: primary_condition = "Diabetes"
    
    service_group = SERVICES[primary_condition]

    # 3. RAG LAYER (Conditional)
    rag_context = ""
    if request.enable_rag:
        try:
            r_rag = requests.post(service_group["rag"], json={"query": request.user_query, "top_k": 3}, timeout=5)
            if r_rag.status_code == 200:
                results = r_rag.json().get("results", [])
                rag_context = " ".join([r.get("content", "") for r in results])
        except: pass
    else:
        rag_context = "No medical guidelines available."

    # 4. KG LAYER (Conditional - Placeholder logic if KG service exists)
    kg_context = ""
    if request.enable_kg and "kg" in service_group:
        # Placeholder for actual KG call if you have it running
        kg_context = "" 
    else:
        kg_context = "No knowledge graph facts available."

    # 5. AGENT EXECUTION
    attempts = 0
    max_retries = 2
    
    strong_instruction = (
        f"Role: Clinical Dietitian. Task: Create {primary_condition} meal plan.\n"
        f"Conditions: {', '.join(active_conditions)}\n"
        f"Context: {rag_context[:600]}\n"
        f"KG Facts: {kg_context}\n"
        f"Strict Avoid: {avoid_str}\n"
        f"Format: Valid JSON keys: breakfast(list), lunch(list), dinner(list)."
    )
    
    final_result = {}
    while attempts < max_retries:
        payload = {"text": strong_instruction}
        try:
            r_agent = requests.post(service_group["agent"], json=payload, timeout=90)
            if r_agent.status_code == 200:
                raw_json = r_agent.json()
                raw_text = raw_json.get("plan", raw_json)
                plan_result = repair_agent_output(raw_text)
                if "meal_plan" not in plan_result: plan_result = {"meal_plan": plan_result, "warnings": []}
            else:
                plan_result = {"meal_plan": {}, "error": "Agent Failed"}
        except Exception as e:
            plan_result = {"meal_plan": {}, "error": str(e)}

        warnings = []
        if "meal_plan" in plan_result and isinstance(plan_result["meal_plan"], dict):
            warnings = validate_safety(plan_result["meal_plan"], state["avoid"])
        plan_result["warnings"] = warnings

        if not warnings: return plan_result
        else:
            strong_instruction += f" Remove {warnings}. Retry."
            attempts += 1
            final_result = plan_result

    return final_result