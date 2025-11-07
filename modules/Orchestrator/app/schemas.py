from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class Profile(BaseModel):
    version: str = "v1"
    patient_id: str
    age: int
    sex: str
    bmi: float
    diagnoses_icd: List[str]
    activity: str
    culture: str
    locale: str
    budget: float

class DietRules(BaseModel):
    version: str = "v1"
    patient_id: str
    rules: Dict[str, Any]

class Gaps(BaseModel):
    version: str = "v1"
    patient_id: str
    gaps: List[Dict[str, Any]]

class Targets(BaseModel):
    version: str = "v1"
    patient_id: str
    kcal: int
    macros: Dict[str, float]
    micros: Dict[str, float] = {}

class Conflicts(BaseModel):
    version: str = "v1"
    patient_id: str
    items: List[Dict[str, Any]] = []

class Plan(BaseModel):
    version: str = "v1"
    patient_id: str
    plan: Dict[str, Any]
    shopping_list: List[str] = []
    trace: Dict[str, Any] = {}