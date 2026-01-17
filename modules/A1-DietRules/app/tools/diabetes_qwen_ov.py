#!/usr/bin/env python3
"""
app/tools/diabetes_qwen_ov.py
Diabetes specialist agent - Fixed Intent Detection & Universal Key Patch
"""
import os
import re
import json
import logging
import requests
from typing import Optional, List, Dict, Any
from .diabetes_kg import query_diabetes_kg

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

DIAB_OV_URL = os.getenv("DIAB_OV_URL", "http://192.168.2.69:8080")
DIAB_RAG_URL = os.getenv("DIAB_RAG_URL", "http://192.168.2.69:9101")
DIAB_HTTP_TIMEOUT = float(os.getenv("DIAB_HTTP_TIMEOUT", "30"))
DIAB_MAX_NEW_TOKENS = int(os.getenv("DIAB_MAX_NEW_TOKENS", "400"))
DIAB_RAG_TOPK = int(os.getenv("DIAB_RAG_TOPK", "3"))

# -------------------------------------------------------------------
# 1. INTENT DETECTOR (Restored!)
# -------------------------------------------------------------------
_DIAB_PAT = re.compile(
    r"\b(diabet|t2dm|type\s*2|type\s*ii|hba1c|glucose|blood sugar|insulin|"
    r"metformin|glycemic|low\s*gi)\b",
    flags=re.IGNORECASE,
)

def is_diabetes_query(text: Optional[str]) -> bool:
    if not text:
        return False
    return bool(_DIAB_PAT.search(text))

# -------------------------------------------------------------------
# 2. HELPER FUNCTIONS
# -------------------------------------------------------------------
_SECTION_ORDER = ["Breakfast", "Mid-morning snack", "Lunch", "Evening snack", "Dinner", "General Guidelines"]
_LEAK_MARKERS = ["you are a helpful", "system prompt", "generate a", "strict rules", "evidence", "rag evidence"]

def _strip_prompt_leaks(text: str) -> str:
    if not text: return ""
    cleaned = []
    for ln in text.splitlines():
        low = ln.strip().lower()
        if not cleaned and not low: continue
        if low.startswith(("system:", "user:", "assistant:")): continue
        if any(m in low for m in _LEAK_MARKERS): continue
        cleaned.append(ln)
    return "\n".join(cleaned).strip()

def _parse_sections(text: str) -> Dict[str, str]:
    out = {k.lower(): "" for k in _SECTION_ORDER}
    if not text: return out
    s = _strip_prompt_leaks(text)
    s = re.sub(r"(?im)^#+\s*", "", s).strip()
    parts = []
    cur_name = None
    cur_buf = []
    for ln in s.splitlines():
        t = ln.strip()
        m = re.match(r"(?im)^(breakfast|mid-morning snack|mid morning snack|lunch|evening snack|dinner|general guidelines)\s*:\s*$", t)
        if m:
            if cur_name: parts.append((cur_name, "\n".join(cur_buf).strip()))
            cur_name = m.group(1).lower().replace("mid morning", "mid-morning")
            cur_buf = []
        else:
            cur_buf.append(ln)
    if cur_name: parts.append((cur_name, "\n".join(cur_buf).strip()))
    for name, body in parts:
        if name in out: out[name] = body.strip()
    return out

def _pick_bullets(block: str, max_items: int = 2) -> List[str]:
    if not block: return []
    lines = []
    for ln in block.splitlines():
        s = ln.strip()
        if not s: continue
        if s.startswith(("-", "•", "*")):
            s = s.lstrip("*•-").replace("**", "").strip()
            s = re.sub(r"(?i)^\s*option\s*\d+\s*:\s*", "", s).strip()
            if s: lines.append("- " + s)
            if len(lines) >= max_items: break
    if not lines: 
        for ln in block.splitlines():
            s = ln.strip()
            if not s: continue
            s = re.sub(r"(?i)^\s*option\s*\d+\s*:\s*", "", s).strip()
            if s: lines.append("- " + s)
            if len(lines) >= max_items: break
    return lines[:max_items]

