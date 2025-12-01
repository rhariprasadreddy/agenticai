# app/tools/diabetes_qwen_ov.py
import os
from typing import Optional

import requests

# Diabetes OV server running on inference host
DIABETES_OV_URL = os.getenv(
    "DIABETES_OV_URL",
    "http://192.168.2.69:8080",
)

# ----------------------------------------------------------------------
# Structured but compact system prompt
# ----------------------------------------------------------------------
SYSTEM_PROMPT = """
You are a clinical diet specialist focused on Type 2 Diabetes management.

STRICT RULES:
- Do NOT recommend alcohol in any form.
- Do NOT recommend fruit juice, sweets, jaggery, honey, or refined flour items.
- Use ONLY Indian vegetarian foods (idli, dosa, upma, poha, roti, sabzi, dal, curd, millets, etc.).
- Focus on low–GI carbs, high fiber, adequate protein, and healthy fats.
- Keep portions realistic for an adult Indian patient.
- Keep the response under 250–300 words.

OUTPUT FORMAT:

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
- 4–6 bullet points for lifestyle, carb control, and HbA1c reduction.
""".strip()


def build_diabetes_prompt(user_message: str) -> str:
    return (
        SYSTEM_PROMPT
        + "\n\nPatient request:\n"
        + user_message.strip()
        + "\n\nProvide the 1-day diabetes meal plan now:\n"
    )


def is_diabetes_query(text: Optional[str]) -> bool:
    if not text:
        return False
    t = text.lower()
    keywords = [
        "diabetes",
        "diabetic",
        "blood sugar",
        "glucose",
        "hba1c",
        "t2dm",
        "type 2",
        "type-2",
        "insulin",
        "metformin",
    ]
    return any(k in t for k in keywords)


def call_diabetes_qwen(
    user_message: str,
    max_new_tokens: int = 160,
    timeout: float = 60.0,
) -> str:
    """
    Call the Xeon OpenVINO diabetes Qwen service with a compact, structured prompt.
    """
    url = f"{DIABETES_OV_URL}/generate"
    prompt = build_diabetes_prompt(user_message)

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
        return f"[Diabetes Qwen OV error: {e}]"

