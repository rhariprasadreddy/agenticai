from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
import httpx, logging

from pydantic import BaseModel

from .schemas import ProfileV1
from .security import require_api_key
from .config import ORCH_URL
from .utils import mask_phi

app = FastAPI(title="MCP Gateway", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

log = logging.getLogger("uvicorn")
log.setLevel(logging.INFO)


# ---------- Chat models ----------
class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
    provider: str
    specialized: bool


@app.get("/health")
async def health():
    return {"status": "ok", "service": "mcp-gateway"}


# ---------- NEW: /chat passthrough to Orchestrator ----------
@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, _api=Depends(require_api_key)):
    """
    Gateway -> Orchestrator /chat passthrough.
    """
    url = f"{ORCH_URL}/chat"
    try:
        timeout = httpx.Timeout(60.0, connect=5.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, json=req.dict())
        resp.raise_for_status()
    except httpx.RequestError as e:
        log.error(f"Orchestrator /chat unreachable: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Orchestrator unreachable",
        )

    data = resp.json()
    return ChatResponse(**data)


# ---------- Existing profile-based pipeline ----------
@app.post("/v1/cases", status_code=202)
async def submit_case(profile: ProfileV1, _api=Depends(require_api_key)):
    # Validation already enforced by Pydantic schema.Profile.v1
    masked = mask_phi(profile.dict())
    log.info(f"Received case: {masked}")

    url = f"{ORCH_URL}/v1/route"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json=profile.dict())
        if resp.status_code >= 400:
            log.error(f"Orchestrator error: {resp.text}")
            raise HTTPException(status_code=502, detail="Orchestrator failed")
    except httpx.RequestError as e:
        log.error(f"Orchestrator unreachable: {e}")
        raise HTTPException(status_code=502, detail="Orchestrator unreachable")

    return {"status": "accepted", "schema": "Profile.v1"}


@app.get("/v1/cases/{case_id}/plan")
async def get_plan(case_id: str, _api=Depends(require_api_key)):
    url = f"{ORCH_URL}/v1/cases/{case_id}/plan"
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url)
    if r.status_code == 404:
        raise HTTPException(status_code=404, detail="Plan not found")
    return r.json()

