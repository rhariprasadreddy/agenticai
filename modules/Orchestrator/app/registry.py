# Minimal JSON schema registry (version tags only for now)
SCHEMAS = {
    "Profile.v1": {"required": ["patient_id", "age", "sex", "bmi"]},
    "DietRules.v1": {},
    "Gaps.v1": {},
    "Targets.v1": {},
    "Conflicts.v1": {},
    "Plan.v1": {},
}

def list_schemas():
    return list(SCHEMAS.keys())
