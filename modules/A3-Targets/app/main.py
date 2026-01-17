import logging
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, List, Any, Optional

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agent-a3")

app = FastAPI(title="Agent A3: DRI & Target Calculator")

# --- MODELS ---
class Profile(BaseModel):
    patient_id: str
    age: int
    gender: str
    location: str
    ailments: List[str]
    # We need weight/height for accurate DRI, but we'll use defaults if missing
    weight_kg: Optional[float] = 70.0
    height_cm: Optional[float] = 170.0
    activity_level: Optional[str] = "Sedentary"

class TargetsResponse(BaseModel):
    patient_id: str
    calories: int
    protein: Dict[str, float] # min/max
    micronutrients: List[str] # Key nutrients to focus on
    fluid_limit: str

# --- CALCULATOR LOGIC ---
def calculate_bmr(weight: float, height: float, age: int, gender: str) -> int:
    """Mifflin-St Jeor Equation"""
    # s = +5 for males, -161 for females
    s = 5 if gender.lower() in ["male", "m"] else -161
    bmr = (10 * weight) + (6.25 * height) - (5 * age) + s
    return int(bmr)

def get_activity_multiplier(level: str) -> float:
    mapping = {
        "sedentary": 1.2,
        "light": 1.375,
        "moderate": 1.55,
        "active": 1.725
    }
    return mapping.get(level.lower(), 1.2)

def get_protein_needs(weight: float, ailments: List[str]) -> Dict[str, float]:
    """Adjusts protein based on kidney health."""
    # Default: 0.8g - 1.0g per kg
    min_p = 0.8
    max_p = 1.0
    
    ailments_lower = [a.lower() for a in ailments]
    
    # CKD Logic (Non-dialysis CKD usually requires PROTEIN RESTRICTION)
    if any("kidney" in a or "ckd" in a for a in ailments_lower):
        min_p = 0.6
        max_p = 0.8
        logger.info("Adjusting Protein DOWN for Kidney Disease")
        
    return {"min_g": round(min_p * weight, 1), "max_g": round(max_p * weight, 1)}

def get_micronutrient_priorities(age: int, gender: str, ailments: List[str]) -> List[str]:
    """DRI Logic for key vitamins/minerals."""
    needs = []
    
    # General Age/Gender DRI
    if age > 50:
        needs.append("Calcium (1200mg) - Bone Health")
        needs.append("Vitamin D (800IU) - Absorption")
        
    if gender.lower() in ["female", "f"] and age < 50:
        needs.append("Iron (18mg) - Blood Health")
        
    # Disease Specific DRI
    ailments_lower = [a.lower() for a in ailments]
    
    if any("hypertension" in a or "bp" in a for a in ailments_lower):
        needs.append("Potassium (Target: 3500mg unless CKD)")
        needs.append("Magnesium (Heart Rhythm)")
        
    if any("diabetes" in a for a in ailments_lower):
        needs.append("Fiber (Target: >30g) - Blood Sugar Control")
        needs.append("Chromium - Insulin Sensitivity")
        
    return needs

# --- API ENDPOINT ---
@app.post("/targets", response_model=TargetsResponse)
async def calculate_targets(profile: Profile):
    logger.info(f"Calculating DRI for: {profile.patient_id}")
    
    # 1. Calories (BMR * Activity)
    bmr = calculate_bmr(profile.weight_kg, profile.height_cm, profile.age, profile.gender)
    tdee = int(bmr * get_activity_multiplier(profile.activity_level))
    
    # 2. Protein (Disease Adjusted)
    protein = get_protein_needs(profile.weight_kg, profile.ailments)
    
    # 3. Micronutrients
    micros = get_micronutrient_priorities(profile.age, profile.gender, profile.ailments)
    
    # 4. Fluid Logic (Simple check for Heart/Kidney)
    fluid = "2.5 - 3.0 Liters"
    if any(x in str(profile.ailments).lower() for x in ["kidney", "heart failure", "edema"]):
        fluid = "RESTRICTED: 1.5 - 2.0 Liters (Consult Nephrologist)"

    return TargetsResponse(
        patient_id=profile.patient_id,
        calories=tdee,
        protein=protein,
        micronutrients=micros,
        fluid_limit=fluid
    )
