import logging
import requests
import json
import re
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Union

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

# MAP UI NAMES TO INTERNAL KEYS (Crucial for routing)
CONDITION_MAP = {
    "High Cholesterol": "Lipids",
    "Cholesterol": "Lipids",
    "Chronic Kidney Disease": "Kidney",
    "Kidney Failure": "Kidney",
    "Renal": "Kidney",
    "High Blood Pressure": "Hypertension",
    "Hypertension": "Hypertension",
    "Type 2 Diabetes": "Diabetes",
    "Diabetes Type 2": "Diabetes",
    "Diabetes": "Diabetes"
}

class MedicalRecord(BaseModel):
    condition: Union[str, List[str]] # Handles both single string and list inputs
    current_meds: List[str]

class UserRequest(BaseModel):
    patient_id: str
    age: int
    gender: str
    location: str
    medical_record: MedicalRecord
    user_query: str

# --- ROBUST PARSING (Fixes UI Crashes) ---
def clean_json_text(text: str) -> str:
    # Remove Markdown
    match = re.search(r"```(?:json)?(.*?)```", text, re.DOTALL)
    if match: text = match.group(1)
    
    # Remove Echoed Prompt (Heuristic: Find the first outer brace)
    first_brace = text.find("{")
    if first_brace != -1: text = text[first_brace:]
    
    return text.strip()

def repair_agent_output(raw_output: Any) -> Dict:
    if isinstance(raw_output, dict): return raw_output
    text = str(raw_output)
    clean_text = clean_json_text(text)
    
    # Try parsing cleaned text
    try: return json.loads(clean_text)
    except: pass
    
    # Try hunting for JSON object
    try:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end != -1: return json.loads(text[start:end])
    except: pass

    # UI-SAFE FALLBACK: Returns LISTS, not strings.
    logger.warning("JSON Parsing Failed. Returning Structured Fallback.")
    return {
        "meal_plan": {
            "breakfast": ["See detailed guidelines below"],
            "lunch": ["See detailed guidelines below"],
            "dinner": ["See detailed guidelines below"],
            "guidelines": text[:1500] 
        }, 
        "warnings": ["⚠️ Parsing Error: Showing raw model output."]
    }

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

# --- MAIN AGENTIC PIPELINE ---
@app.post("/run-pipeline")
async def run_pipeline(request: UserRequest):
    state = {"guidelines": [], "avoid": []}
    
    # 1. NORMALIZE CONDITIONS
    # Handle Input Variations (String vs List)
    raw_input = request.medical_record.condition
    if isinstance(raw_input, str):
        raw_list = [c.strip() for c in raw_input.split(",")]
    else:
        raw_list = raw_input

    # Map to internal keys
    active_conditions = []
    for item in raw_list:
        mapped = CONDITION_MAP.get(item, item)
        if mapped in SERVICES:
            active_conditions.append(mapped)
            
    # Remove duplicates
    active_conditions = list(set(active_conditions))

    if not active_conditions:
        return {"error": f"No specialist found for {raw_input}"}

    logger.info(f"Active Conditions: {active_conditions}")

    # 2. CALL AGENT A1 (The Rule Engine) - PURE DYNAMIC LOGIC
    # We send ALL conditions to A1. A1 returns the merged "Avoid List".
    try:
        payload_a1 = request.dict()
        payload_a1["ailments"] = active_conditions # Send ["Kidney", "Diabetes"]
        
        logger.info(f"Calling A1 Rules Agent with: {active_conditions}")
        r1 = requests.post(A1_SERVICE, json=payload_a1, timeout=5)
        
        if r1.status_code == 200:
            state["avoid"] = r1.json().get("avoid_foods", [])
            logger.info(f"A1 Returned Avoid List: {state['avoid']}")
        else:
            logger.error(f"A1 Failed: {r1.status_code}")
    except Exception as e:
        logger.error(f"A1 Connection Error: {e}")

    # 3. SELECT PRIMARY SPECIALIST (Hierarchy of Criticality)
    # Logic: Kidney is harder to manage than Diabetes, which is harder than Lipids.
    if "Kidney" in active_conditions:
        primary_condition = "Kidney"
    elif "Diabetes" in active_conditions:
        primary_condition = "Diabetes"
    elif "Hypertension" in active_conditions:
        primary_condition = "Hypertension"
    else:
        primary_condition = active_conditions[0]

    service_group = SERVICES[primary_condition]
    
    # 4. RAG & KG (Context Retrieval)
    rag_context = ""
    try:
        # Query RAG for the PRIMARY condition
        r_rag = requests.post(service_group["rag"], json={"query": request.user_query, "top_k": 3}, timeout=5)
        if r_rag.status_code == 200:
            results = r_rag.json().get("results", [])
            rag_context = " ".join([r.get("content", "") for r in results])
    except Exception as e:
        logger.warning(f"RAG Error: {e}")

    # 5. SPECIALIST AGENT EXECUTION
    attempts = 0
    max_retries = 2
    avoid_str = ", ".join(state["avoid"])
    
    # The Prompt combines: User Query + Medical Context + Strict Avoid List
    strong_instruction = (
        f"Role: Clinical Dietitian. Task: Create {primary_condition} meal plan.\n"
        f"Patient Conditions: {', '.join(active_conditions)}\n"
        f"User Query: {request.user_query}\n"
        f"Context: {rag_context[:600]}\n"
        f"CRITICAL AVOID LIST: {avoid_str}\n"
        f"Format: Valid JSON only. Keys: breakfast (list), lunch (list), dinner (list). No markdown."
    )
    
    final_result = {}

    while attempts < max_retries:
        logger.info(f"Calling Specialist {primary_condition} (Attempt {attempts+1})...")
        payload = {"text": strong_instruction}
        
        try:
            r_agent = requests.post(service_group["agent"], json=payload, timeout=90)
            
            if r_agent.status_code == 200:
                raw_json = r_agent.json()
                raw_text = raw_json.get("plan", raw_json)
                plan_result = repair_agent_output(raw_text)
                
                # Normalize structure
                if "meal_plan" not in plan_result:
                     plan_result = {"meal_plan": plan_result, "warnings": []}
            else:
                plan_result = {"meal_plan": {}, "error": f"Agent Error {r_agent.status_code}"}
        except Exception as e:
            plan_result = {"meal_plan": {}, "error": str(e)}

        # 6. SAFETY CHECK (The "Planner" Logic)
        # We validate the Specialist's output against the A1 Rules.
        warnings = []
        if "meal_plan" in plan_result and isinstance(plan_result["meal_plan"], dict):
            warnings = validate_safety(plan_result["meal_plan"], state["avoid"])
        
        plan_result["warnings"] = warnings

        if not warnings:
            return plan_result
        else:
            logger.warning(f"Safety Violation: {warnings}. Retrying...")
            strong_instruction += f" Remove {warnings}. Re-generate."
            attempts += 1
            final_result = plan_result

    return final_result