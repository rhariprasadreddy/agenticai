from pydantic import BaseModel, Field, validator
from typing import List, Optional

# schema.Profile.v1
class ProfileV1(BaseModel):
    version: str = Field("v1", const=True)
    patient_id: str
    age: int = Field(..., ge=0, le=120)
    sex: str = Field(..., regex="^(male|female|other)$")
    bmi: Optional[float] = Field(None, ge=5, le=80)
    activity: Optional[str] = Field(None, regex="^(sedentary|light|moderate|active|athlete)$")
    culture: Optional[str] = None
    locale: Optional[str] = None          # e.g. "SG", "IN-TN"
    budget: Optional[float] = Field(None, ge=0)
    diagnoses_icd: List[str] = Field(default_factory=list)
    medications: List[str] = Field(default_factory=list)
    allergies: List[str] = Field(default_factory=list)
    labs: Optional[dict] = None           # {"hbA1c": 7.1, "creatinine": 1.8, ...}
    diet_logs: Optional[List[dict]] = None

    @validator("diagnoses_icd", each_item=True)
    def icd_format(cls, v):
        if not v or len(v) < 3:
            raise ValueError("Invalid ICD code")
        return v

# Stubs for downstream contracts (for headers / routing only)
class DietRulesV1(BaseModel):
    version: str = Field("v1", const=True)
    rules: List[dict]

class GapsV1(BaseModel):
    version: str = Field("v1", const=True)
    nutrient_gaps: List[dict]

class TargetsV1(BaseModel):
    version: str = Field("v1", const=True)
    targets: dict

class ConflictsV1(BaseModel):
    version: str = Field("v1", const=True)
    conflicts: List[dict]

class PlanV1(BaseModel):
    version: str = Field("v1", const=True)
    weekly_plan: List[dict]    # 7×day×meals
    shopping_list: List[dict]
    trace: dict