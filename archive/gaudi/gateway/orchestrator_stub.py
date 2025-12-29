# orchestrator_stub.py
from fastapi import FastAPI, HTTPException

app = FastAPI(title="MCP Orchestrator Stub")
plans = {}

@app.get("/health")
def health():
    return {"status": "ok", "service": "mcp-orchestrator"}

@app.post("/v1/route")
def route(payload: dict):
    case_id = payload.get("patient_id", "case-123")
    plans[case_id] = {"plan": "(stub) 7-day plan", "trace": {"steps": []}}
    return {"accepted": True, "case_id": case_id}

@app.get("/v1/cases/{case_id}/plan")
def get_plan(case_id: str):
    if case_id not in plans:
        raise HTTPException(status_code=404, detail="not found")
    return plans[case_id]