#!/usr/bin/env python3
# app/tools/hypertension_qwen_ov.py

import os
import re
import logging
from typing import Optional, List, Dict

import requests

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# Xeon inference server HTN service
# ----------------------------------------------------------------------
HTN_QWEN_OV_URL = os.getenv(
    "HTN_QWEN_OV_URL",
    "http://192.168.2.69:9007",  # adjust if your HTN OV endpoint differs
)
HTN_HTTP_TIMEOUT = float(os.getenv("HTN_HTTP_TIMEOUT", "15.0"))
HTN_MAX_NEW_TOKENS = int(os.getenv("HTN_MAX_NEW_TOKENS", "220"))

# ----------------------------------------------------------------------
# Simple HTN intent detector
# ----------------------------------------------------------------------
_HTN_PAT = re.compile(
    r"\b(hypertension|high\s*blood\s*pressure|bp\s*\d+\/\d+|"
    r"systolic|diastolic|dah?sh|low[\s-]?salt|sodium)\b",
    flags=re.IGNORECASE,
)


def is_hypertension_query(text: Optional[str]) -> bool:
    if not text:
        return False
    return bool(_HTN_PAT.search(text))


# ----------------------------------------------------------------------
# Output cleanup / extraction helpers
# ----------------------------------------------------------------------
_SECTION_ORDER = [
    "Breakfast",
    "Mid-morning snack",
    "Lunch",
    "Evening snack",
    "Dinner",
    "General Guidelines",
]

_HDR_RE = re.compile(
    r"^\s*(?:#{1,6}\s*)?(?:\*\*|\*)?\s*"
    r"(Breakfast|Mid-morning snack|Lunch|Evening snack|Dinner|General Guidelines)"
    r"\s*:\s*(?:\*\*|\*)?\s*$",
    flags=re.IGNORECASE | re.MULTILINE,
)

_LEAK_MARKERS = [
    "you are a",
    "system:",
    "assistant:",
    "user:",
    "output format",
    "strict rules",
    "do not repeat",
    "generate a",
    "keep the response",
    "max_new_tokens",
    "dietitian",
    "instructions",
    "response must be",
    "patient request",
    "extra notes:",
    "comorbidities:",
    "age:",
    "sex:",
]


def _strip_prompt_leaks(text: str) -> str:
    """
    Remove obvious instruction/prompt leakage lines.
    Keeps the actual meal plan content.
    """
    if not text:
        return ""

    lines = text.splitlines()
    cleaned: List[str] = []
    for ln in lines:
        low = ln.strip().lower()

        # drop leading empties
        if not cleaned and not low:
            continue

        if any(m in low for m in _LEAK_MARKERS):
            continue

        cleaned.append(ln)

    return "\n".join(cleaned).strip()


def _strip_preamble(raw: str) -> str:
    """
    If we find a meal heading, drop everything before it.
    """
    if not raw:
        return ""
    s = raw.strip()

    m = re.search(r"(?im)^(#+\s*)?(breakfast|mid[-\s]?morning snack|lunch|evening snack|dinner)\s*:", s)
    if m:
        s = s[m.start():].lstrip()

    return s.strip()


def _parse_sections(text: str) -> Dict[str, str]:
    """
    Parse semi-structured text into our expected sections.
    If headings are missing, everything goes into breakfast (then fallbacks fill rest).
    """
    out = {k.lower(): "" for k in _SECTION_ORDER}
    if not text:
        return out

    s = re.sub(r"(?im)^#+\s*", "", text).strip()

    cur = None
    buf: List[str] = []

    def flush():
        nonlocal cur, buf
        if cur is not None:
            out[cur] = "\n".join(buf).strip()
        buf = []

    for ln in s.splitlines():
        t = ln.strip()
        m = re.match(
            r"(?im)^(breakfast|mid[-\s]?morning snack|lunch|evening snack|dinner|general guidelines?)\s*:\s*$",
            t,
        )
        if m:
            flush()
            name = m.group(1).lower()
            name = name.replace("mid morning", "mid-morning").replace("mid  morning", "mid-morning")
            name = name.replace("mid-morning", "mid-morning snack")
            if name.startswith("general"):
                name = "general guidelines"
            cur = name
            continue

        # accept normal lines
        if cur is None:
            cur = "breakfast"
        buf.append(ln)

    flush()
    return out


