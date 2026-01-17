#!/usr/bin/env python3
"""
app/tools/kidney_qwen_ov.py
Kidney Agent (Renal Specialist) - Region-Aware & Universal Key Patch
"""
import os
import re
import json
import logging
import requests
from typing import Optional, List, Dict, Any
from .kidney_kg import query_kidney_kg

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Config
KIDNEY_OV_URL = os.getenv("KIDNEY_OV_URL", "http://192.168.2.69:8080")
KIDNEY_RAG_URL = os.getenv("KIDNEY_RAG_URL", "http://192.168.2.69:9104") # Port 9104
KIDNEY_HTTP_TIMEOUT = float(os.getenv("KIDNEY_HTTP_TIMEOUT", "30"))
KIDNEY_MAX_NEW_TOKENS = int(os.getenv("KIDNEY_MAX_NEW_TOKENS", "400"))
KIDNEY_RAG_TOPK = int(os.getenv("KIDNEY_RAG_TOPK", "3"))

# 1. INTENT DETECTOR
_CKD_PAT = re.compile(
    r"\b(kidney|ckd|renal|creatinine|potassium|phosphorus|dialysis|gfr|nephropathy)\b",
    flags=re.IGNORECASE,
)

def is_kidney_query(text: Optional[str]) -> bool:
    if not text: return False
    return bool(_CKD_PAT.search(text))

# 2. HELPER FUNCTIONS
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
    logger.info(f"[CKD-RAW-CONTENT] {raw[:500]}...") 
    raw = _strip_prompt_leaks(raw)
    sec = _parse_sections(raw)
    
    b = _ensure_two(_pick_bullets(sec["breakfast"], 2), "Rice Porridge (Congee)", "White Bread Toast + Egg White")
    mid = _ensure_two(_pick_bullets(sec["mid-morning snack"], 2), "1 Apple (Peeled)", "Grapes (Small portion)")
    l = _ensure_two(_pick_bullets(sec["lunch"], 2), "White Rice + Steamed Fish", "Rice Noodles + Clear Soup")
    eve = _ensure_two(_pick_bullets(sec["evening snack"], 2), "Rice Crackers", "Tea (Weak)")
    d = _ensure_two(_pick_bullets(sec["dinner"], 2), "Grilled Chicken + White Rice", "Stir-fry Gourd (Leached)")
    
    g = _pick_bullets(sec["general guidelines"], 6)
    if len(g) < 4:
        g = [
            "- RESTRICT POTASSIUM: Avoid bananas, spinach, coconut water.",
            "- RESTRICT PHOSPHORUS: Avoid dairy, nuts, cola, brown rice.",
            "- DANGER: Avoid Starfruit strictly.",
            "- Leach vegetables (soak/boil) before cooking."
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
        return "Breakfast:\n- Option 1: Plain Rice Porridge (Congee)\n- Option 2: White Bread Toast + Jam\n\nMid-morning snack:\n- Option 1: Apple (Peeled)\n- Option 2: Red Apple\n\nLunch:\n- Option 1: White Rice + Steamed Fish\n- Option 2: Bee Hoon Soup (Clear broth, no internal organs)\n\nEvening snack:\n- Option 1: Rice Crackers\n- Option 2: Weak Tea\n\nDinner:\n- Option 1: Stir-fried Cabbage (Leached) + Chicken\n- Option 2: Steamed Egg + White Rice\n\nGeneral Guidelines:\n- AVOID: Starfruit, Coconut Milk, Herbal Soups.\n- Choose White Rice over Brown Rice (Lower Phosphorus)."
    return "Breakfast:\n- Option 1: Rice Idli (Fermented) + Onion Chutney\n- Option 2: Upma (Low veg)\n\nMid-morning snack:\n- Option 1: Guava (Peeled)\n- Option 2: Pear\n\nLunch:\n- Option 1: White Rice + Leached Dal\n- Option 2: 2 Roti + Bottle Gourd Curry\n\nEvening snack:\n- Option 1: Murmura (Puffed Rice)\n- Option 2: Black Tea\n\nDinner:\n- Option 1: Vegetable Khichdi (Leached veg)\n- Option 2: Arbi (Colocasia) Fry + Roti\n\nGeneral Guidelines:\n- LEACH all vegetables before cooking.\n- Avoid Spinach, Coconut, Dry Fruits."

def _fetch_kidney_rag(query: str, top_k: int) -> List[Dict[str, Any]]:
    try:
        resp = requests.post(f"{KIDNEY_RAG_URL}/v1/kidney/search", json={"query": query, "top_k": top_k}, timeout=KIDNEY_HTTP_TIMEOUT)
        return resp.json().get("hits") or []
    except:
        return []

def build_kidney_prompt(user_input: str, location: str, use_rag: bool = True) -> str:
    rag_query = f"Singapore HealthHub CKD diet {user_input}" if location == "Singapore" else f"ICMR India CKD diet {user_input}"
    rag_hits = _fetch_kidney_rag(rag_query, KIDNEY_RAG_TOPK) if use_rag else []
    
    evidence = ""
    if rag_hits:
        evidence = "Use these Guidelines:\n" + "\n".join([f"- {h.get('text','')[:300]}" for h in rag_hits])

    context = "Patient is in SINGAPORE. Suggest LOW POTASSIUM/PHOSPHORUS HAWKER FOOD. Warn against STARFRUIT." if location == "Singapore" else "Patient is in INDIA. Suggest LOW POTASSIUM HOME FOOD. Warn against SPINACH."
    
    return (
        f"You are a Dietitian specializing in Kidney Disease (CKD). {context}\n"
        f"Create a 1-day CKD meal plan.\n"
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

def call_kidney_qwen(user_message: str, use_rag: bool = True, use_kg: bool = True) -> str:
    location = "India"
    if "singapore" in user_message.lower(): location = "Singapore"
    try:
        data = json.loads(user_message)
        if isinstance(data, dict):
            loc = data.get("patient_profile", {}).get("Location", "") or data.get("Location", "")
            if "Singapore" in loc: location = "Singapore"
    except: pass

    logger.info(f"[KIDNEY AGENT] Detected Location: {location}")
    prompt = build_kidney_prompt(user_message, location, use_rag)
    
    try:
        r = requests.post(f"{KIDNEY_OV_URL}/generate", json={"prompt": prompt, "max_new_tokens": KIDNEY_MAX_NEW_TOKENS}, timeout=KIDNEY_HTTP_TIMEOUT)
        r.raise_for_status()
        js = r.json()
        
        raw = js.get("output") or js.get("generated_text") or js.get("text") or js.get("reply") or ""
        if isinstance(raw, list) and len(raw) > 0: raw = raw[0]
        
        cleaned = _normalize_to_standard_format(raw)
        if _is_valid_format(cleaned):
            return cleaned
            
        logger.warning(f"[CKD] Invalid format. Fallback for {location}.")
        return _fallback_plan(location)
        
    except Exception as e:
        logger.exception(f"Error calling AI: {e}")
        return _fallback_plan(location)
