#!/usr/bin/env python3
# app/tools/lipids_qwen_ov.py

import os
import re
from typing import Optional, List

import requests

# ----------------------------------------------------------------------
# Xeon inference server LIPIDS service
# ----------------------------------------------------------------------
LIPIDS_QWEN_OV_URL = os.getenv(
    "LIPIDS_QWEN_OV_URL",
    "http://192.168.2.69:9006/v1/lipids/plan",
)

# ----------------------------------------------------------------------
# Simple lipids-intent detector
# ----------------------------------------------------------------------
_LIPIDS_PAT = re.compile(
    r"\b(ldl|hdl|triglyceride|triglycerides|cholesterol|lipid profile|"
    r"dyslipidemia|hyperlipidemia)\b",
    flags=re.IGNORECASE,
)


def is_lipids_query(text: Optional[str]) -> bool:
    if not text:
        return False
    return bool(_LIPIDS_PAT.search(text))


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

# Matches lines like:
# Breakfast:
# *Breakfast:*
# ### Breakfast:
# **Breakfast:**
_HDR_RE = re.compile(
    r"^\s*(?:#{1,6}\s*)?(?:\*\*|\*)?\s*"
    r"(Breakfast|Mid-morning snack|Lunch|Evening snack|Dinner|General Guidelines)"
    r"\s*:\s*(?:\*\*|\*)?\s*$",
    flags=re.IGNORECASE | re.MULTILINE,
)