def _pick_bullets(block: str, max_items: int = 2) -> List[str]:
    """
    Extract up to N bullet-ish lines.
    If no bullets, salvage non-empty lines.
    Returns items WITHOUT forcing "Option X:".
    """
    if not block:
        return []

    picked: List[str] = []

    for ln in block.splitlines():
        s = ln.strip()
        if not s:
            continue

        # bullet-ish
        if s.startswith(("-", "•", "*")):
            s = s.lstrip("*•").strip()
            s = s.lstrip("-").strip()

        # remove "Option X:" if present
        s = re.sub(r"(?i)^\s*option\s*[a-z0-9]+\s*:\s*", "", s).strip()
        if not s:
            continue

        picked.append(s)
        if len(picked) >= max_items:
            break

    # salvage if we still have nothing
    if not picked:
        for ln in block.splitlines():
            s = ln.strip()
            if not s:
                continue
            s = re.sub(r"(?i)^\s*option\s*[a-z0-9]+\s*:\s*", "", s).strip()
            if s:
                picked.append(s)
            if len(picked) >= max_items:
                break

    return picked[:max_items]


def _drop_noisy_guidelines(g: List[str]) -> List[str]:
    """
    Remove generic / irrelevant guidelines (e.g., alcohol limits, men/women dosing, etc.).
    """
    bad = ("alcohol", "women", "men", "one drink", "two drinks")
    out: List[str] = []
    for b in g:
        if any(x in b.lower() for x in bad):
            continue
        out.append(b)
    return out


def _normalize_to_standard_format(raw_plan: str) -> str:
    """
    Enforce:
      - exact 2 options per meal section
      - clean headings and leakage removal
      - sodium target + blocklist in guidelines
    """
    txt = _strip_preamble(_strip_prompt_leaks(raw_plan))
    sec = _parse_sections(txt)

    b = _pick_bullets(sec["breakfast"], 2)
    mid = _pick_bullets(sec["mid-morning snack"], 2)
    l = _pick_bullets(sec["lunch"], 2)
    eve = _pick_bullets(sec["evening snack"], 2)
    d = _pick_bullets(sec["dinner"], 2)

    g = _pick_bullets(sec["general guidelines"], 10)
    g = _drop_noisy_guidelines(g)

    # ---- Force exactly 2 options with deterministic fallbacks ----
    if len(b) < 2:
        b = (b + [
            "Vegetable oats upma + mint/coriander chutney (no added salt).",
            "2 idli + sambar (low salt) + coconut chutney (small).",
        ])[:2]

    if len(mid) < 2:
        mid = (mid + [
            "Fruit (guava/orange) + 6–8 unsalted almonds.",
            "Unsalted makhana (small handful) + lemon water.",
        ])[:2]

    if len(l) < 2:
        l = (l + [
            "2 phulka + mixed veg sabzi + dal (measured, low salt).",
            "Brown rice (1 cup) + sambar (less salt/oil) + cucumber salad.",
        ])[:2]

    if len(eve) < 2:
        eve = (eve + [
            "Buttermilk (unsalted) + roasted chana (unsalted, small).",
            "Sprouts chaat (no sev, low salt) + green tea.",
        ])[:2]

    if len(d) < 2:
        d = (d + [
            "Vegetable khichdi (moong dal + rice, low salt) + salad.",
            "2 phulka + lauki/tinda curry + curd (small bowl).",
        ])[:2]

    # ---- Guidelines: inject sodium target + blocklist always ----
    must_have = [
        "Aim ~1500–2000 mg sodium/day (or per your clinician).",
        "Strictly avoid/limit: pickles, papad, namkeen, instant soups/noodles, packaged sauces/masalas, bakery/processed foods, restaurant gravies.",
        "Flavor with lemon, herbs, garlic, jeera, pepper instead of salt.",
        "Prefer DASH plate: more fruits/veg/whole grains; moderate low-fat dairy if tolerated.",
        "If on BP meds or kidney issues, confirm potassium intake with your clinician.",
    ]

    # keep model guidelines, but ensure our must_have are included
    final_g: List[str] = []
    seen = set()

    def add_line(x: str):
        k = x.strip().lower()
        if k and k not in seen:
            seen.add(k)
            final_g.append(x.strip())

    for x in must_have:
        add_line(x)

    for x in g:
        # avoid repeating blocklist/alcohol noise; keep short meaningful ones
        if any(z in x.lower() for z in ("alcohol", "women", "men", "one drink", "two drinks")):
            continue
        add_line(x)

    # keep 4–6 bullets max
    final_g = final_g[:6]

    # ---- Compose final response in your standard format ----
    out: List[str] = []
    out.append("Breakfast:")
    out.append(f"- Option 1: {b[0]}")
    out.append(f"- Option 2: {b[1]}")

    out.append("\nMid-morning snack:")
    out.append(f"- Option 1: {mid[0]}")
    out.append(f"- Option 2: {mid[1]}")

    out.append("\nLunch:")
    out.append(f"- Option 1: {l[0]}")
    out.append(f"- Option 2: {l[1]}")

    out.append("\nEvening snack:")
    out.append(f"- Option 1: {eve[0]}")
    out.append(f"- Option 2: {eve[1]}")

    out.append("\nDinner:")
    out.append(f"- Option 1: {d[0]}")
    out.append(f"- Option 2: {d[1]}")

    out.append("\nGeneral Guidelines:")
    for x in final_g:
        out.append(f"- {x}")

    return "\n".join(out).strip()


