#!/usr/bin/env python3
# app/tools/lipids_qwen_ov.py
import os
import re
from typing import Optional

import requests

# Default: Xeon inference server LIPIDS service
# Adjust IP if your Xeon inference IP is different
LIPIDS_QWEN_OV_URL = os.getenv(
    "LIPIDS_QWEN_OV_URL",
    "http://192.168.2.69:9006/v1/lipids/plan",
)

# --------- Simple lipids-intent detector ----------

_LIPIDS_PAT = re.compile(
    r"\b(ldl|hdl|triglyceride|triglycerides|cholesterol|lipid profile|"
    r"dyslipidemia|hyperlipidemia)\b",
    flags=re.IGNORECASE,
)


def is_lipids_query(text: Optional[str]) -> bool:
    if not text:
        return False
    # very cheap heuristic, same style as HTN
    return bool(_LIPIDS_PAT.search(text))


# --------- HTTP call into Xeon OV Lipids service ----------

def call_lipids_qwen(
    user_message: str,
    timeout: float = 15.0,
) -> str:
    """
    For now, we wrap the free-text user prompt as 'notes' and use
    neutral default lab values. Later, when you plug this into the
    structured patient profile, you'll pass real LDL/HDL/TG values.

    The lipids service schema is:
        POST /v1/lipids/plan
        { age, sex, ldl, hdl, tg, comorbidities, notes }

    Response:
        { "plan": "..." }
    """
    payload = {
        "age": 60,          # neutral defaults for router-based calls
        "sex": "M",
        "ldl": 150.0,
        "hdl": 40.0,
        "tg": 200.0,
        "comorbidities": [],
        "notes": user_message,    # carry the actual question here
    }
    try:
        resp = requests.post(LIPIDS_QWEN_OV_URL, json=payload, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        # Prefer "plan", but fall back to other keys if needed
        return (
            data.get("plan")
            or data.get("completion")
            or data.get("text")
            or data.get("output", "")
        ).strip()
    except Exception as e:
        # Fallback: at least return a usable error string to the caller
        return f"[Lipids Qwen OV error: {e}]"

