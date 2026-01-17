import logging
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agent-a2")

app = FastAPI(title="Agent A2: Nutrient Gap Detective")

# --- KNOWLEDGE BASE: CONDITION -> NUTRIENT NEED ---
NUTRIENT_MAP = {
    "anemia": {
        "nutrient": "Iron + Vitamin C",
        "foods": ["Spinach", "Red Meat", "Lentils", "Citrus"]
    },
    "osteoporosis": {
        "nutrient": "Calcium + Vitamin D",
        "foods": ["Dairy", "Fortified Plant Milk", "Leafy Greens"]
    },
    "diabetes": {
        "nutrient": "Fiber + Chromium",
        "foods": ["Whole Grains", "Broccoli", "Nuts"]
    },
    "fatigue": {
        "nutrient": "Vitamin B12 + Magnesium",
        "foods": ["Eggs", "Fish", "Bananas", "Almonds"]
    },
    "ckd": { # Chronic Kidney Disease
        "nutrient": "Low Phosphorus protein",
        "foods": ["Egg whites", "Fish (limited)", "Berries"]
    }
}

class Profile(BaseModel):
    patient_id: str
    ailments: List[str] = []
    medical_record: Optional[Dict[str, Any]] = {}

class GapsResponse(BaseModel):
    patient_id: str
    gaps: Dict[str, str] # e.g. {"Iron": "Critical Need"}

@app.post("/gaps", response_model=GapsResponse)
async def detect_gaps(profile: Profile):
    logger.info(f"Analyzing Nutrient Gaps for: {profile.patient_id}")
    
    detected_gaps = {}
    
    # 1. Check Ailments
    for ailment in profile.ailments:
        for key, info in NUTRIENT_MAP.items():
            if key in ailment.lower():
                detected_gaps[info["nutrient"]] = f"Include: {', '.join(info['foods'])}"
                
    # 2. Check Labs (if provided in medical_record)
    # Example: {"Hemoglobin": "Low"} -> Add Iron
    if profile.medical_record:
        if profile.medical_record.get("hemoglobin") == "low":
            detected_gaps["Iron"] = "Lab indicates Anemia. Increase Iron."
        if profile.medical_record.get("vitamin_d") == "low":
            detected_gaps["Vitamin D"] = "Lab indicates deficiency. Sun exposure + Mushrooms/Fish."

    if not detected_gaps:
        detected_gaps["General"] = "Maintain balanced RDA profile."

    return GapsResponse(
        patient_id=profile.patient_id,
        gaps=detected_gaps
    )
