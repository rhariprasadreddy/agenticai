from fastapi import FastAPI, HTTPException
from typing import Dict
from .schemas import Profile, Plan
from .registry import list_schemas
from .router import run_pipeline

app = FastAPI(title="MCP Orchestrator", version="0.1.0")

# Simple in-memory store (OK for dev/tests)
PLANS: Dict[str, Plan] = {}

@app.get("/health")
def health():
    return {"status": "ok", "service": "mcp-orchestrator", "schemas": list_schemas()}

@app.post("/v1/route")
async def route_case(profile: Profile):
    plan = await run_pipeline(profile)
    PLANS[profile.patient_id] = plan
    return {"accepted": True, "case_id": profile.patient_id}

@app.get("/v1/cases/{case_id}/plan")
def get_plan(case_id: str):
    if case_id not in PLANS:
        raise HTTPException(status_code=404, detail="not found")
    return PLANS[case_id]
