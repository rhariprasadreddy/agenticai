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

def call_kidney_qwen(
    user_message: str,
    max_new_tokens: int = 200,
    timeout: float = 60.0,
) -> str:
    """
    Thin wrapper around the Xeon OpenVINO kidney generator.

    Expected request:
        POST /generate
        { "prompt": str, "max_new_tokens": int }

    The service currently returns:
        { "output": "..." }
    but we also check "completion"/"text" for future-proofing.
    """
    payload = {
        "prompt": user_message,
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

