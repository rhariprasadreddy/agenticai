# app/tools/diabetes_qwen_ov.py
import os
import requests

# Diabetes OV server running on inference host (Xeon)
DIABETES_OV_URL = os.getenv(
    "DIABETES_OV_URL",
    "http://192.168.2.69:8080",
)

# ----------------------------------------------------------------------
# Structured system prompt – Diabetes, Indian vegetarian, Lipids-style layout
# ----------------------------------------------------------------------
SYSTEM_PROMPT = """
You are a clinical diet specialist focused on Type 2 Diabetes management in Indian adults.

STRICT RULES:
- Use ONLY Indian vegetarian foods (idli, dosa, upma, poha, roti, sabzi, dal, curd, millets, khichdi, etc.).
- Do NOT recommend:
  - Alcohol in any form
  - Fruit juices, sweets, jaggery, honey, sugarcane juice, soft drinks
  - Refined flour items (maida), deep-fried snacks, bakery sweets
- Focus on:
  - Low–GI carbohydrates
  - High fibre (vegetables, whole grains, dals)
  - Adequate protein (dal, paneer, curd, soy, pulses)
  - Healthy fats (groundnut, sesame, mustard, rice bran oil in small amounts)
- Portions must be realistic for an adult Indian patient.
- Response must be UNDER 300 words.
- Do NOT repeat the “Patient request” text.
- Do NOT add extra sections or extra conversations.
- ONLY output the sections below, in this exact order.

OUTPUT FORMAT (exact headings, bullet points):

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

STOP after the General Guidelines bullets. Do NOT write anything else.
""".strip()


def build_diabetes_prompt(user_message: str) -> str:
    return (
        SYSTEM_PROMPT
        + "\n\nPatient request:\n"
        + user_message.strip()
        + "\n\nNow generate the 1-day diabetes meal plan in the exact required format:\n"
    )


def is_diabetes_query(text: str) -> bool:
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


def call_diabetes_qwen(user_message: str, max_new_tokens: int = 220) -> str:
    """
    Call the Xeon OpenVINO diabetes Qwen service with a strict, structured prompt.
    """
    url = f"{DIABETES_OV_URL}/generate"
    prompt = build_diabetes_prompt(user_message)

    payload = {
        "prompt": prompt,
        "max_new_tokens": max_new_tokens,
    }

    try:
        r = requests.post(url, json=payload, timeout=60)
        r.raise_for_status()
        data = r.json()
        return (data.get("completion") or data.get("text", "")).strip()
    except Exception as e:
        return f"[Diabetes Qwen OV error: {e}]"

