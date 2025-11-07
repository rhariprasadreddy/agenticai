import os, asyncio, httpx
from fastapi import HTTPException
from .schemas import Profile, DietRules, Gaps, Targets, Conflicts, Plan

A1_URL = os.getenv("A1_URL", "http://a1:9001")
A2_URL = os.getenv("A2_URL", "http://a2:9002")
A3_URL = os.getenv("A3_URL", "http://a3:9003")
A4_URL = os.getenv("A4_URL", "http://a4:9004")
A5_URL = os.getenv("A5_URL", "http://a5:9005")

TIMEOUT = httpx.Timeout(15.0, connect=5.0)
HEADERS = {"Content-Type": "application/json"}

async def call(url: str, payload: dict) -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.post(url, json=payload, headers=HEADERS)
        if r.status_code >= 400:
            raise HTTPException(status_code=r.status_code, detail=r.text)
        return r.json()

async def run_pipeline(profile: Profile) -> Plan:
    # A1 → diet rules
    a1 = await call(f"{A1_URL}/diet-rules", profile.model_dump())
    diet_rules = DietRules(**a1)

    # A2 → gaps
    a2 = await call(f"{A2_URL}/gaps", {"patient_id": profile.patient_id})
    gaps = Gaps(**a2)

    # A3 → targets
    a3 = await call(f"{A3_URL}/targets", {"patient_id": profile.patient_id})
    targets = Targets(**a3)

    # A4 → conflicts
    a4 = await call(f"{A4_URL}/conflicts", {"patient_id": profile.patient_id})
    conflicts = Conflicts(**a4)

    # A5 → plan
    a5_payload = {
        "patient_id": profile.patient_id,
        "diet_rules": diet_rules.model_dump(),
        "gaps": gaps.model_dump(),
        "targets": targets.model_dump(),
        "conflicts": conflicts.model_dump(),
    }
    a5 = await call(f"{A5_URL}/plan", a5_payload)
    plan = Plan(**a5)
    return plan
