#!/usr/bin/env python3
import requests

DIABETES_URL = "http://localhost:8080/generate"
HYPERTENSION_URL = "http://localhost:8082/generate"
KIDNEY_URL = "http://localhost:9008/generate"
LIPIDS_URL = "http://localhost:9006/v1/lipids/plan"


def test_diabetes():
    prompt = "I have type 2 diabetes. Give me a one-day Indian vegetarian meal plan."
    payload = {
        "prompt": prompt,
        "max_new_tokens": 200,
    }
    print("\n=== DIABETES (8080) ===")
    try:
        r = requests.post(DIABETES_URL, json=payload, timeout=60)
        r.raise_for_status()
        data = r.json()
        text = data.get("completion") or data.get("text", "")
        print(text.strip())
    except Exception as e:
        print(f"[ERROR] Diabetes service: {e}")


def test_hypertension():
    prompt = "My BP is 150/95. Give me a strict DASH-style Indian vegetarian diet plan."
    payload = {
        "prompt": prompt,
        "max_new_tokens": 250,
    }
    print("\n=== HYPERTENSION (8082) ===")
    try:
        r = requests.post(HYPERTENSION_URL, json=payload, timeout=60)
        r.raise_for_status()
        data = r.json()
        text = data.get("completion") or data.get("text", "")
        print(text.strip())
    except Exception as e:
        print(f"[ERROR] Hypertension service: {e}")


def test_kidney():
    prompt = "I have CKD stage 3 and eat tomatoes daily. Is that safe?"
    payload = {
        "prompt": prompt,
        "max_new_tokens": 200,
    }
    print("\n=== KIDNEY (9008) ===")
    try:
        r = requests.post(KIDNEY_URL, json=payload, timeout=60)
        r.raise_for_status()
        data = r.json()
        text = (
            data.get("completion")
            or data.get("text")
            or data.get("output", "")
        )
        print(text.strip())
    except Exception as e:
        print(f"[ERROR] Kidney service: {e}")


def test_lipids():
    print("\n=== LIPIDS (9006) ===")
    payload = {
        "age": 60,
        "sex": "M",
        "ldl": 150.0,
        "hdl": 40.0,
        "tg": 200.0,
        "comorbidities": [],
        "notes": "My LDL is high. How can I reduce it with an Indian vegetarian diet?",
    }

    try:
        r = requests.post(LIPIDS_URL, json=payload, timeout=60)
        r.raise_for_status()
        data = r.json()

        text = (
            data.get("plan")
            or data.get("completion")
            or data.get("text")
            or data.get("output", "")
        )

        print(text.strip())

    except Exception as e:
        print(f"[ERROR] Lipids service: {e}")


if __name__ == "__main__":
    test_diabetes()
    test_hypertension()
    test_kidney()
    test_lipids()
    print("\n=== DONE ===")

