# app/tools/hypertension_qwen_ov.py
import os
from typing import Optional

import requests

# OV service endpoint for hypertension model (running on inference server 69)
HYPERTENSION_OV_URL = os.getenv(
    "HYPERTENSION_OV_URL",
    "http://192.168.2.69:8082",
)

# ----------------------------------------------------------------------
# Structured system prompt for hypertension / DASH diet
# ----------------------------------------------------------------------

SYSTEM_PROMPT = """
You are a clinical diet specialist focused exclusively on hypertension (high blood pressure)
and cardiometabolic risk.

You must follow these STRICT rules:
- Base all advice ONLY on DASH (Dietary Approaches to Stop Hypertension).
- Prefer Indian vegetarian foods (dal, sabzi, roti, idli, dosa, sambar, upma, poha, millets).
- Strongly restrict sodium, pickles, papad, fried snacks, processed foods, bakery items,
  restaurant foods, and instant noodles.
- NEVER invent new "Patient request" sections. Respond ONLY once.
- NEVER ask follow-up questions.
- NEVER continue beyond the required meal plan.
- Output MUST strictly follow the required format below.
- KEEP THE RESPONSE UNDER 300 WORDS.

Required OUTPUT FORMAT:

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
- 4–6 bullet points of lifestyle and salt-reduction advice.

STOP AFTER THIS EXACT FORMAT. DO NOT CONTINUE FURTHER.
""".strip()


def build_htn_prompt(user_message: str) -> str:
    return (
        SYSTEM_PROMPT
        + "\n\nPatient request:\n"
        + user_message.strip()
        + "\n\nProvide the diet plan now:\n"
    )


def is_hypertension_query(text: Optional[str]) -> bool:
    """
    Simple heuristic router for hypertension / blood pressure topics.
    If any of these keywords appear, route to the hypertension agent.
    """
    if not text:
        return False
    t = text.lower()
    keywords = [
        "hypertension",
        "high blood pressure",
        "blood pressure",
        "bp ",
        " bp",
        "high bp",
        "htn",
        "systolic",
        "diastolic",
        "dash diet",
        "dash-style",
    ]
    return any(k in t for k in keywords)


def call_htn_qwen(
    user_message: str,
    max_new_tokens: int = 256,
    timeout: float = 60.0,
) -> str:
    """
    Call the Xeon OpenVINO hypertension Qwen service.
    """
    url = f"{HYPERTENSION_OV_URL}/generate"
    prompt = build_htn_prompt(user_message)

    payload = {
        "prompt": prompt,
        "max_new_tokens": max_new_tokens,
    }

    try:
        r = requests.post(url, json=payload, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        return (
            data.get("completion")
            or data.get("text")
            or data.get("output", "")
        ).strip()
    except Exception as e:
        return f"[Hypertension Qwen OV error: {e}]"

