#!/usr/bin/env python3
import os
import re
from typing import Optional

import requests

# Default: Xeon inference server HTN service
HTN_QWEN_OV_URL = os.getenv(
    "HTN_QWEN_OV_URL",
    "http://192.168.2.69:8082/generate",
)

# --------- Simple hypertension-intent detector ----------

_HTN_PAT = re.compile(
    r"\b(hypertension|high blood pressure|bp control|bp controlled|"
    r"low[- ]sodium|dash diet|salt restriction|salt-restricted)\b",
    flags=re.IGNORECASE,
)

def is_hypertension_query(text: str) -> bool:
    if not text:
        return False
    # very cheap heuristic
    return bool(_HTN_PAT.search(text))


# --------- HTTP call into Xeon OV HTN service ----------

def call_htn_qwen(
    prompt: str,
    max_new_tokens: int = 80,
    timeout: float = 15.0,
) -> str:
    payload = {
        "prompt": prompt,
        "max_new_tokens": max_new_tokens,
    }
    try:
        resp = requests.post(HTN_QWEN_OV_URL, json=payload, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        # Service schema: {prompt, completion, num_tokens}
        return data.get("completion", "").strip()
    except Exception as e:
        # Fallback: at least return a usable error string to the caller
        return f"[HTN Qwen OV error: {e}]"
