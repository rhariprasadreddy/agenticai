#!/usr/bin/env python3
# app/tools/kidney_qwen_ov.py

import os
import re
from typing import Optional

import requests

# -----------------------------------------------------------
# Kidney / CKD OV inference endpoint (Xeon server)
# -----------------------------------------------------------
KIDNEY_QWEN_OV_URL = os.getenv(
    "KIDNEY_QWEN_OV_URL",
    "http://192.168.2.69:9008/generate",  # matches your kidney OV container
)

# -----------------------------------------------------------
# Structured system prompt – CKD, conservative renal dietitian
# Lipids-style layout (Breakfast/Lunch/etc.)
# -----------------------------------------------------------
SYSTEM_PROMPT = """
You are a conservative renal dietitian for CKD patients in India.
You focus on diet, potassium, phosphorus, sodium, protein, and fluids.
You ALWAYS advise the patient to confirm changes with their nephrologist.

STRICT RULES:
- Never prescribe or adjust medications or dialysis.
- Use mostly Indian vegetarian options (dal, sabzi, roti, idli, dosa, rice, curd, etc.).
- Be careful with high-potassium foods (tomato, banana, sapota, coconut water, etc.).
- Be careful with high-phosphorus foods (colas, processed cheese, many bakery items).
- Consider moderate protein and adequate calories.
- Response must be UNDER 300 words.
- Do NOT repeat the “Patient request” text.
- Do NOT create a long back-and-forth conversation.
- ONLY output the sections below, in this exact order.

OUTPUT FORMAT (exact headings):

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
- 4–6 bullet points on potassium/phosphorus restriction, sodium limit, fluids, and when to discuss with nephrologist.

STOP after the General Guidelines bullets. Do NOT write anything else.
""".strip()

# -----------------------------------------------------------
# Simple kidney-intent detector
# -----------------------------------------------------------

_KIDNEY_PAT = re.compile(
    r"\b(ckd|chronic kidney|kidney disease|kidney|renal|egfr|creatinine|"
    r"dialysis|nephro|proteinuria|potassium|phosphorus|fluid restriction)\b",
    flags=re.IGNORECASE,
)


def is_kidney_query(text: Optional[str]) -> bool:
    if not text:
        return False
    return bool(_KIDNEY_PAT.search(text))


# -----------------------------------------------------------
# Call Kidney Qwen OV service on Xeon
# -----------------------------------------------------------


def build_kidney_prompt(user_message: str) -> str:
    return (
        SYSTEM_PROMPT
        + "\n\nPatient request:\n"
        + user_message.strip()
        + "\n\nNow generate the CKD diet plan in the exact required format:\n"
    )


def call_kidney_qwen(
    user_message: str,
    max_new_tokens: int = 220,
    timeout: float = 60.0,
) -> str:
    """
    Thin wrapper around the Xeon OpenVINO kidney generator.

    Expected request:
        POST /generate
        { "prompt": str, "max_new_tokens": int }

    Kidney OV service currently returns:
        { "output": "..." }
    but we also check "completion"/"text" for future-proofing.
    """
    payload = {
        "prompt": build_kidney_prompt(user_message),
        "max_new_tokens": max_new_tokens,
    }

    try:
        resp = requests.post(KIDNEY_QWEN_OV_URL, json=payload, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        return (
            data.get("completion")
            or data.get("text")
            or data.get("output", "")
        ).strip()
    except Exception as e:
        return f"[Kidney Qwen OV error: {e}]"

