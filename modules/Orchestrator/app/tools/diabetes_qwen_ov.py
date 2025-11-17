# app/tools/diabetes_qwen_ov.py
import os
from typing import Optional
import requests

DIABETES_OV_URL = os.getenv("DIABETES_OV_URL", "http://192.168.2.69:8080")

def is_diabetes_query(text: str) -> bool:
    """
    Very simple heuristic router:
    - If the text mentions diabetes / blood sugar / glucose / HbA1c, etc
      we route to the specialized diabetes model.
    """
    t = text.lower()
    diabetes_keywords = [
        "diabetes",
        "diabetic",
        "blood sugar",
        "glucose",
        "insulin",
        "hba1c",
        "metformin",
    ]
    return any(k in t for k in diabetes_keywords)


def call_diabetes_qwen(prompt: str, max_new_tokens: int = 80) -> str:
    """
    Call the Xeon OpenVINO diabetes Qwen service.
    """
    url = f"{DIABETES_OV_URL}/generate"
    payload = {
        "prompt": prompt,
        "max_new_tokens": max_new_tokens,
    }
    r = requests.post(url, json=payload, timeout=60)
    r.raise_for_status()
    data = r.json()
    return data.get("completion", "")

