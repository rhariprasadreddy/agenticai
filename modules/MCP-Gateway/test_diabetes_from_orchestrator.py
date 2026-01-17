#!/usr/bin/env python3
import requests

DIABETES_URL = "http://192.168.2.69:8080/generate"


def build_diabetes_prompt() -> str:
    return (
        "You are an Indian diabetes specialist dietitian.\n"
        "Age: 55, Sex: M\n"
        "BMI: 29.4\n"
        "Fasting glucose: 155 mg/dL, HbA1c: 8.1%\n"
        "Comorbidities: hypertension\n"
        "Extra notes: Sedentary, prefers rice and sweets, newly diagnosed type 2 diabetic.\n\n"
        "Generate a concise 1-day Indian diabetic-friendly diet plan (breakfast, lunch, "
        "snacks, dinner) focused on blood glucose and HbA1c control.\n"
        "- Use bullet points.\n"
        "- Prefer low-GI carbs, high fiber, healthy fats, adequate protein.\n"
        "- Minimize refined sugar and simple carbs.\n"
        "- Use mostly Indian foods (idli, dosa, roti, dal, sabzi, curd, upma, poha, etc.).\n"
        "- Keep the response under 350 words.\n"
    )


def call_diabetes_agent():
    payload = {
        "prompt": build_diabetes_prompt(),
        "max_new_tokens": 350,
    }

    print("🔹 Sending to DIABETES_OV:", DIABETES_URL)
    resp = requests.post(DIABETES_URL, json=payload, timeout=60)
    print("🔹 HTTP status:", resp.status_code)
    print("🔹 Raw JSON:", resp.text)

    resp.raise_for_status()
    data = resp.json()
    print("\n✅ Parsed response.reply:\n")
    print(data.get("reply", "<no reply field>"))


if __name__ == "__main__":
    call_diabetes_agent()