def _deopt(s: str) -> str:
    s = s.strip()
    s = re.sub(r"^\-\s*", "", s)
    s = re.sub(r"(?i)^\s*option\s*\d+\s*:\s*", "", s).strip()
    return s

def _ensure_two(opts: List[str], fallback_a: str, fallback_b: str) -> List[str]:
    out = opts[:2]
    if len(out) < 1: out.append("- " + fallback_a)
    if len(out) < 2: out.append("- " + fallback_b)
    return out[:2]

def _normalize_to_standard_format(raw: str) -> str:
    logger.info(f"[DIAB-RAW-CONTENT] {raw[:500]}...") 
    
    raw = _strip_prompt_leaks(raw)
    sec = _parse_sections(raw)
    
    b = _ensure_two(_pick_bullets(sec["breakfast"], 2), "Oats porridge with nuts", "Whole grain toast + eggs/tofu")
    mid = _ensure_two(_pick_bullets(sec["mid-morning snack"], 2), "1 Apple", "Cucumber slices")
    l = _ensure_two(_pick_bullets(sec["lunch"], 2), "Brown rice + veggies + protein", "Whole wheat wrap/roti + curry")
    eve = _ensure_two(_pick_bullets(sec["evening snack"], 2), "Buttermilk/Tea (no sugar)", "Roasted nuts")
    d = _ensure_two(_pick_bullets(sec["dinner"], 2), "Clear soup + grilled fish/tofu", "Stir-fried greens + small portion rice")
    
    g = _pick_bullets(sec["general guidelines"], 6)
    if len(g) < 4:
        g = [
            "- Choose low-GI carbs (brown rice, wholemeal bread).",
            "- Fill half your plate with non-starchy vegetables.",
            "- Avoid sugary drinks; choose water or 'kosong' beverages.",
            "- Monitor portion sizes."
        ]

    out = []
    out.append("Breakfast:")
    out.append(f"- Option 1: {_deopt(b[0])}")
    out.append(f"- Option 2: {_deopt(b[1])}")
    out.append("\nMid-morning snack:")
    out.append(f"- Option 1: {_deopt(mid[0])}")
    out.append(f"- Option 2: {_deopt(mid[1])}")
    out.append("\nLunch:")
    out.append(f"- Option 1: {_deopt(l[0])}")
    out.append(f"- Option 2: {_deopt(l[1])}")
    out.append("\nEvening snack:")
    out.append(f"- Option 1: {_deopt(eve[0])}")
    out.append(f"- Option 2: {_deopt(eve[1])}")
    out.append("\nDinner:")
    out.append(f"- Option 1: {_deopt(d[0])}")
    out.append(f"- Option 2: {_deopt(d[1])}")
    out.append("\nGeneral Guidelines:")
    out.extend(g)
    return "\n".join(out).strip()

def _is_valid_format(text: str) -> bool:
    if not text: return False
    low = text.lower()
    if "breakfast" in low and "lunch" in low:
        return True
    return False

def _fallback_plan(location: str) -> str:
    if location == "Singapore":
        return "Breakfast:\n- Option 1: Kopi O Kosong + Wholemeal Toast\n- Option 2: Oats with Soy Milk\n\nMid-morning snack:\n- Option 1: 1 Apple\n- Option 2: Cherry Tomatoes\n\nLunch:\n- Option 1: Sliced Fish Soup (No Milk) + Brown Rice\n- Option 2: Yong Tau Foo (Soup base, no sweet sauce)\n\nEvening snack:\n- Option 1: 6 Walnuts\n- Option 2: Green Tea\n\nDinner:\n- Option 1: Steamed Fish + Xiao Bai Cai\n- Option 2: Grilled Chicken Salad\n\nGeneral Guidelines:\n- Ask for 'Siu Dai' (less sugar) or 'Kosong' (no sugar).\n- Avoid gravies with coconut milk (Laksa, Curry)."
    return "Breakfast:\n- Option 1: Oats porridge\n- Option 2: 2 Idli + Sambar\n\nMid-morning snack:\n- Option 1: Fruit\n- Option 2: Cucumber\n\nLunch:\n- Option 1: 2 Roti + Dal + Sabzi\n- Option 2: Brown Rice + Salad\n\nEvening snack:\n- Option 1: Buttermilk\n- Option 2: Roasted Chana\n\nDinner:\n- Option 1: Khichdi\n- Option 2: Roti + Lauki\n\nGeneral Guidelines:\n- Eat on time.\n- Avoid sweets."

