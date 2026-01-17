from pydantic import BaseModel
from typing import List, Dict, Any, Optional

# --- INPUT MODEL ---
class Profile(BaseModel):
    patient_id: str
    age: Optional[int] = None
    gender: Optional[str] = None
    location: Optional[str] = None
    ailments: List[str] = []
    medical_record: Optional[Dict[str, Any]] = {} 
    preferences: Optional[str] = None
    # NEW: Capture the user's specific question/request
    query: Optional[str] = "" 

    class Config:
        extra = "allow"

# --- AGENT RESPONSE MODELS ---
class DietRules(BaseModel):
    patient_id: str = "unknown"
    consolidated_rules: List[str] = []
    sources: List[str] = []

class Gaps(BaseModel):
    patient_id: str = "unknown"
    gaps: Dict[str, Any] = {}

class Targets(BaseModel):
    patient_id: str = "unknown"
    targets: Dict[str, Any] = {}

class Conflicts(BaseModel):
    patient_id: str = "unknown"
    interactions: List[str] = []
    flags: Dict[str, str] = {}

class Plan(BaseModel):
    patient_id: str
    final_plan: str
    safety_notes: str