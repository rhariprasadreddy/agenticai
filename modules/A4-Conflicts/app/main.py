import logging
import requests
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict, Optional

# Logging Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agent-a4")

app = FastAPI(title="Agent A4: Conflict Detector (The Pharmacist)")

# --- CONFIGURATION ---
# In production, these should be env vars
# Use Docker Service Names (Not localhost, Not 192.168...)
# --- CONFIGURATION ---
# The IP of the SMGAILAB Server (Where KG containers run)
KG_HOST = "192.168.2.69" 

KG_DIABETES_URL = f"http://{KG_HOST}:9201/v1/diabetes/kg/check_foods"
KG_HYPERTENSION_URL = f"http://{KG_HOST}:9202/v1/hypertension/kg/check_foods"
KG_LIPIDS_URL = f"http://{KG_HOST}:9203/v1/lipids/kg/check_foods"
KG_KIDNEY_URL = f"http://{KG_HOST}:9204/v1/kidney/kg/check_foods"

# --- MODELS ---
class MedicalRecord(BaseModel):
    condition: str = "Unknown"
    current_meds: List[str] = []

class Profile(BaseModel):
    patient_id: str
    medical_record: MedicalRecord
    # NEW: We allow the orchestrator to send specific foods to check (e.g. from the user's wish)
    foods_to_check: Optional[List[str]] = []

class ConflictResponse(BaseModel):
    patient_id: str
    interactions: List[str]
    flags: Dict[str, str]

# --- HELPER: REAL GRAPH CHECK ---
def check_food_safety(condition: str, food_list: List[str]) -> List[str]:
    """
    Calls the Neo4j Microservices to check if foods are safe.
    """
    alerts = []

    # 1. Determine which Knowledge Graph to ask
    target_url = ""
    condition_lower = condition.lower()
    
    if "diabetes" in condition_lower:
        target_url = KG_DIABETES_URL
    elif "hyper" in condition_lower or "blood pressure" in condition_lower:
        target_url = KG_HYPERTENSION_URL
    elif "lipid" in condition_lower or "cholesterol" in condition_lower:
        target_url = KG_LIPIDS_URL
    elif "kidney" in condition_lower or "renal" in condition_lower or "ckd" in condition_lower:
        target_url = KG_KIDNEY_URL
    
    if not target_url:
        logger.warning(f"No specific KG service found for condition: {condition}")
        return []

    # 2. Call the Microservice
    try:
        # The KG service expects: {"foods": ["Cake", "Spinach"]}
        payload = {"foods": food_list}
        response = requests.post(target_url, json=payload, timeout=3.0)
        
        if response.status_code == 200:
            data = response.json()
            # Parse results from the KG
            for res in data.get("results", []):
                food_name = res.get("food", "Unknown")
                status = res.get("status", "UNKNOWN")
                reasons = res.get("reasons", [])
                
                if status == "RESTRICTED":
                    # We found a REAL conflict in the Graph!
                    reason_str = ", ".join(reasons)
                    alerts.append(f"⛔ KG ALERT: '{food_name}' is RESTRICTED for {condition}. Reasons: {reason_str}")
                elif status == "RECOMMENDED":
                    logger.info(f"KG Validation: {food_name} is Safe/Recommended.")
                    
    except Exception as e:
        logger.error(f"Failed to connect to Knowledge Graph: {str(e)}")
        # We don't crash the whole agent, just log the error
        alerts.append(f"⚠️ System Error: Could not verify food safety with Knowledge Graph.")

    return alerts

# --- ENDPOINT ---
@app.post("/conflicts", response_model=ConflictResponse)
async def check_conflicts(profile: Profile):
    logger.info(f"Checking conflicts for: {profile.patient_id}")
    
    found_interactions = []
    flags = {}
    
    # Normalize inputs
    meds = [m.lower() for m in profile.medical_record.current_meds]
    condition = profile.medical_record.condition
    
    # --- 1. LEGACY DRUG CHECKS (Keep existing logic as backup) ---
    # (Simple dictionary checks for drug-drug interactions)
    if "lisinopril" in meds and "potassium" in str(profile.foods_to_check).lower():
         found_interactions.append("MED ALERT: Lisinopril + High Potassium foods = Risk of Hyperkalemia.")
         flags["Lisinopril"] = "High"

    # --- 2. NEW: REAL KNOWLEDGE GRAPH CHECK ---
    # If the user (or Orchestrator) provided foods to check, ask Neo4j
    if profile.foods_to_check:
        logger.info(f"Querying Knowledge Graph for foods: {profile.foods_to_check}")
        kg_alerts = check_food_safety(condition, profile.foods_to_check)
        found_interactions.extend(kg_alerts)
        
        # Set flags if KG returned alerts
        if kg_alerts:
            flags["KG_Diet_Safety"] = "Critical"

    return ConflictResponse(
        patient_id=profile.patient_id,
        interactions=found_interactions,
        flags=flags
    )