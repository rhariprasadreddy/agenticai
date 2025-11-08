from pydantic import BaseModel
from typing import List, Dict, Any

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
    rules: Dict[str, Any]   # {allow:[], limit:[], avoid:[], portions:{}, notes:[]}