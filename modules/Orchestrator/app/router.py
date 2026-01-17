import os
import httpx
import logging
from fastapi import HTTPException
from .schemas import Profile, DietRules, Gaps, Targets, Conflicts, Plan

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("orchestrator")

# --- CONFIGURATION ---
A1_URL = os.getenv("A1_URL", "http://a1:9001")
A2_URL = os.getenv("A2_URL", "http://a2:9002")
A3_URL = os.getenv("A3_URL", "http://a3:9003")
A4_URL = os.getenv("A4_URL", "http://a4:9004")
A5_URL = os.getenv("A5_URL", "http://a5:9005")

# FIX: Increased Timeout to 3 minutes (180s) for heavy inference loads
TIMEOUT = httpx.Timeout(180.0, connect=10.0) 
HEADERS = {"Content-Type": "application/json"}

# --- HELPER: ASYNC HTTP CALL ---
async def call_service(url: str, payload: dict) -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            logger.info(f"Calling Service: {url}")
            r = await client.post(url, json=payload, headers=HEADERS)
            r.raise_for_status()
            return r.json()
        except httpx.ReadTimeout:
            logger.error(f"Timeout waiting for {url}")
            raise HTTPException(status_code=504, detail=f"Service {url} took too long to respond.")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP Error calling {url}: {e.response.text}")
            raise HTTPException(status_code=e.response.status_code, detail=f"Service {url} failed: {e.response.text}")
        except Exception as e:
            logger.error(f"Connection Error calling {url}: {str(e)}")
            raise HTTPException(status_code=503, detail=f"Service {url} unavailable")

# --- ROUTING LOGIC (Unchanged) ---
async def route_user_message(user_message: str) -> dict:
    return {
        "reply": "Orchestrator is Online. Please send a structured JSON Profile to /run-pipeline.",
        "provider": "Orchestrator",
        "specialized": False
    }
# ... imports and config remain the same ...

async def run_pipeline(profile: Profile) -> Plan:
    logger.info(f"Starting Pipeline for Patient: {profile.patient_id}")

    # STEP 1: A1 (Diet Rules)
    logger.info("--- Step 1: Calling A1 (Diet Rules) ---")
    a1_resp = await call_service(f"{A1_URL}/diet-rules", profile.model_dump())
    diet_rules = DietRules(**a1_resp)
    logger.info(f"A1 Rules Derived: {len(diet_rules.consolidated_rules)} sections found.")

    # STEP 2: A2 (Gaps) - FIXED
    logger.info("--- Step 2: Calling A2 (Deficiencies) ---")
    # OLD: {"patient_id": profile.patient_id}
    # NEW: Send full profile so it sees meds/conditions
    a2_resp = await call_service(f"{A2_URL}/gaps", profile.model_dump())
    gaps = Gaps(**a2_resp)

    # STEP 3: A3 (Targets) - FIXED
    logger.info("--- Step 3: Calling A3 (Targets) ---")
    # OLD: {"patient_id": profile.patient_id}
    # NEW: Send full profile so it sees age/gender/creatinine
    a3_resp = await call_service(f"{A3_URL}/targets", profile.model_dump())
    targets = Targets(**a3_resp)

    # STEP 4: A4 (Conflicts) - FIXED
    logger.info("--- Step 4: Calling A4 (Conflicts) ---")
    # OLD: {"patient_id": profile.patient_id}
    # NEW: Send full profile so it sees meds/diet
    a4_resp = await call_service(f"{A4_URL}/conflicts", profile.model_dump())
    conflicts = Conflicts(**a4_resp)

    # STEP 5: A5 (Planner)
    logger.info("--- Step 5: Calling A5 (Synthesis) ---")
    a5_payload = {
        "patient_id": profile.patient_id,
        "diet_rules": diet_rules.model_dump(),
        "gaps": gaps.model_dump(),
        "targets": targets.model_dump(),
        "conflicts": conflicts.model_dump(),
    }
    a5_resp = await call_service(f"{A5_URL}/plan", a5_payload)
    plan = Plan(**a5_resp)

    return plan