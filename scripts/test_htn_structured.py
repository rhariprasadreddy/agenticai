#!/usr/bin/env python3
import requests

HTN_URL = "http://localhost:8082/generate"

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


def main():
    user_message = "My BP is 160/100. Give me a strict Indian vegetarian DASH diet meal plan."
    prompt = (
        SYSTEM_PROMPT
        + "\n\nPatient request:\n"
        + user_message.strip()
        + "\n\nProvide the diet plan now:\n"
    )

    payload = {
        "prompt": prompt,
        "max_new_tokens": 220,
    }

    print("=== HYPERTENSION (structured prompt to 8082) ===")
    try:
        r = requests.post(HTN_URL, json=payload, timeout=60)
        r.raise_for_status()
        data = r.json()
        text = data.get("completion") or data.get("text") or data.get("output", "")
        print(text.strip())
    except Exception as e:
        print(f"[ERROR] Hypertension OV service: {e}")


if __name__ == "__main__":
    main()
