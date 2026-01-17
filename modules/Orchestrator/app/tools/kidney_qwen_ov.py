#!/usr/bin/env python3
"""
app/tools/kidney_qwen_ov.py

Kidney (CKD) specialist agent integrating:
- Strict renal diet system prompt (India-focused)
- RAG evidence from Kidney FAISS service (optional)

Used by the MCP Orchestrator router.
"""

import os
import logging
import re
from typing import Any, Dict, List, Optional

import requests
# ------------------------------------------------------------------
# Router helpers (DO NOT REMOVE – orchestrator depends on these)
# ------------------------------------------------------------------

def is_kidney_query(text: str) -> bool:
    if not text:
        return False
    t = text.lower()
    return any(k in t for k in [
        "ckd", "kidney", "renal", "creatinine",
        "potassium", "phosphorus", "dialysis"
    ])


_KIDNEY_PAT = re.compile(
    r"\b(ckd|chronic kidney|kidney disease|kidney|renal|egfr|creatinine|"
    r"dialysis|nephro|proteinuria|potassium|phosphorus|fluid restriction)\b",
    flags=re.IGNORECASE,
)

def is_kidney_query(text: Optional[str]) -> bool:
    if not text:
        return False
    return bool(_KIDNEY_PAT.search(text))


logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# Endpoints
# ----------------------------------------------------------------------

KIDNEY_OV_URL = os.getenv("KIDNEY_OV_URL", "http://192.168.2.69:9008")
KIDNEY_RAG_URL = os.getenv("KIDNEY_RAG_URL", "http://192.168.2.69:9104")

KIDNEY_MAX_NEW_TOKENS = int(os.getenv("KIDNEY_MAX_NEW_TOKENS", "220"))
KIDNEY_HTTP_TIMEOUT = float(os.getenv("KIDNEY_HTTP_TIMEOUT", "120"))
KIDNEY_RAG_TIMEOUT = float(os.getenv("KIDNEY_RAG_TIMEOUT", "5.0"))

# ----------------------------------------------------------------------
# System prompt (IMPORTANT: no placeholders like <short option>, no STOP-after text)
# ----------------------------------------------------------------------

SYSTEM_PROMPT = """
You are a conservative renal dietitian for CKD patients in India.
You focus on diet, potassium, phosphorus, sodium, protein, and fluids.
You ALWAYS advise the patient to confirm changes with their nephrologist.

STRICT RULES:
- Never prescribe or adjust medications or dialysis.
- Use mostly Indian vegetarian options (dal, sabzi, roti, idli, dosa, rice, curd, paneer).
- Keep sodium low; avoid pickles/papad/namkeen/packaged foods/restaurant gravies.
- Be careful with high-potassium foods (tomato, banana, coconut water) depending on labs.
- Be careful with high-phosphorus foods (colas, processed cheese, bakery/processed foods).
- Keep response under 300 words.
- DO NOT repeat the patient request.
- Output ONLY the exact headings and bullet format below.

Output format (exact headings in this order, each meal has exactly 2 options):

Breakfast:
- Option 1: ...
- Option 2: ...

Mid-morning snack:
- Option 1: ...
- Option 2: ...

Lunch:
- Option 1: ...
- Option 2: ...

Evening snack:
- Option 1: ...
- Option 2: ...

Dinner:
- Option 1: ...
- Option 2: ...

General Guidelines:
- 4–6 bullets on sodium, potassium/phosphorus, protein, fluids, and when to consult nephrologist.
""".strip()

# ----------------------------------------------------------------------
# RAG helpers
# ----------------------------------------------------------------------

def _query_kidney_rag(question: str, top_k: int = 3) -> List[Dict[str, Any]]:
    url = f"{KIDNEY_RAG_URL}/v1/kidney/search"
    payload = {"query": question, "top_k": top_k}
    try:
        resp = requests.post(url, json=payload, timeout=KIDNEY_RAG_TIMEOUT)
        resp.raise_for_status()
        data = resp.json() or {}
        hits = data.get("hits", []) or []

        print(f"[KIDNEY-RAG] query={question!r} top_k={top_k} hits={len(hits)}", flush=True)
        for h in hits[:top_k]:
            print(f"[KIDNEY-RAG] id={h.get('id')} title={h.get('title')} score={h.get('score')}", flush=True)

        return hits
    except Exception as e:
        logger.warning("[KIDNEY-RAG] error calling RAG: %s", e)
        print(f"[KIDNEY-RAG] ERROR: {e}", flush=True)
        return []