def _fallback_plan(_: str) -> str:
    """
    Deterministic fallback (always strict-low-salt, Indian veg).
    """
    return (
        "Breakfast:\n"
        "- Option 1: Vegetable oats upma + mint/coriander chutney (no added salt).\n"
        "- Option 2: 2 idli + sambar (low salt) + coconut chutney (small).\n\n"
        "Mid-morning snack:\n"
        "- Option 1: Fruit (guava/orange) + 6–8 unsalted almonds.\n"
        "- Option 2: Unsalted makhana (small handful) + lemon water.\n\n"
        "Lunch:\n"
        "- Option 1: 2 phulka + mixed veg sabzi + dal (measured, low salt).\n"
        "- Option 2: Brown rice (1 cup) + sambar (less salt/oil) + cucumber salad.\n\n"
        "Evening snack:\n"
        "- Option 1: Buttermilk (unsalted) + roasted chana (unsalted, small).\n"
        "- Option 2: Sprouts chaat (no sev, low salt) + green tea.\n\n"
        "Dinner:\n"
        "- Option 1: Vegetable khichdi (moong dal + rice, low salt) + salad.\n"
        "- Option 2: 2 phulka + lauki/tinda curry + curd (small bowl).\n\n"
        "General Guidelines:\n"
        "- Aim ~1500–2000 mg sodium/day (or per your clinician).\n"
        "- Strictly avoid/limit: pickles, papad, namkeen, instant soups/noodles, packaged sauces/masalas, bakery/processed foods, restaurant gravies.\n"
        "- Flavor with lemon, herbs, garlic, jeera, pepper instead of salt.\n"
        "- Prefer DASH plate: more fruits/veg/whole grains; moderate low-fat dairy if tolerated.\n"
        "- If on BP meds or kidney issues, confirm potassium intake with your clinician.\n"
    ).strip()


# ----------------------------------------------------------------------
# HTTP call into HTN OV service + normalization
# ----------------------------------------------------------------------
def call_htn_qwen(user_message: str, timeout: float = HTN_HTTP_TIMEOUT) -> str:
    """
    Call HTN model server and normalize response into standard 6-section format.
    """
    # If your HTN OV service expects /generate like kidney, keep this.
    payload = {
        "prompt": (
            "You are a hypertension dietitian.\n"
            "Return a strict low-salt Indian vegetarian 1-day plan.\n"
            "Format strictly with headings: Breakfast, Mid-morning snack, Lunch, Evening snack, Dinner, General Guidelines.\n"
            "Each meal must have exactly 2 options, each option one line.\n"
            "Guidelines: include sodium target and avoid/limit list.\n\n"
            f"User: {user_message}\n"
        ),
        "max_new_tokens": HTN_MAX_NEW_TOKENS,
    }

    try:
        r = requests.post(f"{HTN_QWEN_OV_URL}/generate", json=payload, timeout=timeout)
        r.raise_for_status()
        data = r.json() or {}
        raw = (data.get("output") or data.get("text") or data.get("completion") or "").strip()

        cleaned = _normalize_to_standard_format(raw)
        return cleaned if cleaned else _fallback_plan(user_message)

    except Exception:
        logger.exception("Hypertension Qwen OV error")
        return _fallback_plan(user_message)