# Common “prompt leakage” markers from the lipids service output
_LEAK_MARKERS = [
    "you are a cardiometabolic",
    "cardiometabolic lipids specialist",
    "generate a concise",
    "keep the response",
    "response must be",
    "output format",
    "strict rules",
    "do not repeat",
    "patient request",
    "extra notes:",
    "comorbidities:",
    "age:",
    "sex:",
    "ldl:",
    "hdl:",
    "tg:",
    "notes:",
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

        # drop leading empty lines
        if not cleaned and not low:
            continue

        # drop common leaked instruction lines
        if any(m in low for m in _LEAK_MARKERS):
            continue

        # drop obvious transcript prefixes
        if low.startswith(("system:", "user:", "assistant:")):
            continue

        cleaned.append(ln)

    return "\n".join(cleaned).strip()


def _extract_sections(raw: str) -> str:
    """
    Extract only the known meal-plan sections.
    If the model didn't give headings, return best-effort cleaned raw.
    """
    if not raw:
        return ""

    raw = _strip_prompt_leaks(raw)

    matches = list(_HDR_RE.finditer(raw))
    if not matches:
        return raw.strip()

    blocks: List[str] = []
    for idx, m in enumerate(matches):
        sec = (m.group(1) or "").strip()
        start = m.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(raw)
        body = raw[start:end].strip()

        canonical = next((s for s in _SECTION_ORDER if s.lower() == sec.lower()), sec)

        # remove accidental headings inside body
        body = _HDR_RE.sub("", body).strip()

        blocks.append(f"{canonical}:\n{body}".rstrip())

    # order sections in canonical order
    sec_map = {}
    for b in blocks:
        head = b.splitlines()[0].rstrip(":").strip().lower()
        sec_map[head] = b

    ordered: List[str] = []
    for s in _SECTION_ORDER:
        b = sec_map.get(s.lower())
        if b:
            ordered.append(b)

    return ("\n\n".join(ordered).strip()) if ordered else raw.strip()


def _is_valid_format(text: str) -> bool:
    """
    Minimal validation:
    - must include key headings
    - must not contain placeholder markers
    """
    if not text:
        return False
    low = text.lower()
    if "breakfast:" not in low or "dinner:" not in low:
        return False
    if "<short" in low:
        return False
    # discourage ellipsis placeholders (but don't reject normal sentences with "...")
    if "option 1: ..." in low or "option 2: ..." in low:
        return False
    return True


def _fallback_plan(_: str) -> str:
    """
    Deterministic fallback plan (clean and presentable).
    """
    return (
        "Breakfast:\n"
        "- Option 1: Oats porridge (water/low-fat milk) + 1 tbsp flax/chia + 1 small apple.\n"
        "- Option 2: Vegetable ragi upma + 8–10 unsalted almonds.\n\n"
        "Mid-morning snack:\n"
        "- Option 1: Unsweetened curd (small bowl) + cucumber.\n"
        "- Option 2: Roasted chana / makhana (small handful, unsalted).\n\n"
        "Lunch:\n"
        "- Option 1: 2 phulka + mixed veg sabzi + moong/masoor dal (measured).\n"
        "- Option 2: Brown rice (1 cup) + sambar (less oil) + salad.\n\n"
        "Evening snack:\n"
        "- Option 1: Green tea / lemon water + sprouts chaat (no sev, low salt).\n"
        "- Option 2: Fruit (guava/orange) + 4–6 walnuts.\n\n"
        "Dinner:\n"
        "- Option 1: Khichdi (moong dal + brown rice) + stir-fried vegetables.\n"
        "- Option 2: 2 phulka + lauki/tinda curry + curd (small bowl).\n\n"
        "General Guidelines:\n"
        "- Prefer high-fiber carbs (oats, millets, brown rice) and plenty of vegetables.\n"
        "- Use MUFA/PUFA oils (groundnut/mustard/olive) and limit fried foods, ghee, butter.\n"
        "- For high TG: avoid sugary drinks/desserts/juice; keep portions controlled.\n"
        "- Add omega-3 veg sources: flax/chia, walnuts.\n"
        "- Reduce refined flour/bakery foods and avoid trans fats.\n"
    ).strip()


# ----------------- Lipids output normalization helpers -----------------

_LIPIDS_SECTION_PAT = re.compile(
    r"(?im)^(#+\s*)?(breakfast|mid[-\s]?morning snack|snacks?|lunch|evening snack|dinner|general guidelines?)\s*:\s*$"
)

def _veg_guard(text: str) -> str:
    """
    Last-mile safety: if model leaks non-veg, swap to veg equivalents.
    Keep it simple (regex word-boundary) so formatting stays intact.
    """
    if not text:
        return text

    swaps = {
        "chicken": "paneer/tofu",
        "fish": "tofu/paneer",
        "salmon": "tofu/paneer",
        "cod": "tofu/paneer",
        "egg": "besan/tofu",
        "eggs": "besan/tofu",
        "meat": "paneer/tofu",
    }

    out = text
    for k, v in swaps.items():
        out = re.sub(rf"\b{k}\b", v, out, flags=re.IGNORECASE)
    return out


def _strip_preamble(raw: str) -> str:
    """
    Remove the long system/prompt-like preamble and start from the first meal heading if present.
    """
    if not raw:
        return ""

    s = raw.strip()

    # If the response contains a heading, cut everything before the first heading
    m = re.search(r"(?im)^(#+\s*)?(breakfast|lunch|snacks?|dinner)\s*:", s)
    if m:
        s = s[m.start():].lstrip()

    # Drop repeated "You are a ..." / "Age:" etc lines if still present at top
    lines = s.splitlines()
    cleaned = []
    drop_prefix = True
    for ln in lines:
        t = ln.strip()
        if drop_prefix and (
            t.lower().startswith("you are ")
            or t.lower().startswith("age:")
            or t.lower().startswith("ldl:")
            or t.lower().startswith("hdl:")
            or t.lower().startswith("tg:")
            or t.lower().startswith("comorbidities:")
            or t.lower().startswith("extra notes:")
            or t.lower().startswith("generate a ")
        ):
            continue
        drop_prefix = False
        cleaned.append(ln)
    return "\n".join(cleaned).strip()


def _parse_sections(text: str) -> dict:
    """
    Parse any of: Breakfast/Lunch/Dinner/Snacks/General Guidelines from semi-structured text.
    Returns dict with keys: breakfast, snacks, lunch, dinner, guidelines
    """
    out = {"breakfast": "", "snacks": "", "lunch": "", "dinner": "", "guidelines": ""}

    if not text:
        return out

    # Normalize headings like "### Breakfast:" to "Breakfast:"
    s = re.sub(r"(?im)^#+\s*", "", text).strip()

    # Split on headings
    parts = []
    cur_name = None
    cur_buf = []

    for ln in s.splitlines():
        if re.match(r"(?im)^(breakfast|lunch|snacks?|dinner|general guidelines?)\s*:\s*$", ln.strip()):
            # flush previous
            if cur_name is not None:
                parts.append((cur_name, "\n".join(cur_buf).strip()))
            cur_name = ln.strip().lower().split(":")[0]
            cur_buf = []
        else:
            cur_buf.append(ln)

    if cur_name is not None:
        parts.append((cur_name, "\n".join(cur_buf).strip()))

    for name, body in parts:
        key = name
        if key.startswith("snack"):
            key = "snacks"
        if key.startswith("general"):
            key = "guidelines"
        if key in out:
            out[key] = body

    return out

def _pick_bullets(block: str, max_items: int = 2) -> list[str]:
    """
    Extract up to N non-empty bullet-ish lines.
    If no bullets exist, salvage non-empty lines as bullets.
    """
    if not block:
        return []

    lines: list[str] = []

    for ln in block.splitlines():
        s = ln.strip()
        if not s:
            continue

        # bullet-ish lines
        if s.startswith(("-", "•", "*")):
            s = s.lstrip("*•").strip()
            s = s.lstrip("-").strip()

            # Strip any "Option X:" prefix the model may include
            s = re.sub(r"(?i)^\s*option\s*\d+\s*:\s*", "", s).strip()

            # skip empty bullets
            if not s:
                continue

            lines.append("- " + s)

            if len(lines) >= max_items:
                break

    # salvage if no explicit bullets were found
    if not lines:
        for ln in block.splitlines():
            s = ln.strip()
            if s:
                s = re.sub(r"(?i)^\s*option\s*\d+\s*:\s*", "", s).strip()
                if s:
                    lines.append("- " + s)
            if len(lines) >= max_items:
                break

    return lines[:max_items]

def _drop_noisy_guidelines(g: list[str]) -> list[str]:
    bad = ("alcohol", "women", "men", "one drink", "two drinks")
    out: list[str] = []
    for b in g:
        if any(x in b.lower() for x in bad):
            continue
        out.append(b)
    return out

def _normalize_to_standard_format(raw_plan: str) -> str:
    """
    Convert Lipids plan into the same 6-section format as other agents.
    We map:
      - Breakfast -> Breakfast
      - Snacks -> split into Mid-morning + Evening (duplicate if only 1–2 items)
      - Lunch -> Lunch
      - Dinner -> Dinner
      - Guidelines -> General Guidelines (or create defaults)
    """
    txt = _veg_guard(_strip_preamble(raw_plan))
    sec = _parse_sections(txt)

    b = _pick_bullets(sec["breakfast"], 2)
    l = _pick_bullets(sec["lunch"], 2)
    d = _pick_bullets(sec["dinner"], 2)

    snacks = _pick_bullets(sec["snacks"], 4)

    # Mid-morning uses first 2 snack bullets (if any)
    mid = snacks[:2] if snacks else []

    # Evening snack uses next 2 snack bullets; if only 1–2 exist, create alternates
    if len(snacks) >= 4:
        eve = snacks[2:4]
    elif len(snacks) >= 2:
        eve = [
            "- Green tea / lemon water + unsalted makhana (small handful).",
            "- Fruit (guava/orange) + 4–6 walnuts.",
        ]
    else:
        eve = []

    g = _pick_bullets(sec["guidelines"], 6)
    g = _drop_noisy_guidelines(g)

    # Default guidelines if missing / all filtered
    if not g:
        g = [
            "- Prefer high-fiber carbs (oats, millets, legumes) and plenty of vegetables.",
            "- Use MUFA/PUFA oils (groundnut/mustard/olive); limit fried foods, ghee, butter.",
            "- For high TG: avoid sugary drinks/desserts/juice; keep portions controlled.",
            "- Add omega-3 veg sources: flax/chia, walnuts.",
            "- Avoid refined flour/bakery foods and trans fats.",
        ]
    # If guidelines are too generic/short, use defaults
    if len(g) < 4:
        g = [
            "- Prefer high-fiber carbs (oats, millets, legumes) and plenty of vegetables.",
            "- Use MUFA/PUFA oils (groundnut/mustard/olive); limit fried foods, ghee, butter.",
            "- For high TG: avoid sugary drinks/desserts/juice; keep portions controlled.",
            "- Add omega-3 veg sources: flax/chia, walnuts.",
            "- Avoid refined flour/bakery foods and trans fats.",
        ]

    # Ensure each meal has 2 options (fallback if missing)
    if len(b) < 2:
        b = (b + ["- Oats/porridge + nuts", "- Ragi upma + sprouts"])[:2]
    if len(mid) < 2:
        mid = (mid + ["- Unsalted makhana/roasted chana", "- Fruit (guava/orange)"])[:2]
    if len(l) < 2:
        l = (l + ["- 2 phulka + veg sabzi + dal (measured)", "- Brown rice + sambar + salad"])[:2]
    if len(eve) < 2:
        eve = (eve + ["- Green tea + sprouts chaat (low salt)", "- 4–6 walnuts"])[:2]
    if len(d) < 2:
        d = (d + ["- Khichdi (moong dal + rice) + veg", "- 2 phulka + lauki/tinda curry"])[:2]

    def _deopt(s: str) -> str:
        """
        Normalize a bullet line into plain text (remove leading '-'
        and any 'Option X:' prefix).
        """
        s = s.strip()
        s = re.sub(r"^\-\s*", "", s)
        s = re.sub(r"(?i)^\s*option\s*\d+\s*:\s*", "", s).strip()
        return s

    # Compose final response (exact headings you use in other agents)
    out: list[str] = []

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
    out.extend(g[:6])  # already "- " bullets

    return "\n".join(out).strip()




# ----------------- HTTP call into Xeon OV Lipids service -----------------
def call_lipids_qwen(
    user_message: str,
    timeout: float = 15.0,
) -> str:
    """
    Calls the Xeon Lipids plan service and normalizes output to our standard 6-section format.
    Always returns a usable 6-section answer (fallback if needed).
    """

    # Strong, unambiguous instruction injected into notes
    guard_notes = (
        "Indian vegetarian only. STRICT: no egg, fish, chicken, meat, seafood.\n"
        "Return exactly these sections in this order:\n"
        "Breakfast, Mid-morning snack, Lunch, Evening snack, Dinner, General Guidelines.\n"
        "Under each meal heading: exactly 2 bullets:\n"
        "- Option 1: <one line>\n"
        "- Option 2: <one line>\n"
        "General Guidelines: 4–6 bullets.\n"
        "No extra prose, no calorie estimates, no Option A/B.\n"
        "Only Indian foods.\n"
    )

    payload = {
        "age": 60,
        "sex": "M",
        "ldl": 150.0,
        "hdl": 40.0,
        "tg": 200.0,
        "comorbidities": [],
        "notes": f"{guard_notes}\nUSER_QUESTION: {user_message}",
    }

    try:
        resp = requests.post(LIPIDS_QWEN_OV_URL, json=payload, timeout=timeout)
        resp.raise_for_status()
        data = resp.json() or {}

        # Raw model output
        raw_plan = (
            data.get("plan")
            or data.get("completion")
            or data.get("text")
            or data.get("output")
            or ""
        ).strip()

        # Normalize + veg-guard
        cleaned = _normalize_to_standard_format(raw_plan)

        # Validate; fallback if not sane
        if not _is_valid_format(cleaned):
            return _fallback_plan(user_message)

        return cleaned

    except Exception:
        # Never crash the orchestrator; always return a clean fallback plan
        return _fallback_plan(user_message)