def _format_rag_evidence(hits: List[Dict[str, Any]], max_items: int = 3) -> str:
    """
    Keep evidence short and clearly marked as INTERNAL USE so we can strip it if echoed.
    """
    if not hits:
        return "RAG_EVIDENCE: none"
    lines = ["RAG_EVIDENCE (internal, do not repeat):"]
    for h in hits[:max_items]:
        title = (h.get("title") or "").strip()
        text = (h.get("text") or "").strip()
        if title and text:
            lines.append(f"- {title}: {text}")
        elif text:
            lines.append(f"- {text}")
    return "\n".join(lines)

# ----------------------------------------------------------------------
# Prompt builder
# ----------------------------------------------------------------------

def build_kidney_prompt(user_message: str, use_rag: bool = True) -> str:
    parts: List[str] = [SYSTEM_PROMPT]

    if use_rag:
        hits = _query_kidney_rag(user_message, top_k=3)
        parts.append(_format_rag_evidence(hits))

    parts.append(f"PATIENT_REQUEST (do not repeat): {user_message.strip()}")
    parts.append("Write the final answer now, exactly in the required format.")
    return "\n\n".join(parts).strip() + "\n"

# ----------------------------------------------------------------------
# Output cleanup + validation
# ----------------------------------------------------------------------

HEADINGS = [
    "Breakfast:",
    "Mid-morning snack:",
    "Lunch:",
    "Evening snack:",
    "Dinner:",
    "General Guidelines:",
]

def _contains_bad_markers(text: str) -> bool:
    bad = [
        "OUTPUT FORMAT",
        "STOP after",
        "RAG_EVIDENCE",
        "PATIENT_REQUEST",
        "Dietitian:",
        "<short",
        "<",
        ">",
        "Option  :",
        "Option option",
        'Breakfast:"',
    ]
    t = (text or "").lower()
    return any(b.lower() in t for b in bad)

def _extract_sections(raw: str) -> str:
    """
    Extract only the 6 required sections from the model output.
    If model output contains extra junk, we drop it.
    """
    if not raw:
        return ""

    # Normalize newlines
    text = raw.replace("\r\n", "\n").replace("\r", "\n")

    # Find first real "Breakfast:" line and drop everything before it
    idx = text.find("Breakfast:")
    if idx != -1:
        text = text[idx:]

    # Build regex that captures each heading block up to next heading
    pattern = re.compile(
        r"(?s)"
        r"(Breakfast:.*?)(?=Mid-morning snack:|$)"
        r"(Mid-morning snack:.*?)(?=Lunch:|$)"
        r"(Lunch:.*?)(?=Evening snack:|$)"
        r"(Evening snack:.*?)(?=Dinner:|$)"
        r"(Dinner:.*?)(?=General Guidelines:|$)"
        r"(General Guidelines:.*)$"
    )

    m = pattern.search(text)
    if not m:
        return text.strip()

    cleaned = "\n\n".join(s.strip() for s in m.groups() if s)
    return cleaned.strip()

def _is_valid_format(text: str) -> bool:
    """
    Must contain each heading exactly once.
    For each meal heading, must have Option 1 and Option 2 lines.
    For General Guidelines, must have at least 4 bullets.
    """
    if not text:
        return False

    # Headings appear once
    for h in HEADINGS:
        if text.count(h) != 1:
            return False

    # No placeholder / prompt leak markers
    if _contains_bad_markers(text):
        return False

    # Each meal section has both options
    for h in HEADINGS[:-1]:
        # block from heading to next heading
        start = text.find(h)
        end = min([text.find(nh) for nh in HEADINGS if nh != h and text.find(nh) > start] + [len(text)])
        block = text[start:end]
        if "Option 1:" not in block or "Option 2:" not in block:
            return False

    # General guidelines bullets count
    g = "General Guidelines:"
    gs = text.find(g)
    gblock = text[gs:]
    bullets = [ln for ln in gblock.splitlines() if ln.strip().startswith("-")]
    if len(bullets) < 4:
        return False

    return True