def _fetch_diab_rag(query: str, top_k: int) -> List[Dict[str, Any]]:
    try:
        resp = requests.post(f"{DIAB_RAG_URL}/v1/diabetes/search", json={"query": query, "top_k": top_k}, timeout=DIAB_HTTP_TIMEOUT)
        return resp.json().get("hits") or []
    except:
        return []

def build_diabetes_prompt(user_input: str, location: str, use_rag: bool = True) -> str:
    rag_query = f"Singapore HealthHub diabetes diet {user_input}" if location == "Singapore" else f"ICMR India diabetes diet {user_input}"
    rag_hits = _fetch_diab_rag(rag_query, DIAB_RAG_TOPK) if use_rag else []
    
    evidence = ""
    if rag_hits:
        evidence = "Use these Guidelines:\n" + "\n".join([f"- {h.get('text','')[:300]}" for h in rag_hits])

    context = "Patient is in SINGAPORE. Suggest LOCAL HAWKER FOOD (Yong Tau Foo, Fish Soup)." if location == "Singapore" else "Patient is in INDIA. Suggest TRADITIONAL HOME FOOD."
    
    return (
        f"You are a Dietitian. {context}\n"
        f"Create a 1-day meal plan.\n"
        f"REQUIRED FORMAT:\n"
        f"Breakfast:\n- Option 1: ...\n- Option 2: ...\n"
        f"Mid-morning snack:\n- Option 1: ...\n- Option 2: ...\n"
        f"Lunch:\n- Option 1: ...\n- Option 2: ...\n"
        f"Evening snack:\n- Option 1: ...\n- Option 2: ...\n"
        f"Dinner:\n- Option 1: ...\n- Option 2: ...\n"
        f"General Guidelines:\n- ...\n\n"
        f"EVIDENCE TO USE:\n{evidence}\n\n"
        f"Patient Profile: {user_input}"
    )

def call_diabetes_qwen(user_message: str, use_rag: bool = True, use_kg: bool = True) -> str:
    location = "India"
    if "singapore" in user_message.lower(): location = "Singapore"
    try:
        data = json.loads(user_message)
        if isinstance(data, dict):
            loc = data.get("patient_profile", {}).get("Location", "") or data.get("Location", "")
            if "Singapore" in loc: location = "Singapore"
    except: pass

    logger.info(f"[DIABETES AGENT] Detected Location: {location}")
    prompt = build_diabetes_prompt(user_message, location, use_rag)
    
    # TRY ALL COMMON KEYS
    try:
        r = requests.post(f"{DIAB_OV_URL}/generate", json={"prompt": prompt, "max_new_tokens": DIAB_MAX_NEW_TOKENS}, timeout=DIAB_HTTP_TIMEOUT)
        r.raise_for_status()
        js = r.json()
        
        # UNIVERSAL KEY FINDER
        raw = js.get("output") or js.get("generated_text") or js.get("text") or js.get("reply") or ""
        
        if isinstance(raw, list) and len(raw) > 0: raw = raw[0] # handle list output
        
        cleaned = _normalize_to_standard_format(raw)
        if _is_valid_format(cleaned):
            return cleaned
            
        logger.warning(f"[DIAB] Invalid format received. Triggering Fallback for {location}.")
        return _fallback_plan(location)
        
    except Exception as e:
        logger.exception(f"Error calling AI: {e}")
        return _fallback_plan(location)
