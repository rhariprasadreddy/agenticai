#!/usr/bin/env python3
"""
app/tools/hypertension_qwen_ov.py
Hypertension Agent (DASH Specialist) - Fixed Naming Mismatch
"""
import os
import re
import json
import logging
import requests
from typing import Optional, List, Dict, Any
from .hypertension_kg import query_hypertension_kg

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Config
HTN_OV_URL = os.getenv("HTN_OV_URL", "http://192.168.2.69:8080")
HTN_RAG_URL = os.getenv("HTN_RAG_URL", "http://192.168.2.69:9103") # Port 9103
HTN_HTTP_TIMEOUT = float(os.getenv("HTN_HTTP_TIMEOUT", "30"))
HTN_MAX_NEW_TOKENS = int(os.getenv("HTN_MAX_NEW_TOKENS", "400"))
HTN_RAG_TOPK = int(os.getenv("HTN_RAG_TOPK", "3"))

# 1. INTENT DETECTOR
_HTN_PAT = re.compile(
    r"\b(hypertension|high\s*bp|blood\s*pressure|dash|sodium|salt|systolic|diastolic)\b",
    flags=re.IGNORECASE,
)

def is_hypertension_query(text: Optional[str]) -> bool:
    if not text: return False
    return bool(_HTN_PAT.search(text))

# 2. HELPER FUNCTIONS (Formatting)
_SECTION_ORDER = ["Breakfast", "Mid-morning snack", "Lunch", "Evening snack", "Dinner", "General Guidelines"]
_LEAK_MARKERS = ["you are a helpful", "system prompt", "generate a", "strict rules", "evidence"]

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
    logger.info(f"[HTN-RAW-CONTENT] {raw[:500]}...") 
    raw = _strip_prompt_leaks(raw)
    sec = _parse_sections(raw)
    
    b = _ensure_two(_pick_bullets(sec["breakfast"], 2), "Oats porridge (no sugar)", "Whole grain toast + egg white")
    mid = _ensure_two(_pick_bullets(sec["mid-morning snack"], 2), "1 Banana (Potassium rich)", "Unsalted Almonds")
    l = _ensure_two(_pick_bullets(sec["lunch"], 2), "Brown Rice + Steamed Fish", "Whole wheat chapati + Dal (low salt)")
    eve = _ensure_two(_pick_bullets(sec["evening snack"], 2), "Coconut water", "Roasted Makhana (no salt)")
    d = _ensure_two(_pick_bullets(sec["dinner"], 2), "Grilled Chicken Salad", "Vegetable Khichdi (low salt)")
    
    g = _pick_bullets(sec["general guidelines"], 6)
    if len(g) < 4:
        g = [
            "- STRICTLY LIMIT SALT: <1 teaspoon (2300mg) per day.",
            "- Eat Potassium-rich foods: Spinach, Bananas, Coconut Water.",
            "- Avoid processed foods: Pickles, Papad, Canned Soup, Ham/Sausages.",
            "- Use herbs/lemon instead of salt for flavor."
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
    if "breakfast" in low and "lunch" in low: return True
    return False

def _fallback_plan(location: str) -> str:
    if location == "Singapore":
        return "Breakfast:\n- Option 1: Oatmeal with Banana\n- Option 2: Wholemeal Bread + Peanut Butter\n\nMid-morning snack:\n- Option 1: Papaya slices\n- Option 2: Unsalted Walnuts\n\nLunch:\n- Option 1: Yong Tau Foo (Dry style, sauce on side)\n- Option 2: Economic Rice (Steamed Egg, Tofu, Veggies)\n\nEvening snack:\n- Option 1: Soya Bean Milk (Low sugar)\n- Option 2: 1 Apple\n\nDinner:\n- Option 1: Sliced Fish Soup (No milk, don't drink soup)\n- Option 2: Grilled Chicken Breast + Salad\n\nGeneral Guidelines:\n- ASK FOR LESS SALT.\n- Avoid: Lor Mee, Curry Chicken Gravy, Salted Egg."
    return "Breakfast:\n- Option 1: Dalia Upma (Low salt)\n- Option 2: Oats Porridge\n\nMid-morning snack:\n- Option 1: Coconut Water\n- Option 2: Fruit Salad\n\nLunch:\n- Option 1: 2 Roti + Moong Dal (No tadka)\n- Option 2: Brown Rice + Curd\n\nEvening snack:\n- Option 1: Roasted Chana (Unsalted)\n- Option 2: Green Tea\n\nDinner:\n- Option 1: Khichdi with lots of veggies\n- Option 2: Bottle Gourd (Lauki) Curry + 1 Roti\n\nGeneral Guidelines:\n- NO PICKLES or PAPAD.\n- Limit salt usage."

def _fetch_htn_rag(query: str, top_k: int) -> List[Dict[str, Any]]:
    try:
        resp = requests.post(f"{HTN_RAG_URL}/v1/hypertension/search", json={"query": query, "top_k": top_k}, timeout=HTN_HTTP_TIMEOUT)
        return resp.json().get("hits") or []
    except:
        return []

def build_hypertension_prompt(user_input: str, location: str, use_rag: bool = True) -> str:
    rag_query = f"Singapore HealthHub hypertension DASH diet {user_input}" if location == "Singapore" else f"ICMR India hypertension DASH diet {user_input}"
    rag_hits = _fetch_htn_rag(rag_query, HTN_RAG_TOPK) if use_rag else []
    
    evidence = ""
    if rag_hits:
        evidence = "Use these Guidelines:\n" + "\n".join([f"- {h.get('text','')[:300]}" for h in rag_hits])

    context = "Patient is in SINGAPORE. Suggest LOW SALT HAWKER FOOD. Warn against GRAVY/SOUP." if location == "Singapore" else "Patient is in INDIA. Suggest LOW SALT HOME FOOD. Warn against PICKLES/PAPAD."
    
    return (
        f"You are a Dietitian specializing in Hypertension (DASH Diet). {context}\n"
        f"Create a 1-day DASH meal plan.\n"
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

# --- RENAMED FUNCTION TO MATCH ROUTER ---
def call_htn_qwen(user_message: str, use_rag: bool = True, use_kg: bool = True) -> str:
    location = "India"
    if "singapore" in user_message.lower(): location = "Singapore"
    try:
        data = json.loads(user_message)
        if isinstance(data, dict):
            loc = data.get("patient_profile", {}).get("Location", "") or data.get("Location", "")
            if "Singapore" in loc: location = "Singapore"
    except: pass

    logger.info(f"[HYPERTENSION AGENT] Detected Location: {location}")
    prompt = build_hypertension_prompt(user_message, location, use_rag)
    
    try:
        r = requests.post(f"{HTN_OV_URL}/generate", json={"prompt": prompt, "max_new_tokens": HTN_MAX_NEW_TOKENS}, timeout=HTN_HTTP_TIMEOUT)
        r.raise_for_status()
        js = r.json()
        
        # UNIVERSAL KEY FINDER
        raw = js.get("output") or js.get("generated_text") or js.get("text") or js.get("reply") or ""
        if isinstance(raw, list) and len(raw) > 0: raw = raw[0]
        
        cleaned = _normalize_to_standard_format(raw)
        if _is_valid_format(cleaned):
            return cleaned
            
        logger.warning(f"[HTN] Invalid format. Fallback for {location}.")
        return _fallback_plan(location)
        
    except Exception as e:
        logger.exception(f"Error calling AI: {e}")
        return _fallback_plan(location)
