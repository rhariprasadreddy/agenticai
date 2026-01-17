#!/usr/bin/env python3
import time
import json
import requests

ENGINES = [
    ("diabetes",      "http://localhost:8080/generate",
     "You are a diabetes dietitian. Give a 1-day Indian vegetarian low-GI meal plan in bullets. No extra text.", 160),

    ("hypertension",  "http://localhost:8082/generate",
     "You are a hypertension dietitian. STRICT DASH, strict low-salt Indian vegetarian 1-day plan. "
     "Use headings: Breakfast, Mid-morning snack, Lunch, Evening snack, Dinner, General Guidelines. "
     "Each meal section: exactly 2 bullets. No extra prose.", 160),

    ("lipids",        "http://localhost:9006/generate",
     "You are a lipid dietitian. 1-day Indian veg meal plan to lower LDL/TG. "
     "Use headings + 2 options each meal + 4-6 guidelines.", 180),

    ("kidney",        "http://localhost:9008/generate",
     "You are a kidney dietitian. CKD stage 3 Indian vegetarian 1-day plan: low salt, moderate protein. "
     "Mention potassium/phosphorus caution. Use headings + 2 options each meal.", 180),
]

KEY_CANDIDATES = ("output", "text", "completion", "reply", "response", "result")

def extract_text(payload: dict) -> str:
    if not isinstance(payload, dict):
        return str(payload)
    for k in KEY_CANDIDATES:
        v = payload.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    # fallback: stringify small payload
    return json.dumps(payload, ensure_ascii=False)[:1200]

def run_one(name, url, prompt, max_new_tokens):
    body = {"prompt": prompt, "max_new_tokens": max_new_tokens}
    t0 = time.time()
    try:
        r = requests.post(url, json=body, timeout=(3, 90))
        dt = time.time() - t0
        ct = r.headers.get("content-type", "")
        try:
            data = r.json()
        except Exception:
            data = {"_raw": r.text}
        text = extract_text(data)
        return {
            "name": name,
            "url": url,
            "http": r.status_code,
            "time_s": round(dt, 3),
            "content_type": ct,
            "preview": text[:700].replace("\r", ""),
        }
    except Exception as e:
        dt = time.time() - t0
        return {
            "name": name,
            "url": url,
            "http": None,
            "time_s": round(dt, 3),
            "error": str(e),
        }

def main():
    print("=== OpenVINO Engines Direct Smoke Test ===")
    for name, url, prompt, mx in ENGINES:
        res = run_one(name, url, prompt, mx)
        print("\n---", name.upper(), "---")
        print("URL:", res["url"])
        print("HTTP:", res.get("http"), "TIME_S:", res.get("time_s"))
        if "error" in res:
            print("ERROR:", res["error"])
            continue
        print("CONTENT-TYPE:", res.get("content_type"))
        print("PREVIEW:\n", res.get("preview", ""))

if __name__ == "__main__":
    main()