def _fallback_plan(user_message: str) -> str:
    """
    Deterministic safe fallback if model output is messy.
    Keep it practical for CKD stage 3 Indian vegetarian.
    """
    # Tomato note depends on potassium labs; keep conservative.
    return (
        "Breakfast:\n"
        "- Option 1: Vegetable upma (no added salt) + 1 small bowl curd.\n"
        "- Option 2: 2 idli + sambar (low salt) + coconut chutney (small).\n\n"
        "Mid-morning snack:\n"
        "- Option 1: 1 apple or guava (small).\n"
        "- Option 2: Unsalted makhana (1 small handful).\n\n"
        "Lunch:\n"
        "- Option 1: 2 phulka (no salted ghee) + lauki/beans sabzi + moong dal (measured).\n"
        "- Option 2: 1 cup rice + cabbage/cauliflower sabzi + curd (small bowl).\n\n"
        "Evening snack:\n"
        "- Option 1: Lemon water + roasted chana (unsalted, small).\n"
        "- Option 2: Poha (low oil, no added salt) with veggies.\n\n"
        "Dinner:\n"
        "- Option 1: 2 phulka + ridge gourd (turai) curry + small dal portion.\n"
        "- Option 2: Vegetable khichdi (moong dal + rice, low salt) + cucumber salad.\n\n"
        "General Guidelines:\n"
        "- Tomatoes: if potassium is normal, use small portions occasionally; avoid tomato-heavy dishes daily.\n"
        "- Keep salt low: avoid pickles, papad, namkeen, packaged snacks, instant soups/noodles.\n"
        "- Protein: keep moderate—measured portions of dal/legumes/paneer; avoid protein powders unless advised.\n"
        "- Prefer home-cooked meals; flavor with lemon, herbs, garlic, cumin instead of salt.\n"
        "- Review labs (potassium/phosphorus/creatinine) and confirm diet limits with your nephrologist/dietitian.\n"
    ).strip()

def _strip_prompt_leaks(text: str) -> str:
    if not text:
        return ""

    BAD_MARKERS = [
        "STOP after",
        "RAG_EVIDENCE",
        "PATIENT_REQUEST",
        "You are a",
        "Under each meal heading",
        "<short",
        "Option : <",
    ]

    cleaned = []
    for line in text.splitlines():
        if any(b.lower() in line.lower() for b in BAD_MARKERS):
            continue
        cleaned.append(line)

    return "\n".join(cleaned).strip()

# ----------------------------------------------------------------------
# Main call
# ----------------------------------------------------------------------

def call_kidney_qwen(user_message: str, use_rag: bool = True) -> str:
    """
    Generate CKD diet response using Qwen-OV.
    Ensures:
    - No prompt leakage
    - Strict output format
    - Safe fallback if model misbehaves
    """

    prompt = build_kidney_prompt(user_message, use_rag=use_rag)
    payload = {
        "prompt": prompt,
        "max_new_tokens": KIDNEY_MAX_NEW_TOKENS,
    }

    try:
        r = requests.post(
            f"{KIDNEY_OV_URL}/generate",
            json=payload,
            timeout=KIDNEY_HTTP_TIMEOUT,
        )
        r.raise_for_status()

        data = r.json() or {}
        raw = (
            data.get("output")
            or data.get("text")
            or data.get("completion")
            or ""
        ).strip()

        # 1️⃣ Hard strip prompt leaks / garbage
        raw = _strip_prompt_leaks(raw)

        # 2️⃣ Extract only required sections
        cleaned = _extract_sections(raw)

        # 3️⃣ Validate strict format
        if not _is_valid_format(cleaned):
            print("[KIDNEY] invalid format after cleanup → fallback", flush=True)
            return _fallback_plan(user_message)

        # 4️⃣ Final sanity guard
        if len(cleaned) < 120:
            print("[KIDNEY] response too short → fallback", flush=True)
            return _fallback_plan(user_message)

        return cleaned

    except Exception:
        logger.exception("Kidney Qwen OV error")
        return _fallback_plan(user_message)

