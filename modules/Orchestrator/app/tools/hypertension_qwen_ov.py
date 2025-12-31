# app/tools/hypertension_qwen_ov.py
import os
import requests

# OV service endpoint for hypertension model (Xeon inference server)

import os
import requests

# OV service endpoint for hypertension model (running on Xeon inference server)
HYPERTENSION_OV_URL = os.getenv(
    "HYPERTENSION_OV_URL",
    "http://192.168.2.69:8082",
)

# ----------------------------------------------------------------------
# Structured system prompt for hypertension / DASH diet
# Lipids-style layout (Breakfast/Lunch/etc.)
# ----------------------------------------------------------------------
SYSTEM_PROMPT = """
You are a clinical diet specialist focused exclusively on hypertension (high blood pressure)
and cardiometabolic risk in Indian adults.

STRICT RULES:
- Base all advice ONLY on the DASH (Dietary Approaches to Stop Hypertension) principles.
- Prefer Indian vegetarian foods:
  dal, sabzi, roti, idli, dosa, sambar, upma, poha, curd, buttermilk, millets, fruits, salads.
- Strongly restrict:
  sodium, pickles, papad, fried snacks, processed foods, bakery items, restaurant foods,
  instant noodles, salted namkeens, preserved meats.
- Keep response UNDER 300 words.
- Do NOT ask follow-up questions.
- Do NOT start a dialogue; respond only once.
- Do NOT repeat the “Patient request” text.
- Do NOT add any sections beyond the ones listed below.
- Output MUST strictly follow the exact headings and bullet structure below.

OUTPUT FORMAT (exact headings):
# Strict, structured system prompt for Hypertension / DASH-style diet
# ----------------------------------------------------------------------
SYSTEM_PROMPT = """
You are a clinical dietitian specialized in hypertension and salt-sensitive
high blood pressure in Indian adults.

GOALS:
- Lower systolic and diastolic blood pressure.
- Reduce sodium intake.
- Increase potassium-rich, fiber-rich vegetarian foods.
- Support weight control and cardiometabolic health.

ABSOLUTE RULES:
- Use ONLY Indian vegetarian foods (idli, dosa, roti, dal, sabzi, poha, upma,
  salads, curd, buttermilk, millets, fruits, nuts, seeds).
- Do NOT recommend: pickles, papad, chutney powders, bakery biscuits, instant noodles,
  chips, fried snacks, packaged soups, processed/packaged foods, salted nuts.
- Do NOT recommend alcohol, sugary drinks, red meat, fish, eggs.
- Prefer steamed/boiled/roasted preparations with minimal oil.
- Mention portions in everyday terms (2 phulkas, 1 small katori, etc.).
- KEEP THE RESPONSE UNDER 260 WORDS.
- Do NOT repeat these instructions or the patient question.
- Do NOT create a conversation or back-and-forth; answer once and stop.

OUTPUT FORMAT (use EXACT headings):

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

STOP after the General Guidelines bullets. Do NOT continue further or repeat any section.
- Bullet 1 ...
- Bullet 2 ...
- Bullet 3 ...
- Bullet 4 ...
""".strip()


def build_hypertension_prompt(user_message: str) -> str:
    """
    Wrap the user message with the strict hypertension system prompt
    and enforce the exact structured output format.
    """
    return (
        SYSTEM_PROMPT
        + "\n\nPatient request:\n"
        + user_message.strip()
        + "\n\nNow generate the hypertension DASH-style plan in the exact required format:\n"
        + (
            "\n\nNow generate a 1-day low-sodium Indian vegetarian hypertension "
            "meal plan in the exact structure above. Do not output anything else.\n"
        )
    )


def is_hypertension_query(text: str) -> bool:
    """
    Simple heuristic router for hypertension / blood pressure topics.
    If any of these keywords appear, route to the hypertension agent.
    """
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


def call_htn_qwen(user_message: str, max_new_tokens: int = 260) -> str:
    """
    Call the Xeon OpenVINO hypertension Qwen service, using the fixed
    structured system prompt plus the user message.
def call_htn_qwen(user_message: str, max_new_tokens: int = 220) -> str:
    """
    Call the Xeon OpenVINO hypertension Qwen service with a strict,
    structured prompt. max_new_tokens is capped to keep latency and
    verbosity under control.

    The OV service is expected to expose a /generate endpoint that
    accepts JSON:
        { "prompt": str, "max_new_tokens": int }

    and returns something like:
        { "completion": str, ... }
    """
    url = f"{HYPERTENSION_OV_URL}/generate"
    prompt = build_hypertension_prompt(user_message)

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
        return f"[Hypertension Qwen OV error: {e}]"

