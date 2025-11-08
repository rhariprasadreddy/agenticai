from fastapi import FastAPI, Request
from .schemas import Profile, DietRules
from pathlib import Path
import yaml
from .rag import query_hints

app = FastAPI(title="A1 Condition Diet Agent", version="0.1.0")

RULES_DIR = Path(__file__).parent / "rules"
DIAB = yaml.safe_load((RULES_DIR / "diabetes.yaml").read_text())
COMMON = yaml.safe_load((RULES_DIR / "common_portions.yaml").read_text())

@app.get("/health")
def health():
    return {"status":"ok","agent":"A1","rulesets":["diabetes"]}

def _pick_rules(profile: Profile):
    # naive selector: if any ICD contains E11.* → diabetes rules
    icds = " ".join(profile.diagnoses_icd).lower()
    if "e11" in icds:
        return DIAB
    return None

@app.post("/diet-rules")
async def diet_rules(req: Request):
    data = await req.json()
    profile = Profile(**data)
    ruleset = _pick_rules(profile)
    if not ruleset:
        return {"version":"v1","patient_id":profile.patient_id,
                "rules":{"allow":[],"limit":[],"avoid":[],"portions":{},"notes":["No matching ruleset"]}}
    portions = ruleset.get("portions", {}).get("default", {}).copy()
    # culture overrides
    culture = (profile.culture or "").lower()
    ov = ruleset.get("portions", {}).get("culture_overrides", {}).get(culture, {})
    portions.update(ov)
    # inject rag hints
    hints = query_hints(["diabetes_gi","whole_grains","legumes","fruits","fats"])
    out = {
        "allow": ruleset.get("allow", []),
        "limit": ruleset.get("limit", []),
        "avoid": ruleset.get("avoid", []),
        "portions": portions,
        "notes": ruleset.get("notes", []) + hints
    }
    return DietRules(version="v1", patient_id=profile.patient_id, rules=out)
